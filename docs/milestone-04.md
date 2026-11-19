# Milestone 04 — completed JOB CPU pilot

The full frozen schedule is complete. This milestone moves beyond the earlier
synthetic checks and populated-data preflight to measured JOB execution evidence.
It is an exploratory engineering pilot; timing anomalies and substantial noise
prevent treating it as publication-ready performance evidence.

## Completed schedule and integrity

Twelve performance-blind selected templates received 30 CPU simulated-annealing
(SA) draws and 30 PostgreSQL GEQO planning seeds each. The original settings and
all completed measurements were preserved through the full run.

| Item | Observed count |
|---|---:|
| Optimizer trials | 720 |
| Verified proposals | 715 |
| Unenforced directed SA hints | 5 |
| Distinct physical plans, including baselines, summed across queries | 485 |
| Warmup attempts: successful / timeout | 418 / 67 |
| Scheduled measured execution slots | 2,425 |
| Actual measured attempts: successful / timeout | 2,042 / 14 |
| Remaining slots explicitly not run after timeout | 369 |

Every successful measured execution passed physical-plan fingerprint checks and,
where requested, directed-tree verification. All initial eight checkpoint records
remain byte-identical with attempt number one. The completed-run resume added
zero tasks and changed zero task payloads: 3,678 task records before and after.
The audit, no-op check, and environment verification are included in
[the evidence manifest](pilot-001/evidence.json). Installed package versions and
upstream tracked Python sources matched the initial environment at the postrun
check; the original runner did not enforce these on every resume.

The frozen measurement source is commit
`cdca2c90ca68ecdfc14c61ef5305161eacaf08b7`. Subsequent analysis and recovery changes
do not rewrite that identity or any measurement. To resume the historical run,
restore those five frozen source files from that revision in an isolated checkout
with the original inputs/environment. The newer runner intentionally rejects its
changed source identity against the old run.

## Timing validity and what can be learned

The runner executes `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` with default per-node
`TIMING ON`. PostgreSQL documents that node clock reads add profiling overhead,
which depends on both query and platform. The reported values are profiled executor
times, not ordinary SELECT latency; serialization/network costs are not measured.
See the [official PostgreSQL 18 EXPLAIN documentation](https://www.postgresql.org/docs/18/sql-explain.html),
checked for this report. No instrumentation effect has been causally measured here.

A postrun clock audit found 27 successful measured repeats across 23 plans whose
server execution time exceeded the enclosing client monotonic time by more than
one second: one repeat each in `13a` and `25a`, and 25 in `28a`. Five `28a`
warmups also had this discrepancy. The excess ranged from about 58 seconds to
59 minutes across warmups and measurements. This is consistent with system sleep
during the overnight campaign; no OS sleep trace was collected, so the cause is
not proven. A nominal 60-second statement timeout does not make these recorded
server durations valid latency samples.

The **post-hoc** quality screen makes an entire plan median unavailable if any of
its five measured repeats has `execution_ms > client_wall_ms + 1000`. It does not
substitute client time, drop individual repeats to form a smaller median, redraw
work, or modify saved measurements. All detected excesses are far above the
chosen one-second tolerance. Raw records and unscreened five-success medians
remain available in the evidence and per-plan summary. This screen cannot certify
that the remaining timings are unaffected. Warmup anomalies are disclosed but
are not used as measured samples or to change historical eligibility.

The default plans for `18a` and `25a` timed out, making all candidate/default
comparisons for those queries unknown. Among the ten completed baselines,
five-repeat CV ranges from 0.120 to 1.178. This is too noisy for interpreting
small differences or attaching significance to the descriptive thresholds.

After the screen, runtime ratios are available for 223/360 SA draws and 291/360
GEQO draws. With every planned draw retained and queries weighted equally, the
observed identification bounds for slowdown greater than 1.25x are:

| Solver | Confirmed slow / planned | Unknown / planned | Observed bounds |
|---|---:|---:|---:|
| CPU SA | 175 / 360 | 137 / 360 | 48.6%–86.7% |
| GEQO | 90 / 360 | 69 / 360 | 25.0%–44.2% |

These bounds describe this run's profiled, screened ratios and unknown outcomes.
They are neither confidence intervals nor estimates of general workload risk.
Before the post-hoc screen, the corresponding arithmetic bounds were
52.5%–86.7% and 26.4%–43.6%; those include timing-invalid profiles.
The [generated report](pilot-001/README.md) includes 1.1x and 2x sensitivity points,
per-query coverage, baseline CV, and separate optimizer timings.

Mean per-query pairwise physical-plan disagreement, conditional on verified
proposals, is 0.971 for SA and 0.588 for GEQO. Raw SA membership checks pass
206/360 draws, but check only relation-count/nesting constraints, not complete
auxiliary feasibility. Decoding includes unchanged upstream repair/postprocessing.
Neither statistic demonstrates a quantum effect.

## Safeguard interpretation

The pre-execution estimated-cost guard falls back for all 360 SA proposals and
134/360 GEQO proposals. For SA it degenerates to always using the cached default.
Its zero confirmed slowdowns on measurable baselines is therefore not evidence
of a useful optimization improvement. The guard is an offline diagnostic that
reuses physical-plan medians; end-to-end policy latency was not replayed. Unknown
baselines remain unknown even after fallback.

This CPU adaptation uses ten SA reads and 200 sweeps, fixed PostgreSQL estimated
base/pair inputs, and directed nested hints. The pinned QDBO helper emits flat
Leading hints that leave directions free. Plan spaces, cost representations, and
search budgets differ across methods. This is not a full iterative QDBO
reproduction, equal-compute comparison, QPU experiment, or quantum-hardware result.

## Evidence and next experimental gate

[PNG figure](pilot-001/pilot.png), [SVG figure](pilot-001/pilot.svg),
[summary](pilot-001/summary.json), and the [evidence manifest](pilot-001/evidence.json)
are committed. The figure was visually reviewed. The bundle contains 720 trial
rows, 2,910 warmup/measurement rows, raw SA samples, preflight and timed EXPLAIN
evidence, and file hashes. Independent verification recomputes plan fingerprints,
directed trees, screened medians, and per-query risk counts from exported files.
Database files, credentials, full session settings, local paths, and literature
PDFs are excluded.

After the historical no-op check, future-run recovery was hardened to retain a
crashed session's warmup as an abandoned attempt and rewarm under a new session
without treating interruption as a measured failure. A crash-during-warmup test
checks history retention, new warmup, successful remaining repeats, and subsequent
no-op resume. The historical pilot had no abandoned warmups.

The next experiment should use a machine kept awake throughout, log power/sleep
events and resource load, characterize baseline noise, and compare TIMING OFF
with ordinary query execution. Freeze a new run ID before collecting those
measurements. Also ablate flat versus directed hints, examine full encoding
constraint feasibility and penalties, and replay an actual guarded policy before
claiming safeguard utility. Strengthen future identity enforcement for installed
packages/upstream sources. Do not silently replace this pilot's evidence.
