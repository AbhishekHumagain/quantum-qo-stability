"""Failure-aware summaries of the prospective study; no timeout-cap imputation."""
from collections import Counter
import json
import statistics
from qopt.cli import ROOT

from qopt.job_analysis import bounded_risk,disagreement


def median(values):
    return statistics.median(values) if values else None


def usable(row):
    return bool(row and row.get('status')=='ok' and not row.get('clock_anomaly',True))


def paired_ratio(rows,base_hash,expected):
    ratios=[];raw=[]
    for pair in rows:
        a,b=pair.get('baseline'),pair.get('candidate')
        if not (usable(a) and usable(b) and a['session']==b['session'] and a['execution_ms']>0):
            continue
        value=b['execution_ms']/a['execution_ms'];raw.append(value)
        ratios.append(1.0 if b['requested_plan_hash']==base_hash else value)
    return {'known_pairs':len(ratios),'median_ratio':median(ratios) if len(ratios)==expected else None,
        'raw_pair_ratios':raw,'raw_min':min(raw) if raw else None,'raw_max':max(raw) if raw else None,
        'note':'Identical physical plan uses structural ratio one; raw independent pairs remain a noise control. All five same-session clock-valid pairs are required.'}


def summarize(records,identity):
    config=identity['config']
    previous=json.loads((ROOT/config['source_pilot_evidence']).read_text())['identity']['config']
    shared_seeds=set(range(config['seed'],config['seed']+config['solve_repeats'])) & set(range(previous['seed'],previous['seed']+previous['solve_repeats']))
    finished=[r for r in records if r['state']=='finished']
    bykey={r['key']:r['payload'] for r in finished}
    qids=[r['query_id'] for r in finished if r['phase']=='baseline']
    queries=[]
    for qid in qids:
        base=bykey[qid+'/baseline'];base_hash=base['plan_hash']
        proposals={(m,i):bykey.get(f'{qid}/proposal/{m}/{i:03d}',{'status':'not_recorded'})
            for m in config['candidate_methods'] for i in range(config['solve_repeats'])}
        fingerprints={base_hash}|{p['plan_hash'] for p in proposals.values() if p['status']=='ok'}
        plan_metrics={}
        for h in sorted(fingerprints):
            pairs=[{role:bykey.get(f'{qid}/profile/{r:02d}/{h}/{role}') for role in ['baseline','candidate']}
                for r in range(config['execution_repeats'])]
            plan_metrics[h]=paired_ratio(pairs,base_hash,config['execution_repeats'])
        methods={}
        for m in config['candidate_methods']:
            trials=[proposals[(m,i)] for i in range(config['solve_repeats'])]
            valid=[t for t in trials if t['status']=='ok']
            ratios=[plan_metrics[t['plan_hash']]['median_ratio'] if t['status']=='ok' else None for t in trials]
            methods[m]={'planned_draws':len(trials),'proposal_statuses':dict(Counter(t['status'] for t in trials)),
                'distinct_verified_plans':len({t['plan_hash'] for t in valid}),
                'disagreement_conditional_on_verified':disagreement([t['plan_hash'] for t in valid]),
                'known_ratios':sum(x is not None for x in ratios),'median_ratio_complete_only':median([x for x in ratios if x is not None]),
                'risk':[bounded_risk(ratios,t) for t in config['descriptive_slowdown_thresholds']]}
        hint_pairs=[(proposals[('sa_flat',i)],proposals[('sa_directed',i)]) for i in range(config['solve_repeats'])]
        both=[(a,b) for a,b in hint_pairs if a['status']==b['status']=='ok']
        hint={'planned_sample_pairs':len(hint_pairs),'both_verified':len(both),
            'different_physical_plan':sum(a['plan_hash']!=b['plan_hash'] for a,b in both),
            'flat_estimated_cost_lower':sum(a['estimated_total_cost']<b['estimated_total_cost'] for a,b in both),
            'flat_estimated_cost_equal':sum(a['estimated_total_cost']==b['estimated_total_cost'] for a,b in both),
            'flat_estimated_cost_higher':sum(a['estimated_total_cost']>b['estimated_total_cost'] for a,b in both)}
        policies={}
        for arm in config['policy_arms']:
            rows=[];ratios=[]
            for i in config['policy_seed_indices']:
                for r in range(config['policy_repeats']):
                    row=bykey.get(f'{qid}/policy/{i:03d}/{r:02d}/{arm}',{'status':'not_recorded'})
                    default=bykey.get(f'{qid}/policy/{i:03d}/{r:02d}/default')
                    rows.append(row)
                    ratio=row['end_to_end_ms']/default['end_to_end_ms'] if usable(row) and usable(default) and row['session']==default['session'] and default['end_to_end_ms']>0 else None
                    ratios.append(ratio)
            complete=[r for r in rows if usable(r)]
            policies[arm]={'planned_requests':len(rows),'statuses':dict(Counter(r['status'] for r in rows)),
                'complete_requests':len(complete),'known_paired_default_ratios':sum(x is not None for x in ratios),
                'guard_fallback_decisions':sum(r.get('guard_fallback',False) for r in rows),
                'recorded_guard_decisions':sum('guard_fallback' in r for r in rows),
                'median_end_to_end_ms_success_only':median([r['end_to_end_ms'] for r in complete]),
                'median_execute_client_ms_success_only':median([r['execute_client_ms'] for r in complete if 'execute_client_ms' in r]),
                'median_ratio_complete_only':median([x for x in ratios if x is not None]),
                'risk':[bounded_risk(ratios,t) for t in config['descriptive_slowdown_thresholds']]}
        samples=[bykey.get(f'{qid}/sample/{i:03d}') for i in range(config['solve_repeats'])]
        samples=[s for s in samples if s and s['status']=='ok']
        queries.append({'query_id':qid,'baseline_plan_hash':base_hash,'distinct_physical_plans':len(fingerprints),
            'encoding_task_ms':bykey[qid+'/encoding'].get('task_wall_seconds',0)*1000,
            'sample_hard_feasible':sum(s['encoding_audit']['hard_feasible'] for s in samples),
            'decoder_changed_raw_order':sum(s['decoder_changed_raw_order'] for s in samples),
            'hint_pairing':hint,'methods':methods,'physical_plan_metrics':plan_metrics,'policies':policies})
    def aggregate(group,names):
        output={}
        for name in names:
            items=[q[group][name] for q in queries]
            risks=[]
            for j,t in enumerate(config['descriptive_slowdown_thresholds']):
                risks.append({'threshold':t,'lower':statistics.mean(i['risk'][j]['observed_lower_bound'] for i in items),
                    'upper':statistics.mean(i['risk'][j]['observed_upper_bound'] for i in items),
                    'confirmed_slow':sum(i['risk'][j]['confirmed_slow_trials'] for i in items),
                    'unknown':sum(i['risk'][j]['unknown_trials'] for i in items)})
            output[name]={'query_weighted_risk':risks}
        return output
    measured=[r['payload'] for r in finished if r['phase'] in {'profile','policy'}]
    admission_events={}
    for record in finished:
        row=record['payload']
        if record['phase'] in {'profile','policy'} and 'admission_wait_seconds' in row:
            event=(record['query_id'],row.get('session'),row.get('pair_plan_hash'),row.get('repetition'),
                   row.get('arm'),row.get('run'),row['admission_wait_seconds'])
            admission_events[event]=row['admission_wait_seconds']
    return {'kind':'Controlled CPU follow-up; paired TIMING OFF profiles and actual validated warm requests',
        'config':config,'queries':queries,
        'seed_reuse':{'shared_sa_seeds_per_query':len(shared_seeds),
            'shared_seed_query_pairs':len(shared_seeds)*len(qids),
            'interpretation':'Partially reused seeds and same workload/estimates: controlled remeasurement, not an independent replication of the original pilot.'},
        'planned_profile_slots':sum(q['distinct_physical_plans']*config['execution_repeats']*2 for q in queries),
        'recorded_profile_slots':sum(r['phase']=='profile' for r in finished),
        'planned_policy_slots':len(qids)*len(config['policy_seed_indices'])*config['policy_repeats']*len(config['policy_arms']),
        'recorded_policy_slots':sum(r['phase']=='policy' for r in finished),
        'phase_statuses':{phase:dict(Counter(r['payload']['status'] for r in finished if r['phase']==phase)) for phase in ['sample','proposal','warmup','profile','policy']},
        'measured_clock_anomalies':sum(r.get('clock_anomaly',False) for r in measured),
        'abandoned_warmup_attempts':sum(r['state']=='abandoned' and r['phase']=='warmup' for r in records),
        'measured_load_after_above_admission_limit':sum(bool(r.get('load_after')) and r['load_after'][0]>r.get('admission_limit',float('inf')) for r in measured),
        'total_recorded_admission_wait_seconds':sum(admission_events.values()),
        'method_aggregate':aggregate('methods',config['candidate_methods']),
        'policy_aggregate':aggregate('policies',config['policy_arms']),
        'limits':['Coverage-selected twelve templates on one shared host; load admission is not isolation.',
            'Unknown-outcome intervals are descriptive identification bounds, not confidence intervals.',
            'Fixed cached inputs/BQM: request timer is validated prepared-input warm-request service latency; queue wait and preprocessing are separate.',
            'Plain SELECT actual timed plan is not directly observed; logged pre/post fingerprints are checks, not a sampled execution tree.',
            'Six selected seeds and three policy blocks per query are dependent repeated requests, not independent workload samples.',
            'Five profile pairs characterize a preliminary noise diagnostic; retain raw same-plan ratios.',
            'No quantum hardware, full iterative QDBO, equal-compute fairness, or production-safety guarantee.']}
