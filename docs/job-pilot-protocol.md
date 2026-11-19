# CPU JOB pilot v1 — fixed before timing collection

Configuration: `config/job-pilot-v1.json`. Workload: frozen `workloads/job/pilot.json`.
The prior milestone only collected EXPLAIN plans. This protocol adds real JOB timing.
It is an exploratory pilot, not a preregistered confirmatory experiment.

Each of 12 templates receives 30 independent CPU SA seeds on the published QDBO
BQM and 30 seeded PostgreSQL GEQO planning trials: 720 optimizer trials in total.
SA uses ten reads and 200 sweeps; it selects the lowest-energy read and uses unchanged
upstream decoding, including connected-order postprocessing. Raw membership validity
checks only count/nesting constraints, not full auxiliary feasibility. Save bits,
energy, raw-validity flag, selected order, and estimated model cost. Inputs and encoding
are fixed once per query so repeated sampling variability can be observed directly.
This is not full iterative QDBO, QAOA, or a quantum-hardware experiment.

The baseline uses PostgreSQL's normal DP/GEQO switch at 12 relations, GEQO seed 0;
GEQO trials force threshold 2 with seeds (i+1)/31. GEQO's effort/pool/generation
parameters are 5/0/0. SA hinted planning disables GEQO. All use 4 MB work_mem,
parallel execution off, JIT off, frozen statistics/indexes, and a 60-second statement
timeout. These methods differ in plan space, cost representation, and search budget;
their comparison does not isolate a quantum effect or establish equal-compute fairness.

Complete all optimizer trials before observing any execution timings. For each query,
deduplicate verified **physical** plan hashes across all trials and the baseline.
Perform one warmup per eligible distinct plan, then five deterministic randomized
blocks, each containing the baseline and every eligible distinct physical plan once.
This is a warmup policy, not a guarantee that all pages fit in cache. Save buffer
statistics and all measured plan trees. Verify directed hints and physical hashes
again on each completed execution. Unsupported/mismatched plans are explicit failures.

After the first timeout for a physical plan, retain that censored attempt and mark
its remaining scheduled repeats as not run after timeout. Other failed warmups or
executions similarly stop that plan's later repeats. Never replace a timeout by 60 s,
and never compute a five-repeat median from only the surviving successful runs.
Keep failed optimizer trials and unmeasurable/censored plans in workload accounting.
Risk bounds over unknown outcomes are not statistical confidence intervals.

The estimated-cost guard falls back on preflight failure or a candidate Total Cost
greater than the cached baseline estimate. Its diagnostic runtime calculation reuses
plan medians; it is **not an actually replayed end-to-end guarded execution policy**.
Separate encoding, sampling, decoding, validation, and guard-decision timings. The
encoding/baseline/model costs are shared preprocessing, not freshly measured per trial.
Thresholds 1.1x, 1.25x, and 2x are descriptive sensitivity points; interpret them
alongside measured baseline noise. Do not claim p99 or significant quantum effects.

SQLite task records are durable and single-owner. Finished successes and failures
are never automatically redrawn on resume. An interrupted running task receives a
new attempt while its interruption event is retained. Inputs, code, configuration,
binary, and statistics must match on resume; use another run for changed conditions.
A resumed timing session rewarms eligible plans before continuing and is identified
in each record. A fully completed run performs no additional warmups/executions.
Actual interruption times are not latency samples.

Run/resume with the same command:

```sh
bash scripts/postgres.sh start
.venv/bin/python scripts/run_job_pilot.py --output results/job-pilot-001
```

`--max-new-tasks N` stops cleanly after N additional durable tasks for verification.
Omit it to continue. `run.sqlite3` is authoritative; `tasks.jsonl` is an export.
Raw plans/timings stay under ignored `results/`; publish a reviewed summary separately.

## Completion and post-hoc quality audit

Pilot 001 completed the entire schedule; see [milestone 04](milestone-04.md).
The frozen runner uses `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` with default
`TIMING ON`. These are profiled executor times; node timing can substantially
affect execution, as described in the
[PostgreSQL 18 documentation](https://www.postgresql.org/docs/18/sql-explain.html).
TIMING OFF and plain-query comparisons require a separately frozen experiment.

A post-hoc quality screen flags successful measured profiles exceeding their
enclosing client monotonic clock by over 1,000 ms. Affected plan medians become
unavailable, with no substitution, redraw, or modification of historical tasks.
Raw medians are retained separately. This was not a preselected exclusion rule
and does not prove other profiles are free of sleep or instrumentation effects.

After the original completed-run no-op check, future-run recovery now preserves
orphan running warmups as abandoned interruption records. Only finished
failures/timeouts stop later repeats; a new session warms eligible plans again.
The historical run had no such orphan. The five frozen source files must match
the original revision for historical resumption; new source uses a new run ID.
