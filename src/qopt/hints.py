"""Conservative enforcement of directed inner-join trees for the pilot."""
import re


def left_deep_tree(aliases):
    if len(aliases) < 2 or len(set(aliases)) != len(aliases):
        raise ValueError("Need at least two distinct aliases")
    if any(not re.fullmatch(r"[a-z_][a-z0-9_]*", alias) for alias in aliases):
        raise ValueError("Pilot accepts only simple lowercase SQL aliases")
    tree = tuple(aliases[:2])
    for alias in aliases[2:]:
        tree = (tree, alias)
    return tree


def leading_hint(tree):
    def render(t):
        if isinstance(t, str):
            if not re.fullmatch(r"[a-z_][a-z0-9_]*", t):
                raise ValueError("Unsafe SQL alias")
            return t
        if not isinstance(t, tuple) or len(t) != 2:
            raise ValueError("Need a binary join tree")
        return "(" + render(t[0]) + " " + render(t[1]) + ")"
    return "/*+ Leading(" + render(tree) + ") */"


def extract_join_tree(node):
    """Preserve physical outer/inner direction, ignoring unary wrappers.

    Reject unrecognized shapes instead of treating a partial tree as verified.
    Scan children, e.g. bitmap index scans, do not represent additional relations.
    """
    if any(c.get("Parent Relationship") in {"InitPlan", "SubPlan"} for c in node.get("Plans", [])):
        raise ValueError("Subplans are outside the pilot verifier's scope")
    if node["Node Type"] in {"Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Heap Scan"}:
        return node["Alias"]
    children = node.get("Plans", [])
    if node["Node Type"] in {"Nested Loop", "Hash Join", "Merge Join"}:
        if node.get("Join Type") != "Inner" or len(children) != 2:
            raise ValueError("Only binary inner joins are supported")
        return tuple(extract_join_tree(child) for child in children)
    if node["Node Type"] in {"Aggregate", "Hash", "Sort", "Materialize", "Memoize", "Gather", "Gather Merge", "Result"} and len(children) == 1:
        return extract_join_tree(children[0])
    raise ValueError(f"Unsupported plan shape: {node['Node Type']}")


def verify_tree(plan, expected):
    observed = extract_join_tree(plan)
    if observed != expected:
        raise ValueError(f"Join hint not enforced: expected {expected!r}, observed {observed!r}")
    return observed
