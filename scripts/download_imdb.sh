#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
# Resume interrupted transfers. prepare_imdb.py separately checks length, gzip/tar
# validity, expected CSV inventory, and computes a local SHA256 receipt.
curl --fail --location --retry 2 --continue-at - \
  https://event.cwi.nl/da/job/imdb.tgz -o data/raw/imdb.tgz
