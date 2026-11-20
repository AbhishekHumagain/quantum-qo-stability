"""Independently recompute numeric results from exported prospective task records.

This verifier deliberately does not import the study summary implementation.
"""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import sys
from qopt.core import plan_hash
from qopt.study_hints import verify_order


def main():
    directory=Path(sys.argv[1])
    evidence=json.loads((directory/'evidence.json').read_text())
    for name,digest in evidence['file_sha256'].items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
    with gzip.open(directory/'records.jsonl.gz','rt') as stream:
        records=[json.loads(line) for line in stream]
    report=json.loads((directory/'summary.json').read_text());config=report['config']
    values={r['key']:r['payload'] for r in records}
    def valid(r):
        return r is not None and r.get('status')=='ok' and r.get('clock_anomaly') is False
    def check_risks(ratios,expected):
        for item in expected:
            slow=sum(r is not None and r>item['threshold'] for r in ratios)
            unknown=sum(r is None for r in ratios);n=len(ratios)
            assert slow==item['confirmed_slow_trials'] and unknown==item['unknown_trials']
            assert item['planned_trials']==n
            assert slow/n==item['observed_lower_bound'] and (slow+unknown)/n==item['observed_upper_bound']
    for record in records:
        row=record['payload']
        if row['status']=='ok' and record['phase'] in {'baseline','proposal','profile'}:
            assert plan_hash(row['explain']['Plan'])==row['plan_hash']
            if record['phase'] in {'baseline','proposal'}:
                recipe=row['recipe']
                if recipe['aliases'] is not None:
                    verify_order(row['explain']['Plan'],recipe['aliases'],recipe['directed'])
            if record['phase']=='profile':
                assert row['plan_hash']==row['requested_plan_hash']
        if record['phase']=='policy' and row['status']=='ok':
            assert row['pre_plan_hash']==row['post_plan_hash']==row['requested_plan_hash']
            assert row['end_to_end_ms']>=row['execute_client_ms']
    method_risks={m:[] for m in config['candidate_methods']};policy_risks={a:[] for a in config['policy_arms']}
    planned_profiles=0
    for q in report['queries']:
        qid=q['query_id'];base=values[qid+'/baseline'];base_h=base['plan_hash']
        proposals={(m,i):values[f'{qid}/proposal/{m}/{i:03d}'] for m in config['candidate_methods'] for i in range(config['solve_repeats'])}
        hashes={base_h}|{r['plan_hash'] for r in proposals.values() if r['status']=='ok'}
        assert len(hashes)==q['distinct_physical_plans'];planned_profiles+=len(hashes)*config['execution_repeats']*2
        plan_medians={}
        for h in hashes:
            raw=[]
            for rep in range(config['execution_repeats']):
                a=values[f'{qid}/profile/{rep:02d}/{h}/baseline'];b=values[f'{qid}/profile/{rep:02d}/{h}/candidate']
                if valid(a) and valid(b) and a['session']==b['session'] and a['execution_ms']>0:
                    raw.append(b['execution_ms']/a['execution_ms'])
            value=(1.0 if h==base_h else statistics.median(raw)) if len(raw)==config['execution_repeats'] else None
            expected=q['physical_plan_metrics'][h]
            assert expected['known_pairs']==len(raw) and expected['raw_pair_ratios']==raw
            assert expected['median_ratio']==value
            plan_medians[h]=value
        for method in config['candidate_methods']:
            ratios=[plan_medians[p['plan_hash']] if p['status']=='ok' else None for p in [proposals[(method,i)] for i in range(config['solve_repeats'])]]
            expected=q['methods'][method]
            assert expected['known_ratios']==sum(v is not None for v in ratios)
            check_risks(ratios,expected['risk']);method_risks[method].append(expected['risk'])
        digests=set()
        for arm in config['policy_arms']:
            ratios=[];fallbacks=0;decisions=0
            for i in config['policy_seed_indices']:
                for rep in range(config['policy_repeats']):
                    row=values[f'{qid}/policy/{i:03d}/{rep:02d}/{arm}'];default=values[f'{qid}/policy/{i:03d}/{rep:02d}/default']
                    ratios.append(row['end_to_end_ms']/default['end_to_end_ms'] if valid(row) and valid(default) and row['session']==default['session'] and default['end_to_end_ms']>0 else None)
                    fallbacks+=bool(row.get('guard_fallback'));decisions+='guard_fallback' in row
                    if row['status']=='ok':
                        digests.add(row['result_sha256'])
                    if arm.endswith('_guarded') and 'guard_fallback' in row:
                        p=proposals[(arm.rsplit('_',1)[0],i)]
                        decision=row['proposal_status']!='ok' or p['estimated_total_cost']>base['estimated_total_cost']
                        assert row['guard_fallback']==decision
                        assert row['requested_plan_hash']==(base_h if decision else p['plan_hash'])
            expected=q['policies'][arm]
            assert expected['guard_fallback_decisions']==fallbacks and expected['recorded_guard_decisions']==decisions
            assert expected['known_paired_default_ratios']==sum(v is not None for v in ratios)
            check_risks(ratios,expected['risk']);policy_risks[arm].append(expected['risk'])
        assert len(digests)<=1
    for label,collected in [('method_aggregate',method_risks),('policy_aggregate',policy_risks)]:
        for name,items in collected.items():
            for j,result in enumerate(report[label][name]['query_weighted_risk']):
                assert result['lower']==statistics.mean(q[j]['observed_lower_bound'] for q in items)
                assert result['upper']==statistics.mean(q[j]['observed_upper_bound'] for q in items)
                assert result['confirmed_slow']==sum(q[j]['confirmed_slow_trials'] for q in items)
                assert result['unknown']==sum(q[j]['unknown_trials'] for q in items)
    assert report['planned_profile_slots']==report['recorded_profile_slots']==planned_profiles
    assert report['planned_policy_slots']==report['recorded_policy_slots']==len(report['queries'])*len(config['policy_seed_indices'])*config['policy_repeats']*len(config['policy_arms'])
    print('Independent arithmetic verified: paired medians, all query/method and actual-policy risk bounds, fallback selections, result consistency and aggregate counts')


if __name__=='__main__':
    main()
