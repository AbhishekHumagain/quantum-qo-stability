"""Generate final manuscript assets from verified completed evidence, never live DBs."""
import gzip
import hashlib
import json
from pathlib import Path
import statistics as st
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
LABELS={'sa_flat':'SA flat','sa_directed':'SA directed','geqo':'GEQO'}

def build():
    source=ROOT/'docs/submission-study-001';encoding=ROOT/'docs/encoding-001';paper=ROOT/'paper'
    for command in [
        ['scripts/analyze_submission_study.py','--verify-export',str(source)],
        ['scripts/verify_submission_export.py',str(source)],
        ['scripts/verify_encoding_export.py',str(encoding)]]:
        subprocess.run([sys.executable,*command],cwd=ROOT,check=True)
    r=json.loads((source/'summary.json').read_text());e=json.loads((encoding/'summary.json').read_text())
    with gzip.open(source/'records.jsonl.gz','rt') as f:
        records=[json.loads(line) for line in f]
    bykey={x['key']:x['payload'] for x in records if x['state']=='finished'}
    qs=sorted(r['queries'],key=lambda q:int(q['query_id'][:-1]))
    def fmt(v):return '--' if v is None else f'{v:.2f}'
    def table(name,rows):
        (paper/'tables'/name).write_text('\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)+'\n'+r'\bottomrule'+'\n')
    table('study-profile.tex',[[q['query_id'],q['distinct_physical_plans'],*[q['methods'][m]['known_ratios'] for m in LABELS],*[fmt(q['methods'][m]['median_ratio_complete_only']) for m in LABELS]] for q in qs])
    table('study-risk.tex',[[LABELS[m],f"{v['threshold']:.2f}",f"{100*v['lower']:.1f}--{100*v['upper']:.1f}",v['unknown']] for m,d in r['method_aggregate'].items() for v in d['query_weighted_risk']])
    policy=[];derived={'policy':{},'hint_runtime':{},'noise':{}}
    for arm in r['config']['policy_arms']:
        items=[q['policies'][arm] for q in qs];risk=r['policy_aggregate'][arm]['query_weighted_risk'][1]
        complete=sum(x['complete_requests'] for x in items);fallback=sum(x['guard_fallback_decisions'] for x in items)
        values=[x['payload'] for x in records if x['phase']=='policy' and x['payload'].get('arm')==arm and x['payload']['status']=='ok' and not x['payload'].get('clock_anomaly',True)]
        nonexec=st.median(x['end_to_end_ms']-x['execute_client_ms'] for x in values)
        derived['policy'][arm]={'complete':complete,'fallback':fallback,'nonexecution_ms_success_only_median':nonexec}
        label='Default' if arm=='default' else LABELS[arm.rsplit('_',1)[0]]+(' + guard' if arm.endswith('_guarded') else '')
        policy.append([label,complete,f'{fallback}/216' if arm.endswith('_guarded') else '--',f"{100*risk['lower']:.1f}--{100*risk['upper']:.1f}",risk['unknown'],f'{nonexec:.1f}'])
    table('study-policy.tex',policy)
    table('study-policy-query.tex',[[q['query_id'],*[fmt(q['policies'][a]['median_ratio_complete_only']) for a in r['config']['policy_arms'] if a!='default']] for q in qs])
    table('encoding-grid.tex',[[mult,budget,sum(x['hard_feasible'] for x in e['configurations'] if x['penalty_multiplier']==mult and x['budget']==budget),360] for mult in [1,4] for budget in ['pilot','higher']])
    # Pair matched hint variants by the original sample, retaining unavailable outcomes.
    diffs=[]
    for q in qs:
        qid=q['query_id'];available=[]
        for i in range(30):
            a=bykey[f'{qid}/proposal/sa_flat/{i:03d}'];b=bykey[f'{qid}/proposal/sa_directed/{i:03d}']
            ra=q['physical_plan_metrics'].get(a.get('plan_hash'),{}).get('median_ratio');rb=q['physical_plan_metrics'].get(b.get('plan_hash'),{}).get('median_ratio')
            if ra is not None and rb is not None:
                available.append((ra,rb))
        diffs.extend(available)
        derived['hint_runtime'][qid]={'known':len(available),'flat_lower':sum(a<b for a,b in available),'equal':sum(a==b for a,b in available),'flat_higher':sum(a>b for a,b in available)}
    derived['hint_runtime_total']={'known':len(diffs),'flat_lower':sum(a<b for a,b in diffs),'equal':sum(a==b for a,b in diffs),'flat_higher':sum(a>b for a,b in diffs),'unknown':360-len(diffs)}
    raw=[]
    for q in qs:
        p=q['physical_plan_metrics'][q['baseline_plan_hash']];raw+=p['raw_pair_ratios']
        derived['noise'][q['query_id']]={'pairs':p['known_pairs'],'raw_min':p['raw_min'],'raw_max':p['raw_max']}
    derived['same_plan_noise']={'valid_pairs':len(raw),'minimum':min(raw),'maximum':max(raw),'outside_1_25_band':sum(x<.8 or x>1.25 for x in raw)}
    derived['mean_disagreement']={m:st.mean(q['methods'][m]['disagreement_conditional_on_verified'] for q in qs) for m in LABELS}
    derived['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source/'summary.json',source/'records.jsonl.gz',encoding/'summary.json']}
    (paper/'derived-results.json').write_text(json.dumps(derived,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':9,'svg.fonttype':'none','svg.hashsalt':'qopt-study-001'})
    fig,axes=plt.subplots(1,2,figsize=(7.1,3.25),gridspec_kw={'width_ratios':[1.6,1]},layout='constrained')
    x=np.arange(len(qs));styles=[('sa_flat','#0072B2','o'),('sa_directed','#D55E00','s'),('geqo','#009E73','^')]
    for m,color,marker in styles:
        y=[q['methods'][m]['median_ratio_complete_only'] or np.nan for q in qs]
        axes[0].plot(x,y,marker=marker,color=color,label=LABELS[m],linewidth=1,markersize=4)
    axes[0].axhline(1,color='gray',linestyle='--',linewidth=.8);axes[0].set_yscale('log');axes[0].set_xticks(x,[q['query_id'] for q in qs],rotation=55);axes[0].set_ylabel('Profile ratio to paired default (log)');axes[0].set_title('(a) Complete-only per-query medians',fontsize=9);axes[0].legend(fontsize=8,loc='upper left');axes[0].grid(axis='y',alpha=.2)
    arms=[a for a in r['config']['policy_arms'] if a!='default']
    for i,a in enumerate(arms):
        v=r['policy_aggregate'][a]['query_weighted_risk'][1];color=styles[i//2][1]
        axes[1].plot([100*v['lower'],100*v['upper']],[i,i],color=color,lw=4,solid_capstyle='butt');axes[1].plot(100*v['lower'],i,'o',color=color,ms=4)
    axes[1].set_yticks(range(6),['Flat','Flat + guard','Directed','Directed + guard','GEQO','GEQO + guard']);axes[1].invert_yaxis();axes[1].set_xlim(0,100);axes[1].set_xlabel('Requests with slowdown >1.25 (%)');axes[1].set_title('(b) Service-latency bounds',fontsize=9);axes[1].grid(axis='x',alpha=.2)
    for ext in ['png','svg']:
        fig.savefig(paper/'figures'/f'study.{ext}',dpi=240,metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)
    prov=json.loads((paper/'results-provenance.json').read_text())
    for name,directory in [('submission_study',source),('encoding',encoding)]:
        evidence=json.loads((directory/'evidence.json').read_text())
        prov[name]={'source':str(directory.relative_to(ROOT)),'measurement_source_commit':evidence['measurement_source_commit'],'evidence_sha256':hashlib.sha256((directory/'evidence.json').read_bytes()).hexdigest(),'file_sha256':evidence['file_sha256'],'completed_resume_verification':evidence['completed_resume_verification']}
    prov['derived_results_sha256']=hashlib.sha256((paper/'derived-results.json').read_bytes()).hexdigest()
    (paper/'results-provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
    print('Completed-study tables, PNG/SVG, and provenance generated')

if __name__=='__main__':build()
