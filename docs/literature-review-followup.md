# Literature follow-up — 2026-11-19

This extends the targeted audit in `literature-audit.md` with primary-source
methods/evaluation checks and backward-reference screening. It is not an
exhaustive systematic review and cannot establish a priority claim. The final
paper should claim an auditable CPU diagnostic/evaluation contribution, not a
new safeguard algorithm or the first study of stability, runtime distributions,
constraint penalties, or end-to-end query optimization.

## Search and scope

Searches combined quantum join ordering with stability, regression risk,
reliability, and reproducibility; exact-title searches covered conformal learned
optimizer verification, robustness, and hint semantics. Backward screening used
the reference lists of QDBO, structured initialization, and the newer HUBO paper.
Inclusion here requires a directly relevant primary paper or official artifact;
secondary search summaries are discovery aids only. The November journal hybrid
version remains the preferred citation over its differently ordered preprint.
No claim is made that every forward citation was retrieved.

## Expanded closest-work checks

**Conformal verification (PVLDB 2025), §§3–6, especially §6.1.**
[Primary paper](https://www.vldb.org/pvldb/vol18/p2653-liu.pdf).
Calibration nonconformity scores support latency bounds, runtime verification,
fallback, and guided search; the evaluation integrates Balsa, Lero, and RTOS.
Repeated calibration/test sampling is already studied. Its guarantees depend
on the stated calibration/distribution assumptions, not arbitrary per-query
runtime safety. Our unknown-outcome identification bounds are not conformal
coverage guarantees, and our uncalibrated PostgreSQL-cost guard is a simpler
baseline. **Consequence:** do not market fallback or verification as new, and
do not call descriptive coverage bounds a reliability guarantee.

**Robust Predicate Transfer (SIGMOD/PACMMOD 2025), §§3–5.**
[Versioned full text](https://arxiv.org/html/2502.15181v2).
The study already samples many random left-deep and bushy plans and reports
per-query runtime distributions normalized by the default optimizer, with
explicit timeouts. Its DuckDB execution changes use LargestRoot and SafeSubjoin,
with an acyclic-query robustness result and separate cyclic evaluations.
**Consequence:** runtime-distribution measurement is prior art. Our distinction
is repeated outputs of a specified stochastic planner pipeline, matched hint
orientations, enforcement accounting, and actually charged guard requests in
PostgreSQL. We do not implement RPT or compare engines as interchangeable
baselines. Graph cycle rank does not establish alpha-acyclicity.

**Hype or Heuristic? (IEEE QCE 2024), §§IV–V.**
[Versioned full text](https://arxiv.org/html/2405.07770v1).
The work uses quantum reinforcement learning for bushy plans, simulation-based
quantum evaluation, cross-validation, and model-cost metrics. It explicitly
separates model cost from actual query execution time and discusses quantum
resource and noise limits. **Consequence:** use its published IEEE citation,
recognize prior careful quantum/classical comparisons, and distinguish our
annealing pipeline from learned policy training and circuit noise experiments.

**Higher-order join-order encoding (2025 preprint), §§3–5 and evaluation appendix.**
[Versioned full text](https://arxiv.org/html/2502.00362v1).
The paper models precise/heuristic objectives with HUBO formulations and explicit
validity constraints, relating formulations to classical enumeration under its
assumptions. Its analysis reinforces that an encoding's objective and its
constraint penalty are separate from observed database latency.
**Consequence:** our reconstructed pinned-QUBO penalties and finite synthetic
witness diagnose an adaptation; they do not disprove other formulations or show
that a quantum solver caused a JOB regression. The preprint is not assigned an
invented journal venue.

**QDBO / structured initialization / digital annealing recheck.**
Use the original hashed primary PDFs and artifact source already audited.
QDBO's iterative mapping/correction and quantum service remain outside this CPU
adaptation. Structured initialization explicitly studies optimization stability
and connectivity fallback. Digital annealing already uses probabilistic repeated
runs and readout repair. The pinned helper emits flat Leading lists; our previous
directed nesting is an integration ablation, not equivalent reproduction.
**Consequence:** the new paired flat/directed experiment must share raw samples;
encoding sensitivity must not silently tune the runtime condition.

## Claim boundary for the manuscript revision

The intended result is a reproducible, failure-aware CPU evaluation showing how
constraint feasibility, hint orientation, physical-plan variability, censoring,
and measured policy overhead affect conclusions. Novelty is in the documented
combination and evidence, subject to reviewer assessment; no first-of-kind claim
is needed. State negative or inconclusive findings directly. Keep statistical
identification bounds separate from measurement noise and confidence guarantees.

## Remaining scope limits

The exact new experiment must be audited before its findings enter the paper.
A QPU comparison, full iterative QDBO reproduction, production deployment study,
and a systematic all-literature survey remain outside the CPU paper's claims.
The publisher endpoint for the older co-design paper was access-restricted in
this follow-up; it was a reference-chain screen, not a newly completed full-text
audit. Target-venue requirements and author details are still needed for actual
submission. A term-paper/research draft can be completed with these limits stated.
