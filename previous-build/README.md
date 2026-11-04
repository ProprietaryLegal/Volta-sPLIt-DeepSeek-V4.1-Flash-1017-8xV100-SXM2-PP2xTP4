> **Previous build.** This is the record of our first build on the same eight V100s (2026-11-01): philbert440's EXL3
> pack on his SM70 engine, 71.2-71.6 ms per verify round, 42-46 tok/s single stream with thinking off. It is kept here as
> history. The current build, [Volta sPLIt](../README.md), runs about 2.7x faster per round (119.0 tok/s decode, MEASURED 2026-11-03).
> Paths below are relative to this folder.

# Volta sPLIce: DeepSeek-V4.1-Flash on 8x V100, PP2 x TP4 on two NVLink quads, Engram resident in host RAM

[![proprietarylegal.ai](https://img.shields.io/badge/proprietarylegal.ai-website-0B3D91)](https://proprietarylegal.ai) [![PLI Labs](https://img.shields.io/badge/PLI%20Labs-research-1F6FEB)](https://proprietarylegal.ai/labs.html) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](../LICENSE) [![Hardware: 8x V100-SXM2-32GB](https://img.shields.io/badge/hardware-8x%20V100--SXM2--32GB-76B900)](#hardware) [![Evidence: evidence/](https://img.shields.io/badge/evidence-evidence%2F-555555)](evidence/)

Built by **Nick Mermiges, Esq.**, founder of [PLI Labs](https://proprietarylegal.ai/labs.html) · [proprietarylegal.ai](https://proprietarylegal.ai)

This is the master page for our V100 work on DeepSeek V4.1 Flash: the configuration that serves in production, every
number we measured on it, every experiment that won or lost, and the patches and tools that are ours.

DeepSeek-V4.1-Flash-1017, in Phil Tompkins' franken-v100 EXL3 pack, served by his SM70 engine
([philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100), built on 1CatAI's
[1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM)) on one host with eight V100-SXM2-32GB cards. The cards sit on two
NVLink quad boards: tensor parallel 4 inside each board over NVLink, pipeline parallel 2 between the boards over PCIe.
On top of the engine we run three small patches, the Engram tables resident in host RAM after a RAM upgrade, and a
shared-memory-staged EXL3 MoE prefill kernel of our own. Requests may be 327,680 tokens long, three at a time, from a KV
pool of 927,004 tokens.

<table>
<tr>
<td align="center"><h2>25.8&nbsp;s</h2>first token, 75K-token prompt<br><sub>cold or warm; was 46.0 cold</sub></td>
<td align="center"><h2>~2,910</h2>tok/s prefill<br><sub>75K-token prompts</sub></td>
<td align="center"><h2>71.2&#8209;71.6</h2>ms per verify round<br><sub>42&#8209;46 tok/s single stream, thinking off</sub></td>
<td align="center"><h2>29.6</h2>tok/s decode beside a 75K prefill<br><sub>was 18.2; longest gap 0.62 s</sub></td>
<td align="center"><h2>16&nbsp;/&nbsp;16</h2>greedy outputs byte-identical<br><sub>to the unmodified baseline</sub></td>
</tr>
</table>

<sub>Production configuration (resident Engram + staged MoE prefill), boot 2026-11-01 05:19 UTC. Host memory at
DDR4-2666, graphics clock capped at 1425 MHz, 180 W power limit per card. Six seeds per cell, ~75,000-token prompts, a
fresh <code>cache_salt</code> on every request, 2,048-token outputs. Baseline: the same engine and settings with Engram
read from NVMe, 2026-11-01 00:36-01:33 UTC. Numbers: <a href="evidence/2026-11-01-final/results.json">evidence/</a>;
method: <a href="docs/method.md">docs/method.md</a>.</sub>

- **First token for a 75K-token prompt in 25.81 s cold and 25.75 s warm**, against 46.00 s and 27.02 s on the baseline
  (−43.9 %, CI −48.8..−37.6; −4.7 %, CI −5.0..−4.3).
  <sub>6 seeds per cell, 2026-11-01 · [measurements](docs/measurements.md#2026-11-01-production-final)</sub>
- **Engram resident in host RAM removed the cold penalty**: cold equals warm on every seed, and the bimodal cold cells
  went away (cold −41.4 %, CI −46.5..−34.8, on its own). It holds ~208 GiB of the host's ~251 GiB.
  <sub>arm ER1, 2026-11-01 01:51-02:17 UTC · [experiments](docs/experiments.md#er1-engram-tables-resident-in-host-ram)</sub>
- **Our staged EXL3 MoE prefill kernel**: −7.5 to −13.2 % on the tiled MoE pass at the kernel level, bit-identical
  outputs; warm 75K first token −2.33 % (CI −3.15..−1.50) in the server.
  <sub>arm MP1, 2026-11-01 04:33 UTC boot · [patch 0003](patches/README.md#0003-shared-memory-staged-exl3-tiled-moe-prefill)</sub>
- **Decode beside a prefill**: a running stream keeps 29.6 tok/s while a cold 75K prompt prefills beside it (baseline
  18.2 tok/s, longest gap 2.10 s → 0.62 s), and that prompt's first token comes in 50.6 s instead of 104.3 s.
  <sub>seed 36, 2026-11-01 · [measurements](docs/measurements.md#decode-beside-a-cold-75k-prefill)</sub>
- **Three ~300K-token prompts at once finish in 355.5 s** (baseline 476.1 s), 0 preemptions, peak KV use 50 %.
  <sub>seed 58, 2026-11-01 · [measurements](docs/measurements.md#2026-11-01-production-final)</sub>
- **Three full-length requests fit in the KV pool at once**: 3 x 314,728-token prompts resident together peaked at
  71.5 % KV use with 0 preemptions (~960K tokens resident); the largest load the server accepts, 3 x 327,680 tokens,
  would use ~73 % (ESTIMATED).
  <sub>KV hold-stress, 2026-11-01 09:56-10:10 UTC · [KV capacity](docs/kv-capacity.md#the-measurement-2026-11-01)</sub>
- **Context and cache**: prefill holds ~3,300 tok/s from 32K to 75K tokens and is ~10 % lower at 300K; an exact
  repeat, or a new tail on the same cached 75K prefix, answers in ~0.5 s instead of ~23 s. llama-benchy on book text:
  37-46 tok/s decode for one stream at depths 0-65K.
  <sub>2026-11-01 10:18-10:51 UTC · [measurements](docs/measurements.md#2026-11-01-production-second-session)</sub>
- **Quality gates unchanged**: greedy 16 / 16 byte-identical to the baseline's references, 0 near-ties; 15 / 15
  functional API checks (including `tool_choice=required`, thinking on/off and a 32K three-needle recall); our private
  task suite scores the same as the baseline (41 of 46 both).
  <sub>2026-11-01 05:19-06:07 UTC · [method](docs/method.md#gates)</sub>

We also lose, or have not won yet, on several rows, and [what did not work](#what-did-not-work) lists them: KV growth
beyond 927,004 tokens cost either decode speed (+9-13 % per verify round) or byte identity; adaptive draft depth was
not byte-identical; Engram lookahead, a larger prefill chunk and the engine's decode-lane switch all lost; a warm-up
after start showed nothing measurable. Single-stream decode has not moved: a verify round costs ~71.5 ms in every
configuration. The profile and decode study show why (not memory bandwidth, but per-kernel cost, the two pipeline
stages running in series, and host time); the exact fixes found so far are ESTIMATED at 70 → ~65-66 ms per round.
Thinking-mode decode is lower (31.4 tok/s) because the drafter accepts fewer tokens on reasoning text. No test has yet
checked that concurrent requests leave each other's greedy output unchanged, and an in-memory prefix-cache hit is not
always byte-identical to a cold run (an open finding, below).

**Engine:** [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100) tag
`ds41-vision-20261025b` (`23cec6a9`), prebuilt SM70 wheel, its `_C` library rebuilt with our patch 0003.
**Weights:** [philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100](https://huggingface.co/philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100)
@ `99d85a46`, plus DeepSeek's two Engram shards. **Production:** [docs/production.md](docs/production.md).
**Numbers:** [docs/measurements.md](docs/measurements.md). **Every experiment:** [docs/experiments.md](docs/experiments.md).

This repository is the record: what we run, how we measured it, what worked, what did not, and what is still open.
Several results are still being measured; their slots are marked **PENDING** in [docs/roadmap.md](docs/roadmap.md) and
will be filled as they finish. Issues, measurements on your own V100s and pull requests are welcome; see
[CONTRIBUTING.md](../CONTRIBUTING.md).

**Earlier V100 reports:**
[deepseek-v4-flash-v100](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100) (its
[2026-11-01 interim report](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100/blob/main/docs/v4.1-flash-1cat-vllm-2026-11-01.md)
is superseded by this page).

<!-- pli:blurb:start -->

> Published by [PLI Labs](https://proprietarylegal.ai/labs.html), the open research arm of [Proprietary Legal Intelligence](https://proprietarylegal.ai). PLI builds AI systems around a legal organization's own work product, combining retrieval, staged workflows, validation, and attorney review. Visit [proprietarylegal.ai](https://proprietarylegal.ai) to explore our work and discuss what your organization needs.

<!-- pli:blurb:end -->

## What runs

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two NVLink quad boards, one host |
| Host | AMD Ryzen Threadripper PRO 3945WX (12 cores, 24 threads), one NUMA node, 8 x 32 GB DDR4 RDIMM run at DDR4-2666 (MemTotal ~251 GiB) |
| Software | Ubuntu 24.04, kernel 6.8, NVIDIA driver 580.159.03, CUDA 12.8, Python 3.12, torch 2.10.0+cu128 |
| Power and clocks | 180 W per card, graphics clock capped at 1425 MHz, launcher host tuning off (`DS41_HOST_TUNING=0`) |
| Engine | `philbert440/deepseek-v4.1-v100` @ `ds41-vision-20261025b` (`23cec6a9`), wheel `1.5.2.dev1149+ds41vision1025b`; `_C` rebuilt with [patch 0003](patches/0003-mp1-exl3-tiled-smem-staging.patch) |
| Layout | PP2 x TP4: one pipeline stage per NVLink quad (20 + 20 layers); TP all-reduce inside a board over NVLink (the engine's SM70 custom all-reduce), the PP hop between boards over PCIe |
| Drafter | DSpark from the pack, k = 5 |
| Context and concurrency | `--max-model-len 327680`, at most 3 sequences; KV pool 927,004 tokens at boot ("2.83x" for 327,680) |
| Prefill | `--max-num-batched-tokens 1024`, prefix caching on, MP1 staged MoE kernel on (`VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1`) |
| Engram | resident in host RAM (`VLLM_DS41_ENGRAM_RESIDENT=1`): 4 x 45.78 GiB on the stage-0 ranks, ~208 GiB host RAM held |
| NUMA | all eight ranks on node 0 ([patch 0001](patches/0001-numa-single-node.patch)) |
| Thinking | off by default; `chat_template_kwargs: {"thinking": true}` turns it on |

Details, start requirements and rollback: [docs/production.md](docs/production.md).

## Results

All MEASURED on our host. Conditions: DDR4-2666, 1425 MHz cap, 180 W; KV 927,004; six seeds per cell; ~75K-token
prompts; fresh `cache_salt` per request (prefix hits 0 in every timing cell). Cold = host page cache dropped before the
request; warm = the same prompt again under a new salt. CIs are 95 % bootstraps of the change against the baseline.

| arm | cold 75K first token | warm 75K first token | decode tok/s (cold / warm cells) | ms per verify round | 3 x 300K wall |
|---|---:|---:|---:|---:|---:|
| baseline (Engram from NVMe) | 46.00 s (sd 6.21) | 27.02 s (sd 0.07) | 42.15 / 40.91 | 71.8 | 476.1 s |
| + resident Engram (ER1) | 26.94 s | 27.10 s | 46.41 / 44.78 | 71.7 | 368 s |
| + staged MoE prefill, Engram from NVMe (MP1) | 47.37 s (NVMe noise) | **26.39 s** (−2.33 %) | 43.55 / 47.04 | 71.3-73.4 | 498.4 s |
| **both = production** | **25.81 s** (−43.9 %) | **25.75 s** (−4.7 %) | 45.53 / 42.05 | 71.2-71.6 | **355.5 s** |

Decode tok/s follows the drafter's acceptance on the generated text, so six-seed means move by ±10 % with CIs spanning
0. The time per verify round, 1000 x (accepted tokens per draft + 1) / decode tok/s, is the stable engine-speed measure:
it spreads by 0.3 ms across boots. Production against resident Engram alone: cold −4.18 %, warm −4.97 %.

| thinking on, warm | first token | decode tok/s | ms per round | accepted per draft |
|---|---:|---:|---:|---:|
| baseline | 29.88 s | 32.55 | 72.1 | 1.35 |
| production | 26.01 s | 31.44 | 71.84 | 1.26 |

Earlier runs (the upstream default 1,048,576 x 2 context at DDR4-3200 and the 1425 MHz cap, and the Q0 baseline at
uncapped clocks) and every table are in
[docs/measurements.md](docs/measurements.md); the same numbers as JSON are in [evidence/](evidence/).

## What worked

| ID | change | result | status |
|---|---|---|---|
| [ER1](docs/experiments.md#er1-engram-tables-resident-in-host-ram) | Engram tables resident in host RAM (after a RAM upgrade) | cold 75K −41.4 % (CI −46.5..−34.8), warm unchanged, greedy 16 / 16 | **production** since 2026-11-01 |
| [MP1](docs/experiments.md#mp1-staged-exl3-moe-prefill-kernel) | shared-memory-staged EXL3 MoE prefill kernel ([0003](patches/0003-mp1-exl3-tiled-smem-staging.patch)) | kernel −7.5..−13.2 %, bit-identical; warm 75K −2.33 % (CI −3.15..−1.50) | **production** since 2026-11-01 |
| [AUD1](docs/experiments.md#aud1-in-memory-prefix-reuse) | in-memory prefix reuse (same prompt, same salt) | 74,752 of ~75.1K tokens reused; first token in 0.61-0.73 s | works as shipped |
| [327,680 x 3](docs/decisions.md) | shorter context, three sequences instead of two | same prefill speed as 1M x 2 ([ML1](docs/experiments.md#ml1-max-model-len-1048576-x-2-against-327680-x-3)); chosen for concurrency | **production** |
| [0001](patches/0001-numa-single-node.patch) | bind all ranks to the one NUMA node the host has | required to start on a one-socket host | **production** |

## What did not work

| ID | change | why it was not promoted |
|---|---|---|
| [GMU1-p](docs/experiments.md#gmu1-grow-the-kv-pool) | turn off vLLM's CUDA-graph memory estimate | KV 1,194,319 tokens, but +9-13 % per verify round |
| [GMU1-t](docs/experiments.md#gmu1-grow-the-kv-pool) | trimmed graph capture list + memory utilisation 0.945 | KV +1.0 % only; greedy 12 / 16 identical + 4 near-ties |
| [DEP1](docs/experiments.md#dep1-adaptive-draft-depth-p_min) | adaptive draft depth, `p_min` 0.3 | not byte-identical (5 of 8 prompts diverge; one at 1.15 nats); decode gain inside noise |
| [ER1-LA](docs/experiments.md#er1-la-engram-lookahead) | Engram lookahead 1,024 (non-resident) | cold first token +26.2 % (wide CI; other load on the host during the arm) |
| [PC1](docs/experiments.md#pc1-prefill-chunk-2048) | prefill chunk 1,024 → 2,048 | KV pool fell to 385,363 tokens |
| [DLANE1](docs/experiments.md#dlane1-engine-decode-lane-switch) | the engine's `VLLM_DS41_DECODE_LANE` switch | no gain: first token +0.4-0.6 % (CI includes 0), decode beside a prefill 28.9 vs 29.6 tok/s |
| [OPS1](docs/experiments.md#ops1-bounded-startup-warm-up) | bounded warm-up after each start | no first-request penalty visible above the cold spread; moot under resident Engram |
| [PIN1](docs/experiments.md#pin1-engram-io-thread-placement) | Engram IO threads on their own CPUs | moot: IO threads at 1-5 % CPU, none in the request path when resident |
| [#1335](docs/survey.md) | 1Cat's 32-slot grouped EXL3 kernel | does not apply: every prefill pass of 128+ tokens already uses the row-tiled kernel |
| [KMOE1](docs/experiments.md#kmoe1-next-steps-for-the-moe-prefill-kernel) | MoE prefill kernel: bank-conflict fix, 64-row staging, activation layout | bit-identical, but slower or flat on the tiers that carry the time (one card) |

## Open work

Results not in yet are marked **PENDING** in [docs/roadmap.md](docs/roadmap.md), each with what it will measure:

- **Where the 71.5 ms verify round goes**: profiled. At one stream the two stages run one after the other (~29 ms,
  then ~32 ms of kernels) and the bandwidth-heavy routed MoE is only ~11 ms of a 70 ms step; small kernels and launch
  gaps are about a third ([measurements](docs/measurements.md#where-a-decode-step-goes-2026-11-01-profiled)). The
  decode study is done: the round is not bandwidth-bound (HBM floor ~12 ms, ESTIMATED, against 70 ms). Three exact
  changes are written and ESTIMATED to take a round from 70 to ~65-66 ms; none is timed on the server yet.
- **MoE prefill, next step**: the next kernel variants were timed and did not win (above); the next step is removing
  the host wait after each layer's routing plan (~4 ms of GPU idle per 1,016-token prefill chunk on stage 0, MEASURED).
- **Concurrent identity**: the 16 greedy prompts re-run while two ~150K-token requests generate beside them, plus a
  300K needle. Test written, not run.
- **Prefix-cache identity** (open finding): cold against cold is byte-identical (8 / 8), but a warm in-memory hit
  against cold gave 2 identical and 3 near-ties of 5 valid pairs, and 3 more warm requests reused nothing because a
  guard in the engine's decoder replay dropped the cached prefix. Under investigation
  ([measurements](docs/measurements.md#prefix-cache-identity-warm-hit-against-cold)).
- **Expert-usage counters**: built, not installed; the input for spending expert bits by routing frequency.
- **Persistent prefix tier** that survives restarts: port design done, ESTIMATED 3.5-5 weeks; its byte-identity gate
  depends on the prefix-cache finding above.
- **1Cat's GLM changes** (done, code reading): nothing large to pull; the engine already has each optimization worth
  having and the GLM correctness bugs do not apply. Details in [docs/roadmap.md](docs/roadmap.md).

## Hardware

Eight V100-SXM2-32GB on two NVLink quad boards; Threadripper PRO 3945WX; 8 x 32 GB DDR4 RDIMM. Two things on this host
shaped the configuration, and [docs/hardware-notes.md](docs/hardware-notes.md) has the details:

- **PCIe completion-timeout resets** under load with uncapped clocks; the 1425 MHz cap was restored, and a board whose
  power connection showed a burn mark was taken out. No reset since.
- **Uncorrected DDR4 ECC errors at DDR4-3200** on one channel; at DDR4-2666 the same DIMMs pass every probe, and EDAC
  is read before and after every server start.

## Reproduce

```bash
git clone https://github.com/philbert440/deepseek-v4.1-v100 && cd deepseek-v4.1-v100
git checkout ds41-vision-20261025b
git apply /path/to/patches/0001-numa-single-node.patch          # one NUMA node
git apply /path/to/patches/0003-mp1-exl3-tiled-smem-staging.patch # csrc/: rebuild _C (patches/README.md)
# optional, inert unless its variables are set: patches/0002-gmu1-cudagraph-sizes-and-profiler-switch.patch
```

Then, in the launcher's environment file, on top of the engine's defaults:

```bash
export DS41_MAX_MODEL_LEN=327680 DS41_MAX_NUM_SEQS_OVERRIDE=3 DS41_HOST_TUNING=0
export VLLM_DS41_ENGRAM_RESIDENT=1          # needs ~241 GiB host RAM available at start (docs/production.md)
export VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1    # only with the rebuilt _C
export CUDA_HOME=/usr/local/cuda-12.8 CC=gcc-14 CXX=g++-14
```

The `_C` rebuild command, the RAM requirement and the rollback are in [patches/README.md](patches/README.md) and
[docs/production.md](docs/production.md). To compare two runs of your own the way we do, see
[tools/compare_speed.py](tools/compare_speed.py) and [docs/method.md](docs/method.md); please send results as a
performance report (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## Repository layout

| Path | What it is |
|-|-|
| `docs/` | [production](docs/production.md), [measurements](docs/measurements.md), [experiments](docs/experiments.md), [decisions](docs/decisions.md), [survey](docs/survey.md), [method](docs/method.md), [KV capacity](docs/kv-capacity.md), [hardware notes](docs/hardware-notes.md), [roadmap](docs/roadmap.md), [publication](docs/publication.md) |
| `patches/` | our three engine patches (0001 NUMA, 0002 KV-experiment switches, 0003 staged MoE prefill) and the single-GPU harness behind 0003 |
| `tools/` | `compare_speed.py` (bootstrap CI of a change), `warmup.py` / `warmup.sh` (OPS1), `proc_census.py` / `pin_io.py` (PIN1), `check_data_boundary.sh`, CPU tests |
| `evidence/` | every published number as JSON, with dates and conditions |
| `.publication/SOURCE.json` | what this tree was assembled from and what was left out |

## Tests

```bash
python3 -I -m unittest discover -s tools -p 'test_*.py' -v      # CPU only, a few seconds; no server needed
python3 -I -m pytest -p no:cacheprovider tools/test_proc_census.py   # 3 pytest-style tests (proc_census, pin_io)
bash tools/check_data_boundary.sh --tree HEAD                    # the data-boundary scan we run before publishing
```

## Related repositories

| Repository | What it holds |
|-|-|
| [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100) | the engine, launcher and SM70 kernels we run (Phil Tompkins) |
| [ProprietaryLegal/deepseek-v4.1-v100](https://github.com/ProprietaryLegal/deepseek-v4.1-v100) | our snapshot of that engine and its SM70 wheel |
| [ProprietaryLegal/1Cat-vLLM](https://github.com/ProprietaryLegal/1Cat-vLLM) | our mirror of 1CatAI's 1Cat-vLLM, the SM70 vLLM fork underneath |
| [ProprietaryLegal/v100-skinny](https://github.com/ProprietaryLegal/v100-skinny) | our mirror of dnv2003's v100-skinny: hand-written NVFP4 / FP8 weight-only kernels for Volta |
| [ProprietaryLegal/deepseek-v4-flash-v100](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100) | our earlier V100 reports (DeepSeek V4 Flash, then the V4.1 interim report and its patches) |
| [ProprietaryLegal/swift-1.5-v100](https://github.com/ProprietaryLegal/swift-1.5-v100) | another model on the same V100 host |
| [ProprietaryLegal/dsv41-offload](https://github.com/ProprietaryLegal/dsv41-offload) | DGX sPLIce's research archive, where several of our gates and ideas came from |

## Credits and licence

This build is mostly other people's work: DeepSeek's model, DSpark drafter and Engram tables; Phil Tompkins'
(philbert440) engine, launcher, SM70 kernels and franken-v100 EXL3 pack; 1CatAI's 1Cat-vLLM; the vLLM project;
turboderp's EXL3 format. Every source is listed in [CREDITS.md](CREDITS.md). If you build on this repository, please
credit them as well.

Original code is Apache-2.0 ([LICENSE](../LICENSE)). The patches modify Apache-2.0 engine sources; see [NOTICE](NOTICE).
No model weights, wheels or prompt corpora are distributed here.

## Work with PLI Labs

[PLI Labs](https://proprietarylegal.ai/labs.html) is the open research arm of Proprietary Legal Intelligence. PLI builds
AI around an organization's own work product: retrieval over its documents, staged workflows, validation of every output
and attorney review before anything goes out. This stack is how we run that privately, on hardware we own. If you want
private, on-prem LLM serving of your own, from choosing the hardware to the measured stack and the workflows on top, we
consult on exactly that: [proprietarylegal.ai](https://proprietarylegal.ai).
