# Reliability of stochastic join-order optimization

Measuring regression risk and evaluating safeguards in quantum-augmented query planning.

The full authorized CPU study is complete: **7,450 paired profile slots and
1,512 actual policy-request slots**, plus a separate 1,440-draw encoding diagnostic.
Start with [milestone 07](docs/milestone-07.md) and the
[completed report and portable evidence](docs/submission-study-001/README.md).
Failures, timeouts, unknown comparisons, six profile clock discrepancies and
substantial same-plan variation are explicit. This is a diagnostic CPU study,
not a quantum advantage, full-QDBO reproduction or production-safety claim.

The [completed IEEE research draft](paper/main.tex) integrates the actual results.
Build its PDF and self-contained Overleaf ZIP with `bash scripts/build_paper.sh`.
[Finalization status](docs/submission-readiness.md) distinguishes completed
experiments from pending author/advisor review and venue/affiliation details.
No paper has been submitted externally.

The [frozen study protocol](docs/submission-study-protocol.md),
[encoding evidence](docs/encoding-001/README.md), and
[preparation snapshot](docs/study-preparation-001/README.md) retain source identities.
The new measurements reuse 28/30 SA seeds per query (336 identical shared samples)
and the GEQO grid: this is controlled remeasurement, not independent replication.
Historical [pilot](docs/pilot-001/README.md) and
[calibration](docs/calibration-001/README.md) exports remain separate and unchanged.

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
The synthetic smoke guard reuses measured medians; actual policy latency is
separately measured in the completed JOB follow-up.
The full JOB CPU execution campaign is complete with a durable task ledger and
explicit failure/timeout accounting. Its report flags post-hoc clock anomalies
consistent with overnight sleep and retains unavailable comparisons as unknown.
The historical pilot uses EXPLAIN ANALYZE with per-node timing. The completed
follow-up uses paired TIMING OFF profiles and actual ordinary SELECT requests.
Shared-host noise still limits inference. QPU/full iterative QDBO evaluation and
production guarantees remain outside this CPU study.

Read [the protocol](docs/protocol.md), [artifact audit](docs/artifact-audit.md),
and milestone reports [1](docs/milestone-01.md) and [2](docs/milestone-02.md)
before interpreting outputs.

Continue with the [literature audit](docs/literature-audit.md),
[JOB setup instructions](docs/job-setup.md), and
[selected workload](workloads/job/README.md). The review found prior work explicitly
studying quantum join-optimization stability; the completed CPU diagnostic
contribution is positioned conservatively without a first-of-kind claim.
The [third milestone report](docs/milestone-03.md) records the earlier populated-data
preflight. Actual JOB CPU timings were collected under the
[frozen pilot protocol](docs/job-pilot-protocol.md); see the [completion record](docs/job-pilot-running.md),
[fourth milestone](docs/milestone-04.md), and [results](docs/pilot-001/README.md).
