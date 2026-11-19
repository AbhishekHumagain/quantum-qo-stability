import pytest
from qopt.job_analysis import bounded_risk, disagreement, performance


def test_unknown_outcomes_widen_bounds_instead_of_disappearing():
    risk=bounded_risk([.5,2,None,None],1.25)
    assert risk['observed_lower_bound']==.25
    assert risk['observed_upper_bound']==.75
    assert risk['known_ratios']==2


def test_timeout_cap_is_not_a_completed_runtime():
    records=[{'status':'ok','execution_ms':10},{'status':'timeout'},
             {'status':'not_run_after_timeout'}]
    result=performance(records,[],3)
    assert result['status']=='censored'
    assert result['median_ms'] is None
    assert result['completed_repeats']==1
    complete=performance([{'status':'ok','execution_ms':v} for v in [10,12,11]],[],3)
    assert complete['median_ms']==11


def test_pairwise_disagreement_excludes_self_pairs():
    assert disagreement(['a','a','b'])==pytest.approx(2/3)
    assert disagreement(['a','a'])==0
    assert disagreement(['a']) is None


def test_cross_clock_anomaly_preserves_raw_median_but_makes_ratio_unavailable():
    result=performance([{'status':'ok','execution_ms':v,'client_wall_ms':20}
                        for v in [10,12,60010]],[],3)
    assert result['status']=='timing_anomaly'
    assert result['clock_anomaly_repeats']==1
    assert result['reported_median_ms_before_quality_screen']==12
    assert result['median_ms'] is None
    assert result['completed_repeats']==3
