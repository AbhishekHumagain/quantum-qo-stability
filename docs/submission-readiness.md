# From IEEE first draft to submission evidence

The IEEE conference first draft is in `paper/`. Generated PDF and Overleaf ZIP
are produced by `bash scripts/build_paper.sh`. Tables and the figure derive from
the independently verified pilot 001 bundle. No pending experiment is presented
as an observed result. The target venue, page limit, author affiliation, and email
have not yet been supplied; the draft uses Abhishek Humagain's name only.

## Evidence gates

| Gate | Current evidence | Required next evidence |
|---|---|---|
| Reproducible pilot | Complete; 720 trials and all 2,425 slots audited | Preserve historical evidence and source identity |
| Measurement validity | Clock anomalies and high baseline CV disclosed | Calibration 001 completed without detected clock anomalies; high CV persists, so resource-controlled candidate replay is still required |
| Plan-space comparability | Directed hints verified | Flat versus directed hints under matched seeds/inputs; report enforcement failures and physical choices |
| Runtime risk | Descriptive bounds with unknowns | New fixed-budget candidate execution under validated timing; template-aware uncertainty, no arbitrary significance claims |
| Safeguard utility | Offline guard rejects all SA candidates | Actually replay guarded and unguarded requests, charging all stages and retaining an always-default control |
| Objective/encoding validity | Full pinned hard-constraint reconstruction and 1,440-draw model-only grid complete | Integrate audited diagnostic; do not infer a JOB runtime cause or tune runtime conditions from it |
| Literature and novelty | Extended methods/evaluation and backward-reference review complete | Apply conservative claim boundaries; no priority or exhaustive-survey claim |
| Venue readiness | Generic IEEEtran conference draft | Venue-specific template, page limit, authorship/affiliation, disclosure and artifact policies |

## Calibration 001: frozen before new timing collection

Configuration: `config/measurement-calibration-v1.json`. All twelve existing
queries are included; there is no outcome-based subset or new solver draw.
Measure the default baseline under three modes: EXPLAIN ANALYZE TIMING ON,
EXPLAIN ANALYZE TIMING OFF, and ordinary SELECT. Keep the original PostgreSQL
settings/statistics and seed-zero default plan. Verify each baseline fingerprint
against the historical preflight before collecting new measurements.

One warmup per mode/session precedes ten blocks, each with seeded randomized
mode order. There are 360 planned measured slots, plus up to 36 initial warmups.
A first timeout/error stops that query/mode's remaining slots, which are explicitly
recorded. Other modes remain eligible. No global cap or silent redraw is used.
The experiment has a new SQLite ledger and cannot change pilot 001.

Profile server executor time and plain SELECT client time have different scopes.
Plain times include planning, execution, result transfer, and fetching. Plain
queries have pre/post EXPLAIN fingerprints, not a directly observed timed plan;
profiles have actual plan verification. Plain result digests must remain stable.
Do not subtract these timing scopes to estimate an overhead component.

The runner uses a process-bound macOS `caffeinate -i -s` assertion. It records
client monotonic and UTC elapsed clocks, per-attempt load, and local session
power/assertion snapshots. This does not override lid closure, prove absence of
thermal effects, or guarantee no resource contention. A preselected one-second
cross-clock discrepancy makes a complete median unavailable; all original rows
remain present. Ten repeats are calibration evidence, not a tail estimate.

Before reporting completion, audit all scheduled keys and profiles, check result
consistency, and verify a completed-run resume changes no task records. Then run:

```sh
.venv/bin/python scripts/analyze_measurement_calibration.py --run results/measurement-calibration-001 --output docs/calibration-001
.venv/bin/python scripts/analyze_measurement_calibration.py --verify-export docs/calibration-001
```

Only after reviewing this calibration should the next candidate replay protocol
be frozen. Do not collect an expanding set of experiments and select favorable
outcomes afterward. Calibration alone does not close the hint/safeguard gates.

## Calibration 001 completed

All 360 slots are recorded: 308 successful measurements, 3 measured timeouts,
and 49 explicit skips; warmups have 33 successes and 3 timeouts. No clock anomaly
was detected. All 408 tasks remained unchanged after completed-run resume.
[Results and portable evidence](calibration-001/README.md) are audited and exported.

This closes the initial baseline instrumentation comparison, not the measurement
validity gate. ON/OFF server-median ratios range from 0.602 to 1.086; four queries
have plain-client CV above 0.3. Resource load, cache state, and thermal/power
effects remain unresolved. Do not replace pilot candidate measurements using
new baseline times: measurements from different runs must not be combined into
new purportedly controlled ratios. Freeze a resource-controlled candidate replay
and paired baseline policy next, retaining the two unavailable queries.

## Prospective completion run

The remaining hint/profile/request evidence is executing under
[the frozen protocol](submission-study-protocol.md), after all optimizer outputs
were fixed. [Milestone 06](milestone-06.md) records completed encoding/literature
work and preflight counts. The 7,450 paired-profile sides and 1,512 actual requests
remain pending until the ledger is fully audited. Do not label these outcomes
complete or the paper ready for submission merely because the runner exists.
