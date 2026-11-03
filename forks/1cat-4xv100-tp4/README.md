# 1cat-4xv100-tp4: DeepSeek-V4.1-Flash on one 4x V100 board, with every lever adopted on the 8-GPU build

**Status: GPU-unverified.** Built, traced and CPU-tested on 2026-11-03. Nobody has booted this exact profile on four
GPUs yet; the smoke test is queued on our host. Run [the smoke test](#gpu-unverified-the-smoke-test) before you trust it.

We built this so the Volta sPLIt engine can run on a single 4-GPU V100 board as well as on our 8-GPU host.

## What this is

- **The engine is the 1Cat-vLLM #1277 GGUF stack**, the same engine as the 8-GPU Volta sPLIt build (not the EXL3
  engine of our [previous build](../../previous-build/)).
  - Model: DeepSeek-V4.1-Flash, GSQ-RCO IQ2_XXS routed experts, Engram in IQ4_NL, DSpark 5 drafter (FP8).
  - KV: 512K packed FP4 KV.
  - Cold experts: a `shared_original` host cache serves them.
  - Kernels: the `v41k` SM70 CUDA extension.
  - Upstream: [1CatAI/1Cat-vLLM#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277), merged as `899e9ed33`.
- **Layout:** one 4x V100-SXM2-32GB NVLink board, TP4, PP=1, all 40 layers on every rank. This is the layout #1277
  targets.
- **Source of the levers:** our 8-GPU PP2xTP4 build (V41PKG, our 1Cat-vLLM fork, at `7e9a15686`). Every lever adopted there is on in this profile where it means something at PP=1.

| Piece | Where |
|---|---|
| Patch series against `899e9ed33`: 49 patches, each verified by the git tree id it must leave | `patches/`, `SERIES.tsv` |
| Series tools: `apply_series.sh` (install), `gen_series.sh` + `series.in` (maintainers) | `tools/` |
| Serving profile and lever environment | `configs/serve-4card.yaml.in`, `configs/4card.env` |
| Venv pins (#1277's torch 2.10.0+cu128 set) | `configs/requirements-venv.txt` |
| v41k build on the target machine, plus the 12-hex source pins | `v41k/build_v41k.sh`, `v41k/SOURCES` |
| Install, start, stop, verify | `install.sh`, `start.sh`, `stop.sh`, `verify.sh` |
| GPU smoke runner and its client | `smoke-4card.sh`, `smoke_client.py` |
| CPU checks of this profile | `tests/test_fork_profile.py` |

The series ends at V41PKG `e4b21f060`, tree `b0d692425297`:
- the 8-GPU production tree `7e9a15686` (tree `6e72b034f88b`, patch 0048);
- plus one CPU test added for this fork (patch 0049; see [the PP=1 trace](#pp1-classification)).

For publication, added lines in two patches were edited, so the tree ids above differ from our private ones: absolute
home paths in 0001 became `/path/to/`, and one comment in 0039 names "the 8-GPU build" instead of our host. No code
changed. MEASURED 2026-11-03: `tools/apply_series.sh` on a fresh clone at `899e9ed33` rebuilt tree `b0d692425297`.
The 8-GPU production engine adds [our expert-kernel diet](../../engine/production/) on top of this tree.

## Install (on the target machine)

```bash
# 1. Machine settings: edit the MACHINE block of configs/4card.env, or export the same names.
#    Set FORK_HOME, the four model paths, DS41_GPUS (four PCI_BUS_ID indices of ONE NVLink board) and the port.
# 2. Build. CPU only, resumable, about 1-3 h. Needs CUDA 12.8, gcc-14 and uv.
./install.sh                        # clone series venv wheel v41k check
# 3. Check without a GPU, then boot.
./verify.sh --static
./start.sh                          # writes $FORK_HOME/run/serve-4card.{yaml,log,pid,ready}
./verify.sh                         # /health, /v1/models, one T=0 reply, lever activation lines
./stop.sh
```

- **Build v41k on the target.** `v41k.so` is a torch cpp_extension, so its ABI is tied to the venv's torch. Build it on
  the machine that will serve, never copy it in. `install.sh` does this with `TORCH_CUDA_ARCH_LIST=7.0`.
- **Model files.** Use the same downloads #1277 uses (UPSTREAM sizes, `benchmarks/deepseek_v41/README.md`):
  - backbone, four GGUF shards: 138.24 GB;
  - Engram GGUF: 110.60 GB;
  - DSpark, three HF shards: 7.93 GB;
  - the HF config and tokenizer directory (`DS41_BASE`).
- **Never commit model files.** None of them goes in this repository.

## Levers

These are the 8-GPU numbers: MEASURED on our PP2xTP4 build (DSpark 5, one request) with the ABBA harness
([method](../../docs/method.md)).
- Baseline with no levers: T=0 31.1 ms/round (99.2 tok/s); T=1 31.7 ms/round (88.0 tok/s).
- Full adopted stack: T=0 about 27.1-27.3 ms (about 114 tok/s); T=1 about 27.7-27.8 ms (about 117 tok/s).
- **These are not 4-card numbers.** See [what to expect on four cards](#what-to-expect-on-four-cards).

| Knob (value) | Series patch | What it does | 8-GPU PP2 effect (MEASURED) | PP=1 status |
|---|---|---|---|---|
| `VLLM_V41_INDEX_REDUCE=1` | 0031 | indexer top-k reduce through the custom all-reduce IPC bank, not NCCL | about -0.85 ms/round; T=1 text byte-identical across boots | **works, on** |
| `VLLM_V41_DMV_X=1` | 0036 | dense M<=6 matvecs on v41k `dmv13_x` | -0.42 ms (ABBA 6/6) | **works, on** |
| `VLLM_V41_COUPLED_DRAFTS=1`, `VLLM_V41_COUPLED_DRAFT_TEMP=1.0` | 0030, 0035 | DSpark drafts and verification share keyed Gumbel draws | T=1 acceptance 1.85 to 2.25 tokens/round, +14% tok/s; no T=0 cost | **works, on** (CPU test 0049) |
| `VLLM_V41_MARKOV_SHARD=1` | 0001, 0041 | greedy Markov draft head sharded over the TP ranks; checks itself at load | -0.2 ms at T=0 | **works, on** |
| `VLLM_V41_COUPLED_SHARD=1` | 0038 | coupled draft head from vocabulary shards in a captured graph | -0.23 ms at T=1 | **works, on** |
| `VLLM_V41_COUPLED_LOCAL=1` | 0039 | coupled verification on rank-local vocabulary shards | -0.12 to -0.24 ms at T=1 | **works, on** |
| `VLLM_V41_PLAN_FUSE=1` | 0034, 0040 | expert plan built inside the q8 quantize launch | -0.36 T=0, -0.27 T=1 | **works, on** |
| `VLLM_V41_EXPERT_FAST=1` | 0043 | routed experts on v41k `gate_up_fast` + `down_rows_fast` | down -0.68/-0.84 T=0, -0.62/-0.63 T=1; gate_up a further -0.82/-0.53 T=0, -0.64/-0.58 T=1 | **works, on** |
| `VLLM_V41_FUSE_ATTN_PREP=1`, `VLLM_V41_FUSE_ATTN_POST=1` | 0044 (registers the knobs), 0045 | decode attention prologue and epilogue fused into one launch each | average -0.19 ms | **works, on** |
| `VLLM_V41_DOWN_ROWS=1`, `VLLM_V41_SESSION_PREFIX=1`, `VLLM_V41_PACKED_KV=1`, `VLLM_V41_INDEX_TILE_MB=32` | #1277 itself | #1277's own serving set (upstream `run_serve3.sh`): G3 down rows, same-session prefix reuse, 512K packed KV | part of the baseline | **works, on** (#1277-native PP=1) |
| `VLLM_V41_HOT_REFILL=1`, `VLLM_V41_RING_REACH=124` | 0048 | [1Cat #1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341): refills the packed-KV hot ring on a same-session prefix hit | correctness fix; fired on all 8 workers | **works, on** (#1341 was written for 4 cards) |
| `VLLM_V41_PP_KEEP_BATCH=0` | 0042 | keeps the batch across PP2's empty pipeline steps | 32K -9.7%, 64K -17.4%, 128K -24.8%; short -0.17/-0.30 | **no-op at PP=1, set 0** |

**What the patches carry but leave off.** The series also contains levers that LOST or were never adopted. Each is off
by default, and the profile does not set it:
- `VLLM_V41_PRUNE_TOPP` (0029, 0032): lossy; greedy FAIL.
- `VLLM_V41_GATE_COLS` (0033, 0037): slower at M>=2.
- `VLLM_V41_ROUTE_FAST` (0033): on in the 8-GPU production REC since D34R (2026-11-03, with `VLLM_V41_ROUTE_WARPS=4`)
  under the upstream-backed default-on rule, after an ABBA of −0.165 ms/round that was not a WIN. Off here until it
  passes this board's own A/B.
- `VLLM_V41_FUSE_TRANSITION` (0044, 0047): lost. Our 8-GPU engine carries the v1 file of this off knob; the series carries v2 (0047).
- The L1-hint experiment (0046): backed out.

The upstream fixes are 0002-0027:
- 1Cat main `6db9c81`;
- open PRs #1344, #1345, #1328, #1325, #1321, #1320, #1294, #1293, #1300, #1273, #1338, #1322, #1319, #1318, #1317,
  #1316, #1315, #1314, #1309, #1308, #1307, #1306, #1305, #1304, and #1282 (which includes #1280).

`SERIES.tsv` gives one line per patch.

### PP=1 classification

Each lever was traced in the V41PKG source at `7e9a15686` along the PP=1 path. This is a code trace, not a GPU run.

- **Works at PP=1:** every adopted lever except `PP_KEEP_BATCH`.
  - Each one is either PP-generic or scoped to the TP group.
  - `INDEX_REDUCE` builds one IPC bank for the single stage. If the custom all-reduce is not fully connected over the
    four GPUs, it logs `VLLM_V41_INDEX_REDUCE=1 needs TP4 and a fully connected custom all-reduce` and falls back.
  - `PLAN_FUSE` and `EXPERT_FAST` consume the slot ids that the expert cache already resolved. They never see the
    cold path, so the cold experts that 4 cards require do not change them.
  - The fused attention handles layer 0's non-ring window (at PP=1 layer 0 keeps its paged window, as in #1277).
  - Hot refill runs on the single stage and restores Engram at `start_layer` 0.
- **No-op at PP=1:** `PP_KEEP_BATCH`.
  - `pp_keep_batch_decision` returns "pipeline_parallel_size is 1, so there are no empty pipeline steps". The runner
    and the scheduler log `... ignored` and run the default path.
  - The profile sets it to 0 so that warning does not appear.
- **Broken or unsafe:** none. No engine change was needed.
- **One interaction exists only at PP=1: cold-expert verify truncation with coupled verification.**
  - Our 8-GPU build keeps every expert resident, so it never exercised this. Four cards must offload, so the cold
    set is not empty.
  - With a cold set, `VLLM_V41_TRUNC` (default on in `gguf_shared_runtime`) makes the runner mask drafts past the
    truncation point to -1 before sampling.
  - Traced safe: the mask runs before the coupled and keyed-local samplers. Both coupled paths verify through
    `token_match_sample`, which stops at the first -1 draft.
  - Patch 0049 (`tests/models/test_deepseek_v41_fork4card_pp1.py`) pins this. It checks the order of the mask and the
    sampler calls in the AST. It runs the real `token_match_sample_kernel` under `TRITON_INTERPRET` with truncation
    1-6. It also runs a simulated coupled loop with random truncation, which must equal plain keyed sampling.
  - MEASURED: 15 passed. With the mask removed (negative control), 9 failed.
- **PP2-only code stays inert at PP=1:**
  - the accepted-draft prepend (`not is_last_rank` only);
  - the scheduler's negative-count skip;
  - the engine core's draft take (it needs a batch queue, and sync PP=1 has none);
  - the stage-2 anchor ring (layer > 0 without a ring window);
  - `StageCommit` (None when the stage spans layers 0-40).

**CPU tests, MEASURED on the build host.** The V41PKG test files for these paths were run under PP=1 with the CPU platform, one
pytest process per file: 37 files plus the new one.
- All pass except three single tests. All three are stale test fixtures, not PP=1 faults, and all three also fail on the
  production tree `7e9a15686`:
  - `test_deepseek_v41_dspark.py::test_v41_metadata_carries_noncausal_contract_into_the_existing_proposer`: its
    `SimpleNamespace` stub has no `_set_flag`.
  - `test_deepseek_v41_plan_fuse.py::test_dispatch_on_uses_fused_ops`: its AST-compiled namespace has no
    `_PLAN_FUSE_LOGGED`.
  - `test_deepseek_v41_small_fuse_knob_off.py::test_attention_knob_off`: it pins `DeepseekV41Model` to `49cb1b7`, and
    the #1341 port (0048) changed `restore_prefix`.
- `tests/test_fork_profile.py` checks that the env and yaml carry this classification. Run it with
  `python3 -m pytest -q -p no:cacheprovider forks/1cat-4xv100-tp4/tests`.

## Pending levers (off; add when it wins)

Each pending lever has a commented hook in `configs/4card.env`. None of these knobs is in the series. Each lives on its
own V41PKG branch, so add its patch to `tools/series.in` and recut the series before you turn it on.

| Lever | Knob | 8-GPU test | Under PP=1 |
|---|---|---|---|
| Async scheduling | `VLLM_V41_ASYNC=1` + `async-scheduling: true` (`start.sh ASYNC=1`) | under PP2 it LOST: crash at request end | **First candidate.** #1277 itself ran async at PP=1 (UPSTREAM: about 4 ms/round less host time than sync). None of the adopted coupled levers has async coverage, so the smoke runner's `ARMS="sync async"` arm decides it. |
| MIX side stream | `VLLM_V41_MIX_STREAM` (+ `_GROUPS`) | D33 | applies |
| Expert instruction diet | `VLLM_V41_EXPERT_DIET` (adopted value on 8 GPUs: `3`) | D34: **adopted** on the 8-GPU build (ABBA -0.871 ms/round, MEASURED 2026-11-03); [patch](../../engine/production/0050-expert-diet.patch) applies on this series' end tree | applies; not yet in this fork's profile |
| Prefill skip rows | `VLLM_V41_PREFILL_SKIP_ROWS` | D35 | applies |
| MRV2 model runner | `VLLM_USE_V2_MODEL_RUNNER=1` | D32 (port `ae8e0cb33`) | applies; motivated by the PP2 async crash |
| C3 hot ring | `VLLM_V41_KV_HOT_POSITIONS=524288` | D31 (partial, MEASURED 8-GPU on vs off: 150K 31.7 vs 31.91 ms/round, 300K 35.99 vs 36.9) | applies. The hot ring grows 16x (22 MiB MEASURED; about +330 MiB/GPU ESTIMATED). Mind the 500K-prefill memory floor below. |
| Multi-sequence interleave | `VLLM_V41_MULTI_SEQ` | D42 | **PP2-only by design** (it interleaves sequences across pipeline stages) |

`VLLM_V41_PP_KEEP_BATCH` is also PP2-only (see above).

## Memory and KV

**MEASURED, 4-card #1277 at `899e9ed`.** One board of our host, #1277's serving profile, offload 0.33, no levers,
2026-11-02. Per GPU:

| Item | Value |
|---|---|
| Free at start | 31.02 GiB |
| Model load | 26.37 GiB |
| KV pool | 0.25 GiB |
| CUDA graphs | 0.20 GiB |
| Packed KV, host latents | 360 MiB |
| Packed KV, GPU index | 85 MiB |
| Packed KV, hot ring | 22 MiB |
| Packed KV, staging | 135 MiB |
| **GPU KV cache size** | **2,076,870 tokens (3.96x at 524,288)** |

**ESTIMATED for this fork.**
- The levers add about 8 MiB per rank for the INDEX_REDUCE bank. The 8-GPU build's stage 2 logged "524296 columns,
  8.0 MiB", and PP=1 has one store of the same size.
- They add under about 50 MiB for tables and graphs. DMV_X, PLAN_FUSE, the coupled shards and hot refill allocate
  nothing large.
- That leaves about 3.5-4 GiB of headroom per GPU.
- The KV pool is fixed by `kv-cache-memory-bytes: 268435456`, so the fork should report the same **about 2,076,870
  tokens**.
- Every expert resident is impossible on four cards: the routed experts alone are 132.07 GB (UPSTREAM). The profile
  keeps #1277's measured cold share of 0.33.

**ESTIMATED host RAM.**
- Engram: 110.6 GB.
- Cold experts at 0.33: about 43.6 GB (UPSTREAM: 39.55 GB at 0.30).
- Packed-KV host latents: about 1.4 GB.
- #1277's 8 GiB reserve.
- Total about 165 GB, so plan for 192 GB or more.

**Known risk (UPSTREAM #1277 HANDOFF).** Free VRAM can fall to 25 MiB during a 500K-token prefill at PP=1. The fork adds
about 60 MiB ESTIMATED. Watch the first long-context run.

## What to expect on four cards

**MEASURED 4-card reference, #1277 `899e9ed`, no levers.** One board of our host, 2026-11-02, cards capped at
150-175 W / 1522 MHz:

| Measurement | Result |
|---|---|
| Warm decode round, end to end | 27.8 ms (GPU busy 24.89 ms). UPSTREAM: 24.9 ms; the gap is host time. |
| Warm real text | 30.8 ms/round, 97.1 tok/s |
| Fresh text | 116.7 ms/round, 25.0 tok/s, 27.4 cold-expert misses/round (the 8-GPU host's shared Gen3 x16 uplink, 12.87 GB/s aggregate). UPSTREAM: 53.5 ms and 54.5 tok/s. |
| 75K context | 35.8 tok/s, TTFT 69.1 s, prefill 1085 tok/s, 89.8 ms/round |
| Greedy, strict, across a restart | 13/16 (near-ties under the NCCL index all-reduce). INDEX_REDUCE made output boot-stable on 8 GPUs. |

**ESTIMATED.**
- The adopted kernel levers saved about 4 ms/round on 8 GPUs. At PP=1 the same 40 layers run once per round, so a warm
  round should drop by a similar amount: about 24-25 ms instead of 27.8.
- T=1 should gain the coupled-draft acceptance (about +14% or more).
- Fresh text is dominated by cold-expert fetches, so the levers move it far less. A host link faster than the 8-GPU host's would
  matter more there.
- `PP_KEEP_BATCH`'s long-context gains are PP2 host work and do not carry over.

## GPU-unverified: the smoke test

Nothing above has run on four GPUs with the levers on. Before anyone uses this profile, run:

```bash
# any 4-card host, after ./install.sh and the MACHINE block:
ARMS="sync async" ./smoke-4card.sh
```

**Refusals.** `smoke-4card.sh` starts nothing if:
- `:18042` (our PP2 server's port) or the smoke port (default 18044) is listening;
- any GPU has a compute process;
- the four indices are not one board with peer access;
- on our 8-GPU host, they are not board B (from the host's GPU map).

**Per arm, it:**
1. boots on the four GPUs (our board B is `CUDA_VISIBLE_DEVICES=0,1,4,5`, with `CUDA_DEVICE_ORDER=PCI_BUS_ID`);
2. runs a warm-up;
3. runs greedy T=0 repeat identity (3 prompts);
4. measures T=0 and T=1 ms/round and tok/s (from `/metrics`) and checks a same-session prefix hit;
5. checks every activation line and the absence of every fallback line (`verify.sh --activation`);
6. records GPU memory and the KV size, then stops the server.

**Output.** Everything goes to `$FORK_HOME/run/smoke-<UTC>/SUMMARY`. The async arm's greedy text is compared with the
sync arm's.

**Promote async if** the async arm passes greedy (identical, or near-tie only) and wins on ms/round. Then make it the
default in `serve-4card.yaml.in` and `4card.env`.

## Maintaining the series

`tools/gen_series.sh V41PKG_REPO tools/series.in OUT` re-cuts every patch from first-parent V41PKG ranges and rewrites
`SERIES.tsv` with the tree id each patch must leave. To add a lever:
1. merge its branch on V41PKG;
2. append a row to `tools/series.in`;
3. re-cut;
4. re-run `apply_series.sh` on a fresh clone at `899e9ed33`.

The patches carry abbreviated index lines and no binaries, so no 40-hex ids enter the repo.
