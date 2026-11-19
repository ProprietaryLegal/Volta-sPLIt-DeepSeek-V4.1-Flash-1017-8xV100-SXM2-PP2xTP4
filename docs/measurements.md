# Measurements

Every number on our host, 8x V100-SXM2-32GB at 150 W, one request at a time, DSpark 5 drafts per round. Labels:
MEASURED (observed here, with date), ESTIMATED (arithmetic on measurements), UPSTREAM CLAIM (someone else's figure).

## The benchmarks

- **The A/B harness** ([method](method.md)) decides levers: T=0 is 3 x 1,024 greedy tokens with thinking off; T=1 is a
  seeded set of 12 prompts at temperature 1 with thinking on. The drafter accepts about 2.2 drafts per round here.
- **The long-context benchmark** measures long prompts with thinking on: our
  [dsv41-longctx-bench-tools](https://github.com/ProprietaryLegal/dsv41-longctx-bench-tools) (`bench2.py`, `report.py`,
  `needle.py`), unmodified, temperature 1, top_p 1, thinking on at high effort, cold prompts on an idle server, 1,500 generated
  tokens. Decode tok/s = (generated tokens − 1) / (last token time − first token time). On its legal prompt the drafter
  accepts 1.2-1.6 drafts per round.
- **The serving benchmark** (from 2026-11-05) measures the server as a client sees it: decode by text class, thinking
  on, long prompts, requests sent together and LegalBench ([quality.md](quality.md)); results below.

Per-request throughput is (1 + accepted drafts per round) / round time, so the same engine shows different tok/s on
different sets.

## Checkpoint benchmark (2026-11-05)

MEASURED 2026-11-05 15:15-15:46Z on the checkpoint boot (all 30 keys, one request at a time), with our serving benchmark
kit: real server-sent streams, token IDs and server counters reconciled per request; 1,342 records, 0 errors. Decode
tok/s = (completion tokens − 1) / (last streamed token − first), client side, median of the repetitions (range).
Tokens per round = 1 + accepted drafts per verify round, from the server's counters. Each class is one prompt of that
kind of text, 1,024 generated tokens, thinking off.

| class | greedy (T=0) tok/s | tokens per round | T=1 tok/s | tokens per round |
|---|---:|---:|---:|---:|
| code | **213.1** (211.8-213.3) | 4.70 | 196.8 (188.3-203.8) | 4.34 |
| structured (JSON) | **209.4** (209.3-210.3) | 4.63 | 205.4 (200.8-213.3) | 4.56 |
| legal | **115.7** (115.3-115.7) | 2.56 | 108.4 (106.7-116.9) | 2.40 |
| prose | **98.0** (97.7-98.3) | 2.17 | 87.2 (87.1-89.5) | 1.92 |
| chat | **96.2** (96.1-96.5) | 2.11 | 93.8 (93.4-96.5) | 2.05 |

Greedy repetitions were byte-identical for every class. The spread between classes is the drafter: on code and JSON it
gets 3.6-3.7 drafts per round accepted, on prose and chat 1.1-1.2. The engine's round time is the same.

Thinking on (T=1, seeded): 200.7, 151.8, 182.7 and 114.1 tok/s on four prompts (209 to 2,048 tokens), token-weighted
**132.3 tok/s**.

Long prompts (cold, public CC BY legal text with a unique first line, 2 repetitions, median; prompt reading = prompt
tokens / first-token time, which includes the first sampled token):

| prompt | first token | prompt reading | decode after it |
|---:|---:|---:|---:|
| 8,167 tokens | 6.57 s | 1,245 tok/s | 103.7 tok/s |
| 32,744 tokens | **16.42 s** | 1,994 tok/s | 88.2 tok/s |
| 130,448 tokens | **58.26 s** | 2,239 tok/s | 90.6 tok/s |

Two and three requests sent together: the checkpoint queues them (one request at a time, `max-num-seqs: 1`), so they
run one after another: 120.2 tok/s combined for two, 108.5 for three.

### Context sweep 2026-11-05

MEASURED 2026-11-05 on the checkpoint build: 135 requests, one at a time. Each prompt is a real document of its kind,
cut to exactly the stated length in the server's own chat template, then the head-to-head kit's instruction for that
kind (code = vLLM's Python source; structured = LegalBench items as JSON lines; legal = a public CC BY legal corpus, then
LegalBench prompt texts; prose = War and Peace; chat = a chat-style instruction over Les Misérables). Greedy, 1,024
tokens out, random cache salt (no prefix-cache hits). Thinking off: 2 runs per cell (largest difference 2.7 tok/s;
greedy outputs byte-identical in 45 of 45 cells). Thinking on (reasoning effort 50): 1 run per cell.

**Thinking off: first token, prompt reading, decode tok/s**

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

**Thinking on: decode tok/s**

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

**Prompt reading tok/s by kind (thinking off)**

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

**Accepted drafts per round (thinking off, mean over lengths):** code 3.72, structured 3.82, legal 1.62, prose 1.16,
chat 1.33. A round costs about 22.5-23 ms after a 1K prompt and 26.5-27 ms after 256K for every kind.

## Decode, tok/s and ms per round (A/B harness, 2026-11-03/04)

| stage | T=0 tok/s | T=0 ms/round | T=1 tok/s | T=1 ms/round | label |
|---|---:|---:|---:|---:|---|
| PP2 x TP4 port, no levers | 99.2 | 31.1 | 88.0 | 31.7 | MEASURED |
| + six token-path and draft levers | ~105.8 | 29.55 | ~108.4 | 30.0 | MEASURED, ABBA averages |
| + plan fusion, keep-batch, fast expert kernels, attention fusions | ~114 | ~27.1 | ~117 | ~27.7 | MEASURED |
| + expert-kernel instruction diet | ~118 | ~26.2 | ~121 | ~26.8 | ESTIMATED then (−0.871 ms ABBA) |
| + prefill skip, larger hot ring (all 17 switches; D39, 2 arms) | 118.3-118.5 | 26.4-26.5 | 119.9-120.5 | 27.0-27.1 | MEASURED |
| production after the PCIe-switch move (PB1103) | 119.0 | 26.3 | 120.8 | 26.9 | MEASURED, one boot |
| + tiled and fused index scorers, drafter projection sharding: 22 keys, V1 runner (D54A OFF / OFF2, 2026-11-04) | 120.5 / 120.2 | 26.0 / 26.0 | 121.8 / 122.0 | 26.7 / 26.6 | MEASURED, 2 arms |
| **+ Model Runner V2: the production set (D54A ON / ON2, 2026-11-04)** | **134.2 / 135.0** | **23.4 / 23.2** | **136.6 / 136.4** | **23.8 / 23.8** | MEASURED, 2 arms |

ms per round above includes the first token. Decode-only (harness v2): all 17 switches before the move 25.34-25.54 (T=0,
four arms) and 25.27-25.35 (T=1); after the move 25.30 (T=0) and 25.20 (T=1), 2.25 accepted drafts per round at T=1.
Per prompt after the move, T=0: 82.9 / 139.8 / 166.8 tok/s at 1.14 / 2.72 / 3.49 accepted drafts per round; T=1: 98.3-146.0
tok/s across the 12 prompts. Greedy gate PASS (8 of 8 identical, KL 0 over 1,215 positions).

D54A (2026-11-04, one window, arms OFF ON ASYNC-ON ASYNC-ON2 ON2 OFF2): decode-only ms per round V1 24.98 / 24.98 (T=0)
and 24.98 / 24.92 (T=1); Model Runner V2 22.26 / 22.22 and 22.17 / 22.19. Per prompt with MRV2, T=0: 93.0 / 159.5 /
187.4 tok/s at 1.14 / 2.74 / 3.49 accepted drafts per round; T=1: 110.8-164.3 tok/s across the 12 prompts. Output
bitwise-identical to the V1 arms (T=0 3 of 3, T=1 12 of 12, greedy 8 of 8). The ON arms booted the 22-key set plus
`VLLM_USE_V2_MODEL_RUNNER=1` with the same code that production now runs; the production boot itself has not been
benchmarked yet.

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
| 124 tokens | 0.4 s |  | 84.6-84.7 | 25.97-26.02 ms | 1.21 | 3 |
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
| 65,589 / 65,595 | 37.739 / 37.583 s | 27.50 / 27.56 |  |
| 150,038 / 150,045 | 86.934 / 87.001 s | 30.02 / 29.58 | 88.775 / 88.321 / 88.438 s |
| 299,227 | 177.977 s | 34.45 | 182.034 / 181.258 / 181.472 s |

"Before the move" is D39's 2K arm and the three base arms of D37 (same afternoon). Mean first-token change across the
move, ESTIMATED arithmetic: 32K 20.24 vs 20.68 s (−2.1 %), 150K 86.97 vs 88.51 s (−1.7 %), 300K 177.98 vs 181.59 s
(−2.0 %). Without the prefill skip the same lengths took 22.6-22.8, 111.1-111.9 and 263.9-265.0 s (D35).

**With the tiled index scorer** (`INDEX_TILED=1`, adopted 2026-11-04; depth ABBA, MEASURED):

| context | ms per round OFF | ms per round ON | change | pairs (ON − OFF) | A/A (OFF2 − OFF) | output |
|---|---:|---:|---:|---:|---:|---|
| 150,000 tokens | 29.98 | **27.88** | **−7.0 %** | −2.10 / −1.73 | +0.08 | identical, 139 rounds every arm |
| 300,000 tokens | 34.33 | **29.62** | **−13.7 %** | −4.71 / −4.57 | +0.10 | identical, 89 rounds every arm |
| short (A/B harness T=0 and T=1) |  |  | +0.032 ms average | +0.067, +0.069, −0.006, −0.001 |  | texts identical; not detectable |

The "ms per round" column of the table above was measured before it.

**With the fused prefill index scorer** (`INDEX_FUSE=ilp4`, adopted 2026-11-04; test D52R2, V1 runner, arms OFF ON ON2
OFF2, one prompt per length per arm, MEASURED):

| prompt | first token OFF / OFF2 | first token ON / ON2 | change | output |
|---|---:|---:|---:|---|
| 32,718 tokens | 19.945 / 20.166 s | 20.148 / 20.065 s | +0.3 %, noise | identical (sha), all arms |
| 150,038 tokens | 85.127 / 86.161 s | **81.323 / 81.626 s** | **−4.9 %** | identical |
| 299,227 tokens | 174.113 / 176.795 s | **158.994 / 158.416 s** | **−9.5 %** | identical |

Change = ON mean against OFF mean (ESTIMATED arithmetic). Decode not detectable (ABBA average +0.015 ms per round).
Prompt reading at 300K is now about 1,885 tok/s (299,227 / 158.7 s, ESTIMATED).

**With Model Runner V2** (D54A, the 22-key set plus MRV2, single runs; MEASURED):

| prompt | first token | ms per round | sha vs V1 | V1 runner reference (other windows) |
|---|---:|---:|---|---|
| 32,718 tokens | 19.37 s | 28.02 | identical | 20.11 / 20.375 s, 26.96 / 26.96 ms per round (PB1103, 17 switches) |
| 150,038 tokens | 82.77 s | 26.65 | identical | 81.323 / 81.626 s first token (D52R2); 27.88 ms per round (D48 ON) |

Without the prefill-skip hook (D54R, an earlier MRV2 kit) the same 150K prompt took 105.53 s to the first token, and
the 32K round was also 28.02 ms. The 32K round is about 1.1 ms slower than the V1 reference and the 150K round about
1.2 ms faster (ESTIMATED: different windows, one run each).

**Same-window depth sweep** (D55, 2026-11-04, report-only; the production set with the V1 runner (OFF arms) and with
MRV2 (ON arms), arms OFF ON ON2 OFF2, each its own boot, one prompt per length, 512 decode tokens; ms per round,
MEASURED):

| prompt length | V1 runner, OFF / OFF2 | MRV2, ON / ON2 | MRV2 − V1 | tokens per round (both) |
|---|---:|---:|---:|---:|
| 2,048 | 25.41 / 25.67 | 22.82 / 22.80 | −2.59 / −2.87 | 3.97 |
| 8,192 | 25.77 / 25.82 | 22.99 / 22.97 | −2.78 / −2.85 | 3.56-3.58 |
| 16,384 | 25.93 / 26.01 | 23.26 / 23.34 | −2.67 / −2.67 | 4.41 |
| 32,768 | 26.33 / 26.35 | **27.74 / 27.79** | **+1.41 / +1.44** | 4.10 |
| 65,536 | 26.28 / 26.69 | 23.58 / 23.75 | −2.70 / −2.94 | 4.57 |

MRV2 is 2.6-2.9 ms per round faster at every length except the 32K prompt, where it is about 1.4 ms slower, in both MRV2
arms. Tokens per round are the same on both runners, so the output path matches and only the round time differs. The
cause is not known yet (INCONCLUSIVE); the block-table gather and padding are the first suspects and need a device trace.

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

One request at a time today. ESTIMATED before any test: about 1.85x combined at two requests, because the second
request fills the bubble between the two pipeline stages. The V1 two-request build was withdrawn; its successor on
Model Runner V2 (`single`, `conc2`, `conc3`) is built and waits for its window. Nothing about concurrency on this build
is measured yet.

## Upstream claims (not reproduced here)

- 1Cat #1277: a warm DSpark-5 round of 24.9 ms on 4x V100 TP4 with a third of the experts offloaded; fresh text 53.5 ms
  per round, limited by cold-expert misses. Our own 4-card run of #1277 without levers (2026-11-02): 27.8 ms warm, 30.8
  ms and 97.1 tok/s on warm real text, 116.7 ms and 25.0 tok/s on fresh text over our slower host link.
- 1Cat #344: DeepSeek V4 Flash with native MXFP4 and FP8 kernels, PP2 x TP4, no drafting: 73.6-75.6 tok/s.

## Moved from the README (2026-11-19)

These sections stood on the front page until the README was rewritten on 2026-11-19. They are kept here as they were,
with three changes: empty table cells no longer hold a dash, links point from this folder, and the rows and sentences
that compared this build with our previous build were taken out (the previous build is described on its own in
[previous-build/](../previous-build/)). Figures and labels are unchanged.

#### The progression, in tok/s

| build (8x V100-SXM2-32GB, same host) | date | decode, thinking off | thinking on | label |
|---|---|---:|---:|---|
| **Volta sPLIt**: PP2 x TP4 port of 1Cat #1277, no speed levers | 2026-11-03 | 99.2 | 88.0 | MEASURED |
| + six token-path and draft levers | 2026-11-03 | ~105.8 | ~108.4 | MEASURED (ABBA) |
| + fused quantize plan, keep-batch, fast expert kernels, attention fusions, instruction diet | 2026-11-03 | ~118 | ~121 | MEASURED / ESTIMATED |
| + prefill skip, larger GPU hot ring, PCIe-switch move (17 switches) | 2026-11-03 | 119.0 | 120.8 | MEASURED, one boot |
| + tiled and fused index scorers, drafter projection sharding (V1 runner) | 2026-11-04 | 120.2-120.5 | 121.8-122.0 | MEASURED, 2 arms |
| + Model Runner V2 | 2026-11-04 | 134.2-135.0 | 136.4-136.6 | MEASURED, 2 arms |
| **+ all-reduce push, NCCL host hand-off, SM70 prefill expert GEMM: the 2026-11-05 checkpoint (30 keys)** | 2026-11-05 | **~135.2** | **~137.6** | ESTIMATED: the row above with the all-reduce push's −0.180 ms per round; the other two change prompt reading only |

<sub>This table uses one fixed set throughout (A/B harness: 3 x 1,024 greedy tokens; a seeded T=1 thinking-on set of 12
prompts) so the rows compare. The by-kind tables use other prompts.</sub>

**First token, same prompts across serving sets** (A/B harness depth prompts and the head-to-head kit's 128K prompt, cold,
MEASURED):

| prompt | 2026-11-03 port | + prefill skip | + fused index scorer, MRV2 | **2026-11-05 checkpoint** |
|---|---:|---:|---:|---:|
| 32K | 22.6 s | 20.1 s | 19.4 s | **16.4 s** |
| 128K |  |  | 69.0-71.5 s (before the NCCL hand-off) | **58.3 s** |
| 150K | 111.1 s | 87.0 s | 81.3-82.8 s |  |
| 300K | 263.9 s | 178.0 s | 158.4-159.0 s |  |

<sub>32K and 128K on the checkpoint: head-to-head kit, 32,744 and 130,448 tokens, 2 runs, median. The other cells are the
A/B harness depth runs of their dates (32,718 / 150,038 / 299,227 tokens). The context sweep above gives the checkpoint
at 256K.</sub>

#### Time per round: the engineering metric behind the tok/s

| stage | T=0 ms/round | T=1 ms/round | label |
|---|---:|---:|---|
| PP2 x TP4 port, no levers (2026-11-03) | 31.1 | 31.7 | MEASURED |
| all 17 switches, after the PCIe-switch move (2026-11-03) | 26.3 | 26.9 | MEASURED; decode-only 25.30 / 25.20 |
| + index scorers, drafter sharding, V1 runner (2026-11-04) | 26.0 | 26.6-26.7 | MEASURED, 2 arms; decode-only 24.98 / 24.92-24.98 |
| + Model Runner V2 (2026-11-04) | 23.2-23.4 | 23.8 | MEASURED, 2 arms; decode-only 22.22-22.26 / 22.17-22.19 |
| **+ all-reduce push: checkpoint (2026-11-05)** | **~23.1** | **~23.6** | ESTIMATED: −0.180 ms (ABBAABBA, 95 % −0.278..−0.081); decode-only ~22.05 |

A round is one target verification step: the target checks the drafted tokens and emits one token plus every accepted
draft. Per-request throughput is (1 + accepted drafts per round) / round time. Every change on this page was decided on
round time, measured decode-only in paired ABBA arms ([method](method.md)).

### What this is

**A 249 GB model on GPUs from 2018, every expert resident.** DeepSeek-V4.1-Flash-1017 is a 551.9B-parameter mixture of
experts with DeepSeek's Engram n-gram memory. Its weights here are 248.8 GB (138.24 GB of IQ2_XXS experts and backbone,
110.60 GB of IQ4_NL Engram tables). The experts and backbone live in the 256 GiB of HBM2 on eight V100-SXM2-32GB cards:
sm_70 silicon with no FP8 or BF16 tensor cores and no `cp.async`. No expert is paged from host memory during decode. The
Engram tables stay in host RAM and each round gathers only the rows it needs: about 0.12 ms per decode round, measured
over 52 profiled rounds ([docs/levers.md](levers.md#did-not-work), "hot Engram in HBM"). Correction 2026-11-06:
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
[docs/levers.md](levers.md#after-the-checkpoint-adopted-2026-11-11). The speed tables on this page are the
checkpoint's and were not re-measured.

**Exact outputs.** The target verifies every draft with the speculative-sampling acceptance rule, so the text keeps the
target model's distribution whatever the drafter proposes. The speed changes do not change what the model computes
(bitwise-identical, or within the near-tie gate). One difference under Model Runner V2: a sampled (T>0) request that
asks for logprobs uses MRV2's rejection sampler instead of our keyed draw streams. Its text still follows the target
distribution, but it is not the same sample the V1 runner would have drawn. Requests without logprobs keep the keyed
streams.

**One request at a time.** The checkpoint took one request at a time. Since 2026-11-11 our host keeps three chats'
caches (three slots) and still runs one request at a time; more combined throughput is not established. The previous
build on these cards, described in [previous-build/](../previous-build/), read short and medium prompts at about 2,900 to
3,300 tok/s by its own method and served three requests at once.

**Everything is published:** the measurements, the 49-patch engine series, our production patches, the serving profile
and environment, the A/B harness, and the log of the test queue.


### What runs

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two 4-GPU SXM2 boards, NVLink inside each board; four PLX switches, each on its own CPU root complex at PCIe Gen3 x16, Gen3 x8 per GPU |
| Host | AMD Threadripper PRO 3945WX (12 cores), one NUMA node, 251 GB RAM |
| Power and clocks | 150 W per card, graphics clock capped at 1522 MHz |
| Model | DeepSeek-V4.1-Flash-1017: [ISTA-DASLab GSQ-RCO GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF) @ `ad1e8991` (IQ2_XXS experts, 138.24 GB; IQ4_NL Engram, 110.60 GB); config, tokenizer and DSpark drafter (FP8, 7.93 GB) from [deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017) @ `1bae0e10` |
| Engine | 1Cat-vLLM #1277 (merge `899e9ed33`) + 1Cat main `6db9c81` and 25 open 1Cat PRs + our PP2 port and lever stack: the [49-patch series](../forks/1cat-4xv100-tp4/) and our production patches in [engine/production/](../engine/production/); the `v41k`, `v41idx`, `v41pidx` and `v41prefmoe` SM70 CUDA libraries built from that source |
| Layout | PP2 x TP4. Stage 1 (board B): layers 0-19, Engram lookup and hash state (Engram tables in host RAM). Stage 2 (board C): layers 20-39, the head, the drafter. TP all-reduce over NVLink; the stage hand-off over host shared memory (`NCCL_P2P_LEVEL=NVL`) |
| Engine settings | vLLM Model Runner V2, synchronous scheduling, FULL CUDA graphs for 1-6 tokens per step, chunked prefill 8,192, prefix caching, every expert resident |
| Drafter | DSpark, 5 drafts per round, coupled (keyed) sampled drafts at T>0 |
| Context | 524,288 tokens per request, one request at a time (`max-num-seqs 1`; three chat slots on our host since 2026-11-11), KV pool 2,076,870 tokens (packed KV: a 524,288-position GPU hot ring + host arena) |
| Thinking | on by default; `chat_template_kwargs: {"thinking": false}` turns it off |
| Switch set | 32 keys (the checkpoint's 30 and two adopted 2026-11-11): [engine/configs/rec.env](../engine/configs/rec.env) |

Serving profile, environment and the production switch set: [engine/](../engine/) and [docs/production.md](production.md).

### What worked

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
| Hot-ring refill after a prefix-cache hit (`HOT_REFILL`) | our port of 1Cat issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341) | correctness fix |  |
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
between the stages, not a kernel. Detail: [docs/levers.md](levers.md#adopted).

### What did not work

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
| Expert "wave" down kernel | +0.216 ms per round slower |  |
| Fused layer transition (three variants) | slower or neutral | the mixing step dominates |
| Probabilistic sharded drafts, draft temperatures | no variant faster beyond noise | the extra drafter work eats the acceptance gain |
| Bitwise FP8 drafter mat-vec | slower than the sharding alone | off |
| Asynchronous scheduling on Model Runner V2 | −0.085..−0.117 ms against synchronous MRV2 | about 0.4 %; off for now |
| CPU pinning, spin-wait broadcast, 200 W, deeper prefetch, L2 warm-up, Engram GPU cache, IQ1_M repack | neutral, slower or no-go | details in [docs/levers.md](levers.md#did-not-work) |

Full table with numbers: [docs/levers.md](levers.md#did-not-work).

### Next

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

Queue order and status: [docs/roadmap.md](roadmap.md).

### Our upstream contributions

Work we sent upstream, with authorship checked on GitHub. Third-party credits are at the end.

| PR | author | state | what it does | what it means for this build |
|---|---|---|---|---|
| [1Cat-vLLM #651](https://github.com/1CatAI/1Cat-vLLM/pull/651) | ProprietaryLegal | **merged** 2026-09-26 | SM70: accept the DFlash embedding replica across split `load_weights` calls | an SM70 drafter-loading fix in the engine this build runs on |
| [1Cat-vLLM #1031](https://github.com/1CatAI/1Cat-vLLM/pull/1031) | PLI Labs (founder) | open (2026-10-07) | DeepSeek-V4.1-Flash on V100: PP3 x TP4 (12 GPUs, 256K) and PP2 x TP4 (8 GPUs) | the multi-board pipeline layout this build's PP2 x TP4 port follows |
| [1Cat-vLLM #1030](https://github.com/1CatAI/1Cat-vLLM/pull/1030) | PLI Labs (founder) | open (2026-10-07) | SM70: generalise the MXFP4 MoE geometry; skinny split-K 4/6/9/12/18 | native-FP4 expert route; not served here (this build serves GGUF) |
| [1Cat-vLLM #1021](https://github.com/1CatAI/1Cat-vLLM/pull/1021) | PLI Labs (founder) | open (2026-10-07) | SM70: keep 32x32 UE8M0 block-FP8 dense weights in FP8 on Volta | native-FP8 dense route; not served here |

Details and two earlier closed PRs: [docs/upstream-contributions.md](upstream-contributions.md).

### Hardware

Eight V100-SXM2-32GB on two NVLink quad boards; Threadripper PRO 3945WX; 251 GB RAM, one NUMA node. Each of the four PCIe
switches has its own CPU root complex at Gen3 x16, and each GPU links to its switch at Gen3 x8. Volta has FP16
`mma.sync.m8n8k4` only: no `cp.async`, no `ldmatrix`, no FP8 tensor-core math, and a read ceiling of about 879 GB/s
(measured by [v100-skinny](https://github.com/dnv2003/v100-skinny)). Our fast expert kernels reach about 290-415 GB/s:
they are limited by instruction issue and latency, which is why the instruction diet won.
