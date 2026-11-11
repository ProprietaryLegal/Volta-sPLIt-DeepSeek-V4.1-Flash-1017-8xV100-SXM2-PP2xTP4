# Production

What serves on our host, and how to reproduce it.

**Since 2026-11-11** the host runs the checkpoint below with three later changes: three chat slots
(`max-num-seqs: 3`), `VLLM_V41_SYSTEM_IN_PLACE=1` (patch 0058) and `VLLM_V41_TOPK_SEG=1024` (patch 0059); results in
[levers.md](levers.md#after-the-checkpoint-adopted-2026-11-11). The two keys and their patches are published here. The
three slots run on multi-request engine work later than the checkpoint that is not published: the tree and profile on
this page serve one slot.

**The 2026-11-05 checkpoint.** This build is our checkpoint: we measure it and use it as it stands, and further build and
test work happens on a separate test machine, not on this host. It is the 2026-11-04 production set plus three
adoptions: the all-reduce push path (test D44R5, 2026-11-04 evening), lever G (`NCCL_P2P_LEVEL=NVL`, installed
2026-11-05 14:06Z) and the SM70 prefill expert GEMM (test D51, installed 2026-11-05 15:12Z). One request at a time
(`max-num-seqs: 1`). Greedy identity of the production prompts, unchanged by both 2026-11-05 installs (MEASURED, the
installs' own checks): 32,768 tokens → output sha `cdf3cf45c3cf`, 131,072 tokens → `e70897e7b29e`.

## Hardware

| part | what it is | role |
|---|---|---|
| GPUs | 8x NVIDIA V100-SXM2-32GB on two 4-GPU SXM2 boards; NVLink inside each board | board B: pipeline stage 1 (layers 0-19, Engram lookup and hash state; the Engram tables are in host RAM), TP4. Board C: stage 2 (layers 20-39, the head and the drafter), TP4 |
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

### Prepare the drafter folder (required)

`dspark-v41/` is not a plain download. It is a small generated folder: the drafter's own `config.json`, its own
`model.safetensors.index.json`, and links to the three shards. Without that `config.json` the engine describes the
drafter with the parent model's nested config, and the boot fails in one of two ways:

- `AttributeError: 'DeepseekV41Config' object has no attribute 'hidden_size'`;
- `num_speculative_tokens:5 must be divisible by n_predict=3` (the parent config has `num_nextn_predict_layers: 3`;
  the drafter's own config has `0` and `dspark_block_size: 5`).

Lay the downloads out like this, then run #1277's own script once from the engine source tree, with the Python of
the venv the engine is installed in (the script imports `gguf` and `regex`):

```
$MODEL_HOME/base/                      config.json, model.safetensors.index.json, tokenizer.json,
                                       tokenizer_config.json, encoding/     (deepseek-ai @ 1bae0e10)
$MODEL_HOME/base/dspark/               model-00044-of-00048.safetensors, model-00045-..., model-00046-...
                                       (the same repository; they sit at its top level, move or link them here)
```

```bash
cd $ENGINE_HOME/src-pp2
python -m benchmarks.deepseek_v41.prepare_dspark --model-root $MODEL_HOME --destination $MODEL_HOME/dspark-v41
# prints {"tensors": 2401, "payload_bytes": 7932874632, "weight_conversion": false}
```

It writes `dspark-v41/config.json` (flat, `model_type: deepseek_v41_text`, 3 layers, `architectures:
["DSparkDeepseekV41ForCausalLM"]`), `dspark-v41/model.safetensors.index.json` (the 2,401 `mtp.*` tensors) and three
symlinks into `base/dspark/`. No weight is converted. It refuses to overwrite: remove a hand-made `dspark-v41/` first.
MEASURED 2026-11-10: the script as it is in the #1277 merge, run on the revisions above, gives a `config.json` and
an index byte-identical to the ones production serves from. `num_speculative_tokens: 5` in the profile is then
accepted as it stands.

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
4. Then [engine/production/0056-allreduce-sum2-push.patch](../engine/production/0056-allreduce-sum2-push.patch) (the
   custom all-reduce push path for V4.1's MoE-sum message; result tree `007852b33339`; it changes `csrc/`, so the vLLM
   build compiles it into `_C`) and
   [engine/production/0057-prefill-iq-gemm.patch](../engine/production/0057-prefill-iq-gemm.patch) (our SM70 prefill IQ
   GEMM and the source of its `v41prefmoe` library; result tree `42947e400952`). MEASURED 2026-11-05 with
   `git apply --check` on the tree before each, rebuilt from the published patches: the 0056 files and the three Python
   files of 0057 are byte-identical to the deployed files ([engine/README.md](../engine/README.md) lists the one known
   `envs.py` difference). Build `v41prefmoe.so` after the vLLM build with `python build.py` in
   `benchmarks/deepseek_v41/v41prefmoe/`; it is copied next to `gguf_prefill_iq.py`, where the module loads it.
5. Build vLLM into a venv (torch 2.10.0+cu128; pins in
   [forks/1cat-4xv100-tp4/configs/requirements-venv.txt](../forks/1cat-4xv100-tp4/configs/requirements-venv.txt)) and
   `v41k` with `TORCH_CUDA_ARCH_LIST=7.0` on the serving machine ([engine/README.md](../engine/README.md)).

## Serving profile

[engine/configs/serve-pp2.yaml](../engine/configs/serve-pp2.yaml), with paths as `${ENGINE_HOME}` and `${MODEL_HOME}`
placeholders (substitute them, e.g. with `envsubst`, before use):

- `tensor-parallel-size: 4`, `pipeline-parallel-size: 2`; split at layer 20, the only admissible split;
- `max-model-len: 524288`, `max-num-seqs: 1` (our host: 3 since 2026-11-11, see the top of this page),
  `max-num-batched-tokens: 8192` (4,096 and 16,384 failed the near-tie
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
VLLM_SM70_MOE_ADD_ALLREDUCE=1 VLLM_V41_SUM2_PUSH_ANY=1
VLLM_SM70_TP4_PUSH_ALLREDUCE_SMALL_MESSAGES=1                                 adopted 2026-11-04 (D44R5)
NCCL_P2P_LEVEL=NVL                                                            adopted 2026-11-05 (lever G)
VLLM_V41_PREFILL_IQ_GEMM=1 VLLM_V41_PREFILL_IQ_TILES=5,4,4,4,4,4
VLLM_V41_PREFILL_IQ_GRID=0                                                    adopted 2026-11-05 (D51)
VLLM_V41_SYSTEM_IN_PLACE=1                                                    adopted 2026-11-11 (patch 0058)
VLLM_V41_TOPK_SEG=1024                                                        adopted 2026-11-11 (patch 0059)
HOT_REFILL on by default
```

32 keys: the checkpoint's 30 and the two of 2026-11-11. The first 17 are the production boot's recorded set of 2026-11-03. `INDEX_TILED` and `INDEX_FUSE` joined on
2026-11-04 (long context only; short context unchanged), then `DRAFT_MP_SHARD` and Model Runner V2. MEASURED on the
17-key set after the PCIe-switch move: T=0 119.0 tok/s, T=1 120.8 tok/s, decode-only 25.30 / 25.20 ms per round. On the
22-key set with Model Runner V2, which is the production set (test D54A ON arms, 2026-11-04): T=0 134.2 / 135.0 tok/s,
T=1 136.6 / 136.4, decode-only 22.26 / 22.22 and 22.17 / 22.19 ms per round. The all-reduce push path took a further
0.180 ms per round off decode (D44R5, ABBAABBA, 95 % interval −0.278..−0.081). Lever G and D51 change prompt reading
only: first token at 32K −13.4 % (G) and −4.1 % (D51), each in its own window (numbers in
[levers.md](levers.md#adopted)). The checkpoint boot itself was benchmarked on 2026-11-05
([measurements.md](measurements.md#checkpoint-benchmark-2026-11-05)).

## Start

```bash
export ENGINE_HOME=... MODEL_HOME=... CUDA_VISIBLE_DEVICES=<board B x4>,<board C x4>
source engine/configs/rec.env
bash $ENGINE_HOME/run-pp2/run_serve.sh serve-pp2      # copy env.sh, run_serve.sh and serve-pp2.yaml into run-pp2/
```

The profile file is `serve-pp2.yaml`. On our host the same file is named `serve-v41pkg-pp2.yaml`, which is the name
the logs under `evidence/` show; the two differ only in the header comment and the path placeholders. The harness
scripts default to `PROFILE=serve-pp2.yaml`.

A boot takes about 2.5-4 minutes to ready, plus untimed warm-up requests (the first request of a boot JIT-compiles about
ten Triton kernels; there is no compile cache).
