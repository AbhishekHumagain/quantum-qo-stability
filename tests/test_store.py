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
