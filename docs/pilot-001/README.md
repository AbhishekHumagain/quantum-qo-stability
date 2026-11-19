# JOB CPU pilot v1

**Exploratory measured JOB results; no quantum hardware.**

Optimizer trials recorded: 720/720. Measured execution attempts: 2056; warmups: 485.
Pipeline state: complete. Optimizer outcomes: {'ok': 715, 'unverified_plan': 5}.

Post-hoc timing quality screen: 27 measured repeats across 23 plans have PostgreSQL execution time over one second above the enclosing client clock. Their plan medians are unavailable in the ratios below. All raw records are preserved; no repeat was redrawn.

| Query | Relations | Default median ms | Default CV | SA plans | GEQO plans | SA median ratio* | SA known/30 | GEQO median ratio* | GEQO known/30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3a | 4 | 586.385 | 0.483 | 5 | 1 | 1.142 | 30/30 | 1.000 | 30/30 |
| 16a | 8 | 156.930 | 1.178 | 27 | 5 | 10.977 | 19/30 | 1.000 | 30/30 |
| 10a | 7 | 5936.792 | 0.182 | 26 | 1 | 0.438 | 30/30 | 1.142 | 30/30 |
| 18a | 7 | unknown | unknown | 27 | 1 | unknown | 0/30 | unknown | 0/30 |
| 21a | 9 | 53.292 | 0.682 | 29 | 9 | 14.909 | 29/30 | 2.908 | 30/30 |
| 23a | 11 | 856.673 | 0.597 | 30 | 16 | 2.640 | 30/30 | 1.182 | 30/30 |
| 25a | 9 | unknown | unknown | 30 | 10 | unknown | 0/30 | unknown | 0/30 |
| 13a | 9 | 5022.193 | 0.246 | 30 | 2 | 4.115 | 7/30 | 1.000 | 30/30 |
| 26a | 12 | 23416.473 | 0.120 | 29 | 23 | 1.596 | 16/30 | 0.333 | 28/30 |
| 29a | 17 | 10.530 | 1.161 | 30 | 30 | 616.094 | 28/30 | 1.769 | 30/30 |
| 24a | 12 | 1469.642 | 0.840 | 30 | 27 | 5.534 | 30/30 | 1.089 | 30/30 |
| 28a | 14 | 1883.702 | 0.357 | 30 | 29 | 12.755 | 4/30 | 1.154 | 23/30 |

*Ratios use only plans with all five successful measured repetitions and a complete baseline. A post-hoc clock screen also excludes affected plan medians. These are conditional descriptions; failed/censored/timing-invalid plans remain unknown.

## Risk accounting

| Solver | Slowdown threshold | Observed lower bound | Observed upper bound | Offline guard lower | Offline guard upper |
|---|---:|---:|---:|---:|---:|
| sa | >1.1x | 53.6% | 91.7% | 0.0% | 16.7% |
| sa | >1.25x | 48.6% | 86.7% | 0.0% | 16.7% |
| sa | >2.0x | 42.5% | 80.6% | 0.0% | 16.7% |
| geqo | >1.1x | 35.3% | 54.4% | 15.0% | 32.8% |
| geqo | >1.25x | 25.0% | 44.2% | 6.1% | 23.9% |
| geqo | >2.0x | 12.8% | 31.9% | 1.9% | 19.7% |

Bounds retain unknown outcomes in all 30 planned trials/query and weight queries equally. They are identification bounds over the observed pilot, not confidence intervals or a population guarantee.
Guard decisions use pre-execution costs; their runtime diagnostics reuse measured plan medians. This is not a replayed end-to-end safeguard experiment.

## Timing components

| Query | SA optimizer task ms | SA sampling ms | SA decode/hint ms | SA preflight EXPLAIN/hash ms | GEQO optimizer task ms | SA guard comparison us |
|---|---:|---:|---:|---:|---:|---:|
| 3a | 1.219 | 0.764 | 0.083 | 0.246 | 0.947 | 0.208 |
| 16a | 4.999 | 3.621 | 0.129 | 1.061 | 10.898 | 0.208 |
| 10a | 3.137 | 2.272 | 0.124 | 0.615 | 9.123 | 0.208 |
| 18a | 4.148 | 2.709 | 0.193 | 0.885 | 8.815 | 0.292 |
| 21a | 7.797 | 5.016 | 0.187 | 2.418 | 13.045 | 0.292 |
| 23a | 14.323 | 8.088 | 0.231 | 5.834 | 17.177 | 0.458 |
| 25a | 7.352 | 4.975 | 0.167 | 2.021 | 13.344 | 0.250 |
| 13a | 6.082 | 4.193 | 0.152 | 1.539 | 12.478 | 0.250 |
| 26a | 20.602 | 10.249 | 0.273 | 9.748 | 18.214 | 0.520 |
| 29a | 462.300 | 28.140 | 0.481 | 433.462 | 28.484 | 0.667 |
| 24a | 28.221 | 11.137 | 0.284 | 16.372 | 19.760 | 0.562 |
| 28a | 63.601 | 17.675 | 0.364 | 45.194 | 23.662 | 0.500 |

Optimizer task time includes adapter and planning overhead. Model extraction, encoding, and baseline estimation were cached once/query; encoding-task wall time includes first-use imports. The guard comparison is only a Python comparison. The preflight EXPLAIN/hash timer ends before the subsequent structural-tree comparison; optimizer task time includes that comparison. None of these columns is total end-to-end guarded latency.

Timing interpretation follows the [PostgreSQL 18 EXPLAIN documentation](https://www.postgresql.org/docs/18/sql-explain.html): per-node clock reads can add substantial, plan-dependent profiling overhead. A TIMING OFF/plain-query ablation is still needed.

## Limits

- Twelve selected templates; one machine; low-budget CPU solvers; estimated pairwise inputs.
- No quantum, hybrid service, full iterative QDBO, or true-cardinality intervention.
- This pilot fixes directed nested join hints; the pinned QDBO helper emits flat Leading hints that leave directions free. These are different planning restrictions.
- Complete-only ratios require five successful repeats and no detected cross-clock anomaly; risk bounds retain unknowns.
- EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) uses default per-node TIMING ON. Profile overhead is plan/platform dependent; these are not plain SELECT latencies.
- Overnight cross-clock discrepancies are consistent with system sleep; the quality screen is post-hoc and cannot certify that other timings are unaffected. Raw reported medians remain available per plan.
- Offline guard diagnostics reuse shared medians and do not measure guarded end-to-end latency.
- Five repetitions characterize only a preliminary execution-noise floor; no p99 or significance claim.
