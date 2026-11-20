"""Prospective paired-plan study and real validated warm-request guard replay."""
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import subprocess
import time
import uuid

import dimod
import numpy as np
import psycopg
from psycopg import sql

from qopt.cli import ROOT,write_json
from qopt.calibration import keep_awake,clock_quality
from qopt.core import plan_hash,intermediate_cost
from qopt.encoding_audit import components
from qopt.hints import extract_join_tree
from qopt.job_runner import mode,controls
from qopt.store import RunStore,failure
from qopt.study_hints import hint_for,verify_order


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def upstream_identity():
    result={}
    for name in ['qdbo','q2o','job','pg_hint_plan']:
        repo=ROOT/'vendor'/name
        files=subprocess.check_output(['git','-C',str(repo),'ls-files','*.py'],text=True).splitlines()
        result[name]={'commit':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(),
            'tracked_python_sha256':{f:sha(repo/f) for f in files}}
    return result


def preflight(conn,statement,solver,seed,aliases,directed,config):
    mode(conn,config,solver,seed)
    started=time.perf_counter_ns()
    tree=None
    try:
        observed=conn.execute('EXPLAIN (FORMAT JSON) '+statement).fetchone()[0][0]
        tree=extract_join_tree(observed['Plan'])
        if aliases is not None:
            verify_order(observed['Plan'],aliases,directed)
        status='ok'
    except ValueError as exc:
        status='unverified_plan'
        message=str(exc)
    except psycopg.Error as exc:
        return {**failure(exc),'preflight_ms':(time.perf_counter_ns()-started)/1e6}
    result={'status':status,'explain':observed,'plan_hash':plan_hash(observed['Plan']),
        'estimated_total_cost':observed['Plan']['Total Cost'],'observed_tree':tree,
        'preflight_ms':(time.perf_counter_ns()-started)/1e6,
        'recipe':{'sql':statement,'solver':solver,'seed':seed,'aliases':aliases,'directed':directed}}
    if status!='ok':
        result['message']=message
    return result


def draw_sa(model,bqm,run,config):
    from dwave.samplers import SimulatedAnnealingSampler
    from qdbo.join_ordering.backend.jo_utils import parse_selectivities
    from qdbo.join_ordering.helpers import read_out,get_raw_join_order
    pred,sel=parse_selectivities(model['factors'])
    started=time.perf_counter_ns()
    best=SimulatedAnnealingSampler().sample(bqm,seed=config['seed']+run,
        num_reads=config['sa_reads'],num_sweeps=config['sa_sweeps']).first
    sampling_ms=(time.perf_counter_ns()-started)/1e6
    started=time.perf_counter_ns()
    bits=[int(best.sample[v]) for v in bqm.variables]
    order,cost,connected=read_out(np.asarray(bits),model['cards'],pred,sel,{})
    independent_cost=intermediate_cost(order,model['cards'],model['factors'])
    if not np.isclose(cost,independent_cost,atol=1.01,rtol=0):
        raise ValueError('Decoded intermediate cost disagrees')
    n=len(model['cards'])
    raw=get_raw_join_order(np.asarray(bits[:n*(n-2)]).reshape(n,n-2).dot(np.arange(n-2,0,-1)))
    audit=components(bits,model['cards'],pred,sel)
    if not np.isclose(float(best.energy),audit['reconstructed_energy'],atol=1e-5,rtol=1e-8):
        raise ValueError('Independent QUBO reconstruction disagrees')
    aliases=[model['alias_mapping'][i]['alias'] for i in order]
    return {'status':'ok','seed':config['seed']+run,'run':run,'bits':bits,
        'bits_sha256':hashlib.sha256(bytes(bits)).hexdigest(),'energy':float(best.energy),
        'order':order,'raw_order':raw,'aliases':aliases,'decoder_selected_connected':bool(connected),
        'decoder_changed_raw_order':raw!=order,'model_cost':independent_cost,'encoding_audit':audit,
        'sampling_ms':sampling_ms,'decode_and_audit_ms':(time.perf_counter_ns()-started)/1e6}


def proposal(conn,statement,model,bqm,method,run,config,sample=None):
    if method=='geqo':
        return preflight(conn,statement,'geqo',(run+1)/(config['solve_repeats']+1),None,False,config)
    sample=sample if sample is not None else draw_sa(model,bqm,run,config)
    directed=method=='sa_directed'
    result=preflight(conn,hint_for(sample['aliases'],directed)+'\n'+statement,
        'sa',None,sample['aliases'],directed,config)
    result['sample_bits_sha256']=sample['bits_sha256']
    result['sampling_ms']=sample['sampling_ms']
    result['decode_and_audit_ms']=sample['decode_and_audit_ms']
    return result


def gate(output,config,phase,qid):
    started=time.perf_counter();stable=0;checks=[]
    limit=config['resource_load_per_core_limit']*(os.cpu_count() or 1)
    while stable<config['resource_stable_checks']:
        load=os.getloadavg()[0];checks.append(load)
        stable=stable+1 if load<=limit else 0
        if stable<config['resource_stable_checks']:
            if load>limit:
                write_json(output/'state.json',{'state':'waiting_for_resources','phase':phase,'query_id':qid,
                    'load':load,'limit':limit,'utc':stamp()})
            time.sleep(config['resource_check_interval_seconds'])
    wait=time.perf_counter()-started
    with (output/'resource-events.jsonl').open('a') as stream:
        stream.write(json.dumps({'utc':stamp(),'phase':phase,'query_id':qid,'wait_seconds':wait,
            'checks':checks,'limit':limit})+'\n')
    write_json(output/'state.json',{'state':'running','phase':phase,'query_id':qid})
    return {'admission_wait_seconds':wait,'load_before':checks[-1],'admission_limit':limit}


def verify_observed(observed,candidate):
    fingerprint=plan_hash(observed['Plan'])
    if fingerprint!=candidate['plan_hash']:
        raise ValueError('Physical plan changed')
    recipe=candidate['recipe']
    extract_join_tree(observed['Plan'])
    if recipe['aliases'] is not None:
        verify_order(observed['Plan'],recipe['aliases'],recipe['directed'])
    return fingerprint


def profile_once(conn,candidate,config):
    recipe=candidate['recipe'];mode(conn,config,recipe['solver'],recipe['seed'])
    mono=time.perf_counter_ns();wall=time.time_ns()
    try:
        observed=conn.execute('EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) '+recipe['sql']).fetchone()[0][0]
        try:
            fingerprint=verify_observed(observed,candidate)
            status='ok'
        except ValueError:
            fingerprint=plan_hash(observed['Plan']);status='execution_plan_mismatch'
        result={'status':status,'execution_ms':observed['Execution Time'],'planning_ms':observed['Planning Time'],
            'plan_hash':fingerprint,'explain':observed}
    except psycopg.Error as exc:
        result=failure(exc)
    client=(time.perf_counter_ns()-mono)/1e6;utc=(time.time_ns()-wall)/1e6
    result.update(client_wall_ms=client,utc_elapsed_ms=utc,
        clock_anomaly=clock_quality(result.get('execution_ms'),client,utc,config['clock_tolerance_ms']),
        load_after=list(os.getloadavg()))
    return result


def plain_once(conn,candidate,config):
    recipe=candidate['recipe'];mode(conn,config,recipe['solver'],recipe['seed'])
    before=conn.execute('EXPLAIN (FORMAT JSON) '+recipe['sql']).fetchone()[0][0]
    verify_observed(before,candidate)
    mono=time.perf_counter_ns();wall=time.time_ns()
    try:
        rows=conn.execute(recipe['sql']).fetchall()
        result={'status':'ok','result_rows':len(rows),'result_sha256':hashlib.sha256(json.dumps(rows,default=str).encode()).hexdigest()}
    except psycopg.Error as exc:
        result=failure(exc)
    client=(time.perf_counter_ns()-mono)/1e6;utc=(time.time_ns()-wall)/1e6
    result.update(execute_client_ms=client,execute_utc_ms=utc,
        clock_anomaly=clock_quality(None,client,utc,config['clock_tolerance_ms']),
        plan_observation='Plain SELECT timed plan not directly observed; verified pre/post EXPLAIN',
        pre_plan_hash=candidate['plan_hash'])
    if result['status']=='ok':
        after=conn.execute('EXPLAIN (FORMAT JSON) '+recipe['sql']).fetchone()[0][0]
        try:
            result['post_plan_hash']=verify_observed(after,candidate)
        except ValueError:
            result['post_plan_hash']=plan_hash(after['Plan']);result['status']='execution_plan_mismatch'
    return result


def failures(store,qid,stage):
    return {r['payload']['requested_plan_hash']:r['key'] for r in store.records(query_id=qid)
        if r['state']=='finished' and r['phase'] in {'warmup','profile','policy'} and r['payload']
        and r['payload'].get('stage')==stage and r['payload'].get('requested_plan_hash')
        and r['payload']['status'] in {'timeout','error','execution_plan_mismatch'}}


def warm(store,conn,qid,candidates,config,session,stage):
    blocked=failures(store,qid,stage)
    hashes=sorted(candidates);random.Random(f"{config['seed']}:{qid}:{stage}:warmup").shuffle(hashes)
    for h in hashes:
        if h in blocked:
            continue
        key=f'{qid}/warmup/{session}/{stage}/{h}'
        if store.get(key) is not None:
            continue
        admission=gate(store.directory,config,stage+'_warmup',qid)
        result=store.perform(key,'warmup',qid,
            lambda c=candidates[h]:profile_once(conn,c,config) if stage=='profile' else plain_once(conn,c,config),
            context={'session':session,'stage':stage,'requested_plan_hash':h,**admission})
        if result['status'] in {'timeout','error','execution_plan_mismatch'}:
            blocked[h]=key
    return blocked


def run_profiles(store,conn,qid,candidates,baseline,config,session):
    def key(r,h,role):
        return f'{qid}/profile/{r:02d}/{h}/{role}'
    if all(store.get(key(r,h,role)) is not None for r in range(config['execution_repeats']) for h in candidates for role in ['baseline','candidate']):
        return
    blocked=warm(store,conn,qid,candidates,config,session,'profile')
    for r in range(config['execution_repeats']):
        hashes=sorted(candidates);random.Random(f"{config['seed']}:{qid}:{r}:pairs").shuffle(hashes)
        for h in hashes:
            roles=['baseline','candidate'];random.Random(f"{config['seed']}:{qid}:{r}:{h}").shuffle(roles)
            if all(store.get(key(r,h,role)) is not None for role in roles):
                continue
            admission=gate(store.directory,config,'profile',qid)
            for role in roles:
                k=key(r,h,role)
                if store.get(k) is not None:
                    continue
                c=baseline if role=='baseline' else candidates[h]
                fingerprint=c['plan_hash']
                context={'session':session,'stage':'profile','repetition':r,'pair_plan_hash':h,'pair_role':role,
                         'requested_plan_hash':fingerprint,**admission}
                if fingerprint in blocked:
                    store.perform(k,'profile',qid,lambda:{'status':'not_run_after_failure','failure_task':blocked[fingerprint]},context=context)
                else:
                    result=store.perform(k,'profile',qid,lambda:profile_once(conn,c,config),context=context)
                    if result['status'] in {'timeout','error','execution_plan_mismatch'}:
                        blocked[fingerprint]=k


def request(conn,statement,model,bqm,arm,run,config,expected,baseline_expected,blocked):
    mono=time.perf_counter_ns();wall=time.time_ns()
    def finish(result):
        client=(time.perf_counter_ns()-mono)/1e6;utc=(time.time_ns()-wall)/1e6
        result.update(end_to_end_ms=client,utc_elapsed_ms=utc,
            clock_anomaly=result.get('clock_anomaly',False) or clock_quality(None,client,utc,config['clock_tolerance_ms']))
        return result
    guarded=arm.endswith('_guarded');fallback=False;proposed=None;decision_ms=0.0
    if arm=='default' or guarded:
        base=preflight(conn,statement,'default',None,None,False,config)
        if base['status']!='ok' or base['plan_hash']!=baseline_expected['plan_hash']:
            return finish({'status':'baseline_changed_or_failed','baseline_preflight':base})
    if arm=='default':
        selected=base
    else:
        method=arm.rsplit('_',1)[0]
        try:
            proposed=proposal(conn,statement,model,bqm,method,run,config)
        except Exception as exc:
            proposed=failure(exc)
        decision_start=time.perf_counter_ns()
        fallback=guarded and (proposed['status']!='ok' or proposed['estimated_total_cost']>base['estimated_total_cost'])
        decision_ms=(time.perf_counter_ns()-decision_start)/1e6
        if proposed['status']=='ok' and (expected['status']!='ok' or proposed['plan_hash']!=expected['plan_hash'] or proposed.get('sample_bits_sha256')!=expected.get('sample_bits_sha256')):
            return finish({'status':'prospective_proposal_changed','proposal':proposed})
        if not guarded and proposed['status']!='ok':
            return finish({'status':'invalid_proposal','proposal_status':proposed['status'],'proposal':proposed})
        selected=base if fallback else proposed
    h=selected['plan_hash']
    if h in blocked:
        result={'status':'not_run_after_failure','failure_task':blocked[h]}
    else:
        try:
            result=plain_once(conn,selected,config)
        except (psycopg.Error,ValueError) as exc:
            result=failure(exc)
    client=(time.perf_counter_ns()-mono)/1e6;utc=(time.time_ns()-wall)/1e6
    result.update(end_to_end_ms=client,utc_elapsed_ms=utc,
        clock_anomaly=result.get('clock_anomaly',False) or clock_quality(None,client,utc,config['clock_tolerance_ms']),
        requested_plan_hash=h,guard_fallback=fallback,guard_decision_ms=decision_ms,proposal_status=proposed['status'] if proposed else None,
        proposal_plan_hash=proposed.get('plan_hash') if proposed else None,
        selected_estimated_cost=selected['estimated_total_cost'],load_after=list(os.getloadavg()),
        components={k:proposed[k] for k in ['sampling_ms','decode_and_audit_ms','preflight_ms'] if proposed and k in proposed},
        baseline_preflight_ms=base['preflight_ms'] if arm=='default' or guarded else None)
    return result


def run_policies(store,conn,qid,statement,model,bqm,baseline,proposals,config,session):
    def key(run,r,arm):
        return f'{qid}/policy/{run:03d}/{r:02d}/{arm}'
    if all(store.get(key(i,r,a)) is not None for i in config['policy_seed_indices'] for r in range(config['policy_repeats']) for a in config['policy_arms']):
        return
    candidates={baseline['plan_hash']:baseline}
    for method in config['candidate_methods']:
        for i in config['policy_seed_indices']:
            c=proposals[(method,i)]
            if c['status']=='ok':
                candidates.setdefault(c['plan_hash'],c)
    blocked=warm(store,conn,qid,candidates,config,session,'policy')
    blocks=[(i,r) for i in config['policy_seed_indices'] for r in range(config['policy_repeats'])]
    random.Random(f"{config['seed']}:{qid}:policyblocks").shuffle(blocks)
    for i,r in blocks:
        arms=list(config['policy_arms']);random.Random(f"{config['seed']}:{qid}:{i}:{r}:arms").shuffle(arms)
        for arm in arms:
            k=key(i,r,arm)
            if store.get(k) is not None:
                continue
            admission=gate(store.directory,config,'policy',qid)
            expected=proposals[(arm.rsplit('_',1)[0],i)] if arm!='default' else baseline
            result=store.perform(k,'policy',qid,
                lambda:request(conn,statement,model,bqm,arm,i,config,expected,baseline,blocked),
                context={'stage':'policy','session':session,'arm':arm,'run':i,'repetition':r,**admission})
            if result.get('requested_plan_hash') and result['status'] in {'timeout','error','execution_plan_mismatch'}:
                blocked[result['requested_plan_hash']]=k


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=ROOT/'config/submission-study-v1.json')
    parser.add_argument('--prepare-only',action='store_true',help='Record all optimizer proposals, then stop before timing; same output resumes the full schedule')
    args=parser.parse_args();config=json.loads(args.config.read_text())
    pilot=json.loads((ROOT/config['workload']).read_text())
    models=json.loads((ROOT/config['estimated_inputs']).read_text())
    binary=next(iter(sorted((ROOT/'.local/lib').glob('pg_hint_plan.*'))))
    files=['submission_study.py','study_hints.py','encoding_audit.py','job_runner.py','store.py','core.py','hints.py','cli.py','calibration.py']
    identity={'config':config,'input_sha256':{p:sha(ROOT/p) for p in [config['workload'],config['estimated_inputs'],config['source_pilot_evidence'],'data/load-receipt.json']},
        'source_sha256':{n:sha(ROOT/'src/qopt'/n) for n in files},'hint_binary_sha256':sha(binary),
        'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()},'upstream':upstream_identity()}
    for q in pilot['queries']:
        if sha(ROOT/q['sql_path'])!=q['sql_sha256']:
            raise ValueError('Frozen SQL changed')
    session=uuid.uuid4().hex[:12]
    dsn=os.environ.get('QOPT_JOB_DSN',f'host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=qopt_job')
    with keep_awake() as awake,RunStore(args.output,identity) as store,psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as conn:
        conn.execute(sql.SQL('LOAD {}').format(sql.Literal(str(binary))))
        for statement in ['SET search_path TO public','SET jit=off','SET max_parallel_workers_per_gather=0',
                          'SET default_transaction_read_only=on','SET pg_hint_plan.enable_hint=on']:
            conn.execute(statement)
        for n,v in [('statement_timeout',config['statement_timeout_ms']),('work_mem',config['work_mem']),
            ('geqo_effort',config['geqo_effort']),('geqo_pool_size',config['geqo_pool_size']),('geqo_generations',config['geqo_generations'])]:
            conn.execute('SELECT set_config(%s,%s,false)',(n,str(v)))
        stats=[r[0] for r in conn.execute("SELECT row_to_json(s)::text FROM pg_stats s WHERE schemaname='public' ORDER BY tablename,attname,inherited").fetchall()]
        if hashlib.sha256('\n'.join(stats).encode()).hexdigest()!=json.loads((ROOT/'data/load-receipt.json').read_text())['statistics_sha256']:
            raise ValueError('Statistics snapshot changed')
        with (args.output/'sessions.jsonl').open('a') as stream:
            stream.write(json.dumps({'session':session,'utc':stamp(),'awake_assertion_alive':awake.poll() is None})+'\n')
        for event in ['assertions','batt']:
            snapshot=subprocess.run(['/usr/bin/pmset','-g',event],capture_output=True,text=True,check=True)
            (args.output/f'power-{session}-{event}.txt').write_text(snapshot.stdout)
        write_json(args.output/'state.json',{'state':'running','phase':'preparation','session':session})
        for q in pilot['queries']:
            qid=q['query_id'];statement=(ROOT/q['sql_path']).read_text();model=models[qid]
            def encode():
                from qdbo.join_ordering.backend.bqm_solver_execution import build_bqm
                from qdbo.join_ordering.backend.jo_utils import parse_selectivities
                pred,sel=parse_selectivities(model['factors']);bqm=build_bqm(model['cards'],pred,sel)
                assert list(bqm.variables)==list(range(len(bqm.variables)))
                return {'bqm':bqm.to_serializable(use_bytes=False),'variables':len(bqm.variables)}
            encoding=store.perform(qid+'/encoding','encoding',qid,encode)
            if encoding['status']!='ok':
                raise RuntimeError(f'{qid}: encoding failed; records preserved')
            bqm=dimod.BinaryQuadraticModel.from_serializable(encoding['bqm'])
            base=store.perform(qid+'/baseline','baseline',qid,lambda:preflight(conn,statement,'default',None,None,False,config))
            if base['status']!='ok':
                raise RuntimeError(f'{qid}: baseline preflight failed')
            control=store.perform(qid+'/control','control',qid,lambda:controls(conn,q,base,config))
            if control['status']!='ok':
                raise RuntimeError(f'{qid}: hint controls failed')
            for i in range(config['solve_repeats']):
                sample=store.perform(f'{qid}/sample/{i:03d}','sample',qid,lambda:draw_sa(model,bqm,i,config))
                if sample['status']!='ok':
                    raise RuntimeError(f'{qid}: sample failed')
                for method in config['candidate_methods']:
                    store.perform(f'{qid}/proposal/{method}/{i:03d}','proposal',qid,
                        lambda:proposal(conn,statement,model,bqm,method,i,config,sample),
                        context={'method':method,'run':i})
            print(f'{qid}: 30 samples and 90 proposals recorded',flush=True)
        if args.prepare_only:
            write_json(args.output/'state.json',{'state':'prepared','session':session})
            return
        for phase in ['profile','policy']:
            for q in pilot['queries']:
                if awake.poll() is not None:
                    raise RuntimeError('Awake assertion exited')
                qid=q['query_id'];base=store.get(qid+'/baseline');statement=(ROOT/q['sql_path']).read_text()
                proposals={(m,i):store.get(f'{qid}/proposal/{m}/{i:03d}') for m in config['candidate_methods'] for i in range(config['solve_repeats'])}
                if phase=='profile':
                    candidates={base['plan_hash']:base}
                    for c in proposals.values():
                        if c['status']=='ok':
                            candidates.setdefault(c['plan_hash'],c)
                    print(f'{qid}: paired profiles for {len(candidates)} physical plans',flush=True)
                    run_profiles(store,conn,qid,candidates,base,config,session)
                else:
                    bqm=dimod.BinaryQuadraticModel.from_serializable(store.get(qid+'/encoding')['bqm'])
                    print(f'{qid}: actual policy requests started',flush=True)
                    run_policies(store,conn,qid,statement,models[qid],bqm,base,proposals,config,session)
                print(f'{qid}: {phase} schedule recorded',flush=True)
        write_json(args.output/'state.json',{'state':'complete','session':session})


if __name__=='__main__':
    main()
