import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import time

import numpy as np
from qopt.core import exhaustive_best, intermediate_cost, order_key, plan_hash, valid_membership

ROOT = Path(__file__).resolve().parents[2]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def provenance(args):
    repos = {}
    for name in ("qdbo", "q2o", "job", "pg_hint_plan"):
        repo = ROOT / "vendor" / name
        repos[name] = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    return {"utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "platform": platform.platform(), "upstream_commits": repos,
            "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
            "arguments": vars(args)}


def sa_pilot(args):
    from dwave.samplers import SimulatedAnnealingSampler
    from qdbo.join_ordering.backend.bqm_solver_execution import build_bqm
    from qdbo.join_ordering.backend.jo_utils import parse_selectivities
    from qdbo.join_ordering.helpers import read_out

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "manifest.json", provenance(args))
    rows = []
    for query in args.queries:
        folder = ROOT / "vendor/qdbo/workloads/join_ordering/JOB" / query
        cards = json.loads((folder / "cardinalities.json").read_text())
        sels = json.loads((folder / "selectivities.json").read_text())
        pred, pred_sel = parse_selectivities(sels)
        optimum, optimal_order = exhaustive_best(cards, sels)
        started = time.perf_counter()
        bqm = build_bqm(cards, pred, pred_sel)
        build_seconds = time.perf_counter() - started
        for run in range(args.repeats):
            seed = args.seed + run
            started = time.perf_counter()
            samples = SimulatedAnnealingSampler().sample(bqm, seed=seed,
                num_reads=args.reads, num_sweeps=args.sweeps)
            solve_seconds = time.perf_counter() - started
            best = samples.first
            bits = [int(best.sample[v]) for v in bqm.variables]
            order, upstream_cost, repaired = read_out(np.asarray(bits), cards, pred, pred_sel, {})
            cost = intermediate_cost(order, cards, sels)
            if not np.isclose(cost, upstream_cost, atol=1.01, rtol=0):
                raise ValueError("Upstream decoded cost disagrees with independent oracle")
            row = {"kind": "cost_model_only", "query": query,
                "sql_file": next(folder.glob("*.sql")).name,
                "solver": "sa_on_qdbo_bqm", "run": run, "seed": seed,
                "relations": len(cards), "variables": len(bqm.variables),
                "reads": args.reads, "sweeps": args.sweeps, "bits": bits,
                "energy": float(best.energy), "raw_membership_valid": valid_membership(bits, len(cards)),
                "decoder_selected_connected": bool(repaired), "order": order,
                "order_key": order_key(order), "cost": cost, "model_optimum": optimum,
                "optimal_order": optimal_order, "cost_ratio_to_model_optimum": cost / optimum,
                "build_seconds": build_seconds, "solve_seconds": solve_seconds}
            rows.append(row)
            with (out / "runs.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
        print(f"{query}: {len(cards)} relations, {len(bqm.variables)} variables, {args.repeats} solves", flush=True)
    summaries = []
    for query in args.queries:
        subset = [r for r in rows if r["query"] == query]
        keys = [r["order_key"] for r in subset]
        counts = [keys.count(k) for k in set(keys)]
        n = len(keys)
        summaries.append({"query": query, "solves": n, "unique_orders": len(counts),
            "pairwise_order_disagreement": 1-sum(c*(c-1) for c in counts)/(n*(n-1)) if n > 1 else None,
            "raw_membership_valid_fraction": np.mean([r["raw_membership_valid"] for r in subset]).item(),
            "median_model_cost_ratio": float(np.median([r["cost_ratio_to_model_optimum"] for r in subset])),
            "max_model_cost_ratio": max(r["cost_ratio_to_model_optimum"] for r in subset)})
    write_json(out / "summary.json", summaries)
    print(json.dumps(summaries, indent=2))


def db_pilot(args):
    """Standalone GEQO smoke test with raw plans and randomized executions."""
    import psycopg
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    manifest = provenance(args)
    sql = (ROOT / "workloads/smoke/query.sql").read_text()
    with psycopg.connect(os.environ.get("QOPT_DSN", f"host=/tmp/qopt-reliability-{os.getuid()} port=55432 dbname=postgres"), autocommit=True) as conn:
        conn.execute((ROOT / "workloads/smoke/setup.sql").read_text())
        for setting in ("SET search_path TO qopt_smoke, public", "SET max_parallel_workers_per_gather=0",
                        "SET jit=off", "SET work_mem='16MB'", "SET statement_timeout='10s'",
                        "SET geqo_threshold=2", "SET geqo_effort=1", "SET geqo_pool_size=10",
                        "SET geqo_generations=2"):
            conn.execute(setting)
        manifest["postgres_version"] = conn.execute("SELECT version()").fetchone()[0]
        manifest["settings"] = dict(conn.execute("SELECT name, setting FROM pg_settings").fetchall())
        write_json(out / "manifest.json", manifest)
        # Warm-up both planner modes; every measured call still replans.
        for mode in ("off", "on"):
            conn.execute(f"SET geqo={mode}")
            conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql).fetchone()
        schedule = [(solver, run, repetition) for solver in ("postgres_dp", "geqo")
                    for run in range(args.repeats) for repetition in range(args.executions)]
        random.Random(args.seed).shuffle(schedule)
        with (out / "runs.jsonl").open("w") as stream:
            for solver, run, repetition in schedule:
                conn.execute("SET geqo=" + ("on" if solver == "geqo" else "off"))
                geqo_seed = (run+1)/(args.repeats+1)
                conn.execute("SELECT set_config('geqo_seed', %s, false)", (str(geqo_seed),))
                started = time.perf_counter()
                plan = conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql).fetchone()[0][0]
                row = {"kind": "synthetic_db_smoke", "solver": solver, "run": run,
                       "repetition": repetition, "geqo_seed": geqo_seed, "plan_hash": plan_hash(plan["Plan"]),
                       "execution_ms": plan["Execution Time"], "planning_ms": plan["Planning Time"],
                       "wall_ms": (time.perf_counter()-started)*1000, "explain": plan}
                stream.write(json.dumps(row) + "\n")
    print(f"Recorded {len(schedule)} executions in {out}; synthetic smoke data only")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sa = sub.add_parser("sa-pilot")
    sa.add_argument("--queries", nargs="+", default=["q1", "q2", "q3"])
    sa.add_argument("--reads", type=int, default=10)
    sa.add_argument("--sweeps", type=int, default=200)
    db = sub.add_parser("db-pilot")
    db.add_argument("--executions", type=int, default=5)
    hinted = sub.add_parser("hinted-pilot")
    hinted.add_argument("--executions", type=int, default=5)
    hinted.add_argument("--reads", type=int, default=10)
    hinted.add_argument("--sweeps", type=int, default=200)
    for p in (sa, db, hinted):
        p.add_argument("--repeats", type=int, default=30)
        p.add_argument("--seed", type=int, default=20261118)
        p.add_argument("--output", required=True)
    args = parser.parse_args()
    for field in ("repeats", "reads", "sweeps", "executions"):
        if hasattr(args, field) and getattr(args, field) < 1:
            parser.error(f"--{field} must be positive")
    if args.command == "sa-pilot":
        sa_pilot(args)
    elif args.command == "db-pilot":
        db_pilot(args)
    else:
        from qopt.hinted import run
        run(args)
