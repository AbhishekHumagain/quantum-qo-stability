# Reliability of stochastic join-order optimization

Measuring regression risk and evaluating safeguards in quantum-augmented query planning.

This project is an experimental research artifact in development. The full 12-template
JOB CPU pilot is complete: 720 optimizer trials and 2,425 execution slots. Timing
anomalies and high baseline noise limit interpretation; this is not a quantum
advantage or publication-ready performance claim. Start with [milestone 04](docs/milestone-04.md)
and the [measured pilot report and evidence](docs/pilot-001/README.md).

The [IEEE conference first draft](paper/main.tex) reports these results with their
limitations. Build an Overleaf ZIP and reviewed PDF using
`bash scripts/build_paper.sh`. The [submission evidence plan](docs/submission-readiness.md)
tracks the controlled follow-up experiments. The separate
[baseline calibration](docs/calibration-001/README.md) completed all 360 slots
without detected clock discrepancies, while substantial timing variation remains.

## What works

- Project-local Python 3.12 environment, pinned installed dependencies.
- Pinned QDBO, Q2O, and Join Order Benchmark repositories under `vendor/`.
- Simulated annealing using the **unmodified published QDBO BQM builder and decoder**.
- Independent left-deep cost oracle, exhaustive reference for up to eight relations,
  membership-constraint checks, and structural PostgreSQL plan fingerprints.
- JSONL records containing seeds, bitstrings, solver parameters, timings, plans,
  dependency versions, and upstream commit identifiers.
- Isolated PostgreSQL 18.3 synthetic smoke workload with DP and seeded GEQO.
- Locally compiled pg_hint_plan 1.8.1 for PostgreSQL 18; session-local loading.
- Database-backed SA pilot with directed tree verification, ignored-hint controls,
  repeated executions, and an exploratory estimated-cost fallback guard.
- Targeted primary-paper audit, checked bibliography, and a deterministic JOB catalog
  and 12-template stratified pilot manifest with SQL/input hashes.
- Canonical IMDB loaded into a separate database; all 12 selected JOB queries pass
  EXPLAIN-only preflight, including filtered-base/pair model extraction.
- Complete JOB CPU pilot, audited resume, portable raw evidence, independently
  verified clock-screened analysis, and reviewed PNG/SVG figures.

## Run locally

From this directory:

```sh
source .venv/bin/activate
python -m pytest -q
qopt sa-pilot --output results/sa-pilot-002
bash scripts/postgres.sh start
qopt db-pilot --output results/db-smoke-002
bash scripts/build_hint_plan.sh
qopt hinted-pilot --output results/hinted-pilot-003
bash scripts/postgres.sh stop
```

Each output directory must be new, preventing accidental result overwrites.
The database smoke command creates only the dedicated `qopt_smoke` schema.
The cluster lives in `.local/pgdata`, uses a private Unix socket, and does not listen on TCP.
Override `QOPT_DSN` to use a different explicitly chosen test database.
`scripts/postgres.sh` defaults to the PostgreSQL 18 Homebrew installation; set `PG_BIN`
for another installation. Initialization and server operation may require sandbox approval.

## Recreate the environment

Use Python 3.12, clone the pinned sources with `python3 scripts/fetch_sources.py`,
create `.venv`, and install `requirements.lock.txt` from this directory. For example:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
```

The current machine's Homebrew Python could not create a working environment, so
an isolated runtime was downloaded into `.python/`; the existing system installation
was left untouched. The installed QDBO package brings Qiskit and Ocean dependencies;
their presence does not mean QAOA or QPU experiments have been run.

## Current limitations

The SA pilot uses published numerical inputs, whose cardinality provenance still
needs verification. Its cost ratios compare against an exact optimum **for the
same multiplicative cardinality model and left-deep plan space**, not PostgreSQL
runtime. It is not the complete iterative QDBO algorithm and does not use a QPU.
The first three QDBO folders correspond to variants of the same JOB template.
They are a plumbing check, not independent workload coverage.

The original `db-pilot` remains a standalone GEQO check. The new `hinted-pilot`
extracts estimated filtered base/pair rows from the synthetic database, builds the
published BQM, solves it on a CPU, and executes the decoded plans through verified
hints. Every selected directed order and the baseline receives repeated measurements.
This is still a tiny synthetic workload; it is not a JOB execution experiment.
The guard decisions use only pre-execution planner costs, but their reported runtime
ratios reuse the measured plan medians; complete policy latency is not yet replayed.
The full JOB CPU execution campaign is complete with a durable task ledger and
explicit failure/timeout accounting. Its report flags post-hoc clock anomalies
consistent with overnight sleep and retains unavailable comparisons as unknown.
Measured executions use EXPLAIN ANALYZE with per-node timing; a controlled noise
and instrumentation study is needed before performance claims. Hybrid/QPU adapters,
other safeguards, and inferential analysis remain pending.

Read [the protocol](docs/protocol.md), [artifact audit](docs/artifact-audit.md),
and milestone reports [1](docs/milestone-01.md) and [2](docs/milestone-02.md)
before interpreting outputs.

Continue with the [literature audit](docs/literature-audit.md),
[JOB setup instructions](docs/job-setup.md), and
[selected workload](workloads/job/README.md). The review found prior work explicitly
studying quantum join-optimization stability; our narrower database-regression
contribution remains a hypothesis requiring real evidence and further literature review.
The [third milestone report](docs/milestone-03.md) records the earlier populated-data
preflight. Actual JOB CPU timings were collected under the
[frozen pilot protocol](docs/job-pilot-protocol.md); see the [completion record](docs/job-pilot-running.md),
[fourth milestone](docs/milestone-04.md), and [results](docs/pilot-001/README.md).
