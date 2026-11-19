import pytest
from qopt.store import RunStore, StopRequested


def test_finished_and_failed_tasks_are_not_reexecuted(tmp_path):
    with RunStore(tmp_path,{'seed':1}) as store:
        assert store.perform('a','solve','q',lambda:{'value':7})['value']==7
        result=store.perform('b','solve','q',lambda:1/0,context={'seed':123})
        assert result['status']=='error' and result['seed']==123
    with RunStore(tmp_path,{'seed':1}) as store:
        assert store.perform('a','solve','q',lambda:pytest.fail('duplicate execution'))['value']==7
        assert store.perform('b','solve','q',lambda:pytest.fail('failure must remain recorded'))['status']=='error'
    with pytest.raises(ValueError,match='identity changed'):
        RunStore(tmp_path,{'seed':2})


def test_interrupted_attempt_is_retained_and_recovered(tmp_path):
    def interrupted():
        raise KeyboardInterrupt
    with RunStore(tmp_path,{'seed':1}) as store:
        with pytest.raises(KeyboardInterrupt):
            store.perform('a','execution','q',interrupted)
        assert store.records()[0]['state']=='running'
    with RunStore(tmp_path,{'seed':1}) as store:
        result=store.perform('a','execution','q',lambda:{'value':8})
        assert result['attempt']==2
        assert store.db.execute("SELECT count(*) FROM events WHERE event='interrupted_attempt'").fetchone()[0]==1


def test_single_owner_and_checkpoint(tmp_path):
    with RunStore(tmp_path,{},max_new_tasks=1) as store:
        with pytest.raises(RuntimeError,match='Another process'):
            RunStore(tmp_path,{})
        store.perform('a','solve','q',lambda:{})
        with pytest.raises(StopRequested):
            store.perform('b','solve','q',lambda:{})
        assert store.get('b') is None


def test_crashed_warmup_is_preserved_and_new_session_rewarms(tmp_path,monkeypatch):
    from qopt.job_runner import execute_query_plans
    calls=[]
    def measure(conn,candidate,config,session):
        calls.append(session)
        if session=='old':
            raise KeyboardInterrupt
        return {'status':'ok','execution_ms':10,'client_wall_ms':11}
    monkeypatch.setattr('qopt.job_runner.execute_plan',measure)
    candidates={'hash':{'plan_hash':'hash'}}
    config={'execution_repeats':2,'seed':1}
    with RunStore(tmp_path,{}) as store:
        with pytest.raises(KeyboardInterrupt):
            execute_query_plans(store,None,'q',candidates,config,'old')
        assert store.records()[0]['payload']['requested_plan_hash']=='hash'
    with RunStore(tmp_path,{}) as store:
        orphan=store.records()[0]
        assert orphan['state']=='abandoned'
        assert orphan['payload']['status']=='interrupted'
        assert orphan['payload']['session']=='old'
        assert orphan['attempt']==1
        execute_query_plans(store,None,'q',candidates,config,'new')
        assert store.get('q/warmup/new/hash')['status']=='ok'
        assert all(store.get(f'q/execution/{r:02d}/hash')['status']=='ok' for r in range(2))
        assert store.db.execute("SELECT count(*) FROM events WHERE event='interrupted_attempt'").fetchone()[0]==1
    assert calls==['old','new','new','new']
    with RunStore(tmp_path,{}) as store:
        execute_query_plans(store,None,'q',candidates,config,'third')
        assert len(store.records())==4
        assert store.db.execute("SELECT count(*) FROM events WHERE event='interrupted_attempt'").fetchone()[0]==1
    assert calls==['old','new','new','new']
