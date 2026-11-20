# Milestone 06 — completed encoding diagnostic and prospective study in progress

The remaining evidence work is running under the separately frozen
[submission study protocol](submission-study-protocol.md). This milestone records
completed preparation/model evidence, not completed runtime or safeguard results.
Historical pilot and calibration records remain unchanged.

## Completed model and literature work

The [encoding diagnostic](encoding-001/README.md) audits all 360 historical raw
SA samples and completes a 1,440-draw penalty/budget grid over every selected
query. Full hard feasibility is 114/360 for the historical sample set; the earlier
206/360 count only covered membership count/nesting. Prospective sensitivity
feasibility is 117/360 at the original setting, 276/360 with a higher sampling
budget, 351/360 at four times the penalty with the original budget, and 360/360
with both changes. All configurations remain visible; none is selected as the
runtime method. Energies and hard-constraint components are independently
reconstructed from exported bitstrings.

An exhaustive, explicitly synthetic post-hoc witness shows that the pinned
three-relation objective can favor an infeasible ground state at its original
penalty. It does not identify the cause of a JOB runtime regression or evaluate
the full QDBO system. See the diagnostic for exact values and limitations.

The [literature follow-up](literature-review-followup.md) checks methods and
evaluation scope in conformal verification, Robust Predicate Transfer, quantum
reinforcement learning and higher-order encodings, alongside the earlier closest
systems. Runtime distributions, fallback, repair, stability and encoding validity
are established topics; the paper should make no first-of-kind claim. The
contribution remains the failure-aware CPU pipeline evaluation and its evidence.

## Prospective optimizer preparation complete

Source: `82f2f61` (full revision retained in the run evidence). Before any new query
timing, the driver recorded 360 new raw SA samples and 1,080 proposals: 360 paired
SA-flat, 360 paired SA-directed, and 360 seeded GEQO plans. Flat/directed conditions
share each SA sample; they are not 720 independent SA draws. Outcomes are 355
verified/5 unenforced proposals for each SA hint condition and 360 verified GEQO
proposals. All 1,476 preparation records remain byte-identical after resuming the
full schedule, with attempt number one.

Among 355 jointly verified hint pairs, 292 change physical fingerprint. Flat
estimated cost is lower in 275 pairs, equal in 78, and higher in two. This is an
EXPLAIN-based ablation, not measured runtime improvement. PostgreSQL's search
heuristics can return a higher estimated cost despite a less restrictive hint.
[Preparation evidence](study-preparation-001/README.md) is published separately
and explicitly contains no execution results.

## Timed work now running

The union contains 745 physical plans across queries, including baselines.
The full schedule has 7,450 paired-profile sides (five candidate/baseline pairs
per physical plan) and 1,512 actual policy-request slots, plus warmups. There is
no global budget cap or timing-driven plan selection. Timeouts stop later
attempts of the affected physical plan within its phase; explicit skipped slots
remain in the denominators.

The run uses TIMING OFF profiles, randomized candidate/default pair order,
process-bound sleep inhibition, load admission, paired clocks and load diagnostics.
The request phase freshly prepares proposals and actually executes the selected
ordinary SELECT, including the cost of guard/preflight/validation in the warm
request timer. Fixed inputs and BQM are prepared once. The phase is not simulated
by reusing old plan medians. Its actual results must be audited before publication.

The sole local worker owns `results/submission-study-001`. Do not modify frozen
source/config/inputs or start a duplicate. The queued completion workflow audits
the full saved ledger, checks no-op resume, exports/verifies evidence, updates
and visually reviews the IEEE manuscript, pushes focused commits authored and
committed solely by Abhishek Humagain, and stops PostgreSQL. User author details
and target venue/page limit remain unspecified; no affiliation is invented and
no external submission is authorized.
