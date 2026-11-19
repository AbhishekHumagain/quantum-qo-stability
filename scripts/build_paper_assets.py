"""Generate manuscript tables and figures only from the verified pilot export."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'docs/pilot-001'
    subprocess.run([sys.executable,str(ROOT/'scripts/verify_pilot_export.py'),str(source)],check=True)
    report=json.loads((source/'summary.json').read_text())
    paper=ROOT/'paper'
    (paper/'tables').mkdir(parents=True,exist_ok=True)
    (paper/'figures').mkdir(parents=True,exist_ok=True)
    def fmt(v):
        return '--' if v is None else f'{v:.2f}'
    rows=[]
    for q in report['queries']:
        sa,ge=q['solvers']['sa'],q['solvers']['geqo']
        rows.append(f"{q['query_id']} & {q['relations']} & {fmt(q['baseline'].get('median_ms'))} & {fmt(q['baseline'].get('cv'))} & {sa['distinct_physical_plans']} & {ge['distinct_physical_plans']} & {sa['known_runtime_ratios']} & {ge['known_runtime_ratios']} \\\\")
    (paper/'tables/query-results.tex').write_text('\n'.join(rows)+'\n'+r'\bottomrule'+'\n')
    rows=[]
    for solver,label in [('sa','CPU SA'),('geqo','GEQO')]:
        for risk in report['aggregate'][solver]['query_weighted_risk']:
            rows.append(f"{label} & {risk['threshold']:.2f} & {risk['lower']*100:.1f}--{risk['upper']*100:.1f} & {risk['offline_guard_lower']*100:.1f}--{risk['offline_guard_upper']*100:.1f} \\\\")
    (paper/'tables/risk-results.tex').write_text('\n'.join(rows)+'\n'+r'\bottomrule'+'\n')
    shutil.copy2(source/'pilot.png',paper/'figures/pilot.png')
    evidence=json.loads((source/'evidence.json').read_text())
    (paper/'results-provenance.json').write_text(json.dumps({
        'source':'docs/pilot-001/summary.json',
        'summary_sha256':hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
        'measurement_source_commit':evidence['frozen_code_commit'],
        'note':'Generated tables and copied figure use audited pilot-001, including its explicitly post-hoc timing screen.'},indent=2)+'\n')
    print('Manuscript assets generated from verified pilot-001')

if __name__=='__main__':
    main()
