import pytest
from qopt.study_hints import unordered_tree,hint_for,verify_order
from qopt.encoding_audit import components,validity_bqm


def test_flat_equivalence_allows_directions_but_not_changed_prefixes():
    assert unordered_tree((('a','b'),'c'))==unordered_tree(('c',('b','a')))
    assert unordered_tree((('a','b'),'c'))!=unordered_tree((('a','c'),'b'))
    assert hint_for(['a','b','c'],False)=='/*+ Leading(a b c) */'
    assert hint_for(['a','b','c'],True)=='/*+ Leading(((a b) c)) */'
    with pytest.raises(ValueError):
        hint_for(['a','a'],False)


def test_energy_reconstruction_and_one_way_predicate_constraints():
    # Three relations -> one encoded join, three membership bits, one predicate, six slack bits.
    cards=[1,1,1];pred=[(0,1)];sels=[1]
    bits=[1,1,0,0]+[0]*6
    c=components(bits,cards,pred,sels)
    assert c['hard_feasible'] and c['inactive_applicable_predicates']==1
    assert c['reconstructed_energy']==0
    assert validity_bqm(3,pred).energy(dict(enumerate(bits)))==0
    bad=[1,0,1,1]+[0]*6
    c=components(bad,cards,pred,sels)
    assert c['predicate_activation_penalty']==1
    assert validity_bqm(3,pred).energy(dict(enumerate(bad)))==1


def test_actual_guard_executes_fallback_and_retains_failed_proposal_cost(monkeypatch):
    import qopt.submission_study as study
    calls=[]
    base={'status':'ok','plan_hash':'baseline','estimated_total_cost':10,'preflight_ms':1}
    candidate={'status':'ok','plan_hash':'candidate','estimated_total_cost':20,'sample_bits_sha256':'bits','sampling_ms':2,'preflight_ms':3}
    monkeypatch.setattr(study,'preflight',lambda *a,**kw:base)
    monkeypatch.setattr(study,'proposal',lambda *a,**kw:candidate.copy())
    def execute(conn,selected,config):
        calls.append(selected['plan_hash'])
        return {'status':'ok','execute_client_ms':5,'clock_anomaly':False}
    monkeypatch.setattr(study,'plain_once',execute)
    config={'clock_tolerance_ms':1000}
    result=study.request(None,'sql',None,None,'sa_flat_guarded',0,config,candidate,base,{})
    assert result['status']=='ok' and result['guard_fallback']
    assert result['requested_plan_hash']=='baseline' and calls==['baseline']
    assert result['components']['sampling_ms']==2 and result['end_to_end_ms']>=0
    candidate['estimated_total_cost']=5
    result=study.request(None,'sql',None,None,'sa_flat_guarded',0,config,candidate,base,{})
    assert not result['guard_fallback'] and calls[-1]=='candidate'
    candidate['status']='unverified_plan'
    result=study.request(None,'sql',None,None,'sa_flat_unguarded',0,config,candidate,base,{})
    assert result['status']=='invalid_proposal' and 'end_to_end_ms' in result
    assert calls==['baseline','candidate']


def test_paired_schedule_retains_timeout_and_completed_resume(monkeypatch,tmp_path):
    import qopt.submission_study as study
    from qopt.store import RunStore
    calls=[]
    monkeypatch.setattr(study,'gate',lambda *a:{})
    def profile(conn,candidate,config):
        calls.append(candidate['plan_hash'])
        return {'status':'timeout' if candidate['plan_hash']=='bad' else 'ok','execution_ms':10,'clock_anomaly':False}
    monkeypatch.setattr(study,'profile_once',profile)
    base={'plan_hash':'base'};candidates={'base':base,'bad':{'plan_hash':'bad'}}
    config={'execution_repeats':2,'seed':1}
    with RunStore(tmp_path,{}) as store:
        study.run_profiles(store,None,'q',candidates,base,config,'one')
        assert len(store.records('profile'))==8
        assert calls.count('bad')==1
        saved=store.records()
    with RunStore(tmp_path,{}) as store:
        study.run_profiles(store,None,'q',candidates,base,config,'two')
        assert store.records()==saved
    assert calls.count('bad')==1


def test_pair_ratio_rejects_partial_and_mixed_sessions_but_keeps_noise_control():
    from qopt.study_analysis import paired_ratio
    def row(h,ms,session='s'):
        return {'status':'ok','clock_anomaly':False,'requested_plan_hash':h,'execution_ms':ms,'session':session}
    pair={'baseline':row('base',10),'candidate':row('other',20)}
    assert paired_ratio([pair],'base',1)['median_ratio']==2
    assert paired_ratio([pair],'base',2)['median_ratio'] is None
    pair['candidate']['session']='another'
    assert paired_ratio([pair],'base',1)['known_pairs']==0
    same={'baseline':row('base',10),'candidate':row('base',30)}
    result=paired_ratio([same],'base',1)
    assert result['median_ratio']==1 and result['raw_pair_ratios']==[3]
