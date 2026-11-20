# CPU model-only encoding diagnostic

All 1,440 sensitivity draws are complete. Every twelve-query configuration has
thirty seeds. This experiment changes penalty weight and sampling budget for
model diagnostics only; no winning setting is transferred into the frozen
runtime experiment.

| Penalty multiplier | Reads x sweeps | Hard-feasible /360 | Fraction |
|---|---:|---:|---:|
| 1 | 10 x 200 | 117 | 32.5% |
| 1 | 50 x 1000 | 276 | 76.7% |
| 4 | 10 x 200 | 351 | 97.5% |
| 4 | 50 x 1000 | 360 | 100.0% |

The independent audit reconstructs count, nesting, and one-way predicate
activation penalties, plus the separate slack objective, and checks energies
against saved sampler output. Inactive applicable predicates are permitted by
the pinned hard constraints and are not counted as violations. The historical
pilot has 114/360 samples satisfying these complete hard constraints, compared
with 206/360 satisfying only membership count/nesting. This does not imply that
the upstream decoder failed: it applies its own raw/connected readout and repair.

## Exhaustive synthetic witness

A post-hoc explanatory three-relation example uses base cardinalities 1,000,000,
all pair factors 0.01, threshold 0.63, and two decimal digits. All 4,096 binary
states were independently reconstructed. At the original hard-penalty weight 20,
minimum energy is 48.8369, below the minimum hard-feasible energy 87.7969. Thus
this particular encoded objective has an infeasible ground state. At multiplier
four, all minimum-energy states are hard-feasible with energy 87.7969.

The witness is synthetic, selected after the pilot, and does not establish a
causal explanation of any JOB runtime or a defect in the full iterative QDBO
system. Neither four times the penalty nor a higher sampling budget is a general
feasibility guarantee. Energies across differently weighted models are not directly
comparable; decoded multiplicative model cost is separate from PostgreSQL cost
and measured runtime.

## Reproducibility

Configuration: `config/encoding-sensitivity-v1.json`. Raw sample/constraint
records, summary and hashes are in this directory. Original literature PDFs and
local database files are excluded. Run:

```sh
.venv/bin/python scripts/verify_encoding_export.py docs/encoding-001
```

The prospective runtime study keeps the original 10-read/200-sweep, unmodified
penalty condition to avoid selecting a favorable setting using this sensitivity.
