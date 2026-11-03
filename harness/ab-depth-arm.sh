#!/bin/bash
# ab-depth-arm.sh LABEL [VAR=VAL ...]: boot PROFILE (default serve-v41pkg-pp2.yaml) with the env and run ab_depth.py
# (32K and 64K public prompts, 2 reps, 512 tokens, T=0) -> bench5/depth-<LABEL>.jsonl (main, 11-03, the owner "Try async at
# 32 64k tokens"). Log: bench5/ab-<LABEL>-<ts>.log. Leaves the server up.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5
LABEL=$1; shift
LOG=$O/ab-$LABEL-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
log "AB $LABEL start env: $* PROFILE=${PROFILE:-serve-v41pkg-pp2.yaml}"
KEEP_LOCK=1 bash $O/stop-pp2.sh >> "$LOG" 2>&1; sleep 10
if ! env "$@" PROFILE=${PROFILE:-serve-v41pkg-pp2.yaml} bash $O/serve-pp2.sh >> "$LOG" 2>&1; then log "AB $LABEL BOOT FAILED: $(cat $O/serve-pp2.failed)"; exit 1; fi
log "AB $LABEL up; async: $(/usr/bin/grep -m1 -o "Asynchronous scheduling is [a-z]*" $B/run-pp2/state/serve-pp2.log)"
source $O/arm-checks.sh
warm
/usr/bin/python3 -I $O/ab_depth.py http://127.0.0.1:18042 $LABEL $O/depth-$LABEL.jsonl ${LENS:-32768,65536} ${REPS:-2} 512 2>&1 | tee "$O/ab-$LABEL-depth.out" | tee -a "$LOG"
need_line "$O/ab-$LABEL-depth.out" "^DEPTH "
log "AB $LABEL done"
