#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
pg_bin="${PG_BIN:-/opt/homebrew/opt/postgresql@18/bin}"
socket_dir="/tmp/qopt-reliability-$(id -u)"
case "${1:-status}" in
  init)
    "$pg_bin/initdb" -D .local/pgdata --auth=trust --no-locale -E UTF8
    ;;
  start)
    mkdir -p "$socket_dir"
    chmod 700 "$socket_dir"
    "$pg_bin/pg_ctl" -D .local/pgdata -l .local/postgres.log -o "-k $socket_dir -p 55432 -h ''" start
    ;;
  stop) "$pg_bin/pg_ctl" -D .local/pgdata stop -m fast ;;
  status) "$pg_bin/pg_ctl" -D .local/pgdata status ;;
  *) echo 'Usage: bash scripts/postgres.sh {init|start|stop|status}' >&2; exit 2 ;;
esac
