#!/usr/bin/env bash
# run_serve.sh <name>: upstream phase-3 API on 127.0.0.1 (run_serve3.sh envs), own process group.
# PROFILE=<yaml> selects another profile in this directory. PP2 defaults to
# serve-pp2.yaml and stays synchronous (V41_PP2_ASYNC=1 is experimental and not used in production).
# Stop it with: kill -TERM -- -$(cat state/<name>.pid)
set -uo pipefail
RUN=$(cd "$(dirname "$0")" && pwd)
source "$RUN/env.sh" || exit 1
name=${1:-serve3}
export VLLM_V41_DOWN_ROWS=1 VLLM_V41_SESSION_PREFIX=1 VLLM_V41_PACKED_KV=1 VLLM_V41_INDEX_TILE_MB=32
if [ "$V41PKG_PP" = 1 ] || [ "${V41_PP2_ASYNC:-0}" = 1 ]; then export VLLM_V41_ASYNC=1; else unset VLLM_V41_ASYNC; fi
setsid "$PY" -m vllm.entrypoints.openai.api_server --config "$RUN/${PROFILE:-$V41PKG_DEFAULT_PROFILE}" > "$RUN/state/$name.log" 2>&1 &
echo $! > "$RUN/state/$name.pid"; echo "serve pid/pgid $(cat "$RUN/state/$name.pid"), log $RUN/state/$name.log"
