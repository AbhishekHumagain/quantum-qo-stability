import pytest
from qopt.hints import extract_join_tree, leading_hint, left_deep_tree, verify_tree


def scan(alias):
    return {"Node Type": "Seq Scan", "Alias": alias}


def test_directed_hint_and_hash_wrappers():
    tree = left_deep_tree(["f", "a", "b"])
    assert leading_hint(tree) == "/*+ Leading(((f a) b)) */"
    join = {"Node Type": "Hash Join", "Join Type": "Inner", "Plans": [scan("f"), {"Node Type": "Hash", "Plans": [scan("a")]}]}
    assert extract_join_tree(join) == ("f", "a")
    assert verify_tree(join, ("f", "a")) == ("f", "a")
    with pytest.raises(ValueError, match="not enforced"):
        verify_tree(join, ("a", "f"))


def test_bitmap_children_are_not_extra_relations():
    assert extract_join_tree({"Node Type": "Bitmap Heap Scan", "Alias": "a", "Plans": [{"Node Type": "Bitmap Index Scan"}]}) == "a"


def test_unsupported_shapes_and_unsafe_aliases_fail_closed():
    with pytest.raises(ValueError):
        extract_join_tree({"Node Type": "Append", "Plans": [scan("a"),scan("b")]})
    with pytest.raises(ValueError):
        left_deep_tree(["f", "a); SELECT 1"])
    with pytest.raises(ValueError):
        left_deep_tree(["f", "f"])
