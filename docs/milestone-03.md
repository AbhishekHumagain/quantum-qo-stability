# Milestone 3 — literature audit and populated JOB setup

Completed 2026-11-18. **No JOB benchmark query executions or runtime results.**

## Research positioning

The [targeted audit](literature-audit.md) covers primary methods/results and explicitly
labels abstract-only screens and remaining review work. There are 12 bibliography
entries/versions and nine locally retained PDFs. PDF/source hashes and reading scopes
are recorded; original publications are not redistributed in the repository.

The most consequential finding is direct prior work on stability through structured
QAOA initialization. Connected-order fallback, multiple annealing batches, learned
optimizer regression protection, and join-order robustness are also established work.
Our candidate contribution is the controlled database-level distribution of repeated
solve outcomes, enforcement failures, runtime risk, and safeguard/optimization cost.
Priority and publication suitability remain unverified until broader review and results.

## Workload

The catalog covers 113 instances/33 templates; the frozen pilot covers 12 distinct
templates, with four per 4–8 / 9–11 / 12–17 relation stratum and six self-join queries.
Selection uses SQL structure only, anchors size extremes, balances structural groups,
and uses seeded ranking. It is a coverage pilot, not a representative probability sample.

All canonical SQLs, alias orders, and numerical-input dimensions match their pinned
QDBO counterparts. Supplied cardinalities are still not established as true values.
The numerical-factor file for one artifact query contains values above one; this
is tracked separately from consistency checks.

## Dataset and preflight

Downloaded the JOB-documented IMDB archive: 1,263,193,115 bytes. Verified gzip trailer,
archive structure and 21 expected CSVs, computed archive/file hashes, and loaded all
tables into the isolated `qopt_job` database. Created canonical primary-key and
foreign-key-column indexes; explicitly analyzed and fingerprinted statistics with
benchmark-table autovacuum disabled. No foreign-key constraints were added.

Archive SHA256:
`25f9d893c54f903366e0c263f88db0d429dbc2b159d4987ebc1e203242a7e988`.
This is a locally computed fingerprint, not a publisher-verified checksum.

The [setup receipt](../workloads/job/setup-receipt.json) records row counts for all
21 tables, CSV hashes, index policy, PostgreSQL version, and controlled settings.
The setup uses PostgreSQL 18.3 on this machine, rather than the paper's 16.4 environment.

All 12 selected JOB queries planned successfully. An additional 291 EXPLAIN-only
plans supplied filtered-base/predicate-connected-pair estimates. None of these
models has a predicate edge lost to QDBO's factor-equals-one sentinel in this snapshot.
These are estimated, rounded pairwise models; they are not exact multiway cardinalities.
Full raw evidence is local in `results/job-preflight-001/`.

## Validation and next step

Ten unit tests pass. Manifest regeneration is byte-identical. Schema-only transactional
checks, CSV escape handling, real data import, and populated-data preflight passed.
The reusable extractor was also checked against the known synthetic model.

Next implement a resumable JOB experiment runner with one record per solve/execution,
failure/timeout outcomes retained, verified physical plans, repeated interleaved
executions, and explicit baseline/guard overhead. Then execute the frozen pilot and
choose main-experiment budgets from its uncertainty. Existing timing measurements
remain synthetic pilot evidence; the JOB plans above are setup evidence only.
