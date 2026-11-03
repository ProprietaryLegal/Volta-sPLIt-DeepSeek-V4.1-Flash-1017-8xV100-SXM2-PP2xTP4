#!/bin/bash
# serve-pp2.sh: the owner 2026-11-02 ~23:15Z "get 8 gpus up running on newest version of build with all upstream fixes, fix
# bugs ... then run llama benchy ... and local law prompts through it".
# Boots the 1Cat PP2xTP4 build (run-pp2, .venv-pp2 = v41pkg/pp2-up: our PP2 port + 1Cat main 6db9c81 + open PRs) on all
# eight GPUs, API on the 8-GPU host 127.0.0.1:18042.
#   - GPUs by UUID, never by index (the 11-02 PEX change renumbered them): stage 1 = Board B (ds41.env DS41_GPUS_A),
#     stage 2 = Board C (DS41_GPUS_C), passed as PCI_BUS_ID indices because custom all-reduce maps index entries.
#   - Engram: dd prewarm, then engram_lock.py (root mlock) pins it in RAM until stop-pp2.sh releases it.
#   - Model GGUF from the NVMe copy when models/gguf/COPY.done exists, else the HDD original.
# Writes bench5/$NAME.ready or $NAME.failed. Never stops the server on success (stop-pp2.sh does).
# Run on the 8-GPU host in tmux serve-pp2-d1:  PROFILE=serve-v41pkg-pp2.yaml bash bench5/serve-pp2.sh
set -uo pipefail
B=${ENGINE_HOME} R=$B/run-pp2 O=$B/bench5
ENGRAM=$B/engram/DeepSeek-V4.1-Flash-Engram-IQ4_NL.gguf
NV=$B/models/gguf HDD=${MODEL_HOME}/gguf
PORT=18042 NAME=${NAME:-serve-pp2} PROFILE=${PROFILE:-serve-v41pkg-pp2.yaml} WAIT_MIN=${WAIT_MIN:-60}
mkdir -p "$O"; LOG=$O/$NAME-$(date -u +%Y%m%dT%H%M%SZ).log
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOG"; }
memgib() { awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo; }
fail() { log "FAIL: $*"; echo "$*" > "$O/$NAME.failed"; exit 1; }
rm -f "$O/$NAME.ready" "$O/$NAME.failed"

log "$NAME start; profile $PROFILE; MemAvailable $(memgib) GiB; build $(cat $B/src-pp2/V41PKG_VERSION)"
[ -e "$B/logs/phase-pp2check.done" ] || fail "pp2check not done"
[ -s "$R/$PROFILE" ] || fail "no $R/$PROFILE (stage run-pp2 first)"
# v41k expert-major kernels: without them TP>1 falls back to TP1-only kernels and dies at graph capture (11-02 boot 2)
V41K=$(sed -n 's/^export VLLM_V41K_LIB="\(.*\)"$/\1/p' "$R/env.sh")
[ -s "$V41K" ] || fail "v41k library missing: ${V41K:-VLLM_V41K_LIB not set in env.sh} (re-run build phase pp2v41k)"
ss -ltn | awk '{print $4}' | /usr/bin/grep -qE '[:.]8000$' && fail ":8000 listening (FINAL up?)"
ss -ltn | awk '{print $4}' | /usr/bin/grep -qE "[:.]$PORT\$" && fail "port $PORT in use"

# shellcheck disable=SC1090
source <(/usr/bin/grep -E '^export DS41_GPUS_[AC]=' /path/to/gpus.env)
export CUDA_DEVICE_ORDER=PCI_BUS_ID
map=$(nvidia-smi --query-gpu=index,uuid --format=csv,noheader)
idx() { local u; for u in $1; do echo "$map" | awk -F', ' -v u="$u" '$2 == u {print $1}'; done | paste -sd,; }
B4=$(idx "$DS41_GPUS_A") C4=$(idx "$DS41_GPUS_C") IDS=$(idx "$DS41_GPUS_A"),$(idx "$DS41_GPUS_C")
[ "$(echo "$IDS" | tr ',' '\n' | /usr/bin/grep -c '^[0-9]')" -eq 8 ] || fail "could not resolve 8 indices ($IDS)"
apps=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader | /usr/bin/grep -c .)
[ "$apps" = 0 ] || fail "$apps compute process(es) on the GPUs"
log "stage 1 Board B = idx $B4; stage 2 Board C = idx $C4"
p2p=$(CUDA_VISIBLE_DEVICES=$IDS "$B/.venv-pp2/bin/python" -I -c 'import torch
ok = all(torch.cuda.can_device_access_peer(i, j) for s in (0, 4) for i in range(s, s + 4) for j in range(s, s + 4) if i != j)
print("P2P within each board:", ok)' 2>&1 | tail -1)
log "$p2p"
nvidia-smi -i "$IDS" --query-gpu=index,power.limit,clocks.sm,memory.used --format=csv,noheader | paste -sd';' | tee -a "$LOG"

# model path: NVMe copy when complete, else HDD
cur=$(/usr/bin/grep -E '^model:' "$R/$PROFILE" | awk '{print $2}')
want=$HDD/$(basename "$cur")
if [ -e "$NV/COPY.done" ] && [ "$(ls "$NV"/*.gguf | wc -l)" = 4 ]; then want=$NV/$(basename "$cur"); fi
if [ "$cur" != "$want" ]; then
  sed -i "s#^model: .*#model: $want#" "$R/$PROFILE"; log "model path -> $want"
fi
log "model $(/usr/bin/grep -E '^model:' "$R/$PROFILE" | awk '{print $2}')"

# Engram: prewarm and pin
t=$SECONDS; dd if="$ENGRAM" of=/dev/null bs=64M status=none
log "Engram prewarmed in $((SECONDS - t)) s (MemAvailable $(memgib) GiB)"
if [ -s "$O/engram-lock.pid" ] && sudo -n kill -0 "$(cat "$O/engram-lock.pid")" 2> /dev/null; then
  log "Engram lock already held (pid $(cat "$O/engram-lock.pid"))"
else
  : > "$O/engram-lock.log"
  sudo -n setsid /usr/bin/python3 -I "$B/tools/engram_lock.py" "$ENGRAM" "$O/engram-lock.pid" \
    >> "$O/engram-lock.log" 2>&1 < /dev/null &
  for ((i = 0; i < 120; i++)); do /usr/bin/grep -qE 'LOCKED|failed' "$O/engram-lock.log" && break; sleep 5; done
  /usr/bin/grep -q LOCKED "$O/engram-lock.log" || fail "Engram lock: $(tail -1 "$O/engram-lock.log")"
  log "Engram $(tail -1 "$O/engram-lock.log") (pid $(cat "$O/engram-lock.pid"); MemAvailable $(memgib) GiB)"
fi

rm -f "$R/state/$NAME.pid"
(cd "$R" && env CUDA_VISIBLE_DEVICES="$IDS" PROFILE="$PROFILE" ./run_serve.sh "$NAME") < /dev/null >> "$LOG" 2>&1
[ -s "$R/state/$NAME.pid" ] || fail "run_serve.sh $NAME wrote no pid file"
pid=$(cat "$R/state/$NAME.pid")
log "server $NAME group $pid starting; log $R/state/$NAME.log"
for ((i = 0; i < WAIT_MIN * 12; i++)); do
  /usr/bin/grep -q 'Application startup complete' "$R/state/$NAME.log" 2> /dev/null && break
  kill -0 "$pid" 2> /dev/null || fail "server exited during startup (see $R/state/$NAME.log)"
  sleep 5
done
/usr/bin/grep -q 'Application startup complete' "$R/state/$NAME.log" || fail "not up in $WAIT_MIN min (group $pid left running)"
log "server $NAME up after about $((i * 5)) s; MemAvailable $(memgib) GiB"
nvidia-smi -i "$IDS" --query-gpu=index,memory.used --format=csv,noheader | paste -sd';' | tee -a "$LOG"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 http://127.0.0.1:$PORT/v1/models)
[ "$code" = 200 ] || fail "/v1/models HTTP $code"
echo "$(date -u +%FT%TZ) group $pid port $PORT ids $IDS profile $PROFILE" > "$O/$NAME.ready"
log "READY: $NAME group $pid on 127.0.0.1:$PORT"
