"""Run a durable, model-only constraint/penalty/budget diagnostic."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import statistics
import time

import dimod
import numpy as np
from dwave.samplers import SimulatedAnnealingSampler
from qdbo.join_ordering.backend.bqm_solver_execution import build_bqm
from qdbo.join_ordering.backend.jo_utils import parse_selectivities
from qdbo.join_ordering.helpers import read_out
from qopt.cli import ROOT,write_json
from qopt.encoding_audit import components,validity_bqm
from qopt.store import RunStore


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    config_path=ROOT/'config/encoding-sensitivity-v1.json'
    config=json.loads(config_path.read_text());models=json.loads((ROOT/config['estimated_inputs']).read_text())
    identity={'config':config,'inputs_sha256':sha(ROOT/config['estimated_inputs']),
        'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__).resolve(),ROOT/'src/qopt/encoding_audit.py',ROOT/'src/qopt/store.py']},
        'upstream_generator_sha256':sha(ROOT/'vendor/qdbo/qdbo/join_ordering/backend/ProblemGenerator.py'),
        'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}}
    with RunStore(args.run,identity) as store:
        with sqlite3.connect(f'file:{ROOT/"results/job-pilot-001/run.sqlite3"}?mode=ro',uri=True) as old:
            rows=[(q,json.loads(p)) for q,p in old.execute("SELECT query_id,payload FROM tasks WHERE phase='solve' AND key LIKE '%/sa/%' ORDER BY key")]
        audit=[]
        for q,row in rows:
            m=models[q];pred,sel=parse_selectivities(m['factors'])
            a=components(row['bits'],m['cards'],pred,sel)
            assert np.isclose(a['reconstructed_energy'],row['energy'],atol=1e-5,rtol=1e-8)
            audit.append({'query_id':q,'run':row['run'],'seed':row['seed'],**a})
        for q,m in models.items():
            pred,sel=parse_selectivities(m['factors']);base=build_bqm(m['cards'],pred,sel)
            validity=validity_bqm(len(m['cards']),pred)
            for multiplier in config['penalty_multipliers']:
                bqm=base+(multiplier-1)*max(20,2*(len(m['cards'])-2))*validity
                for budget in config['sampling_budgets']:
                    for run in range(config['seeds_per_query']):
                        def sample():
                            start=time.perf_counter_ns()
                            best=SimulatedAnnealingSampler().sample(bqm,seed=config['seed']+run,
                                num_reads=budget['reads'],num_sweeps=budget['sweeps']).first
                            elapsed=(time.perf_counter_ns()-start)/1e6
                            bits=[int(best.sample[v]) for v in bqm.variables]
                            a=components(bits,m['cards'],pred,sel)
                            expected=multiplier*a['penalty_weight']*a['hard_penalty']+a['cost_component']
                            assert np.isclose(best.energy,expected,atol=1e-5,rtol=1e-8)
                            order,cost,connected=read_out(np.asarray(bits),m['cards'],pred,sel,{})
                            return {'bits':bits,'energy':float(best.energy),'audit':a,'decoded_order':order,
                                'decoded_model_cost':cost,'connected_selected':bool(connected),'sampling_ms':elapsed,
                                'query_id':q,'run':run,'seed':config['seed']+run,
                                'penalty_multiplier':multiplier,'budget':budget['name']}
                        store.perform(f'{q}/{multiplier}/{budget["name"]}/{run:03d}','sensitivity',q,sample,
                            context={'query_id':q,'run':run,'seed':config['seed']+run,'penalty_multiplier':multiplier,'budget':budget['name']})
            print(q+': all encoding sensitivity configurations recorded',flush=True)
        # Exhaustive post-hoc synthetic witness: all states, no selected sample or runtime claim.
        cards=[1e6]*3;pred=[(0,1),(0,2),(1,2)];sel=[.01]*3;base=build_bqm(cards,pred,sel);v=validity_bqm(3,pred)
        witness=[]
        for multiplier in [1,4]:
            all_states=dimod.ExactSolver().sample(base+(multiplier-1)*20*v)
            feasible=[];ground=[]
            for r in all_states.data():
                bits=[int(r.sample[k]) for k in base.variables];a=components(bits,cards,pred,sel)
                assert np.isclose(r.energy,multiplier*20*a['hard_penalty']+a['cost_component'],atol=1e-7)
                if a['hard_feasible']:
                    feasible.append(float(r.energy))
                if np.isclose(r.energy,all_states.first.energy,atol=1e-7,rtol=0):
                    ground.append(a['hard_feasible'])
            witness.append({'penalty_multiplier':multiplier,'states':len(all_states),'minimum_energy':float(all_states.first.energy),
                'minimum_hard_feasible_energy':min(feasible),'all_ground_states_hard_feasible':all(ground)})
        records=[r['payload'] for r in store.records('sensitivity') if r['state']=='finished']
        assert len(records)==len(models)*len(config['penalty_multipliers'])*len(config['sampling_budgets'])*config['seeds_per_query']
        grouped=[]
        for q in models:
            for multiplier in config['penalty_multipliers']:
                for budget in config['sampling_budgets']:
                    rows=[r for r in records if r.get('query_id')==q and r.get('penalty_multiplier')==multiplier and r.get('budget')==budget['name']]
                    ok=[r for r in rows if r['status']=='ok']
                    grouped.append({'query_id':q,'penalty_multiplier':multiplier,'budget':budget['name'],'planned':len(rows),
                        'statuses':dict(Counter(r['status'] for r in rows)),
                        'hard_feasible':sum(r['audit']['hard_feasible'] for r in ok),
                        'membership_feasible':sum(r['audit']['count_penalty']==r['audit']['nesting_penalty']==0 for r in ok),
                        'median_decoded_model_cost':statistics.median(r['decoded_model_cost'] for r in ok) if ok else None,
                        'median_sampling_ms':statistics.median(r['sampling_ms'] for r in ok) if ok else None})
        args.output.mkdir(parents=True,exist_ok=True)
        write_json(args.output/'summary.json',{'identity':identity,'original_pilot_samples_audited':len(audit),
            'original_pilot_hard_feasible':sum(a['hard_feasible'] for a in audit),'configurations':grouped,'synthetic_witness':witness,
            'note':'Model-only sensitivity, no tuning choice transferred to runtime experiment; synthetic witness is not an observed JOB failure mechanism.'})
        for name,data in [('pilot-constraint-audit.json.gz',audit),('sensitivity-samples.json.gz',records)]:
            (args.output/name).write_bytes(gzip.compress(json.dumps(data,sort_keys=True).encode(),mtime=0))
        write_json(args.output/'evidence.json',{'identity':identity,'file_sha256':{p.name:sha(p) for p in args.output.iterdir() if p.name!='evidence.json'}})
        write_json(args.run/'state.json',{'state':'complete'})


if __name__=='__main__':
    main()
