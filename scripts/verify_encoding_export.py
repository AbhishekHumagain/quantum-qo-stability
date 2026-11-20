"""Recheck model-only evidence from public bitstrings and independent penalties."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from qopt.cli import ROOT
from qopt.encoding_audit import components


def main():
    directory=Path(sys.argv[1]);evidence=json.loads((directory/'evidence.json').read_text())
    for name,digest in evidence['file_sha256'].items():
        assert hashlib.sha256((directory/name).read_bytes()).hexdigest()==digest
    report=json.loads((directory/'summary.json').read_text())
    models=json.loads((ROOT/report['identity']['config']['estimated_inputs']).read_text())
    rows=json.loads(gzip.decompress((directory/'sensitivity-samples.json.gz').read_bytes()))
    def audit(row):
        model=models[row['query_id']];f=model['factors']
        pred=[(i,j) for i in range(len(f)) for j in range(i+1,len(f)) if f[i][j]!=1]
        return components(row['bits'],model['cards'],pred,[f[i][j] for i,j in pred])
    for row in rows:
        if row['status']=='ok':
            a=audit(row);assert a==row['audit']
            assert np.isclose(row['energy'],row['penalty_multiplier']*a['penalty_weight']*a['hard_penalty']+a['cost_component'],atol=1e-5,rtol=1e-8)
    for group in report['configurations']:
        subset=[r for r in rows if all(r.get(k)==group[k] for k in ['query_id','penalty_multiplier','budget'])]
        assert len(subset)==group['planned']==report['identity']['config']['seeds_per_query']
        assert sum(r['status']=='ok' and r['audit']['hard_feasible'] for r in subset)==group['hard_feasible']
    original=json.loads(gzip.decompress((ROOT/'docs/pilot-001/sa-samples.json.gz').read_bytes()))
    original_audits=json.loads(gzip.decompress((directory/'pilot-constraint-audit.json.gz').read_bytes()))
    lookup={(r['query_id'],r['run']):r for r in original_audits}
    feasible=0
    for row in original:
        a=audit(row);saved=lookup[(row['query_id'],row['run'])]
        assert all(saved[k]==v for k,v in a.items())
        assert np.isclose(a['reconstructed_energy'],row['energy'],atol=1e-5,rtol=1e-8)
        feasible+=a['hard_feasible']
    assert feasible==report['original_pilot_hard_feasible']
    assert len(original)==report['original_pilot_samples_audited']
    print(f'Encoding export verified: {len(rows)} prospective sensitivity draws and {len(original)} historical raw samples; energies and hard feasibility agree')


if __name__=='__main__':
    main()
