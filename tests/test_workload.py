import pytest
from qopt.workload import inspect_sql, select_pilot


def test_local_or_and_self_join_aliases():
    row = inspect_sql("SELECT min(a.id) FROM title a,title b WHERE a.id=b.id AND (a.x=1 OR a.x=2)")
    assert row["self_join"]
    assert row["relations"] == 2
    assert row["edges"] == [["a","b"]]
    assert len(row["local_filters"]["a"]) == 1


def test_cross_alias_disjunction_is_not_silently_a_graph_edge():
    row = inspect_sql("SELECT * FROM title a,title b WHERE a.id=b.id OR a.x=b.x")
    assert not row["edges"]
    assert len(row["unsupported_cross_alias_predicates"]) == 1
    with pytest.raises(ValueError):
        inspect_sql("SELECT * FROM title a WHERE a.id IN (SELECT id FROM title)")


def test_selection_is_order_independent_and_template_disjoint():
    rows = [{"template_id": i, "variant": variant, "size_stratum": stratum,
             "self_join": bool(i%2), "density_band": "sparse", "relations": 4+i}
            for i,stratum in enumerate(["small"]*5+["medium"]*5+["large"]*5)
            for variant in ("a","b")]
    result = select_pilot(rows)
    assert result == select_pilot(list(reversed(rows)))
    assert len(result) == len({r["template_id"] for r in result}) == 12
    assert all(r["variant"] == "a" for r in result)
