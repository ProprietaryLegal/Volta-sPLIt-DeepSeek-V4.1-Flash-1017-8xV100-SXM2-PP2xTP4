#!/usr/bin/env bash
# OPS1 startup warm-up with a hard process bound. The helper's own deadline cannot stop a trickling HTTP read, so the
# whole process ends at DS41_WARMUP_HARD_S (default 160 s; KILL 5 s later). A non-zero exit is a WARN for the caller.
#   tools/warmup.sh [PORT] [SERVED_NAME]
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec timeout --kill-after=5s "${DS41_WARMUP_HARD_S:-160}s" python3 "$here/warmup.py" \
  --port "${1:-${DS41_PORT:-8000}}" --model "${2:-${DS41_SERVED_NAME:?served model name (argument 2 or DS41_SERVED_NAME)}}"
