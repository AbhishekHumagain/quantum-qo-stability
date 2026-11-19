"""Audit a complete baseline calibration and export its measurement evidence."""
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics

from qopt.cli import ROOT
from qopt.core import plan_hash


def summary(rows,identity):
    config=identity['config']
    queries=json.loads((ROOT/config['workload']).read_text())['queries']
    output=[]
    for q in queries:
        qid=q['query_id']
        modes={}
        for m in config['modes']:
            items=[r for r in rows if r['query_id']==qid and r['phase']=='execution' and r['measurement_mode']==m]
            valid=[r for r in items if r['status']=='ok' and not r['clock_anomaly']]
            complete=len(valid)==len(items)==config['execution_repeats']
            def stats(field):
                values=[r[field] for r in valid]
                return {'median_ms':statistics.median(values) if complete else None,
                        'cv':statistics.stdev(values)/statistics.mean(values) if complete and len(values)>1 and statistics.mean(values)>0 else None}
            modes[m]={'recorded_slots':len(items),'statuses':dict(Counter(r['status'] for r in items)),
                'clock_anomalies':sum(r.get('clock_anomaly',False) for r in items),
                'complete_valid_repeats':len(valid),'client':stats('client_wall_ms'),
                'server':stats('execution_ms') if m!='plain' else None}
        on=modes['timing_on']['server']['median_ms']
        off=modes['timing_off']['server']['median_ms']
        output.append({'query_id':qid,'modes':modes,
            'profile_on_off_server_median_ratio':on/off if on is not None and off else None})
    return {'kind':'Baseline measurement calibration; no new solver or safeguard effectiveness result',
        'config':config,'planned_measured_slots':len(queries)*len(config['modes'])*config['execution_repeats'],
        'recorded_measured_slots':sum(r['phase']=='execution' for r in rows),
        'measurement_statuses':dict(Counter(r['status'] for r in rows if r['phase']=='execution')),
        'warmup_statuses':dict(Counter(r['status'] for r in rows if r['phase']=='warmup')),
        'clock_anomalies_all_attempts':sum(r.get('clock_anomaly',False) for r in rows),
        'queries':output,
        'limits':['Ten repeats per mode, one machine, fixed query order, interleaved mode order; descriptive calibration only.',
            'Profile server executor time and plain SELECT client latency have different scopes; no subtraction is valid.',
            'Plain SELECT has pre/post EXPLAIN checks, not a directly observed timed physical plan.',
            'Keeping the machine awake does not eliminate load, cache, thermal, or power-state variation.',
            'No rerun of optimizer candidates, hint ablation, or actual end-to-end safeguard evaluation yet.']}


def verify_export(directory):
    evidence=json.loads((directory/'evidence.json').read_text())
    for name,digest in evidence['file_sha256'].items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
    with gzip.open(directory/'observations.jsonl.gz','rt') as stream:
        rows=[json.loads(line) for line in stream]
    expected=json.loads((directory/'summary.json').read_text())
    assert summary(rows,evidence['identity'])==expected
    for row in rows:
        if 'client_wall_ms' in row:
            tolerance=evidence['identity']['config']['clock_tolerance_ms']
            anomaly=abs(row['utc_elapsed_ms']-row['client_wall_ms'])>tolerance or (row.get('execution_ms') is not None and row['execution_ms']>row['client_wall_ms']+tolerance)
            assert row['clock_anomaly']==anomaly
        if row['status']=='ok' and row['measurement_mode']=='plain':
            assert row['pre_plan_hash']==row['post_plan_hash']==row['expected_plan_hash']
        if row['status']=='ok' and row['measurement_mode']!='plain':
            assert plan_hash(row['explain']['Plan'])==row['plan_hash']==row['expected_plan_hash']
    print('Calibration export hashes, summaries, and profile fingerprints verified')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify-export',type=Path)
    args=parser.parse_args()
    if args.verify_export:
        verify_export(args.verify_export)
        return
    assert args.run and args.output
    assert json.loads((args.run/'state.json').read_text())['state']=='complete'
    with sqlite3.connect(f'file:{args.run/"run.sqlite3"}?mode=ro',uri=True) as db:
        identity=json.loads(db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0])
        records=[(k,p,q,s,json.loads(v)) for k,p,q,s,v in db.execute('SELECT key,phase,query_id,state,payload FROM tasks ORDER BY key')]
    assert all(s=='finished' or (s=='abandoned' and p=='warmup') for k,p,q,s,v in records)
    queries=json.loads((ROOT/identity['config']['workload']).read_text())['queries']
    bykey={k:v for k,p,q,s,v in records if s=='finished'}
    for q in queries:
        qid=q['query_id']
        for r in range(identity['config']['execution_repeats']):
            for m in identity['config']['modes']:
                value=bykey[f'{qid}/execution/{r:02d}/{m}']
                if value['status']=='not_run_after_failure':
                    assert any(p in {'warmup','execution'} and q2==qid and s=='finished'
                        and v.get('measurement_mode')==m and v['status'] not in {'ok','not_run_after_failure'}
                        for k,p,q2,s,v in records)
        plain=[v for k,p,q2,s,v in records if p=='execution' and q2==qid and s=='finished' and v['status']=='ok' and v['measurement_mode']=='plain']
        assert len({v['result_sha256'] for v in plain})<=1,'Plain SELECT results changed'
        assert all(v['pre_plan_hash']==v['post_plan_hash']==v['expected_plan_hash'] for v in plain)
    columns=['task_key','measurement_mode','session','repetition','status','expected_plan_hash','execution_ms',
        'planning_ms','client_wall_ms','utc_elapsed_ms','clock_anomaly','load_average','result_rows','result_sha256',
        'pre_plan_hash','post_plan_hash','plan_hash','plan_observation','sqlstate','error_type','finished_utc','attempt','task_wall_seconds','explain']
    rows=[{'query_id':q,'phase':p,**{n:v[n] for n in columns if n in v}}
        for k,p,q,s,v in records if p in {'warmup','execution'} and s=='finished']
    report=summary(rows,identity)
    assert report['planned_measured_slots']==report['recorded_measured_slots']
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    raw=''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows).encode()
    (args.output/'observations.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    fields=['query_id','phase']+[n for n in columns if n!='explain']
    with (args.output/'observations.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)
    lines=['# Baseline measurement calibration v1','','Completed descriptive calibration, separate from pilot 001.',
        'ON/OFF values are server executor times; plain SELECT values are client times including planning and transfer.',
        'A missing median means ten valid repetitions were unavailable. No timeout cap is substituted.',
        f"Measured outcomes: {report['measurement_statuses']}. Warmups: {report['warmup_statuses']}. Detected clock anomalies: {report['clock_anomalies_all_attempts']}.",'',
        '| Query | ON median ms | OFF median ms | ON/OFF | Plain client ms | Plain CV |','|---|---:|---:|---:|---:|---:|']
    def fmt(v):
        return 'unknown' if v is None else f'{v:.3f}'
    for q in report['queries']:
        m=q['modes'];lines.append(f"| {q['query_id']} | {fmt(m['timing_on']['server']['median_ms'])} | {fmt(m['timing_off']['server']['median_ms'])} | {fmt(q['profile_on_off_server_median_ratio'])} | {fmt(m['plain']['client']['median_ms'])} | {fmt(m['plain']['client']['cv'])} |")
    lines+=['','## Limits','']+['- '+s for s in report['limits']]
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')
    evidence={'identity':identity,'measurement_source_commit':(args.run/'frozen-code-commit.txt').read_text().strip(),'profile_evidence_verified':True,'plain_result_consistency_verified':True,
        'completed_resume_verification':json.loads((args.run/'completed-resume-verification.json').read_text()),
        'file_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output.iterdir() if p.name in {'summary.json','observations.jsonl.gz','observations.csv','README.md'}}}
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    verify_export(args.output)


if __name__=='__main__':
    main()
