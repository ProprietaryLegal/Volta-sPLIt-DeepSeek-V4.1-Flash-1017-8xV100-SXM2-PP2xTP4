#!/usr/bin/env bash
# start.sh: boot the 4-card fork's OpenAI-compatible server (TP4, PP=1) on DS41_GPUS, DS41_HOST:DS41_PORT.
# Renders configs/serve-4card.yaml.in into $FORK_HOME/run/$NAME.yaml, starts the server in its own process group, and
# waits for "Application startup complete". Writes $FORK_HOME/run/$NAME.{pid,log,ready|failed}. Stop with ./stop.sh.
#   NAME=serve-4card      run name (log, pid and yaml file names)
#   ASYNC=1               PENDING arm: async scheduling + VLLM_V41_ASYNC=1 (upstream #1277's mode; see README)
#   ENGINE_PY=...         python of the engine venv (default $FORK_HOME/.venv/bin/python)
#   PREWARM=1             read the Engram file once before the boot (110.6 GB; makes the load start from page cache)
#   WAIT_MIN=60           minutes to wait for startup
set -uo pipefail
FORK=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=configs/4card.env
source "$FORK/configs/4card.env"
NAME=${NAME:-serve-4card} WAIT_MIN=${WAIT_MIN:-60} ENGINE_PY=${ENGINE_PY:-$FORK_HOME/.venv/bin/python}
RUN=$FORK_HOME/run; mkdir -p "$RUN" "$FORK_HOME/cache"
LOG=$RUN/$NAME.log YAML=$RUN/$NAME.yaml
fail() { echo "start.sh: FAIL: $*" >&2; echo "$*" > "$RUN/$NAME.failed"; exit 1; }
rm -f "$RUN/$NAME.ready" "$RUN/$NAME.failed"

for v in DS41_GGUF DS41_BASE DS41_ENGRAM DS41_DSPARK DS41_GPUS; do
  [[ "${!v}" == *__SET_ME__* ]] && fail "$v is not set (edit the MACHINE block of configs/4card.env or export it)"
done
for f in "$DS41_GGUF" "$DS41_ENGRAM" "$VLLM_V41K_LIB"; do [[ -s "$f" ]] || fail "missing file $f"; done
for d in "$DS41_BASE" "$DS41_DSPARK"; do [[ -d "$d" ]] || fail "missing directory $d"; done
[[ -x "$ENGINE_PY" ]] || fail "no engine python at $ENGINE_PY (run ./install.sh)"
[[ "$(tr ',' '\n' <<< "$DS41_GPUS" | grep -cE '^[0-9]+$')" == 4 ]] || fail "DS41_GPUS must be four PCI_BUS_ID indices, got $DS41_GPUS"
if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$DS41_PORT\$"; then fail "port $DS41_PORT already listening"; fi
if [[ -s "$RUN/$NAME.pid" ]] && kill -0 -- "-$(cat "$RUN/$NAME.pid")" 2>/dev/null; then
  fail "$NAME already running (group $(cat "$RUN/$NAME.pid"))"
fi

sed -e "s#@DS41_GGUF@#$DS41_GGUF#; s#@DS41_BASE@#$DS41_BASE#g; s#@DS41_ENGRAM@#$DS41_ENGRAM#" \
    -e "s#@DS41_DSPARK@#$DS41_DSPARK#; s#@DS41_SERVED_NAME@#$DS41_SERVED_NAME#; s#@DS41_HOST@#$DS41_HOST#" \
    -e "s#@DS41_PORT@#$DS41_PORT#; s#@DS41_OFFLOAD@#$DS41_OFFLOAD#" "$FORK/configs/serve-4card.yaml.in" > "$YAML"
if [[ "${ASYNC:-0}" == 1 ]]; then
  sed -i 's/^no-async-scheduling: true$/async-scheduling: true/' "$YAML"; export VLLM_V41_ASYNC=1
fi
grep -q '@[A-Z0-9_]*@' "$YAML" && fail "unfilled field in $YAML"

# The engine must be the venv's installed wheel (its compiled extensions live in site-packages, not in src/).
(cd / && "$ENGINE_PY" -I -c 'import sys, vllm, vllm._C, vllm._C_gguf
sys.exit(0 if vllm.__file__.startswith(sys.prefix) else "vllm imported from " + vllm.__file__)') \
  || fail "engine import check failed for $ENGINE_PY"

if [[ "${PREWARM:-0}" == 1 ]]; then t=$SECONDS; dd if="$DS41_ENGRAM" of=/dev/null bs=64M status=none; echo "Engram read in $((SECONDS - t)) s"; fi

export CUDA_VISIBLE_DEVICES=$DS41_GPUS XDG_CACHE_HOME=$FORK_HOME/cache XDG_CONFIG_HOME=$FORK_HOME/cache/config
export FLASHINFER_WORKSPACE_BASE=$FORK_HOME/cache TRITON_CACHE_DIR=$FORK_HOME/cache/triton
unset PYTHONPATH
cd "$RUN" || fail "cd $RUN"
env | grep -E '^VLLM_V41|^VLLM_USE_V2|^CUDA_VISIBLE_DEVICES=' | sort > "$RUN/$NAME.env"
setsid "$ENGINE_PY" -m vllm.entrypoints.openai.api_server --config "$YAML" > "$LOG" 2>&1 < /dev/null &
pid=$!; echo "$pid" > "$RUN/$NAME.pid"
echo "start.sh: $NAME group $pid on GPUs $DS41_GPUS, $DS41_HOST:$DS41_PORT (async ${ASYNC:-0}); log $LOG"
for ((i = 0; i < WAIT_MIN * 12; i++)); do
  grep -q 'Application startup complete' "$LOG" 2>/dev/null && break
  kill -0 "$pid" 2>/dev/null || fail "server exited during startup (see $LOG)"
  sleep 5
done
grep -q 'Application startup complete' "$LOG" || fail "not up in $WAIT_MIN min (group $pid left running; ./stop.sh)"
echo "$(date -u +%FT%TZ) group $pid port $DS41_PORT gpus $DS41_GPUS async ${ASYNC:-0}" > "$RUN/$NAME.ready"
echo "start.sh: READY after about $((i * 5)) s"
