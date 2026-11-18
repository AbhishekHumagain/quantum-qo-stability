# Milestone 2 — verified solver-to-database execution

2026-11-18. Local synthetic pilot; no quantum hardware or IMDB execution.

## Completed

Compiled pg_hint_plan 1.8.1, tag REL18_1_8_1, against the existing PostgreSQL 18.3.
The binary is copied into `.local/lib` and loaded per session via an absolute path.
No extension files were installed into Homebrew's shared directories, and no
preload setting was added to the server.

The `hinted-pilot` command now:

1. Extracts PostgreSQL estimated filtered base rows and pair-join rows for the
   five-relation synthetic query, deriving multiplicative factors from them.
2. Calls QDBO's unchanged BQM builder and decoder with CPU simulated annealing.
3. Translates each decoded order to an explicitly nested, directed Leading hint.
4. Verifies the complete join tree in preflight EXPLAIN; checks it again during every
   measured execution, and checks the physical plan hash against preflight.
5. Deduplicates identical directed orders, warms each candidate once, then executes
   each candidate and the default baseline five times in randomized blocks.
6. Records raw bitstrings, solve times, numerical inputs, SQL, full EXPLAIN trees,
   source/binary hashes, package versions, server settings, and upstream revisions.
7. Evaluates exploratory fallback decisions based only on pre-execution estimated
   PostgreSQL Total Cost. Performance ratios reuse measured plan medians.

Psycopg automatic prepared statements are disabled in this command to keep the
planning behavior explicit. The verifier deliberately supports a restricted set
of scan types, unary wrappers, and binary inner joins. Unsupported shapes fail closed.

## An enforcement failure found and retained

`results/hinted-pilot-001/` is an incomplete initial attempt. Its control requested
the directed order `d,c,b,a,f`, requiring cross products among dimension aliases.
The enabled extension reported the Leading hint as used but returned `f,a,b,c,d`.
Structural verification rejected it before candidate executions began. Diagnostic
inspection confirmed connected requests were enforced. The completed pilot uses
a connected control tree and checks that it is rejected when hinting is disabled,
then accepted when hinting is enabled. Both control EXPLAIN trees are saved.

This is evidence about enforcement in this local setup, not a general claim that
pg_hint_plan never supports cross products. The main campaign must log hint failures
as outcomes rather than simply terminating or dropping them. Current pilot execution
stops at the first failure; a resumable campaign runner remains pending.

## Completed run

Output: `results/hinted-pilot-002/`.

- 30 independent SA seeds; ten reads and 200 sweeps per solve.
- Six distinct directed candidate orders; one default baseline.
- 35 measured executions, five per order/baseline, following warm-up.
- All measured candidate trees verified, and all physical plan hashes matched preflight.
- Seven unit tests passed, including rejection of reversed join direction, unsafe
  aliases, unsupported shapes, and correct handling of bitmap scan children.

| Plan | Median execution time (ms) |
|---|---:|
| Default PostgreSQL | 3.139 |
| a,f,b,c,d | 4.166 |
| a,f,b,d,c | 4.131 |
| a,f,c,b,d | 4.945 |
| b,f,a,c,d | 4.354 |
| a,f,d,c,b | 4.366 |
| c,f,a,b,d | 5.546 |

The solve-frequency-weighted median candidate/default ratio was 1.327; the largest
candidate ratio was 1.767. These are descriptive values from one tiny, correlated
synthetic query, five repetitions, warm-cache measurements, and a small solver budget.
They are not general estimates of regression risk, and no significance claim is made.
Instrumentation overhead is material at these millisecond scales.

The estimated-cost guard fell back on all 30 solves, yielding a ratio of 1.0 by
construction when baseline medians are reused. This checks policy wiring only:
it neither establishes runtime safety nor measures full guarded end-to-end latency.
Model inputs are estimated pairwise factors, not exact multiway cardinalities.

## Next milestone

- Complete the primary-paper review and reconcile algorithm/measurement differences.
- Build a query manifest with SQL hashes, relation/alias mappings, template identifiers,
  and stratification so the JOB pilot spans independent templates.
- Select and verify the IMDB snapshot and loading procedure before a large download.
- Add structured failed-run records, timeouts, and resumption before benchmark campaigns.
- Run a stratified JOB pilot and use it to finalize repetitions and solver budgets.
