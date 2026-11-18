"""Fixed-input JOB pilot: independent optimizer trials and shared repeated plans."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import time
import uuid

import dimod
import numpy as np
import psycopg
from psycopg import sql

from qopt.cardinality import estimate_inputs
from qopt.cli import ROOT, provenance, write_json
from qopt.core import intermediate_cost, plan_hash, valid_membership
from qopt.hints import extract_join_tree, leading_hint, left_deep_tree, verify_tree
from qopt.store import RunStore, StopRequested, packed, failure


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def as_tuple(value):
    return tuple(as_tuple(x) for x in value) if isinstance(value,list) else value


def explain(conn, statement, analyze=False):
    options = 'ANALYZE, BUFFERS, ' if analyze else ''
    return conn.execute(f'EXPLAIN ({options}FORMAT JSON) '+statement).fetchone()[0][0]


def mode(conn, config, solver, seed=None):
    conn.execute('SET geqo='+('off' if solver == 'sa' else 'on'))
    threshold = 2 if solver == 'geqo' else config['baseline_geqo_threshold']
    conn.execute("SELECT set_config('geqo_threshold',%s,false)",(str(threshold),))
    conn.execute("SELECT set_config('geqo_seed',%s,false)",
                 (str(seed if solver == 'geqo' else config['baseline_geqo_seed']),))


def preflight(conn, statement, solver, seed, expected, config):
    mode(conn,config,solver,seed)
    started = time.perf_counter()
    plan = explain(conn,statement)
    result = {'status':'ok','explain':plan,'plan_hash':plan_hash(plan['Plan']),
        'estimated_total_cost':plan['Plan']['Total Cost'],
        'validation_seconds':time.perf_counter()-started,
        'recipe':{'sql':statement,'solver':solver,'seed':seed,'expected_tree':expected}}
    try:
        # Even GEQO and default trees must be parseable by our verifier.
        result['observed_tree'] = extract_join_tree(plan['Plan'])
        if expected is not None:
            verify_tree(plan['Plan'],expected)
    except ValueError as exc:
        result.update(status='unverified_plan',message=str(exc))
    return result


def controls(conn, query, baseline, config):
    aliases = [item['alias'] for item in query['alias_mapping']]
    neighbors = defaultdict(set)
    for a,b in query['edges']:
        neighbors[a].add(b)
        neighbors[b].add(a)
    baseline_tree = as_tuple(baseline['observed_tree'])
    tree = None
    for first in sorted(aliases):
        order = [first]
        while len(order) < len(aliases):
            frontier = set.union(*(neighbors[a] for a in order))-set(order)
            if not frontier:
                raise ValueError('Control needs a connected graph')
            order.append(sorted(frontier)[0])
        tree = left_deep_tree(order)
        if tree != baseline_tree:
            break
    if tree == baseline_tree:
        raise ValueError('No nondefault control tree')
    statement = leading_hint(tree)+'\n'+(ROOT/query['sql_path']).read_text()
    mode(conn,config,'default')
    conn.execute('SET pg_hint_plan.enable_hint=off')
    try:
        ignored = explain(conn,statement)
    finally:
        conn.execute('SET pg_hint_plan.enable_hint=on')
    rejected = extract_join_tree(ignored['Plan']) != tree
    positive = preflight(conn,statement,'sa',None,tree,config)
    return {'status':'ok' if rejected and positive['status']=='ok' else 'control_failed',
        'disabled_hint_rejected':rejected,'expected_tree':tree,
        'disabled_explain':ignored,'enabled':positive}


def trial_sa(conn, query, model, bqm, run_id, baseline, config):
    from dwave.samplers import SimulatedAnnealingSampler
    from qdbo.join_ordering.backend.jo_utils import parse_selectivities
    from qdbo.join_ordering.helpers import read_out
    cards,factors = model['cards'],model['factors']
    pred,pred_sel = parse_selectivities(factors)
    seed = config['seed']+run_id
    started = time.perf_counter()
    best = SimulatedAnnealingSampler().sample(bqm,seed=seed,
        num_reads=config['sa_reads'],num_sweeps=config['sa_sweeps']).first
    solve_seconds = time.perf_counter()-started
    started = time.perf_counter()
    bits = [int(best.sample[v]) for v in bqm.variables]
    order,upstream_cost,connected = read_out(np.asarray(bits),cards,pred,pred_sel,{})
    cost = intermediate_cost(order,cards,factors)
    if not np.isclose(cost,upstream_cost,atol=1.01,rtol=0):
        raise ValueError('Independent decoded cost disagrees with upstream')
    aliases = [query['alias_mapping'][i]['alias'] for i in order]
    tree = left_deep_tree(aliases)
    statement = leading_hint(tree)+'\n'+(ROOT/query['sql_path']).read_text()
    decode_seconds = time.perf_counter()-started
    try:
        result = preflight(conn,statement,'sa',None,tree,config)
    except psycopg.Error as exc:
        result = failure(exc)
    started = time.perf_counter()
    fallback = result['status']!='ok' or result['estimated_total_cost']>baseline['estimated_total_cost']
    decision_seconds = time.perf_counter()-started
    result.update(solver='sa',run=run_id,seed=seed,order=order,aliases=aliases,
        bits=bits,energy=float(best.energy),model_cost=cost,
        raw_membership_valid=valid_membership(bits,len(cards)),
        decoder_selected_connected=bool(connected),solve_seconds=solve_seconds,
        decode_seconds=decode_seconds,guard_fallback=fallback,
        guard_decision_seconds=decision_seconds)
    return result


def trial_geqo(conn, query, run_id, baseline, config):
    seed = (run_id+1)/(config['solve_repeats']+1)
    result = preflight(conn,(ROOT/query['sql_path']).read_text(),'geqo',seed,None,config)
    started = time.perf_counter()
    fallback = result['status']!='ok' or result['estimated_total_cost']>baseline['estimated_total_cost']
    result.update(solver='geqo',run=run_id,seed=seed,guard_fallback=fallback,
                  guard_decision_seconds=time.perf_counter()-started)
    return result


def execute_plan(conn, candidate, config, session):
    recipe = candidate['recipe']
    mode(conn,config,recipe['solver'],recipe['seed'])
    started = time.perf_counter()
    observed = explain(conn,recipe['sql'],True)
    wall = time.perf_counter()-started
    result = {'status':'ok','session':session,'explain':observed,
        'plan_hash':plan_hash(observed['Plan']),
        'execution_ms':observed['Execution Time'],'planning_ms':observed['Planning Time'],
        'client_wall_ms':wall*1000}
    try:
        if recipe['expected_tree'] is not None:
            verify_tree(observed['Plan'],as_tuple(recipe['expected_tree']))
        if result['plan_hash']!=candidate['plan_hash']:
            raise ValueError('Physical plan changed since preflight')
    except ValueError as exc:
        result.update(status='execution_plan_mismatch',message=str(exc))
    return result


def execute_query_plans(store, conn, query_id, candidates, config, session):
    if all(store.get(f'{query_id}/execution/{r:02d}/{h}') is not None
           for r in range(config['execution_repeats']) for h in candidates):
        return
    timeout_plans = {r['payload'].get('requested_plan_hash') for r in store.records(query_id=query_id)
                     if r['phase'] in {'warmup','execution'} and r['payload'] and r['payload']['status']=='timeout'}
    prior_failed = {r['payload'].get('requested_plan_hash') for r in store.records(query_id=query_id)
                    if r['phase'] in {'warmup','execution'} and r['payload'] and r['payload']['status']!='ok'}
    # A fresh session warms every still-eligible plan, including after a crash.
    for fingerprint in sorted(candidates):
        if fingerprint in prior_failed:
            continue
        key = f'{query_id}/warmup/{session}/{fingerprint}'
        result = store.perform(key,'warmup',query_id,
            lambda c=candidates[fingerprint]: execute_plan(conn,c,config,session),
            context={'requested_plan_hash':fingerprint,'session':session})
        if result['status']!='ok':
            prior_failed.add(fingerprint)
            if result['status']=='timeout':
                timeout_plans.add(fingerprint)
    for repetition in range(config['execution_repeats']):
        fingerprints = sorted(candidates)
        random.Random(f"{config['seed']}:{query_id}:{repetition}").shuffle(fingerprints)
        for fingerprint in fingerprints:
            key = f'{query_id}/execution/{repetition:02d}/{fingerprint}'
            if store.get(key) is not None:
                continue
            if fingerprint in prior_failed:
                reason = 'not_run_after_timeout' if fingerprint in timeout_plans else 'not_run_after_warmup_or_execution_failure'
                store.perform(key,'execution',query_id,lambda r=reason:{'status':r,
                    'requested_plan_hash':fingerprint,'repetition':repetition,'session':session})
                continue
            result = store.perform(key,'execution',query_id,
                lambda c=candidates[fingerprint]:execute_plan(conn,c,config,session),
                context={'requested_plan_hash':fingerprint,'repetition':repetition,'session':session})
            if result['status']!='ok':
                prior_failed.add(fingerprint)
                if result['status']=='timeout':
                    timeout_plans.add(fingerprint)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=ROOT/'config/job-pilot-v1.json')
    parser.add_argument('--max-new-tasks',type=int,help='Stop cleanly at a durable task boundary; rerun to resume')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    workload = ROOT/config['workload']
    pilot = json.loads(workload.read_text())
    binary = next(iter(sorted((ROOT/'.local/lib').glob('pg_hint_plan.*'))),None)
    if binary is None:
        raise RuntimeError('Build pg_hint_plan first')
    source_files = ['job_runner.py','store.py','core.py','hints.py','cardinality.py']
    identity = {'config':config,'pilot_sha256':digest(workload),
        'source_sha256':{name:digest(ROOT/'src/qopt'/name) for name in source_files},
        'hint_binary_sha256':digest(binary),'load_receipt_sha256':digest(ROOT/'data/load-receipt.json')}
    for query in pilot['queries']:
        if digest(ROOT/query['sql_path'])!=query['sql_sha256']:
            raise ValueError('Frozen SQL changed')
    session = uuid.uuid4().hex[:12]
    dsn = os.environ.get('QOPT_JOB_DSN',f'host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=qopt_job')
    with RunStore(args.output,identity,args.max_new_tasks) as store, psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as conn:
        conn.execute(sql.SQL('LOAD {}').format(sql.Literal(str(binary))))
        for statement in ('SET search_path TO public','SET max_parallel_workers_per_gather=0','SET jit=off',
                          'SET pg_hint_plan.enable_hint=on','SET default_transaction_read_only=on'):
            conn.execute(statement)
        for name,value in [('statement_timeout',config['statement_timeout_ms']),('work_mem',config['work_mem']),
                           ('geqo_effort',config['geqo_effort']),('geqo_pool_size',config['geqo_pool_size']),
                           ('geqo_generations',config['geqo_generations'])]:
            conn.execute('SELECT set_config(%s,%s,false)',(name,str(value)))
        stats = [r[0] for r in conn.execute("SELECT row_to_json(s)::text FROM pg_stats s WHERE schemaname='public' ORDER BY tablename,attname,inherited").fetchall()]
        expected = json.loads((ROOT/'data/load-receipt.json').read_text())
        if hashlib.sha256('\n'.join(stats).encode()).hexdigest()!=expected['statistics_sha256']:
            raise RuntimeError('Database statistics changed since imported snapshot')
        manifest_path = args.output/'manifest.json'
        if not manifest_path.exists():
            metadata_args = argparse.Namespace(command='job-pilot',config=str(args.config),output=str(args.output))
            write_json(manifest_path,{**provenance(metadata_args),'identity':identity,
                'settings':dict(conn.execute('SELECT name,setting FROM pg_settings').fetchall()),
                'planned_optimizer_trials':len(pilot['queries'])*config['solve_repeats']*2,
                'kind':'JOB CPU fixed-input pilot; SA and GEQO; no quantum hardware'})
        sessions = args.output/'sessions.jsonl'
        with sessions.open('a') as stream:
            stream.write(packed({'session':session,'utc':datetime.now(timezone.utc).isoformat(),
                'max_new_tasks':args.max_new_tasks})+'\n')
        try:
            # Finish ALL optimizer draws before observing any execution times.
            for query in pilot['queries']:
                qid = query['query_id']
                mode(conn,config,'default')
                model = store.perform(f'{qid}/model','model',qid,lambda q=query:estimate_inputs(conn,q))
                baseline = store.perform(f'{qid}/baseline','baseline',qid,
                    lambda q=query:preflight(conn,(ROOT/q['sql_path']).read_text(),'default',None,None,config))
                control = store.perform(f'{qid}/control','control',qid,
                    lambda q=query,b=baseline:controls(conn,q,b,config)) if baseline['status']=='ok' else {'status':'baseline_failed'}
                eligible = (model['status']=='ok' and baseline['status']=='ok' and control['status']=='ok'
                            and model.get('upstream_factor_parser_preserves_all_predicate_edges',False))
                if eligible:
                    def build(m=model):
                        from qdbo.join_ordering.backend.bqm_solver_execution import build_bqm
                        from qdbo.join_ordering.backend.jo_utils import parse_selectivities
                        pred,sel = parse_selectivities(m['factors'])
                        bqm = build_bqm(m['cards'],pred,sel)
                        return {'bqm':bqm.to_serializable(use_bytes=False),'variables':len(bqm.variables)}
                    encoding = store.perform(f'{qid}/encoding','encoding',qid,build)
                    eligible = encoding['status']=='ok'
                    bqm = dimod.BinaryQuadraticModel.from_serializable(encoding['bqm']) if eligible else None
                for solver in ('sa','geqo'):
                    for run_id in range(config['solve_repeats']):
                        key = f'{qid}/solve/{solver}/{run_id:03d}'
                        if not eligible:
                            store.perform(key,'solve',qid,lambda s=solver,i=run_id:{'status':'blocked_setup',
                                'solver':s,'run':i,'guard_fallback':True})
                        elif solver=='sa':
                            store.perform(key,'solve',qid,lambda i=run_id,q=query,m=model,b=bqm,base=baseline:
                                trial_sa(conn,q,m,b,i,base,config),context={'solver':solver,'run':run_id,'seed':config['seed']+run_id})
                        else:
                            store.perform(key,'solve',qid,lambda i=run_id,q=query,base=baseline:
                                trial_geqo(conn,q,i,base,config),context={'solver':solver,'run':run_id,
                                'seed':(run_id+1)/(config['solve_repeats']+1)})
                print(f"{qid}: optimizer draws recorded (setup {'ok' if eligible else 'failed'})",flush=True)
            for query in pilot['queries']:
                qid = query['query_id']
                baseline = store.get(f'{qid}/baseline')
                if baseline['status']!='ok':
                    continue
                candidates = {baseline['plan_hash']:baseline}
                for row in store.records('solve',qid):
                    trial = row['payload']
                    if trial['status']=='ok':
                        candidates.setdefault(trial['plan_hash'],trial)
                print(f'{qid}: measuring {len(candidates)} distinct physical plans',flush=True)
                execute_query_plans(store,conn,qid,candidates,config,session)
                print(f'{qid}: execution schedule recorded',flush=True)
            write_json(args.output/'state.json',{'state':'complete','session':session})
        except StopRequested as exc:
            write_json(args.output/'state.json',{'state':'checkpointed','message':str(exc),'session':session})
            print(str(exc),flush=True)
        finally:
            with (args.output/'tasks.jsonl').open('w') as stream:
                for row in store.records():
                    stream.write(packed(row)+'\n')


if __name__=='__main__':
    main()
