from copy import deepcopy
import pytest
from qopt.core import exhaustive_best, intermediate_cost, plan_hash, valid_membership


def test_all_prefix_predicates_are_used():
    cards = [100, 200, 300, 400]
    sels = [[1,.1,.01,1],[.1,1,.2,1],[.01,.2,1,1],[1,1,1,1]]
    # First join: 2000; second: 2000*300*.01*.2 = 1200.
    assert intermediate_cost([0,1,2,3], cards, sels) == pytest.approx(3200)
    with pytest.raises(ValueError):
        intermediate_cost([0,0,2,3], cards, sels)


def test_exact_oracle_known_three_relation_problem():
    assert exhaustive_best([10,20,30], [[1,.1,1],[.1,1,.01],[1,.01,1]]) == (6.0, (1,2,0))


def test_hash_ignores_noise_but_keeps_physical_choices():
    plan = {"Node Type":"Seq Scan", "Relation Name":"x", "Actual Total Time":1, "Total Cost":12}
    noise = deepcopy(plan)
    noise.update({"Actual Total Time":99, "Total Cost":100})
    assert plan_hash(plan) == plan_hash(noise)
    noise["Node Type"] = "Index Scan"
    assert plan_hash(plan) != plan_hash(noise)


def test_membership_checks_nesting_and_cardinality():
    assert valid_membership([1,1,1,1,0,1,0,0],4)
    assert not valid_membership([1,0,1,1,0,1,0,1],4)
