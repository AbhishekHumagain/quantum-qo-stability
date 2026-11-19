from qopt.calibration import clock_quality,schedule
from qopt.store import RunStore


def test_two_clocks_detect_sleep_and_server_clock_discrepancy():
    assert not clock_quality(9,10,11,1000)
    assert clock_quality(9,10,60010,1000)
    assert clock_quality(60010,10,10,1000)
    assert not clock_quality(None,10,11,1000)


def test_timeout_stops_only_affected_mode_and_completed_resume_is_noop(tmp_path,monkeypatch):
    calls=[]
    def measure(conn,statement,m,fingerprint,tolerance):
        calls.append(m)
        return {'status':'timeout' if m=='timing_on' else 'ok'}
    monkeypatch.setattr('qopt.calibration.measure',measure)
    config={'modes':['timing_on','timing_off','plain'],'execution_repeats':3,'seed':7,'clock_tolerance_ms':1000}
    with RunStore(tmp_path,{}) as store:
        schedule(store,None,'q','SELECT 1','hash',config,'one')
        assert len(store.records('execution'))==9
        assert all(r['payload']['status']=='not_run_after_failure' for r in store.records('execution') if r['payload']['measurement_mode']=='timing_on')
        assert sum(m=='timing_on' for m in calls)==1
        before=store.records()
    with RunStore(tmp_path,{}) as store:
        schedule(store,None,'q','SELECT 1','hash',config,'two')
        assert store.records()==before
    assert len(calls)==9
