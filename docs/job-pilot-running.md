# JOB CPU pilot — running

The complete frozen schedule is being executed as requested, without a global
execution-budget cap. Per-statement timeout and repeat-stopping rules remain those
in [the original protocol](job-pilot-protocol.md). This page records the handoff
status, not a live dashboard or a completed benchmark claim.

All 720 optimization trials have been recorded: 715 verified proposals and five
SA proposals whose requested directed trees were not enforced. These five failures
are retained. Eight query execution schedules have finished. The 12-relation `26a`
case is currently being measured, followed by `29a`, `24a`, and `28a`.

The original runner continues locally in `results/job-pilot-001/`. Its authoritative
SQLite task ledger commits successes, failures and timeout-related skipped repeats.
The first eight checkpoint records were verified unchanged after resume. Source
hashes match commit `cdca2c90ca68ecdfc14c61ef5305161eacaf08b7`. Do not edit the frozen
runner/inputs or launch another driver against this run while it is active.

For a current operational snapshot:

```sh
.venv/bin/python scripts/job_pilot_status.py results/job-pilot-001
```

A local completion follow-up checks this campaign and will finish the integrity
audit, completed-run no-op check, reviewed analysis/figure, portable evidence export,
CSV verification, milestone report and repository update after the schedule ends.
It stays quiet while normal progress continues and removes itself after completion.

Reporting/verification commands are prepared:

```sh
.venv/bin/python scripts/audit_job_run.py --run results/job-pilot-001
.venv/bin/python scripts/analyze_job_pilot.py --run results/job-pilot-001 --output docs/pilot-001 --plot
.venv/bin/python scripts/export_job_pilot.py --run results/job-pilot-001 --output docs/pilot-001
.venv/bin/python scripts/verify_pilot_export.py docs/pilot-001
```

The final report must distinguish successful profile timings from censored or
unavailable comparisons. This is low-budget CPU SA and GEQO on estimated inputs,
with directed hints. It is not a quantum-hardware experiment, a full QDBO reproduction,
or an actually replayed end-to-end safeguard evaluation. The original manifest's
execution-status field is a selection-time snapshot; the run ledger and subsequent
milestone report describe execution progress.
