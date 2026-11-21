# Prospective CPU submission study

**Complete paired-profile and actual-policy study.**

Profile slots: 7450/7450; policy slots: 1512/1512.

Seed provenance: 28 of 30 SA seeds per query overlap the pilot; all 336 shared raw samples reproduce exactly. Treat this as controlled remeasurement, not independent replication.

| Query | Both hints verified /30 | Changed physical plan | Flat cost lower | Flat cost equal | Flat cost higher |
|---|---:|---:|---:|---:|---:|---:|
| 10a | 30/30 | 13 | 13 | 17 | 0 |
| 13a | 30/30 | 26 | 26 | 4 | 0 |
| 16a | 28/30 | 24 | 24 | 4 | 0 |
| 18a | 29/30 | 26 | 24 | 5 | 0 |
| 21a | 29/30 | 22 | 10 | 17 | 2 |
| 23a | 30/30 | 30 | 30 | 0 | 0 |
| 24a | 30/30 | 27 | 27 | 3 | 0 |
| 25a | 30/30 | 20 | 20 | 10 | 0 |
| 26a | 29/30 | 28 | 25 | 4 | 0 |
| 28a | 30/30 | 28 | 28 | 2 | 0 |
| 29a | 30/30 | 20 | 20 | 10 | 0 |
| 3a | 30/30 | 28 | 28 | 2 | 0 |

## method_aggregate

| Method/arm | Threshold | Lower | Upper | Unknown |
|---|---:|---:|---:|---:|
| sa_flat | 1.1 | 59.4% | 87.8% | 102 |
| sa_flat | 1.25 | 58.6% | 86.9% | 102 |
| sa_flat | 2.0 | 54.7% | 83.1% | 102 |
| sa_directed | 1.1 | 64.4% | 92.5% | 101 |
| sa_directed | 1.25 | 63.3% | 91.4% | 101 |
| sa_directed | 2.0 | 59.7% | 87.8% | 101 |
| geqo | 1.1 | 27.2% | 43.9% | 60 |
| geqo | 1.25 | 25.0% | 41.7% | 60 |
| geqo | 2.0 | 16.1% | 32.8% | 60 |

## policy_aggregate

| Method/arm | Threshold | Lower | Upper | Unknown |
|---|---:|---:|---:|---:|
| default | 1.1 | 0.0% | 8.3% | 18 |
| default | 1.25 | 0.0% | 8.3% | 18 |
| default | 2.0 | 0.0% | 8.3% | 18 |
| sa_flat_unguarded | 1.1 | 64.4% | 78.7% | 31 |
| sa_flat_unguarded | 1.25 | 62.5% | 76.9% | 31 |
| sa_flat_unguarded | 2.0 | 55.6% | 69.9% | 31 |
| sa_flat_guarded | 1.1 | 41.2% | 49.5% | 18 |
| sa_flat_guarded | 1.25 | 29.6% | 38.0% | 18 |
| sa_flat_guarded | 2.0 | 18.5% | 26.9% | 18 |
| sa_directed_unguarded | 1.1 | 63.4% | 80.1% | 36 |
| sa_directed_unguarded | 1.25 | 62.0% | 78.7% | 36 |
| sa_directed_unguarded | 2.0 | 55.1% | 71.8% | 36 |
| sa_directed_guarded | 1.1 | 42.6% | 50.9% | 18 |
| sa_directed_guarded | 1.25 | 31.9% | 40.3% | 18 |
| sa_directed_guarded | 2.0 | 17.6% | 25.9% | 18 |
| geqo_unguarded | 1.1 | 40.3% | 50.0% | 21 |
| geqo_unguarded | 1.25 | 34.3% | 44.0% | 21 |
| geqo_unguarded | 2.0 | 18.1% | 27.8% | 21 |
| geqo_guarded | 1.1 | 43.5% | 51.9% | 18 |
| geqo_guarded | 1.25 | 27.3% | 35.6% | 18 |
| geqo_guarded | 2.0 | 13.0% | 21.3% | 18 |

## Limits

- Coverage-selected twelve templates on one shared host; load admission is not isolation.
- Unknown-outcome intervals are descriptive identification bounds, not confidence intervals.
- Fixed cached inputs/BQM: request timer is validated prepared-input warm-request service latency; queue wait and preprocessing are separate.
- Plain SELECT actual timed plan is not directly observed; logged pre/post fingerprints are checks, not a sampled execution tree.
- Six selected seeds and three policy blocks per query are dependent repeated requests, not independent workload samples.
- Five profile pairs characterize a preliminary noise diagnostic; retain raw same-plan ratios.
- No quantum hardware, full iterative QDBO, equal-compute fairness, or production-safety guarantee.
