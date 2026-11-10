#!/bin/bash
# ab-depth-arm-v2.sh LABEL [VAR=VAL ...]: v2 of ab-depth-arm.sh (harness1103, 11-03; advrev H3/H5). Boots PROFILE with
# the env and runs ab_depth.py (unchanged; already decode-only: streamed, first -> last token) at LENS (default
# 32768,65536), REPS (default 2), 512 tokens -> depth-<LABEL>.jsonl. Adds the H5 provenance line and the H3 activation
# count (ACT_GREP / ACT_EXPECT) to the arm log and pp2-go.state. Leaves the server up.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5
LABEL=$1; shift
source $O/arm-checks-v2.sh
split_args "$@"
mkdir -p "$OUT"
LOG=$OUT/ab-$LABEL-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
log "AB $LABEL start env: ${ARM_ENV[*]} PROFILE=${PROFILE:-serve-pp2.yaml} harness=v2-depth"
boot "${ARM_ENV[@]}"
log "AB $LABEL up; async: $(/usr/bin/grep -m1 -o "Asynchronous scheduling is [a-z]*" "$SERVE_LOG")"
prov
warm
$PY -I $O/ab_depth.py "$URL" "$LABEL" "$OUT/depth-$LABEL.jsonl" ${LENS:-32768,65536} ${REPS:-2} 512 2>&1 \
  | tee "$OUT/ab-$LABEL-depth.out" | tee -a "$LOG"
need_line "$OUT/ab-$LABEL-depth.out" "^DEPTH "
activation
log "AB $LABEL done"
