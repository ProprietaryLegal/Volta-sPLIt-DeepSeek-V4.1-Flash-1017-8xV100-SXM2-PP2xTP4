#!/bin/bash
# ab-arm-t1-v2.sh LABEL [VAR=VAL ...]: v2 of ab-arm-t1.sh (harness1103, 11-03; advrev H1/H2/H3/H5). Same arm flow:
# stop (Engram kept), boot PROFILE (default serve-pp2.yaml) with the env, warm-up, T=0 3 x 1024, gate, seeded
# T=1 run of the lever-1 prompt set. Leaves the server up. Differences from v1:
#   - T0 and T1 run through ab_t1_v2.py (streamed): every line also carries ttft, dec_s, dec-ms/round (decode-only) and
#     toksha (sha of the generated token ids); score with pairs_arms_v2.py --metric dec, then win3.py.
#   - gate: GATE=auto|approved|legacy|both|none (arm-checks-v2.sh gate_v2; SKIP_GREEDY=1 = GATE=none, as v1).
#   - H5 provenance line (v41k.so sha16 + build dir + deployed vllm .py digest) and H3 activation count (ACT_GREP,
#     ACT_EXPECT=on|off|any) in the arm log and pp2-go.state.
#   - SKIP_T1=1 stops after T0 + gate (the ab-arm.sh flow).
#   - Outputs: ab-<LABEL>-<ts>.log, ab-<LABEL>-{warm,tput,t1,greedy,neartie}.out, tput-v2-<LABEL>.jsonl,
#     t1v2-<LABEL>.jsonl (token ids + text sha + text; the v1 t1-<LABEL>.jsonl name is never written).
#   - A label already used by a v1 arm (ab-<LABEL>-tput.out without dec_s) is refused: v1 and v2 arms never pair.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5
LABEL=$1; shift
source $O/arm-checks-v2.sh
split_args "$@"
[ "${SKIP_GREEDY:-0}" = 1 ] && GATE=none
mkdir -p "$OUT"
LOG=$OUT/ab-$LABEL-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
if [ -s "$OUT/ab-$LABEL-tput.out" ] && ! /usr/bin/grep -q " dec_s " "$OUT/ab-$LABEL-tput.out"; then
  log "AB $LABEL REFUSED: label already used by a v1 arm (ab-$LABEL-tput.out); pick a new label"; exit 1
fi
log "AB $LABEL start env: ${ARM_ENV[*]} PROFILE=${PROFILE:-serve-pp2.yaml} harness=v2 gate=$(gate_mode) act=${ACT_EXPECT:-any}${ACT_GREP:+ (grep set)}"
boot "${ARM_ENV[@]}"
log "AB $LABEL up"
prov
warm
$PY -I $O/ab_t1_v2.py --tput "$URL" 3 "$OUT/tput-v2-$LABEL.jsonl" 2>&1 | tee "$OUT/ab-$LABEL-tput.out" | tee -a "$LOG"
need_line "$OUT/ab-$LABEL-tput.out" "^TPUT TOTAL"
gate_v2
if [ "${SKIP_T1:-0}" != 1 ]; then
  $PY -I $O/ab_t1_v2.py "$URL" $O/lever1-t1-thinking-prompts.jsonl "$OUT/t1v2-$LABEL.jsonl" 2>&1 \
    | tee "$OUT/ab-$LABEL-t1.out" | tee -a "$LOG"
  need_line "$OUT/ab-$LABEL-t1.out" "^T1 TOTAL"
fi
activation
log "AB $LABEL done"
