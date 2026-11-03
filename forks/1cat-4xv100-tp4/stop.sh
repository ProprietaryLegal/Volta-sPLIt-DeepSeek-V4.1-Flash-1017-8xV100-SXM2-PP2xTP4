#!/usr/bin/env bash
# stop.sh [NAME]: stop the server group start.sh recorded in $FORK_HOME/run/NAME.pid (default serve-4card).
# Kills only that exact process group: TERM, then KILL after 60 s.
set -uo pipefail
FORK=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=configs/4card.env
source "$FORK/configs/4card.env"
NAME=${1:-${NAME:-serve-4card}} RUN=$FORK_HOME/run
[[ -s "$RUN/$NAME.pid" ]] || { echo "stop.sh: no $RUN/$NAME.pid"; exit 0; }
g=$(cat "$RUN/$NAME.pid")
if kill -0 -- "-$g" 2>/dev/null; then
  kill -TERM -- "-$g"
  for _ in $(seq 1 60); do kill -0 -- "-$g" 2>/dev/null || break; sleep 1; done
  kill -0 -- "-$g" 2>/dev/null && { kill -KILL -- "-$g"; echo "stop.sh: group $g needed KILL"; }
  echo "stop.sh: stopped group $g"
else
  echo "stop.sh: group $g not running"
fi
rm -f "$RUN/$NAME.pid" "$RUN/$NAME.ready"
