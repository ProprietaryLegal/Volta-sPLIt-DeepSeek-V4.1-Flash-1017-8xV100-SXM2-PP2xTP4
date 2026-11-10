#!/bin/bash
# ab-arm.sh LABEL [VAR=VAL ...]: A/B arm on the the 8-GPU host PP2 server (main, 11-03). Stops the server (Engram kept), boots
# serve-pp2.yaml with the given env, runs ab_tput.py (3 x 1024 tokens) and the greedy check against the boot-7
# reference (--runs 1, near-tie 0.9 nats). Log: bench5/ab-<LABEL>-<ts>.log. Leaves the server up.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5 Q=${QUALITY_TOOLS}
REF=$B/run-pp2/quality-runs/20261103T002941Z-greedy-B5PP2-g1/references.jsonl
LABEL=$1; shift
LOG=$O/ab-$LABEL-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
log "AB $LABEL start env: $*"
KEEP_LOCK=1 bash $O/stop-pp2.sh >> "$LOG" 2>&1; sleep 10
if ! env "$@" PROFILE=${PROFILE:-serve-pp2.yaml} bash $O/serve-pp2.sh >> "$LOG" 2>&1; then log "AB $LABEL BOOT FAILED: $(cat $O/serve-pp2.failed)"; exit 1; fi
log "AB $LABEL up"
source $O/arm-checks.sh
warm
/usr/bin/python3 -I $O/ab_tput.py http://127.0.0.1:18042 3 2>&1 | tee "$O/ab-$LABEL-tput.out" | tee -a "$LOG"
need_line "$O/ab-$LABEL-tput.out" "^TPUT TOTAL"
env -C "$Q" DS41_URL=http://127.0.0.1:18042 DS41_SERVED_NAME=deepseek-v4.1-flash DS41_QUALITY_RUNS="$B/run-pp2/quality-runs" \
  DS41_CLOCK_CONDITION="AB $LABEL" timeout 20m python3 -m quality.greedy check --label AB-$LABEL --reference "$REF" --runs 1 --nats 0.9 \
  > "$O/ab-$LABEL-greedy.out" 2>&1; g=$?
log "AB $LABEL GREEDY rc=$g: $(/usr/bin/grep -E 'GREEDY|IDENTICAL|NEAR|DIFF|PASS|FAIL' "$O/ab-$LABEL-greedy.out" | tail -n 12 | tr '\n' ' ' | cut -c1-900)"
log "AB $LABEL done"
