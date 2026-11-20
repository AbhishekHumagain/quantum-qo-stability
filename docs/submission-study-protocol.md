# Prospective submission study v1 — frozen before new timings

This run addresses the remaining measurement, hint, and actual-policy questions.
It cannot guarantee publication or eliminate shared-host variation. Historical
pilot and calibration records remain untouched. Do not combine their baselines
with new candidate times.

Configuration: `config/submission-study-v1.json`. The twelve original coverage
queries and fixed estimated base/pair inputs are reused. Thirty prospective SA
seeds (20261120 + index) each produce one raw sample with ten reads and 200
sweeps, then paired flat/directed hints. Thirty GEQO seeds use (index+1)/31.
All 360 SA samples, 720 SA hint proposals and 360 GEQO proposals must finish
before any query execution time is observed. BQM construction, raw constraint
components, exact energy reconstruction, decoder output and postprocessing are
recorded. This is CPU adaptation, not full QDBO or a quantum hardware evaluation.

## Hint ablation

Flat Leading fixes the left-deep prefix structure while allowing orientations;
directed nesting additionally fixes outer/inner choices. Verify the unordered
binary tree for flat hints and exact directed tree for directed hints. A changed
prefix is invalid in either condition. Use the same raw sample for each paired
hint condition, retain failures, and compare physical fingerprints and estimated
costs. Do not present a direction change as hint failure in the flat condition.
Hint-disabled and enabled controls are repeated per query.

## Paired physical-plan measurements

Deduplicate every verified physical plan, including baseline, per query. Warm
eligible plans once per session. Five deterministic randomized blocks contain
all physical-plan pairs; the baseline and candidate within each pair are also
randomized. Execute EXPLAIN ANALYZE with BUFFERS and TIMING OFF; verify actual
physical hash and the appropriate requested order after each success.

Every pair side is a separate durable task. A mixed-session pair is unavailable
for ratios after interruption; no finished side is redrawn. A median paired
ratio requires five complete, clock-valid same-session pairs. An identical
physical fingerprint has structural execution ratio one; its raw independent
same-plan pairs are retained as a noise diagnostic. Other ratios are the median
of paired server executor ratios, not ratios of old/new medians. Draws sharing
a physical plan share measurements but still retain their draw multiplicities.

Within this phase, a first timeout/error for a physical plan stops its later
attempts; skipped sides remain explicit and ratios become unknown. Query/method
coverage and identification bounds retain all 30 planned draws. Noise and
resource violations are reported, not silently screened or rerun. Five pairs
are descriptive evidence, not p99 or a population-confidence guarantee.

## Actual policy replay

Six prospective indices [0,5,10,15,20,25] are fixed before timing, with three
blocks of seven arms per query: default, SA-flat guarded/unguarded, SA-directed
guarded/unguarded, and GEQO guarded/unguarded. This is 1,512 planned request slots.
Randomize block and arm order deterministically. These are not 1,512 independent
query templates.

Each request freshly samples/decodes/plans its candidate. Guarded requests also
obtain a fresh default estimate and fall back before execution when validation
fails or estimated candidate cost exceeds default. They actually execute the
selected ordinary SELECT; no shared execution median stands in for the policy.
Default requests obtain their own preflight and execute default. Every arm pays
for its own pre/post plan validation. Guarded arms additionally pay for the
fresh default estimate. Record sampling/decoding/preflight/selection, actual
execution client time, result digest, and complete validated request latency.

The request timer includes these steps and validation but excludes resource
admission queue time, which is recorded separately. Fixed inputs and the BQM
are prepared once per query; preprocessing is reported separately, not charged
anew to every warm request. This is **validated prepared-input warm-request
latency**, not cold-start or uninstrumented production latency. Plain SELECT
has pre/post EXPLAIN checks; its timed physical tree is not directly observed.

Warm policy-eligible physical plans using ordinary SELECT in a separate phase.
Do not propagate profiling timeouts to plain policy execution. A first actual
policy-phase timeout/error stops later executions of that selected physical
plan. Later requests still perform their planning/guard decision and record
explicit unavailable execution slots; do not treat partial request time as
successful latency. Compare only complete outcomes and keep unknowns in every
planned denominator. Require result digests to agree within each query.

## Environmental controls and inference limits

Keep the host awake with a process-bound assertion. Admit a pair or request after
two resource checks, two seconds apart, with one-minute load <= 0.75 times the
logical CPU count. A high load waits without changing the schedule; all wait
intervals are logged. Record load before/after and paired UTC/monotonic elapsed
clocks. The one-second cross-clock tolerance is specified before collection.
Load is an admission proxy, not CPU isolation, reserved hardware, or causal proof
that contention is absent. Do not kill user applications or modify global power
settings. Keep power diagnostics local. Do not discard noisy observations merely
to obtain favorable CV or thresholds.

Report the twelve queries separately, query-weighted summaries, all statuses,
noise-control dispersion, fallback/acceptance frequencies, and the full request
overhead. Any intervals over unknown outcomes are identification bounds, not
confidence intervals. No claim of general quantum reliability, equal-compute
fairness, or superiority follows from these controls alone.

## Encoding diagnostic, separate from runtime method selection

`config/encoding-sensitivity-v1.json` fixes a model-only 2x2 grid: penalty
multipliers 1/4 and sampling budgets 10x200/50x1000, thirty seeds for every query.
Retain every configuration. Do not select a favorable configuration for the
runtime study. Audit count/nesting and one-way predicate implications separately
from objective slack; inactive applicable predicates are not hard violations.
Reconstruct energy independently. Include the explicitly synthetic, post-hoc
three-relation exhaustive witness to distinguish encoding penalties from search
budget; it is not a causal explanation of observed JOB performance.

## Completion

Use the same command/output for safe resume; source, inputs, settings, packages,
upstream tracked Python and hint binary are frozen. `--prepare-only` stops after
all prospective optimizer outputs and performs no timed query execution. After
the full schedule, verify completed-run resume adds no tasks or changed payloads.
Export portable evidence, recompute summaries independently, update the IEEE
manuscript only with audited observations, and inspect its rendered pages. Sole
author and committer remain Abhishek Humagain. Stop the isolated cluster on
completion. Submission itself needs venue/author details and explicit instruction.
