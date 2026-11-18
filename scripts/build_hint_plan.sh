#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pg_config="${PG_CONFIG:-/opt/homebrew/opt/postgresql@18/bin/pg_config}"
make -C vendor/pg_hint_plan PG_CONFIG="$pg_config"
mkdir -p .local/lib
if [[ -f vendor/pg_hint_plan/pg_hint_plan.dylib ]]; then
  cp vendor/pg_hint_plan/pg_hint_plan.dylib .local/lib/
else
  cp vendor/pg_hint_plan/pg_hint_plan.so .local/lib/
fi
# Session-local LOAD uses this binary directly; no system-wide make install.
