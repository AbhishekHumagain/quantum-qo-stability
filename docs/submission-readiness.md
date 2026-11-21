# IEEE manuscript readiness

The completed research draft is in [paper/main.tex](../paper/main.tex).
`bash scripts/build_paper.sh` generates the PDF and self-contained Overleaf ZIP.
The completed CPU study is reported in [milestone 07](milestone-07.md).

## Evidence status

| Item | Status |
|---|---|
| Historical pilot | Complete, preserved with explicit post-hoc clock screen and offline guard scope |
| Baseline instrumentation calibration | Complete; timing scopes and remaining noise disclosed |
| Paired flat/directed hints | Complete; shared samples, enforcement failures, physical choices and profile summaries reported |
| Candidate/default profiles | All 7,450 slots accounted for; six clock anomalies and unknown ratios retained |
| Actual guarded/unguarded/default requests | All 1,512 slots accounted for; fallback frequency, service cost, failures and unknowns reported |
| Encoding validity/sensitivity | Complete 1,440-draw grid and finite synthetic witness; no runtime tuning transferred |
| Literature positioning | Targeted primary-source follow-up complete; no first-of-kind or exhaustive-survey claim |
| Durability and evidence | No-op resume preserves 11,350 study and 1,440 encoding rows; both study export checks and encoding verification pass |
| Manuscript | Actual results integrated; generated assets and source hashes in package; factual AI-assistance acknowledgment |
| Venue and author finalization | Pending affiliation, publication email, target venue/page limit, final author/advisor review and venue-specific policy checks |

## What the evidence supports

An auditable failure-aware CPU diagnostic study of a low-budget BQM/decoder
adaptation and seeded GEQO on twelve coverage-selected JOB templates. It shows
that hint semantics, feasibility, censoring, noise, and actual policy cost change
what can be concluded. It does not establish that any solver is causally more
reliable across workloads, or that a guard is production-safe.

The full frozen schedule is complete. Do not add runs to select favorable
outcomes or describe the partially reused seeds as independent replication.
Twenty-eight of thirty SA seeds/query overlap the pilot, with all 336 shared
bitstrings reproduced; GEQO seeds are reused. Guard requests have cached estimated
inputs/BQM, fresh proposer/selection/validation and ordinary SELECT, with queue
wait outside the service timer. Plain timed plans are checked indirectly through
pre/post fingerprints and result consistency, not directly observed.

## Submission boundary

This is a completed generic IEEEtran research draft, not a certification of
acceptance prospects or compliance with an unspecified venue. The shared-host
noise is substantial and six profile clock discrepancies remain; the manuscript
reports these limits rather than claiming validated causal rankings. A venue
requiring strong performance superiority or quantum hardware evidence would need
a different evidence scope. No external submission is authorized or performed.

The sole author must review the methods, code, numerical results, references,
AI-assistance acknowledgment and final manuscript, and supply affiliation/email
and a target venue. Then apply that venue's page limit, anonymity, artifact and
disclosure rules without inventing missing metadata. See
[IEEE submission notes](ieee-submission-notes.md).
