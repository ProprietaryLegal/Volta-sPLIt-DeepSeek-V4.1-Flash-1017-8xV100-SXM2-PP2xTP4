#!/usr/bin/env bash
# smoke-4card.sh: GPU smoke of the 4-card fork on ONE idle 4x V100 NVLink board. Not run yet: the fork is GPU-unverified.
# For each arm (ARMS, default "sync"; "sync async" adds the PENDING async arm) it boots start.sh on a spare port, runs
# smoke_client.py (warm-up, greedy T=0 repeat identity, T=0 and T=1 ms/round + tok/s, a same-session prefix hit),
# checks every lever's activation line (verify.sh --activation), records GPU memory, and stops the server again.
# The async arm's greedy output is compared with the sync arm's (NEAR-TIE vs DIFF at the first divergence).
#
# On the 8-GPU host (Board B, production stopped by its owner first):
#   SMOKE_ENV=/path/to/out bash smoke-4card.sh
# Elsewhere: fill the MACHINE block of configs/4card.env (or a SMOKE_ENV file that overrides it) and run ./install.sh.
#
# Preflight refusals (nothing is started): port 18042 (the 8-GPU host's PP2 dev server) or the smoke port listening; any compute
# process on ANY GPU; DS41_GPUS not four indices; on the 8-GPU host, DS41_GPUS not equal to Board B (DS41_GPUS_A UUIDs in
# /path/to/gpus.env); peer access missing inside the four.
# Output: $FORK_HOME/run/smoke-<UTC>/ (SUMMARY, per-arm client output, activation report, server log copy). Generated
# text stays there: never commit it.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
if [[ -x "$here/start.sh" ]]; then FORK=$here; else FORK=${FORK:-$here/1cat-4xv100-tp4}; fi
[[ -x "$FORK/start.sh" ]] || { echo "smoke: no fork at $FORK (set FORK)" >&2; exit 2; }
# shellcheck disable=SC1090
[[ -n "${SMOKE_ENV:-}" ]] && { set -a; source "$SMOKE_ENV"; set +a; }
# shellcheck source=configs/4card.env
source "$FORK/configs/4card.env"
export FORK_HOME DS41_GGUF DS41_BASE DS41_ENGRAM DS41_DSPARK DS41_GPUS DS41_HOST DS41_PORT DS41_SERVED_NAME DS41_OFFLOAD
export ENGINE_PY=${ENGINE_PY:-$FORK_HOME/.venv/bin/python} VLLM_V41K_LIB
PROD_PORT=18042 ARMS=${ARMS:-sync}
OUT=$FORK_HOME/run/smoke-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$OUT"
S=$OUT/SUMMARY
say() { echo "$(date -u +%FT%TZ) $*" | tee -a "$S"; }
refuse() { say "REFUSED: $*"; exit 3; }
listening() { ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$1\$"; }

# ---------------------------------------------------------------- preflight ----------------------------------------
say "smoke-4card: fork $FORK; engine $ENGINE_PY; v41k $VLLM_V41K_LIB; GPUs $DS41_GPUS; port $DS41_PORT; arms $ARMS"
[[ "$DS41_PORT" != "$PROD_PORT" ]] || refuse "DS41_PORT is $PROD_PORT; use a spare port"
listening "$PROD_PORT" && refuse ":$PROD_PORT is listening (the PP2 server is up)"
listening "$DS41_PORT" && refuse ":$DS41_PORT is listening"
command -v nvidia-smi >/dev/null || refuse "no nvidia-smi"
held=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | grep -c .)
[[ "$held" == 0 ]] || refuse "$held compute process(es) hold GPUs; every GPU must be idle"
[[ "$(tr ',' '\n' <<< "$DS41_GPUS" | grep -cE '^[0-9]+$')" == 4 ]] || refuse "DS41_GPUS must be four indices: $DS41_GPUS"
DEPLOY_ENV=/path/to/gpus.env
if [[ -r "$DEPLOY_ENV" ]] && grep -q '^export DS41_GPUS_A=' "$DEPLOY_ENV"; then
  uuids=$(source <(grep -E '^export DS41_GPUS_A=' "$DEPLOY_ENV") && echo "$DS41_GPUS_A")
  map=$(CUDA_DEVICE_ORDER=PCI_BUS_ID nvidia-smi --query-gpu=index,uuid --format=csv,noheader)
  boardb=$(for u in $uuids; do awk -F', ' -v u="$u" '$2 == u {print $1}' <<< "$map"; done | sort -n | paste -sd,)
  mine=$(tr ',' '\n' <<< "$DS41_GPUS" | sort -n | paste -sd,)
  [[ "$boardb" == "$mine" ]] || refuse "DS41_GPUS {$mine} is not Board B {$boardb} (ds41.env DS41_GPUS_A)"
  say "Board B check: DS41_GPUS = Board B indices {$boardb}"
fi
p2p=$(CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=$DS41_GPUS "$ENGINE_PY" -I -c 'import torch
n = torch.cuda.device_count()
print(n == 4 and all(torch.cuda.can_device_access_peer(i, j) for i in range(n) for j in range(n) if i != j))' 2>&1 | tail -1)
[[ "$p2p" == True ]] || refuse "peer access inside $DS41_GPUS: $p2p"
say "P2P inside the four: True"
nvidia-smi -i "$DS41_GPUS" --query-gpu=index,power.limit,clocks.max.sm,clocks.sm,memory.used --format=csv,noheader \
  | paste -sd';' | sed 's/^/gpus: /' | tee -a "$S"
bash "$FORK/verify.sh" --static > "$OUT/static.txt" 2>&1 || { cat "$OUT/static.txt" >> "$S"; refuse "verify.sh --static failed"; }
say "verify --static PASS"

# ---------------------------------------------------------------- arms ---------------------------------------------
rc_all=0 ref=""
trap 'for a in $ARMS; do NAME=smoke-$a bash "$FORK/stop.sh" >/dev/null 2>&1; done' EXIT
for arm in $ARMS; do
  case $arm in sync) async=0 ;; async) async=1 ;; *) say "unknown arm $arm"; rc_all=1; continue ;; esac
  name=smoke-$arm A=$OUT/$arm; mkdir -p "$A"
  say "arm $arm: boot"
  if ! NAME=$name ASYNC=$async PREWARM=${PREWARM:-0} bash "$FORK/start.sh" > "$A/start.txt" 2>&1; then
    say "arm $arm: BOOT FAILED: $(tail -1 "$A/start.txt")"; cp "$FORK_HOME/run/$name.log" "$A/server.log" 2>/dev/null
    NAME=$name bash "$FORK/stop.sh" >> "$A/start.txt" 2>&1; rc_all=1; continue
  fi
  say "arm $arm: $(tail -1 "$A/start.txt")"
  nvidia-smi -i "$DS41_GPUS" --query-gpu=index,memory.used,memory.total --format=csv,noheader | paste -sd';' \
    | sed "s/^/arm $arm memory after boot: /" | tee -a "$S"
  "$(command -v python3)" -I "$FORK/smoke_client.py" "http://$DS41_HOST:$DS41_PORT" "$DS41_SERVED_NAME" "$A" \
    ${ref:+--reference "$ref"} > "$A/client.txt" 2>&1; crc=$?
  grep -E '^(WARM|GREEDY|TPUT|SESSION|greedy p)' "$A/client.txt" | sed "s/^/arm $arm: /" | tee -a "$S"
  (( crc == 0 )) || { say "arm $arm: client rc=$crc (tail: $(tail -1 "$A/client.txt"))"; rc_all=1; }
  NAME=$name bash "$FORK/verify.sh" --activation "$FORK_HOME/run/$name.log" > "$A/activation.txt" 2>&1 || rc_all=1
  grep -E '^(FAIL|INFO)|^verify' "$A/activation.txt" | sed "s/^/arm $arm: /" | tee -a "$S"
  grep -aE 'KV cache size|Maximum concurrency|Model loading took|Graph capturing finished|Available KV cache memory' \
    "$FORK_HOME/run/$name.log" | sed -E 's/\x1b\[[0-9;]*m//g; s/^.*\] //' | sort | uniq -c | sed "s/^/arm $arm: /" | tee -a "$S"
  nvidia-smi -i "$DS41_GPUS" --query-gpu=index,memory.used --format=csv,noheader | paste -sd';' \
    | sed "s/^/arm $arm memory after smoke: /" | tee -a "$S"
  cp "$FORK_HOME/run/$name.log" "$A/server.log"; cp "$FORK_HOME/run/$name.env" "$A/server.env" 2>/dev/null
  NAME=$name bash "$FORK/stop.sh" | tee -a "$S"
  [[ -z "$ref" && -s "$A/greedy.json" ]] && ref=$A/greedy.json
done
say "smoke-4card: $([[ $rc_all == 0 ]] && echo PASS || echo FAIL); details in $OUT"
exit $rc_all
