"""Export compact, reviewable evidence without local paths, DSNs, or full settings."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3


def write_csv(path, records, columns):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({key:record.get(key) for key in columns})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    assert json.loads((args.run/'state.json').read_text())['state']=='complete'
    args.output.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(f'file:{args.run/"run.sqlite3"}?mode=ro',uri=True) as db:
        identity=json.loads(db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0])
        records=[(q,p,json.loads(v)) for q,p,v in db.execute("SELECT query_id,phase,payload FROM tasks WHERE state='finished' ORDER BY key")]
    trials,executions,baselines,models,plans,samples,rejected=[],[],{},{},{},[],[]
    for qid,phase,value in records:
        if phase=='solve':
            row={'query_id':qid,**value,'optimizer_task_wall_ms':value['task_wall_seconds']*1000}
            for source,target,factor in [('solve_seconds','sa_sampling_ms',1000),('decode_seconds','decode_ms',1000),
                ('validation_seconds','validation_ms',1000),('guard_decision_seconds','guard_comparison_us',1e6)]:
                if source in value:
                    row[target]=value[source]*factor
            row['guard_fallback']=value.get('guard_fallback',True)
            trials.append(row)
            if value['status']!='ok':
                rejected.append({'query_id':qid,**value})
            if 'bits' in value:
                samples.append({'query_id':qid,**{key:value[key] for key in (
                    'run','seed','bits','energy','order','aliases','model_cost',
                    'raw_membership_valid','decoder_selected_connected')}})
        if phase in {'warmup','execution'}:
            executions.append({'query_id':qid,'phase':phase,**value})
        if phase=='baseline':
            baselines[qid]={'plan_hash':value.get('plan_hash'),'status':value['status'],
                'estimated_total_cost':value.get('estimated_total_cost')}
        if phase=='model' and value['status']=='ok':
            models[qid]={key:value[key] for key in ('cards','factors','alias_mapping','kind','warning')}
        if phase in {'baseline','solve'} and value['status']=='ok':
            plans.setdefault(qid,{})[value['plan_hash']]={'plan':value['explain']['Plan'],
                'recipe':value['recipe'],'estimated_total_cost':value['estimated_total_cost']}
    write_csv(args.output/'trials.csv',trials,['query_id','solver','run','seed','status','plan_hash',
        'raw_membership_valid','decoder_selected_connected','energy','model_cost','estimated_total_cost',
        'guard_fallback','optimizer_task_wall_ms','sa_sampling_ms','decode_ms','validation_ms','guard_comparison_us'])
    write_csv(args.output/'executions.csv',executions,['query_id','phase','requested_plan_hash','repetition',
        'session','status','execution_ms','planning_ms','client_wall_ms','plan_hash','sqlstate','finished_utc'])
    (args.output/'baselines.json').write_text(json.dumps(baselines,indent=2)+'\n')
    (args.output/'estimated-inputs.json').write_text(json.dumps(models,indent=2)+'\n')
    # mtime=0 makes repeated exports identical byte-for-byte.
    with (args.output/'plans.json.gz').open('wb') as stream:
        stream.write(gzip.compress(json.dumps(plans,sort_keys=True).encode(),mtime=0))
    (args.output/'sa-samples.json.gz').write_bytes(gzip.compress(json.dumps(samples,sort_keys=True).encode(),mtime=0))
    (args.output/'rejected-plans.json.gz').write_bytes(gzip.compress(json.dumps(rejected,sort_keys=True).encode(),mtime=0))
    with (args.output/'timed-plans.jsonl.gz').open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as stream:
            for qid,phase,value in records:
                if phase in {'warmup','execution'}:
                    stream.write((json.dumps({'query_id':qid,'phase':phase,**value},sort_keys=True)+'\n').encode())
    evidence={'identity':identity,'raw_record_counts':{'optimizer_trials':len(trials),
        'execution_and_warmup_rows':len(executions)},
        'frozen_code_commit':(args.run/'frozen-code-commit.txt').read_text().strip(),
        'machine':json.loads((args.run/'machine.json').read_text()),
        'integrity_audit':json.loads((args.run/'integrity-audit.json').read_text()),
        'note':'CSV rows, raw SA samples, preflight plans, and timed EXPLAIN evidence are exported. Full SQLite event ledger and session-wide server settings remain local.'}
    evidence['file_sha256']={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
        for path in args.output.iterdir() if path.name in {'trials.csv','executions.csv','baselines.json','estimated-inputs.json','plans.json.gz','sa-samples.json.gz','rejected-plans.json.gz','timed-plans.jsonl.gz'}}
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(f'Exported {len(trials)} optimizer trials and {len(executions)} timing/warmup records')


if __name__=='__main__':
    main()
