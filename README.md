# Volta sPLIt: DeepSeek-V4.1-Flash-1017 on 8x V100-SXM2, split PP2 x TP4

## 134.2 tok/s decode · 136.6 tok/s thinking on · 524K context per request · 8x V100 from 2018

[![decode: 134.2 tok/s](https://img.shields.io/badge/decode-134.2%20tok%2Fs-2EA043?style=for-the-badge)](#tokens-per-second)
[![thinking on: 136.6 tok/s](https://img.shields.io/badge/thinking%20on-136.6%20tok%2Fs-1F6FEB?style=for-the-badge)](#tokens-per-second)
[![vs previous V100 build: 3.0x](https://img.shields.io/badge/vs%20previous%20V100%20build-3.0x%20per%20round-8250DF?style=for-the-badge)](#the-progression-in-toks)
[![first token at 300K: 159 s](https://img.shields.io/badge/first%20token%20at%20300K-159%20s%2C%20was%20264-D29922?style=for-the-badge)](#long-prompts)
[![decode round at 300K: -13.7%](https://img.shields.io/badge/decode%20round%20at%20300K-%E2%88%9213.7%25-D29922?style=for-the-badge)](#long-context-decode-the-tiled-index-scorer)
[![context: 524K](https://img.shields.io/badge/context-524K%20per%20request-555555?style=for-the-badge)](docs/measurements.md#long-context)

Built by **Nick Mermiges, Esq.**, founder of [PLI Labs](https://proprietarylegal.ai/labs.html) · [proprietarylegal.ai](https://proprietarylegal.ai)

[![proprietarylegal.ai](https://img.shields.io/badge/proprietarylegal.ai-website-0B3D91)](https://proprietarylegal.ai) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-card-FFD21E)](https://huggingface.co/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-GGUF) [![PLI Labs](https://img.shields.io/badge/PLI%20Labs-research-1F6FEB)](https://proprietarylegal.ai/labs.html) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Hardware: 8x V100-SXM2-32GB](https://img.shields.io/badge/hardware-8x%20V100--SXM2--32GB-76B900)](#hardware) [![Method: ABBA paired](https://img.shields.io/badge/method-ABBA%20paired-555555)](docs/method.md)

## Tokens per second

<table>
<tr>
<td align="center"><h1>134.2</h1>tok/s decode<br><sub>thinking off, T=0<br>MEASURED, production switch set</sub></td>
<td align="center"><h1>136.6</h1>tok/s, thinking on<br><sub>T=1, our 12-prompt set<br>MEASURED, 2.25 accepted drafts per round</sub></td>
<td align="center"><h1>84.6&#8209;87.3</h1>tok/s, thinking high<br><sub>legal prompt, long-context benchmark<br>MEASURED 2026-11-03, older stack</sub></td>
<td align="center"><h1>159&nbsp;s</h1>to the first token<br>of a 300,000-token prompt<br><sub>MEASURED (was 263.9 s, then 178.0 s)</sub></td>
<td align="center"><h1>61.7</h1>tok/s after a<br>500,000-token prompt<br><sub>MEASURED 2026-11-03</sub></td>
</tr>
</table>

<sub>Single stream, one request at a time, on our host: 8x V100-SXM2-32GB, 150 W per card, DSpark 5 drafts per round.
MEASURED = observed on this host. The 134.2 / 136.6 tok/s are the first Model Runner V2 arm of test D54A (2026-11-04),
which booted exactly today's production switch set (23 keys, [engine/configs/rec.env](engine/configs/rec.env)) with
the production patches: 3,072 greedy tokens in 22.89 s and 8,445 thinking-on tokens in 61.83 s, first-token time
included; 22.26 and 22.17 ms per round decode-only; bitwise-identical output to the V1-runner arms. The second arm of
the same window measured 135.0 / 136.4 tok/s. The full benchmark of the production boot runs after the current test
queue. The 300K first token (158.4-159.0 s) was measured on 2026-11-04 with the V1 runner and the fused prefill index
scorer (test D52R2); with Model Runner V2 it has been measured at 150K only (next sections). The long-context
benchmark rows are from 2026-11-03.</sub>

### The progression, in tok/s

| build (8x V100-SXM2-32GB, same host) | date | decode, thinking off | thinking on | label |
|---|---|---:|---:|---|
| [Previous build](previous-build/): EXL3 pack on philbert440's SM70 engine | 2026-11-01 | 42-46 | 31.4 | MEASURED (its own method) |
| **Volta sPLIt**: PP2 x TP4 port of 1Cat #1277, no speed levers | 2026-11-03 | 99.2 | 88.0 | MEASURED |
| + six token-path and draft levers | 2026-11-03 | ~105.8 | ~108.4 | MEASURED (ABBA) |
| + fused quantize plan, keep-batch, fast expert kernels, attention fusions | 2026-11-03 | ~114 | ~117 | MEASURED |
| + expert-kernel instruction diet | 2026-11-03 | ~118 | ~121 | ESTIMATED then (−0.871 ms ABBA) |
| + prefill skip and the larger GPU hot ring: all 17 switches | 2026-11-03 | 118.3-118.5 | 119.9-120.5 | MEASURED, 2 arms |
| production after the PCIe-switch move | 2026-11-03 | 119.0 | 120.8 | MEASURED, one boot |
| + tiled and fused index scorers, drafter projection sharding (22 keys, V1 runner) | 2026-11-04 | 120.2-120.5 | 121.8-122.0 | MEASURED, 2 arms (D54A OFF) |
| **+ Model Runner V2: production since 2026-11-04** | 2026-11-04 | **134.2-135.0** | **136.4-136.6** | MEASURED, 2 arms (D54A ON) |

"Thinking off" is 3 x 1,024 greedy tokens; "thinking on" is a seeded temperature-1 set of 12 prompts with thinking
enabled. Both come from the same A/B harness ([method](docs/method.md)). The previous build used other prompts, so the
fair engine comparison is the time per verify round: 71.2-71.6 ms there against 23.4 ms measured here (same timing,
first token included; 22.26 ms decode-only), **about 3.0x faster per round** (71.2 / 23.4 = 3.04, ESTIMATED arithmetic).

**The PCIe-switch move (2026-11-03).** We moved one PCIe switch card. Before, the switch carrying two of board C's GPUs
hung off an x8 link on a CPU root complex shared with board B's GPUs; now each of the four switches has its own root
complex at Gen3 x16 (MEASURED from the link status: four x16 Gen3 upstream links on four root complexes). Each GPU's own
link to its switch stays Gen3 x8, as SXM2 baseboards are built. Same eight GPUs, same NVLink boards. Effect: decode
unchanged within noise (25.30 ms per round decode-only after, 25.34-25.54 in four same-day arms before), and first-token
time on long prompts about 1.7-2.1 % lower (table below). Small samples: one or two runs per length.

### By text type

Per-type decode (code, structured output, chat, prose) has **not been measured on this build yet**; it runs after the
current test queue. What we know today: tok/s follows the drafter's acceptance, which follows the text. Our greedy set
accepts about 2.2 drafts per round; the legal prompt of our long-context benchmark ([dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools)) with high-effort thinking
accepts 1.2-1.6. That is why the same engine shows ~119 tok/s on one set and
~85 on the other.

### Long prompts

| prompt | first token | prompt reading | decode after it | label |
|---|---:|---:|---:|---|
| 124 tokens | 0.4 s | – | 84.6-84.7 tok/s | MEASURED 2026-11-03, 3 runs |
| 32,000 tokens | 22.3-22.5 s | ~1,430 tok/s | 86.8-87.3 tok/s | MEASURED 2026-11-03, 2 runs |
| 150,000 tokens | 111.1-111.7 s | ~1,350 tok/s | 79.8-80.3 tok/s | MEASURED 2026-11-03, 2 runs |
| 256,000 tokens | 215.5 s | ~1,190 tok/s | 65.5 tok/s | MEASURED 2026-11-03, 1 run |
| 300,000 tokens | 264.9 s | ~1,130 tok/s | 71.8 tok/s | MEASURED 2026-11-03, 1 run |
| 500,000 tokens (literal) | 536 s | ~930 tok/s | 61.7 tok/s | MEASURED 2026-11-03, 1 run |
| repeat of a 500K prompt (prefix cache) | 2.2 s | 499,616 tokens reused | – | MEASURED 2026-11-03 |

Long-context benchmark ([dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools)): temperature 1, thinking high, 1,500 generated tokens, cold prompts on an idle server.
Those rows were measured before the prefill skip and the hot ring; they will be re-run.

**First token on the 17-switch stack** (A/B harness depth run, T=0, 512 generated tokens, cold prompts, MEASURED
2026-11-03 after the PCIe-switch move; prefill skip and the 524,288-position hot ring on; the 2026-11-04 changes below
come on top):

| prompt | first token | prompt reading | ms per round after it | before the switch move (same stack) | label |
|---|---:|---:|---:|---:|---|
| 2,061 tokens | 2.40-2.41 s | – | 25.73-25.92 | 2.40-2.42 s | MEASURED, 2 runs |
| 32,718 tokens | **20.11-20.38 s** (was 22.6 s) | ~1,620 tok/s | 26.96 | 20.65-20.71 s | MEASURED, 2 runs |
| 65,589 tokens | **37.6-37.7 s** | ~1,740 tok/s | 27.50-27.56 | – | MEASURED, 2 runs |
| 150,038 tokens | **86.93-87.00 s** (was 111.1 s) | ~1,725 tok/s | 29.58-30.02 | 88.32-88.78 s | MEASURED, 2 runs |
| 299,227 tokens | **177.98 s** (was 263.9 s) | ~1,680 tok/s | 34.45 | 181.26-182.03 s | MEASURED, 1 run |

"Was" is the same stack without the prefill skip (its A/B, below). "Before the switch move" is the prefill-profile test's
three base arms of the same afternoon. Mean change across the move: 32K −2.1 %, 150K −1.7 %, 300K −2.0 % (ESTIMATED
arithmetic on 1-3 runs per side: 20.24 vs 20.68 s, 86.97 vs 88.51 s, 177.98 vs 181.59 s). Prompt reading = prompt tokens
/ first-token time. The "ms per round after it" column predates the tiled index scorer (next).

#### Long-context decode: the tiled index scorer

Adopted 2026-11-04 (`VLLM_V41_INDEX_TILED=1`, test D48): a register-tiled, persistent replacement for the decode
indexer's scoring kernel, bitwise-identical to it. MEASURED on the production stack, A/B harness depth runs (T=0, 512
tokens, arms OFF ON ON2 OFF2):

| context | ms per round OFF | ms per round ON | change | pairs (ON − OFF) | A/A (OFF2 − OFF) | output |
|---|---:|---:|---:|---:|---:|---|
| 150,000 tokens | 29.98 | **27.88** | **−7.0 %** | −2.10 / −1.73 | +0.08 | identical, 139 rounds every arm |
| 300,000 tokens | 34.33 | **29.62** | **−13.7 %** | −4.71 / −4.57 | +0.10 | identical, 89 rounds every arm |
| short (A/B harness T=0 and T=1) | – | – | +0.032 ms average | +0.067, +0.069, −0.006, −0.001 | – | texts identical; not detectable |

Short-context speed did not change. At long context a round is now 2.1 ms shorter at 150K and 4.7 ms shorter at 300K;
the sparse-attention scorer was most of the growth of round time with context depth.

#### Long-prompt reading: the fused prefill index scorer

Adopted 2026-11-04 (`VLLM_V41_INDEX_FUSE=ilp4`, test D52R2): our SM70 kernel computes the prefill indexer's per-rank
head sums for a block of tiles in one launch, with the scores kept in registers, then runs the same all-reduce and one
top-k launch per block. Its summation order (`ilp4`) is not bitwise-identical to the old path, so it went through the
near-tie gate, which it passed. MEASURED, A/B harness depth runs (T=0, 512 tokens, arms OFF ON ON2 OFF2, one prompt
per length per arm, V1 runner):

| prompt | first token OFF / OFF2 | first token ON / ON2 | change | output |
|---|---:|---:|---:|---|
| 32,718 tokens | 19.945 / 20.166 s | 20.148 / 20.065 s | +0.3 % (noise) | identical (sha), all four arms |
| 150,038 tokens | 85.127 / 86.161 s | **81.323 / 81.626 s** | **−4.9 %** | identical |
| 299,227 tokens | 174.113 / 176.795 s | **158.994 / 158.416 s** | **−9.5 %** | identical |

Decode is not affected: ABBA means +0.013, +0.011, +0.033, +0.003 ms per round (average +0.015), not detectable; T=1
texts 11 of 11 the same. Changes are of the arm means (ESTIMATED arithmetic: 150K 85.64 → 81.47 s, 300K 175.45 →
158.71 s). The prefill skip and this scorer together took a 300,000-token first token from 263.9 s to about 159 s.

#### Model Runner V2 at depth

Production moved to vLLM's Model Runner V2 (MRV2) on 2026-11-04 (next section). Its depth runs so far are single runs
in the D54A window, compared with V1-runner runs from other windows, so read the changes as ESTIMATED:

| prompt | MRV2 first token | MRV2 ms per round | V1 runner reference | label |
|---|---:|---:|---|---|
| 32,718 tokens | 19.37 s | 28.02 | 20.11 s, 26.96 ms per round (2026-11-03, 17 switches) | MEASURED, one run each; **decode about 1.1 ms per round slower** |
| 150,038 tokens | 82.77 s | 26.65 | 81.3-81.6 s with the fused scorer (D52R2); 27.88 ms per round with the tiled scorer (D48) | MEASURED, one run each; decode about 1.2 ms per round faster |

Output was identical (sha) to the V1 runner at both lengths. The same-window depth sweep that followed (test D55,
2026-11-04, the production set on each runner, two arms each, one prompt per length, decode ms per round, MEASURED)
settles the decode side:

| prompt length | V1 runner, OFF / OFF2 | MRV2, ON / ON2 | MRV2 − V1 | tokens per round (both) |
|---|---:|---:|---:|---:|
| 2,048 | 25.41 / 25.67 | 22.82 / 22.80 | −2.59 / −2.87 | 3.97 |
| 8,192 | 25.77 / 25.82 | 22.99 / 22.97 | −2.78 / −2.85 | 3.56-3.58 |
| 16,384 | 25.93 / 26.01 | 23.26 / 23.34 | −2.67 / −2.67 | 4.41 |
| 32,768 | 26.33 / 26.35 | **27.74 / 27.79** | **+1.41 / +1.44** | 4.10 |
| 65,536 | 26.28 / 26.69 | 23.58 / 23.75 | −2.70 / −2.94 | 4.57 |

MRV2 is faster by 2.6-2.9 ms per round at 2K, 8K, 16K and 64K, and slower by about 1.4 ms at the 32K prompt, in both
arms. The cause of the 32K case is not known yet (INCONCLUSIVE); it is next on the list after the queue.

### Time per round: the engineering metric behind the tok/s

| stage (2026-11-03/04) | T=0 ms/round | T=1 ms/round | label |
|---|---:|---:|---|
| PP2 x TP4 port, no levers | 31.1 | 31.7 | MEASURED |
| + six token-path and draft levers | 29.55 | 30.0 | MEASURED, ABBA averages |
| + quantize-plan fusion, keep-batch, fast expert kernels, attention fusions | ~27.1 | ~27.7 | MEASURED |
| + expert-kernel instruction diet | ~26.2 | ~26.8 | ESTIMATED then: the row above minus 0.871 ms (ABBA) |
| + prefill skip and the larger hot ring (all 17 switches) | 26.4-26.5 | 27.0-27.1 | MEASURED, 2 arms; decode-only 25.34-25.45 / 25.27-25.35 |
| production after the PCIe-switch move | 26.3 | 26.9 | MEASURED; decode-only 25.30 / 25.20 |
| + tiled and fused index scorers, drafter projection sharding (22 keys, V1 runner; 2026-11-04) | 26.0 | 26.6-26.7 | MEASURED, 2 arms (D54A OFF); decode-only 24.98 / 24.92-24.98 |
| **+ Model Runner V2: production (2026-11-04)** | **23.2-23.4** | **23.8** | MEASURED, 2 arms (D54A ON); **decode-only 22.22-22.26 / 22.17-22.19** |

The first four rows time a round with the first token included (about 1 ms per round on these 1,024-token texts). Our
second-version harness (published 2026-11-03, A/A spread under 0.1 ms per round) also reports decode-only rounds, which
is what levers are decided on from now on.

A round is one target verification step: the target checks the drafted tokens and emits one token plus every accepted
draft. Per-request throughput is (1 + accepted drafts per round) / round time. Acceptance moves with the text; round time
is the stable engine-speed measure, and every change on this page was decided on it.

## What this is

**A 249 GB model on GPUs from 2018, every expert resident.** DeepSeek-V4.1-Flash-1017 is a 551.9B-parameter mixture of
experts with DeepSeek's Engram n-gram memory. Its weights here are 248.8 GB (138.24 GB of IQ2_XXS experts and backbone,
110.60 GB of IQ4_NL Engram tables), and all of it lives in the 256 GiB of HBM2 on eight V100-SXM2-32GB cards: sm_70
silicon with no FP8 or BF16 tensor cores and no `cp.async`. No expert is paged from host memory during decode.

**Split across two NVLink boards.** 1CatAI's [1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM) DeepSeek-V4.1 package
([#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277)) runs this model on one 4-GPU board with experts offloaded. We
ported it to pipeline parallel 2 x tensor parallel 4: layers 0-19 and the Engram tables on one NVLink quad; layers 20-39,
the head and the DSpark drafter on the other; PCIe between them. Then we made it fast, one switch at a time, each
admitted only by a paired A/B on this machine.

**99 to 134 tok/s in two days.** On 2026-11-03 the port went from 31.1 to 26.3 ms per round (MEASURED; 25.30
decode-only) through thirteen adopted changes, most of them our own CUDA and host-path work, every one bitwise-identical
or proven output-identical. The same day the prefill skip cut the first token of a 300,000-token prompt from 264 to 178
seconds. On 2026-11-04 our tiled index scorer cut a decode round at 300K context by 13.7 % (34.33 → 29.62 ms), our fused
prefill index scorer cut the 300K first token by a further 9.5 % (to about 159 s), the drafter's projection was sharded
across the four GPUs of its board (−0.130 ms per round, bitwise), and the move to Model Runner V2 took a round to 23.4 ms
(22.26 decode-only), bitwise-identical output. About thirty more ideas lost their A/B or failed a numerics gate; they are
all listed below with the reason.

**Exact outputs.** The target verifies every draft with the speculative-sampling acceptance rule, so the text keeps the
target model's distribution whatever the drafter proposes. The speed changes do not change what the model computes.
One difference under Model Runner V2: a sampled (T>0) request that asks for logprobs uses MRV2's rejection sampler
instead of our keyed draw streams. Its text still follows the target distribution, but it is not the same sample the
V1 runner would have drawn. Every MRV2 boot logs this. Requests without logprobs keep the keyed streams; in the A/B
harness they were bitwise-identical to the V1 runner.

**Where the previous build is still ahead.** It read prompts faster (about 2,900-3,300 tok/s against about 1,630-1,890
here with the prefill skip and the fused scorer, ESTIMATED from the first-token times above) and served three requests
at once; this build takes one request at a time today. A concurrency switch on Model Runner V2 (one, two or three
requests) is built and waits for its test window; one request at a time stays the default unless a lone request is not
detectably slower with it. A tensor-core prefill expert kernel is in testing too. Details of that build:
[previous-build/](previous-build/).

**Everything is published:** the measurements, the 49-patch engine series, our six production patches (expert-kernel
diet, prefill skip, tiled index scorer, fused prefill index scorer, drafter projection sharding, Model Runner V2 port),
the patches still in testing, the serving profile and environment, the A/B harness, and the log of the test queue.

<!-- pli:blurb:start -->

> Published by [PLI Labs](https://proprietarylegal.ai/labs.html), the open research arm of [Proprietary Legal Intelligence](https://proprietarylegal.ai). PLI builds AI systems around a legal organization's own work product, combining retrieval, staged workflows, validation, and attorney review. Visit [proprietarylegal.ai](https://proprietarylegal.ai) to explore our work and discuss what your organization needs.

<!-- pli:blurb:end -->

## What runs

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two 4-GPU SXM2 boards, NVLink inside each board; four PLX switches, each on its own CPU root complex at PCIe Gen3 x16 (since 2026-11-03), Gen3 x8 per GPU |
| Host | AMD Threadripper PRO 3945WX (12 cores), one NUMA node, 251 GB RAM |
| Power and clocks | 150 W per card, graphics clock capped at 1522 MHz (200 W measured neutral: −0.06 ms per round) |
| Model | DeepSeek-V4.1-Flash-1017: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` (IQ2_XXS experts, 138.24 GB; IQ4_NL Engram, 110.60 GB); config, tokenizer and DSpark drafter (FP8, 7.93 GB) from [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` |
| Engine | 1Cat-vLLM #1277 (merge `899e9ed33`) + 1Cat main `6db9c81` and 25 open 1Cat PRs + our PP2 port and lever stack: the [49-patch series](forks/1cat-4xv100-tp4/), [our expert-kernel diet](engine/production/0050-expert-diet.patch), [our prefill skip](engine/production/0051-prefill-skip.patch), [our tiled index scorer](engine/production/0052-index-tiled.patch), [our fused prefill index scorer](engine/production/0053-index-fuse.patch), [our drafter projection sharding](engine/production/0054-draft-mp-shard.patch) and [our Model Runner V2 port](engine/production/0055-mrv2.patch); the `v41k`, `v41idx` and `v41pidx` SM70 CUDA libraries built from that source |
| Layout | PP2 x TP4. Stage 1 (board B): layers 0-19, Engram tables, hash state. Stage 2 (board C): layers 20-39, the head, the drafter. TP all-reduce over NVLink; the stage hand-off over PCIe |
| Engine settings | vLLM Model Runner V2 (since 2026-11-04; the V1 runner before), synchronous scheduling, FULL CUDA graphs for 1-6 tokens per step, chunked prefill 8,192, prefix caching, every expert resident |
| Drafter | DSpark, 5 drafts per round, coupled (keyed) sampled drafts at T>0 |
| Context | 524,288 tokens per request, one request at a time, KV pool 2,076,870 tokens (packed KV: a 524,288-position GPU hot ring + host arena) |
| Thinking | on by default; `chat_template_kwargs: {"thinking": false}` turns it off |

Serving profile, environment and the production switch set: [engine/](engine/) and [docs/production.md](docs/production.md).

## What worked

Each lever is a `VLLM_V41_*` switch that defaults off; with the switch off the code path is the old one. ms per round,
ABBA averages, 2026-11-03/04. Model Runner V2 is not a `VLLM_V41_*` switch: it is vLLM's own `VLLM_USE_V2_MODEL_RUNNER`.

| change | where it came from | effect | numerics |
|---|---|---|---|
| Indexer top-k reduce on the device (`INDEX_REDUCE`) | ours | −0.85 ms; also makes T=1 output identical across restarts | exact |
| Double-buffered Volta dense mat-vec (`DMV_X`) | ours, on #1277's `dmv13` | −0.42 ms (6/6 pairs) | bitwise |
| Coupled sampled drafts (`COUPLED_DRAFTS`) | [TensorFold #25](https://github.com/Elevatormusic/TensorFold/pull/25) (merged); our port | T=1 acceptance 1.85 → 2.25 per round, +14 % tok/s | exact (keyed draws) |
| Draft-head and sampler sharding (`MARKOV_SHARD`, `COUPLED_SHARD`, `COUPLED_LOCAL`) | ours; the coupled shards reuse code from our Sparks research lane | −0.2 ms (T=0); −0.23 and −0.12..−0.24 ms (T=1) | exact |
| Expert plan fused into the q8 quantize launch (`PLAN_FUSE`) | ours, code from our Sparks research lane | −0.36 (T=0), −0.27 (T=1) | bitwise |
| Keep the request in the batch across empty pipeline steps (`PP_KEEP_BATCH`) | our V1-runner port of 1Cat [#1263](https://github.com/1CatAI/1Cat-vLLM/pull/1263) | 128K −24.8 % (84 → 111 tok/s), 64K −17.4 %, 32K −9.7 % | texts identical |
| Fast routed-expert kernels, down and gate/up (`EXPERT_FAST`) | ours | down −0.68..−0.84; gate/up a further −0.53..−0.82 (T=0) | bitwise, sanitizers clean |
| Fused attention prologue and epilogue (`FUSE_ATTN_PREP`, `_POST`) | ours | −0.19 ms | bitwise |
| Hot-ring refill after a prefix-cache hit (`HOT_REFILL`) | our port of 1Cat issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341) | correctness fix; fired on all 8 workers | – |
| Expert-kernel instruction diet (`EXPERT_DIET=3`) | ours | **−0.871 ms** (T=0 −0.74/−1.02, T=1 −0.79/−0.93) | T=1 texts 11/11; greedy 7/8 + one known near-tie; memcheck, racecheck, synccheck 0 errors |
| Router floor (`ROUTE_FAST`, 4 warps) | ours, code from our Sparks research lane | −0.165 ms, inside the session's drift: not a significant win | greedy bitwise; kept on as upstream-backed |
| **Prefill skip (`PREFILL_SKIP_ROWS=3072`)** | ours; design reference: [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100)'s replay rows | **first token −8.8 % at 32K, −20.6 % at 150K, −31.5 % at 300K** (two repetitions per arm, OFF ON ON OFF) | identical output at every length; abort-and-resend guard identical; prefix-cache test pass |
| **Tiled decode index scorer (`INDEX_TILED`, `v41idx`)** | ours | **decode round −7.0 % at 150K (29.98 → 27.88 ms), −13.7 % at 300K (34.33 → 29.62 ms)**; short context not detectable (+0.03 ms) | bitwise; texts identical in every arm; GPU matrix 51,090 cases 0 mismatches; memcheck and racecheck 0 errors |
| Larger GPU hot ring (`KV_HOT_POSITIONS=524288`) | our setting of #1277's packed KV | 300K −1.09 ms per round, 150K −0.25 (ABBA); KV pool unchanged at 2,076,870 | identical output; prefix-cache test 3 of 3 |
| **Fused prefill index scorer (`INDEX_FUSE=ilp4`, `v41pidx`)** | ours; ideas from 1Cat [#1280](https://github.com/1CatAI/1Cat-vLLM/pull/1280) and [#1282](https://github.com/1CatAI/1Cat-vLLM/pull/1282) and philbert440's fused SM70 indexer; new code for V4.1's path | **first token −4.9 % at 150K, −9.5 % at 300K**; 32K and decode not detectable | near-tie gate PASS; output identical (sha) at 32K, 150K and 300K |
| Drafter projection sharding (`DRAFT_MP_SHARD`) | ours | −0.130 ms per round (ABBAABBA, 8 of 8 pairs faster); drafter step 841.7 → 640.7 µs in isolation | bitwise; every arm identical |
| **Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER=1`)** | vLLM's newer runner as carried by 1Cat, with 1Cat [#1221](https://github.com/1CatAI/1Cat-vLLM/pull/1221)'s DSpark path; our DeepSeek-V4.1 port, capture fix and prefill-skip hook | **−2.759 ms per round** decode-only (ABBA; 120.5 → 134.2 tok/s at T=0) | bitwise; every arm identical |

Two lessons: two of the winners were predicted near zero by isolated kernel benchmarks, so only the full A/B decides; and
the slope with context depth was host work, not GPU work. The drafter sharding missed the queue's automatic win bar
(its ABBAABBA verdict was "not detectable", average −0.130 ms); we adopted it by hand because it is bitwise-identical,
so it carries no quality risk, and all eight pairs were faster. Detail: [docs/levers.md](docs/levers.md#adopted).

## What did not work

| change | result | why |
|---|---|---|
| Expert top-p pruning (0rand / TensorFold) | 78 tok/s, greedy output changed | the divergence is built into the method |
| Async scheduling under PP2 + drafting | 90.5 tok/s first try, then crashes at request end | the crash is fixed by a request-end guard, but the guarded version is slower (next row) |
| V1 async with the request-end guard | **+1.678 ms per round slower** (ABBA, 95 % interval +1.54..+1.82); a 20-request soak with aborts ran clean | rejected; 1Cat's newer model runner is being re-ported instead |
| TP8: one 8-way tensor-parallel group across both boards | no-go at the probe: best modeled round 24.65 ms against a 22.0 ms bar | the 8-way all-reduce across the boards took 30.8 µs against 5.28 µs for 4-way inside a board |
| 16,384-token prefill chunks | first token +17.5 % at 32K, +5.6 % at 150K; near-tie gate FAIL | – |
| Indexer overlap in prefill | neutral (−0.1 to +0.3 %), bitwise | nothing to gain |
| Prefill chunk 4,096, re-gated | near-tie gate FAIL: the 7K and 22K prompts moved a confident token (gaps 0.31 and 0.78 nats) | chunk size changes long-prompt numerics |
| Suggested tiling config for the dense kernel, re-run | near-tie gate FAIL: 2 of 8 identical, confident tokens moved | – |
| CPU pinning to physical cores | +0.079 ms per round (ABBAABBA; 95 % interval −0.020..+0.177) | not a lever on this host |
| Side stream for the hyper-connection mixing step | parked: below the win bar in its GPU micro-benchmark; the graph-topology check failed | not a real fork and join in the captured graph |
| Engram rows cached in spare GPU memory | not built | sized from 52 profiled rounds: host Engram costs ~0.12 ms per round in total; a round needs all 288 rows, so a partial cache removes nothing; fully resident is 103 GiB against ~44 GiB free on the stage-1 board |
| Fused layer-transition kernel, v1 and v2 | slower than the two kernels it replaced | the mixing step dominates; the side-stream version was parked (above); a third variant is queued |
| Side-branch L2 warm-up of the next weight matrix | lost | the warm-up stretched beside the main kernel; at best 2-4 µs per projection |
| Deeper prefetch in the dense mat-vec | bitwise over 3,648 runs, slower in every variant | the double buffer is enough |
| MoE sum folded into the all-reduce, env-only | +0.28 ms | V4.1's message size falls back to the slow path; a rebuilt admission is in testing |
| Spin-loop wait in the broadcast queue | +0.04..+0.09 ms | – |
| 200 W instead of 150 W | −0.06 ms, neutral | an older 200 W gain came from a higher clock ceiling |
| 19 expert-kernel variants; L1 prefetch + evict-first | all bit-clean, none beat production | issue- and latency-bound at low occupancy, not bandwidth-bound; this led to the diet |
| Gate-column router variant | slower at 2+ tokens per step | – |
| 3 or 4 drafts per round | refused at boot | the DSpark block size is 5 |
| Expert "wave" down kernel (`EXPERT_WAVE`, D45R4) | **+0.216 ms per round slower** (ABBAABBA, 95 % interval +0.118..+0.314); gate PASS, T=1 texts the same | rejected: detectably slower |
| Split-K tensor-core decode attention (`ATTN_HMMA=2`, D47R2) | −0.143 ms per round, not detectable; near-tie gate FAIL: a confident token moved in 6 of 8 rows, KL mean 0.0058 (max 0.25) | rejected on quality |
| FP16-packed shared-expert down kernel (`SHARED_DOWN`, D49R) | near-tie gate FAIL: a confident token moved (KL max 0.17); 25.30 → 25.15 ms per round | rejected on quality |
| Fused layer transition, no-early variant (`FTNE`, D50R2) | +0.020 ms per round (ABBAABBA, 95 % interval −0.078..+0.118); identical 8 of 8 | neutral; not adopted |
| Probabilistic sharded drafts for thinking mode (D46) | +0.05..+0.15 accepted drafts per round but +0.5..+1.55 ms per round: −3.1 to +0.6 % tok/s at T=1; no variant faster beyond noise | the extra drafter work eats the acceptance gain |
| Draft temperature 1.2 / 0.85 (D46) | −2.9 % / about 0 tok/s at T=1 | – |
| Bitwise FP8 drafter GEMV (`DRAFT_GEMV2`, D53R) | with the sharding: −0.069 ms per round, not detectable; drafter step 780.1 µs against 627.8 µs for the sharding alone | slower than the sharding alone; off |
| Lookup-free IQ1_M expert repack | no-go before a build: 360 → 344 instructions per 256 weights (−4.4 %, gate 20 %), +35.7 % bytes | not worth the memory |
| Asynchronous scheduling on Model Runner V2 (D54A) | −2.860 ms per round against V1, −0.085..−0.117 against synchronous MRV2; bitwise | about 0.4 %; needs its own profile; off for now |

Prefill chunk: 8,192 kept (4,096 saved 5.6 % of first-token time at 32K and nothing at 128K, then failed the near-tie
gate on its re-test; 2,048 and 16,384 slower).
Every lever lost on 2026-11-03 was re-reviewed for a build or deploy defect that could void its result; none was found.
Several 2026-11-04 tests first failed in their own checks (a test feeding the wrong type, a stale build cache, a
sanitizer running out of memory, a report parser); each check was fixed and the test re-run before its verdict.
Full table with numbers: [docs/levers.md](docs/levers.md#did-not-work).

## In testing

Not results yet. Each is reported with its A/B when it finishes; queue order and status are in
[docs/roadmap.md](docs/roadmap.md), the patches in [engine/in-testing/](engine/in-testing/).

| test | what it is | first result or expectation | label |
|---|---|---|---|
| **Concurrency on Model Runner V2** | one command switches `single`, `conc2` or `conc3`; `single` stays the default unless a lone request is not detectably slower | built and CPU-tested; a review found and fixed a warm-up crash before any GPU run; window not run yet | PENDING |
| All-reduce push path for V4.1's message size (D44R5) | rebuilt admission | −0.08..−0.15 ms per round; earlier runs stopped in their own build, check and deploy steps | ESTIMATED, PENDING |
| Tensor-core prefill expert GEMM (D51R4) | grouped HMMA for prefill only; report-only | micro-benchmark −19 % against the current kernels (30,989 vs 38,270 µs cold aggregate); the GPU matrix check stopped on a tooling error, now fixed | ESTIMATED, PENDING |
| Four-card fork smoke | the 49-patch series on one board | – | PENDING |
| Full benchmark of the production boot | tok/s, depth and long-context benchmark on the 23-key set | after the items above | PENDING |

The two-request build on the V1 runner (`MULTI_SEQ`) was withdrawn in favour of the MRV2 concurrency port; the cause of
its boot failure was found (the drafter was profiled with 2 x 5 = 10 draft rows against a 5-row limit).

After the queue: decode by text type and a legal benchmark.

## Quality

- **The quant.** ISTA-DASLab report the IQ2_XXS build scoring the same as the unquantized release on their three
  benchmarks: AIME25 100.00, GPQA-Diamond 90.91, LiveCodeBench v6 89.71 (100 % recovery, reasoning effort 50). UPSTREAM
  CLAIM from their [model card](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF); we have not
  reproduced it, and those benchmarks are small (AIME is 30 problems).
- **Token-level fidelity of this build: not measured yet.** A KL-divergence and top-1 agreement test against the
  unquantized model is planned, with fixed reference logits and prompt panels.
- **The speed work changed nothing measurable, by construction.** Every adopted lever is bitwise-identical or passes the
  near-tie gate (the instruction diet and the fused prefill index scorer); drafting changes speed, not the output
  distribution. Model Runner V2 was bitwise-identical to the V1 runner in every A/B arm (logprob requests at T>0: see
  "Exact outputs" above).
- **Long context works.** Needle retrieval at ~450K and ~498K tokens: 6 of 6 needles in 4 of 4 runs. Prefix-cache hits
  from 36K to 500K return the same text as cold runs.

More: [docs/quality.md](docs/quality.md).

## Our upstream contributions

Work we sent upstream, with authorship checked on GitHub. Third-party credits are at the end.

| PR | author | state | what it does | what it means for this build |
|---|---|---|---|---|
| [1Cat-vLLM #651](https://github.com/1CatAI/1Cat-vLLM/pull/651) | ProprietaryLegal | **merged** 2026-09-26 | SM70: accept the DFlash embedding replica across split `load_weights` calls | an SM70 drafter-loading fix in the engine this build runs on |
| [1Cat-vLLM #1031](https://github.com/1CatAI/1Cat-vLLM/pull/1031) | PLI Labs (founder) | open (2026-10-07) | DeepSeek-V4.1-Flash on V100: PP3 x TP4 (12 GPUs, 256K) and PP2 x TP4 (8 GPUs) | the multi-board pipeline layout this build's PP2 x TP4 port follows |
| [1Cat-vLLM #1030](https://github.com/1CatAI/1Cat-vLLM/pull/1030) | PLI Labs (founder) | open (2026-10-07) | SM70: generalise the MXFP4 MoE geometry; skinny split-K 4/6/9/12/18 | native-FP4 expert route; not served here (this build serves GGUF) |
| [1Cat-vLLM #1021](https://github.com/1CatAI/1Cat-vLLM/pull/1021) | PLI Labs (founder) | open (2026-10-07) | SM70: keep 32x32 UE8M0 block-FP8 dense weights in FP8 on Volta | native-FP8 dense route; not served here |

Details and two earlier closed PRs: [docs/upstream-contributions.md](docs/upstream-contributions.md).

## Four cards

The same engine is packaged for a single 4x V100 NVLink board: the [49-patch series](forks/1cat-4xv100-tp4/) against 1Cat
#1277 rebuilds our exact source tree, with a serving profile and install, start and verify scripts. At PP=1 every adopted
lever works except keep-batch, which is a no-op there. Four cards must offload some experts to host memory, so expect
different numbers. The 2026-11-04 production patches (0052-0055) are not in the four-card series yet. **Status: built
and CPU-tested; the four-GPU smoke test is queued.** [docs/four-card.md](docs/four-card.md)

## Hardware

Eight V100-SXM2-32GB on two NVLink quad boards; Threadripper PRO 3945WX; 251 GB RAM, one NUMA node. Host-to-device
bandwidth differed between the boards (512 MiB pinned, MEASURED 2026-11-02: 25.5 GB/s for all four cards of board B
together, 13.1 GB/s on board C, where two GPUs then shared an x8 path). On 2026-11-03 we moved that PCIe switch card: now
each of the four switches has its own CPU root complex at Gen3 x16, and each GPU links to its switch at Gen3 x8. The
host-to-device bandwidth has not been re-measured since the move. Volta has FP16 `mma.sync.m8n8k4` only: no `cp.async`, no `ldmatrix`, no FP8
tensor-core math, and a read ceiling of about 879 GB/s (measured by [v100-skinny](https://github.com/dnv2003/v100-skinny)).
Our fast expert kernels reach about 290-415 GB/s: they are limited by instruction issue and latency, which is why the
instruction diet won.

## Reproduce

1. Rebuild the engine source: in [forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/), `tools/apply_series.sh` applies the
   49 patches to 1Cat-vLLM #1277 (`899e9ed33`) and checks the result against the recorded tree (`b0d692425297`).
2. Apply the six production patches in order: [0050](engine/production/0050-expert-diet.patch) (result tree
   `4447483248bb`), [0051](engine/production/0051-prefill-skip.patch) (`32d4a9d9b0c1`),
   [0052](engine/production/0052-index-tiled.patch) (`4760febd4fe7`), [0053](engine/production/0053-index-fuse.patch)
   (`421c427444a4`), [0054](engine/production/0054-draft-mp-shard.patch) (`09cf8cc28b7b`) and
   [0055](engine/production/0055-mrv2.patch) (`e85291152ae9`), then build vLLM, the `v41k` extension and the `v41idx`
   and `v41pidx` libraries ([engine/README.md](engine/README.md)).
3. Download the weights (links above; none are distributed here), set `ENGINE_HOME`, `MODEL_HOME` and
   `CUDA_VISIBLE_DEVICES`, source [engine/configs/rec.env](engine/configs/rec.env) and start with
   [engine/configs/run_serve.sh](engine/configs/run_serve.sh).
4. Measure with the [A/B harness](harness/) ([method](docs/method.md)).

## Repository layout

| Path | What it is |
|-|-|
| `docs/` | [production](docs/production.md), [measurements](docs/measurements.md), [levers](docs/levers.md), [method](docs/method.md), [quality](docs/quality.md), [four cards](docs/four-card.md), [roadmap](docs/roadmap.md), [upstream contributions](docs/upstream-contributions.md) |
| `engine/` | the production patches, patches in testing, serving profile, environment and production switch set |
| `forks/1cat-4xv100-tp4/` | the 49-patch series against 1Cat #1277, with install, start, verify and smoke scripts |
| `harness/` | the A/B harness: arm runners, pairing and verdict scripts, greedy and divergence tracing |
| `evidence/queue-log.txt` | the state log of the 2026-11-02/04 test queue, through Model Runner V2 entering production and the D55 depth sweep (paths replaced) |
| `previous-build/` | our first build on these eight cards (EXL3 pack, 2026-11-01): its page, measurements, experiments, patches and tools |
| `tools/` | `check_data_boundary.sh` (pre-publication scan), [UPDATE.md](tools/UPDATE.md) (how this page is refreshed) |
| `.publication/SOURCE.json` | what this tree was assembled from and what was left out |

## Work with PLI Labs

[PLI Labs](https://proprietarylegal.ai/labs.html) is the open research arm of Proprietary Legal Intelligence. PLI builds
AI around an organization's own work product: retrieval over its documents, staged workflows, validation of every output
and attorney review before anything goes out. This stack is how we run that privately, on hardware we own. If you want
private, on-prem LLM serving of your own, from choosing the hardware to the measured stack and the workflows on top, we
consult on exactly that: [proprietarylegal.ai](https://proprietarylegal.ai).

## Licence

Original documentation and code are Apache-2.0 ([LICENSE](LICENSE)); see [NOTICE](NOTICE). Patches against third-party
code keep that code's licence. No model weights, wheels, compiled libraries or prompt corpora are distributed here.

## Credits

This build stands on other people's work:

- **DeepSeek**: DeepSeek-V4.1-Flash-1017, the DSpark drafter and the Engram design.
- **ISTA-DASLab**: the GSQ-RCO GGUF quantization served here.
- **1CatAI / 1Cat-vLLM**: the Volta vLLM fork, and the #1277 DeepSeek-V4.1 package (yangzhuxinyzx) that this build ports
  and extends; #1263 (Peuqui), #183 and #344 (yangzhuxinyzx), issue #1341 (squibloads), and the other PRs in the series.
- **The vLLM project**: the serving engine. **ggml**: the GGUF and IQ formats.
- **Phil Tompkins (philbert440)**: the V100 engine and EXL3 pack our previous build ran on, and the replay-row design
  behind our prefill skip.
- **Dennis Vertzyas (dnv2003), v100-skinny**: Volta kernel and bandwidth findings.
- **TensorFold (Elevatormusic)**: coupled sampled drafts.

Every source, with what we took from it, is in [CREDITS.md](CREDITS.md). If you build on this repository, please credit
them as well.
