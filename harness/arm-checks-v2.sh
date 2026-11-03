# arm-checks-v2.sh: sourced by ab-arm-t1-v2.sh, ab-depth-arm-v2.sh and rerecord-greedy-ref-v2.sh (harness1103, 11-03).
# arm-checks.sh (v1) is unchanged and still serves the v1 arm scripts and the queued D32-D37 windows.
# Sets the shared v2 paths (each overridable for dry tests only; the defaults are the live ones) and needs LABEL, LOG and
# log() from the caller.
#   alive               0 when the server answers /health
#   invalid REASON      log "AB <label> INVALID: REASON" to the arm log and the state file, then exit 1
#   warm                untimed warm-up (warmup.py, unchanged); INVALID on failure
#   need_line F P       INVALID unless file F has a line matching P and the server is still alive
#   prov                H5: log + state line "AB <label> PROV so=<sha16> sodir=<build dir> pyvllm=<sha16> harness=<sha16>"
#   activation          H3: when ACT_GREP is set, count its matches in this boot's serve log; ACT_EXPECT=on needs >= 1,
#                       off needs 0, any (default) records only. Line "AB <label> ACT n=<count> pat=<sha8> expect=<x>"
#   split_args "$@"     harness vars (ACT_GREP ACT_EXPECT GATE NUMERICS SKIP_T1 SKIP_GREEDY) given as arm args are
#                       exported for the script; the rest go to ARM_ENV (the server env), so they never reach the engine
#   gate_v2             H1: GATE=legacy|approved|both|auto|none (default auto: approved when greedy-ref-v2.env exists,
#                       else legacy). legacy = the v1 check (old reference, 0.9 nats). approved = quality.neartie check
#                       at 0.10 nats + teacher-forced KL panel <= 0.02 against the H1 reference (NUMERICS=1 adds
#                       --require-drift). Line "AB <label> GATE <mode> <PASS|FAIL|NO-EFFECT|ERROR> rc=<n>"
B=${B:-${ENGINE_HOME}}
O=${O:-$B/bench5}
Q=${V2_Q:-${QUALITY_TOOLS}}
OUT=${V2_OUT:-$O}                                   # arm logs and outputs
STATE=${V2_STATE:-$O/pp2-go.state}
URL=${V2_URL:-http://127.0.0.1:18042}
QRUNS=${V2_QRUNS:-$B/run-pp2/quality-runs}
SERVE_LOG=${V2_SERVE_LOG:-$B/run-pp2/state/serve-pp2.log}
ENVSH=${V2_ENVSH:-$B/run-pp2/env.sh}
SPV=${V2_SPVLLM:-$B/.venv-pp2/lib/python3.12/site-packages/vllm}
STOP_CMD=${V2_STOP:-bash $O/stop-pp2.sh}
SERVE_CMD=${V2_SERVE:-bash $O/serve-pp2.sh}
PAUSE=${V2_PAUSE:-10}
REF_V1=$B/run-pp2/quality-runs/20261103T002941Z-greedy-B5PP2-g1/references.jsonl
REFPTR=${V2_REFPTR:-$O/greedy-ref-v2.env}
PY=/usr/bin/python3

alive() { /usr/bin/curl -sf -m 10 "$URL/health" > /dev/null; }
st_line() { echo "$(date -u +%FT%TZ) $*" >> "$STATE"; }
invalid() {
  log "AB $LABEL INVALID: $*"
  st_line "AB $LABEL INVALID: $*"
  exit 1
}
warm() {
  $PY -I $O/warmup.py "$URL" > "$OUT/ab-$LABEL-warm.out" 2>&1
  cat "$OUT/ab-$LABEL-warm.out" >> "$LOG"
  /usr/bin/grep -q "^WARMUP OK" "$OUT/ab-$LABEL-warm.out" || invalid "warm-up failed"
}
need_line() {
  /usr/bin/grep -q "$2" "$1" || invalid "no '$2' line (bench crashed or the engine died)"
  alive || invalid "server not answering /health after the bench"
}
sha16() { sha256sum "$1" 2> /dev/null | cut -c1-16; }
prov() {
  local so sodir py h
  so=$(sed -n 's/^export VLLM_V41K_LIB="\(.*\)"$/\1/p' "$ENVSH")
  sodir=$(dirname "$(readlink -f "$so" 2> /dev/null || echo "$so")")
  # digest of every deployed vllm .py (path + content), so a wrong-tree deploy (D28) shows as an unchanged digest
  py=$(cd "$SPV" 2> /dev/null && nice -n 19 find . -name '*.py' -type f -print0 | LC_ALL=C sort -z \
       | nice -n 19 xargs -0 sha256sum | sha256sum | cut -c1-16)
  h=$(cat $O/ab_t1_v2.py $O/arm-checks-v2.sh 2> /dev/null | sha256sum | cut -c1-16)
  log "AB $LABEL PROV so=$(sha16 "$so") sodir=$sodir pyvllm=${py:-none} harness=$h"
  st_line "AB $LABEL PROV so=$(sha16 "$so") sodir=$sodir pyvllm=${py:-none} harness=$h"
}
activation() {
  [ -n "${ACT_GREP:-}" ] || return 0
  local n pat
  n=$(/usr/bin/grep -cE -- "$ACT_GREP" "$SERVE_LOG" 2> /dev/null); n=${n:-0}
  pat=$(printf '%s' "$ACT_GREP" | sha256sum | cut -c1-8)
  log "AB $LABEL ACT n=$n pat=$pat expect=${ACT_EXPECT:-any}"
  st_line "AB $LABEL ACT n=$n pat=$pat expect=${ACT_EXPECT:-any}"
  case "${ACT_EXPECT:-any}" in
    on) [ "$n" -ge 1 ] || invalid "activation line absent (ACT_EXPECT=on, pattern $pat): the knob did not reach the engine" ;;
    off) [ "$n" = 0 ] || invalid "activation line present in an OFF arm ($n, pattern $pat)" ;;
  esac
}
gate_mode() {
  local g=${GATE:-auto}
  if [ "$g" = auto ]; then
    if [ -s "$REFPTR" ]; then g=approved; else g=legacy; fi
  fi
  echo "$g"
}
gate_v2() {
  local g rc v REF_V2="" LP_V2=""
  g=$(gate_mode)
  [ "$g" = none ] && { log "AB $LABEL GATE none (skipped)"; return 0; }
  if [ "$g" = legacy ] || [ "$g" = both ]; then
    env -C "$Q" DS41_URL="$URL" DS41_SERVED_NAME=deepseek-v4.1-flash DS41_QUALITY_RUNS="$QRUNS" \
      DS41_CLOCK_CONDITION="AB $LABEL" timeout 20m $PY -m quality.greedy check --label "AB-$LABEL" --reference "$REF_V1" \
      --runs 1 --nats 0.9 > "$OUT/ab-$LABEL-greedy.out" 2>&1; rc=$?
    v=ERROR; [ $rc = 0 ] && v=PASS; [ $rc = 1 ] && v=FAIL
    log "AB $LABEL GREEDY rc=$rc: $(/usr/bin/grep -E 'GREEDY|IDENTICAL|NEAR|DIFF|PASS|FAIL' "$OUT/ab-$LABEL-greedy.out" | tail -n 12 | tr '\n' ' ' | cut -c1-900)"
    log "AB $LABEL GATE legacy $v rc=$rc"; st_line "AB $LABEL GATE legacy $v rc=$rc"
  fi
  if [ "$g" = approved ] || [ "$g" = both ]; then
    [ -s "$REFPTR" ] || invalid "GATE=$g but no $REFPTR (run rerecord-greedy-ref-v2.sh first)"
    REF_V2=$(sed -n 's/^REF_V2=//p' "$REFPTR"); LP_V2=$(sed -n 's/^LP_V2=//p' "$REFPTR")
    [ -s "$REF_V2" ] && [ -s "$LP_V2" ] || invalid "greedy-ref-v2.env points at missing files"
    env -C "$Q" DS41_URL="$URL" DS41_SERVED_NAME=deepseek-v4.1-flash DS41_QUALITY_RUNS="$QRUNS" \
      DS41_CLOCK_CONDITION="AB $LABEL" timeout 20m $PY -m quality.neartie check --label "AB-$LABEL" \
      --reference "$REF_V2" --lp-reference "$LP_V2" --runs 1 --gap 0.10 --kl-max 0.02 \
      ${NUMERICS:+--require-drift} > "$OUT/ab-$LABEL-neartie.out" 2>&1; rc=$?
    v=ERROR; [ $rc = 0 ] && v=PASS; [ $rc = 1 ] && v=FAIL
    /usr/bin/grep -q "^NEARTIE NO EFFECT" "$OUT/ab-$LABEL-neartie.out" && v=NO-EFFECT
    log "AB $LABEL NEARTIE rc=$rc: $(/usr/bin/grep -E '^NEARTIE|^logprob drift|^run 1 row [0-9]+ (NEAR-TIE|FAIL)' "$OUT/ab-$LABEL-neartie.out" | tail -n 12 | tr '\n' ' ' | cut -c1-900)"
    log "AB $LABEL GATE approved $v rc=$rc"; st_line "AB $LABEL GATE approved $v rc=$rc"
  fi
}
split_args() {  # split_args "$@": harness vars given as arm args are exported here, never passed to the server env
  ARM_ENV=()
  local kv
  for kv in "$@"; do
    case "$kv" in
      ACT_GREP=*|ACT_EXPECT=*|GATE=*|NUMERICS=*|SKIP_T1=*|SKIP_GREEDY=*) export "$kv" ;;
      *) ARM_ENV+=("$kv") ;;
    esac
  done
}
boot() {   # boot "$@": stop (Engram kept), then boot PROFILE with the env; INVALID-free failure exit like v1
  KEEP_LOCK=1 $STOP_CMD >> "$LOG" 2>&1; sleep "$PAUSE"
  if ! env "$@" PROFILE=${PROFILE:-serve-v41pkg-pp2.yaml} $SERVE_CMD >> "$LOG" 2>&1; then
    log "AB $LABEL BOOT FAILED: $(cat $O/serve-pp2.failed 2> /dev/null)"; exit 1
  fi
}
