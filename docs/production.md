# Production

What serves on our host as of 2026-11-04 (afternoon), and how to reproduce it.

## Hardware

| part | what it is | role |
|---|---|---|
| GPUs | 8x NVIDIA V100-SXM2-32GB on two 4-GPU SXM2 boards; NVLink inside each board | board B: pipeline stage 1 (layers 0-19, Engram tables and hash state), TP4. Board C: stage 2 (layers 20-39, the head and the drafter), TP4 |
| PCIe | four PLX switches, two GPUs each, Gen3 x8 per GPU; since 2026-11-03 each switch on its own CPU root complex at Gen3 x16 (before: one switch on an x8 link sharing a root complex with board B) | the stage hand-off and host traffic. MEASURED 2026-11-02, before the move (512 MiB pinned host-to-device): board B 25.5 GB/s for all four cards together; board C 13.1 GB/s. Not re-measured since |
| host | AMD Threadripper PRO 3945WX (12 cores), one NUMA node, 251 GB RAM, Linux, Python 3.12, NVIDIA driver 580 | scheduler, tokenizer, the packed-KV host arena |
| power | 150 W cap per GPU, graphics clock capped at 1522 MHz | MEASURED: 200 W neutral (−0.06 ms per round) |

## Model files

| file | source | size |
|---|---|---:|
| backbone, IQ2_XXS routed experts, four GGUF shards | [ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` | 138.24 GB |
| Engram tables, IQ4_NL | same repository | 110.60 GB |
| config and tokenizer (`base/`) | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` | small |
| DSpark drafter, FP8, three shards (`dspark-v41/`) | same repository | 7.93 GB |

The files we serve are byte-identical to those revisions. 1Cat #1277's README lists the same downloads.

## Engine

1. [forks/1cat-4xv100-tp4/](../forks/1cat-4xv100-tp4/): `tools/apply_series.sh` applies 49 patches to 1Cat-vLLM #1277
   (merge `899e9ed33`): our PP2 x TP4 port (0001), 1Cat main `6db9c81` (0002), 25 open 1Cat PRs (0003-0027), our lever
   stack and fixes (0028-0048), and a CPU test (0049). Result: tree `b0d692425297`.
2. [engine/production/0050-expert-diet.patch](../engine/production/0050-expert-diet.patch), then
   [engine/production/0051-prefill-skip.patch](../engine/production/0051-prefill-skip.patch) (our prefill skip; result
   tree `32d4a9d9b0c1`, MEASURED with `git apply --check` on tree `4447483248bb`; its new `prefill_skip.py` is
   byte-identical to the deployed file), then
   [engine/production/0052-index-tiled.patch](../engine/production/0052-index-tiled.patch) (our tiled decode index
   scorer and its `v41idx` library; result tree `4760febd4fe7`, MEASURED with `git apply --check` on `32d4a9d9b0c1`;
   `index_tiled.py`, `attention_ops.py`, `v41idx.cu`, `v41idx_ref.cuh` and `build.py` byte-identical to the deployed
   files). Build `v41idx.so` with `python build.py` in `benchmarks/deepseek_v41/v41idx/`. 0050 is our expert-kernel
   instruction diet. Result: tree `4447483248bb`. Its `v41k` files are byte-identical to the source of the deployed
   `v41k.so` (MEASURED 2026-11-03: `build.py`, `v41k.cu`, `v41k_diet.cuh`, `v41k_fast.cuh`, `v41k_fast_gu.cuh`). The
   patch also carries the L1 evict-first weight-load hints of the kernel-variant sweep, because the diet was built on
   that branch; those hints alone measured neutral (−0.04 ms).
3. Then, in order (each MEASURED with `git apply --check` on the tree before it):
   [engine/production/0053-index-fuse.patch](../engine/production/0053-index-fuse.patch) (our fused prefill index
   scorer and its `v41pidx` library; result tree `421c427444a4`),
   [engine/production/0054-draft-mp-shard.patch](../engine/production/0054-draft-mp-shard.patch) (drafter projection
   sharding, plus the `DRAFT_GEMV2` switch that stays off and its `v41draft` library; result tree `09cf8cc28b7b`), and
   [engine/production/0055-mrv2.patch](../engine/production/0055-mrv2.patch) (our DeepSeek-V4.1 port of Model Runner V2;
   result tree `e85291152ae9`). After all three, 25 of the 26 files they touch are byte-identical to the deployed files
   (MEASURED 2026-11-04). The 26th, `v41pidx/build.py`, differs only in one docstring line, where we replaced our host's
   name. Build `v41pidx.so` with `python build.py` in `benchmarks/deepseek_v41/v41pidx/` (`V41PIDX_BUILD_DIR`
   overrides the output directory). `v41draft.so` (`benchmarks/deepseek_v41/v41draft/`) is only needed for
   `DRAFT_GEMV2`; production does not build it.
4. Build vLLM into a venv (torch 2.10.0+cu128; pins in
   [forks/1cat-4xv100-tp4/configs/requirements-venv.txt](../forks/1cat-4xv100-tp4/configs/requirements-venv.txt)) and
   `v41k` with `TORCH_CUDA_ARCH_LIST=7.0` on the serving machine ([engine/README.md](../engine/README.md)).

## Serving profile

[engine/configs/serve-pp2.yaml](../engine/configs/serve-pp2.yaml), with paths as `${ENGINE_HOME}` and `${MODEL_HOME}`
placeholders (substitute them, e.g. with `envsubst`, before use):

- `tensor-parallel-size: 4`, `pipeline-parallel-size: 2`; split at layer 20, the only admissible split;
- `max-model-len: 524288`, `max-num-seqs: 1`, `max-num-batched-tokens: 8192` (4,096 and 16,384 failed the near-tie
  gate);
- `kv-cache-memory-bytes: 268435456` (0.25 GiB per GPU) gives a KV pool of 2,076,870 tokens (MEASURED, engine log):
  3.96 full-length requests; the target is 2M tokens in total, so spare memory goes to speed, not more KV;
- Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER=1`, in `rec.env`) since 2026-11-04;
- FULL CUDA graphs for 1-6 tokens per step, synchronous scheduling, chunked prefill, prefix caching;
- every expert resident (`expert_cache_offload_fraction: 0`); packed-KV GPU hot ring of 524,288 positions
  (`VLLM_V41_KV_HOT_POSITIONS`, in `rec.env`);
- DSpark, FP8, 5 drafts per round;
- thinking on by default (`default-chat-template-kwargs: {"thinking": true}`), DeepSeek V4 reasoning parser, tool calls;
- loopback only, no API key: put your own authenticating proxy in front.

## Environment

- [engine/configs/env.sh](../engine/configs/env.sh): the engine environment (`CUDA_VISIBLE_DEVICES` = board B's four
  indices, then board C's; `CUDA_DEVICE_ORDER=PCI_BUS_ID`; the `v41k.so` path; an import check that fails fast).
- [engine/configs/run_serve.sh](../engine/configs/run_serve.sh): #1277's serving set (`DOWN_ROWS=1 SESSION_PREFIX=1
  PACKED_KV=1 INDEX_TILE_MB=32`) and the server start.
- [engine/configs/rec.env](../engine/configs/rec.env): the production lever set:

```
INDEX_REDUCE DMV_X COUPLED_DRAFTS (COUPLED_DRAFT_TEMP=1.0) MARKOV_SHARD COUPLED_SHARD COUPLED_LOCAL
PLAN_FUSE PP_KEEP_BATCH EXPERT_FAST FUSE_ATTN_PREP FUSE_ATTN_POST     each VLLM_V41_*=1
VLLM_V41_EXPERT_DIET=3 VLLM_V41_ROUTE_FAST=1 VLLM_V41_ROUTE_WARPS=4
VLLM_V41_PREFILL_SKIP_ROWS=3072 VLLM_V41_KV_HOT_POSITIONS=524288
VLLM_V41_INDEX_TILED=1 (VLLM_V41_INDEX_TILED_LIB = the v41idx.so path)        adopted 2026-11-04
VLLM_V41_INDEX_FUSE=ilp4 (VLLM_V41_INDEX_FUSE_LIB = the v41pidx.so path)      adopted 2026-11-04
VLLM_V41_DRAFT_MP_SHARD=1                                                     adopted 2026-11-04
VLLM_USE_V2_MODEL_RUNNER=1                                                    adopted 2026-11-04
HOT_REFILL on by default
```

23 keys. The first 17 are the production boot's recorded set of 2026-11-03. `INDEX_TILED` and `INDEX_FUSE` joined on
2026-11-04 (long context only; short context unchanged), then `DRAFT_MP_SHARD` and Model Runner V2. MEASURED on the
17-key set after the PCIe-switch move: T=0 119.0 tok/s, T=1 120.8 tok/s, decode-only 25.30 / 25.20 ms per round. On the
22-key set with Model Runner V2, which is the production set (test D54A ON arms, 2026-11-04): T=0 134.2 / 135.0 tok/s,
T=1 136.6 / 136.4, decode-only 22.26 / 22.22 and 22.17 / 22.19 ms per round. The production boot itself (up
2026-11-04 16:38Z, adoption activation lines present) has not been benchmarked yet.

## Start

```bash
export ENGINE_HOME=... MODEL_HOME=... CUDA_VISIBLE_DEVICES=<board B x4>,<board C x4>
source engine/configs/rec.env
bash $ENGINE_HOME/run-pp2/run_serve.sh serve-pp2      # copy env.sh, run_serve.sh and serve-pp2.yaml into run-pp2/
```

A boot takes about 2.5-4 minutes to ready, plus untimed warm-up requests (the first request of a boot JIT-compiles about
ten Triton kernels; there is no compile cache).
