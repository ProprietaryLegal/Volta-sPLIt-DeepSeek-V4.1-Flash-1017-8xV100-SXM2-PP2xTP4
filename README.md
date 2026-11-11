# Volta sPLIt: DeepSeek-V4.1-Flash-1017 on 8x V100-SXM2, split PP2 x TP4

## ~200 tok/s code and JSON · ~110 legal · ~85-110 prose and chat · 2,200 tok/s prompt reading at 128K · 8x V100 from 2018

[![code and JSON: ~200 tok/s](https://img.shields.io/badge/code%20and%20JSON-~200%20tok%2Fs-2EA043?style=for-the-badge)](#tokens-per-second)
[![legal: ~110 tok/s](https://img.shields.io/badge/legal-~110%20tok%2Fs-1F6FEB?style=for-the-badge)](#tokens-per-second)
[![prose and chat: ~85-110 tok/s](https://img.shields.io/badge/prose%20and%20chat-~85--110%20tok%2Fs-8250DF?style=for-the-badge)](#tokens-per-second)
[![prompt reading at 128K: 2,200 tok/s](https://img.shields.io/badge/prompt%20reading%20at%20128K-2%2C200%20tok%2Fs-D29922?style=for-the-badge)](#long-prompts-1k-to-256k)
[![first token at 128K: 59 s](https://img.shields.io/badge/first%20token%20at%20128K-59%20s-D29922?style=for-the-badge)](#long-prompts-1k-to-256k)
[![context: 524K per request](https://img.shields.io/badge/context-524K%20per%20request-555555?style=for-the-badge)](docs/measurements.md#context-sweep-2026-11-05)

Built by **Nick Mermiges, Esq.**, founder of [PLI Labs](https://proprietarylegal.ai/labs.html) · [proprietarylegal.ai](https://proprietarylegal.ai)

[![proprietarylegal.ai](https://img.shields.io/badge/proprietarylegal.ai-website-0B3D91)](https://proprietarylegal.ai) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-card-FFD21E)](https://huggingface.co/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-GGUF) [![PLI Labs](https://img.shields.io/badge/PLI%20Labs-research-1F6FEB)](https://proprietarylegal.ai/labs.html) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE) [![Hardware: 8x V100-SXM2-32GB](https://img.shields.io/badge/hardware-8x%20V100--SXM2--32GB-76B900)](#hardware) [![Method: ABBA paired](https://img.shields.io/badge/method-ABBA%20paired-555555)](docs/method.md)

## Tokens per second

Decode speed depends on what the model is writing, much less on how long the prompt is. MEASURED 2026-11-05 on the
checkpoint build, one request at a time, thinking off, greedy, 1,024 tokens out:

- **Code: 215 tok/s** after a 1K prompt, 200 at 32K, 183 at 128K, 160 at 256K.
- **Structured (JSON): 203 tok/s** at 1K, 207 at 32K, 197 at 128K, 180 at 256K.
- **Legal: 118 tok/s** at 1K, 117 at 32K, 111 at 128K, 103 at 256K.
- **Prose: 89 tok/s** at 1K, 90 at 32K, 91 at 128K, 84 at 256K.
- **Chat: 95 tok/s** at 1K, 107 at 32K, 96 at 128K, 81 at 256K.

**Prompt reading** is the same for every kind of text and rises with length: about 830-950 tok/s at 1K, 1,900 at 32K,
2,120 at 64K and 2,200 at 128K and 256K. A 32K prompt shows its first token in 17 s, 128K in 59 s, 256K in 119 s.
With thinking on, code and JSON decode at about 125-180 tok/s and the other kinds about as with thinking off.

### Long prompts: 1K to 256K

| prompt | first token | prompt reading | code | structured | legal | prose | chat |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1K | 1.22 s | 820-948 tok/s | 215.0 | 202.5 | 117.6 | 89.2 | 95.1 |
| 2K | 1.95 s | 1,024-1,082 tok/s | 203.6 | 207.2 | 114.8 | 97.9 | 94.5 |
| 4K | 3.26 s | 1,245-1,264 tok/s | 194.9 | 195.6 | 111.6 | 92.9 | 103.4 |
| 8K | 6.94 s | 1,178-1,188 tok/s | 207.9 | 209.0 | 109.1 | 92.2 | 108.2 |
| 16K | 10.4 s | 1,574-1,583 tok/s | 201.8 | 212.7 | 105.6 | 95.8 | 110.7 |
| 32K | 17.2 s | 1,894-1,913 tok/s | 200.5 | 206.6 | 116.5 | 90.1 | 106.9 |
| 64K | 30.9 s | 2,111-2,132 tok/s | 194.1 | 196.3 | 108.3 | 92.1 | 94.7 |
| 128K | 59.2 s | 2,198-2,220 tok/s | 182.8 | 196.5 | 110.9 | 91.1 | 95.8 |
| 256K | 118.7 s | 2,197-2,222 tok/s | 160.0 | 179.7 | 103.1 | 84.1 | 80.5 |

<sub>MEASURED 2026-11-05, checkpoint build, 135 requests. Each prompt is a real document of its kind cut to exactly that many
tokens in the server's own chat template, followed by the instruction for that kind from our head-to-head kit: code =
vLLM's Python source; structured = LegalBench items as JSON lines; legal = a public CC BY legal corpus, then LegalBench
prompt texts; prose = War and Peace; chat = a chat-style instruction over Les Misérables (both Project Gutenberg).
Thinking off, greedy, 1,024 tokens out, a random cache salt so no prompt is served from the prefix cache. Each cell is the
mean of 2 runs; the largest difference between the two runs of a cell was 2.7 tok/s, and the greedy output of the two
runs was byte-identical in 45 of 45 cells. First token = median of the five kinds; prompt reading = prompt tokens / first
token time, range over the five kinds; decode = (tokens − 1) / (last token − first token), client side.</sub>

### Thinking on

| prompt | first token | code | structured | legal | prose | chat |
|---|---:|---:|---:|---:|---:|---:|
| 1K | 1.2 s | 135.4 | 165.8 | 113.8 | 102.9 | 96.2 |
| 2K | 1.9 s | 136.1 | 158.3 | 118.7 | 99.0 | 110.4 |
| 4K | 3.2 s | 127.6 | 159.7 | 113.1 | 92.8 | 97.3 |
| 8K | 6.9 s | 133.3 | 134.6 | 110.1 | 101.7 | 100.2 |
| 16K | 10.3 s | 132.8 | 170.1 | 104.5 | 97.2 | 94.9 |
| 32K | 17.1 s | 125.6 | 177.3 | 112.5 | 102.0 | 91.1 |
| 64K | 30.9 s | 143.6 | 155.3 | 113.6 | 98.6 | 93.0 |
| 128K | 59.2 s | 141.9 | 168.0 | 103.2 | 93.8 | 96.7 |
| 256K | 119.0 s | 106.3 | 131.3 | 94.8 | 86.0 | 87.7 |

<sub>MEASURED 2026-11-05, same prompts, thinking on at reasoning effort 50 (our head-to-head kit's setting), one run per cell.
Each reply starts with the model's reasoning before the code or JSON, and code and JSON accept fewer drafts per round than
with thinking off; legal, prose and chat are within a few tok/s of thinking off.</sub>

### Prompt reading by text type

| prompt | code | structured | legal | prose | chat |
|---|---:|---:|---:|---:|---:|
| 1K | 834 | 820 | 838 | 948 | 852 |
| 2K | 1,024 | 1,038 | 1,051 | 1,082 | 1,062 |
| 4K | 1,264 | 1,245 | 1,254 | 1,255 | 1,259 |
| 8K | 1,178 | 1,178 | 1,180 | 1,182 | 1,188 |
| 16K | 1,579 | 1,574 | 1,576 | 1,583 | 1,577 |
| 32K | 1,904 | 1,894 | 1,903 | 1,913 | 1,897 |
| 64K | 2,119 | 2,118 | 2,111 | 2,132 | 2,115 |
| 128K | 2,220 | 2,199 | 2,198 | 2,218 | 2,216 |
| 256K | 2,208 | 2,202 | 2,197 | 2,222 | 2,219 |

<sub>Prompt reading = prompt tokens / first-token time, thinking off, mean of 2 runs. The rate depends on the length of the
prompt, not on its kind: at every length the five kinds are within a few percent of each other. It rises with length
because each 8,192-token prefill chunk carries a fixed cost and the two pipeline stages overlap more on long prompts.</sub>

### Short prompts, by text type

| kind of output | greedy (T=0) | sampled (T=1) | tokens per round, T=0 |
|---|---:|---:|---:|
| code | **213.1** (211.8-213.3) | 196.8 (188.3-203.8) | 4.70 |
| structured (JSON) | **209.4** (209.3-210.3) | 205.4 (200.8-213.3) | 4.63 |
| legal | **115.7** (115.3-115.7) | 108.4 (106.7-116.9) | 2.56 |
| prose | **98.0** (97.7-98.3) | 87.2 (87.1-89.5) | 2.17 |
| chat | **96.2** (96.1-96.5) | 93.8 (93.4-96.5) | 2.11 |
| thinking on, 4 prompts, token-weighted | – | **132.3** (114.1-200.7 per prompt) | – |

<sub>MEASURED 2026-11-05 on the checkpoint build, our head-to-head kit (short prompts, 1,024 tokens out, thinking off,
median of reps with range; client-side decode = (tokens − 1) / (last token − first token)). Greedy repeats were
byte-identical. Tokens per round = 1 + accepted drafts per verify round, from the server's counters.</sub>

### Why the kinds differ

Every round the DSpark drafter proposes five tokens and the target model verifies them all at once; the round costs
about the same whatever is accepted. Code and JSON are predictable, so 3.6-3.8 of the five drafts are accepted and a
round emits about 4.7 tokens. Legal writing, prose and chat accept 1.1-1.6, so a round emits 2.1-2.6. The engine runs at
the same speed in both cases; the text decides how many tokens each round yields. Context length matters
less: a round costs about 22.5-23 ms after a 1K prompt and 26.5-27 ms after 256K. Code also accepts fewer drafts
deep in a long file (3.98 per round at 1K, 3.29 at 256K), so it slows the most at depth.

### The progression, in tok/s

| build (8x V100-SXM2-32GB, same host) | date | decode, thinking off | thinking on | label |
|---|---|---:|---:|---|
| [Previous build](previous-build/): EXL3 pack on philbert440's SM70 engine | 2026-11-01 | 42-46 | 31.4 | MEASURED (its own method) |
| **Volta sPLIt**: PP2 x TP4 port of 1Cat #1277, no speed levers | 2026-11-03 | 99.2 | 88.0 | MEASURED |
| + six token-path and draft levers | 2026-11-03 | ~105.8 | ~108.4 | MEASURED (ABBA) |
| + fused quantize plan, keep-batch, fast expert kernels, attention fusions, instruction diet | 2026-11-03 | ~118 | ~121 | MEASURED / ESTIMATED |
| + prefill skip, larger GPU hot ring, PCIe-switch move (17 switches) | 2026-11-03 | 119.0 | 120.8 | MEASURED, one boot |
| + tiled and fused index scorers, drafter projection sharding (V1 runner) | 2026-11-04 | 120.2-120.5 | 121.8-122.0 | MEASURED, 2 arms |
| + Model Runner V2 | 2026-11-04 | 134.2-135.0 | 136.4-136.6 | MEASURED, 2 arms |
| **+ all-reduce push, NCCL host hand-off, SM70 prefill expert GEMM: the 2026-11-05 checkpoint (30 keys)** | 2026-11-05 | **~135.2** | **~137.6** | ESTIMATED: the row above with the all-reduce push's −0.180 ms per round; the other two change prompt reading only |

<sub>This table uses one fixed set throughout (A/B harness: 3 x 1,024 greedy tokens; a seeded T=1 thinking-on set of 12
prompts) so the rows compare. The by-kind tables above use other prompts. The previous build used its own method; the
fair engine comparison is the time per verify round: 71.2-71.6 ms there against 23.4 ms here before the all-reduce push,
about 3.0x faster per round (ESTIMATED arithmetic).</sub>

**First token, same prompts across builds** (A/B harness depth prompts and the head-to-head kit's 128K prompt, cold,
MEASURED):

| prompt | 2026-11-03 port | + prefill skip | + fused index scorer, MRV2 | **2026-11-05 checkpoint** |
|---|---:|---:|---:|---:|
| 32K | 22.6 s | 20.1 s | 19.4 s | **16.4 s** |
| 128K | – | – | 69.0-71.5 s (before the NCCL hand-off) | **58.3 s** |
| 150K | 111.1 s | 87.0 s | 81.3-82.8 s | – |
| 300K | 263.9 s | 178.0 s | 158.4-159.0 s | – |

<sub>32K and 128K on the checkpoint: head-to-head kit, 32,744 and 130,448 tokens, 2 runs, median. The other cells are the
A/B harness depth runs of their dates (32,718 / 150,038 / 299,227 tokens). The context sweep above gives the checkpoint
at 256K.</sub>

### Time per round: the engineering metric behind the tok/s

| stage | T=0 ms/round | T=1 ms/round | label |
|---|---:|---:|---|
| PP2 x TP4 port, no levers (2026-11-03) | 31.1 | 31.7 | MEASURED |
| all 17 switches, after the PCIe-switch move (2026-11-03) | 26.3 | 26.9 | MEASURED; decode-only 25.30 / 25.20 |
| + index scorers, drafter sharding, V1 runner (2026-11-04) | 26.0 | 26.6-26.7 | MEASURED, 2 arms; decode-only 24.98 / 24.92-24.98 |
| + Model Runner V2 (2026-11-04) | 23.2-23.4 | 23.8 | MEASURED, 2 arms; decode-only 22.22-22.26 / 22.17-22.19 |
| **+ all-reduce push: checkpoint (2026-11-05)** | **~23.1** | **~23.6** | ESTIMATED: −0.180 ms (ABBAABBA, 95 % −0.278..−0.081); decode-only ~22.05 |

A round is one target verification step: the target checks the drafted tokens and emits one token plus every accepted
draft. Per-request throughput is (1 + accepted drafts per round) / round time. Every change on this page was decided on
round time, measured decode-only in paired ABBA arms ([method](docs/method.md)).

## What this is

**A 249 GB model on GPUs from 2018, every expert resident.** DeepSeek-V4.1-Flash-1017 is a 551.9B-parameter mixture of
experts with DeepSeek's Engram n-gram memory. Its weights here are 248.8 GB (138.24 GB of IQ2_XXS experts and backbone,
110.60 GB of IQ4_NL Engram tables). The experts and backbone live in the 256 GiB of HBM2 on eight V100-SXM2-32GB cards:
sm_70 silicon with no FP8 or BF16 tensor cores and no `cp.async`. No expert is paged from host memory during decode. The
Engram tables stay in host RAM and each round gathers only the rows it needs: about 0.12 ms per decode round, measured
over 52 profiled rounds ([docs/levers.md](docs/levers.md#did-not-work), "hot Engram in HBM"). Correction 2026-11-06:
this paragraph used to say all 248.8 GB lived in HBM2.

**Split across two NVLink boards.** 1CatAI's [1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM) DeepSeek-V4.1 package
([#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277)) runs this model on one 4-GPU board with experts offloaded. We
ported it to pipeline parallel 2 x tensor parallel 4: layers 0-19 and the Engram lookup on one NVLink quad; layers 20-39,
the head and the DSpark drafter on the other; PCIe between them. Then we made it fast, one switch at a time, each
admitted only by a paired A/B on this machine.

**From 99 to about 135 tok/s in three days, and prompts read twice as fast.** Decode went from 31.1 to about 23.1 ms per
round (2026-11-03 to 11-05) through our own CUDA and host-path work and the move to Model Runner V2, every change
bitwise-identical or through the near-tie gate. Prompt reading went from about 1,350 tok/s at 150K (2026-11-03) to
about 2,200 tok/s at 128K today: the prefill skip, the fused prefill index scorer, the NCCL host hand-off between the
two boards and our SM70 prefill expert GEMM. About thirty more ideas lost their A/B or failed a numerics gate; they are
listed below with the reason.

**The 2026-11-05 checkpoint.** This is the build we now use day to day. It is frozen: new work is built and tested on a
separate 4-GPU test machine and comes here only through a paired window. It serves one request at a time.

**Since 2026-11-11** our host runs it with three later changes, each tested here against a rule written before its
data: three chat slots (three long chats taking turns keep their caches: 6 of 6 hits against 0 of 6, first token
0.57-0.88 s against 20.6-49.2 s), system notes kept in place on the Messages endpoint, and top-k segments of 1,024
(decode round −0.17 to −0.40 ms, outputs identical). Detail:
[docs/levers.md](docs/levers.md#after-the-checkpoint-adopted-2026-11-11). The speed tables on this page are the
checkpoint's and were not re-measured.

**Exact outputs.** The target verifies every draft with the speculative-sampling acceptance rule, so the text keeps the
target model's distribution whatever the drafter proposes. The speed changes do not change what the model computes
(bitwise-identical, or within the near-tie gate). One difference under Model Runner V2: a sampled (T>0) request that
asks for logprobs uses MRV2's rejection sampler instead of our keyed draw streams. Its text still follows the target
distribution, but it is not the same sample the V1 runner would have drawn. Requests without logprobs keep the keyed
streams.

**Where the previous build is still ahead.** It read short and medium prompts faster (about 2,900-3,300 tok/s, its own
method) and served three requests at once. The checkpoint took one request at a time. Since 2026-11-11 our host keeps
three chats' caches (three slots) and still runs one request at a time; more combined throughput is not established.

**Everything is published:** the measurements, the 49-patch engine series, our production patches, the serving profile
and environment, the A/B harness, and the log of the test queue.

<!-- pli:blurb:start -->

> Published by [PLI Labs](https://proprietarylegal.ai/labs.html), the open research arm of [Proprietary Legal Intelligence](https://proprietarylegal.ai). PLI builds AI systems around a legal organization's own work product, combining retrieval, staged workflows, validation, and attorney review. Visit [proprietarylegal.ai](https://proprietarylegal.ai) to explore our work and discuss what your organization needs.

<!-- pli:blurb:end -->

## What runs

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two 4-GPU SXM2 boards, NVLink inside each board; four PLX switches, each on its own CPU root complex at PCIe Gen3 x16, Gen3 x8 per GPU |
| Host | AMD Threadripper PRO 3945WX (12 cores), one NUMA node, 251 GB RAM |
| Power and clocks | 150 W per card, graphics clock capped at 1522 MHz |
| Model | DeepSeek-V4.1-Flash-1017: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` (IQ2_XXS experts, 138.24 GB; IQ4_NL Engram, 110.60 GB); config, tokenizer and DSpark drafter (FP8, 7.93 GB) from [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` |
| Engine | 1Cat-vLLM #1277 (merge `899e9ed33`) + 1Cat main `6db9c81` and 25 open 1Cat PRs + our PP2 port and lever stack: the [49-patch series](forks/1cat-4xv100-tp4/) and our production patches in [engine/production/](engine/production/); the `v41k`, `v41idx`, `v41pidx` and `v41prefmoe` SM70 CUDA libraries built from that source |
| Layout | PP2 x TP4. Stage 1 (board B): layers 0-19, Engram lookup and hash state (Engram tables in host RAM). Stage 2 (board C): layers 20-39, the head, the drafter. TP all-reduce over NVLink; the stage hand-off over host shared memory (`NCCL_P2P_LEVEL=NVL`) |
| Engine settings | vLLM Model Runner V2, synchronous scheduling, FULL CUDA graphs for 1-6 tokens per step, chunked prefill 8,192, prefix caching, every expert resident |
| Drafter | DSpark, 5 drafts per round, coupled (keyed) sampled drafts at T>0 |
| Context | 524,288 tokens per request, one request at a time (`max-num-seqs 1`; three chat slots on our host since 2026-11-11), KV pool 2,076,870 tokens (packed KV: a 524,288-position GPU hot ring + host arena) |
| Thinking | on by default; `chat_template_kwargs: {"thinking": false}` turns it off |
| Switch set | 32 keys (the checkpoint's 30 and two adopted 2026-11-11): [engine/configs/rec.env](engine/configs/rec.env) |

Serving profile, environment and the production switch set: [engine/](engine/) and [docs/production.md](docs/production.md).

## What worked

Each lever is a switch that defaults off; with the switch off the code path is the old one. ms per round, ABBA averages.

| change | where it came from | effect | numerics |
|---|---|---|---|
| Indexer top-k reduce on the device (`INDEX_REDUCE`) | ours | −0.85 ms; also makes T=1 output identical across restarts | exact |
| Double-buffered Volta dense mat-vec (`DMV_X`) | ours, on #1277's `dmv13` | −0.42 ms (6/6 pairs) | bitwise |
| Coupled sampled drafts (`COUPLED_DRAFTS`) | [TensorFold #25](https://github.com/Elevatormusic/TensorFold/pull/25) (merged); our port | T=1 acceptance 1.85 → 2.25 per round, +14 % tok/s | exact (keyed draws) |
| Draft-head and sampler sharding (`MARKOV_SHARD`, `COUPLED_SHARD`, `COUPLED_LOCAL`) | ours | −0.2 ms (T=0); −0.23 and −0.12..−0.24 ms (T=1) | exact |
| Expert plan fused into the q8 quantize launch (`PLAN_FUSE`) | ours | −0.36 (T=0), −0.27 (T=1) | bitwise |
| Keep the request in the batch across empty pipeline steps (`PP_KEEP_BATCH`) | our V1-runner port of 1Cat [#1263](https://github.com/1CatAI/1Cat-vLLM/pull/1263) | 128K −24.8 % (84 → 111 tok/s), 64K −17.4 %, 32K −9.7 % | texts identical |
| Fast routed-expert kernels, down and gate/up (`EXPERT_FAST`) | ours | down −0.68..−0.84; gate/up a further −0.53..−0.82 (T=0) | bitwise, sanitizers clean |
| Fused attention prologue and epilogue (`FUSE_ATTN_PREP`, `_POST`) | ours | −0.19 ms | bitwise |
| Hot-ring refill after a prefix-cache hit (`HOT_REFILL`) | our port of 1Cat issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341) | correctness fix | – |
| Expert-kernel instruction diet (`EXPERT_DIET=3`) | ours | **−0.871 ms** | near-tie gate; sanitizers 0 errors |
| Router floor (`ROUTE_FAST`, 4 warps) | ours | −0.165 ms, inside the session's drift | greedy bitwise |
| **Prefill skip (`PREFILL_SKIP_ROWS=3072`)** | ours; design reference: [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100)'s replay rows | **first token −8.8 % at 32K, −20.6 % at 150K, −31.5 % at 300K** | identical output at every length |
| **Tiled decode index scorer (`INDEX_TILED`, `v41idx`)** | ours | **decode round −7.0 % at 150K, −13.7 % at 300K**; short context not detectable | bitwise |
| Larger GPU hot ring (`KV_HOT_POSITIONS=524288`) | our setting of #1277's packed KV | 300K −1.09 ms per round, 150K −0.25 | identical output |
| **Fused prefill index scorer (`INDEX_FUSE=ilp4`, `v41pidx`)** | ours; ideas from 1Cat [#1280](https://github.com/1CatAI/1Cat-vLLM/pull/1280), [#1282](https://github.com/1CatAI/1Cat-vLLM/pull/1282) and philbert440's fused SM70 indexer | **first token −4.9 % at 150K, −9.5 % at 300K** | near-tie gate PASS; output identical |
| Drafter projection sharding (`DRAFT_MP_SHARD`) | ours | −0.130 ms per round, 8 of 8 pairs faster | bitwise |
| **Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER=1`)** | vLLM's newer runner as carried by 1Cat, with 1Cat [#1221](https://github.com/1CatAI/1Cat-vLLM/pull/1221)'s DSpark path; our DeepSeek-V4.1 port | **−2.759 ms per round** (120.5 → 134.2 tok/s at T=0) | bitwise |
| All-reduce push for V4.1's message size (`SM70_MOE_ADD_ALLREDUCE`, `SUM2_PUSH_ANY`, `SM70_TP4_PUSH_ALLREDUCE_SMALL_MESSAGES`; test D44R5) | ours, on 1Cat's SM70 custom all-reduce | −0.180 ms per round (ABBAABBA, 95 % −0.278..−0.081) | T=1 texts identical |
| **NCCL host hand-off between the boards (`NCCL_P2P_LEVEL=NVL`, 2026-11-05)** | NCCL setting; found by our stage-split profile | **first token −13.4 % at 32K, −14.2 % at 128K**; decode unchanged | bitwise |
| **SM70 prefill expert GEMM (`PREFILL_IQ_GEMM`, tiles `5,4,4,4,4,4`, `v41prefmoe`; test D51, 2026-11-05)** | ours | **first token −4.1 % at 32K, −4.3 % at 150K, −2.4 % at 300K** (before the NCCL change) | near-tie gate PASS; identity hashes unchanged |
| **Three chat slots (`max-num-seqs 3`, 2026-11-11)** | ours, on our multi-request engine work (not published yet) | **cache hits when three long chats take turns: 0 of 6 → 6 of 6; first token 20.6-49.2 s → 0.57-0.88 s**; lone request unchanged | near-tie gate PASS, every row identical |
| System notes keep their place (`SYSTEM_IN_PLACE=1`, 2026-11-11) | ours | a system message added mid-chat keeps the cache: 0 → 31,248 of 31,300 tokens cached, next first token 11.2 → 0.51 s | replies without such a note identical |
| Top-k segments of 1,024 (`TOPK_SEG=1024`, 2026-11-11) | ours | decode round −0.17 ms at 8K, −0.31 at 32K, −0.33 at 64K, −0.40 at 128K | byte-identical output |

Two lessons: two of the winners were predicted near zero by isolated kernel benchmarks, so only the full A/B decides;
and the biggest prompt-reading gain of 2026-11-05 was a one-line transport setting found by profiling where time went
between the stages, not a kernel. Detail: [docs/levers.md](docs/levers.md#adopted).

## What did not work

| change | result | why |
|---|---|---|
| Expert top-p pruning (0rand / TensorFold) | 78 tok/s, greedy output changed | the divergence is built into the method |
| V1 async scheduling with the request-end guard | +1.678 ms per round slower | rejected; Model Runner V2 replaced it |
| Router with 8 warps instead of 4 (2026-11-11) | −0.027 ms per round (95 % −0.125..+0.071), texts identical | neutral on this host |
| TP8 across both boards | no-go at the probe | the 8-way all-reduce across the boards took 30.8 µs against 5.28 µs inside a board |
| Prefill chunks of 4,096 or 16,384 | near-tie gate FAIL / slower | chunk size changes long-prompt numerics |
| **Fused prefill attention, exact-softmax mode (lever A mode 2, 2026-11-05)** | first token 32K 16.70 → 14.80 s, 128K 60.47 → 54.19 s; **near-tie gate FAIL**: 1 of 8 identical, KL mean 0.0109 | 99.4 % of attention elements bit-equal, but the rest moved confident tokens; a bitwise version is in testing (below) |
| Split-K tensor-core decode attention (`ATTN_HMMA=2`) | −0.143 ms, not detectable; near-tie gate FAIL | rejected on quality |
| FP16-packed shared-expert down kernel (`SHARED_DOWN`) | near-tie gate FAIL (KL max 0.17) | rejected on quality |
| Expert "wave" down kernel | +0.216 ms per round slower | – |
| Fused layer transition (three variants) | slower or neutral | the mixing step dominates |
| Probabilistic sharded drafts, draft temperatures | no variant faster beyond noise | the extra drafter work eats the acceptance gain |
| Bitwise FP8 drafter mat-vec | slower than the sharding alone | off |
| Asynchronous scheduling on Model Runner V2 | −0.085..−0.117 ms against synchronous MRV2 | about 0.4 %; off for now |
| CPU pinning, spin-wait broadcast, 200 W, deeper prefetch, L2 warm-up, Engram GPU cache, IQ1_M repack | neutral, slower or no-go | details in [docs/levers.md](docs/levers.md#did-not-work) |

Full table with numbers: [docs/levers.md](docs/levers.md#did-not-work).

## Next

Built and tested on the separate 4-GPU test machine; each comes to the checkpoint only through a paired window here.

| item | status | label |
|---|---|---|
| **Fused prefill attention, bitwise mode 3** | bit-identical to production's attention on all 40 test cases and all 256 tail shapes; 42.7 → 20-22 ms per packed layer; sanitizers clean | MEASURED on the test machine (synthetic tensors); real-weight window pending; forecast first token −11 to −14 % at 32K (ESTIMATED) |
| Faster prefill expert tiles (mixed M64/M32) | 3,396 real-shape cases bit-identical to production; best variant −10 % expert-kernel time, being separated from plain retuning | MEASURED on the test machine (kernel only); PENDING |
| Decode kernels for two to four requests at once, each request's output identical to running it alone | started 2026-11-05 on the test machine | forecast 2-3x aggregate decode at four requests (ESTIMATED) |
| Single-request decode: fewer, fused small kernels; one launch per layer for the experts | started 2026-11-05 on the test machine | forecast +3 to +8 % decode (ESTIMATED) |
| Memory for four requests: row-block Engram gather (1Cat issue [#1342](https://github.com/1CatAI/1Cat-vLLM/issues/1342)), prefill scratch reuse | started 2026-11-05 on the test machine | PENDING |
| Three chat slots on Model Runner V2 | **in production since 2026-11-11**: three long chats taking turns hit the cache 6 of 6 times (0 of 6 with one slot); one request runs at a time; the multi-request engine work it runs on is not published yet | MEASURED |
| The 32K decode case under MRV2 (about 1.4 ms per round slower than V1 at that one length) | cause unknown | INCONCLUSIVE |

Queue order and status: [docs/roadmap.md](docs/roadmap.md).

## Quality

- **LegalBench (MEASURED 2026-11-05): 0.716 balanced accuracy over 22 tasks** (issue 0.614, rule 0.693, conclusion
  0.722, interpretation 0.777, rhetoric 0.690). Official base prompts and scoring, greedy, thinking off, 1,292 items,
  0 errors. Per-task scores and the answer-reading rule: [docs/quality.md](docs/quality.md#legalbench-measured-2026-11-05).
- **MMLU-Pro (MEASURED 2026-11-05): 79.9 %** ±1.5 (700 items: the first 50 of each of the 14 subjects; lm-eval 5-shot
  chain of thought, thinking off, greedy, 0 errors). **HumanEval+ pass@1: 89.6 %** on the plus tests (147 of 164) and
  94.5 % on the base tests (EvalPlus, thinking off, greedy, 0 errors). [Method](docs/quality.md#mmlu-pro-and-humaneval).
- **Fidelity to the original model (MEASURED 2026-11-05).** Position by position against the original
  DeepSeek-V4.1-Flash-1017's reference logits (sudoingX's `p4_kld.py` panels): the served build picks the original's
  most likely next token **89.0 %** of the time on the general panel (254,846 positions, 8 domains) and **92.5 %** on our
  legal panel (71,080 positions); KL divergence lower bound 0.132 and 0.156. Closest on code, math, tool calls and
  extraction (89-99 %), furthest on chat, writing and multilingual text (81-86 %). This gap is the 2-bit quantization,
  not the speed work. [Tables and method](docs/quality.md#kl-divergence-against-the-original-model-served-path).
- **The quant.** ISTA-DASLab report the IQ2_XXS build scoring the same as the unquantized release on their three
  benchmarks: AIME25 100.00, GPQA-Diamond 90.91, LiveCodeBench v6 89.71 (100 % recovery, reasoning effort 50). UPSTREAM
  CLAIM from their [model card](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF); we have not
  reproduced it, and those benchmarks are small (AIME is 30 problems).
- **The speed work changed nothing measurable, by construction.** Every adopted lever is bitwise-identical or passes the
  near-tie gate; drafting changes speed, not the output distribution. Model Runner V2 was bitwise-identical to the V1
  runner in every A/B arm (logprob requests at T>0: see "Exact outputs" above).
- **Long context works.** Needle retrieval at ~450K and ~498K tokens: 6 of 6 needles in 4 of 4 runs. Prefix-cache hits
  at 36K-500K returned the same text as cold runs.

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

## Hardware

Eight V100-SXM2-32GB on two NVLink quad boards; Threadripper PRO 3945WX; 251 GB RAM, one NUMA node. Each of the four PCIe
switches has its own CPU root complex at Gen3 x16, and each GPU links to its switch at Gen3 x8. Volta has FP16
`mma.sync.m8n8k4` only: no `cp.async`, no `ldmatrix`, no FP8 tensor-core math, and a read ceiling of about 879 GB/s
(measured by [v100-skinny](https://github.com/dnv2003/v100-skinny)). Our fast expert kernels reach about 290-415 GB/s:
they are limited by instruction issue and latency, which is why the instruction diet won.

## Reproduce

1. Rebuild the engine source: in [forks/1cat-4xv100-tp4/](forks/1cat-4xv100-tp4/), `tools/apply_series.sh` applies the
   49 patches to 1Cat-vLLM #1277 (`899e9ed33`) and checks the result against the recorded tree (`b0d692425297`).
2. Apply the ten production patches in order, checking each result tree:
   [0050](engine/production/0050-expert-diet.patch) (`4447483248bb`), [0051](engine/production/0051-prefill-skip.patch)
   (`32d4a9d9b0c1`), [0052](engine/production/0052-index-tiled.patch) (`4760febd4fe7`),
   [0053](engine/production/0053-index-fuse.patch) (`421c427444a4`), [0054](engine/production/0054-draft-mp-shard.patch)
   (`09cf8cc28b7b`), [0055](engine/production/0055-mrv2.patch) (`e85291152ae9`),
   [0056](engine/production/0056-allreduce-sum2-push.patch) (`007852b33339`),
   [0057](engine/production/0057-prefill-iq-gemm.patch) (`42947e400952`),
   [0058](engine/production/0058-system-notes-in-place.patch) (`1ee8ad2755b4`) and
   [0059](engine/production/0059-topk-segment-width.patch) (`e082b9540245`). Then build vLLM, the `v41k` extension and the
   `v41idx`, `v41pidx` and `v41prefmoe` libraries ([engine/README.md](engine/README.md)). Library builds are not
   byte-reproducible: the claim is the same source and the same flags.
3. Download the weights (links above; none are distributed here), set `ENGINE_HOME`, `MODEL_HOME` and
   `CUDA_VISIBLE_DEVICES`, source [engine/configs/rec.env](engine/configs/rec.env) (32 keys) and start with
   [engine/configs/run_serve.sh](engine/configs/run_serve.sh).
4. Measure with the [A/B harness](harness/) ([method](docs/method.md)).

## Repository layout

| Path | What it is |
|-|-|
| `docs/` | [production](docs/production.md), [measurements](docs/measurements.md), [levers](docs/levers.md), [method](docs/method.md), [quality](docs/quality.md), [roadmap](docs/roadmap.md), [upstream contributions](docs/upstream-contributions.md) |
| `engine/` | the production patches, patches in testing, serving profile, environment and production switch set |
| `forks/1cat-4xv100-tp4/` | the 49-patch series against 1Cat #1277 that the production patches apply on |
| `harness/` | the A/B harness: arm runners, pairing and verdict scripts, greedy and divergence tracing |
| `evidence/queue-log.txt` | the state log of the test queue through the 2026-11-05 checkpoint (paths replaced) |
| `previous-build/` | our first build on these eight cards (EXL3 pack, 2026-11-01) |
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
- **Phil Tompkins (philbert440)**: the V100 engine and EXL3 pack our previous build ran on, the replay-row design behind
  our prefill skip, and the SM70 sparse prefill attention kernel our fused prefill attention starts from.
- **Dennis Vertzyas (dnv2003), v100-skinny**: Volta kernel and bandwidth findings.
- **sudoingX**: the `p4_kld.py` fidelity method and general panel behind our KL divergence measure.
- **TensorFold (Elevatormusic)**: coupled sampled drafts.
Every source, with what we took from it, is in [CREDITS.md](CREDITS.md). If you build on this repository, please credit
them as well.
