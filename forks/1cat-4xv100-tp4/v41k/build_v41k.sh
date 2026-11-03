#!/usr/bin/env bash
# build_v41k.sh SRC PYTHON: build the v41k CUDA extension (SM70) on the TARGET machine into
# SRC/benchmarks/deepseek_v41/v41k/build/v41k.so, with the engine venv's torch (a torch cpp_extension: its ABI is tied to
# that torch, so never copy a v41k.so built on another host or against another venv).
# The source is the patched tree itself (series patches 0036 and 0043 bring in dmv13_x and gate_up_fast/down_rows_fast);
# SOURCES pins it to the gu1103 files the 8-GPU host's production library was built from.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
src=${1:?usage: build_v41k.sh SRC PYTHON} py=${2:?usage: build_v41k.sh SRC PYTHON}
bad=0
while IFS=$'\t' read -r path want; do
  [[ -z "$path" || "$path" == \#* ]] && continue
  got=$(sha256sum "$src/$path" | cut -c1-12)
  if [[ "$got" == "$want" ]]; then echo "source ok  $path $got"; else echo "SOURCE MISMATCH $path $got, want $want" >&2; bad=1; fi
done < "$here/SOURCES"
(( bad == 0 )) || exit 1
export TORCH_CUDA_ARCH_LIST=7.0 CUDA_VISIBLE_DEVICES=""
export CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-12.8} CC=${CC:-gcc-14} CXX=${CXX:-g++-14}
export PATH=$CUDA_HOME/bin:$PATH MAX_JOBS=${MAX_JOBS:-4}
mkdir -p "$src/benchmarks/deepseek_v41/v41k/build"
"$py" -I "$src/benchmarks/deepseek_v41/v41k/build.py"
so=$src/benchmarks/deepseek_v41/v41k/build/v41k.so
[[ -s "$so" ]] || { echo "build_v41k: no $so" >&2; exit 1; }
# The ops the adopted levers call (each lever checks hasattr and fails or falls back without it).
"$py" -I - "$so" <<'PYEOF'
import sys, torch
torch.ops.load_library(sys.argv[1])
need = ["moe7", "q8_aligned", "gate_up7", "q8_plan", "gate_up7p", "gate_up_fast", "down_rows", "down_rows_fast",
        "dmv13_x", "index_reduce_live", "index_scores_decode",
        "peer_gather", "hc_transition"]
miss = [n for n in need if not hasattr(torch.ops.v41k, n)]
print("v41k ops:", "all present" if not miss else "MISSING " + " ".join(miss))
sys.exit(1 if miss else 0)
PYEOF
echo "build_v41k: $so ($(stat -c %s "$so") bytes, sha256 $(sha256sum "$so" | cut -c1-12))"
