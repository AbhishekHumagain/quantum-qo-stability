"""Independent cost oracle, sample validation, and plan fingerprints."""
import hashlib
import itertools
import json


def intermediate_cost(order, cards, sels):
    """Sum non-final intermediate sizes using all predicates in each prefix.

    This matches the intended left-deep objective in QDBO helpers, not the
    PostgreSQL cost model or measured runtime. Cross products are permitted.
    """
    if sorted(order) != list(range(len(cards))):
        raise ValueError("Order must be a permutation of the relation indices")
    size = cards[order[0]]
    total = 0.0
    for pos, relation in enumerate(order[1:], 1):
        size *= cards[relation]
        for previous in order[:pos]:
            size *= sels[previous][relation]
        if pos < len(order) - 1:
            total += size
    return float(total)


def exhaustive_best(cards, sels):
    """Exact only for this model and left-deep space; first pair is unordered."""
    if len(cards) > 8:
        raise ValueError("Pilot exhaustive oracle limited to 8 relations")
    return min(((intermediate_cost(p, cards, sels), p)
                for p in itertools.permutations(range(len(cards))) if p[0] < p[1]),
               key=lambda x: (x[0], x[1]))


def order_key(order):
    order = list(order)
    order[:2] = sorted(order[:2])
    return ",".join(map(str, order))


def valid_membership(bits, n):
    """Check relation-count and prefix nesting constraints before repair."""
    matrix = [bits[i * (n-2):(i+1) * (n-2)] for i in range(n)]
    return (all(sum(row[j] for row in matrix) == j+2 for j in range(n-2))
            and all(row[j] <= row[j+1] for row in matrix for j in range(n-3)))


# Explicit allowlist prevents runtime/cost fields from altering plan identity.
PLAN_FIELDS = ("Node Type", "Parent Relationship", "Join Type", "Relation Name",
               "Schema", "Alias", "Index Name", "Scan Direction", "Strategy",
               "Partial Mode", "Parallel Aware", "Async Capable", "Workers Planned",
               "Inner Unique", "Hash Cond", "Merge Cond", "Join Filter", "Filter",
               "Index Cond", "Recheck Cond", "Sort Key", "Group Key", "CTE Name",
               "Subplan Name")


def canonical_plan(node):
    result = {key: node[key] for key in PLAN_FIELDS if key in node}
    if "Plans" in node:
        result["Plans"] = [canonical_plan(child) for child in node["Plans"]]
    return result


def plan_hash(node):
    return hashlib.sha256(json.dumps(canonical_plan(node), sort_keys=True).encode()).hexdigest()
