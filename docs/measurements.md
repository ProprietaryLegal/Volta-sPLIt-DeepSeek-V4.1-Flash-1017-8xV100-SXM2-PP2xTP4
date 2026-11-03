# Measurements

Every number on our host, 8x V100-SXM2-32GB at 150 W, one request at a time, DSpark 5 drafts per round. Labels:
MEASURED (observed here, with date), ESTIMATED (arithmetic on measurements), UPSTREAM CLAIM (someone else's figure).

## Two benchmarks

- **The A/B harness** ([method](method.md)) decides levers: T=0 is 3 x 1,024 greedy tokens with thinking off; T=1 is a
  seeded set of 12 prompts at temperature 1 with thinking on. The drafter accepts about 2.2 drafts per round here.
- **DGX sPLIce's benchmark** compares builds: its unmodified tools
  ([dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools): `bench2.py`, `report.py`,
  `needle.py`), temperature 1, top_p 1, thinking on at high effort, cold prompts on an idle server, 1,500 generated
  tokens. Decode tok/s = (generated tokens − 1) / (last token time − first token time). On its legal prompt the drafter
  accepts 1.2-1.6 drafts per round.

Per-request throughput is (1 + accepted drafts per round) / round time, so the same engine shows different tok/s on the
two sets.

## Decode, tok/s and ms per round (A/B harness, 2026-11-03)

| stage | T=0 tok/s | T=0 ms/round | T=1 tok/s | T=1 ms/round | label |
|---|---:|---:|---:|---:|---|
| PP2 x TP4 port, no levers | 99.2 | 31.1 | 88.0 | 31.7 | MEASURED |
| + six token-path and draft levers | ~105.8 | 29.55 | ~108.4 | 30.0 | MEASURED, ABBA averages |
| + plan fusion, keep-batch, fast expert kernels, attention fusions | ~114 | ~27.1 | ~117 | ~27.7 | MEASURED |
| + expert-kernel instruction diet | ~118 | ~26.2 | ~121 | ~26.8 | ESTIMATED (−0.871 ms ABBA) |

## DGX sPLIce's benchmark (2026-11-03, before the instruction diet)

| prompt length | first token | prompt reading | decode tok/s | round p50 | accepted per round | runs |
|---|---:|---:|---:|---:|---:|---:|
| 124 tokens | 0.4 s | – | 84.6-84.7 | 25.97-26.02 ms | 1.21 | 3 |
| 32,000 | 22.3-22.5 s | ~1,430 tok/s | 86.8-87.3 | 27.56-27.66 ms | 1.42 | 2 |
| 150,000 | 111.1-111.7 s | ~1,350 tok/s | 79.8-80.3 | 32.23-32.29 ms | 1.58 | 2 |
| 256,000 | 215.5 s | ~1,190 tok/s | 65.5 | 35.17 ms | 1.31 | 1 |
| 300,000 | 264.9 s | ~1,130 tok/s | 71.8 | 36.37 ms | 1.61 | 1 |

The two DGX Sparks of [DGX sPLIce](https://github.com/ProprietaryLegal/DGX-sPLIce-DeepSeek-V4.1-Flash-2xDGX-Spark-2xRTX3090-drafter-x86-offload),
same tools and conditions (MEASURED 2026-10-23, a different quantization of the same model): 49.7-53.1 tok/s and
37.2-37.4 ms per round at 124 tokens; 58.7-66.2 tok/s and a 14.5 s first token at 32K; 53.0-54.9 tok/s and a 68.6 s
first token at 150K. So this build decodes about 1.5x as fast per request (+31 % to +70 % across runs) and reads
prompts about 35-40 % more slowly. A head-to-head rerun of both builds on the same day is in progress.

## Decode by depth (A/B harness, T=0, 512 tokens, 2026-11-03)

Measured before the gate/up expert kernels and the attention fusions:

| prompt length | ms per round |
|---|---:|
| short | ~27.1 (T=0) / ~27.7 (T=1) on the final stack |
| 32,768 | 28.84 |
| 65,536 | 30.05 |
| 131,072 | 32.80 (114.6 tok/s) |

Round time grows with context because the sparse-attention indexer scores the whole cached context each round. On DGX
sPLIce's benchmark a round at 150K is 6.2 ms longer than at a short prompt, at 300K 10.4 ms. Profiling puts most of
that growth in one scoring kernel (2.3-3.6 ms at 150K, 4.7-7.3 ms at 300K); host reads of rows past the GPU hot ring add
0.6-1.5 ms.

Keep-batch (`PP_KEEP_BATCH`) by depth, OFF → ON: 32K 32.69 → 29.51 ms (−9.7 %), 64K 37.19 → 30.73 (−17.4 %), 128K
44.73 → 33.62 (−24.8 %; 84 → 111 tok/s).

## Long context

- **Literal 500,000-token prompt** (one run): first token after 536 s (about 930 prompt tokens per second), then 61.7
  tok/s. DGX sPLIce shows 322 s and 48.2 tok/s. The benchmark stops after 1,500 reasoning tokens, so this proves a 500K
  prompt fits and decodes; it does not show a completed answer.
- **Needles at ~450K and ~498K** (449,597-497,347 prompt tokens): 4 of 4 runs found all 6 needles, no foreign answers, no
  preemptions; about 460 s per request at 450K and 534 s at 498K, prompt reading included.
- **Prefix-cache reuse at 250K and 500K**: both passed, the two hits identical to each other and to the cold answer. 250K
  (249,674 tokens): cold 210 s, repeat 1.3-1.4 s, 249,648 tokens reused. 500K (499,636 tokens): cold 538-539 s, repeat
  2.2 s, 499,616 tokens reused.
- **Prefix-cache reuse at 36K-64K** (the 1Cat issue #1341 test design: cold, hit, then a cold and hit under another cache
  salt; the hits must match and reuse at least 95 %): 4 of 4 passed before the #1341 refill fix and 4 of 4 with it; a
  hit took 0.67-0.75 s against 24.7-44.2 s cold. With the fix the refill ran on both stages (49,152 hot rows on stage 1,
  32,768 on stage 2 for a hit at 35,584 tokens).

## Prefill skip (in testing, 2026-11-03)

`VLLM_V41_PREFILL_SKIP_ROWS=3072`, one repetition per arm, same production stack otherwise:

| prompt | first token OFF | first token ON | change | output |
|---|---:|---:|---:|---|
| 32,718 tokens | 22.634 s | 20.678 s | −8.6 % | identical (sha) |
| 150,038 tokens | 111.054 s | 88.453 s | −20.4 % | identical |
| 299,227 tokens | 263.925 s | 181.321 s | −31.3 % | identical |

Its guard run (abort and resend during a 150K prefill) completed with no early abort, and the prefix-cache test
passed (36K and 64K hits identical to cold). A second repetition was
running when this page was written.

## Capacity

| configuration | KV pool | per-request limit | full-length requests the pool holds |
|---|---:|---:|---:|
| production, 0.25 GiB KV per GPU | 2,076,870 tokens | 524,288 | 3.96 |

One request at a time today. ESTIMATED: about 215 tok/s combined at two requests (about 1.85x) once the two-request
build works; the second request fills the bubble between the two pipeline stages.

## Upstream claims (not reproduced here)

- 1Cat #1277: a warm DSpark-5 round of 24.9 ms on 4x V100 TP4 with a third of the experts offloaded; fresh text 53.5 ms
  per round, limited by cold-expert misses. Our own 4-card run of #1277 without levers (2026-11-02): 27.8 ms warm, 30.8
  ms and 97.1 tok/s on warm real text, 116.7 ms and 25.0 tok/s on fresh text over our slower host link.
- 1Cat #344: DeepSeek V4 Flash with native MXFP4 and FP8 kernels, PP2 x TP4, no drafting: 73.6-75.6 tok/s.
