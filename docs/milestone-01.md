# Milestone 1 — installed environment and working pilots

2026-11-18. All numbers below are infrastructure checks, not paper findings.

## Installed and validated

- Project-local CPython 3.12.16 and 83 installed packages including this project.
- Published QDBO installed editable from the pinned local checkout.
- Ocean/SA, Qiskit dependencies, psycopg, NumPy, SciPy, pandas, matplotlib, and pytest.
- Existing Homebrew PostgreSQL 18.3 used through a new isolated cluster.
- Four initial unit tests passed: prefix-selectivity cost calculation, exact small
  optimum, physical-plan identity independent of runtime noise, membership validity.

## SA cost-model pilot

30 seeds × three QDBO JOB input folders = 90 solves. Each solve uses ten reads and
200 sweeps/read, choosing the lowest-energy sample before upstream decoding.
The three inputs are JOB 1a, 1b, and 1c; they do not cover three independent templates.

| Input | Relations | BQM variables | Distinct canonical orders | Raw membership-valid solves | Median model-cost / optimum |
|---|---:|---:|---:|---:|---:|
| q1 | 5 | 57 | 8 | 27/30 | 1.891 |
| q2 | 5 | 48 | 6 | 22/30 | 1.011 |
| q3 | 5 | 48 | 5 | 30/30 | 1.026 |

Some low-budget solves have extreme model-cost ratios. These are a reason to inspect
energy/objective alignment, feasibility, decoding, and budget sensitivity. They are
**not measured runtime slowdowns or evidence about QPU behavior**. Membership validity
checks only relation counts and nesting, not all auxiliary-variable constraints.

Raw records, bitstrings, parameter settings, and environment metadata:
`results/sa-pilot-001/`. A factorial full-budget experiment remains pending.

## PostgreSQL synthetic smoke test

A deterministic 20,000-row fact table joined to four aliases of a 1,000-row dimension
table. Default dynamic programming versus GEQO configured with a deliberately small
search budget. Thirty seed settings per mode, five measured executions per setting,
randomized schedule, one warm-up per mode: 300 measured executions.

Default planning produced one physical plan; GEQO produced six. Pooled median execution
times were 3.037 ms and 2.8595 ms respectively. These sub-millisecond differences on
tiny correlated synthetic data are **not a general performance comparison**. This check
shows plan fingerprinting, seeded settings, repeated execution, raw EXPLAIN collection,
and manifest recording work. Recorded plans include all measured execution timings.

Raw records and settings: `results/db-smoke-001/`.

## Still pending

Full-paper literature review, paper-version reconciliation, pg_hint_plan, IMDB loading,
SA-plan execution in PostgreSQL, workload-level regression analysis, safeguards,
hybrid/QPU execution, and manuscript results. No paid services were called.
