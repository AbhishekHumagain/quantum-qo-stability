"""Check a finished pilot's identities, complete task accounting, and plan evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from qopt.core import plan_hash
from qopt.hints import verify_tree
from qopt.job_runner import as_tuple


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    args=parser.parse_args()
    with sqlite3.connect(f'file:{args.run/"run.sqlite3"}?mode=ro',uri=True) as db:
        identity=json.loads(db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0])
        rows=[{'key':k,'phase':p,'qid':q,'state':s,'attempt':a,'raw':v,'value':json.loads(v) if v else None}
              for k,p,q,s,a,v in db.execute('SELECT key,phase,query_id,state,attempt,payload FROM tasks ORDER BY key')]
    assert json.loads((args.run/'state.json').read_text())['state']=='complete'
    assert all(row['state']=='finished' or (row['state']=='abandoned' and row['phase']=='warmup'
               and row['value']['status']=='interrupted') for row in rows), 'Unfinished task records'
    abandoned_warmups=sum(row['state']=='abandoned' for row in rows)
    rows=[row for row in rows if row['state']=='finished']
    root=Path(__file__).resolve().parents[1]
    pilot_path=root/identity['config']['workload']
    assert hashlib.sha256(pilot_path.read_bytes()).hexdigest()==identity['pilot_sha256']
    pilot=json.loads(pilot_path.read_text())
    expected_trials=identity['config']['solve_repeats']
    repetitions=identity['config']['execution_repeats']
    by_key={row['key']:row for row in rows}
    timeout_evidence=Counter()
    for row in rows:
        if row['phase'] in {'warmup','execution'} and row['value']['status']=='timeout':
            assert 'execution_ms' not in row['value']
            timeout_evidence[(row['qid'],row['value']['requested_plan_hash'])]+=1
    verified=0
    for query in pilot['queries']:
        qid=query['query_id']
        baseline=by_key[qid+'/baseline']['value']
        assert baseline['status']=='ok'
        candidates={baseline['plan_hash']:baseline}
        for solver in ('sa','geqo'):
            trials=[by_key[f'{qid}/solve/{solver}/{i:03d}']['value'] for i in range(expected_trials)]
            assert len(trials)==expected_trials
            for trial in trials:
                assert trial['solver']==solver
                if trial['status']=='ok':
                    candidates.setdefault(trial['plan_hash'],trial)
                    assert plan_hash(trial['explain']['Plan'])==trial['plan_hash']
        for fingerprint,candidate in candidates.items():
            for repetition in range(repetitions):
                value=by_key[f'{qid}/execution/{repetition:02d}/{fingerprint}']['value']
                assert value['requested_plan_hash']==fingerprint
                if value['status']=='ok':
                    assert plan_hash(value['explain']['Plan'])==fingerprint==value['plan_hash']
                    tree=candidate['recipe']['expected_tree']
                    if tree is not None:
                        verify_tree(value['explain']['Plan'],as_tuple(tree))
                    assert value['execution_ms']==value['explain']['Execution Time']
                    verified+=1
                elif value['status']=='not_run_after_timeout':
                    assert timeout_evidence[(qid,fingerprint)]>0
                    assert 'execution_ms' not in value
    checkpoint=json.loads((args.run/'checkpoint-verification-before.json').read_text())
    for key,fingerprint in checkpoint.items():
        assert hashlib.sha256(by_key[key]['raw'].encode()).hexdigest()==fingerprint
        assert by_key[key]['attempt']==1
    summary={'complete':True,'optimizer_trials':len(pilot['queries'])*expected_trials*2,
        'verified_measured_executions':verified,'timeout_attempts':sum(timeout_evidence.values()),
        'abandoned_warmup_attempts':abandoned_warmups,
        'initial_checkpoint_records_unchanged':len(checkpoint),'plan_evidence_verified':True}
    (args.run/'integrity-audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
