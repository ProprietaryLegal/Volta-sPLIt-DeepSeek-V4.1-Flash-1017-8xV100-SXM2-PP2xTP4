#!/bin/bash
# ab-arm-t1.sh LABEL [VAR=VAL ...]: ab-arm.sh plus a seeded T=1 run of the lever-1 prompt set (main, 11-03).
# Boots PROFILE (default serve-pp2.yaml) with the env, runs ab_tput.py (T=0, 3 x 1024), the greedy check
# unless SKIP_GREEDY=1, then ab_t1.py -> bench5/t1-<LABEL>.jsonl. Log: bench5/ab-<LABEL>-<ts>.log. Leaves the server up.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5 Q=${QUALITY_TOOLS}
REF=$B/run-pp2/quality-runs/20261103T002941Z-greedy-B5PP2-g1/references.jsonl
LABEL=$1; shift
LOG=$O/ab-$LABEL-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
log "AB $LABEL start env: $* PROFILE=${PROFILE:-serve-pp2.yaml}"
KEEP_LOCK=1 bash $O/stop-pp2.sh >> "$LOG" 2>&1; sleep 10
if ! env "$@" PROFILE=${PROFILE:-serve-pp2.yaml} bash $O/serve-pp2.sh >> "$LOG" 2>&1; then log "AB $LABEL BOOT FAILED: $(cat $O/serve-pp2.failed)"; exit 1; fi
log "AB $LABEL up"
source $O/arm-checks.sh
warm
/usr/bin/python3 -I $O/ab_tput.py http://127.0.0.1:18042 3 2>&1 | tee "$O/ab-$LABEL-tput.out" | tee -a "$LOG"
need_line "$O/ab-$LABEL-tput.out" "^TPUT TOTAL"
if [ "${SKIP_GREEDY:-0}" != 1 ]; then
  env -C "$Q" DS41_URL=http://127.0.0.1:18042 DS41_SERVED_NAME=deepseek-v4.1-flash DS41_QUALITY_RUNS="$B/run-pp2/quality-runs" \
    DS41_CLOCK_CONDITION="AB $LABEL" timeout 20m python3 -m quality.greedy check --label AB-$LABEL --reference "$REF" --runs 1 --nats 0.9 \
    > "$O/ab-$LABEL-greedy.out" 2>&1; g=$?
  log "AB $LABEL GREEDY rc=$g: $(/usr/bin/grep -E 'GREEDY|IDENTICAL|NEAR|DIFF|PASS|FAIL' "$O/ab-$LABEL-greedy.out" | tail -n 12 | tr '\n' ' ' | cut -c1-900)"
fi
/usr/bin/python3 -I $O/ab_t1.py http://127.0.0.1:18042 $O/lever1-t1-thinking-prompts.jsonl $O/t1-$LABEL.jsonl 2>&1 | tee "$O/ab-$LABEL-t1.out" | tee -a "$LOG"
need_line "$O/ab-$LABEL-t1.out" "^T1 TOTAL"
log "AB $LABEL done"
