# Measurements

Every number here is MEASURED on our 8x V100 host unless labelled otherwise. The protocol is in [method.md](method.md).
Prefill tok/s = prompt tokens / time to first token. Model outputs are never kept. The same numbers are in
[evidence/](../evidence/) as JSON.

Clock and memory conditions changed twice on 2026-10-31, so each section states its own, and sections with different
conditions are not directly comparable:

| section | memory | graphics clock | power |
|---|---|---|---|
| 2026-10-31 first runs | DDR4-3200 | 1425 MHz cap | 180 W |
| 2026-10-31 Q0 baseline | DDR4-3200 | uncapped (boost up to 1530 MHz) | 180 W |
| 2026-11-01 (every arm and production) | DDR4-2666 | 1425 MHz cap | 180 W |

## 2026-11-01 production (FINAL)

Boot 2026-11-01 05:19 UTC, resident Engram + staged MoE prefill, KV 927,004. Seeds 190-195. Control: the baseline
below (same boot settings, Engram from NVMe, staged kernel off).

| cell | baseline | production | change, 95 % CI |
|---|---:|---:|---|
| cold 75K first token | 46.00 s (sd 6.21) | **25.81 s** | **−43.9 %** (−48.8, −37.6) |
| warm 75K first token | 27.02 s (sd 0.07) | **25.75 s** | **−4.7 %** (−5.0, −4.3) |
| prefill tok/s, cold / warm | 1,656 / 2,774 | 2,910 / 2,916 | |
| decode tok/s, cold / warm cells | 42.15 / 40.91 | 45.53 / 42.05 | CI spans 0 (drafter acceptance) |
| ms per verify round | 71.8 | 71.2-71.6 | unchanged |
| 3 x ~300K stress wall | 476.1 s | **355.5 s** | 0 preemptions in both; peak KV 35.4 % → 50 % |

Against resident Engram alone (ER1): cold −4.18 %, warm −4.97 %.

### Decode beside a cold 75K prefill

A 3,000-token decode stream runs; 10 s later a cold ~75K-token prompt is submitted beside it.

| arm | decode before → during | longest gap between tokens | that prefill's first token |
|---|---|---|---|
| baseline | 32.2 → 18.2 tok/s | 2.10 s | 104.3 s |
| resident Engram (ER1) | → 29.5 tok/s | 1.21 s | 53.6 s |
| staged MoE prefill, Engram from NVMe (MP1) | → 17.7 tok/s | | 128.6 s |
| **production** | 37.8 → **29.6** tok/s | **0.62 s** | **50.6 s** |

### Thinking on (warm)

| arm | seeds | first token | decode tok/s | ms per round | accepted per draft |
|---|---|---:|---:|---:|---:|
| baseline | 140-145 | 29.88 s | 32.55 | 72.1 | 1.35 |
| production | 196-201 | 26.01 s (−13.0 %) | 31.44 (−3.4 %, CI −6.7..+0.3) | 71.84 | 1.26 |

The per-round time is the same; the tok/s gap is the drafter's acceptance on reasoning text.

### Stress, 3 x ~300K at once

| arm | wall | first tokens | preemptions | peak KV use |
|---|---:|---|---:|---:|
| baseline | 476 s | 194 / 339 / 469 s | 0 | 35.4 % |
| resident Engram (ER1) | 368 s | 120 / 241 / 361 s | 0 | |
| staged MoE prefill, Engram from NVMe (MP1) | 498.4 s | | 0 | 35 % |
| production | 355.5 s | | 0 | 50 % |

Peak power during the production stress run was 206.8 W on one card (1 Hz `power.draw`, above the 180 W limit; see
[hardware notes](hardware-notes.md)). The lowest host MemAvailable was 37.7 GiB.

## 2026-11-01 production, second session

KV capacity, context length, prefix cache, concurrency and llama-benchy. The same production configuration (resident
Engram + staged MoE prefill, KV 927,004; DDR4-2666, 1425 MHz cap, 180 W), restarted at 09:49 UTC. Requests only, no
other traffic, at most three requests in flight.

**Two kinds of prompt text.** The KV hold-stress and the sweep, refill, concurrency and overlap cells send a synthetic
numbered word list. The drafter predicts it almost perfectly (4.3-4.9 tokens accepted per draft), so their decode rates
(~82-87 tok/s for one stream) are a best case, **not typical decode**. llama-benchy sends ordinary book text with
thinking off (1.7-2.2 accepted per draft); its ~37-46 tok/s for one stream is in line with the gated production
decode above (42-46 tok/s). Prefill and first-token times do not depend on draft acceptance, but the runners use
different prompts: the synthetic 75K prompt prefills in 22.85 s here against 25.8 s for the gated 75K document
prompts above, so compare rows within one table.

### KV hold-stress: three full-length requests at once

- Three synthetic requests of 314,728 prompt tokens each (944,184 in all), 12,000 output tokens each, temperature 0.
  All three were running together after the last prefill. 0 preemptions, 0 HTTP errors.
- Peak KV use **71.5 %**, with ~960K tokens resident (DERIVED from each request's first-token time and decode rate).
- First tokens at 109.1, 343.5 and 658.2 s: the prefills queue one after another.
- The largest load production accepts, 3 x 327,680 = 983,040 tokens, would use ~73 % (ESTIMATED). Analysis:
  [kv-capacity.md](kv-capacity.md#the-measurement-2026-11-01).

### Context sweep (cold, 2 runs per cell, 1,024 output tokens, synthetic text)

| prompt tokens | first token | prefill tok/s | decode tok/s (synthetic, best case) |
|---:|---:|---:|---:|
| 1,024 | 0.615 s | 1,665 | 86.8 |
| 8,192 | 2.693 s | 3,042 | 81.7 |
| 32,768 | 9.847 s | 3,328 | 82.5 |
| 75,000 | 22.851 s | 3,282 | 87.5 |
| 150,000 | 47.215 s | 3,177 | 86.1 |
| 300,000 | 101.915 s | 2,944 | 85.4 |

Prefill holds about 3,300 tok/s from 32K to 75K tokens and is about 10 % lower at 300K. Decode does not slow with
context on this text.

### Prefix-cache refill at 75K (2 runs per case)

| case | first token | prefix tokens reused |
|---|---:|---:|
| cold | 22.786 s | 0 |
| warm (exact repeat) | 0.519 s | 74,496 |
| same prefix, new tail | 0.537 s | 74,496 |
| middle of the prompt changed | 22.824 s | 0 |

An exact repeat, or a new tail on the same 75K prefix, answers in about 0.5 s instead of about 23 s. A change in the
middle of the prompt invalidates the cache, as designed.

### Concurrency (synthetic text)

"Together" is the aggregate while all streams decode at once. The 32K rows with two and three streams use 4,096 output
tokens so that the streams overlap.

| cell | mean first token | decode tok/s per stream | together, tok/s |
|---|---:|---:|---:|
| 1K x 1 | 0.607 s | 86.8 | 86.8 |
| 1K x 2 | 1.199 s | 66.7 | 132.4 |
| 1K x 3 | 1.384 s | 54.6 | 166.8 |
| 32K x 1 | 9.815 s | 82.5 | 82.5 |
| 32K x 2 | 18.862 s | 72.3 | 138.4 |
| 32K x 3 | 30.052 s | 64.9 | 161.7 |

At 32K the prefills queue behind each other: the third request waits about 30 s for its first token.

### Decode beside a 75K prefill (synthetic text)

A decoding stream ran 76.8 tok/s before, 79.4 during and 89.5 after another request's 75K prefill (2 runs), and that
prefill took 22.19 s against 22.85 s alone. On document text the gated figure is 29.6 tok/s beside a prefill
([above](#decode-beside-a-cold-75k-prefill)); it was not re-measured in this session.

### llama-benchy 0.4.0 (book text, thinking off, pp 2,048, tg 128, 3 runs per cell)

| cell | first token | prefill tok/s | decode tok/s per request | aggregate tok/s | accepted per draft |
|---|---:|---:|---:|---:|---:|
| depth 0 | 0.922 s | 2,332 | 45.8 | 45.8 | 2.16 |
| depth 8,192 | 3.334 s | 3,112 | 39.6 | 39.6 | 1.81 |
| depth 32,768 | 10.594 s | 3,300 | 36.8 | 36.8 | 1.67 |
| depth 65,536 | 20.671 s | 3,277 | 38.7 | 38.7 | 1.72 |
| c1 | 0.928 s | 2,317 | 40.2 | 40.2 | 1.75 |
| c2 | 1.781 s | 1,707 | 32.1 | 45.7 | 1.69 |
| c3 | 2.584 s | 1,472 | 29.1 | 54.8 | 1.77 |

llama-benchy's aggregate for c2 / c3 covers only 128 output tokens, staggered starts included, so it understates
sustained multi-user throughput; the concurrency table above measures that, on synthetic text.

### Prefix-cache identity: warm hit against cold

Eight synthetic prompts (four of ~24K tokens, four of ~75K), greedy, at most 300 output tokens, one request in flight.

- **Cold against cold: 8 / 8 byte-identical**: one cold request at a time was deterministic.
- **Warm (in-memory prefix hit) against cold**, 5 valid pairs: 2 IDENTICAL, 3 NEAR-TIE (the top two candidates swapped
  at a close margin, 0.11-0.36 nats), 0 DIFFERS.
- The other 3 warm requests reused nothing: a guard in the engine's decoder replay dropped the cached prefix ("cached
  window not exact" in the server log), so they ran the full cold prefill and are not valid pairs.

**Open finding, under investigation.** An exact resend of a long prompt does not always hit the in-memory prefix cache
today (3 of 8 missed here), and a miss costs the full cold prefill. The root cause of the dropped hits is not
determined yet. For the near-ties, one hypothesis, not yet tested: a warm request computes the uncached tail in a
different prefill-chunk partition from a cold request, and these kernels are not batch-invariant (INFERRED). The check
is rerun once the dropped hits are understood.

## 2026-11-01 arms (DDR4-2666, 1425 MHz cap, 180 W)

Each arm is one restart of the server with one change against the baseline, six fresh seeds per speed cell. Arms that
did not pass a gate are summarised here and described in [experiments.md](experiments.md).

| arm | seeds | cold 75K | warm 75K | decode tok/s (cold / warm) | ms per round | 3 x 300K wall | verdict |
|---|---|---:|---:|---:|---:|---:|---|
| baseline (Q0b) | 100-105 | 46.00 s | 27.02 s | 42.15 / 40.91 | 71.81 (median) | 476.1 s | control |
| ER1 resident Engram | 106-111 | 26.94 s | 27.10 s | 46.41 / 44.78 | 71.7 (pooled) | 368 s | promoted |
| MP1 staged MoE prefill | 230-235 | 47.37 s | 26.39 s | 43.55 / 47.04 | 71.3-73.4 | 498.4 s | promoted |
| ER1-LA Engram lookahead 1,024 | | 58.03 s (+26.2 %, confounded) | unchanged | | | | lost |
| PC1 prefill chunk 2,048 | | | | | | | lost (KV 385,363) |
| DEP1 `p_min` 0.3 | | | | +3.2..+6.7 % (CI spans 0) | | | lost (not byte-identical) |
| GMU1-p graph estimate off | | | | −3.6 / −4.6 % | 78-81 | ran clean | not promoted (KV 1,194,319) |
| GMU1-t trimmed capture list | | | | | | | not promoted (KV 936,683; 12 / 16 identical) |
| DLANE1 decode lane | | +0.41 % (CI incl. 0) | +0.59 % (CI incl. 0) | warm +8.4 % (CI −5.9..+25.3) | | | not promoted |
| **production (ER1 + MP1)** | 190-195 | **25.81 s** | **25.75 s** | 45.53 / 42.05 | 71.2-71.6 | **355.5 s** | **production** |

The "71.7" for ER1 is the median pooled over three boots (baseline, ER1, DEP1; mean 71.81, sd 0.61). The baseline's
warm control read 26.99-27.10 s on four other boots, so MP1's 0.63 s warm cut is outside the boot-to-boot spread.

## 2026-10-31 Q0 baseline, uncapped clocks (DDR4-3200, 327,680 x 3, KV 927,004)

Cold = page cache dropped before each request; warm = the same prompt again with a new salt. Prefix hits 0,
preemptions 0 in every cell.

| cell | seeds | mean first token | range | mean prefill tok/s | mean decode tok/s |
|---|---|---:|---:|---:|---:|
| cold 75K | 5-9 | 46.04 s | 39.63-53.33 s | 1,645.6 | 41.52 |
| warm 75K | 5-9 | 27.46 s | 27.35-27.58 s | 2,733.3 | 41.39 |

A truly cold Engram cost ~18.6 s (1.68x) at 75K. Decode beside an 8K prefill (smoke, not a gate run): ~32 → ~24 tok/s,
longest gap 0.88 s. The 75K decode-beside-prefill cell and the stress run did not run: the host reset that evening
([hardware notes](hardware-notes.md)).

## 2026-10-31 first runs (DDR4-3200, 1425 MHz cap)

### Upstream default context: 1,048,576 x 2 (KV 1,055,580)

| run | prompt tokens | thinking | first token | prefill tok/s | decode tok/s |
|---|---:|---|---:|---:|---:|
| seed 0 | 74,952 | off | 39.56 s | 1,894.5 | 50.73 |
| seed 1 | 74,964 | off | 34.05 s | 2,201.4 | 37.85 |
| seed 2 | 75,040 | on | 33.71 s | 2,226.0 | 32.14 |
| smoke | short | off | | | 39.25 (256 tokens) |

### Production context: 327,680 x 3 (KV 927,004)

Same prompts as the 1M runs:

| run | prompt tokens | output tokens | thinking | first token | prefill tok/s | decode tok/s |
|---|---:|---:|---|---:|---:|---:|
| seed 0 | 74,952 | 2,048 | off | 28.05 s | 2,671.7 | 43.75 |
| seed 1 | 74,964 | 1,668 | off | 27.54 s | 2,722.4 | 42.09 |
| seed 2 | 75,040 | 2,048 | on | 27.55 s | 2,724.0 | 32.48 |

CONFOUND: these prompts had already run against the 1M server, so their Engram rows were warm in the page cache. Unseen
seeds on the same server:

| run | prompt tokens | output tokens | thinking | first token | prefill tok/s | decode tok/s |
|---|---:|---:|---|---:|---:|---:|
| seed 3 | 74,980 | 1,110 | off | 39.14 s | 1,915.9 | 43.00 |
| seed 4 | 74,942 | 2,048 | off | 32.21 s | 2,326.9 | 41.98 |

Result: cold prefill at 327K (1,916-2,327 tok/s) matches 1M (1,895-2,226 tok/s). The shorter context did not speed
prefill; the 2,672-2,724 tok/s runs were Engram-warm. Warm against cold Engram on the same server was a ~20-40 %
prefill difference, the evidence behind resident Engram. (The seed 3-4 control dropped no caches and was partly warm;
the Q0 cold cells above are the true cold number.)

During a 75K prefill with Engram from NVMe: ~1,000-1,500 NVMe reads/s, ~5 MB/s, 3 % utilisation, ~159 GB of page
cache. The tables were mostly served from the page cache even when not resident.

## Where a decode step goes (2026-11-01, profiled)

One production boot (resident Engram, rebuilt `_C`, DDR4-2666, 1425 MHz cap, 180 W) with the torch profiler on all
eight ranks. Greedy, a short synthetic prompt (39 tokens), 512 output tokens. The prompt is ordinary prose, so the
drafter is accepted rarely: 244 steps for 512 tokens, 1.10 accepted drafts per step. MEASURED unless marked.

| one stream | profiled | plain (same boot) |
|---|---:|---:|
| wall time for 512 tokens | 18.26 s | 17.09 s |
| ms per decode step | 74.8 | **70.0** |

The profiler costs ~7 % at one stream. Per step, profiled, on TP rank 0 of each stage (the other TP ranks are
similar):

| ms per step | stage 0 | stage 1 |
|---|---:|---:|
| kernel window | 74.5 | 74.3 |
| GPU busy | 29.1 | 56.7, of which 24.3 is the NCCL receive kernel waiting for stage 0, so **~32.4** of work |
| GPU idle | 45.4 | 17.6 |
| routed MoE (EXL3 grouped GEMV + gating) | 5.8 | 5.1 |
| dense GEMM (CUTLASS WMMA, fp16 s884, cuBLAS, fp32 SGEMM, GEMV) | 6.3 | 8.4 |
| norm, elementwise, copy, reduce (small torch ops) | 6.0 | 7.3 |
| attention + indexer (partial / merge, RoPE, KV insert) | 3.8 | 4.3 |
| TP4 all-reduce over NVLink (~40 per stage per step, ~57-75 µs each) | 3.7 | 3.5 |
| other (mHC Sinkhorn / pre / post, fused gate-up SwiGLU, down-combine, radix sort) | 3.7 | 4.1 |

Kernels inside each stage's forward, read from the traces: ~2,370 on stage 0 and ~2,320 on stage 1 per round, 85 %
of them shorter than 16 µs. Counting the whole step from the profiler's table gives at least ~2,530 on stage 0 and
~3,510 on stage 1 (a lower bound; the step also includes input preparation and, on stage 1, the sampler and drafter).

What the table says (DERIVED from it):

- With one stream the two stages run one after the other: ~29 ms of kernels on stage 0, then ~32 ms on stage 1, then
  the sampled tokens go back. Each board is idle while the other works. The remaining ~9-13 ms of a step are launch and
  host gaps and the pipeline hand-off.
- Memory bandwidth is not the limit. The weight-heavy routed MoE is ~11 ms of ~70 (16 %), and the HBM-byte floor of
  the whole round is ~12 ms (ESTIMATED: backbone, LM-head and drafter bytes at 830 GB/s). The decode study is in
  [roadmap.md](roadmap.md).
- Small kernels are the largest single cost: small torch ops ~13 ms plus the gaps ~9-13 ms, roughly a third of the
  step. Dense GEMMs at verify width (M = 6) ~15 ms, all-reduce ~7 ms, attention ~8 ms, mHC and the rest ~8 ms.

Two more cells from the same boot (plain, without the profiler unless stated):

- **Three streams, short prompt:** ~103 ms per step, ~59 tok/s in aggregate. Profiled, stage 0's all-reduce grows from
  3.7 to 29.2 ms per step (a window mean) and its MoE from 5.8 to 16.0 ms. The growth is ranks waiting for each other,
  not link time (MEASURED from all four stage-0 traces): ~15.7 ms per step of the mean is one 3.7 s host stall in
  which two ranks started a step late (cause not determined); ~6 ms per step is host skew at the step's first
  all-reduce, where the late rank's GPU sits idle waiting for its host; and ~4.4 ms per step is per-layer expert-load
  imbalance, which moves from rank to rank with the routing. At one stream the per-layer wait is ~1.9 ms per step,
  almost all of it expert-kernel time.
- **One stream at ~32K context, prefix cached:** 9.89 s for 129 steps, **76.7 ms per step**. The profiled windows of
  this cell include the prefill, so they are not decode-only numbers and are not tabulated here.

## Kernel level: staged EXL3 MoE prefill (2026-10-31, one card, no server)

One V100-SXM2-32GB, 1425 MHz cap, 180 W. T = 1,016 tokens, TP rank 0, random trellis words and activations, routing
from the engine's balance histograms. Before the change, `ncu` on layer 5:

| layer | local experts | tiled pass | HBM floor | decode-ALU floor | HMMA floor | over HBM floor |
|---|---:|---:|---:|---:|---:|---:|
| 5 | 94 | 7.64 ms | 1.46 ms | 1.33 ms | 1.09 ms | 5.2x |
| 12 | 96 | 7.96 ms | 1.44 ms | 1.36 ms | 1.08 ms | 5.5x |

| tile | grid | regs / thread | achieved occupancy | duration | DRAM | L1/TEX | SM |
|---|---|---:|---:|---:|---:|---:|---:|
| 16-row, K=4 | 7,920 x 128 | 128 | 24.7 % | 2.05 ms | 25.8 % | | 56.9 % |
| 32-row, K=3 | 3,312 x 128 | 168 | 18.6 % | 1.42 ms | 21.5 % | 81.2 % | 45.5 % |
| 64-row, K=3 | 1,152 x 128 | 168 | 18.5 % | 0.78 ms | 15.3 % | 86.7 % | 42.7 % |

The kernel is far from HBM-bound; its scattered 16-bit trellis-word loads saturate the L1/TEX path at low occupancy
(top stall: L1TEX long scoreboard, 43.9 % of stall cycles on the 32-row tile). The engine author measured 6.5 ms per
layer (UPSTREAM, clock condition not stated); the 1425 MHz cap alone would explain ~7 % of the difference
(ESTIMATED).

After [patch 0003](../patches/0003-mp1-exl3-tiled-smem-staging.patch), through the patched dispatcher (knob off → on,
separate processes, bit-identical every run):

| layer, rep | gate | down |
|---|---|---|
| 5, r1 | 2.255 → 2.021 ms (−10.4 %) | 2.240 → 1.943 ms (−13.2 %) |
| 5, r2 | 2.273 → 1.994 ms (−12.3 %) | 2.217 → 2.009 ms (−9.4 %) |
| 12, r1 | 2.563 → 2.320 ms (−9.5 %) | 2.498 → 2.248 ms (−10.0 %) |
| 12, r2 | 2.577 → 2.343 ms (−9.1 %) | 2.502 → 2.314 ms (−7.5 %) |

About −10 % of the tiled pass, ~0.7 ms of 7.6 ms per layer per rank: ESTIMATED ~3-4 % of prefill compute, which the
server arm then measured as −2.33 % on warm 75K first token. The author's design target (2.5-3 ms per layer) needs the
later steps; see [roadmap](roadmap.md).

## Reference, not this host

The DGX sPLIce deployment measures its own numbers on two DGX Sparks
([its measurements](https://github.com/ProprietaryLegal/DGX-sPLIce-DeepSeek-V4.1-Flash-2xDGX-Spark-2xRTX3090-drafter-x86-offload/blob/main/docs/measurements.md)).
Different hardware; not comparable and not repeated here.
