"""Validate selected JOB queries with EXPLAIN only; no query execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import psycopg
from qopt.cardinality import estimate_inputs

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--extract-models',action='store_true',help='Also EXPLAIN filtered bases and predicate-connected pairs; no execution')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((ROOT/'workloads/job/pilot.json').read_text())
    dsn=os.environ.get('QOPT_JOB_DSN',f'host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=qopt_job')
    rows=[]
    with psycopg.connect(dsn,autocommit=True,prepare_threshold=None) as conn:
        conn.execute("SET statement_timeout='60s'")
        conn.execute('SET max_parallel_workers_per_gather=0')
        conn.execute('SET jit=off')
        settings=dict(conn.execute('SELECT name,setting FROM pg_settings').fetchall())
        for query in manifest['queries']:
            path=ROOT/query['sql_path']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=query['sql_sha256']:
                raise ValueError(f"SQL changed: {path}")
            row={'query_id':query['query_id'],'template_id':query['template_id'],
                 'sql_sha256':query['sql_sha256'],'kind':'JOB_EXPLAIN_only_no_runtime'}
            started=time.perf_counter()
            try:
                row['explain']=conn.execute('EXPLAIN (FORMAT JSON) '+path.read_text()).fetchone()[0][0]
                if args.extract_models:
                    row['estimated_model']=estimate_inputs(conn,query)
                row['status']='ok'
            except psycopg.Error as exc:
                row.update(status='error',sqlstate=exc.sqlstate,message=str(exc))
            except ValueError as exc:
                row.update(status='model_error',message=str(exc))
            row['wall_seconds']=time.perf_counter()-started
            rows.append(row)
            with (args.output/'queries.jsonl').open('a') as stream:
                stream.write(json.dumps(row)+'\n')
    receipt=ROOT/'data/load-receipt.json'
    (args.output/'manifest.json').write_text(json.dumps({'pilot_sha256':hashlib.sha256((ROOT/'workloads/job/pilot.json').read_bytes()).hexdigest(),
        'load_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest() if receipt.exists() else None,
        'settings':settings,'execution':'EXPLAIN only'},indent=2)+'\n')
    print(f"Preflight: {sum(r['status']=='ok' for r in rows)}/{len(rows)} queries planned; none executed")
    if any(r['status']!='ok' for r in rows):
        raise SystemExit(1)


if __name__=='__main__':
    main()
