# Milestone 05 — IEEE draft and completed baseline calibration

The IEEE conference first draft now includes two separate experiments: the
historical candidate pilot and the new baseline measurement calibration. Tables
are generated from their verified summaries and each source hash/revision is
recorded in `paper/results-provenance.json`. The generic IEEE format has not been
adapted to a selected venue. Author affiliation/email and venue/page limit remain
unspecified; no details have been invented.

## Calibration accounting and integrity

The new run includes the same twelve default baseline plans, TIMING ON,
TIMING OFF, and ordinary SELECT, with ten measured blocks per query/mode.
Selection and scheduling were fixed before collection. Source revision:
`edd06b4ed082dc72ff38925ce6a883c94f146472`.

| Phase | Successful | Timeout | Explicit skipped slots |
|---|---:|---:|---:|
| Warmup | 33 | 3 | 0 |
| Measured | 308 | 3 | 49 |

All 360 planned measured slots and 36 warmups are accounted for. The twelve
preflights match their historical baseline fingerprints. Profiled plans and
plain-query pre/post EXPLAIN fingerprints match; plain result digests remain
consistent within each query. The completed-run resume adds no tasks and changes
no payloads or attempts among all 408 records. Its task hash and source/config
identity are in [the evidence manifest](calibration-001/evidence.json).

There are **zero detected cross-clock anomalies** in this calibration. A
process-bound sleep assertion, paired UTC/monotonic times, load averages, and
local power/assertion snapshots were recorded. Private power diagnostics and the
local database remain excluded from the public artifact. Absence of a detected
anomaly does not prove absence of all environmental effects.

## Observed timing and remaining uncertainty

[The full table and evidence](calibration-001/README.md) separate server executor
times from plain SELECT client latency. Among ten queries with complete medians,
TIMING ON/OFF server-median ratios range from **0.602 to 1.086**. The mixed
ordering and remaining variation do not support a clean causal overhead estimate.
Plain SELECT times include planning, execution, transfer, and fetching. A
server/client subtraction would conflate different scopes. Unlike profiled
runs, plain SELECT's timed physical plan is not directly observed.

Plain-client CV ranges from **0.013 to 0.797**. Four complete queries have CV above
0.3 (`3a`, `16a`, `23a`, `24a`). Recorded one-minute load averages range from 3.71
to 8.90 on the ten-core host; this is a diagnostic, not a causal explanation.
The default plans for `18a` and `25a` still lack complete medians in all modes.
No timeout is converted to a numeric cap or hidden from coverage accounting.

These findings do not repair the original pilot or justify replacing its
baselines with measurements from this different run. Profiling sensitivity is
examined for default plans only, not all 485 candidate plans. The next evidence
gate is a resource-controlled candidate replay with paired baseline observations,
followed by the flat/directed hint comparison and actual end-to-end safeguard
replay. Calibration alone does not make the paper ready for submission.

## Deliverables and checks

The manuscript, bibliography, generated tables, and figure are in `paper/`.
`bash scripts/build_paper.sh` produces the PDF and self-contained Overleaf ZIP.
The calibration export contains CSV, compressed observation/EXPLAIN records,
summary, identity, completed-resume proof, and hashes. Verification recomputes
summaries, clocks, and profile fingerprints from exported JSONL evidence. The
original pilot bundle and its source identity remain unchanged.
