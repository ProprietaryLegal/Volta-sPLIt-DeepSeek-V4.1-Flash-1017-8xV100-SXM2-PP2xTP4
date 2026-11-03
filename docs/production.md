# Production

What serves on our host as of 2026-11-03, and how to reproduce it.

## Hardware

| part | what it is | role |
|---|---|---|
| GPUs | 8x NVIDIA V100-SXM2-32GB on two 4-GPU SXM2 boards; NVLink inside each board | board B: pipeline stage 1 (layers 0-19, Engram tables and hash state), TP4. Board C: stage 2 (layers 20-39, the head and the drafter), TP4 |
| PCIe | four PLX switches, two GPUs each, Gen3 x8 per GPU; one switch in an x8 slot | the stage hand-off and host traffic. MEASURED 2026-11-02 (512 MiB pinned host-to-device): board B 25.5 GB/s for all four cards together; board C 13.1 GB/s |
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
2. [engine/production/0050-expert-diet.patch](../engine/production/0050-expert-diet.patch): our expert-kernel
   instruction diet. Result: tree `4447483248bb`. Its `v41k` files are byte-identical to the source of the deployed
   `v41k.so` (MEASURED 2026-11-03: `build.py`, `v41k.cu`, `v41k_diet.cuh`, `v41k_fast.cuh`, `v41k_fast_gu.cuh`). The
   patch also carries the L1 evict-first weight-load hints of the kernel-variant sweep, because the diet was built on
   that branch; those hints alone measured neutral (−0.04 ms).
3. Build vLLM into a venv (torch 2.10.0+cu128; pins in
   [forks/1cat-4xv100-tp4/configs/requirements-venv.txt](../forks/1cat-4xv100-tp4/configs/requirements-venv.txt)) and
   `v41k` with `TORCH_CUDA_ARCH_LIST=7.0` on the serving machine ([engine/README.md](../engine/README.md)).

## Serving profile

[engine/configs/serve-pp2.yaml](../engine/configs/serve-pp2.yaml), with paths as `${ENGINE_HOME}` and `${MODEL_HOME}`
placeholders (substitute them, e.g. with `envsubst`, before use):

- `tensor-parallel-size: 4`, `pipeline-parallel-size: 2`; split at layer 20, the only admissible split;
- `max-model-len: 524288`, `max-num-seqs: 1`, `max-num-batched-tokens: 8192`;
- `kv-cache-memory-bytes: 268435456` (0.25 GiB per GPU) gives a KV pool of 2,076,870 tokens (MEASURED, engine log):
  3.96 full-length requests; the target is 2M tokens in total, so spare memory goes to speed, not more KV;
- FULL CUDA graphs for 1-6 tokens per step, synchronous scheduling, chunked prefill, prefix caching;
- every expert resident (`expert_cache_offload_fraction: 0`);
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
HOT_REFILL on by default
```

## Start

```bash
export ENGINE_HOME=... MODEL_HOME=... CUDA_VISIBLE_DEVICES=<board B x4>,<board C x4>
source engine/configs/rec.env
bash $ENGINE_HOME/run-pp2/run_serve.sh serve-pp2      # copy env.sh, run_serve.sh and serve-pp2.yaml into run-pp2/
```

A boot takes about 2.5-4 minutes to ready, plus untimed warm-up requests (the first request of a boot JIT-compiles about
ten Triton kernels; there is no compile cache).
