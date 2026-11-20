"""Flat/directed hint verification; the flat constraint leaves orientations free."""
import re
from qopt.hints import extract_join_tree,left_deep_tree,leading_hint


def hint_for(aliases,directed):
    if not aliases or len(set(aliases))!=len(aliases) or any(not re.fullmatch(r'[a-z_][a-z0-9_]*',a) for a in aliases):
        raise ValueError('Unsafe or duplicate aliases')
    return leading_hint(left_deep_tree(aliases)) if directed else '/*+ Leading('+' '.join(aliases)+') */'


def unordered_tree(tree):
    if isinstance(tree,str):
        return tree
    return tuple(sorted((unordered_tree(tree[0]),unordered_tree(tree[1])),key=repr))


def verify_order(plan,aliases,directed):
    observed=extract_join_tree(plan)
    expected=left_deep_tree(aliases)
    if (observed if directed else unordered_tree(observed)) != (expected if directed else unordered_tree(expected)):
        raise ValueError('Requested join order was not enforced')
    return observed
