# Volta sPLIt: DeepSeek-V4.1-Flash-1017 on eight V100-SXM2 32 GB cards, ISTA-DASLab's 2-bit GGUF with every routed expert on the cards, two pipeline stages of four (PP2 x TP4)

Built by **Nick Mermiges, Esq.**, founder of [PLI Labs](https://proprietarylegal.ai/labs.html) · [proprietarylegal.ai](https://proprietarylegal.ai)

[![code and JSON: ~200 tok/s](https://img.shields.io/badge/code%20and%20JSON-~200%20tok%2Fs-2EA043?style=for-the-badge)](#speed)
[![legal: ~110 tok/s](https://img.shields.io/badge/legal-~110%20tok%2Fs-1F6FEB?style=for-the-badge)](#speed)
[![prose and chat: ~85-110 tok/s](https://img.shields.io/badge/prose%20and%20chat-~85--110%20tok%2Fs-8250DF?style=for-the-badge)](#speed)
[![prompt reading at 128K: 2,200 tok/s](https://img.shields.io/badge/prompt%20reading%20at%20128K-2%2C200%20tok%2Fs-D29922?style=for-the-badge)](#speed)
[![first token at 128K: 59 s](https://img.shields.io/badge/first%20token%20at%20128K-59%20s-D29922?style=for-the-badge)](#speed)
[![context: 524K per request](https://img.shields.io/badge/context-524K%20per%20request-555555?style=for-the-badge)](#long-context-and-cached-prompts)

[![proprietarylegal.ai](https://img.shields.io/badge/proprietarylegal.ai-website-0B3D91)](https://proprietarylegal.ai) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-card-FFD21E)](https://huggingface.co/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-GGUF) [![PLI Labs](https://img.shields.io/badge/PLI%20Labs-research-1F6FEB)](https://proprietarylegal.ai/labs.html) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Hardware: 8x V100-SXM2-32GB](https://img.shields.io/badge/hardware-8x%20V100--SXM2--32GB-76B900)](#requirements) [![Method: ABBA paired](https://img.shields.io/badge/method-ABBA%20paired-555555)](docs/method.md)

Weights: the backbone and the routed experts are the
[ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) (MIT) at revision
`ad1e8991`: IQ2_XXS experts and backbone, 138.24 GB in four shards, and the Engram tables in IQ4_NL, 110.60 GB. It is
ISTA-DASLab's 2-bit quantization of [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017)
(MIT), a 551.9B-parameter mixture of experts with DeepSeek's Engram n-gram memory. The config, the tokenizer and the
DSpark drafter (FP8, 7.93 GB in three shards) are DeepSeek's, at revision `1bae0e10`. The files we serve are
byte-identical to those revisions. This repository holds no weights, no wheels and no compiled libraries, and it
downloads nothing.

This repository is the build's record as of its seventh release (2026-11-11): the 49-patch engine series and its
one-board fork ([forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/)), the ten production patches 0050 to 0059 and the
patches tested and not adopted ([engine/](engine/)), the serving profile, environment, start script and switch set
([engine/configs/](engine/configs/)), the A/B harness ([harness/](harness/)), the queue log through the 2026-11-05
checkpoint ([evidence/](evidence/)), the measurement, lever, method, quality and roadmap pages ([docs/](docs/)), and the
record of our first build on the same cards ([previous-build/](previous-build/)). It does not hold the prompt sets,
generated text, greedy references, the quality tools, server logs, or the multi-request engine work that the seventh
release's three chat slots run on: the published tree serves one slot. How to run it is in [RUNNING.md](RUNNING.md).

The engine is 1CatAI's [1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM), the SM70 fork of vLLM, at the merge of the
DeepSeek-V4.1-Flash package of [#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277) (`899e9ed33`), which runs this
model on one board of four cards with a third of the experts offloaded to host memory. Our series adds 1Cat main
`6db9c81`, 25 open 1Cat pull requests carried so the tree rebuilds exactly, our port to two boards and our lever stack,
and ends at tree `b0d692425297`; the production patches take it to tree `e082b9540245`. The two-board layout, the split
at layer 20 and the stage contract follow PLI Labs' 1Cat-vLLM pull request
[#1031](https://github.com/1CatAI/1Cat-vLLM/pull/1031) (a port of the official checkpoint to twelve and eight cards);
the port of #1277 is new code. Four SM70 CUDA libraries are built from the published source: `v41k` (#1277's expert and
dense kernels with our changes), `v41idx`, `v41pidx` and `v41prefmoe` (ours).

Every figure on this page is labelled. **MEASURED** is observed on our eight-card host, with its date and its test
(tests are short labels such as `D35`, `D54A`, `PB1103` or `lever G`; their windows and pairs are in
[docs/levers.md](docs/levers.md) and [docs/roadmap.md](docs/roadmap.md)). **ESTIMATED** is arithmetic or a model on
measurements, with its basis. **UPSTREAM CLAIM** is someone else's number, which we have not reproduced, with its source.
A figure from one run says so.

What it does:

- Eight V100-SXM2-32GB cards as two pipeline stages of four tensor-parallel cards, one stage on each NVLink board. Stage 1
  holds layers 0-19 with the Engram lookup; stage 2 holds layers 20-39, the head and the DSpark drafter. Layer 20 is the
  only admissible split. The hand-off between the boards takes NCCL's host path.
- Every routed expert resident in the 256 GiB of card memory, so no expert is paged from host memory. The Engram tables
  stay in host RAM; each round gathers only the rows it needs, about 0.12 ms a decode round (MEASURED, 52 rounds).
- 524,288 tokens of context a request from a key-value pool of 2,076,870 tokens, one request at a time; three chat slots
  on our host since 2026-11-11.
- DSpark speculative decoding with DeepSeek's FP8 drafter, five drafts a round, with coupled sampled drafts above
  temperature 0. The target verifies every draft, so the text keeps the target's distribution.
- Model Runner V2 with synchronous scheduling, full CUDA graphs for 1 to 6 tokens a step, prompt chunks of 8,192 tokens
  and prefix caching, behind vLLM's OpenAI-compatible server with the Messages endpoint, thinking on by default and tool
  calls. It listens on loopback only, with no API key.
- Every speed change is a `VLLM_V41_*` switch that defaults off, decided on milliseconds a verify round in paired ABBA
  arms ([docs/method.md](docs/method.md)), and bitwise-identical or passed the near-tie gate.

The 32 keys of the production switch set, [engine/configs/rec.env](engine/configs/rec.env):

| Keys | What it does | Release |
|---|---|---|
| `VLLM_V41_INDEX_REDUCE=1` | the index's top-k reduce through the custom all-reduce's IPC bank | first |
| `VLLM_V41_DMV_X=1` | a double-buffered Volta dense mat-vec on #1277's `dmv13` | first |
| `VLLM_V41_COUPLED_DRAFTS=1`, `VLLM_V41_COUPLED_DRAFT_TEMP=1.0` | drafter and verifier share keyed Gumbel draws | first |
| `VLLM_V41_MARKOV_SHARD=1`, `VLLM_V41_COUPLED_SHARD=1`, `VLLM_V41_COUPLED_LOCAL=1` | draft head and coupled sampler on vocabulary shards, in a captured graph | first |
| `VLLM_V41_PLAN_FUSE=1` | the experts' routing plan built inside the q8 quantize launch | first |
| `VLLM_V41_PP_KEEP_BATCH=1` | the request stays in the batch across the pipeline's empty steps | first |
| `VLLM_V41_EXPERT_FAST=1`, `VLLM_V41_EXPERT_DIET=3` | fast routed-expert kernels and their instruction diet (patch 0050) | first |
| `VLLM_V41_FUSE_ATTN_PREP=1`, `VLLM_V41_FUSE_ATTN_POST=1` | decode attention prologue and epilogue as one launch each | first |
| `VLLM_V41_ROUTE_FAST=1`, `VLLM_V41_ROUTE_WARPS=4` | the router floor, four warps | first |
| `VLLM_V41_PREFILL_SKIP_ROWS=3072` | early prompt chunks skip stage-2 window-ring rows they can never reach (patch 0051) | second |
| `VLLM_V41_KV_HOT_POSITIONS=524288` | the packed-KV hot ring at 524,288 positions (#1277's default is 32,768) | second |
| `VLLM_V41_INDEX_TILED=1`, `VLLM_V41_INDEX_TILED_LIB` | a register-tiled decode index scorer, `v41idx.so` (patch 0052) | third |
| `VLLM_V41_INDEX_FUSE=ilp4`, `VLLM_V41_INDEX_FUSE_LIB` | a fused prefill index scorer, `v41pidx.so` (patch 0053) | fourth |
| `VLLM_V41_DRAFT_MP_SHARD=1` | the drafter's `main_proj` in quarters across its board (patch 0054) | fourth |
| `VLLM_USE_V2_MODEL_RUNNER=1` | Model Runner V2 with our DeepSeek-V4.1 port (patch 0055) | fourth |
| `VLLM_SM70_MOE_ADD_ALLREDUCE=1`, `VLLM_V41_SUM2_PUSH_ANY=1`, `VLLM_SM70_TP4_PUSH_ALLREDUCE_SMALL_MESSAGES=1` | the expert sum inside the four-card all-reduce, on the push path (patch 0056) | fifth |
| `NCCL_P2P_LEVEL=NVL` | peer-to-peer only inside a board; the board-to-board hand-off goes through the host (lever G) | fifth |
| `VLLM_V41_PREFILL_IQ_GEMM=1`, `VLLM_V41_PREFILL_IQ_TILES=5,4,4,4,4,4`, `VLLM_V41_PREFILL_IQ_GRID=0` | an SM70 prefill GEMM for the routed experts, `v41prefmoe.so` (patch 0057) | fifth |
| `VLLM_V41_SYSTEM_IN_PLACE=1` | a mid-chat system message stays where it was sent (patch 0058) | seventh |
| `VLLM_V41_TOPK_SEG=1024` | the decode index's top-k in segments of 1,024 (patch 0059) | seventh |

[engine/configs/run_serve.sh](engine/configs/run_serve.sh) adds #1277's own serving set (`VLLM_V41_DOWN_ROWS=1`,
`VLLM_V41_SESSION_PREFIX=1`, `VLLM_V41_PACKED_KV=1`, `VLLM_V41_INDEX_TILE_MB=32`), and the hot-ring refill after a
prefix hit (`HOT_REFILL`, our port of 1Cat issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341)) is on by the
engine's default.

## Seventh release (2026-11-11, commits `507dffb` and `00fc962`): what changed

Four items were tested on the production host overnight, each against a rule written before its data, and three were
adopted together at 01:28Z (the fourth, the router with 8 warps, was neutral). The clock ceiling in these windows was
1,477 MHz, so a row compares only figures of one window. Every prompt was generated filler text. Cells are from [docs/levers.md](docs/levers.md#after-the-checkpoint-adopted-2026-11-11) and
[CHANGELOG.md](CHANGELOG.md).

| | Before: the checkpoint (30 keys, one slot) | After: 32 keys, three slots | Change | Measured in |
|---|---|---|---|---|
| Keys in `rec.env`; slots | 30; `max-num-seqs 1` | 32; `max-num-seqs 3` on our host | `VLLM_V41_SYSTEM_IN_PLACE`, `VLLM_V41_TOPK_SEG` added | |
| Three chats of 60K, 100K and 150K tokens taking turns for three rounds: cache hits on return | 0 of 6 | 6 of 6 | | slots window |
| First token on a return | 20.6 / 32.9 / 49.2 s | 0.57 to 0.88 s | | slots window |
| A lone request | 132.1 tok/s, 21.80 ms a decode round | 132.0 tok/s, 21.78 ms | not slower | slots window |
| Chats of 150K, 150K and 480K tokens held together | | 3 of 3 hits: 0.91 / 0.86 / 2.24 s against 49.3 / 49.3 / 170.1 s cold; least free memory on a card 7,228 MiB | | slots window |
| Near-tie gate on the rotation's turns (cached follow-ups against cold reads of the same prompt in one boot) | 6 rows | 6 rows | every row identical: PASS | slots window |
| A system note added before turn 2 of a 31,267-token chat: cached tokens | 0 | 31,248 of 31,300 | | system-note window |
| First token of turn 2 | 11.2 s | 0.51 s | | system-note window |
| The note obeyed | 10 of 10 | 10 of 10 | | system-note window |
| Decode round at 8K / 32K / 64K / 128K, the installed set against the baseline before the windows (outputs identical 8 of 8) | 22.37 / 27.46 / 23.13 / 24.70 ms | 22.20 / 27.16 / 22.80 / 24.31 ms | -0.17 / -0.31 / -0.33 / -0.40 ms, 0.8 to 1.6 % of a round | after adoption |

**Three chat slots** (`max-num-seqs: 3`). With one slot the server kept one chat's prompt cache, so when long chats took
turns every return read its whole prompt again. The slots keep three chats' caches; requests still run one at a time,
so this is not a throughput claim. They run on our multi-request engine work of 2026-11-06 and 2026-11-07, which is not
in this repository's patches. A cached reply on a chat-template turn can differ from a cold read of the same turn; that
predates the slots (What did not work, below).

**System notes keep their place** (`VLLM_V41_SYSTEM_IN_PLACE=1`, patch 0058). On the Messages endpoint a system message
sent after the first turn was moved to the front of the prompt, so every later token shifted and the chat read its whole
prompt again. With the switch the note stays where the client sent it. Unset or 0 is the old behaviour; any other value
stops the server at start.

**Top-k segments of 1,024** (`VLLM_V41_TOPK_SEG=1024`, patch 0059). Each decode round selects the top entries of the
index's score row, which was cut into segments of 8,192 scores; segments of 1,024 run more of that work in parallel, and
the selection is the same for every width. In two windows of four arms, all 16 pairs were faster (-0.08 to -0.57 ms a
round) with every output byte-identical. The adoption rule looked at 131,072 tokens only. Window 1 missed it by 0.01 ms
(-0.20 against an A/A drift of +0.21); a repeat window, fixed in writing with the arm order reversed, passed by 0.01 ms.
Both windows are in [docs/levers.md](docs/levers.md#after-the-checkpoint-adopted-2026-11-11).

Patches 0058 and 0059 were measured on our production tree, which holds the later multi-request work. The published
patches are the same changes cut against the published tree: they apply and compile there, and the patched
`serving.py` is byte-identical to the deployed file, but they were not run on the published tree. The Results tables
are the checkpoint's and were not re-measured.

The same day (commit `00fc962`), `tools/check_data_boundary.sh` was fixed. Under `pipefail`, grep's early exit killed
the sender with SIGPIPE and the script read that as "no match", so it could miss a credential-shaped string in a file
larger than about 64 KB. MEASURED with a fake token in a 240 KB file: missed 10 of 10 before, refused 10 of 10 after. The
tree published before the fix was rescanned: no credential pattern in its 176 files.

## Sixth release (2026-11-10, commit `c0813c2`): what changed

An install fix, reported by [@phacoguy](https://github.com/phacoguy) in issue #1, and no engine or measurement change.

- **The drafter folder must be generated.** The install guide listed `dspark-v41/` as three downloaded shards. It also
  needs its own `config.json` and index, written by #1277's `benchmarks.deepseek_v41.prepare_dspark`. A folder with only
  the shards fails at boot with `'DeepseekV41Config' object has no attribute 'hidden_size'` or
  `num_speculative_tokens:5 must be divisible by n_predict=3` (the parent config has `num_nextn_predict_layers: 3`; the
  drafter's own has `0` and `dspark_block_size: 5`). The script prints `{"tensors": 2401, "payload_bytes": 7932874632,
  "weight_conversion": false}`, converts no weight, writes three links into `base/dspark/` and refuses to overwrite.
  MEASURED 2026-11-10: as it is in the #1277 merge, run on the revisions above, it gives a `config.json` and an index
  byte-identical to the ones production serves from. [docs/production.md](docs/production.md#prepare-the-drafter-folder-required)
  and [RUNNING.md](RUNNING.md) give the layout and the command; the four-card fork's README points to the same step.
- **Harness default profile.** The harness scripts defaulted to `serve-v41pkg-pp2.yaml`, our host's name for the profile
  published as `engine/configs/serve-pp2.yaml`; they now default to `serve-pp2.yaml`.

## Fifth release (2026-11-05, commits `2e6f3fb`, `8781968` and `8e9f281`): the checkpoint

The 2026-11-04 production set plus three adoptions: the all-reduce push path (D44R5), lever G (`NCCL_P2P_LEVEL=NVL`)
and the SM70 prefill expert GEMM (D51). 30 keys, one request at a time. This build is the checkpoint: later work is built
and tested on a separate four-card test machine and returns to the production host only for its final serving window.
Each before is the test's own reference arms. Cells are from
[docs/levers.md](docs/levers.md#all-reduce-pipeline-hand-off-and-prefill-experts-adopted-2026-11-0405-the-2026-11-05-checkpoint)
and [docs/measurements.md](docs/measurements.md).

| | Before | After | Change | Measured in |
|---|---|---|---|---|
| Keys in `rec.env` | 23 | 30 | the all-reduce push (3 keys), lever G (1), the prefill GEMM (3) | |
| Decode round, decode-only, ABBAABBA, 8 pairs | | -0.034, -0.067, -0.138, +0.003, -0.062, -1.062, -0.056, -0.021 ms | average -0.180 ms (95 % -0.278 to -0.081); T=1 texts 11 of 11 the same; A/A +0.069 (T=0), +0.031 (T=1) | D44R5 |
| Forward of a later prompt chunk on the stage-1 board, median | 4,176 ms | 3,429 ms | | lever G timer arms |
| First token at 32,718 tokens, OFF / OFF2 against ON / ON2 | 18.99 / 19.41 s | 16.67 / 16.57 s | -13.4 % of the means; output identical (sha) | lever G |
| First token at 131,419 tokens | 69.05 / 71.48 s | 60.34 / 60.27 s | -14.2 % | lever G |
| Decode round at 32K under lever G | 28.10 / 27.95 ms | 27.74 / 27.88 ms | A/A +0.053: not a decode lever | lever G |
| First token at 32,768 / 150,000 / 300,000 tokens, before lever G | 20.40 / 82.41 / 161.77 s | 19.57 / 78.86 / 157.86 s | -4.1 / -4.3 / -2.4 %; generated tokens identical at every length; decode time ratio 0.9998 (T=0), 0.9987 (T=1) | D51 |
| Routed-expert prefill kernels on 153,600 captured rows of real routing | 35,601 us (the exact and tuned old paths 35,114 and 35,052 us) | 29,693 us | -16.6 % | D51 micro-benchmark |
| Greedy identity of the production prompts after both installs | | 32,768 tokens to output sha `cdf3cf45c3cf`, 131,072 to `e70897e7b29e`; identical 8 of 8, KL 0.0 over 1,215 positions | unchanged | D51 install |

**The all-reduce push.** Folding the shared and routed expert sum into the four-card all-reduce had lost 0.28 ms as an
environment-only switch, because this model's 61,440-byte message fell back to pull. Patch 0056 rebuilds the admission.
**Lever G** is one environment line: a step timer on the stage-1 board found the later prompt chunks waiting on the
hand-off to the other board, and with NCCL's peer-to-peer limited to a board that hand-off goes through the host.

**The prefill expert GEMM.** Prompt reading on the first stage was 44 % expert FFN (MEASURED profile, 131K prompt). The
kernel keeps 1Cat's SM70 operand decoders, FP32 HMMA mainloop and FP16 epilogue (OpenMMLab TurboMind code carried by
1Cat) and replaces the scheduling: compact per-expert member tiles, a tile family of 4 and 8 warps, and one tile choice
frozen per codec and role. Decode never enters it. Its FP64 matrix was within bound in every case and not bitwise, so it
went through the near-tie gate.

The release also brought the benchmark by kind of text, the context sweep of 135 requests from 1K to 256K tokens and the
quality results (Results, below). Commit `8e9f281` corrected the front page: it had said that all 248.8 GB of weights
lived in card memory, and the Engram tables are in host RAM.

## Fourth release (2026-11-04, afternoon, commit `a4c7c19`): what changed

Model Runner V2, the fused prefill index scorer and drafter projection sharding, all in production by 16:38Z; `rec.env`
went to 23 keys. Test D54A ran, in one window, the 22-key set on the V1 runner (OFF arms) against the same set with
`VLLM_USE_V2_MODEL_RUNNER=1` (ON arms), with the code production now runs. Every cell is copied from
[docs/levers.md](docs/levers.md#drafter-and-model-runner-adopted-2026-11-04) and [docs/measurements.md](docs/measurements.md).

| | Before | After | Change | Measured in |
|---|---|---|---|---|
| Production headline, A/B harness, T=0 / T=1 | 119.0 / 120.8 tok/s (17 keys, one boot) | 134.2 / 135.0 and 136.6 / 136.4 tok/s (two arms) | | PB1103; D54A |
| Decode-only round, T=0 / T=1 | 24.98 / 24.98 and 24.98 / 24.92 ms | 22.26 / 22.22 and 22.17 / 22.19 ms | ABBA means -2.735, -2.809, -2.756, -2.736; average -2.759 ms (95 % -2.898 to -2.620) | D54A |
| Per prompt with Model Runner V2, T=0 | 82.9 / 139.8 / 166.8 tok/s after the PCIe move (V1, 17 keys) | 93.0 / 159.5 / 187.4 tok/s at 1.14 / 2.74 / 3.49 accepted drafts a round | | PB1103; D54A |
| First token at 32,718 / 150,038 / 299,227 tokens, fused prefill index scorer, OFF / OFF2 against ON / ON2 | 19.945 / 20.166, 85.127 / 86.161, 174.113 / 176.795 s | 20.148 / 20.065, 81.323 / 81.626, 158.994 / 158.416 s | +0.3 % (noise), -4.9 %, -9.5 %; output identical (sha) | D52R2 |
| Drafter projection sharding, decode-only, 8 pairs | | average -0.130 ms | 8 of 8 faster; bitwise in every arm | D53R2 |
| The isolated drafter step | 841.7 us | 640.7 us | | the kit's GPU check |

**Model Runner V2** is vLLM's newer model runner as carried in 1Cat-vLLM, with 1Cat
[#1221](https://github.com/1CatAI/1Cat-vLLM/pull/1221)'s DSpark path. Our port adds a DeepSeek-V4.1 model state, the
DSpark speculator for V4.1, the pipeline commit hooks, dummy and capture batches that carry positions 0..n-1 for the
Engram hash, and the prefill-skip hook (without it the 150K first token was 105.53 s instead of about 83 s, D54R).
Scheduling stays synchronous. One behaviour differs: a request at a temperature above 0 that asks for logprobs uses
Model Runner V2's rejection sampler instead of our keyed draws, so its text follows the same distribution but is not the
same sample. The same-window depth sweep D55 (report-only) found Model Runner V2 2.6 to 2.9 ms a round faster than V1 at
2K, 8K, 16K and 64K with the same tokens a round, and about 1.4 ms slower at 32K, cause not known
([docs/measurements.md](docs/measurements.md#decode-and-first-token-by-depth-production-stack-ab-harness-t0-512-tokens)).
It was adopted on the decode win and the 150K result.

**The fused prefill index scorer** replaced four library calls a tile, which wrote an fp16 score tile once and read it
three times, with one kernel that keeps `mma.m8n8k4` scores in registers; no FP32 order was bitwise-identical to the old
path, so it ran under the near-tie gate. **Drafter projection sharding**: every rank of the drafter's board read the full
5,120 x 15,360 FP8 weight (78.6 MB) every round; now each computes a quarter of the output columns and the results are
all-gathered, bitwise the replicated result. The queue's automatic rule called it "not detectable" and rolled it back; it
was adopted by hand (D53A2) because it is bitwise, every pair was faster (one-sided sign test p = 0.5^8, about 0.004) and
the isolated drafter step agreed. The day's failed tests are under What did not work.

## Third release (2026-11-04, commits `971b8a8` and `444800a`): what changed

The tiled decode index scorer (`VLLM_V41_INDEX_TILED=1`, test D48, patch 0052, library `v41idx.so`; `v41k.so` untouched),
and every comparison with builds on other hardware taken off the pages. The old scoring kernel launched a block for each
32 keys of capacity; the new one walks only the live 64-key blocks and stages the query once a block, with the same FP32
multiply-add chain a dot product and the same epilogue, so it is bitwise by construction. Before the A/B: a GPU matrix of
51,090 cases with 0 mismatches, and compute-sanitizer memcheck and racecheck with 0 errors. Depth ABBA (OFF ON ON2 OFF2,
T=0, 512 tokens), copied from [docs/levers.md](docs/levers.md#long-context-adopted-2026-11-03):

| | Before (OFF) | After (ON) | Change | Pairs (ON minus OFF) | A/A (OFF2 minus OFF) | Output |
|---|---:|---:|---:|---:|---:|---|
| Decode round at 150,000 tokens | 29.98 ms | 27.88 ms | -7.0 % | -2.10 / -1.73 | +0.08 | identical, 139 rounds every arm |
| Decode round at 300,000 tokens | 34.33 ms | 29.62 ms | -13.7 % | -4.71 / -4.57 | +0.10 | identical, 89 rounds every arm |
| Short context, A/B harness T=0 and T=1, ABBA means | | | average +0.032 ms | +0.067, +0.069, -0.006, -0.001 | | texts identical; not detectable |

It was adopted on the depth win; the short-context headline stayed at 119.0 / 120.8 tok/s.

## Second release (2026-11-03, evening, commit `6f767a9`): what changed

The first MEASURED production baseline, after one PCIe switch card was moved, and two long-context adoptions: the prefill
skip (D35) and the larger hot ring (D31, adoption boot D38). Every cell is copied from
[docs/measurements.md](docs/measurements.md) and [docs/levers.md](docs/levers.md#long-context-adopted-2026-11-03).

| | Before | After | Change | Measured in |
|---|---|---|---|---|
| Production headline, A/B harness, T=0 / T=1 | about 118 / 121 tok/s (ESTIMATED: the measured stack less the diet's 0.871 ms) | 119.0 / 120.8 tok/s, 17 keys, one boot; 2.25 accepted drafts a round at T=1 | | PB1103 |
| Decode-only round, T=0 / T=1 | 25.34 to 25.54 (four arms) / 25.27 to 25.35 ms, all 17 switches before the move | 25.30 / 25.20 ms | within noise | D39; PB1103 |
| First token at 32,718 / 150,038 / 299,227 tokens, prefill skip, OFF / OFF2 against ON / ON2 | 22.634 / 22.776, 111.054 / 111.855, 263.925 / 265.040 s | 20.678 / 20.743, 88.453 / 88.462, 181.321 / 180.860 s | -8.8 / -20.6 / -31.5 %; output identical (sha) in all four arms | D35 |
| Decode round at 300K / 150K, hot ring of 524,288 positions | 36.92 / 37.12 and 31.91 / 32.10 ms | 35.99 / 35.88 and 31.70 / 31.81 ms | -1.09 / -0.25 ms; identical output | D31 |
| First token at 32K / 150K / 300K across the PCIe move, same stack | 20.68 / 88.51 / 181.59 s (means) | 20.24 / 86.97 / 177.98 s | -2.1 / -1.7 / -2.0 % (ESTIMATED arithmetic; one or two runs a length) | D37, D39; after the move |
| Greedy gate after the move | | PASS, 8 of 8 identical, KL 0 over 1,215 positions | | PB1103 |

**The PCIe move.** Before, the switch carrying two of board C's cards hung off an x8 link on a CPU root complex shared
with board B's cards. Now each of the four switches has its own root complex at Gen3 x16 (MEASURED from the PCIe link
status). Decode did not change beyond noise; the first token on long prompts came about 2 % sooner. **The prefill
skip**'s design reference is the replay rows of philbert440's
[deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100); our code is patch 0051. Its guard run (an abort
during a 150K prompt, then a resend) returned the same text as a whole run. Decode is untouched.

The same day: harness v2 (greedy references re-recorded on the deterministic stack, a decode-only round metric, a
measured A/A spread under 0.1 ms a round). Commit `f13fc27` corrected the credits of the plan fusion, router floor and
coupled-draft levers. The day's failed tests are under What did not work.

## First release (2026-11-03, commits `973760d` and `3fd86c2`): what it held

The two-board port of 1Cat-vLLM #1277 and eleven adopted levers with the expert-kernel instruction diet; the 49-patch
series and the four-card fork; the diet patch; seven patches in testing; the serving configs; the A/B harness; the day's
queue log; and the record of our previous build.

| What | Figure | Label |
|---|---|---|
| The port, no levers, A/B harness, T=0 / T=1 | 31.1 / 31.7 ms a round; 99.2 / 88.0 tok/s; 1.78 accepted drafts a round at T=1 | MEASURED |
| Plus six token-path and draft levers | 29.55 / 30.0 ms; about 105.8 / 108.4 tok/s (+6.7 %, +23 %) | MEASURED, ABBA averages |
| Plus plan fusion, keep-batch, fast expert kernels, attention fusions | about 27.1 / 27.7 ms; about 114 / 117 tok/s | MEASURED |
| Plus the expert-kernel instruction diet | about 26.2 / 26.8 ms; about 118 / 121 tok/s | ESTIMATED: the row above less 0.871 ms (ABBA) |
| Keep-batch by depth, decode round OFF to ON | 32K 32.69 to 29.51 ms (-9.7 %); 64K 37.19 to 30.73 (-17.4 %); 128K 44.73 to 33.62 (-24.8 %; 84 to 111 tok/s) | MEASURED |
| Decode round by depth before the gate/up kernels and the attention fusions | 32,768 tokens 28.84 ms; 65,536 30.05; 131,072 32.80 (114.6 tok/s) | MEASURED |

The day's long-context benchmark ([dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools),
unmodified; thinking on at high effort, cold prompts, 1,500 generated tokens) on its legal prompt, before the diet: first
token 22.3 to 22.5 s at 32,000 tokens, 111.1 to 111.7 s at 150,000 and 264.9 s at 300,000; decode 86.8 to 87.3, 79.8 to
80.3 and 71.8 tok/s. The table is in
[docs/measurements.md](docs/measurements.md#long-context-benchmark-thinking-high-2026-11-03-before-the-instruction-diet).

How it got there. #1277 runs this model on one board with a third of the experts in host memory; its cold-expert
fetches set the speed on fresh text. We ported it to two pipeline stages so that every expert fits on the cards, then
made it fast one switch at a time, each admitted only by a paired A/B on this machine. Two winners were predicted near
zero by isolated kernel benchmarks: the double-buffered mat-vec gave -0.42 ms where its micro-benchmark predicted 0.03 to
0.07. The expert kernels turned out to be issue-bound, not memory-bound (about 7 instructions a weight byte at decode,
0.46 issued a cycle), which led to the instruction diet: ABBA average -0.871 ms, T=1 texts 11 of 11 the same, greedy 7 of
8 plus one known near-tie. The router floor (-0.165 ms, inside that session's drift) was kept under our rule for
upstream-backed changes that are correct and inconclusive.

Contributors: [@yangzhuxinyzx](https://github.com/yangzhuxinyzx) (#1277), [@Peuqui](https://github.com/Peuqui) (#1263,
keep-batch), [@squibloads](https://github.com/squibloads) (issue #1341), [@Elevatormusic](https://github.com/Elevatormusic)
(TensorFold #25, coupled drafts) and [@dnv2003](https://github.com/dnv2003) (v100-skinny); see Credits.

## Results

All numbers are ours, MEASURED with our own clients on the eight-card host, on the 2026-11-05 checkpoint (30 keys, one
request at a time, DSpark five drafts a round) at 150 W per card and a 1,522 MHz graphics clock ceiling, unless a row
names another test. Thinking off, greedy, 1,024 tokens out, unless a row says otherwise. The seventh release's rows were
measured at a 1,477 MHz ceiling and are in its section above; the speed tables were not re-measured after it. The prompt
sets and generated text are not published; the arithmetic of every table is in [docs/measurements.md](docs/measurements.md).

### Speed

The context sweep: 135 requests, one at a time. Each prompt is a real document of its kind cut to the stated length in
the server's chat template: code is vLLM's Python source, structured is LegalBench items as JSON lines, legal is a public
CC BY legal corpus, prose is War and Peace and chat is a chat-style instruction over Les Misérables. A random cache salt
keeps every prompt out of the prefix cache. Two runs a cell; the largest difference was 2.7 tok/s, and greedy output was
byte-identical in 45 of 45 cells. Decode is (tokens - 1) over (last token - first token), client side.

**Thinking off, decode tok/s**

| Prompt | First token | Prompt reading | Code | Structured | Legal | Prose | Chat | Measured in |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1K | 1.22 s | 820 to 948 tok/s | 215.0 | 202.5 | 117.6 | 89.2 | 95.1 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 2K | 1.95 s | 1,024 to 1,082 tok/s | 203.6 | 207.2 | 114.8 | 97.9 | 94.5 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 4K | 3.26 s | 1,245 to 1,264 tok/s | 194.9 | 195.6 | 111.6 | 92.9 | 103.4 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 8K | 6.94 s | 1,178 to 1,188 tok/s | 207.9 | 209.0 | 109.1 | 92.2 | 108.2 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 16K | 10.4 s | 1,574 to 1,583 tok/s | 201.8 | 212.7 | 105.6 | 95.8 | 110.7 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 32K | 17.2 s | 1,894 to 1,913 tok/s | 200.5 | 206.6 | 116.5 | 90.1 | 106.9 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 64K | 30.9 s | 2,111 to 2,132 tok/s | 194.1 | 196.3 | 108.3 | 92.1 | 94.7 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 128K | 59.2 s | 2,198 to 2,220 tok/s | 182.8 | 196.5 | 110.9 | 91.1 | 95.8 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |
| 256K | 118.7 s | 2,197 to 2,222 tok/s | 160.0 | 179.7 | 103.1 | 84.1 | 80.5 | [sweep](docs/measurements.md#context-sweep-2026-11-05) |

With thinking on (reasoning effort 50, the head-to-head kit's setting, one run a cell) decode was 106.3 to 143.6 tok/s
on code and 131.3 to 177.3 on structured text; legal, prose and chat were 86.0 to 118.7 tok/s against 80.5 to 117.6 with
thinking off, and the first token was the same. Prompt reading by kind is within a few percent at every length. Both
tables are in [docs/measurements.md](docs/measurements.md#context-sweep-2026-11-05).

**Short prompts, by kind** (the checkpoint benchmark: real server-sent streams reconciled with the server's counters,
1,342 records, 0 errors; 1,024 tokens out, thinking off; median with range; tokens a round = 1 + accepted drafts)

| Kind | Greedy (T=0) | Tokens a round, T=0 | Sampled (T=1) | Tokens a round, T=1 | Measured in |
|---|---:|---:|---:|---:|---|
| Code | **213.1** (211.8 to 213.3) | 4.70 | 196.8 (188.3 to 203.8) | 4.34 | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| Structured (JSON) | **209.4** (209.3 to 210.3) | 4.63 | 205.4 (200.8 to 213.3) | 4.56 | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| Legal | **115.7** (115.3 to 115.7) | 2.56 | 108.4 (106.7 to 116.9) | 2.40 | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| Prose | **98.0** (97.7 to 98.3) | 2.17 | 87.2 (87.1 to 89.5) | 1.92 | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| Chat | **96.2** (96.1 to 96.5) | 2.11 | 93.8 (93.4 to 96.5) | 2.05 | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |

Thinking on (T=1, seeded) on four prompts of 209 to 2,048 tokens: 200.7, 151.8, 182.7 and 114.1 tok/s, token-weighted
**132.3 tok/s**. Greedy repetitions were byte-identical for every kind. Long legal prompts in the same benchmark (cold,
public CC BY legal text with a unique first line, two repetitions, median):

| Prompt | First token | Prompt reading | Decode after it | Measured in |
|---:|---:|---:|---:|---|
| 8,167 tokens | 6.57 s | 1,245 tok/s | 103.7 tok/s | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| 32,744 tokens | 16.42 s | 1,994 tok/s | 88.2 tok/s | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |
| 130,448 tokens | 58.26 s | 2,239 tok/s | 90.6 tok/s | [benchmark](docs/measurements.md#checkpoint-benchmark-2026-11-05) |

Two and three requests sent together are queued by the checkpoint (`max-num-seqs: 1`) and run one after another:
120.2 tok/s combined for two, 108.5 for three.

How to read these figures:

- **The text decides the tokens a round, not the engine.** The drafter proposes five tokens and the target verifies them
  at once, at about the same cost whatever is accepted. Accepted drafts a round, thinking off, mean over the lengths:
  code 3.72, structured 3.82, legal 1.62, prose 1.16, chat 1.33.
- **Context length matters less.** A round costs about 22.5 to 23 ms after a 1K prompt and 26.5 to 27 ms after 256K, for
  every kind. Code accepts fewer drafts deep in a long file (3.98 a round at 1K, 3.29 at 256K), so it slows the most.
- **Prompt reading depends on the length, not the kind.** It rises with length because each 8,192-token chunk carries a
  fixed cost and the two stages overlap more on long prompts.

Where the time goes. Throughput is (1 + accepted drafts a round) over the round time, so the round time is the engine's
own speed. It grows with context because the sparse-attention index scores the whole cached context each round; before
the tiled scorer, one scoring kernel took 2.3 to 3.6 ms of a round at 150K and 4.7 to 7.3 ms at 300K. All host Engram
work costs about 0.12 ms a round. The fast expert kernels reach about 290 to 415 GB/s of the card's read ceiling of
about 879 GB/s (UPSTREAM CLAIM, v100-skinny): they are limited by instruction issue and latency, which is why the
instruction diet won.

### Long context and cached prompts

| Check | Result | Measured in |
|---|---|---|
| Context | 524,288 tokens a request; KV pool 2,076,870 tokens at 0.25 GiB of KV a card, 3.96 full-length requests | the engine log |
| A literal 500,000-token prompt, one run | first token after 536 s (about 930 tok/s of prompt), then 61.7 tok/s; the benchmark stops after 1,500 reasoning tokens, so this shows the prompt fits and decodes, not a completed answer | first release |
| Needles at about 450K and 498K (449,597 to 497,347 prompt tokens) | 4 of 4 runs found all 6 needles; no foreign answers, no preemptions; about 460 s a request at 450K and 534 s at 498K, prompt reading included | [long context](docs/measurements.md#long-context) |
| Prefix-cache reuse at 250K (249,674 tokens) | cold 210 s, repeat 1.3 to 1.4 s, 249,648 tokens reused; the two hits identical to each other and to the cold answer | [long context](docs/measurements.md#long-context) |
| Prefix-cache reuse at 500K (499,636 tokens) | cold 538 to 539 s, repeat 2.2 s, 499,616 tokens reused; identical | [long context](docs/measurements.md#long-context) |
| Prefix-cache reuse at 36K to 64K, 1Cat issue #1341's design | 4 of 4 with the refill; a hit 0.67 to 0.75 s against 24.7 to 44.2 s cold; the refill ran on both stages | [long context](docs/measurements.md#long-context) |
| The prefill skip's guard run: an abort during a 150K prompt, then a resend | the same text as a whole run; hits at 36K, 64K and 150K identical to cold | D35 |
| Three long chats taking turns, three slots | 6 of 6 returns from cache, first token 0.57 to 0.88 s | seventh release, 1,477 MHz |
| Chats of 150K, 150K and 480K tokens held together, three slots | 3 of 3 hits: 0.91 / 0.86 / 2.24 s against 49.3 / 49.3 / 170.1 s cold | seventh release |

### Gates

Every adopted change passed the gates of [docs/method.md](docs/method.md#gates) before it served: greedy identity (8
greedy prompts compared byte for byte with a reference, a near-tie reported separately under a rule fixed in advance);
for kernel changes, single-card and TP4 bitwise checks over every changed layer and shape, then compute-sanitizer
memcheck, racecheck and synccheck; a CPU test and an AST comparison that the switch-off path is the old code; and the
switch's activation line on all 8 workers in every ON arm and none in the OFF arms.

- Greedy identity on the serving set: 8 of 8 identical, KL 0 over 1,215 positions, after the PCIe move (PB1103) and
  after the D51 install.
- Bitwise: Model Runner V2 against the V1 runner (T=0 3 of 3, T=1 12 of 12, greedy 8 of 8, D54A); the tiled decode
  index scorer (51,090 GPU cases, 0 mismatches, D48); the drafter sharding (every arm, D53A2).
- Near-tie gate PASS: the fused prefill index scorer (greedy 8 of 8, T=1 texts 11 of 11, D52R2); the prefill expert GEMM
  (504 of 1,280 FP64 cases bit-identical, at most 48 ulp, greedy 8 of 8, D51); the instruction diet (T=1 texts 11 of 11,
  greedy 7 of 8 plus one known near-tie, D34); the three chat slots (every row identical).
- Sanitizers: compute-sanitizer memcheck, racecheck and synccheck clean for the diet, the tiled scorer and the prefill
  GEMM, on one card and on each TP4 worker.
- Repeatability: greedy output byte-identical in 45 of 45 cells of the context sweep; the checkpoint benchmark's 1,342
  records with 0 errors.
- **LegalBench, MEASURED 2026-11-05: 0.716 balanced accuracy over 22 tasks** (issue 0.614, rule 0.693, conclusion
  0.722, interpretation 0.777, rhetoric 0.690). Official base prompts and scoring; greedy, thinking off, 1,292 items, 0
  errors. A reply that commits to no label scores as wrong: 4 such replies, all in `proa`
  ([docs/quality.md](docs/quality.md#legalbench-measured-2026-11-05)).
- **MMLU-Pro, MEASURED 2026-11-05: 79.9 %** ±1.5, 700 items (50 from each of the 14 subjects), lm-eval 5-shot chain of
  thought, temperature 0, 11 replies cut at the 2,048-token limit. **HumanEval+ pass@1: 89.6 %** on the plus tests (147
  of 164) and 94.5 % on the base tests, EvalPlus, temperature 0. Both with thinking off; thinking on was not run.
- **Fidelity to the original model, MEASURED 2026-11-05.** Position by position against reference logits computed once
  from the original DeepSeek-V4.1-Flash-1017 with DeepSeek's reference implementation ([@sudoingX](https://github.com/sudoingX)'s
  `p4_kld.py` method; each panel sequence sent as token ids, greedy, `prompt_logprobs` 20, no prefix-cache hits):

  | Panel | Positions | Top-1 agreement | KL, lower bound (mean) | KL p99 | NLL original | NLL served |
  |---|---:|---:|---:|---:|---:|---:|
  | General (8 domains, 199 conversations) | 254,846 | **89.0 %** | **0.132** | 1.71 | 0.470 | 0.564 |
  | Legal (210 sequences) | 71,080 | **92.5 %** | **0.156** | 3.00 | 0.197 | 0.301 |

  Closest on code, math, tool calls and extraction (89 to 99 % top-1), furthest on chat, writing and multilingual text
  (81 to 86 %). The KL covers the tokens in both top lists plus one bucket for the rest, so it is a lower bound. It
  measures the 2-bit quantization, not the speed work
  ([docs/quality.md](docs/quality.md#kl-divergence-against-the-original-model-served-path)).
- **The quant, UPSTREAM CLAIM.** ISTA-DASLab report the IQ2_XXS build scoring the same as the unquantized release on
  AIME25 (100.00), GPQA-Diamond (90.91) and LiveCodeBench v6 (89.71) at reasoning effort 50: 100 % recovery
  ([model card](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF)). We have not reproduced it,
  and those benchmarks are small (AIME25 is 30 problems), so they can hide small losses.

These figures say how closely the build tracks the original model and its own references. They do not by themselves say
that its answers are better for a given kind of work, and answer quality in use is not established by them.

### Run-time inputs

| Input | Value | Source |
|---|---|---|
| Model files | backbone and IQ2_XXS experts, four GGUF shards, 138.24 GB; Engram IQ4_NL, 110.60 GB (ISTA-DASLab @ `ad1e8991`); config and tokenizer (`base/`) and the DSpark drafter, FP8, three shards, 7.93 GB (deepseek-ai @ `1bae0e10`); byte-identical to those revisions | [docs/production.md](docs/production.md#model-files) |
| The drafter folder | generated by #1277's `prepare_dspark`: `{"tensors": 2401, "payload_bytes": 7932874632, "weight_conversion": false}`; `config.json` and index byte-identical to production's | sixth release |
| The engine tree | the 49-patch series on `899e9ed33` gives tree `b0d692425297`; patches 0050 to 0059 end at `e082b9540245`, each MEASURED with `git apply --check` on the tree before it; every tree is listed in RUNNING.md | [engine/README.md](engine/README.md) |
| The patches against the deployed files | after 0053 to 0055, 25 of the 26 touched files byte-identical (the 26th differs in one docstring line); 0056's four `csrc/` and config files and 0057's three Python modules byte-identical; the deployed `envs.py` differs only in switch registrations | [engine/README.md](engine/README.md) |
| Compiled libraries | `v41k`, `v41idx`, `v41pidx`, `v41prefmoe` and vLLM's `_C` built from the published source with `TORCH_CUDA_ARCH_LIST=7.0`; library builds are not byte-reproducible, so the claim is the same source and the same flags | [engine/README.md](engine/README.md) |
| Venv | torch 2.10.0+cu128 with the pins of `requirements-venv.txt`, Python 3.12 | [forks/1cat-4xv100-tp4/configs/](forks/1cat-4xv100-tp4/configs/requirements-venv.txt) |
| KV memory | `kv-cache-memory-bytes: 268435456` (0.25 GiB a card) gives 2,076,870 tokens; the target is 2M tokens in all, so spare memory goes to speed | [docs/production.md](docs/production.md#serving-profile) |
| Device order | `CUDA_VISIBLE_DEVICES` = board B's four indices, then board C's, with `CUDA_DEVICE_ORDER=PCI_BUS_ID`; indices, not UUIDs, because the custom all-reduce maps entries with `int()` | [engine/configs/env.sh](engine/configs/env.sh) |
| Host-to-device bandwidth, 512 MiB pinned, before the PCIe move | board B 25.5 GB/s for its four cards together; board C 13.1 GB/s; not re-measured since | [docs/production.md](docs/production.md#hardware) |

### Earlier serving sets

| Set | Date | Decode, thinking off (A/B harness, T=0) | Thinking on (T=1) | Label |
|---|---|---:|---:|---|
| The port of #1277, no levers | 2026-11-03 | 99.2 tok/s | 88.0 | MEASURED |
| Plus six token-path and draft levers | 2026-11-03 | about 105.8 | about 108.4 | MEASURED (ABBA) |
| Plus plan fusion, keep-batch, fast expert kernels, attention fusions, the diet (first release) | 2026-11-03 | about 118 | about 121 | MEASURED / ESTIMATED |
| Plus prefill skip, hot ring, PCIe move: 17 keys (second release) | 2026-11-03 | 119.0 | 120.8 | MEASURED, one boot |
| Plus both index scorers and drafter sharding, V1 runner: 22 keys (D54A's OFF arms) | 2026-11-04 | 120.2 to 120.5 | 121.8 to 122.0 | MEASURED, two arms |
| Plus Model Runner V2: 23 keys (fourth release) | 2026-11-04 | 134.2 to 135.0 | 136.4 to 136.6 | MEASURED, two arms |
| Plus all-reduce push, lever G, prefill GEMM: 30 keys (the checkpoint) | 2026-11-05 | about 135.2 | about 137.6 | ESTIMATED: the row above less 0.180 ms a round |
| Plus three slots and two keys: 32 keys (seventh release) | 2026-11-11 | a lone request 132.0 tok/s at 1,477 MHz (another prompt set) | | MEASURED |

The table uses one fixed set throughout (3 x 1,024 greedy tokens; a seeded T=1 thinking-on set of 12 prompts), so its
rows compare; the by-kind tables above use other prompts. The time a verify round went from 31.1 / 31.7 ms (T=0 / T=1)
for the port to 23.2 to 23.4 / 23.8 ms with Model Runner V2, MEASURED, and about 23.1 / 23.6 ms at the checkpoint,
ESTIMATED; the table is in [docs/measurements.md](docs/measurements.md#decode-toks-and-ms-per-round-ab-harness-2026-11-0304).

The first token across the sets (cold, MEASURED; the checkpoint's cells are the benchmark's 32,744 and 130,448 tokens,
the others the A/B harness depth runs at 32,718, 150,038 and 299,227 tokens):

| Prompt | 2026-11-03 port | Plus the prefill skip | Plus the fused index scorer, Model Runner V2 | The checkpoint |
|---|---:|---:|---:|---:|
| 32K | 22.6 s | 20.1 s | 19.4 s | **16.4 s** |
| 128K | not run | not run | 69.0 to 71.5 s (before the NCCL hand-off) | **58.3 s** |
| 150K | 111.1 s | 87.0 s | 81.3 to 82.8 s | not run |
| 300K | 263.9 s | 178.0 s | 158.4 to 159.0 s | not run |

**The earlier build on these cards.** Our first DeepSeek-V4.1 build on the same eight cards (2026-11-01) served
philbert440's [EXL3 pack](https://huggingface.co/philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100) on his SM70
engine ([philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100)) with three small patches of
ours and the Engram tables in host RAM. MEASURED by its own method: 71.2 to 71.6 ms a verify round, 42 to 46 tok/s with
thinking off and 31.4 with thinking on; requests of up to 327,680 tokens, three at a time. Its record is in
[previous-build/](previous-build/).

## The served settings

The serving boot runs vLLM's OpenAI-compatible API server from [engine/configs/serve-pp2.yaml](engine/configs/serve-pp2.yaml)
on the eight cards, board B's four first: tensor parallel 4, pipeline parallel 2, `max-model-len 524288`,
`max-num-seqs 1` in the published profile (3 on our host since 2026-11-11), `max-num-batched-tokens 8192`,
`kv-cache-memory-bytes 268435456`, `dtype half` with GGUF loading, full CUDA graphs for 1 to 6 tokens, synchronous
scheduling, chunked prefill, prefix caching, every expert resident (`expert_cache_offload_fraction: 0`), the DSpark
drafter in FP8 with `num_speculative_tokens: 5`, the `deepseek_v41` tool-call parser and the `deepseek_v4` reasoning
parser. Thinking is on by default; a request passes `chat_template_kwargs: {"thinking": false}` to turn it off. It
listens on loopback with no API key. Paths in the profile are `${ENGINE_HOME}` and `${MODEL_HOME}` placeholders.

The environment is [engine/configs/env.sh](engine/configs/env.sh) (device order, the `v41k.so` path, and an import check
that fails in seconds when vLLM does not come from the installed wheel), #1277's serving set from
[run_serve.sh](engine/configs/run_serve.sh), and the 32 keys of `rec.env` in the table at the top. The two library keys
carry no fallback: a missing library fails the boot. Unset as served: `VLLM_V41_DRAFT_GEMV2`, asynchronous scheduling,
and the switches of the tests that failed, which the patches carry off by default. A boot takes about 2.5 to 4 minutes
to ready; the first request of a boot JIT-compiles about ten Triton kernels, and there is no compile cache.

## Requirements

- Eight Tesla V100-SXM2-32GB cards on two four-card SXM2 boards with NVLink inside each board. Tensor parallelism stays
  inside a board; the pipeline hand-off between the boards goes over PCIe. On our host four PLX switches carry two cards
  each at Gen3 x8 per card, each switch on its own CPU root complex at Gen3 x16.
- Host memory for the Engram tables (110.60 GB) and the packed-KV host arena: our host has 251 GB of RAM in one NUMA
  node, on an AMD Threadripper PRO 3945WX (12 cores), with Linux, Python 3.12 and NVIDIA driver 580.
- Volta has FP16 `mma.sync.m8n8k4` only: no FP8 or BF16 tensor-core math, no `cp.async`, no `ldmatrix`. Every IQ format
  is decoded in software into FP16 operands.
- The engine rebuilt from this repository: 1Cat-vLLM at `899e9ed33`, the 49-patch series, the production patches 0050 to
  0059, vLLM built into its own venv (torch 2.10.0+cu128; CUDA 12.8, gcc-14 and uv for the fork's installer), and the
  `v41k`, `v41idx`, `v41pidx` and `v41prefmoe` libraries built with `TORCH_CUDA_ARCH_LIST=7.0` on the machine that
  serves (`v41k` is a torch C++ extension, its ABI tied to the venv's torch).
- The model files above, with the drafter folder generated once by `prepare_dspark`.
- An authenticating proxy in front of the server if anything other than the host itself will call it.
- For the CPU checks only Python 3, pytest and bash ([RUNNING.md](RUNNING.md#7-cpu-checks-of-this-repository)).

## Running it

[RUNNING.md](RUNNING.md) gives the steps: the engine and its patches, the cards and the model files with the drafter
folder, the profile and the switch set, the start and its checks, the stop, an A/B window with the harness and its
verdict rules, the one-board fork, and the CPU checks. [docs/production.md](docs/production.md) and
[engine/README.md](engine/README.md) are the pages the steps come from.

## What did not work

Each of these was built and tested on this machine. Figures are milliseconds a verify round, ABBA averages on the A/B
harness, unless the item says otherwise; the full table with every pair is in [docs/levers.md](docs/levers.md#did-not-work).

**Expert top-p pruning** (0rand's TensorFold `TF_DSV41_EXPERT_TOPP` at 0.85): 78 tok/s and greedy FAIL. It drops experts
the target would use, so the divergence is built into the method.

**Asynchronous scheduling.** On the V1 runner it crashed at request end on invalid sampled token ids; with a request-end
guard (D41) it ran clean through a 20-request soak with aborts but cost +1.678 ms (95 % +1.539 to +1.817). On Model
Runner V2 it gave -0.085 to -0.117 ms, bitwise, about 0.4 %, with no verdict run; it needs its own profile and is off.

**TP8 across both boards** (D36): no-go at the probe. The best modelled round was 24.65 ms against a 22.0 ms bar,
because the eight-way all-reduce across the boards measured 30.8 us against 5.28 us for four cards inside a board.

**Prompt chunks other than 8,192.** 16,384 (D37) gave first token +17.5 % at 32K and +5.6 % at 150K and failed the
near-tie gate. 4,096 saved 5.6 % at 32K and nothing at 128K, then failed the near-tie gate (D43: 6 of 8 identical, top-2
gaps 0.31 and 0.78 nats against a bar of 0.1). 2,048 was slower; above 16,384 the model refuses.

**Fused prefill attention, exact-softmax mode** (lever A mode 2, a port of philbert440's SM70 sparse prefill attention):
first token -11.4 % at 32,768 tokens and -10.4 % at 131,072, but numerics gate FAIL: identical 1 of 8, a confident token
moved at a top-2 gap of 0.406 nats, KL mean 0.0109 over 366 positions. The difference is the order of the score sums;
the bitwise mode is under Next.

**Split-K tensor-core decode attention** (`ATTN_HMMA=2`, D47R2): average -0.143, not detectable, and near-tie gate FAIL
(a confident token moved in 6 of 8 rows, KL mean 0.0058). **The FP16-packed shared-expert down kernel** (`SHARED_DOWN`,
D49R): 25.30 to 25.15 ms a round, near-tie gate FAIL (KL max 0.17). Both were rejected on quality.

**The expert "wave" down kernel** (`EXPERT_WAVE`, D45R4): ABBAABBA, 8 pairs, average +0.216 (95 % +0.118 to +0.314), gate
PASS. Detectably slower.

**The fused layer transition.** v1 was slower; v2 took 26.8 us against 16.53 us for the pair it replaces; the variant
without the early path (D50R2) gave +0.020 ms (95 % -0.078 to +0.118), neutral.

**A side stream for the mixing step** (`MIX_STREAM`, D33C): numerics passed, but stand-ins lost 0.19 to 0.73 ms and the
graph-topology check found no real fork and join in the captured graph. Parked until a new design.

**Probabilistic sharded drafts and draft temperatures** (D46): four variants gave +0.05 to +0.15 accepted drafts a round
at T=1 but cost +0.5 to +1.55 ms, -3.1 to +0.6 % tok/s. Draft temperature 1.2 gave -2.9 %. At most 3 verified drafts a
round lost 0.877 accepted drafts a round, -14.5 % tok/s; 3 or 4 drafts a round are refused at boot, since the
drafter's block size is 5.

**The bitwise FP8 drafter mat-vec** (`DRAFT_GEMV2`, D53R): with the sharding it gave -0.069 ms, not detectable, and the
isolated drafter step was 780.1 us against 627.8 us with the sharding alone. It stays off.

**Expert kernel variants and memory hints.** 19 expert-kernel variants were bit-clean and none beat production. L1
prefetch with evict-first weights was neutral (-0.04 ms), an L2 warm-up of the next weight matrix on a side branch lost,
a deeper dense-kernel prefetch was 1.2 to 5 us slower, and a lookup-free IQ1_M repack was a no-go before a build (-4.4 %
instructions against a 20 % gate, +35.7 % bytes).

**Router changes.** The gate-column router was slower at 2 or more tokens a step (18.12 against 14.82 us at 6). The
router with 8 warps instead of 4 (2026-11-11) was neutral: average -0.027 (95 % -0.125 to +0.071).

**Small host and tuning changes.** The suggested dense-kernel tiling failed greedy (D43R: 2 of 8 identical); the FP8
tuning set was neutral; CPU pinning gave +0.079 ms (95 % -0.020 to +0.177); a spin-loop wait in the broadcast queue gave
+0.04 to +0.09 ms; the indexer overlap in prefill was neutral and bitwise; a higher per-card power cap gave -0.06 ms,
neutral.

**Engram rows cached in spare card memory**: not built. All host Engram work costs about 0.12 ms a round, a round needs
all 288 rows, and full residence is 103 GiB against about 44 GiB free on the stage-1 board.

**Two requests at once on the V1 runner** (D42): the boot failed and so did its diagnostic; withdrawn. On Model Runner V2,
two- and three-request output matches single-request output exactly (49,152 generated positions), but a combined
throughput gain is not established.

**The four-card fork** ([forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/)): its smoke test on one board (D40) failed at
boot, and the series predates patches 0052 to 0057. It is GPU-unverified ([docs/four-card.md](docs/four-card.md)).

**Model Runner V2 at the 32K prompt** is about 1.4 ms a round slower than the V1 runner (D55), the only length where it
is. Cause unknown, INCONCLUSIVE.

**Cached chat-template turns.** A cached reply can differ from a cold read of the same turn: 2 of 4 turns differed in one
check on the one-slot server, before the slots. A second check that recorded token probabilities found every compared row
identical, but only 1 of its 4 returns came from cache. The size and cause of the differences are not measured.

## Next

Built and tested on the separate four-card test machine first; each comes to the production host only through a paired
window, and none of these is a result. From [docs/roadmap.md](docs/roadmap.md):

- **Fused prefill attention, bitwise mode 3**: the fused prefill attention with production's summation order. Built;
  bit-identical to production's attention on every synthetic case tried (40 shapes, 17 to 8,192 tokens, context 0 to
  300K), sanitizers clean. ESTIMATED from mode 2's window: first token -11 to -14 % at 32K and -10 to -13 % at 128K.
- **Prefill expert GEMM follow-ups**: the D51 kernel on the real production shapes, and mixed M64/M32 tiles (3,396
  real-shape cases bit-identical; the best variant -10 % expert-kernel time, not yet separated from plain retuning).
- **Concurrency on Model Runner V2**: decode kernels for two to four requests at once, each request's output identical
  to running it alone (ESTIMATED 2 to 3 times aggregate decode at four requests), and memory for four requests (a
  row-block Engram gather, 1Cat issue [#1342](https://github.com/1CatAI/1Cat-vLLM/issues/1342), and prefill scratch
  reuse).
- **Single-request decode**: fewer, fused small kernels and one launch a layer for the experts (ESTIMATED +3 to +8 %).
- **The 32K round under Model Runner V2**: a device trace of the block-table gather and padding, the first suspects.
- **The decode kernels that failed the near-tie gate** (`ATTN_HMMA`, `SHARED_DOWN`): find the element-level difference
  and whether a bitwise form keeps the speed.
- **The four-card fork** rebuilt on the current patches before it is tried again.

## Related builds

Other PLI Labs builds of DeepSeek-V4.1-Flash-1017 on V100 cards: [Volta Max uPLIft](https://github.com/ProprietaryLegal/Volta-Max-uPLIft-FP4-DeepSeek-V4.1-Flash-1017-NVFP4-8xV100-SXM2-PP2xTP4) ·
[Volta Full NVFP4](https://github.com/ProprietaryLegal/Volta-Full-NVFP4-DeepSeek-V4.1-Flash-8xV100) ·
[Volta 12X AmPLIfy](https://github.com/ProprietaryLegal/Volta-12X-AmPLIfy-DeepSeek-V4.1-Flash-1017-NVFP4-12xV100-SXM2-PP3xTP4).
The Volta architecture and kernel research they stand on: [volta-v100-research](https://github.com/ProprietaryLegal/volta-v100-research).

## Work with PLI Labs

[PLI Labs](https://proprietarylegal.ai/labs.html) is the open research arm of Proprietary Legal Intelligence. PLI builds
AI around an organization's own work product: retrieval over its documents, staged workflows, validation of every output
and attorney review before anything goes out. This stack is how we run that privately, on hardware we own. If you want
private, on-prem LLM serving of your own, from choosing the hardware to the measured stack and the workflows on top, we
consult on exactly that: [proprietarylegal.ai](https://proprietarylegal.ai).

## Licence

Original documentation and code are Apache-2.0 ([LICENSE](LICENSE)); see [NOTICE](NOTICE). Patches against third-party
code keep that code's licence; patch 0057 carries 42 OpenMMLab TurboMind / 1Cat SM70 headers with their original notices
and their Apache-2.0 licence beside them. No model weights, wheels, compiled libraries or prompt corpora are distributed
here.

## Credits

This build stands on other people's work: DeepSeek (the model, the DSpark drafter, the Engram design); ISTA-DASLab (the
GSQ-RCO GGUF served here); ggml (the GGUF container and the IQ formats); 1CatAI and the authors of 1Cat-vLLM's SM70 work:
[@yangzhuxinyzx](https://github.com/yangzhuxinyzx) (#1277, which this build ports and extends; #183, #344, #1338),
[@Peuqui](https://github.com/Peuqui) (#1263, #1221, #1280 and series patches #1344, #1345, #1294, #1293, #1273, #1282),
[@squibloads](https://github.com/squibloads) (issue #1341 and its test design; #1328, #1325), and
[@Leonccaa](https://github.com/Leonccaa), [@andrewleech](https://github.com/andrewleech),
[@SabaTech-dev](https://github.com/SabaTech-dev) and [@elight](https://github.com/elight), whose open pull requests the
series carries; the vLLM project; Phil Tompkins ([@philbert440](https://github.com/philbert440): the engine and EXL3 pack
of our earlier build, the replay-row design behind the prefill skip, the fused SM70 indexer and the sparse prefill
attention that our fused prefill work starts from; his 1Cat pull request #1243 as [@rivetphilbot](https://github.com/rivetphilbot)
stacks on our #1031); Dennis Vertzyas ([@dnv2003](https://github.com/dnv2003), v100-skinny: Volta kernel and bandwidth
findings, cited, no code copied); [@sudoingX](https://github.com/sudoingX) (the `p4_kld.py` fidelity method and its
general panel); TensorFold ([@Elevatormusic](https://github.com/Elevatormusic), coupled sampled drafts, #25) and
[@0rand](https://github.com/0rand) (expert top-p pruning, tested and not adopted); OpenMMLab (the TurboMind code inside
the prefill GEMM); NVIDIA (compute-sanitizer); and [@phacoguy](https://github.com/phacoguy), whose issue #1 fixed the
install guide. Every source, with what we took from it, is in [CREDITS.md](CREDITS.md).

Our own upstream work: 1Cat-vLLM [#651](https://github.com/1CatAI/1Cat-vLLM/pull/651) (an SM70 drafter-loading fix in the
engine this build runs on, merged 2026-09-26), [#1021](https://github.com/1CatAI/1Cat-vLLM/pull/1021) (block-FP8 dense
weights kept in FP8 on Volta, merged 2026-11-16), and the open [#1031](https://github.com/1CatAI/1Cat-vLLM/pull/1031)
and [#1030](https://github.com/1CatAI/1Cat-vLLM/pull/1030) ([docs/upstream-contributions.md](docs/upstream-contributions.md)).
On 2026-11-05 we opened twenty 1Cat-vLLM pull requests with this build's port and the levers that won, each new switch
off by default. Read with `gh pr view` on 2026-11-19, twelve are merged
([#1372](https://github.com/1CatAI/1Cat-vLLM/pull/1372), [#1373](https://github.com/1CatAI/1Cat-vLLM/pull/1373),
[#1375](https://github.com/1CatAI/1Cat-vLLM/pull/1375), [#1380](https://github.com/1CatAI/1Cat-vLLM/pull/1380),
[#1381](https://github.com/1CatAI/1Cat-vLLM/pull/1381), [#1382](https://github.com/1CatAI/1Cat-vLLM/pull/1382),
[#1383](https://github.com/1CatAI/1Cat-vLLM/pull/1383), [#1384](https://github.com/1CatAI/1Cat-vLLM/pull/1384),
[#1385](https://github.com/1CatAI/1Cat-vLLM/pull/1385), [#1386](https://github.com/1CatAI/1Cat-vLLM/pull/1386),
[#1387](https://github.com/1CatAI/1Cat-vLLM/pull/1387), [#1390](https://github.com/1CatAI/1Cat-vLLM/pull/1390)) and eight
are open, among them the two-board port [#1370](https://github.com/1CatAI/1Cat-vLLM/pull/1370) and Model Runner V2
[#1379](https://github.com/1CatAI/1Cat-vLLM/pull/1379) (also #1371, #1374, #1376, #1377, #1388, #1389). If you build on this repository, please credit them as well.
