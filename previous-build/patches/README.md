# Patches for DeepSeek-V4.1-Flash-1017 on the SM70 engine

These diffs apply to [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100) at tag
`ds41-vision-20261025b` (commit `23cec6a9`). They are ours; the files they modify are the engine's (Apache-2.0).

| file | what it changes | status |
|---|---|---|
| [`0001-numa-single-node.patch`](0001-numa-single-node.patch) | `v100/serve_ds41.sh`: `--numa-bind-nodes 0 0 0 0 1 1 1 1` becomes `0 0 0 0 0 0 0 0`, for a host with one NUMA node | **production** since 2026-10-31 |
| [`0002-gmu1-cudagraph-sizes-and-profiler-switch.patch`](0002-gmu1-cudagraph-sizes-and-profiler-switch.patch) | `v100/serve_ds41.sh`, `v100/ds41_common.sh`: `DS41_CUDAGRAPH_SIZES` replaces the CUDA-graph capture list, and `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS` is forwarded to the server, each only when set | applied in production, **inert** (neither variable is set); the experiment that used it was not promoted ([GMU1](../docs/experiments.md#gmu1-grow-the-kv-pool)) |
| [`0003-mp1-exl3-tiled-smem-staging.patch`](0003-mp1-exl3-tiled-smem-staging.patch) | `csrc/sm70_turbomind/ops/exl3_moe_sm70.cu`: shared-memory-staged k-tile loads for the 16- and 32-row tiles (layout 1, mul1) of the EXL3 tiled MoE prefill kernel, behind `VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1` (default off) | **production** since 2026-11-01, in a rebuilt `_C` |
| [`mp1-harness/`](mp1-harness/) | the single-GPU harness that produced the 0003 kernel numbers | measurement tool |

0001 and 0003 and the harness are byte-identical to the copies first published in
[deepseek-v4-flash-v100](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100/tree/main/patches/v4.1-flash-1cat-vllm).
The numbering follows our internal series; patch comments refer to it.

```bash
cd deepseek-v4.1-v100 && git checkout ds41-vision-20261025b
for p in 0001-numa-single-node 0002-gmu1-cudagraph-sizes-and-profiler-switch 0003-mp1-exl3-tiled-smem-staging; do
  git apply --check /path/to/patches/$p.patch && git apply /path/to/patches/$p.patch
done
```

## 0001: single NUMA node

The upstream launcher binds the eight ranks to NUMA nodes 0 and 1 (one node per NVLink quad). Our host has a single
NUMA node (one 12-core Threadripper PRO 3945WX), so the patch binds all eight ranks to node 0.

## 0002: KV-experiment switches

Two opt-in switches for the KV-pool experiment, both inert unless set:

- `DS41_CUDAGRAPH_SIZES='[1,2,...]'` replaces the `cudagraph_capture_sizes` list in the launcher's
  `--compilation-config` argument.
- `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS` is forwarded to the API server. The stock launcher forwards only
  `VLLM_DS41_*` variables, so without this line an exported value would be silently ignored.

Results: turning the estimate off grew the pool to 1,194,319 tokens but cost +9-13 % per verify round; a trimmed list
`[1..12,16,18]` with utilisation 0.945 grew it by 1.0 % and lost byte identity on 4 of 16 checks. Neither was promoted.

## 0003: shared-memory-staged EXL3 tiled MoE prefill

This is the first step of the design in the engine's `docs/moe_prefill_persistent.md`. Each warp walks the same k range
of its 32-column strip as `exl3_tiled_kwarp_kernel`, but loads CH k-tiles of trellis words at a time with coalesced
128-bit `__ldg` into registers, one chunk ahead, stores them to a per-warp shared-memory ring, and each lane then gathers
the words `LaneWords::load` would have read from global memory. Decode, MMA order, k summation order and the cross-warp
reduction are unchanged, so outputs are bit-identical to the upstream kernel. The 64-row tile stays on the upstream
register path (staging was slower there at every chunk size we tried). Launch also requires the trellis base (and the
fused second trellis) to be 16-byte aligned; otherwise it falls back to the upstream kernel.

Applying it changes compiled source (`csrc/`), so the wheel's `vllm/_C.abi3.so` must be rebuilt; applying the diff
without rebuilding leaves the source and the binary disagreeing.

### Kernel level (2026-10-31)

One V100-SXM2-32GB, graphics clock capped at 1425 MHz, 180 W, no server, no checkpoint; T = 1,016 tokens, TP rank 0,
random trellis words and activations, routing drawn from the engine's `v100/balance/v1-ab24` histograms.

- `git apply --check` passes at the pinned tag; the patched file compiles with the engine's include set (nvcc 12.8,
  sm_70), no spills.
- Dispatch check (`mp1-harness/mp1_dispatch.py`, knob off against on in two processes, layers 5 and 12, two
  repetitions each): every run bit-identical (`torch.equal`). Tiled-pass totals (16 + 32 + 64-row tiers), off → on:

| layer, rep | gate | down |
|---|---|---|
| 5, r1 | 2.255 → 2.021 ms (−10.4 %) | 2.240 → 1.943 ms (−13.2 %) |
| 5, r2 | 2.273 → 1.994 ms (−12.3 %) | 2.217 → 2.009 ms (−9.4 %) |
| 12, r1 | 2.563 → 2.320 ms (−9.5 %) | 2.498 → 2.248 ms (−10.0 %) |
| 12, r2 | 2.577 → 2.343 ms (−9.1 %) | 2.502 → 2.314 ms (−7.5 %) |

The 64-row tier runs the same kernel in both processes; its spread (±3 %) is this harness's run-to-run noise.

### In the server (2026-11-01)

Rebuilt `_C` plus the knob, Engram from NVMe, against the baseline (DDR4-2666, 1425 MHz cap, 180 W): greedy 16 / 16
byte-identical, functional checks 15 / 15, warm 75K first token 26.39 s against 27.02 s (−2.33 %, CI −3.15..−1.50),
per-round decode time unchanged (decode does not use the tiled kernel). In production since 2026-11-01 05:19 UTC with
resident Engram. Full record: [MP1](../docs/experiments.md#mp1-staged-exl3-moe-prefill-kernel).

## Rebuilding `_C`

From a `git archive` of the pinned checkout with 0003 applied, offline (no network during the build):

```bash
export CC=gcc-14 CXX=g++-14 TORCH_CUDA_ARCH_LIST=7.0 VLLM_CUTLASS_SRC_DIR=<a CUTLASS checkout>
cmake <src> -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DVLLM_TARGET_DEVICE=cuda \
  -DVLLM_PYTHON_EXECUTABLE=<the engine venv>/bin/python -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.8/bin/nvcc \
  -DFETCHCONTENT_BASE_DIR=<build>/fc -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DVLLM_SM70_79T_PREFILL=OFF \
  -DCUTLASS_INCLUDE_DIR=<CUTLASS>/include -DCUTLASS_TOOLS_UTIL_INCLUDE_DIR=<CUTLASS>/tools/util/include \
  -DCMAKE_JOB_POOLS:STRING=compile=8 -DNVCC_THREADS=1
nice -n 19 cmake --build . -j 8 --target _C     # 81 steps, ~16 min cold; ~77 s incremental after 0003
```

Two configure errors came up, and both were fixed:

- "VLLM_SM70_79T_PREFILL requires SM70 FA2": `-DVLLM_SM70_79T_PREFILL=OFF` fixes it; that option affects only the FA2
  target.
- `cutlass/cutlass.h: No such file`: the CUTLASS copy we built against (4.5.0 headers, bundled with an installed
  flashinfer) has no CMakeLists, so the include directories are passed explicitly. Upstream pins 4.4.2.

Install the new `_C.abi3.so` into the engine's venv with the server stopped and keep the wheel's original for rollback.
We also built the same tree without 0003 as a fidelity control. The build is memory-hungry at `-j 8`; on a host with
other workloads, a lower `-j` avoids running out of RAM.

## mp1-harness

- `mp1_bench.py` builds `mp1_ext.cu`, which includes the upstream tiled kernel (extracted unmodified from the pinned
  `exl3_moe_sm70.cu` at build time) and the staged kernel (`mp1_smem.cuh`), feeds both the same inputs, compares outputs
  bit for bit and times each tier with CUDA events.
- `mp1_dispatch.py` builds `mp1_dispatch_ext.cu` from the **patched** `exl3_moe_sm70.cu` (first `#include` through
  the end of `launch_tiled`, unmodified) and calls `launch_tiled` the way `exl3_moe_tiled` does. The knob is read once
  per process, so run it twice: knob off with `--save`, knob on with `--compare`.
- `--plan` expects `{"layers": {"<layer>": [[expert_id, K], ...]}}`. The pack's `exl3_moe_plan.json` stores K as a
  384-digit string per layer, so convert it first (same K values).

```bash
export TORCH_CUDA_ARCH_LIST=7.0 CUDA_VISIBLE_DEVICES=<one V100>
python mp1_bench.py --upstream <engine checkout> --plan plan-list.json --build build --layer 5 --ch 4 8 16 --iters 50
VLLM_DS41_MOE_EXL3_PREFILL_SMEM=0 python mp1_dispatch.py --patched <patched exl3_moe_sm70.cu> \
  --upstream <engine checkout> --plan plan-list.json --build build-d --layer 5 --save ref.pt
VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1 python mp1_dispatch.py --patched <patched exl3_moe_sm70.cu> \
  --upstream <engine checkout> --plan plan-list.json --build build-d --layer 5 --compare ref.pt
```

The harness needs the engine's Python package installed (it imports `vllm.models.deepseek_v41`). Apache-2.0, as the
engine.
