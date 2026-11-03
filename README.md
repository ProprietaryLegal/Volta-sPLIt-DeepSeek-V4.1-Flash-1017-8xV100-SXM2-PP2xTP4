# Volta sPLIt: DeepSeek-V4.1-Flash-1017 on 8x V100-SXM2, split PP2 x TP4

## ~118 tok/s decode · ~121 tok/s thinking on · 524K context per request · 8x V100 from 2018

[![decode: ~118 tok/s](https://img.shields.io/badge/decode-~118%20tok%2Fs-2EA043?style=for-the-badge)](#tokens-per-second)
[![thinking on: ~121 tok/s](https://img.shields.io/badge/thinking%20on-~121%20tok%2Fs-1F6FEB?style=for-the-badge)](#tokens-per-second)
[![vs previous V100 build: 2.6x](https://img.shields.io/badge/vs%20previous%20V100%20build-2.6x%20per%20round-8250DF?style=for-the-badge)](#the-progression-in-toks)
[![context: 524K](https://img.shields.io/badge/context-524K%20per%20request-555555?style=for-the-badge)](docs/measurements.md#long-context)

Built by **Nick Mermiges, Esq.**, founder of [PLI Labs](https://proprietarylegal.ai/labs.html) · [proprietarylegal.ai](https://proprietarylegal.ai)

[![proprietarylegal.ai](https://img.shields.io/badge/proprietarylegal.ai-website-0B3D91)](https://proprietarylegal.ai) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-card-FFD21E)](https://huggingface.co/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-GGUF) [![PLI Labs](https://img.shields.io/badge/PLI%20Labs-research-1F6FEB)](https://proprietarylegal.ai/labs.html) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Hardware: 8x V100-SXM2-32GB](https://img.shields.io/badge/hardware-8x%20V100--SXM2--32GB-76B900)](#hardware) [![Method: ABBA paired](https://img.shields.io/badge/method-ABBA%20paired-555555)](docs/method.md)

## Tokens per second

<table>
<tr>
<td align="center"><h1>~118</h1>tok/s decode<br><sub>thinking off, T=0<br>ESTIMATED from measured deltas</sub></td>
<td align="center"><h1>~121</h1>tok/s, thinking on<br><sub>T=1, our 12-prompt set<br>ESTIMATED from measured deltas</sub></td>
<td align="center"><h1>84.6&#8209;87.3</h1>tok/s, thinking high<br><sub>DGX sPLIce's benchmark, MEASURED<br>(the two DGX Sparks: 49.7&#8209;53.1)</sub></td>
<td align="center"><h1>61.7</h1>tok/s after a<br>500,000-token prompt<br><sub>MEASURED</sub></td>
</tr>
</table>

<sub>Single stream, one request at a time, all on our host on 2026-11-03: 8x V100-SXM2-32GB, 150 W per card, DSpark 5
drafts per round. MEASURED = observed on this host. ESTIMATED = the last measured stack minus the measured A/B gain of the
one change added after it (the expert-kernel instruction diet, −0.871 ms per round, ABBA average).</sub>

### The progression, in tok/s

| build (8x V100-SXM2-32GB, same host) | date | decode, thinking off | thinking on | label |
|---|---|---:|---:|---|
| [Previous build](previous-build/): EXL3 pack on philbert440's SM70 engine | 2026-11-01 | 42-46 | 31.4 | MEASURED (its own method) |
| **Volta sPLIt**: PP2 x TP4 port of 1Cat #1277, no speed levers | 2026-11-03 | 99.2 | 88.0 | MEASURED |
| + six token-path and draft levers | 2026-11-03 | ~105.8 | ~108.4 | MEASURED (ABBA) |
| + fused quantize plan, keep-batch, fast expert kernels, attention fusions | 2026-11-03 | ~114 | ~117 | MEASURED |
| **+ expert-kernel instruction diet (production now)** | 2026-11-03 | **~118** | **~121** | ESTIMATED |

"Thinking off" is 3 x 1,024 greedy tokens; "thinking on" is a seeded temperature-1 set of 12 prompts with thinking
enabled. Both come from the same A/B harness ([method](docs/method.md)). The previous build used other prompts, so the
fair engine comparison is the time per verify round: 71.2-71.6 ms there against about 27.1 ms measured (about 26.2 ms
estimated) here, **about 2.6x faster per round**.

### By text type

Per-type decode (code, structured output, chat, prose) has **not been measured on this build yet**; it is part of the
head-to-head benchmark against DGX sPLIce that runs after the current test queue. What we know today: tok/s follows the
drafter's acceptance, which follows the text. Our greedy set accepts about 2.2 drafts per round; the legal prompt of DGX
sPLIce's benchmark with high-effort thinking accepts 1.2-1.6. That is why the same engine shows ~114 tok/s on one set and
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
| **300K with prefill skip (in testing)** | **181.3 s** (was 263.9) | ~1,650 tok/s | – | MEASURED 2026-11-03, 1 repetition, identical output |

DGX sPLIce's benchmark conditions: temperature 1, thinking high, 1,500 generated tokens, cold prompts on an idle server.
The prefill-skip row is a change still in its test: first token −31 % at 300K, −20 % at 150K (111.1 → 88.5 s) and −9 %
at 32K (22.6 → 20.7 s), byte-identical output, one repetition so far. It is not in production until its test finishes.

### Time per round: the engineering metric behind the tok/s

| stage (2026-11-03) | T=0 ms/round | T=1 ms/round | label |
|---|---:|---:|---|
| PP2 x TP4 port, no levers | 31.1 | 31.7 | MEASURED |
| + six token-path and draft levers | 29.55 | 30.0 | MEASURED, ABBA averages |
| + quantize-plan fusion, keep-batch, fast expert kernels, attention fusions | ~27.1 | ~27.7 | MEASURED |
| + expert-kernel instruction diet | ~26.2 | ~26.8 | ESTIMATED: the row above minus 0.871 ms (ABBA) |

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

**99 to ~118 tok/s in one day.** On 2026-11-03 the port went from 31.1 to about 26.2 ms per round through eleven adopted
changes, most of them our own CUDA and host-path work, every one bitwise-identical or proven output-identical. Eleven
more ideas lost their A/B; they are all listed below with the reason.

**Exact outputs.** The target verifies every draft with the speculative-sampling acceptance rule, so the text keeps the
target model's distribution whatever the drafter proposes. The speed changes do not change what the model computes.

**Where the previous build is still ahead.** It read prompts faster (about 2,900-3,300 tok/s against 1,130-1,430 here)
and served three requests at once; this build takes one request at a time today. A two-request build and a prefill
speed-up are in testing. Details of that build: [previous-build/](previous-build/).

**Everything is published:** the measurements, the 49-patch engine series, our production kernel patch, the patches
still in testing, the serving profile and environment, the A/B harness, and the log of the day's test queue.

**Sister build:** [DGX sPLIce](https://github.com/ProprietaryLegal/DGX-sPLIce-DeepSeek-V4.1-Flash-2xDGX-Spark-2xRTX3090-drafter-x86-offload),
the same model on two DGX Sparks with an x86 offload host and an RTX 3090 drafter. A head-to-head benchmark of the two
builds is in progress.

<!-- pli:blurb:start -->

> Published by [PLI Labs](https://proprietarylegal.ai/labs.html), the open research arm of [Proprietary Legal Intelligence](https://proprietarylegal.ai). PLI builds AI systems around a legal organization's own work product, combining retrieval, staged workflows, validation, and attorney review. Visit [proprietarylegal.ai](https://proprietarylegal.ai) to explore our work and discuss what your organization needs.

<!-- pli:blurb:end -->

## What runs

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two 4-GPU SXM2 boards, NVLink inside each board; four PLX switches, PCIe Gen3 x8 per GPU |
| Host | AMD Threadripper PRO 3945WX (12 cores), one NUMA node, 251 GB RAM |
| Power and clocks | 150 W per card, graphics clock capped at 1522 MHz (200 W measured neutral: −0.06 ms per round) |
| Model | DeepSeek-V4.1-Flash-1017: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` (IQ2_XXS experts, 138.24 GB; IQ4_NL Engram, 110.60 GB); config, tokenizer and DSpark drafter (FP8, 7.93 GB) from [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` |
| Engine | 1Cat-vLLM #1277 (merge `899e9ed33`) + 1Cat main `6db9c81` and 25 open 1Cat PRs + our PP2 port and lever stack: the [49-patch series](forks/1cat-4xv100-tp4/) and [our expert-kernel diet](engine/production/0050-expert-diet.patch); the `v41k` SM70 CUDA extension built from that source |
| Layout | PP2 x TP4. Stage 1 (board B): layers 0-19, Engram tables, hash state. Stage 2 (board C): layers 20-39, the head, the drafter. TP all-reduce over NVLink; the stage hand-off over PCIe |
| Engine settings | vLLM V1 runner, synchronous scheduling, FULL CUDA graphs for 1-6 tokens per step, chunked prefill 8,192, prefix caching, every expert resident |
| Drafter | DSpark, 5 drafts per round, coupled (keyed) sampled drafts at T>0 |
| Context | 524,288 tokens per request, one request at a time, KV pool 2,076,870 tokens (packed KV: GPU hot ring + host arena) |
| Thinking | on by default; `chat_template_kwargs: {"thinking": false}` turns it off |

Serving profile, environment and the production switch set: [engine/](engine/) and [docs/production.md](docs/production.md).

## What worked

Each lever is a `VLLM_V41_*` switch that defaults off; with the switch off the code path is the old one. ms per round,
ABBA averages, 2026-11-03.

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

Two lessons: two of the winners were predicted near zero by isolated kernel benchmarks, so only the full A/B decides; and
the slope with context depth was host work, not GPU work. Detail: [docs/levers.md](docs/levers.md#adopted).

## What did not work

| change | result | why |
|---|---|---|
| Expert top-p pruning (0rand / TensorFold) | 78 tok/s, greedy output changed | the divergence is built into the method |
| Async scheduling under PP2 + drafting | 90.5 tok/s first try, then crashes at request end | parked; a guarded version is in testing |
| Fused layer-transition kernel, v1 and v2 | slower than the two kernels it replaced | the mixing step dominates; a side-stream version is in testing |
| Side-branch L2 warm-up of the next weight matrix | lost | the warm-up stretched beside the main kernel; at best 2-4 µs per projection |
| Deeper prefetch in the dense mat-vec | bitwise over 3,648 runs, slower in every variant | the double buffer is enough |
| MoE sum folded into the all-reduce, env-only | +0.28 ms | V4.1's message size falls back to the slow path; a rebuilt admission is in testing |
| Spin-loop wait in the broadcast queue | +0.04..+0.09 ms | – |
| 200 W instead of 150 W | −0.06 ms, neutral | an older 200 W gain came from a higher clock ceiling |
| 19 expert-kernel variants; L1 prefetch + evict-first | all bit-clean, none beat production | issue- and latency-bound at low occupancy, not bandwidth-bound; this led to the diet |
| Gate-column router variant | slower at 2+ tokens per step | – |
| 3 or 4 drafts per round | refused at boot | the DSpark block size is 5 |

Prefill chunk: 8,192 kept (4,096 saved 5.6 % of first-token time at 32K and nothing at 128K; 2,048 and 16,384 slower).
Every lost lever was re-reviewed on 2026-11-03 for a build or deploy defect that could void its result; none was found.
Full table with numbers: [docs/levers.md](docs/levers.md#did-not-work).

## In testing

Not results yet. Each is reported with its A/B when it finishes; queue order and status are in
[docs/roadmap.md](docs/roadmap.md), the patches in [engine/in-testing/](engine/in-testing/).

| test | what it is | first result or expectation | label |
|---|---|---|---|
| Prefill skip (`PREFILL_SKIP_ROWS=3072`) | early prefill chunks skip stage-2 layers whose windowed state they cannot reach (design reference: [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100)) | first token at 300K −31 %, identical output | MEASURED, 1 repetition |
| TP8 feasibility probe | one 8-way tensor-parallel group across both boards | pre-test estimate: no-go | ESTIMATED |
| Prefill profile and three prefill switches | indexer overlap, 16,384-token chunks, token-blocked mixing | – | – |
| Larger GPU hot ring (`KV_HOT_POSITIONS=524288`) | more KV rows on the GPU | 300K −1.09 ms per round, 150K −0.25, identical output | MEASURED (A/B won); adoption check queued |
| Second-version A/B harness | decode-only timing, measured A/A spread, three-way verdict | – | – |
| Async scheduling with a request-end guard | V1 async rounds on PP2 | – | – |
| **Two requests at once** | per-request state split so a second request fills the pipeline bubble | ~1.85x combined at two requests | ESTIMATED |
| Env-only switches | dense tiling, CPU pinning, chunk 4,096 | – | – |
| All-reduce push path for V4.1's message size | rebuilt admission | −0.08..−0.15 ms per round | ESTIMATED |
| Expert "wave" down kernel | rolled, four rows per block, bitwise | −0.3..−0.8 ms per round | ESTIMATED |
| Thinking-mode acceptance | probabilistic drafts (as in 1Cat [#183](https://github.com/1CatAI/1Cat-vLLM/pull/183)), sharded; draft temperature | – | – |
| Tensor-core decode attention | split-K HMMA, near-tie numerics | – | – |
| Four-card fork smoke | the 49-patch series on one board | – | – |

## Quality

- **The quant.** ISTA-DASLab report the IQ2_XXS build scoring the same as the unquantized release on their three
  benchmarks: AIME25 100.00, GPQA-Diamond 90.91, LiveCodeBench v6 89.71 (100 % recovery, reasoning effort 50). UPSTREAM
  CLAIM from their [model card](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF); we have not
  reproduced it, and those benchmarks are small (AIME is 30 problems).
- **Token-level fidelity of this build: not measured yet.** A KL-divergence and top-1 agreement test against the
  unquantized model is planned with the harness and panels used on DGX sPLIce, so the builds can be read side by side.
- **The speed work changed nothing measurable, by construction.** Every adopted lever is bitwise-identical or passes the
  greedy byte-identity gate; drafting changes speed, not the output distribution.
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
different numbers. **Status: built and CPU-tested; the four-GPU smoke test is queued.** [docs/four-card.md](docs/four-card.md)

## Hardware

Eight V100-SXM2-32GB on two NVLink quad boards; Threadripper PRO 3945WX; 251 GB RAM, one NUMA node. Host-to-device
bandwidth differs between the boards (512 MiB pinned: 25.5 GB/s for all four cards of board B together, 13.1 GB/s on
board C, where two GPUs share an x8 path). Volta has FP16 `mma.sync.m8n8k4` only: no `cp.async`, no `ldmatrix`, no FP8
tensor-core math, and a read ceiling of about 879 GB/s (measured by [v100-skinny](https://github.com/dnv2003/v100-skinny)).
Our fast expert kernels reach about 290-415 GB/s: they are limited by instruction issue and latency, which is why the
instruction diet won.

## Reproduce

1. Rebuild the engine source: in [forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/), `tools/apply_series.sh` applies the
   49 patches to 1Cat-vLLM #1277 (`899e9ed33`) and checks the result against the recorded tree (`b0d692425297`).
2. Apply [engine/production/0050-expert-diet.patch](engine/production/0050-expert-diet.patch) (result tree
   `4447483248bb`), then build vLLM and the `v41k` extension ([engine/README.md](engine/README.md)).
3. Download the weights (links above; none are distributed here), set `ENGINE_HOME`, `MODEL_HOME` and
   `CUDA_VISIBLE_DEVICES`, source [engine/configs/rec.env](engine/configs/rec.env) and start with
   [engine/configs/run_serve.sh](engine/configs/run_serve.sh).
4. Measure with the [A/B harness](harness/) ([method](docs/method.md)).

## Repository layout

| Path | What it is |
|-|-|
| `docs/` | [production](docs/production.md), [measurements](docs/measurements.md), [levers](docs/levers.md), [method](docs/method.md), [quality](docs/quality.md), [four cards](docs/four-card.md), [roadmap](docs/roadmap.md), [upstream contributions](docs/upstream-contributions.md) |
| `engine/` | the production patch, patches in testing, serving profile, environment and production switch set |
| `forks/1cat-4xv100-tp4/` | the 49-patch series against 1Cat #1277, with install, start, verify and smoke scripts |
| `harness/` | the A/B harness: arm runners, pairing and verdict scripts, greedy and divergence tracing |
| `evidence/queue-log.txt` | the state log of the 2026-11-03 test queue (paths replaced) |
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
  behind the prefill skip in testing.
- **Dennis Vertzyas (dnv2003), v100-skinny**: Volta kernel and bandwidth findings.
- **TensorFold (Elevatormusic)**: coupled sampled drafts.

Every source, with what we took from it, is in [CREDITS.md](CREDITS.md). If you build on this repository, please credit
them as well.
