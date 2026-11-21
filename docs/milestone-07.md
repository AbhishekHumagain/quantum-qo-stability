# Milestone 07 — completed CPU evidence and IEEE manuscript

The full frozen follow-up is complete and audited. The manuscript now reports
actual paired profiles and guarded requests, rather than treating preparation
or an offline guard diagnostic as execution evidence. Measurement source identity
is preserved at `82f2f61` (full revision in the public evidence).

## Completed schedule

- 360 SA samples feed both hint conditions; 1,080 proposals are not independent solves.
- SA flat/directed each verify 355/360; GEQO verifies 360/360; 745 union physical plans.
- 7,450 profile slots: 6,489 successes, 12 measured timeouts, 949 explicit skips.
- 1,512 actual policy slots: 1,378 successes, 3 timeouts, 119 skips, 12 invalid proposals.
- 912 warmups: 832 successes and 80 timeouts. No abandoned warmup attempts.
- All 11,350 task rows, payloads and attempts remain unchanged after completed-run resume.
  The 1,476 preparation checkpoint records also remain unchanged, all at attempt one.
- Both the analyzer export verification and the independent arithmetic verifier pass.
- The encoding diagnostic's 1,440 cached rows also remain unchanged after resume;
  its independent energy/constraint verifier passes.
- The isolated research PostgreSQL cluster is stopped; other local clusters are untouched.

[Complete report and portable evidence](submission-study-001/README.md),
[encoding diagnostic](encoding-001/README.md),
[frozen study protocol](submission-study-protocol.md).

## Observations and their limits

At slowdown threshold 1.25, query-weighted profile bounds are 58.6–86.9% for
flat SA, 63.3–91.4% for directed SA, and 25.0–41.7% for GEQO. Unknown counts are
102/360, 101/360, and 60/360. These descriptive identification bounds are not CIs
and do not account for timing noise within available ratios.

Actual service-latency bounds are 62.5–76.9% versus 29.6–38.0% for unguarded/
guarded flat SA, 62.0–78.7% versus 31.9–40.3% for directed SA, and 34.3–44.0%
versus 27.3–35.6% for GEQO. Guard fallback counts are 210/216, 216/216, and
87/216, respectively. Accepted candidates are not necessarily runtime wins.
Directed SA always falls back, yet 69 known service ratios exceed 1.25: plan
fallback does not remove fresh optimization/validation cost or execution noise.

Timing remains a substantive limitation. Six profile clock discrepancies on
10a are retained and screened. Fifty raw same-default-plan pairs range from
0.175 to 19.836; 27 lie outside [0.8, 1.25]. There are 104 post-attempt load
readings above the admission limit and about 3.78 hours of recorded admission
waiting. Admission and sleep inhibition did not establish isolation or eliminate
clock symptoms. No policy clock anomaly was detected; this does not prove low noise.

The two SA hint conditions share samples. Twenty-eight of thirty SA seeds/query
overlap the pilot, and all 336 shared samples reproduce exactly. GEQO seeds are
also reused. This is controlled remeasurement, not independent replication.

The model-only grid yields 117/360, 276/360, 351/360 and 360/360 hard-feasible
draws across the two penalties and budgets. The timed study retains its original
budget and penalty. A finite synthetic infeasible-ground-state witness is not a
JOB runtime causal explanation or a general statement about QDBO.

## Manuscript and remaining finalization

[IEEE manuscript source](../paper/main.tex),
[package instructions](../paper/README.md),
[readiness assessment](submission-readiness.md).
Run `bash scripts/build_paper.sh` to regenerate the reviewed PDF and self-contained
Overleaf ZIP. Generated tables, PNG/SVG, derived diagnostics and provenance are
included. Historical pilot/calibration exports remain separate and unchanged.

The finite authorized CPU experiments are complete. The manuscript is suitable
for author/advisor review as a diagnostic research draft; strong causal rankings,
population guarantees, QPU effects, full-QDBO reproduction, and production safety
are unsupported. Affiliation, publication email, target venue/page limit, final
author review, and venue-specific policy checks remain before external submission.
No paper has been submitted. The factual OpenAI Codex acknowledgment identifies
the scope of assistance and author responsibility.
