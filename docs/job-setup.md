# JOB benchmark setup

This is a new PostgreSQL 18 study environment. QDBO's published environment uses
PostgreSQL 16.4; measurements from this machine will not be labelled exact reproduction.
All previous measured query timings remain from synthetic pilots.
The archive has been verified, all 21 tables loaded, and all 12 selected queries
passed populated-data EXPLAIN-only preflight with 291 input-estimation plans.
See `workloads/job/setup-receipt.json` for data hashes, row counts, and settings.

## Frozen workload selection

`workloads/job/catalog.json` describes 113 SQL instances and 33 templates from the
pinned JOB checkout. It records SQL hashes, table/alias/index mapping, explicit join
predicates, local filters, graph structure, and QDBO numerical-input hashes. All
canonical SQLs match QDBO's normalized SQL and alias order; all input dimensions match.
Every query graph is connected and uses supported cross-alias equality predicates.
Supplied QDBO cardinality provenance remains unverified despite these consistency checks.

`workloads/job/pilot.json` selects 12 templates with no observed performance input:

- Small, 4–8 aliases: 3a, 16a, 10a, 18a.
- Medium, 9–11 aliases: 21a, 23a, 25a, 13a.
- Large, 12–17 aliases: 26a, 29a, 24a, 28a.

Each template contributes its first alphabetical variant. Selection anchors the
minimum and maximum relation count of each stratum, then fills underrepresented
self-join/density groups, with seeded SHA256 ranking for ties. The initial structural
inspection found only three templates above 12 aliases, so the large boundary was
set at 12 before any runtime inspection. Final all-instance stratum sizes are 62/31/20;
first-variant template counts are 17/9/7. SQL graph density includes redundant explicit
equalities. This is a coverage pilot, not a probability sample representing all JOB
instances; equal allocation deliberately oversamples larger templates.

Rebuild deterministically:

```sh
.venv/bin/python scripts/build_job_manifest.py
```

The proposed 30 solves and five execution repetitions are pilot defaults, not a
power calculation. The proposed 60-second statement timeout is our resource cap,
not an inferred QDBO join-query setting. No main-experiment result has been selected.

## Dataset and database

The [pinned JOB README](https://github.com/gregrahn/join-order-benchmark) points to
the May 2013 IMDB CSV snapshot and warns that the separately generated Frozen Data
Set may produce unexpected query results. We use that documented archive endpoint:
`https://event.cwi.nl/da/job/imdb.tgz`. HTTP inspection on 2026-11-18 reported
1,263,193,115 bytes and last-modified 2024-12-19. This server timestamp does not
independently establish the content's historical snapshot date.

The local archive and CSVs are ignored by Git. `prepare_imdb.py` checks the observed
length, gzip/tar integrity, and the expected 21 CSV files; it copies only expected
regular members to fixed names and records SHA256 hashes. These are local integrity
receipts, not publisher-verified authenticity checksums.

```sh
bash scripts/download_imdb.sh
.venv/bin/python scripts/prepare_imdb.py extract
bash scripts/postgres.sh start
```

A dedicated empty `qopt_job` database has been created in the local cluster. To
recreate it on another machine:

```sh
/opt/homebrew/opt/postgresql@18/bin/createdb \
  -h /tmp/qopt-reliability-$(id -u) -p 55432 qopt_job
```

Then load and preflight:

```sh
.venv/bin/python scripts/prepare_imdb.py load
.venv/bin/python scripts/job_preflight.py --extract-models --output results/job-preflight-001
bash scripts/postgres.sh stop
```

Override `QOPT_JOB_DSN` for an explicitly selected alternative test database. The
loader refuses a nonempty public schema and never drops tables. Schema creation,
COPY, primary keys, pinned JOB foreign-key indexes, and ANALYZE are one transaction.
COPY uses the backslash CSV escape convention. Successful load receipt contains
actual per-table row counts, server version, archive hash, index policy, and elapsed
load time. Benchmark-table autovacuum is disabled and statistics are explicitly
analyzed and fingerprinted after loading. Do not run the real campaign until this receipt and populated-data
preflight exist. Keep CPU resources/cache policy/statistics fixed for the campaign.

## Verification performed before loading

All 12 selected queries were EXPLAIN-planned against the pinned schema inside a
transaction that was then rolled back. A quoted-string COPY check verified the CSV
escape setting; the public schema was empty after rollback. These are compatibility
checks, not populated-data baseline plans or query execution measurements.

`job_preflight.py` issues EXPLAIN without ANALYZE, records plans or explicit SQL
errors per query, checks SQL hashes, saves all server settings, and returns nonzero
if any query fails. It does not generate runtime samples. The current long-campaign
runner is still pending: need durable failure/timeout records, safe resumption,
verified hints for all accepted plan shapes, and phase
separation between optimizer solves and randomized executions.

With `--extract-models`, preflight also EXPLAINs each filtered base relation and
predicate-connected pair, saving the SQL, estimates, and plan evidence. All local
filters and pair predicates are retained, including parenthesized disjunctions.
It flags any actual predicate whose derived factor is exactly one: upstream QDBO's
parser would otherwise silently drop that edge. This representation remains an
approximation to multiway cardinalities. The reusable extractor was checked against
the known synthetic five-relation model without executing the query.
