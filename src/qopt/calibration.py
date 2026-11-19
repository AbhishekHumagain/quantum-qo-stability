"""Frozen baseline calibration: profiling ON/OFF and ordinary SELECT latency."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import subprocess
import time
import uuid

import psycopg
from psycopg import sql

from qopt.cli import ROOT,write_json
from qopt.core import plan_hash
from qopt.job_runner import mode
from qopt.store import RunStore,failure


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clock_quality(server_ms,client_ms,wall_ms,tolerance):
    return abs(wall_ms-client_ms)>tolerance or (server_ms is not None and server_ms>client_ms+tolerance)


def measure(conn,statement,measurement_mode,expected_hash,tolerance):
    # Plain-query checks bracket, but do not enter, its timed client interval.
    if measurement_mode=='plain':
        before=conn.execute('EXPLAIN (FORMAT JSON) '+statement).fetchone()[0][0]
        if plan_hash(before['Plan'])!=expected_hash:
            return {'status':'plan_mismatch_before_plain'}
    wall_started=time.time_ns()
    mono_started=time.perf_counter_ns()
    try:
        if measurement_mode=='plain':
            rows=conn.execute(statement).fetchall()
            result={'status':'ok','result_rows':len(rows),
                'result_sha256':hashlib.sha256(json.dumps(rows,default=str).encode()).hexdigest(),
                'plan_observation':'Pre/post EXPLAIN only; timed SELECT plan not directly observed'}
        else:
            timing='ON' if measurement_mode=='timing_on' else 'OFF'
            observed=conn.execute(f'EXPLAIN (ANALYZE, BUFFERS, TIMING {timing}, FORMAT JSON) '+statement).fetchone()[0][0]
            result={'status':'ok','explain':observed,'execution_ms':observed['Execution Time'],
                'planning_ms':observed['Planning Time'],'plan_hash':plan_hash(observed['Plan'])}
            if result['plan_hash']!=expected_hash:
                result['status']='execution_plan_mismatch'
    except psycopg.Error as exc:
        result=failure(exc)
    client_ms=(time.perf_counter_ns()-mono_started)/1e6
    wall_ms=(time.time_ns()-wall_started)/1e6
    result.update(client_wall_ms=client_ms,utc_elapsed_ms=wall_ms,
        clock_anomaly=clock_quality(result.get('execution_ms'),client_ms,wall_ms,tolerance),
        load_average=list(os.getloadavg()))
    if measurement_mode=='plain' and result['status']=='ok':
        after=conn.execute('EXPLAIN (FORMAT JSON) '+statement).fetchone()[0][0]
        result['pre_plan_hash']=expected_hash
        result['post_plan_hash']=plan_hash(after['Plan'])
        if result['post_plan_hash']!=expected_hash:
            result['status']='plan_mismatch_after_plain'
    return result


def schedule(store,conn,qid,statement,fingerprint,config,session):
    modes=config['modes']
    repeats=config['execution_repeats']
    def key(rep,measurement_mode):
        return f'{qid}/execution/{rep:02d}/{measurement_mode}'
    if all(store.get(key(r,m)) is not None for r in range(repeats) for m in modes):
        return
    failed={r['payload']['measurement_mode'] for r in store.records(query_id=qid)
        if r['state']=='finished' and r['phase'] in {'warmup','execution'}
        and r['payload']['status'] not in {'ok','not_run_after_failure'}}
    def perform(task_key,phase,m,rep=None):
        return store.perform(task_key,phase,qid,
            lambda:measure(conn,statement,m,fingerprint,config['clock_tolerance_ms']),
            context={'measurement_mode':m,'session':session,'repetition':rep,'expected_plan_hash':fingerprint})
    warm_modes=list(modes)
    random.Random(f"{config['seed']}:{qid}:warmup").shuffle(warm_modes)
    for m in warm_modes:
        if m not in failed:
            result=perform(f'{qid}/warmup/{session}/{m}','warmup',m)
            if result['status']!='ok':
                failed.add(m)
    for r in range(repeats):
        ordered=list(modes)
        random.Random(f"{config['seed']}:{qid}:{r}").shuffle(ordered)
        for m in ordered:
            if store.get(key(r,m)) is not None:
                continue
            if m in failed:
                store.perform(key(r,m),'execution',qid,lambda:{'status':'not_run_after_failure'},
                    context={'measurement_mode':m,'session':session,'repetition':r,'expected_plan_hash':fingerprint})
            elif perform(key(r,m),'execution',m,r)['status']!='ok':
                failed.add(m)


@contextmanager
def keep_awake():
    process=subprocess.Popen(['/usr/bin/caffeinate','-i','-s','-w',str(os.getpid())])
    try:
        if process.poll() is not None:
            raise RuntimeError('Sleep inhibition did not start')
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--config',type=Path,default=ROOT/'config/measurement-calibration-v1.json')
    args=parser.parse_args()
    config=json.loads(args.config.read_text())
    evidence=json.loads((ROOT/config['pilot_evidence']).read_text())
    pilot_config=evidence['identity']['config']
    workload=ROOT/config['workload']
    pilot=json.loads(workload.read_text())
    baselines=json.loads((ROOT/'docs/pilot-001/baselines.json').read_text())
    hint_binary=next(iter(sorted((ROOT/'.local/lib').glob('pg_hint_plan.*'))))
    identity={'config':config,'pilot_evidence_sha256':sha(ROOT/config['pilot_evidence']),
        'baseline_sha256':sha(ROOT/'docs/pilot-001/baselines.json'),
        'workload_sha256':sha(workload),'load_receipt_sha256':sha(ROOT/'data/load-receipt.json'),
        'hint_binary_sha256':sha(hint_binary),
        'source_sha256':{n:sha(ROOT/'src/qopt'/n) for n in ['calibration.py','job_runner.py','store.py','core.py','hints.py','cli.py']},
        'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
    for q in pilot['queries']:
        if sha(ROOT/q['sql_path'])!=q['sql_sha256']:
            raise ValueError('Frozen SQL changed')
    session=uuid.uuid4().hex[:12]
    dsn=os.environ.get('QOPT_JOB_DSN',f'host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=qopt_job')
    with keep_awake() as awake, RunStore(args.output,identity) as store, psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as conn:
        conn.execute(sql.SQL('LOAD {}').format(sql.Literal(str(hint_binary))))
        for statement in ['SET search_path TO public','SET max_parallel_workers_per_gather=0','SET jit=off',
                          'SET default_transaction_read_only=on','SET pg_hint_plan.enable_hint=on']:
            conn.execute(statement)
        for name,value in [('statement_timeout',config['statement_timeout_ms']),('work_mem',pilot_config['work_mem']),
                           ('geqo_effort',pilot_config['geqo_effort']),('geqo_pool_size',pilot_config['geqo_pool_size']),
                           ('geqo_generations',pilot_config['geqo_generations'])]:
            conn.execute('SELECT set_config(%s,%s,false)',(name,str(value)))
        stats=[r[0] for r in conn.execute("SELECT row_to_json(s)::text FROM pg_stats s WHERE schemaname='public' ORDER BY tablename,attname,inherited").fetchall()]
        receipt=json.loads((ROOT/'data/load-receipt.json').read_text())
        if hashlib.sha256('\n'.join(stats).encode()).hexdigest()!=receipt['statistics_sha256']:
            raise ValueError('Database statistics changed')
        # Keep power diagnostics local: these may contain host/user process details.
        for event in ['assertions','batt']:
            snapshot=subprocess.run(['/usr/bin/pmset','-g',event],capture_output=True,text=True,check=True)
            (args.output/f'power-{session}-{event}.txt').write_text(snapshot.stdout)
        write_json(args.output/'state.json',{'state':'running','session':session})
        with (args.output/'sessions.jsonl').open('a') as stream:
            stream.write(json.dumps({'session':session,'utc_ns':time.time_ns(),'caffeinate_active':awake.poll() is None,
                'load_average':list(os.getloadavg())})+'\n')
        for q in pilot['queries']:
            qid=q['query_id']
            mode(conn,pilot_config,'default')
            statement=(ROOT/q['sql_path']).read_text()
            def preflight():
                observed=conn.execute('EXPLAIN (FORMAT JSON) '+statement).fetchone()[0][0]
                return {'status':'ok' if plan_hash(observed['Plan'])==baselines[qid]['plan_hash'] else 'baseline_plan_changed',
                    'plan_hash':plan_hash(observed['Plan']),'explain':observed}
            result=store.perform(qid+'/preflight','preflight',qid,preflight)
            if result['status']!='ok':
                raise RuntimeError(f'{qid}: baseline preflight failed; records preserved')
            if awake.poll() is not None:
                raise RuntimeError('Sleep inhibition exited; records preserved')
            print(f'{qid}: calibration started',flush=True)
            schedule(store,conn,qid,statement,result['plan_hash'],config,session)
            print(f'{qid}: calibration schedule recorded',flush=True)
        write_json(args.output/'state.json',{'state':'complete','session':session})


if __name__=='__main__':
    main()
