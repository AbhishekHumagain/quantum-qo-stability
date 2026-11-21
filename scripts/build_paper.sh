#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python scripts/build_paper_assets.py
mkdir -p .local/paper-build output/pdf
cd paper
TEXINPUTS="../.local/tex//:${TEXINPUTS:-}" BSTINPUTS="../.local/tex//:${BSTINPUTS:-}" \
  latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=../.local/paper-build main.tex
cp ../.local/paper-build/main.pdf ../output/pdf/quantum-qo-ieee-draft.pdf
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
with ZipFile('../output/quantum-qo-ieee-draft.zip','w',ZIP_DEFLATED) as bundle:
    for path in sorted(Path('.').rglob('*')):
        if path.is_file() and (path.suffix in {'.tex','.bib','.png','.svg','.json','.md'}):
            bundle.write(path,path.as_posix())
PY
