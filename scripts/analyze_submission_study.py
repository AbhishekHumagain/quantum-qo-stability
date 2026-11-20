"""Audit/export the complete prospective study, or inspect preparation only."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3

from qopt.cli import ROOT,write_json
from qopt.core import plan_hash
from qopt.encoding_audit import components
from qopt.study_analysis import summarize
from qopt.study_hints import verify_order


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(records,identity,complete):
    config=identity['config'];bykey={r['key']:r['payload'] for r in records if r['state']=='finished'}
    pilot=json.loads((ROOT/config['workload']).read_text());models=json.loads((ROOT/config['estimated_inputs']).read_text())
    for path in [config['workload'],config['estimated_inputs'],config['source_pilot_evidence']]:
        assert sha(ROOT/path)==identity['input_sha256'][path], 'Frozen public inputs changed'
    def parse_selectivities(factors):
        pred=[(i,j) for i in range(len(factors)) for j in range(i+1,len(factors)) if factors[i][j]!=1]
        return pred,[factors[i][j] for i,j in pred]
    original_path=ROOT/'docs/pilot-001/sa-samples.json.gz'
    previous_evidence=json.loads((ROOT/config['source_pilot_evidence']).read_text())
    assert sha(original_path)==previous_evidence['file_sha256']['sa-samples.json.gz']
    original=json.loads(gzip.decompress(original_path.read_bytes()))
    original_lookup={(r['query_id'],r['seed']):hashlib.sha256(bytes(r['bits'])).hexdigest() for r in original}
    shared=0
    for q in pilot['queries']:
        qid=q['query_id'];base=bykey[qid+'/baseline'];assert base['status']=='ok'
        assert bykey[qid+'/control']['status']=='ok'
        for i in range(config['solve_repeats']):
            sample=bykey[f'{qid}/sample/{i:03d}'];model=models[qid];pred,sel=parse_selectivities(model['factors'])
            a=components(sample['bits'],model['cards'],pred,sel)
            assert a==sample['encoding_audit']
            assert hashlib.sha256(bytes(sample['bits'])).hexdigest()==sample['bits_sha256']
            if (qid,sample['seed']) in original_lookup:
                shared+=1
                assert sample['bits_sha256']==original_lookup[(qid,sample['seed'])]
            assert abs(a['reconstructed_energy']-sample['energy'])<1e-4
            for method in config['candidate_methods']:
                value=bykey[f'{qid}/proposal/{method}/{i:03d}']
                if method.startswith('sa_'):
                    assert value.get('sample_bits_sha256')==sample['bits_sha256']
                if value['status']=='ok':
                    assert plan_hash(value['explain']['Plan'])==value['plan_hash']
                    recipe=value['recipe']
                    if recipe['aliases'] is not None:
                        verify_order(value['explain']['Plan'],recipe['aliases'],recipe['directed'])
        if complete:
            plans={base['plan_hash']:base}
            for method in config['candidate_methods']:
                for i in range(config['solve_repeats']):
                    c=bykey[f'{qid}/proposal/{method}/{i:03d}']
                    if c['status']=='ok':
                        plans.setdefault(c['plan_hash'],c)
            for record in records:
                if record['query_id']==qid and record['phase']=='warmup' and record['state']=='finished' and record['payload']['status']=='ok':
                    row=record['payload'];h=row['requested_plan_hash']
                    if row['stage']=='profile':
                        assert plan_hash(row['explain']['Plan'])==row['plan_hash']==h
                        recipe=plans[h]['recipe']
                        if recipe['aliases'] is not None:
                            verify_order(row['explain']['Plan'],recipe['aliases'],recipe['directed'])
                    else:
                        assert row['pre_plan_hash']==row['post_plan_hash']==h
            for h in plans:
                for r in range(config['execution_repeats']):
                    for role in ['baseline','candidate']:
                        value=bykey[f'{qid}/profile/{r:02d}/{h}/{role}']
                        if value['status']=='ok':
                            expected=base if role=='baseline' else plans[h]
                            assert value['requested_plan_hash']==value['plan_hash']==plan_hash(value['explain']['Plan'])==expected['plan_hash']
                            recipe=expected['recipe']
                            if recipe['aliases'] is not None:
                                verify_order(value['explain']['Plan'],recipe['aliases'],recipe['directed'])
            for i in config['policy_seed_indices']:
                for r in range(config['policy_repeats']):
                    for arm in config['policy_arms']:
                        value=bykey[f'{qid}/policy/{i:03d}/{r:02d}/{arm}']
                        if value['status']=='ok':
                            assert value['pre_plan_hash']==value['post_plan_hash']==value['requested_plan_hash']
                            assert value['end_to_end_ms']>=value['execute_client_ms']
            digests={r['payload']['result_sha256'] for r in records if r['state']=='finished' and r['query_id']==qid
                and r['phase']=='policy' and r['payload']['status']=='ok'}
            assert len(digests)<=1,'Policy result changed across join orders'
    for record in records:
        if record['state']!='finished':
            assert not complete or (record['state']=='abandoned' and record['phase']=='warmup')
            continue
        row=record['payload']
        tolerance=config['clock_tolerance_ms']
        if 'client_wall_ms' in row:
            expected_anomaly=abs(row['utc_elapsed_ms']-row['client_wall_ms'])>tolerance or (row.get('execution_ms') is not None and row['execution_ms']>row['client_wall_ms']+tolerance)
            assert row['clock_anomaly']==expected_anomaly
        elif 'end_to_end_ms' in row:
            expected_anomaly=abs(row['utc_elapsed_ms']-row['end_to_end_ms'])>tolerance
            if 'execute_client_ms' in row:
                expected_anomaly=expected_anomaly or abs(row['execute_utc_ms']-row['execute_client_ms'])>tolerance
            assert row['clock_anomaly']==expected_anomaly
        elif 'execute_client_ms' in row:
            assert row['clock_anomaly']==(abs(row['execute_utc_ms']-row['execute_client_ms'])>tolerance)
        if record['phase']=='policy' and row.get('proposal_status')=='ok':
            arm=row['arm'];expected_proposal=bykey[f"{record['query_id']}/proposal/{arm.rsplit('_',1)[0]}/{row['run']:03d}"]
            assert row['proposal_plan_hash']==expected_proposal['plan_hash']
            if arm.endswith('_guarded'):
                expected_base=bykey[record['query_id']+'/baseline']
                assert row['guard_fallback']==(expected_proposal['estimated_total_cost']>expected_base['estimated_total_cost'])
                assert row['requested_plan_hash']==(expected_base if row['guard_fallback'] else expected_proposal)['plan_hash']
        if row['status']=='not_run_after_failure':
            failure=bykey[row['failure_task']]
            assert failure['status'] in {'timeout','error','execution_plan_mismatch'}
            assert failure.get('requested_plan_hash')==row.get('requested_plan_hash')
        if row['status']=='timeout' or row['status']=='not_run_after_failure':
            assert 'execution_ms' not in row
    return {'preparation_verified':True,'complete_schedule_verified':complete,'result_consistency_verified':complete,
        'reused_seed_samples_bit_identical':shared}


def clean(value):
    if isinstance(value,dict):
        return {k:clean(v) for k,v in value.items() if k not in {'message'}}
    if isinstance(value,list):
        return [clean(v) for v in value]
    return value


def verify_export(directory):
    evidence=json.loads((directory/'evidence.json').read_text())
    for name,digest in evidence['file_sha256'].items():
        assert sha(directory/name)==digest
    with gzip.open(directory/'records.jsonl.gz','rt') as stream:
        records=[json.loads(line) for line in stream]
    audit(records,evidence['identity'],True)
    assert summarize(records,evidence['identity'])==json.loads((directory/'summary.json').read_text())
    print('Prospective evidence hashes, plan trees, sample constraints, policy results, and recomputed summary verified')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--verify-export',type=Path)
    args=parser.parse_args()
    if args.verify_export:
        verify_export(args.verify_export);return
    assert args.run and args.output
    with sqlite3.connect(f'file:{args.run/"run.sqlite3"}?mode=ro',uri=True) as db:
        identity=json.loads(db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0])
        records=[{'key':k,'phase':p,'query_id':q,'state':s,'attempt':a,'payload':json.loads(v) if v else None}
            for k,p,q,s,a,v in db.execute('SELECT key,phase,query_id,state,attempt,payload FROM tasks ORDER BY key')]
    if args.prepare_only:
        records=[r for r in records if r['phase'] in {'baseline','control','encoding','proposal','sample'}]
        assert all(r['state']=='finished' for r in records)
    else:
        assert json.loads((args.run/'state.json').read_text())['state']=='complete'
    integrity=audit(records,identity,not args.prepare_only)
    checkpoint=args.run/'preparation-checkpoint.json'
    if checkpoint.exists():
        bykey={r['key']:r for r in records if r['state']=='finished'}
        saved=json.loads(checkpoint.read_text())
        for key,digest in saved.items():
            assert bykey[key]['attempt']==1
            assert hashlib.sha256(json.dumps(bykey[key]['payload'],sort_keys=True,allow_nan=False).encode()).hexdigest()==digest
        integrity['preparation_resume_unchanged_records']=len(saved)
    report=summarize(records,identity)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/'summary.json',report)
    payload=''.join(json.dumps(clean(r),sort_keys=True)+'\n' for r in records if r['state']=='finished').encode()
    (args.output/'records.jsonl.gz').write_bytes(gzip.compress(payload,mtime=0))
    evidence={'identity':identity,'measurement_source_commit':(args.run/'frozen-code-commit.txt').read_text().strip(),
        'integrity':integrity,'kind':'Optimizer preparation only; execution pending' if args.prepare_only else 'Completed prospective study'}
    if not args.prepare_only:
        evidence['completed_resume_verification']=json.loads((args.run/'completed-resume-verification.json').read_text())
    lines=['# Prospective CPU submission study','','**Preparation only; no runtime results yet.**' if args.prepare_only else '**Complete paired-profile and actual-policy study.**','',
        f"Profile slots: {report['recorded_profile_slots']}/{report['planned_profile_slots']}; policy slots: {report['recorded_policy_slots']}/{report['planned_policy_slots']}.",'',
        f"Seed provenance: {report['seed_reuse']['shared_sa_seeds_per_query']} of 30 SA seeds per query overlap the pilot; all {integrity['reused_seed_samples_bit_identical']} shared raw samples reproduce exactly. Treat this as controlled remeasurement, not independent replication.",'',
        '| Query | Both hints verified /30 | Changed physical plan | Flat cost lower | Flat cost equal | Flat cost higher |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for q in report['queries']:
        h=q['hint_pairing'];lines.append(f"| {q['query_id']} | {h['both_verified']}/30 | {h['different_physical_plan']} | {h['flat_estimated_cost_lower']} | {h['flat_estimated_cost_equal']} | {h['flat_estimated_cost_higher']} |")
    if not args.prepare_only:
        for group in ['method_aggregate','policy_aggregate']:
            lines+=['',f'## {group}','','| Method/arm | Threshold | Lower | Upper | Unknown |','|---|---:|---:|---:|---:|']
            for method,values in report[group].items():
                for risk in values['query_weighted_risk']:
                    lines.append(f"| {method} | {risk['threshold']} | {risk['lower']:.1%} | {risk['upper']:.1%} | {risk['unknown']} |")
    lines+=['','## Limits','']+['- '+s for s in report['limits']]
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')
    evidence['file_sha256']={p.name:sha(p) for p in args.output.iterdir() if p.name in {'summary.json','records.jsonl.gz','README.md'}}
    write_json(args.output/'evidence.json',evidence)
    if not args.prepare_only:
        verify_export(args.output)
    else:
        print('All prospective optimizer preparation records and paired hint constraints verified; timings pending')


if __name__=='__main__':
    main()
