#!/bin/bash
# rerecord-greedy-ref-v2.sh [LABEL]: H1 runner (harness1103, 11-03; advrev H1/M4). Records a new greedy reference and
# its near-tie lp-reference on the current recommended (REC) stack, validates them, and only then publishes
# bench5/greedy-ref-v2.env, which the v2 arm scripts read for the the owner-approved gate (0.10 nats + KL panel <= 0.02,
# memory the 8-GPU host-near-tie-gate-approved; quality.neartie). For a GPU window the owner schedules; not run by harness1103.
#
# Steps (each logged to bench5/rerec-<LABEL>-<ts>.log and as "REREC-V2 ..." lines in pp2-go.state):
#   1. REC env: REC_ENV/PROFILE when given, else derived exactly as queue-d37.sh derives its base (FULL + the D33/D34/
#      D34R/D35 keeps) plus D37's own final keeps from its "QUEUE-D37 server up: REC ... profile X" line. Without
#      REC_ENV it refuses unless "QUEUE-D37 done" is in pp2-go.state (the stack is still moving before that).
#   2. stop (Engram kept) + boot REC (NO_BOOT=1 uses the running server; the caller then asserts it is REC), warm-up,
#      provenance line (v41k.so sha16, build dir, deployed vllm .py digest).
#   3. quality.greedy record --runs 3: all three runs must be byte-identical, else no reference and exit 1 (the stack
#      is not deterministic; that is a finding, report it).
#   4. quality.neartie record --runs 2 against the new reference: both runs must reproduce it byte for byte with
#      top-20 logprobs on, and it writes lp-reference.jsonl (token ids + top-20, no text).
#   5. validation: quality.greedy check --strict --runs 1 (8/8 IDENTICAL) and quality.neartie check --runs 1 (PASS,
#      near-tie 0). Informational: the old IDX=0 reference at 0.9 nats (expect the known row 7 0.1094 near-tie).
#   6. publish: greedy-ref-v2.env (REF_V2, LP_V2, stack, so sha) via .new + mv, and a line in greedy-ref-v2.history.
#      On a validation failure it writes greedy-ref-v2.candidate-<ts>.env instead and publishes nothing.
# Never overwrites a reference: quality.greedy/neartie write fresh <UTC>-<kind>-<label> folders beside the old one
# (run-pp2/quality-runs; mkdir exist_ok=False, files opened "x"); the old 20261103T002941Z reference is only read.
# GPU minutes (ESTIMATED from bench5 logs): stop + boot ~3.5, warm-up 0.1, record 3 x ~0.6, neartie record 2 x ~0.7,
# strict check ~0.6, neartie check ~0.7, old-reference check ~0.9 -> about 10 min; schedule 15.
# Leaves the server up on REC. Exit 0 published, 1 not published.
set -uo pipefail
B=${ENGINE_HOME} O=$B/bench5
LABEL=${1:-REFV2}
TS=$(date -u +%Y%m%dT%H%M%SZ)
source $O/arm-checks-v2.sh
mkdir -p "$OUT"
LOG=$OUT/rerec-$LABEL-$TS.log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
st() { st_line "REREC-V2 $*"; log "REREC-V2 $*"; }
qenv() { env -C "$Q" DS41_URL="$URL" DS41_SERVED_NAME=deepseek-v4.1-flash DS41_QUALITY_RUNS="$QRUNS" \
           DS41_CLOCK_CONDITION="REREC-V2 $LABEL" timeout 30m $PY -m "$@"; }

# 1. REC env
if [ -z "${REC_ENV:-}" ]; then
  /usr/bin/grep -q "QUEUE-D37 done" "$STATE" || { st "refused: QUEUE-D37 not done and no REC_ENV given"; exit 1; }
  REC_ENV="VLLM_V41_INDEX_REDUCE=1 VLLM_V41_DMV_X=1 VLLM_V41_COUPLED_DRAFTS=1 VLLM_V41_COUPLED_DRAFT_TEMP=1.0 VLLM_V41_MARKOV_SHARD=1 VLLM_V41_COUPLED_SHARD=1 VLLM_V41_COUPLED_LOCAL=1 VLLM_V41_PLAN_FUSE=1 VLLM_V41_PP_KEEP_BATCH=1 VLLM_V41_EXPERT_FAST=1 VLLM_V41_FUSE_ATTN_PREP=1 VLLM_V41_FUSE_ATTN_POST=1"
  /usr/bin/grep -q "QUEUE-D33 server up: REC + VLLM_V41_MIX_STREAM=1" "$STATE" && REC_ENV="$REC_ENV VLLM_V41_MIX_STREAM=1"
  /usr/bin/grep "QUEUE-D34 server up" "$STATE" | tail -n 1 | /usr/bin/grep -q "VLLM_V41_EXPERT_DIET=3" && REC_ENV="$REC_ENV VLLM_V41_EXPERT_DIET=3"
  /usr/bin/grep "QUEUE-D34R server up" "$STATE" | tail -n 1 | /usr/bin/grep -q "VLLM_V41_ROUTE_FAST=1" && REC_ENV="$REC_ENV VLLM_V41_ROUTE_FAST=1 VLLM_V41_ROUTE_WARPS=4"
  /usr/bin/grep "QUEUE-D35 server up" "$STATE" | tail -n 1 | /usr/bin/grep -q "VLLM_V41_PREFILL_SKIP_ROWS=3072" && REC_ENV="$REC_ENV VLLM_V41_PREFILL_SKIP_ROWS=3072"
  D37=$(/usr/bin/grep "QUEUE-D37 server up" "$STATE" | tail -n 1)
  [ -n "$D37" ] || { st "refused: no 'QUEUE-D37 server up' line (D37 final boot failed?); give REC_ENV and PROFILE"; exit 1; }
  echo "$D37" | /usr/bin/grep -q "VLLM_V41_INDEX_OVERLAP=1" && REC_ENV="$REC_ENV VLLM_V41_INDEX_OVERLAP=1"
  echo "$D37" | /usr/bin/grep -q "VLLM_V41_HC_TOKEN_BLOCKED=1" && REC_ENV="$REC_ENV VLLM_V41_HC_TOKEN_BLOCKED=1"
  PROFILE=${PROFILE:-$(echo "$D37" | /usr/bin/grep -o -E 'profile [^ ]+' | tail -n 1 | cut -d' ' -f2)}
fi
export PROFILE=${PROFILE:-serve-v41pkg-pp2.yaml}
st "start $LABEL: stack $REC_ENV profile $PROFILE"

# 2. boot + warm + provenance
if [ "${NO_BOOT:-0}" = 1 ]; then
  alive || { st "NO_BOOT=1 but the server does not answer"; exit 1; }
  log "NO_BOOT=1: using the running server (caller asserts it is REC)"
else
  # shellcheck disable=SC2086
  boot $REC_ENV
fi
st "server up"
prov
warm

# 3. reference: 3 runs, byte-identical
qenv quality.greedy record --label "$LABEL" --runs 3 > "$OUT/rerec-$LABEL-$TS-record.out" 2>&1; rc=$?
REF=$(sed -n 's/^GREEDY RECORD .*references \(.*\/references\.jsonl\)$/\1/p' "$OUT/rerec-$LABEL-$TS-record.out" | tail -n 1)
st "greedy record rc=$rc: $(/usr/bin/grep -E '^GREEDY' "$OUT/rerec-$LABEL-$TS-record.out" | tail -n 2 | tr '\n' ' ' | cut -c1-300)"
if [ $rc != 0 ] || [ ! -s "$REF" ]; then st "FAIL: 3 runs not byte-identical on REC (non-deterministic stack) or record error; nothing published"; exit 1; fi
[ "$REF" = "$REF_V1" ] && { st "FAIL: new reference path equals the old one (impossible; refusing)"; exit 1; }

# 4. lp-reference: 2 runs with top-20 logprobs, must reproduce the reference
qenv quality.neartie record --label "NT$LABEL" --reference "$REF" --runs 2 > "$OUT/rerec-$LABEL-$TS-ntrecord.out" 2>&1; rc=$?
LP=$(sed -n 's/^NEARTIE RECORD .*-> \(.*\/lp-reference\.jsonl\)$/\1/p' "$OUT/rerec-$LABEL-$TS-ntrecord.out" | tail -n 1)
st "neartie record rc=$rc: $(/usr/bin/grep -E '^NEARTIE' "$OUT/rerec-$LABEL-$TS-ntrecord.out" | tail -n 2 | tr '\n' ' ' | cut -c1-300)"
if [ $rc != 0 ] || [ ! -s "$LP" ]; then st "FAIL: lp-reference not written; nothing published"; exit 1; fi

# 5. validation
ok=1
qenv quality.greedy check --label "$LABEL-VS" --reference "$REF" --runs 1 --strict > "$OUT/rerec-$LABEL-$TS-strict.out" 2>&1; rc=$?
st "validate strict rc=$rc: $(/usr/bin/grep -E '^GREEDY CHECK' "$OUT/rerec-$LABEL-$TS-strict.out" | cut -c1-200)"
[ $rc = 0 ] || ok=0
qenv quality.neartie check --label "$LABEL-VN" --reference "$REF" --lp-reference "$LP" --runs 1 --gap 0.10 --kl-max 0.02 \
  > "$OUT/rerec-$LABEL-$TS-ntcheck.out" 2>&1; rc=$?
nt=$(/usr/bin/grep -E '^NEARTIE CHECK' "$OUT/rerec-$LABEL-$TS-ntcheck.out")
st "validate neartie rc=$rc: $(echo "$nt" | cut -c1-240)"
{ [ $rc = 0 ] && echo "$nt" | /usr/bin/grep -q "near-tie 0 fail 0"; } || ok=0
if [ "${OLDREF_CHECK:-1}" = 1 ]; then
  qenv quality.greedy check --label "$LABEL-OLD" --reference "$REF_V1" --runs 1 --nats 0.9 > "$OUT/rerec-$LABEL-$TS-oldref.out" 2>&1; rc=$?
  st "info: old IDX=0 reference at 0.9 nats rc=$rc: $(/usr/bin/grep -E '^run 1 row [0-9]+ (NEAR-TIE|FAIL)|^GREEDY CHECK' "$OUT/rerec-$LABEL-$TS-oldref.out" | tr '\n' ' ' | cut -c1-300)"
fi

# 6. publish (or keep as a candidate)
so=$(sed -n 's/^export VLLM_V41K_LIB="\(.*\)"$/\1/p' "$ENVSH")
body="REF_V2=$REF
LP_V2=$LP
RECORDED=$TS
LABEL=$LABEL
PROFILE=$PROFILE
SO_SHA16=$(sha16 "$so")
STACK_ENV=$REC_ENV"
if [ $ok = 1 ]; then
  printf '%s\n' "$body" > "$REFPTR.new" && mv "$REFPTR.new" "$REFPTR"
  echo "$TS REF_V2=$REF LP_V2=$LP profile=$PROFILE" >> "$REFPTR.history"
  st "PUBLISHED $REFPTR (REF_V2 $REF, LP_V2 $LP); v2 arms with GATE=auto now use the approved gate"
  st "done"; exit 0
fi
printf '%s\n' "$body" > "${REFPTR%.env}.candidate-$TS.env"
st "NOT published: validation failed; candidate kept at ${REFPTR%.env}.candidate-$TS.env"
st "done"; exit 1
