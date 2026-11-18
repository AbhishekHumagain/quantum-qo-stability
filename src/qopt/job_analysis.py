"""Descriptive pilot analysis. Censored/failed plans never become numeric caps."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import statistics


def bounded_risk(ratios, threshold):
    known = [x for x in ratios if x is not None]
    slow = sum(x>threshold for x in known)
    n = len(ratios)
    unknown = n-len(known)
    return {'threshold':threshold,'planned_trials':n,'known_ratios':len(known),
            'confirmed_slow_trials':slow,'unknown_trials':unknown,
            'observed_lower_bound':slow/n if n else None,
            'observed_upper_bound':(slow+unknown)/n if n else None,
            'interpretation':'Identification bounds for this observed pilot, not confidence intervals'}


def disagreement(keys):
    counts = Counter(keys)
    n = len(keys)
    return 1-sum(c*(c-1) for c in counts.values())/(n*(n-1)) if n>1 else None


def performance(executions, warmups, expected):
    successful = [r['execution_ms'] for r in executions if r['status']=='ok']
    statuses = Counter(r['status'] for r in executions)
    timed_out = any(r['status']=='timeout' for r in executions+warmups)
    complete = len(executions)==expected and len(successful)==expected
    return {'status':'complete' if complete else 'censored' if timed_out else 'incomplete_or_invalid',
        'scheduled_repeats':expected,'recorded_repeats':len(executions),
        'completed_repeats':len(successful),'execution_statuses':dict(statuses),
        'warmup_statuses':dict(Counter(r['status'] for r in warmups)),
        'median_ms':statistics.median(successful) if complete else None,
        'cv':statistics.stdev(successful)/statistics.mean(successful) if complete and len(successful)>1 and statistics.mean(successful)>0 else None,
        'min_ms':min(successful) if complete else None,'max_ms':max(successful) if complete else None}


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def analyze(directory):
    directory = Path(directory)
    with sqlite3.connect(f'file:{directory / "run.sqlite3"}?mode=ro',uri=True) as db:
        identity = json.loads(db.execute("SELECT value FROM metadata WHERE key='identity'").fetchone()[0])
        records = [{'key':k,'phase':p,'query_id':q,'state':s,'payload':json.loads(value) if value else None}
            for k,p,q,s,value in db.execute('SELECT key,phase,query_id,state,payload FROM tasks ORDER BY key')]
        interruptions = db.execute("SELECT count(*) FROM events WHERE event='interrupted_attempt'").fetchone()[0]
    config = identity['config']
    # The manifest source is frozen by identity; refuse silently changed selection.
    root = Path(__file__).resolve().parents[2]
    pilot_path = root/config['workload']
    if hashlib.sha256(pilot_path.read_bytes()).hexdigest()!=identity['pilot_sha256']:
        raise ValueError('Frozen workload changed')
    pilot = json.loads(pilot_path.read_text())
    finished = [r for r in records if r['state']=='finished']
    by_key = {r['key']:r['payload'] for r in finished}
    queries = []
    for query in pilot['queries']:
        qid = query['query_id']
        base = by_key.get(f'{qid}/baseline',{})
        fingerprints = {base['plan_hash']} if base.get('status')=='ok' else set()
        successful_draws = [r['payload'] for r in finished if r['phase']=='solve' and r['query_id']==qid and r['payload']['status']=='ok']
        fingerprints.update(r['plan_hash'] for r in successful_draws)
        plans = {}
        for fingerprint in sorted(fingerprints):
            executions = [r['payload'] for r in finished if r['phase']=='execution' and r['query_id']==qid
                          and r['payload'].get('requested_plan_hash')==fingerprint]
            warmups = [r['payload'] for r in finished if r['phase']=='warmup' and r['query_id']==qid
                       and r['payload'].get('requested_plan_hash')==fingerprint]
            plans[fingerprint] = performance(executions,warmups,config['execution_repeats'])
        base_metrics = plans.get(base.get('plan_hash'),{})
        base_ms = base_metrics.get('median_ms')
        result = {'query_id':qid,'template_id':query['template_id'],'relations':query['relations'],
            'baseline_status':base.get('status','not_recorded'),'baseline_plan_hash':base.get('plan_hash'),
            'baseline':base_metrics,'physical_plans':plans,'solvers':{}}
        for solver in ('sa','geqo'):
            trials = [by_key.get(f'{qid}/solve/{solver}/{i:03d}',{'status':'not_recorded'}) for i in range(config['solve_repeats'])]
            verified = [t for t in trials if t['status']=='ok']
            ratios, guarded = [], []
            for trial in trials:
                candidate_ms = plans.get(trial.get('plan_hash'),{}).get('median_ms') if trial['status']=='ok' else None
                ratio = candidate_ms/base_ms if candidate_ms is not None and base_ms else None
                ratios.append(ratio)
                guarded.append(1.0 if base_ms and trial.get('guard_fallback',True) else ratio)
            result['solvers'][solver] = {'planned_trials':len(trials),
                'trial_statuses':dict(Counter(t['status'] for t in trials)),
                'verified_trials':len(verified),'distinct_physical_plans':len({t['plan_hash'] for t in verified}),
                'pairwise_plan_disagreement_conditional_on_verified':disagreement([t['plan_hash'] for t in verified]),
                'raw_membership_valid_fraction':statistics.mean(t['raw_membership_valid'] for t in trials if 'raw_membership_valid' in t) if any('raw_membership_valid' in t for t in trials) else None,
                'known_runtime_ratios':sum(v is not None for v in ratios),
                'median_runtime_ratio_complete_only':median(ratios),
                'max_runtime_ratio_complete_only':max((v for v in ratios if v is not None),default=None),
                'risk':[bounded_risk(ratios,t) for t in config['descriptive_slowdown_thresholds']],
                'offline_guard_fallbacks':sum(t.get('guard_fallback',True) for t in trials),
                'offline_guard_risk':[bounded_risk(guarded,t) for t in config['descriptive_slowdown_thresholds']],
                'offline_guard_median_ratio_complete_only':median(guarded),
                'median_optimizer_task_ms':median([t.get('task_wall_seconds',0)*1000 for t in trials if t['status']!='not_recorded']),
                'median_sa_sampling_ms':median([t['solve_seconds']*1000 for t in trials if 'solve_seconds' in t]),
                'median_decoding_ms':median([t['decode_seconds']*1000 for t in trials if 'decode_seconds' in t]),
                'median_validation_ms':median([t['validation_seconds']*1000 for t in trials if 'validation_seconds' in t]),
                'median_incremental_guard_comparison_us':median([t['guard_decision_seconds']*1e6 for t in trials if 'guard_decision_seconds' in t])}
        queries.append(result)
    actual_executions = [r for r in finished if r['phase']=='execution' and not r['payload']['status'].startswith('not_run')]
    warmups = [r for r in finished if r['phase']=='warmup']
    solves = [r for r in finished if r['phase']=='solve']
    aggregate = {}
    for solver in ('sa','geqo'):
        items = [q['solvers'][solver] for q in queries]
        aggregate[solver] = {'planned_trials':len(items)*config['solve_repeats'],
            'verified_trials':sum(s['verified_trials'] for s in items),
            'known_runtime_ratios':sum(s['known_runtime_ratios'] for s in items),
            'mean_query_pairwise_plan_disagreement':statistics.mean(s['pairwise_plan_disagreement_conditional_on_verified'] for s in items if s['pairwise_plan_disagreement_conditional_on_verified'] is not None) if any(s['pairwise_plan_disagreement_conditional_on_verified'] is not None for s in items) else None,
            'offline_guard_fallbacks':sum(s['offline_guard_fallbacks'] for s in items),
            'query_weighted_risk':[]}
        for i,threshold in enumerate(config['descriptive_slowdown_thresholds']):
            aggregate[solver]['query_weighted_risk'].append({'threshold':threshold,
                'lower':statistics.mean(s['risk'][i]['observed_lower_bound'] for s in items),
                'upper':statistics.mean(s['risk'][i]['observed_upper_bound'] for s in items),
                'offline_guard_lower':statistics.mean(s['offline_guard_risk'][i]['observed_lower_bound'] for s in items),
                'offline_guard_upper':statistics.mean(s['offline_guard_risk'][i]['observed_upper_bound'] for s in items)})
    return {'kind':'Descriptive JOB CPU pilot; fixed-input SA/GEQO; no quantum hardware',
        'config':config,'planned_optimizer_trials':len(queries)*config['solve_repeats']*2,
        'recorded_optimizer_trials':len(solves),'optimizer_statuses':dict(Counter(r['payload']['status'] for r in solves)),
        'recorded_execution_slots':sum(r['phase']=='execution' for r in finished),
        'actual_measured_execution_attempts':len(actual_executions),
        'execution_attempt_statuses':dict(Counter(r['payload']['status'] for r in actual_executions)),
        'warmup_attempts':len(warmups),'warmup_statuses':dict(Counter(r['payload']['status'] for r in warmups)),
        'interrupted_attempt_events':interruptions,'unfinished_tasks':sum(r['state']!='finished' for r in records),
        'pipeline_state':json.loads((directory/'state.json').read_text()) if (directory/'state.json').exists() else {'state':'running_or_interrupted'},
        'aggregate':aggregate,'queries':queries,
        'limitations':['Twelve selected templates; one machine; low-budget CPU solvers; estimated pairwise inputs.',
            'No quantum, hybrid service, full iterative QDBO, or true-cardinality intervention.',
            'Complete-only ratios exclude unmeasurable outcomes; risk bounds retain unknowns.',
            'Offline guard diagnostics reuse shared medians and do not measure guarded end-to-end latency.',
            'Five repetitions characterize only a preliminary execution-noise floor; no p99 or significance claim.']}


def render_report(report, output):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    def fmt(value):
        return f'{value:.3f}' if value is not None else 'unknown'
    lines = ['# JOB CPU pilot v1', '', '**Exploratory measured JOB results; no quantum hardware.**', '',
        f"Optimizer trials recorded: {report['recorded_optimizer_trials']}/{report['planned_optimizer_trials']}. "
        f"Measured execution attempts: {report['actual_measured_execution_attempts']}; warmups: {report['warmup_attempts']}.",
        f"Pipeline state: {report['pipeline_state']['state']}. Optimizer outcomes: {report['optimizer_statuses']}.", '',
        '| Query | Relations | Default median ms | Default CV | SA plans | GEQO plans | SA median ratio* | SA known/30 | GEQO median ratio* | GEQO known/30 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for q in report['queries']:
        sa,geqo = q['solvers']['sa'],q['solvers']['geqo']
        lines.append(f"| {q['query_id']} | {q['relations']} | {fmt(q['baseline'].get('median_ms'))} | {fmt(q['baseline'].get('cv'))} | {sa['distinct_physical_plans']} | {geqo['distinct_physical_plans']} | {fmt(sa['median_runtime_ratio_complete_only'])} | {sa['known_runtime_ratios']}/30 | {fmt(geqo['median_runtime_ratio_complete_only'])} | {geqo['known_runtime_ratios']}/30 |")
    lines += ['', '*Ratios use only plans with all five successful measured repetitions and a complete baseline. '
        'They are conditional descriptions, not estimates that silently count failed/censored plans as fast.', '',
        '## Risk accounting', '', '| Solver | Slowdown threshold | Observed lower bound | Observed upper bound | Offline guard lower | Offline guard upper |',
        '|---|---:|---:|---:|---:|---:|']
    for solver,item in report['aggregate'].items():
        for risk in item['query_weighted_risk']:
            lines.append(f"| {solver} | >{risk['threshold']}x | {risk['lower']:.1%} | {risk['upper']:.1%} | {risk['offline_guard_lower']:.1%} | {risk['offline_guard_upper']:.1%} |")
    lines += ['', 'Bounds retain unknown outcomes in all 30 planned trials/query and weight queries equally. '
        'They are identification bounds over the observed pilot, not confidence intervals or a population guarantee.',
        'Guard decisions use pre-execution costs; their runtime diagnostics reuse measured plan medians. '
        'This is not a replayed end-to-end safeguard experiment.', '', '## Timing components', '',
        '| Query | SA optimizer task ms | SA sampling ms | SA decode ms | SA validation ms | GEQO optimizer task ms | SA guard comparison us |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for q in report['queries']:
        sa,geqo=q['solvers']['sa'],q['solvers']['geqo']
        lines.append(f"| {q['query_id']} | {fmt(sa['median_optimizer_task_ms'])} | {fmt(sa['median_sa_sampling_ms'])} | {fmt(sa['median_decoding_ms'])} | {fmt(sa['median_validation_ms'])} | {fmt(geqo['median_optimizer_task_ms'])} | {fmt(sa['median_incremental_guard_comparison_us'])} |")
    lines += ['', 'Optimizer task time includes adapter and planning overhead. Model extraction, encoding, '
        'and baseline estimation were cached once/query; encoding-task wall time includes first-use imports. '
        'The guard comparison is only a Python comparison; validation is separately measured. '
        'None of these columns is total end-to-end guarded latency.', '',
        '## Limits', '']+[f'- {item}' for item in report['limitations']]
    (output/'README.md').write_text('\n'.join(lines)+'\n')


def plot_report(report, output):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(__file__).resolve().parents[2]/'.local/mpl'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x=list(range(len(report['queries'])))
    figure,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
    for i,q in enumerate(report['queries']):
        value=q['baseline'].get('median_ms')
        if value:
            axes[0].bar(i,value,color='#64748b',width=.55)
        for solver,offset,color,marker in [('sa',-.12,'#c2410c','o'),('geqo',.12,'#0369a1','D')]:
            ratio=q['solvers'][solver]['median_runtime_ratio_complete_only']
            if ratio is not None:
                axes[1].scatter(i+offset,ratio,color=color,marker=marker,s=45,
                    label=solver.upper() if i==0 else None)
    axes[0].set_yscale('log')
    axes[0].set_ylabel('Default median execution (ms)')
    axes[1].set_yscale('log')
    axes[1].axhline(1,color='#334155',linewidth=1)
    axes[1].axhline(1.25,color='#94a3b8',linestyle='--',linewidth=1)
    axes[1].set_ylabel('Median candidate/default ratio\n(complete plans only)')
    axes[1].set_xticks(x,[q['query_id'] for q in report['queries']])
    axes[1].set_xlabel('Selected JOB query')
    axes[1].legend(frameon=False)
    for axis in axes:
        axis.grid(axis='y',alpha=.2)
        axis.set_axisbelow(True)
        axis.spines[['top','right']].set_visible(False)
    figure.suptitle('JOB CPU pilot: timing and conditional slowdown',fontsize=14)
    figure.text(.5,-.025,'Low-budget SA and GEQO; failures/censoring are accounted for separately in the report.',ha='center',fontsize=9)
    figure.savefig(Path(output)/'pilot.png',dpi=180,bbox_inches='tight')
    figure.savefig(Path(output)/'pilot.svg',bbox_inches='tight')
    plt.close(figure)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--plot',action='store_true')
    args=parser.parse_args()
    report=analyze(args.run)
    render_report(report,args.output)
    if args.plot:
        plot_report(report,args.output)
    print(json.dumps({k:report[k] for k in ('recorded_optimizer_trials','optimizer_statuses','actual_measured_execution_attempts','execution_attempt_statuses','warmup_statuses','pipeline_state')},indent=2))


if __name__=='__main__':
    main()
