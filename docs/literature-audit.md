# Literature audit — 2026-11-18

This is a targeted methods/results audit and novelty screen, not a systematic review.
Primary PDFs are retained locally with hashes in `references/sources.json`; published
files and extracted full text are excluded from Git. Page numbers below are PDF pages.
The bibliography is `references/refs.bib`. Local synthetic pilot numbers are not
included as evidence about prior work or JOB performance.

## Closest systems

**QDBO (PVLDB 2026), §§6–7, pp. 8–12.**
[Published paper](https://www.vldb.org/pvldb/vol19/p3606-liu.pdf).
The setup uses PostgreSQL 16.4, matched pg_hint_plan, an i9-9980XE/128-GB server,
and Advantage2_system1.7. Its hot-cache protocol runs three times, discards the
first, and averages the other two. Iteration settings are sampling/correction rounds,
not independent repetitions of a complete optimization trial. Defaults include 100
reads/round, beta 1.0, eta 0.01, and one/three-round variants. Table 1 reports **62
JOB execution improvements for three-round semantic mapping**, versus **7 end-to-end
improvements** in that configuration. Q2O-NL improves 18 JOB executions there.
Overhead is averaged across multiple runs (§7.2). §7.3 uses “stable” in comparisons
across instance sizes. I did not find a repeated-solve physical-plan distribution or
query-level regression-tail analysis in these sections. This is a scoped absence
finding. Its stated 60-second timeout is in the index-selection setup; do not silently
apply it to join ordering. **Consequence:** separate execution from end-to-end risk,
and identify our CPU BQM experiment as an adaptation, not full QDBO reproduction.

**Q2O demonstration (PVLDB 2025), §§2–4, pp. 2–4.**
[Paper](https://www.vldb.org/pvldb/vol18/p5439-liu.pdf).
The system integrates hybrid CQM/NL solving with PostgreSQL through join-order hints.
The encodings consume relation cardinalities and predicate factors, and the remaining
physical choices are made by PostgreSQL. Demonstration scenarios expose plans and
solver/planning/execution timings. The paper is a system demonstration, not a
comprehensive repeated-solve reliability study. **Consequence:** our hint pipeline
follows an existing integration pattern; integration itself is not our contribution.

**Q2O real-time abstract (arXiv:2601.12123v1, 2026), pp. 1–2.**
[Versioned source](https://arxiv.org/abs/2601.12123v1).
PostgreSQL 16.4; NL-based integration. It reports 31/113 JOB execution improvements;
the reported average reduction is restricted to those improved queries. Table I
decomposes end-to-end time for four examples. This is a two-page abstract and should
not be treated as the definitive full experimental specification. Its 31 count and
QDBO's 18 for Q2O-NL refer to different reports/configurations, not a reconciled
reproduction target. **Consequence:** cite versions, workload denominators, and
solver budgets alongside every comparison.

## Direct overlap with stability and safeguards

**Structured initialization for gate-based join ordering (arXiv:2608.20683, 2026),
§§3.3–5, pp. 5–6.** [Paper](https://arxiv.org/abs/2608.20683).
This work explicitly investigates optimization stability with SPIQ-initialized QAOA.
It studies three small three-/four-relation problems in noiseless statevector
simulation, reporting final-state cost probabilities, optimal-output probabilities,
and energy convergence. It also compares a connected-order fallback against raw
decoding. These probability distributions are not measured PostgreSQL runtime
regression distributions. **Consequence:** abandon “first quantum join-optimizer
stability study.” Distinguish initialization/solution-quality stability from repeated
complete solves, enforced physical plans, database timing, and end-to-end risk.
Connectivity repair is prior art and must be an explicitly labelled component or
ablation, not presented as a novel safeguard.

**Quantum-Inspired Digital Annealing (PVLDB 2023), §§5–6, pp. 7–10.**
[Paper](https://www.vldb.org/pvldb/vol17/p511-schonberger.pdf).
§6.1 evaluates DA and classical SA under a 60-second optimization budget, sweeps
multiple configurations, and reports the best configuration result per query.
Each experiment/configuration uses up to ten annealing runs, each with 100 outputs.
Readout includes a query-graph fallback avoiding cross products, with model-cost
selection. **Consequence:** repeated annealing runs, best-of-many selection, connected
fallback, and SA comparisons already exist. Our measurements must preserve all
independent solve outcomes, identify the selection policy, and include its cost.
Do not claim novelty from those ingredients alone.

**Hybrid QUBO/ECP-SQSS (arXiv:2606.16247, 2026), §§4–5.**
[Preprint](https://arxiv.org/abs/2606.16247).
The inspected preprint evaluates quantum/classical methods on ErgastF1 queries,
including selectivity/weight effects and elimination of Cartesian products. It uses
PostgreSQL 14.4-derived weights. The downloaded preprint has placeholder venue/DOI
metadata, so cite its arXiv identifier rather than invent publication details. A
November 2026 journal version was also checked at the publisher (below).
**Consequence:** include encoding/selectivity sensitivity and cross-product handling
in the related-work map; model-cost robustness alone is insufficient differentiation.

**Journal-version follow-up: Information 17(11), 1130, November 10, 2026,
§§5–6.** [Published version](https://doi.org/10.3390/info17111130).
The journal version has different author ordering from the inspected preprint and
explicitly distinguishes PostgreSQL-derived logical join-cost evaluation from a
separate end-to-end native-optimizer comparison. §§6.3 and 6.5 identify systematic
planning/query-execution comparison as future work. Its scope includes connected
inner joins and selectivity experiments, so neither database integration nor studying
selectivity effects is an unoccupied contribution. A full preprint/journal diff has
not been performed. Cite the published version for these scope statements.

## Database reliability context

**Eraser (PVLDB 2024), abstract/§§1–3.**
[Paper](https://www.vldb.org/pvldb/vol17/p926-zhu.pdf).
Eraser addresses learned-optimizer regressions through risk filtering and learned
prediction-quality assessment, with integration on PostgreSQL and Spark. It is more
than a simple “estimated cost exceeds baseline” check. **Consequence:** describe our
current estimated-cost guard as a simple baseline, never an Eraser reproduction.
Evaluate the utility/risk trade-off rather than claiming a runtime guarantee.

**Bao (arXiv:2004.03814; published SIGMOD 2021), §§1–3.**
[Inspected preprint](https://arxiv.org/abs/2004.03814).
Bao steers an existing optimizer using learned hint choices and Thompson sampling;
it already discusses tail behavior. **Consequence:** a meaningful comparison must
specify whether variability comes from training, online policy sampling, or changing
training data. Bao is deferred until these controls and version compatibility are
resolved. The full published version has not been audited in this milestone.

**JOB (PVLDB 2015), §§1–3.**
[Paper](https://www.vldb.org/pvldb/vol9/p204-leis.pdf).
JOB supplies 113 realistic queries from 33 structures over IMDB and separates the
effects of cardinality estimates, costing, and enumeration. It demonstrates why
estimator error must be controlled rather than attributing every poor plan to search.
**Consequence:** variants of one template are not independent workload samples;
an exact optimum under our model is not an actual-runtime optimum.

**Additional primary-source screens (abstracts only; full review pending).**
[Conformal verification, PVLDB 2025](https://www.vldb.org/pvldb/vol18/p2653-liu.pdf)
already investigates pre-execution verification and violation handling for learned
optimizers. [Robust Predicate Transfer, 2025](https://arxiv.org/abs/2502.15181)
studies robustness against join-order variation by changing execution in DuckDB,
including formal results for acyclic queries. Neither should be described as merely
average-speedup work. Our current PostgreSQL experiment changes candidate selection,
not the execution engine. Query-graph cycle rank in our manifest is a descriptive
feature; it does not establish whether those theoretical conditions apply.

## Working contribution and unresolved questions

Candidate contribution: a controlled, reproducible evaluation of repeated stochastic
join-order solves, physical-plan enforcement failures, and database-level regression
distributions, with budget-matched safeguards and explicit optimization overhead.
This is a research direction, not a verified priority claim.

Open items: complete citation-chain/backward/forward review; fully diff the November
hybrid-QUBO version; review conformal/RPT methods fully; verify supplied cardinality
provenance; reconcile artifact costing; distinguish iterative QDBO from our SA control;
and obtain real quantum/hybrid evidence before quantum-specific conclusions.

Searches on 2026-11-18 included combinations of “quantum join ordering stability
regression reproducibility,” paper titles, and “stochastic join ordering variance.”
These searches found direct stability overlap; they cannot prove absence of other work.
