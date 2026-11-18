# Initial artifact audit

Inspected on 2026-11-18. Complete-paper review is pending; novelty is unverified.

| Artifact | Pinned commit | Role |
|---|---|---|
| [QDBO](https://github.com/ihanwen99/VLDB26-QDBO) | `2c8a3b3429634eb5d810b98f343b8729555c24b1` | Published BQM builder, decoder, numerical workload inputs |
| [Q2O](https://github.com/ihanwen99/Q2O) | `1b4b1cd2f1f698cce85c5cb9b94286c681555711` | Reference implementation; downloaded, not executed |
| [JOB](https://github.com/gregrahn/join-order-benchmark) | `a39603662e023e449cb2121997a5034df9e02ebf` | Canonical queries/schema; downloaded, no IMDB data yet |
| [pg_hint_plan](https://github.com/ossc-db/pg_hint_plan/releases/tag/REL18_1_8_1) | `9a3f851e1993d6728a9707956dabfcf22cc35b38` | Version 1.8.1, matching PostgreSQL 18 |

## Findings from code inspection

- QDBO includes all 113 JOB input folders, so an encoding pilot can run without
  downloading IMDB. This does not establish where the supplied cardinalities originated.
- `bqm_solver_execution.build_bqm` calls the published Fujitsu-named left-deep
  builder with threshold 0.63, precision 2, and penalty scaling 2. Our adapter calls
  this function unchanged and samples the resulting BQM on a CPU.
- `helpers.read_out` compares raw and connectivity-postprocessed orders using a
  multiplicative intermediate-size model. The cost excludes the final join and
  canonicalizes the first pair. Our independent oracle implements that objective.
- The decoder returns an integer-truncated cost. We preserve floating-point cost
  separately and check agreement to within its truncation tolerance.
- `jo_utils.compute_db_cost` initializes `involved_relations` with the first relation
  and does not update it inside the join loop. Thus subsequent selectivity products
  omit later prefix relations. The same helper includes the final join, unlike the
  decoder helper. The actual benchmark pipeline uses this helper in its NL/CQM paths.
  This is a source-level inconsistency requiring investigation; it does not by itself
  demonstrate that the published runtime results are wrong. Upstream remains unchanged.
- Q1 inputs contain values greater than one in the file called `selectivities.json`.
  Treat these as supplied multiplicative factors until their semantics are verified.
- Upstream is GPL-3.0-or-later. Preserve attribution/license and review distribution
  obligations before releasing any combined artifact. Q2O licensing needs inspection.
- During milestone 2, a directed Leading hint requesting a dimension-only prefix
  (cross products) was reported as used by pg_hint_plan, while the observed tree
  differed. The verifier rejected it before execution. The same module successfully
  enforced connected left-deep trees. Retain actual-tree validation even when hint
  diagnostics claim success; do not assume arbitrary cross-product orders are enforceable.

## Primary papers to review next

- QDBO: [DOI 10.14778/3836663.3836712](https://doi.org/10.14778/3836663.3836712).
- Q2O demonstration: [PVLDB paper](https://www.vldb.org/pvldb/vol18/p5439-liu.pdf).
- Q2O real-time discussion: [arXiv 2601.12123](https://arxiv.org/abs/2601.12123).

Extract exact versions, datasets, hardware, planner settings, seed policies, repetition
units, timeout treatment, cost definitions, and mitigation policies. Do not repeat the
Claude export's 59/62 or 31-query counts without checking the corresponding version.
