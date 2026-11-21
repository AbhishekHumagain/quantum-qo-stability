# Draft experimental protocol — 2026-11-18

Status: historical design notes, superseded for the completed CPU study by the
[frozen follow-up protocol](submission-study-protocol.md). [Milestone 07](milestone-07.md)
records all 7,450 profile and 1,512 policy slots, no-op resume and export checks,
and manuscript integration. The original questions below are retained as design
history, not a claim that every proposed experiment was performed.

## Questions

1. Under a fixed input and budget, how variable are returned join orders and physical plans?
2. How frequently and severely do their measured runtimes regress against PostgreSQL?
3. How do optimizer-input cardinalities and stochastic solver choices affect these outcomes?
4. Which safeguards reduce risk, and what additional optimization latency do they require?

Do not assume quantum methods are less reliable or that sampler variance dominates.
A negative result or a failure to reproduce an effect is a valid outcome.

## Units and controls

- Query template, query instance, optimizer solve, distinct physical plan, and execution
  repetition are separate units. JOB variants are clustered by template in inference.
- Start with JOB and CPU-based solvers. Add hybrid/QPU only with recorded service,
  hardware identifier, allocation, parameters, and timestamps. No credentials in outputs.
- Fix database version, statistics snapshot, indexes, settings, resources, and cache
  policy. PostgreSQL 18 smoke data is not a reproduction of a PostgreSQL 16 experiment.
- Save actual EXPLAIN trees and verify each enforced join tree. A hint being accepted
  syntactically is insufficient. Keep ignored hints, invalid samples, failed decodes,
  repairs, errors, and timeouts in denominators and log explicit failure categories.
- Separate encoding time, solver submission/queue/service time where available,
  decoding/repair, PostgreSQL planning, execution, and end-to-end wall time.
- Do not equate BQM energy, intermediate-cardinality cost, PostgreSQL estimated cost,
  or observed latency. Record each separately.

## Measurement design

Use at least 30 independent optimizer seeds per selected query/configuration for the
pilot, then size the main experiment using observed uncertainty and resource limits.
Choose the workload before examining the primary outcomes. Record failed solves.

Deduplicate physical plans for execution budgeting, but execute every selected plan
repeatedly. Start with five measured repetitions after warm-up; increase if the noise
pilot requires it. Randomize or interleave baseline and candidate executions in blocks.
Check plan hashes on every execution. Count duplicates when estimating the solver's
output distribution even if their performance measurements are shared.

Primary runtime ratio is candidate median execution time divided by baseline median
under the same execution policy. Define a practical regression threshold before the
main run, based on the noise pilot and an explicitly chosen minimum effect size.
Report risk at multiple preregistered slowdown thresholds; distinguish timeout censoring.

Report per-query results and query-weighted aggregate distributions. Use template-
clustered resampling for workload uncertainty and avoid treating 30 solves of one
query as 30 independent queries. p99 claims require enough independent tail evidence;
thirty solves alone do not justify them. Pairwise plan disagreement is the probability
that two distinct solves return different canonical plans, not an execution-noise metric.

Cardinality experiments need the same solver budgets and a clearly specified baseline
for each condition. True subplan cardinalities cannot generally be represented by a
single pairwise-selectivity matrix. Verify what the published encoding can accept
before describing a condition as an oracle-cardinality intervention. Treat artificial
perturbations as sensitivity experiments. Do not use evaluation runtimes for selection.

## Safeguards

Implement after enforcing candidate plans works:

1. Best-of-k: specify whether selection uses BQM energy or an estimated DB cost.
2. Cost guard: fall back to the baseline using only information available before execution.
3. Classical refinement: same refinement budget and starting-candidate policy across solvers.
4. Plan pinning: distinguish repeat stability from adaptation under workload/statistics changes.

Include optimization and validation overhead, fallback frequency, and unsuccessful calls.
Use equal-time comparisons alongside equal-sample comparisons. An estimated-cost guard
cannot guarantee actual-runtime safety.

## Next gates

1. Targeted methods/results audit completed in `literature-audit.md`, including
   direct stability overlap. Complete systematic citation-chain review remains pending.
2. Resolve the artifact cost-helper inconsistency and cardinality provenance.
3. DONE for the local PostgreSQL 18 pilot: version-matched pg_hint_plan and structural
   enforcement checks. Extend verification beyond supported scan/unary/inner-join shapes
   before accepting other plan shapes; do not silently skip unsupported nodes.
4. Choose the paper's PostgreSQL version, machine, IMDB snapshot, and storage budget.
5. A performance-blind 12-template JOB pilot manifest is prepared in `workloads/job`.
   The full pilot is complete. Resolve clock validity, baseline noise, and instrumentation
   effects in a separately frozen follow-up before specifying the main experiment.
6. Add quantum/hybrid adapters and safeguards; analyse and write only observed findings.

## Measurement gate after pilot 001

Use an awake host and record sleep/power and load events. Keep EXPLAIN ANALYZE
profile times distinct from plain SELECT latency. Compare TIMING OFF/plain query
execution; size repetitions from the resulting noise floor. Preserve pilot 001
unchanged, label its clock exclusion as post-hoc, and retain failures/unknowns in
all denominators. Ablate directed versus flat hints and replay actual safeguard
latency before interpreting the CPU adaptation as a system improvement.

## Completed CPU scope (November 21, 2026)

The finite frozen follow-up is complete. It uses median paired profile ratios,
not the historical ratio-of-separate-medians proposal above. Thresholds remain
descriptive, not calibrated noise margins. Shared-host timing variation and six
clock anomalies prevent strong causal rankings. The cost guard was actually
executed with cached inputs/BQM and fresh proposer/validation work; best-of-k,
classical refinement, pinning, oracle cardinalities and QPU experiments were not
performed. These are outside the completed manuscript's claims, not hidden results.

The SA hint conditions share samples and 28/30 seeds overlap the pilot; disclose
controlled remeasurement rather than independent replication. See the completed
[report](submission-study-001/README.md) and [readiness assessment](submission-readiness.md).
