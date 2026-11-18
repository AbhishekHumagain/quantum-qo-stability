"""Inspect JOB SQL and select a performance-blind, template-disjoint pilot."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess

import networkx as nx
import sqlglot
from sqlglot import exp


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_sql(text):
    statements = sqlglot.parse(text, read="postgres")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("Expected one SELECT")
    statement = statements[0]
    if len(list(statement.find_all(exp.Select))) != 1:
        raise ValueError("Nested SELECT is outside this pilot's scope")
    tables = list(statement.find_all(exp.Table))
    aliases = [table.alias_or_name for table in tables]
    if len(set(aliases)) != len(aliases):
        raise ValueError("Repeated alias")
    mapping = [{"index": i, "alias": t.alias_or_name, "table": t.name} for i, t in enumerate(tables)]
    graph = nx.Graph()
    graph.add_nodes_from(aliases)
    where = statement.args.get("where")
    atoms = []
    def split_and(node):
        if isinstance(node, exp.And):
            split_and(node.this)
            split_and(node.expression)
        else:
            atoms.append(node)
    if where:
        split_and(where.this)
    local = defaultdict(list)
    joins = []
    unsupported = []
    for atom in atoms:
        referenced = {column.table for column in atom.find_all(exp.Column)}
        if "" in referenced or not referenced.issubset(set(aliases)):
            raise ValueError("Unqualified or unknown relation in WHERE")
        if len(referenced) < 2:
            if referenced:
                local[next(iter(referenced))].append(atom.sql(dialect="postgres"))
        elif (isinstance(atom, exp.EQ) and isinstance(atom.this, exp.Column)
              and isinstance(atom.expression, exp.Column) and len(referenced) == 2):
            a, b = sorted(referenced)
            graph.add_edge(a, b)
            joins.append({"aliases": [a, b], "sql": atom.sql(dialect="postgres")})
        else:
            unsupported.append(atom.sql(dialect="postgres"))
    if any(join.args.get("on") is not None or join.args.get("side") for join in statement.args.get("joins", [])):
        raise ValueError("Pilot inspector currently requires implicit inner joins")
    size = len(aliases)
    density = nx.density(graph)
    return {"relations": size, "alias_mapping": mapping,
        "local_filters": dict(local), "join_predicates": joins,
        "unsupported_cross_alias_predicates": unsupported,
        "edges": [list(edge) for edge in sorted(tuple(sorted(e)) for e in graph.edges)],
        "edge_count": graph.number_of_edges(), "components": nx.number_connected_components(graph),
        "cycle_rank": graph.number_of_edges()-size+nx.number_connected_components(graph),
        "density": density, "max_degree": max(dict(graph.degree).values(), default=0),
        "self_join": len({table.name for table in tables}) < size,
        "size_stratum": "small" if size <= 8 else "medium" if size <= 11 else "large",
        "density_band": "sparse" if density < .35 else "moderate" if density < .6 else "dense",
        "normalized_sql_sha256": hashlib.sha256(statement.sql(dialect="postgres", normalize=True).encode()).hexdigest()}


def build_catalog(root):
    root = Path(root)
    qdbo_root = root / "vendor/qdbo/workloads/join_ordering/JOB"
    supplied = {}
    for path in qdbo_root.glob("*/*.sql"):
        if path.name in supplied:
            raise ValueError(f"Duplicate upstream SQL mapping: {path.name}")
        supplied[path.name] = path
    rows = []
    for path in sorted((root / "vendor/job").glob("*.sql")):
        match = re.fullmatch(r"(\d+)([a-z]+)\.sql", path.name)
        if not match:
            continue
        row = {"query_id": path.stem, "template_id": int(match[1]), "variant": match[2],
               "sql_path": str(path.relative_to(root)), "sql_sha256": sha256(path),
               **inspect_sql(path.read_text())}
        counterpart = supplied.get(path.name)
        if counterpart:
            upstream = inspect_sql(counterpart.read_text())
            cards_path = counterpart.parent / "cardinalities.json"
            factors_path = counterpart.parent / "selectivities.json"
            cards = json.loads(cards_path.read_text())
            factors = json.loads(factors_path.read_text())
            row["qdbo"] = {"folder": str(counterpart.parent.relative_to(root)),
                "sql_sha256": sha256(counterpart), "cards_sha256": sha256(cards_path),
                "factors_sha256": sha256(factors_path),
                "normalized_sql_matches": upstream["normalized_sql_sha256"] == row["normalized_sql_sha256"],
                "alias_order_matches": upstream["alias_mapping"] == row["alias_mapping"],
                "dimensions_match": len(cards) == row["relations"] and len(factors) == len(cards) and all(len(r) == len(cards) for r in factors),
                "factor_above_one": any(v > 1 for r in factors for v in r),
                "cardinality_provenance": "unverified_published_artifact_inputs"}
        else:
            row["qdbo"] = None
        rows.append(row)
    if len(rows) != 113 or len({r["template_id"] for r in rows}) != 33:
        raise ValueError("Expected pinned JOB's 113 queries and 33 templates")
    return sorted(rows, key=lambda row: (row["template_id"], row["variant"]))


def select_pilot(rows, seed=20261118, per_stratum=4):
    """One lexicographically first variant/template; balance structural groups."""
    templates = {}
    for row in sorted(rows, key=lambda r: (r["template_id"], r["variant"])):
        templates.setdefault(row["template_id"], row)
    selected = []
    for stratum in ("small", "medium", "large"):
        groups = defaultdict(list)
        for row in templates.values():
            if row["size_stratum"] == stratum:
                groups[(row["self_join"], row["density_band"])].append(row)
        for values in groups.values():
            values.sort(key=lambda row: hashlib.sha256(f"{seed}:{row['template_id']}".encode()).hexdigest())
        group_keys = sorted(groups)
        if sum(map(len, groups.values())) < per_stratum:
            raise ValueError(f"Not enough distinct templates in {stratum}")
        population = [row for group in groups.values() for row in group]
        rank = lambda row: hashlib.sha256(f"{seed}:{row['template_id']}".encode()).hexdigest()
        chosen = []
        # Include each stratum's minimum and maximum size before balancing groups.
        for size in sorted({min(r['relations'] for r in population), max(r['relations'] for r in population)}):
            row = min((r for r in population if r['relations'] == size), key=rank)
            if len(chosen) < per_stratum:
                chosen.append(row)
                groups[(row['self_join'], row['density_band'])].remove(row)
        while len(chosen) < per_stratum:
            used = Counter((r['self_join'], r['density_band']) for r in chosen)
            group = min((g for g in group_keys if groups[g]), key=lambda g: (used[g], g))
            chosen.append(groups[group].pop(0))
        selected.extend(chosen)
    return selected


def generate(root, output, seed=20261118):
    root, output = Path(root), Path(output)
    rows = build_catalog(root)
    selected = select_pilot(rows, seed)
    commits = {name: subprocess.check_output(["git", "-C", str(root/"vendor"/name), "rev-parse", "HEAD"], text=True).strip() for name in ("job", "qdbo")}
    common = {"schema_version": 1, "source_commits": commits,
              "outcome_data_used_for_selection": False}
    output.mkdir(parents=True, exist_ok=True)
    (output/"catalog.json").write_text(json.dumps({**common, "queries": rows}, indent=2)+"\n")
    pilot = {**common, "selection_seed": seed,
        "selection_rule": "First variant per template; 4 templates per relation-size stratum; anchor min/max relation counts then round-robin self-join/density groups; SHA256 seed/template ranking for ties",
        "size_bounds": {"small": "<=8", "medium": "9..11", "large": ">=12"},
        "limits": {"solve_repeats": 30, "execution_repeats": 5, "statement_timeout_ms": 60000},
        "execution_status": "not_executed_on_JOB", "queries": selected}
    (output/"pilot.json").write_text(json.dumps(pilot, indent=2)+"\n")
    lines = ["# JOB pilot manifest", "", "Performance-blind selection; one variant per template. No JOB runtimes measured.", "",
        "| Query | Template | Relations | Edges | Cycle rank | Self join | Stratum |",
        "|---|---:|---:|---:|---:|---|---|"]
    lines += [f"| {r['query_id']} | {r['template_id']} | {r['relations']} | {r['edge_count']} | {r['cycle_rank']} | {r['self_join']} | {r['size_stratum']} |" for r in selected]
    lines += ["", f"Catalog: {len(rows)} instances, {len({r['template_id'] for r in rows})} templates.",
        f"All-instance size strata: {dict(Counter(r['size_stratum'] for r in rows))}.",
        "", "Graph edges reflect explicit cross-alias equality predicates, including redundant equalities;", "cycle rank is not a count of independent semantic join constraints."]
    (output/"README.md").write_text("\n".join(lines)+"\n")
    return pilot
