"""Recompute reported query-level risk accounting from the published CSV files."""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
from pathlib import Path
import statistics

from qopt.core import plan_hash
from qopt.hints import verify_tree


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    directory=args.directory
    evidence=json.loads((directory/'evidence.json').read_text())
    for name,expected in evidence['file_sha256'].items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==expected
    report=json.loads((directory/'summary.json').read_text())
    baselines=json.loads((directory/'baselines.json').read_text())
    trials=list(csv.DictReader((directory/'trials.csv').open()))
    executions=list(csv.DictReader((directory/'executions.csv').open()))
    plans=json.loads(gzip.decompress((directory/'plans.json.gz').read_bytes()))
    for by_hash in plans.values():
        for fingerprint,plan in by_hash.items():
            assert plan_hash(plan['plan'])==fingerprint
    def tuples(value):
        return tuple(tuples(x) for x in value) if isinstance(value,list) else value
    timed_count=0
    with gzip.open(directory/'timed-plans.jsonl.gz','rt') as stream:
        for line in stream:
            row=json.loads(line)
            timed_count+=1
            if row['status']=='ok':
                fingerprint=row['requested_plan_hash']
                assert plan_hash(row['explain']['Plan'])==fingerprint
                expected=plans[row['query_id']][fingerprint]['recipe']['expected_tree']
                if expected is not None:
                    verify_tree(row['explain']['Plan'],tuples(expected))
    assert timed_count==len(executions)
    grouped=defaultdict(list)
    for row in executions:
        if row['phase']=='execution':
            grouped[(row['query_id'],row['requested_plan_hash'])].append(row)
        if row['status']=='ok':
            assert row['plan_hash']==row['requested_plan_hash']
        elif row['status']=='timeout' or row['status'].startswith('not_run'):
            assert not row['execution_ms']
    medians={}
    n=report['config']['execution_repeats']
    for key,rows in grouped.items():
        if len(rows)==n and all(row['status']=='ok' for row in rows):
            medians[key]=statistics.median(float(row['execution_ms']) for row in rows)
    for query in report['queries']:
        qid=query['query_id']
        base=medians.get((qid,baselines[qid]['plan_hash']))
        assert base==query['baseline']['median_ms']
        for solver in ('sa','geqo'):
            rows=[row for row in trials if row['query_id']==qid and row['solver']==solver]
            expected=query['solvers'][solver]
            assert len(rows)==expected['planned_trials']
            ratios=[]
            guarded=[]
            for row in rows:
                value=medians.get((qid,row['plan_hash'])) if row['status']=='ok' else None
                ratio=value/base if value is not None and base else None
                ratios.append(ratio)
                guarded.append(1.0 if base and row['guard_fallback']=='True' else ratio)
            assert sum(value is not None for value in ratios)==expected['known_runtime_ratios']
            for label,values in [('risk',ratios),('offline_guard_risk',guarded)]:
                for item in expected[label]:
                    slow=sum(value is not None and value>item['threshold'] for value in values)
                    unknown=sum(value is None for value in values)
                    assert slow==item['confirmed_slow_trials'] and unknown==item['unknown_trials']
    assert len(trials)==report['recorded_optimizer_trials']
    print(f'CSV evidence verified: {len(trials)} trials; all plan fingerprints, query medians, and risk counts agree')


if __name__=='__main__':
    main()
