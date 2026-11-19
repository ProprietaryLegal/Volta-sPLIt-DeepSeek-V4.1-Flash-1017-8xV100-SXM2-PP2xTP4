# Running it

What follows is how we run the served build: the 49-patch series, the production patches 0050 to 0059, and the 32-key
switch set of the seventh release, one request at a time as published. It comes from [engine/README.md](engine/README.md),
[docs/production.md](docs/production.md), [engine/configs/](engine/configs/), [harness/README.md](harness/README.md) and
[harness/README-v2-harness.md](harness/README-v2-harness.md). The multi-request engine work behind the three chat slots on
our host is not published, so the published tree serves one slot. Paths are placeholders: `$ENGINE_HOME` holds the
source tree (`src-pp2/`), the venv (`.venv-pp2/`) and the run directory (`run-pp2/`); `$MODEL_HOME` holds the model
files; `$REPO` is a checkout of this repository.

## 1. The engine and its patches

Clone 1Cat-vLLM at the merge of #1277, apply the 49-patch series (its script checks every step by its git tree id), then
the ten production patches in order. The tree id after each patch is the one `git write-tree` gives after `git add -A`;
each was MEASURED with `git apply --check` on the tree before it.

```bash
cd $ENGINE_HOME
git clone https://github.com/1CatAI/1Cat-vLLM src-pp2 && cd src-pp2
git checkout 899e9ed33                                               # the #1277 merge
bash $REPO/forks/1cat-4xv100-tp4/tools/apply_series.sh .             # 49 patches; checks tree b0d692425297
git apply $REPO/engine/production/0050-expert-diet.patch             # tree 4447483248bb
git apply $REPO/engine/production/0051-prefill-skip.patch            # tree 32d4a9d9b0c1
git apply $REPO/engine/production/0052-index-tiled.patch             # tree 4760febd4fe7
git apply $REPO/engine/production/0053-index-fuse.patch              # tree 421c427444a4
git apply $REPO/engine/production/0054-draft-mp-shard.patch          # tree 09cf8cc28b7b
git apply $REPO/engine/production/0055-mrv2.patch                    # tree e85291152ae9
git apply $REPO/engine/production/0056-allreduce-sum2-push.patch     # tree 007852b33339 (changes csrc/, built into _C)
git apply $REPO/engine/production/0057-prefill-iq-gemm.patch         # tree 42947e400952
git apply $REPO/engine/production/0058-system-notes-in-place.patch   # tree 1ee8ad2755b4
git apply $REPO/engine/production/0059-topk-segment-width.patch      # tree e082b9540245
```

Build vLLM from this tree into its own venv at `$ENGINE_HOME/.venv-pp2`, the path [env.sh](engine/configs/env.sh)
expects: Python 3.12, torch 2.10.0+cu128 with the pins of
[requirements-venv.txt](forks/1cat-4xv100-tp4/configs/requirements-venv.txt), CUDA 12.8, gcc-14, and
`TORCH_CUDA_ARCH_LIST=7.0`. The four-card fork's [install.sh](forks/1cat-4xv100-tp4/install.sh) shows the venv and wheel
phases (uv, `CMAKE_CUDA_ARCHITECTURES=70`, `MAX_JOBS=4`, a 1 to 3 hour wheel build); its `check` phase expects the
unpatched series end, so it does not apply to this tree. Then build the libraries:

```bash
cd $ENGINE_HOME/src-pp2
(cd benchmarks/deepseek_v41/v41idx  && TORCH_CUDA_ARCH_LIST=7.0 python build.py)   # v41idx.so
(cd benchmarks/deepseek_v41/v41pidx && TORCH_CUDA_ARCH_LIST=7.0 python build.py)   # v41pidx.so
# after the vLLM build, in the venv it serves from; build.py copies it next to gguf_prefill_iq.py
(cd benchmarks/deepseek_v41/v41prefmoe && TORCH_CUDA_ARCH_LIST=7.0 python build.py)
# on the serving machine, against that venv's torch
cd benchmarks/deepseek_v41/v41k && TORCH_CUDA_ARCH_LIST=7.0 python build.py
```

Build `v41k.so` on the machine that serves: it is a torch C++ extension, and its ABI is tied to the venv's torch. Do not
copy it in. `v41draft.so` is only needed for `VLLM_V41_DRAFT_GEMV2`, which production leaves off. Library builds are not
byte-reproducible; what the patches guarantee is the same source and the same flags as ours.

## 2. The cards and the model files

- Eight V100-SXM2 32 GB cards on two four-card SXM2 boards with NVLink inside each board. Tensor parallelism must stay
  inside a board: board B is stage 1 (layers 0-19 and the Engram lookup), board C is stage 2 (layers 20-39, the head and
  the drafter). Layer 20 is the only admissible split.
- Power and clock as in the Results section of the [README](README.md#results).
- Device order: `CUDA_VISIBLE_DEVICES` is board B's four indices, then board C's, with `CUDA_DEVICE_ORDER=PCI_BUS_ID`.
  Use indices, not UUIDs: vLLM's custom all-reduce maps the entries with `int()`, so UUIDs fail.
- Host memory for the Engram tables (110.60 GB) and the packed-KV host arena.
- The model files under `$MODEL_HOME`, byte-identical to these revisions:

| Files | Source | Size |
|---|---|---:|
| backbone and IQ2_XXS routed experts, four GGUF shards (`gguf/`) | [ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` | 138.24 GB |
| Engram tables, IQ4_NL | the same repository | 110.60 GB |
| config and tokenizer (`base/`) | [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` | small |
| DSpark drafter, FP8, three shards (`base/dspark/`) | the same repository | 7.93 GB |

The drafter folder `dspark-v41/` is generated, not downloaded. Lay the downloads out like this:

```
$MODEL_HOME/base/          config.json, model.safetensors.index.json, tokenizer.json,
                           tokenizer_config.json, encoding/                 (deepseek-ai @ 1bae0e10)
$MODEL_HOME/base/dspark/   model-00044-of-00048.safetensors, model-00045-..., model-00046-...
                           (they sit at the top level of the same repository; move or link them here)
```

Then run #1277's own script once from the engine source tree, with the venv's Python (it imports `gguf` and `regex`):

```bash
cd $ENGINE_HOME/src-pp2
python -m benchmarks.deepseek_v41.prepare_dspark --model-root $MODEL_HOME --destination $MODEL_HOME/dspark-v41
# prints {"tensors": 2401, "payload_bytes": 7932874632, "weight_conversion": false}
```

It writes the drafter's own flat `config.json` (`model_type: deepseek_v41_text`, 3 layers), an index of the 2,401 `mtp.*`
tensors and three links into `base/dspark/`. It converts no weight and refuses to overwrite: remove a hand-made
`dspark-v41/` first. Without this folder the boot fails with `'DeepseekV41Config' object has no attribute
'hidden_size'` or `num_speculative_tokens:5 must be divisible by n_predict=3`. MEASURED 2026-11-10: the script as it is
in the #1277 merge gives a `config.json` and an index byte-identical to the ones production serves from.

## 3. The profile and the switches

Copy [env.sh](engine/configs/env.sh), [run_serve.sh](engine/configs/run_serve.sh) and
[serve-pp2.yaml](engine/configs/serve-pp2.yaml) into `$ENGINE_HOME/run-pp2/`, and substitute the `${ENGINE_HOME}` and
`${MODEL_HOME}` placeholders in the profile (for example with `envsubst`). `run_serve.sh` writes its log and process
group id into `run-pp2/state/`, so that folder must exist.

The profile: tensor parallel 4, pipeline parallel 2, `max-model-len 524288`, `max-num-seqs 1`,
`max-num-batched-tokens 8192` (4,096 and 16,384 failed the near-tie gate), `kv-cache-memory-bytes 268435456` (0.25 GiB a
card, a KV pool of 2,076,870 tokens), full CUDA graphs for 1 to 6 tokens a step, synchronous scheduling, chunked
prefill, prefix caching, every expert resident (`expert_cache_offload_fraction: 0`), the DSpark drafter from
`dspark-v41/` in FP8 with 5 drafts a round, thinking on by default, the DeepSeek V4 reasoning parser and tool calls. It
listens on loopback with no API key: put your own authenticating proxy in front. [serve-pp2-mbt16384.yaml](engine/configs/serve-pp2-mbt16384.yaml)
is the 16,384-token chunk profile of test D37, which failed; it is kept for reference.

`env.sh` sets the device order, the `v41k.so` path and the cache folders, and fails in seconds when vLLM does not import
from the installed wheel. `run_serve.sh` adds #1277's serving set and starts the server in its own process group, kept
synchronous. The switch set is [rec.env](engine/configs/rec.env), sourced before the start:

```bash
# Token path and drafts
VLLM_V41_INDEX_REDUCE=1 VLLM_V41_DMV_X=1
VLLM_V41_COUPLED_DRAFTS=1 VLLM_V41_COUPLED_DRAFT_TEMP=1.0
VLLM_V41_MARKOV_SHARD=1 VLLM_V41_COUPLED_SHARD=1 VLLM_V41_COUPLED_LOCAL=1
VLLM_V41_PLAN_FUSE=1 VLLM_V41_PP_KEEP_BATCH=1
# Kernels
VLLM_V41_EXPERT_FAST=1 VLLM_V41_EXPERT_DIET=3 VLLM_V41_FUSE_ATTN_PREP=1 VLLM_V41_FUSE_ATTN_POST=1
VLLM_V41_ROUTE_FAST=1 VLLM_V41_ROUTE_WARPS=4
# Long context
VLLM_V41_PREFILL_SKIP_ROWS=3072 VLLM_V41_KV_HOT_POSITIONS=524288
VLLM_V41_INDEX_TILED=1 VLLM_V41_INDEX_TILED_LIB=<path to v41idx.so>
VLLM_V41_INDEX_FUSE=ilp4 VLLM_V41_INDEX_FUSE_LIB=<path to v41pidx.so>
# Drafter and runner
VLLM_V41_DRAFT_MP_SHARD=1 VLLM_USE_V2_MODEL_RUNNER=1
# All-reduce, hand-off, prefill experts
VLLM_SM70_MOE_ADD_ALLREDUCE=1 VLLM_V41_SUM2_PUSH_ANY=1 VLLM_SM70_TP4_PUSH_ALLREDUCE_SMALL_MESSAGES=1
NCCL_P2P_LEVEL=NVL
VLLM_V41_PREFILL_IQ_GEMM=1 VLLM_V41_PREFILL_IQ_TILES=5,4,4,4,4,4 VLLM_V41_PREFILL_IQ_GRID=0
# 2026-11-11
VLLM_V41_SYSTEM_IN_PLACE=1 VLLM_V41_TOPK_SEG=1024
# run_serve.sh adds: VLLM_V41_DOWN_ROWS=1 VLLM_V41_SESSION_PREFIX=1 VLLM_V41_PACKED_KV=1 VLLM_V41_INDEX_TILE_MB=32
# HOT_REFILL (the hot-ring refill after a prefix hit) is on by the engine's default
```

Every `VLLM_V41_*` switch defaults off in the engine, and with a switch off its code path is the old one. The two
library keys carry no fallback: a missing library fails the boot. For `VLLM_V41_SYSTEM_IN_PLACE`, unset or 0 is
the old behaviour and any value other than 0 or 1 stops the server at start. Leave asynchronous scheduling (`V41_PP2_ASYNC`) unset: it is experimental
and not used in production.

## 4. Start and check

```bash
export ENGINE_HOME=... MODEL_HOME=... CUDA_VISIBLE_DEVICES=<board B x4>,<board C x4>
source $REPO/engine/configs/rec.env
bash $ENGINE_HOME/run-pp2/run_serve.sh serve-pp2
```

The script prints the process group id and the log path. A boot takes about 2.5 to 4 minutes to ready. Then send
untimed warm-up requests ([harness/warmup.py](harness/warmup.py)): the first request of a boot JIT-compiles about ten
Triton kernels, and there is no compile cache.

Check, in this order:

1. The server answers `GET /health` and `GET /v1/models` on loopback, at the port in the profile.
2. The log shows the activation line of every switch you set, on all 8 workers. An ON arm with a missing line is
   invalid, whatever its speed.
3. Greedy output against your own reference: record one with [rerecord-greedy-ref-v2.sh](harness/rerecord-greedy-ref-v2.sh)
   on a boot you trust, then compare every later boot byte for byte. Our reference prompts and outputs are not published.

To turn thinking off for a request, pass `chat_template_kwargs: {"thinking": false}`.

## 5. Stop

```bash
kill -TERM -- -$(cat $ENGINE_HOME/run-pp2/state/serve-pp2.pid)
```

This stops the exact process group `run_serve.sh` recorded and nothing else. [harness/stop-pp2.sh](harness/stop-pp2.sh)
does the same with a 60-second wait before it escalates, and also releases the Engram memory lock that our boot
wrapper takes.

## 6. A test window

Every lever on these pages was decided with the A/B harness in [harness/](harness/): boot an arm, warm it, measure,
check activation lines and the greedy gate, then pair the arms ([docs/method.md](docs/method.md)). The scripts use four
placeholders:

```bash
export ENGINE_HOME=/path/to/engine      # venv, src-pp2, run-pp2
export BENCH_DIR=$ENGINE_HOME/bench5    # the harness scripts, arm outputs and the state log
export MODEL_HOME=/path/to/models       # base/, dspark-v41/, gguf/
export QUALITY_TOOLS=/path/to/quality   # the greedy reference compare; not published
```

`harness/serve-pp2.sh` is our boot wrapper for an arm. It expects two helpers that are not published, an Engram
memory-lock helper and a list of card ids, so adapt it or boot each arm with `run_serve.sh` as above. The prompt sets
are not published: T=0 throughput uses the built-in prompts of `ab_tput.py`; T=1 needs a JSONL of
`{"id", "prompt", "seed", "temperature", "top_p", "max_tokens"}` records.

| Step | Tool | What it decides |
|---|---|---|
| Arm | `ab-arm-t1-v2.sh <label> VAR=VAL ...` | boots with the given switches, warms, times decode-only rounds, writes a provenance line and an activation count, runs the greedy gate |
| Depth arm | `ab-depth-arm-v2.sh` with `ab_depth.py` | decode and first token at a given context depth |
| Activation | `act-check-v2.sh OFF ON` | exits 0 only when the two arms' activation counts differ |
| Pairing | `pairs_arms_v2.py --metric dec` | pairs the arms prompt by prompt and prints the ms-a-round deltas; refuses v1 arms |
| Verdict | `win3.py` | WIN, LOSE or NEUTRAL-or-UNDETECTED, with an ACTION line |
| Noise | `aa_spread_v2.py` | the A/A spread of warm-up batches |
| Near-tie trace | `trace_diverge.py` | token-by-token divergence of a pair of outputs |

An ABBA window (levers expected above 0.2 ms) runs four arms OFF ON ON2 OFF2 with new labels, then pairs and judges them:

```bash
O=$BENCH_DIR
for c in OFF ON ON2 OFF2; do
  case $c in ON*) X="$FULL VLLM_V41_EXAMPLE=1 ACT_EXPECT=on";; *) X="$FULL ACT_EXPECT=off";; esac
  bash $O/ab-arm-t1-v2.sh EX-$c $X "ACT_GREP=<a line only the ON path prints>" || break
done
python3 -I $O/pairs_arms_v2.py --metric dec $O EX-OFF EX-ON EX-OFF2 EX-ON2 EX-OFF EX-OFF2 | python3 -I $O/win3.py --gate PASS
bash $O/act-check-v2.sh EX-OFF EX-ON
```

Here `$FULL` is the production set as `VAR=VAL` arguments and `VLLM_V41_EXAMPLE` stands for the switch under test. For
levers expected at 0.2 ms or less, run ABBAABBA: `win3.py --order abbabaab <prefix>` prints the arm order, and
`win3.py --design abbaabba` judges the eight arms. The verdict rules, written before any data:

- **WIN**: average at or below -0.15 ms a round, no pair mean above +0.05, every T=1 text the same.
- **LOSE**: the mirror rule, average at or above +0.15 and no mean below -0.05.
- **NEUTRAL**: the 95 % interval lies inside plus or minus 0.15. **UNDETECTED**: the interval reaches 0.15.
  **TEXTS-DIFFER**: the speed meets WIN but a T=1 text differs, which a lever that changes numerics always does; it
  goes to the near-tie gate instead.
- The noise model is MEASURED on 36 A/A comparisons: sd 0.126 ms, T=0 and T=1 correlation 0.264, the defaults of
  `--aa-sd` and `--aa-rho`. `--upstream <reference>` keeps an inconclusive upstream-backed change on; `--gate FAIL` always
  rejects.

The near-tie gate (with the unpublished quality tools) compares greedy output with a reference at a gap of 0.10 nats and
a KL ceiling of 0.02. Never pair a v1 arm with a v2 arm: a streamed request is a different request.

Of the harness scripts, `win3.py` and `aa_spread_v2.py` print their usage with `--help`, and `win.py` runs on empty
input. `pairs_arms_v2.py` and `trace_diverge.py` take positional arguments only and do not accept `--help`.

## 7. CPU checks of this repository

These run without a card and were run on the tree of this page:

```bash
# shell syntax of every script in harness/, engine/configs/, forks/ and tools/
for f in $(git ls-files '*.sh'); do bash -n "$f" || echo "FAIL $f"; done        # 25 files, 0 failed
# the four-card fork's profile tests
python3 -m pytest -q -p no:cacheprovider forks/1cat-4xv100-tp4/tests            # 8 passed
# the data-boundary scan of the committed tree
bash tools/check_data_boundary.sh --tree HEAD                                    # data-boundary: OK (176 files, --tree HEAD)
# the verdict tool's options
python3 harness/win3.py --help
```

The four-card fork in [forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/) runs TP4 on one board with #1277's cold expert
share. Its smoke test on one board failed at boot, and its series predates patches 0052 to 0057, so it does not
reproduce the eight-card build ([docs/four-card.md](docs/four-card.md)).
