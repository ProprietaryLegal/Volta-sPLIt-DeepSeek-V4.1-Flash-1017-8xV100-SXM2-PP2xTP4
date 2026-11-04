# Measurements

Every number on our host, 8x V100-SXM2-32GB at 150 W, one request at a time, DSpark 5 drafts per round. Labels:
MEASURED (observed here, with date), ESTIMATED (arithmetic on measurements), UPSTREAM CLAIM (someone else's figure).

## Two benchmarks

- **The A/B harness** ([method](method.md)) decides levers: T=0 is 3 x 1,024 greedy tokens with thinking off; T=1 is a
  seeded set of 12 prompts at temperature 1 with thinking on. The drafter accepts about 2.2 drafts per round here.
- **The long-context benchmark** measures long prompts with thinking on: our
  [dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools) (`bench2.py`, `report.py`,
  `needle.py`), unmodified, temperature 1, top_p 1, thinking on at high effort, cold prompts on an idle server, 1,500 generated
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
| + expert-kernel instruction diet | ~118 | ~26.2 | ~121 | ~26.8 | ESTIMATED then (−0.871 ms ABBA) |
| + prefill skip, larger hot ring (all 17 switches; D39, 2 arms) | 118.3-118.5 | 26.4-26.5 | 119.9-120.5 | 27.0-27.1 | MEASURED |
| **production after the PCIe-switch move (PB1103)** | **119.0** | **26.3** | **120.8** | **26.9** | MEASURED, one boot |

ms per round above includes the first token. Decode-only (harness v2): all 17 switches before the move 25.34-25.54 (T=0,
four arms) and 25.27-25.35 (T=1); after the move 25.30 (T=0) and 25.20 (T=1), 2.25 accepted drafts per round at T=1.
Per prompt after the move, T=0: 82.9 / 139.8 / 166.8 tok/s at 1.14 / 2.72 / 3.49 accepted drafts per round; T=1: 98.3-146.0
tok/s across the 12 prompts. Greedy gate PASS (8 of 8 identical, KL 0 over 1,215 positions).

## The PCIe-switch move (2026-11-03)

We moved one PCIe switch card. Before, the switch carrying two of board C's GPUs hung off an x8 link on a CPU root
complex shared with board B's GPUs. Now each of the four switches has its own root complex at Gen3 x16 (MEASURED from
the PCIe link status: four switch upstream links at x16, 8 GT/s, under four root complexes; eight GPU links at x8,
8 GT/s). Same GPUs, same NVLink boards. Decode did not change beyond noise (25.30 vs 25.34-25.54 ms per round). The
first token on long prompts came about 2 % sooner (next section); one or two runs per length, so treat that as
indicative. Host-to-device bandwidth has not been re-measured since the move.

## Long-context benchmark, thinking high (2026-11-03, before the instruction diet)

| prompt length | first token | prompt reading | decode tok/s | round p50 | accepted per round | runs |
|---|---:|---:|---:|---:|---:|---:|
| 124 tokens | 0.4 s | – | 84.6-84.7 | 25.97-26.02 ms | 1.21 | 3 |
| 32,000 | 22.3-22.5 s | ~1,430 tok/s | 86.8-87.3 | 27.56-27.66 ms | 1.42 | 2 |
| 150,000 | 111.1-111.7 s | ~1,350 tok/s | 79.8-80.3 | 32.23-32.29 ms | 1.58 | 2 |
| 256,000 | 215.5 s | ~1,190 tok/s | 65.5 | 35.17 ms | 1.31 | 1 |
| 300,000 | 264.9 s | ~1,130 tok/s | 71.8 | 36.37 ms | 1.61 | 1 |

## Decode and first token by depth, production stack (A/B harness, T=0, 512 tokens)

MEASURED 2026-11-03 after the PCIe-switch move, all 17 switches (prefill skip and 524,288-position hot ring on):

| prompt | first token | ms per round | before the move, same stack (first token) |
|---|---:|---:|---:|
| 2,061 / 2,062 tokens | 2.408 / 2.395 s | 25.73 / 25.92 | 2.402 / 2.421 s |
| 32,718 / 32,716 | 20.11 / 20.375 s | 26.96 / 26.96 | 20.681 / 20.71 / 20.648 s |
| 65,589 / 65,595 | 37.739 / 37.583 s | 27.50 / 27.56 | – |
| 150,038 / 150,045 | 86.934 / 87.001 s | 30.02 / 29.58 | 88.775 / 88.321 / 88.438 s |
| 299,227 | 177.977 s | 34.45 | 182.034 / 181.258 / 181.472 s |

"Before the move" is D39's 2K arm and the three base arms of D37 (same afternoon). Mean first-token change across the
move, ESTIMATED arithmetic: 32K 20.24 vs 20.68 s (−2.1 %), 150K 86.97 vs 88.51 s (−1.7 %), 300K 177.98 vs 181.59 s
(−2.0 %). Without the prefill skip the same lengths took 22.6-22.8, 111.1-111.9 and 263.9-265.0 s (D35).

Earlier, before the gate/up expert kernels and the attention fusions:

| prompt length | ms per round |
|---|---:|
| short | ~27.1 (T=0) / ~27.7 (T=1) on the final stack |
| 32,768 | 28.84 |
| 65,536 | 30.05 |
| 131,072 | 32.80 (114.6 tok/s) |

Round time grows with context because the sparse-attention indexer scores the whole cached context each round. On the
long-context benchmark a round at 150K is 6.2 ms longer than at a short prompt, at 300K 10.4 ms. Profiling puts most of
that growth in one scoring kernel (2.3-3.6 ms at 150K, 4.7-7.3 ms at 300K); host reads of rows past the GPU hot ring add
0.6-1.5 ms.

Keep-batch (`PP_KEEP_BATCH`) by depth, OFF → ON: 32K 32.69 → 29.51 ms (−9.7 %), 64K 37.19 → 30.73 (−17.4 %), 128K
44.73 → 33.62 (−24.8 %; 84 → 111 tok/s).

## Long context

- **Literal 500,000-token prompt** (one run): first token after 536 s (about 930 prompt tokens per second), then 61.7
  tok/s. The benchmark stops after 1,500 reasoning tokens, so this proves a 500K
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

## Prefill skip (adopted 2026-11-03)

`VLLM_V41_PREFILL_SKIP_ROWS=3072`, arms OFF ON ON2 OFF2 (D35), same production stack otherwise:

| prompt | first token OFF / OFF2 | first token ON / ON2 | change | output |
|---|---:|---:|---:|---|
| 32,718 tokens | 22.634 / 22.776 s | 20.678 / 20.743 s | −8.8 % | identical (sha), all arms |
| 150,038 tokens | 111.054 / 111.855 s | 88.453 / 88.462 s | −20.6 % | identical |
| 299,227 tokens | 263.925 / 265.040 s | 181.321 / 180.860 s | −31.5 % | identical |

Its guard run (abort and resend during a 150K prefill) returned the same text as a whole run, and the prefix-cache test
passed (36K, 64K and 150K hits identical to cold).

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
