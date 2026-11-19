# Baseline measurement calibration v1

Completed descriptive calibration, separate from pilot 001.
ON/OFF values are server executor times; plain SELECT values are client times including planning and transfer.
A missing median means ten valid repetitions were unavailable. No timeout cap is substituted.
Measured outcomes: {'ok': 308, 'not_run_after_failure': 49, 'timeout': 3}. Warmups: {'ok': 33, 'timeout': 3}. Detected clock anomalies: 0.

| Query | ON median ms | OFF median ms | ON/OFF | Plain client ms | Plain CV |
|---|---:|---:|---:|---:|---:|
| 3a | 1854.754 | 1868.596 | 0.993 | 1868.585 | 0.714 |
| 16a | 196.519 | 202.173 | 0.972 | 208.308 | 0.390 |
| 10a | 8581.176 | 8472.541 | 1.013 | 8464.865 | 0.074 |
| 18a | unknown | unknown | unknown | unknown | unknown |
| 21a | 48.358 | 46.625 | 1.037 | 49.431 | 0.052 |
| 23a | 289.509 | 276.051 | 1.049 | 267.208 | 0.437 |
| 25a | unknown | unknown | unknown | unknown | unknown |
| 13a | 8361.852 | 8153.405 | 1.026 | 8143.926 | 0.118 |
| 26a | 33706.696 | 31905.021 | 1.056 | 31531.286 | 0.026 |
| 29a | 13.303 | 13.323 | 0.999 | 65.193 | 0.013 |
| 24a | 581.138 | 965.395 | 0.602 | 726.842 | 0.797 |
| 28a | 927.305 | 854.136 | 1.086 | 822.734 | 0.130 |

## Limits

- Ten repeats per mode, one machine, fixed query order, interleaved mode order; descriptive calibration only.
- Profile server executor time and plain SELECT client latency have different scopes; no subtraction is valid.
- Plain SELECT has pre/post EXPLAIN checks, not a directly observed timed physical plan.
- Keeping the machine awake does not eliminate load, cache, thermal, or power-state variation.
- No rerun of optimizer candidates, hint ablation, or actual end-to-end safeguard evaluation yet.
