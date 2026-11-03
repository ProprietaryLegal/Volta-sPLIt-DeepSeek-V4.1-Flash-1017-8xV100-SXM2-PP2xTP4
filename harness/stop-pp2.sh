#!/bin/bash
# stop-pp2.sh [NAME]: stop the 1Cat PP2 server group started by serve-pp2.sh and release the Engram lock.
# Kills only the exact process group recorded in run-pp2/state/<NAME>.pid and the exact lock pid in bench5/engram-lock.pid.
#   KEEP_LOCK=1 bash bench5/stop-pp2.sh   keeps Engram pinned for an immediate re-boot of the server
set -uo pipefail
B=${ENGINE_HOME} R=$B/run-pp2 O=$B/bench5 NAME=${1:-serve-pp2}
ts() { date -u +%FT%TZ; }
if [ -s "$R/state/$NAME.pid" ]; then
  g=$(cat "$R/state/$NAME.pid")
  if kill -0 -- "-$g" 2> /dev/null; then
    kill -TERM -- "-$g"
    for i in $(seq 1 60); do kill -0 -- "-$g" 2> /dev/null || break; sleep 1; done
    kill -0 -- "-$g" 2> /dev/null && kill -KILL -- "-$g"
    echo "$(ts) stopped group $g"
  else
    echo "$(ts) group $g not running"
  fi
fi
if [ "${KEEP_LOCK:-0}" != 1 ] && [ -s "$O/engram-lock.pid" ]; then
  p=$(cat "$O/engram-lock.pid")
  if sudo -n kill -0 "$p" 2> /dev/null && ps -o args= -p "$p" | /usr/bin/grep -q engram_lock.py; then
    sudo -n kill -TERM "$p" && echo "$(ts) Engram lock $p released"
  fi
  rm -f "$O/engram-lock.pid"
fi
for i in $(seq 1 8); do        # nvidia-smi at most once per 15 s on the 8-GPU host
  n=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | /usr/bin/grep -c .)
  [ "$n" = 0 ] && break; sleep 15
done
echo "$(ts) GPU compute processes: $n; MemAvailable $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo) GiB"
