# IEEE conference first draft for Overleaf

Upload the contents of `quantum-qo-ieee-draft.zip` as a new Overleaf project.
Select `main.tex` as the main document and pdfLaTeX as the compiler. IEEEtran and
its BibTeX style are standard TeX Live/Overleaf dependencies. Recompile from
scratch if citations do not resolve on the first pass.

Author: Abhishek Humagain only. Affiliation/email and target venue/page limit
have not been supplied; none were invented. This is generic IEEE conference
format, not a claim of compliance with a selected venue's submission rules.
There is no invented venue, copyright notice, funding statement, or coauthor.

The draft reports audited pilot 001, including explicit post-hoc exclusions,
unknown comparisons, high baseline noise, and the limits of CPU-only evidence.
It is a first research draft, not a submission-ready manuscript. See
`../docs/submission-readiness.md` for the remaining experimental gates.

Files:
- `main.tex`: manuscript.
- `references.bib`: cited primary sources and artifact.
- `tables/`: automatically generated pilot tables.
- `figures/pilot.png`: reviewed pilot figure.
- `results-provenance.json`: exact summary hash and measurement source revision.

From the repository root, regenerate assets with:

```sh
.venv/bin/python scripts/build_paper_assets.py
```

Compile with `latexmk -pdf main.tex` from this directory. The local helper
`scripts/build_paper.sh` uses a project-local IEEEtran cache if needed. Generated
build files and deliverable PDF/ZIP stay outside this source folder.
