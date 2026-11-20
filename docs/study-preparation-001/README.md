# Prospective CPU submission study

**Preparation only; no runtime results yet.**

Profile slots: 0/7450; policy slots: 0/1512.

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

## Limits

- Coverage-selected twelve templates on one shared host; load admission is not isolation.
- Unknown-outcome intervals are descriptive identification bounds, not confidence intervals.
- Fixed cached inputs/BQM: request timer is validated prepared-input warm-request service latency; queue wait and preprocessing are separate.
- Plain SELECT actual timed plan is not directly observed; logged pre/post fingerprints are checks, not a sampled execution tree.
- Six selected seeds and three policy blocks per query are dependent repeated requests, not independent workload samples.
- Five profile pairs characterize a preliminary noise diagnostic; retain raw same-plan ratios.
- No quantum hardware, full iterative QDBO, equal-compute fairness, or production-safety guarantee.
