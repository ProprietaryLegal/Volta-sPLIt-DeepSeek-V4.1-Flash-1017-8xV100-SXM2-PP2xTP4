# Engine environment (PP=2). Set CUDA_VISIBLE_DEVICES to GPU INDICES: board B's four, then board C's four. vLLM's custom all-reduce maps CUDA_VISIBLE_DEVICES entries
# with int(), so UUIDs there would fail.
# (No apostrophe inside the ${...:?} message: bash pairs it as a quote even inside double quotes.)
: "${CUDA_VISIBLE_DEVICES:?set CUDA_VISIBLE_DEVICES to the Board B indices (then Board C for PP2)}"
export V41PKG_PP=2 V41PKG_DEFAULT_PROFILE=serve-pp2.yaml
export CUDA_DEVICE_ORDER=PCI_BUS_ID
# The engine is the wheel installed in $B/.venv (non-editable: its compiled extensions are in site-packages, not in
# src/vllm). Upstream runs an in-place build, so its PYTHONPATH=src and cd src are safe there; here they would shadow the
# installed vllm with a source tree that has no _C/_moe_C/_C_gguf. So site-packages goes first on PYTHONPATH (src stays
# on it only for the benchmarks package, which the wheel does not ship), and the working directory is $RUN, because
# python -m puts the working directory ahead of PYTHONPATH.
export PYTHONPATH="${ENGINE_HOME}/.venv-pp2/lib/python3.12/site-packages:${ENGINE_HOME}/src-pp2:${ENGINE_HOME}/run-pp2/tools" XDG_CACHE_HOME="${ENGINE_HOME}/run-pp2/cache" XDG_CONFIG_HOME="${ENGINE_HOME}/run-pp2/cache/config"
export FLASHINFER_WORKSPACE_BASE="${ENGINE_HOME}/run-pp2/cache" TRITON_CACHE_DIR="${ENGINE_HOME}/run-pp2/cache/triton" VLLM_NO_USAGE_STATS=1
export VLLM_WORKER_MULTIPROC_METHOD=spawn OMP_NUM_THREADS=1
export VLLM_V41K_LIB="${ENGINE_HOME}/src-pp2/benchmarks/deepseek_v41/v41k/build/v41k.so"
PY=${ENGINE_HOME}/.venv-pp2/bin/python
cd "${ENGINE_HOME}/run-pp2"
# fail fast (seconds, before a model load): vllm must come from the installed wheel, with its compiled ops
"$PY" -c 'import sys, vllm, vllm._C, vllm._C_gguf; p = vllm.__file__; sys.exit(0 if p.startswith(sys.argv[1]) else "vllm imported from " + p)' "${ENGINE_HOME}/.venv-pp2/lib/python3.12/site-packages" || { echo "env.sh: engine import check failed" >&2; return 1; }
