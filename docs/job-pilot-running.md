# JOB CPU pilot — completed

The full frozen schedule finished without a global budget cap: 720 optimizer
trials, 485 distinct physical plans across queries, and all 2,425 measured slots
accounted for. See [milestone 04](milestone-04.md) and the
[generated report](pilot-001/README.md) for actual results and limitations.

Integrity checks passed, and resuming the completed run added no tasks or changed
payloads. The original eight checkpoint records remain unchanged. Measurement
source identity remains `cdca2c90ca68ecdfc14c61ef5305161eacaf08b7`; later recovery
hardening applies to future runs. A new runner source identity must use a new
output directory. Restore the frozen source/environment in an isolated checkout
for any historical-run resumption.

The report retains timeouts and failures, and flags cross-clock timing anomalies
consistent with overnight sleep using an explicitly post-hoc quality screen.
This is low-budget CPU SA/GEQO with directed hints and profiled execution timing,
not quantum hardware, full iterative QDBO, or an end-to-end safeguard evaluation.
The selection manifest's execution-status field remains its historical snapshot.

Verification and reporting commands:

```sh
.venv/bin/python scripts/audit_job_run.py --run results/job-pilot-001
.venv/bin/python scripts/analyze_job_pilot.py --run results/job-pilot-001 --output docs/pilot-001 --plot
.venv/bin/python scripts/export_job_pilot.py --run results/job-pilot-001 --output docs/pilot-001
.venv/bin/python scripts/verify_pilot_export.py docs/pilot-001
```

The portable committed evidence can be verified without the local database using
the final command. Local receipts used by the exporter include the completed-run
resume check and postrun environment verification; database files stay local.
