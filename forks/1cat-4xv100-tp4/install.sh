#!/usr/bin/env bash
# install.sh [PHASE...]: install the DS-V4.1-Flash 4-card fork on the TARGET machine (CPU only; no GPU is touched).
# Phases, in order (default all): clone series venv wheel v41k check
#   clone   git clone https://github.com/1CatAI/1Cat-vLLM into $FORK_HOME/src, detached at 899e9ed33 (#1277 merge)
#   series  tools/apply_series.sh: the 49 patches, each checked by its git tree id; the end tree is V41PKG e4b21f060
#   venv    uv venv (Python 3.12) at $FORK_HOME/.venv with #1277's pins (configs/requirements-venv.txt) + build deps
#   wheel   build the vLLM wheel from the patched tree (TORCH_CUDA_ARCH_LIST=7.0) and install it into the venv
#   v41k    v41k/build_v41k.sh: the SM70 extension, against this venv's torch, into src/.../v41k/build/v41k.so
#   check   the engine and its compiled modules import from the venv; v41k ops present; the tree is still the series end
# Resumable: a finished phase writes $FORK_HOME/logs/phase-<name>.done and is skipped next time (delete it to redo).
# Needs: git, uv, CUDA 12.8 (CUDA_HOME), gcc-14/g++-14, about 40 GB free disk, 24 GiB free RAM. Wheel build: 1-3 h at
# MAX_JOBS=4. Configure the MACHINE block of configs/4card.env (or export its variables) first.
set -euo pipefail
FORK=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=configs/4card.env
source "$FORK/configs/4card.env"
SRC=$FORK_HOME/src VENV=$FORK_HOME/.venv PY=$FORK_HOME/.venv/bin/python LOGS=$FORK_HOME/logs
UPSTREAM=https://github.com/1CatAI/1Cat-vLLM BASE=899e9ed33
END_TREE=$(grep -v '^#' "$FORK/SERIES.tsv" | tail -1 | cut -f4)
mkdir -p "$LOGS" "$FORK_HOME/wheel" "$FORK_HOME/cache"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$LOGS/install.log"; }
die() { log "FAIL: $*"; exit 1; }
export CUDA_HOME CC CXX PATH=$CUDA_HOME/bin:$PATH CUDA_VISIBLE_DEVICES=""
export TORCH_CUDA_ARCH_LIST=7.0 CMAKE_CUDA_ARCHITECTURES=70 VLLM_TARGET_DEVICE=cuda
export MAX_JOBS=${MAX_JOBS:-4} NVCC_THREADS=1 UV_LINK_MODE=copy
export VLLM_VERSION_OVERRIDE=1.5.2.dev1277+ds41v100.fork4card
export XDG_CACHE_HOME=$FORK_HOME/cache TORCH_EXTENSIONS_DIR=$FORK_HOME/cache/torch_extensions

for tool in git uv; do command -v "$tool" >/dev/null || die "$tool not on PATH"; done
[[ -x "$CUDA_HOME/bin/nvcc" ]] || die "no nvcc at $CUDA_HOME (set CUDA_HOME; #1277 used CUDA 12.8)"
"$CUDA_HOME/bin/nvcc" --version | grep -q 'release 12\.8' || log "WARN: nvcc is not 12.8 ($("$CUDA_HOME/bin/nvcc" --version | tail -1)); #1277 built with 12.8"
command -v "$CC" >/dev/null || die "compiler $CC not found (set CC/CXX)"

check_engine() {  # the engine and its compiled modules import from the venv (from /, so no source tree shadows it)
  ( cd / && "$PY" - ) <<'PYEOF'
import importlib, sys
mods = ["vllm", "vllm._C", "vllm._moe_C", "vllm._C_stable_libtorch", "vllm._C_gguf", "vllm._gguf_expert_cache_C",
        "vllm.models.deepseek_v41.model", "vllm.models.deepseek_v41.attention_ops",
        "vllm.model_executor.layers.quantization.gguf_v41_moe",
        "vllm.model_executor.layers.quantization.gguf_shared_runtime",
        "vllm.model_executor.kernels.mhc.deepseek_v41_fused", "flash_attn_v100"]
bad = 0
for m in mods:
    try:
        importlib.import_module(m); print("OK  ", m)
    except Exception as e:  # noqa: BLE001
        bad += 1; print("FAIL", m, type(e).__name__, str(e)[:200])
import vllm; print("vllm", vllm.__version__, vllm.__file__)
if not vllm.__file__.startswith(sys.prefix):
    bad += 1; print("FAIL vllm is not the venv's installed package")
from vllm.models.deepseek_v41.contract import pp_split_problem  # noqa: F401  (the PP-aware contract is in)
print("OK   contract with pp_split_problem")
sys.exit(1 if bad else 0)
PYEOF
}

phases=${*:-clone series venv wheel v41k check}
for ph in $phases; do
  if [[ -e "$LOGS/phase-$ph.done" ]]; then log "phase $ph already done; skipped"; continue; fi
  t0=$SECONDS; log "phase $ph start"
  case $ph in
  clone)
    [[ -d "$SRC/.git" ]] || git clone --no-checkout "$UPSTREAM" "$SRC" >> "$LOGS/clone.log" 2>&1 || die "clone failed"
    git -C "$SRC" checkout --detach -q "$BASE" || die "no commit $BASE in $UPSTREAM"
    ;;
  series)
    bash "$FORK/tools/apply_series.sh" "$SRC" 2>&1 | tee "$LOGS/series.log" || die "series did not apply (see $LOGS/series.log)"
    ;;
  venv)
    [[ -x "$PY" ]] || uv venv --python 3.12 "$VENV" >> "$LOGS/venv.log" 2>&1 || die "uv venv failed"
    uv pip install --python "$PY" -r "$FORK/configs/requirements-venv.txt" >> "$LOGS/venv.log" 2>&1 || die "venv pins failed"
    uv pip install --python "$PY" 'setuptools>=77.0.3,<81' 'setuptools-scm>=8' 'setuptools-rust>=1.9' 'patchelf>=0.19.1' \
      'cmake>=3.26.1' ninja packaging wheel build jinja2 regex >> "$LOGS/venv.log" 2>&1 || die "build deps failed"
    "$PY" -c 'import torch; print("torch", torch.__version__, torch.version.cuda)' | tee -a "$LOGS/venv.log"
    ;;
  wheel)
    [[ "$(git -C "$SRC" write-tree | cut -c1-12)" == "$END_TREE" ]] || die "src tree is not the series end $END_TREE"
    rm -f "$FORK_HOME"/wheel/*.whl
    (cd "$SRC" && "$PY" -m build --wheel --no-isolation --outdir "$FORK_HOME/wheel" .) > "$LOGS/wheel.log" 2>&1 \
      || die "wheel build failed (see $LOGS/wheel.log)"
    whl=$(ls "$FORK_HOME"/wheel/*.whl | head -1)
    uv pip install --python "$PY" --no-deps --reinstall "$whl" >> "$LOGS/wheel.log" 2>&1 || die "wheel install failed"
    uv pip install --python "$PY" "$whl" >> "$LOGS/wheel.log" 2>&1 || die "wheel dependency resolve failed"
    log "installed $(basename "$whl")"
    ;;
  v41k)
    bash "$FORK/v41k/build_v41k.sh" "$SRC" "$PY" 2>&1 | tee "$LOGS/v41k.log" || die "v41k build failed (see $LOGS/v41k.log)"
    [[ "$VLLM_V41K_LIB" -ef "$SRC/benchmarks/deepseek_v41/v41k/build/v41k.so" ]] \
      || log "WARN: VLLM_V41K_LIB=$VLLM_V41K_LIB is not the library just built"
    ;;
  check)
    check_engine 2>&1 | tee "$LOGS/check.log" || die "engine import check failed"
    [[ "$(git -C "$SRC" write-tree | cut -c1-12)" == "$END_TREE" ]] || die "src tree changed after the series"
    [[ -s "$VLLM_V41K_LIB" ]] || die "no v41k library at $VLLM_V41K_LIB"
    log "tree $END_TREE; v41k $(sha256sum "$VLLM_V41K_LIB" | cut -c1-12); next: edit configs/4card.env, then ./verify.sh --static"
    ;;
  *) die "unknown phase $ph" ;;
  esac
  touch "$LOGS/phase-$ph.done"; log "phase $ph done in $((SECONDS - t0)) s"
done
