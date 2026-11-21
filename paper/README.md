# Completed IEEE research draft for Overleaf

Upload the contents of `quantum-qo-ieee-draft.zip` as a new Overleaf project.
Select `main.tex` and pdfLaTeX; recompile from scratch to resolve BibTeX citations.
IEEEtran and its bibliography style are standard Overleaf dependencies.

Sole author: Abhishek Humagain. Affiliation, publication email, target venue and
page limit have not been supplied; none are invented. This is generic IEEE
conference format, not a claim of venue compliance. Final author/advisor review
and venue-specific finalization remain before submission; no external submission
has occurred.

The draft integrates completed paired TIMING OFF profiles, actual guarded and
unguarded prepared-input warm requests, the model-only encoding diagnostic, and
historical pilot/calibration context. Seed reuse, censoring, six clock anomalies,
large same-plan noise, indirect plain-plan observation, and CPU-only scope remain
explicit. The guard is measured in the follow-up; the historical pilot guard
remains an offline diagnostic. The factual acknowledgment discloses OpenAI Codex
assistance beyond language editing.

- `main.tex`, `references.bib`: manuscript and bibliography.
- `tables/`: generated verified study, encoding, and historical tables.
- `figures/study.png`, `figures/study.svg`: main results figure.
- `derived-results.json`: hint comparison, noise and client residual diagnostics.
- `results-provenance.json`: evidence hashes, measurement revisions and no-op proofs.

From the repository root run `bash scripts/build_paper.sh`. The assets builder
runs both completed-study export checks and independent encoding verification,
in addition to historical pilot/calibration checks. It reads public exports,
not live database files. Measurement source identity is distinct from the later
manuscript/build revision. Deliverable PDF/ZIP and TeX build files remain outside
this source directory. See `../docs/submission-readiness.md` for finalization scope.
