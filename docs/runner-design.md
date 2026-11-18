# Durable pilot runner

The SQLite database under each run directory is authoritative. Task identity is
query/phase/solver/seed or query/physical-plan/repetition. A single-owner file lock
prevents concurrent drivers. SQLite FULL synchronous commits retain both successes
and failures. `events` preserves attempt starts, completions, and interrupted retries;
`tasks.jsonl` is a convenience export, not the recovery source.

Model extraction, baseline planning, hint controls, and encoding are shared per-query
tasks. The model, BQM serialization, full plans and input hashes are saved. Independent
SA and GEQO trial tasks are then completed for all queries before execution begins.
Trials that cannot be validated are retained and are not measured as their requested
plans. Physical plan hashes, rather than requested-order text, determine shared
execution measurements. Repeated solves still count repeatedly in the optimizer's
output distribution.

Each timing session warms eligible distinct plans, then performs the configured
randomized blocks. Successful timing records contain executor time, planner time,
client wall time, buffer counters, complete EXPLAIN, and the verified plan identity.
No timeout is converted to a completed 60-second observation. Stopping future repeats
after a timeout is an explicit resource policy, not proof of that plan's median runtime.
Incomplete plan medians remain unknown. Per-solver risk accounting keeps those unknowns
in all planned trials; resulting lower/upper bounds are descriptive, not confidence bounds.

The run identity freezes configuration, SQL selection, imported snapshot receipt,
runner/core/decoder-verifier source hashes, and hint binary hash. A fresh connection
also checks the imported statistics fingerprint. Changing code or inputs requires a
new run or restoring the original version; failed samples must not be redrawn under
the same identity. Session identifiers distinguish resumed timing windows. The
recorded query-deduplication design shares performance evidence; it does not simulate
each repeated draw as a new independent timing sample.

Initial live checkpoint verification retained eight records byte-for-byte with
attempt=1 after resume. Unit tests additionally cover interrupted task retry,
configuration mismatch, failed-task retention, and exclusive ownership. A final
`scripts/audit_job_run.py` checks every expected optimizer trial and execution slot,
recomputes physical identities, verifies successful hinted trees, and checks timeout
evidence for skipped repeats.

The estimated-cost guard is a diagnostic policy evaluated using shared medians.
Cached model/baseline/encoding work is reported separately from per-trial sampling,
decoding and planning, and from the incremental comparison. First-use encoding-task
time includes import/setup cost. None of these components is an independently
replayed guarded end-to-end measurement. A cost guard that falls back on every
candidate can be reliable but offers no measured performance benefit; report that
coverage/utility trade-off explicitly.
The current `validation_seconds` field times preflight EXPLAIN retrieval and hashing;
it ends before the separate tree-comparison step. Whole optimizer-task time includes
that comparison. Decode time also includes hint construction. Keep these clock scopes
explicit rather than labelling every component as pure solver or verification time.

## Planning restriction to ablate next

The pilot's nested Leading hints fix both join shape and outer/inner direction.
The pinned QDBO `jo_utils.generate_postgres_hint` instead emits a flat Leading list,
which permits direction choices. Thus using the published BQM/decoder does not make
our complete pipeline an exact reproduction. More restrictive physical direction
choices can themselves affect performance and plan counts. Keep this pilot unchanged;
compare flat and directed policies with a commutativity-aware logical-tree verifier
in a separately identified experiment before making claims about QDBO's behavior.
