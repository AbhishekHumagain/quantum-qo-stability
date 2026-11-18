"""Database-backed synthetic SA pilot; not an IMDB/JOB experiment."""
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import time

import numpy as np
import psycopg
from psycopg import sql as psql

from qopt.cli import ROOT, provenance, write_json
from qopt.core import intermediate_cost, plan_hash, valid_membership
from qopt.hints import extract_join_tree, leading_hint, left_deep_tree, verify_tree

ALIASES = ["f", "a", "b", "c", "d"]
SOURCES = ["fact f", "dim a", "dim b", "dim c", "dim d"]
FILTERS = ["true", "a.bucket<3", "b.bucket<5", "c.bucket<7", "true"]


def explain(conn, query, analyze=False):
    options = "ANALYZE, BUFFERS, " if analyze else ""
    return conn.execute(f"EXPLAIN ({options}FORMAT JSON) " + query).fetchone()[0][0]


def model_inputs(conn):
    """Estimated filtered base and pair rows, not oracle subplan cardinalities."""
    queries = [f"SELECT * FROM {source} WHERE {where}" for source, where in zip(SOURCES, FILTERS)]
    cards = [explain(conn, query)["Plan"]["Plan Rows"] for query in queries]
    sels = [[1.0]*len(cards) for _ in cards]
    evidence = {"base_queries": queries, "pair_queries": []}
    for j in range(1, len(cards)):
        query = f"SELECT * FROM {SOURCES[0]}, {SOURCES[j]} WHERE f.{ALIASES[j]}={ALIASES[j]}.id AND {FILTERS[j]}"
        rows = explain(conn, query)["Plan"]["Plan Rows"]
        sels[0][j] = sels[j][0] = rows / (cards[0]*cards[j])
        evidence["pair_queries"].append({"sql": query, "estimated_rows": rows})
    return cards, sels, evidence


def run(args):
    from dwave.samplers import SimulatedAnnealingSampler
    from qdbo.join_ordering.backend.bqm_solver_execution import build_bqm
    from qdbo.join_ordering.backend.jo_utils import parse_selectivities
    from qdbo.join_ordering.helpers import read_out

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = provenance(args)
    manifest["kind"] = "synthetic_sa_database_pilot"
    manifest["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("src", "workloads/smoke") for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts}
    binary = next(iter(sorted((ROOT / ".local/lib").glob("pg_hint_plan.*"))), None)
    if binary is None:
        raise RuntimeError("Run bash scripts/build_hint_plan.sh first")
    manifest["hint_binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    query = (ROOT / "workloads/smoke/query.sql").read_text()
    dsn = os.environ.get("QOPT_DSN", f"host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=postgres")
    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
        conn.execute(psql.SQL("LOAD {}").format(psql.Literal(str(binary))))
        conn.execute((ROOT / "workloads/smoke/setup.sql").read_text())
        for statement in ("SET search_path TO qopt_smoke, public", "SET geqo=off",
                          "SET max_parallel_workers_per_gather=0", "SET jit=off",
                          "SET work_mem='16MB'", "SET statement_timeout='10s'",
                          "SET pg_hint_plan.enable_hint=on"):
            conn.execute(statement)
        manifest["postgres_version"] = conn.execute("SELECT version()").fetchone()[0]
        manifest["settings"] = dict(conn.execute("SELECT name, setting FROM pg_settings").fetchall())
        write_json(out / "manifest.json", manifest)
        cards, sels, evidence = model_inputs(conn)
        write_json(out / "model.json", {"aliases": ALIASES, "cards": cards, "factors": sels, "evidence": evidence})
        pred, pred_sel = parse_selectivities(sels)
        started = time.perf_counter()
        bqm = build_bqm(cards, pred, pred_sel)
        build_seconds = time.perf_counter()-started
        baseline = explain(conn, query)
        baseline_tree = extract_join_tree(baseline["Plan"])
        # A different requested tree MUST be rejected when the extension is disabled.
        negative_tree = left_deep_tree(["f", "d", "c", "b", "a"])
        if negative_tree == baseline_tree:
            negative_tree = left_deep_tree(["a", "f", "c", "b", "d"])
        conn.execute("SET pg_hint_plan.enable_hint=off")
        ignored = explain(conn, leading_hint(negative_tree)+"\n"+query)
        rejected = False
        try:
            verify_tree(ignored["Plan"], negative_tree)
        except ValueError:
            rejected = True
        conn.execute("SET pg_hint_plan.enable_hint=on")
        if not rejected:
            raise RuntimeError("Negative control failed: ignored hint was accepted")
        verified = explain(conn, leading_hint(negative_tree)+"\n"+query)
        verify_tree(verified["Plan"], negative_tree)
        write_json(out / "hint-controls.json", {"negative_control_rejected": rejected,
            "positive_control_verified": True, "requested": negative_tree,
            "disabled_explain": ignored, "enabled_explain": verified})

        candidates = {"baseline": {"sql": query, "expected": None, "preflight": baseline}}
        solves = []
        with (out / "solves.jsonl").open("w") as stream:
            for run_id in range(args.repeats):
                seed = args.seed+run_id
                started = time.perf_counter()
                sample = SimulatedAnnealingSampler().sample(bqm, seed=seed, num_reads=args.reads, num_sweeps=args.sweeps).first
                solve_seconds = time.perf_counter()-started
                bits = [int(sample.sample[v]) for v in bqm.variables]
                order, _, connected = read_out(np.asarray(bits), cards, pred, pred_sel, {})
                aliases = [ALIASES[i] for i in order]
                key = ",".join(aliases)
                if key not in candidates:
                    tree = left_deep_tree(aliases)
                    hinted_query = leading_hint(tree)+"\n"+query
                    started = time.perf_counter()
                    preflight = explain(conn, hinted_query)
                    verify_tree(preflight["Plan"], tree)
                    candidates[key] = {"sql": hinted_query, "expected": tree, "preflight": preflight,
                                       "validation_seconds": time.perf_counter()-started}
                row = {"run": run_id, "seed": seed, "candidate": key, "order": order,
                       "energy": float(sample.energy), "bits": bits,
                       "raw_membership_valid": valid_membership(bits, len(cards)),
                       "decoder_selected_connected": bool(connected),
                       "model_cost": intermediate_cost(order, cards, sels),
                       "build_seconds": build_seconds, "solve_seconds": solve_seconds}
                solves.append(row)
                stream.write(json.dumps(row)+"\n")
                stream.flush()
        write_json(out / "candidates.json", candidates)
        # Warm up each distinct candidate once, then interleave executions in blocks.
        for candidate in candidates.values():
            warmed = explain(conn, candidate["sql"], True)
            if candidate["expected"] is not None:
                verify_tree(warmed["Plan"], candidate["expected"])
        rng = random.Random(args.seed)
        records = []
        with (out / "executions.jsonl").open("w") as stream:
            for repetition in range(args.executions):
                keys = list(candidates)
                rng.shuffle(keys)
                for key in keys:
                    candidate = candidates[key]
                    started = time.perf_counter()
                    observed = explain(conn, candidate["sql"], True)
                    if candidate["expected"] is not None:
                        verify_tree(observed["Plan"], candidate["expected"])
                    if plan_hash(observed["Plan"]) != plan_hash(candidate["preflight"]["Plan"]):
                        raise RuntimeError("Physical plan changed between preflight and execution")
                    row = {"candidate": key, "repetition": repetition,
                           "plan_hash": plan_hash(observed["Plan"]), "explain": observed,
                           "execution_ms": observed["Execution Time"], "planning_ms": observed["Planning Time"],
                           "wall_ms": (time.perf_counter()-started)*1000}
                    records.append(row)
                    stream.write(json.dumps(row)+"\n")
                    stream.flush()
        medians = {key: statistics.median(r["execution_ms"] for r in records if r["candidate"] == key) for key in candidates}
        baseline_ms = medians["baseline"]
        # Exploratory guard: selection depends only on pre-execution planner costs.
        # Policy latency is estimated from shared execution measurements, not replayed.
        guarded = []
        for row in solves:
            key = row["candidate"]
            fallback = candidates[key]["preflight"]["Plan"]["Total Cost"] > baseline["Plan"]["Total Cost"]
            guarded.append(medians["baseline" if fallback else key]/baseline_ms)
            row["guard_fallback"] = fallback
        ratios = [medians[row["candidate"]]/baseline_ms for row in solves]
        summary = {"kind": "synthetic_pipeline_check_not_paper_results", "solves": len(solves),
            "distinct_directed_orders": len(candidates)-1, "measured_executions": len(records),
            "hint_controls_passed": True, "all_executed_trees_verified": True,
            "baseline_median_ms": baseline_ms, "median_ms_by_candidate": medians,
            "unguarded_median_ratio": statistics.median(ratios), "unguarded_max_ratio": max(ratios),
            "estimated_cost_guard_fallbacks": sum(r["guard_fallback"] for r in solves),
            "guarded_median_ratio_shared_measurements": statistics.median(guarded),
            "guarded_max_ratio_shared_measurements": max(guarded)}
        write_json(out / "guard-decisions.json", solves)
        write_json(out / "summary.json", summary)
        print(json.dumps(summary, indent=2))
