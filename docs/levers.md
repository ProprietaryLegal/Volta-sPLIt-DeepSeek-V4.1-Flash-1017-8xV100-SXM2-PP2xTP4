# Levers

Every speed change we tried on this build, with its source and its measured result. A lever is a `VLLM_V41_*` switch
that defaults off; with the switch off, the code path is unchanged (proved by a CPU test and an AST comparison). Numbers
are ms per verify round, ABBA averages on the A/B harness ([method](method.md)), 2026-11-03 or 2026-11-04, unless
labelled. Negative is faster.

Baseline, the PP2 x TP4 port with no levers: T=0 31.1 ms per round (99.2 tok/s); T=1 31.7 ms (88.0 tok/s, 1.78
accepted drafts per round).

## Adopted

### Token path and drafts

- **`INDEX_REDUCE=1`, ours.** The sparse-attention indexer's top-k reduce runs through the custom all-reduce's IPC bank
  instead of NCCL. About −0.85 ms per round. It also made T=1 output byte-identical across restarts; with NCCL the
  result varied by boot.
- **`DMV_X=1`, ours** (a Volta dense mat-vec `dmv13_x` with double-buffered loads, built on #1277's `dmv13`). −0.42 ms,
  6 of 6 pairs faster, bitwise-equal kernel. The isolated micro-benchmark predicted 0.03-0.07 ms.
- **`COUPLED_DRAFTS=1`, `COUPLED_DRAFT_TEMP=1.0`.** Source: TensorFold's coupled sampled drafts
  ([Elevatormusic/TensorFold#25](https://github.com/Elevatormusic/TensorFold/pull/25), merged; the idea also appears in
  [0rand/deepseek-v41-tensorfold-spark](https://github.com/0rand/deepseek-v41-tensorfold-spark)). The code reached this
  build through our Sparks research lane. The drafter and the verifier share keyed Gumbel draws, so drafts agree with the target far more often at T>0.
  T=1 acceptance 1.85 → 2.25 per round, +14 % tok/s, about 0.3 ms of overhead, no T=0 cost. Exact.
- **`MARKOV_SHARD=1`** (ours), **`COUPLED_SHARD=1`, `COUPLED_LOCAL=1`** (code from our Sparks research lane): the draft head and the
  coupled sampler work on vocabulary shards, inside a captured graph. −0.2 ms at T=0; −0.23 ms and −0.12..−0.24 ms at
  T=1 (11 of 11 prompts).
- The six levers above together: T=0 29.55 ms (~105.8 tok/s, +6.7 %); T=1 30.0 ms (~108.4 tok/s, +23 %).

### Kernels and host path

- **`PLAN_FUSE=1`** (code from our Sparks research lane): the expert routing plan is built inside the q8 quantize launch. T=0 −0.37/−0.36
  (3/3, 3/3 pairs), T=1 −0.12/−0.42; texts and greedy output identical (bitwise). The micro-benchmark saw no gain.
- **`PP_KEEP_BATCH=1`**, a V1-runner port of 1Cat [#1263](https://github.com/1CatAI/1Cat-vLLM/pull/1263): the request
  stays in the persistent batch and the scheduler record across PP2's empty steps, so the token history is not resent
  and rebuilt every round. 32K 32.69 → 29.51 ms (−9.7 %), 64K 37.19 → 30.73 (−17.4 %), 128K 44.73 → 33.62 (−24.8 %;
  84 → 111 tok/s); short T=0 −0.17, T=1 −0.30; first-token time unchanged; texts identical.
- **`EXPERT_FAST=1`, ours**: fast routed-expert kernels. Down projection −0.68/−0.84 (T=0), −0.62/−0.63 (T=1); then
  gate/up a further −0.82/−0.53 (T=0), −0.64/−0.58 (T=1). Bitwise against the reference kernel, sanitizers clean. At
  6 tokens per step the IQ1_M down kernel went 90.5 → 59.5 µs (196 → 298 GB/s).
- **`FUSE_ATTN_PREP=1`, `FUSE_ATTN_POST=1`, ours**: the decode attention prologue and epilogue as one launch each.
  Average −0.19 ms (T=0 −0.18/−0.20, T=1 −0.12/−0.29), bitwise.
- After these: T=0 ~27.1 ms (~114 tok/s), T=1 ~27.7 ms (~117 tok/s), MEASURED.
- **`HOT_REFILL=1`** (on by default), from 1Cat issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341): on a
  same-session prefix hit, the packed-KV hot ring is refilled from the host copy. A correctness fix; it fired on all 8
  workers in its probe. Our repeat-prompt tests (36K-64K, and 250K and 500K) passed before and after it.
- **`EXPERT_DIET=3`, ours**: an instruction diet for the expert kernels, which profiling showed were issue-bound
  (decode about 7 instructions per weight byte, 0.46 issued per cycle). ABBA average **−0.871 ms** (T=0 −0.74/−1.02,
  T=1 −0.79/−0.93). T1 texts 11 of 11 the same; greedy 7 of 8 plus one known near-tie; compute-sanitizer memcheck,
  racecheck and synccheck 0 errors.
- **`ROUTE_FAST=1`, `ROUTE_WARPS=4`** (router floor, code from our Sparks research lane): average −0.165 ms (T=0 −0.18/−0.60, T=1
  +0.28/−0.15). That is inside the session's measured drift, so it is **not** a significant win. Greedy output bitwise,
  no errors. Kept on under our rule for upstream-backed changes that are correct and inconclusive.

### Long context (adopted 2026-11-03)

- **`PREFILL_SKIP_ROWS=3072`, ours** ([engine/production/0051-prefill-skip.patch](../engine/production/0051-prefill-skip.patch);
  design reference: philbert440/deepseek-v4.1-v100's replay rows): early prefill chunks skip the stage-2 layers that
  hold only 128-wide window rings, for rows those rings can never reach. Test D35, arms OFF ON ON2 OFF2, one prompt per
  length each, MEASURED 2026-11-03:

  | prompt | first token OFF / OFF2 | first token ON / ON2 | change | output |
  |---|---:|---:|---:|---|
  | 32,718 tokens | 22.634 / 22.776 s | 20.678 / 20.743 s | −8.8 % | identical (sha), all four arms |
  | 150,038 tokens | 111.054 / 111.855 s | 88.453 / 88.462 s | −20.6 % | identical |
  | 299,227 tokens | 263.925 / 265.040 s | 181.321 / 180.860 s | −31.5 % | identical |

  Its guard run (abort during a 150K prefill, then resend) returned the same text as a whole run, and the prefix-cache
  test passed (36K, 64K and 150K hits identical to cold). Decode is untouched: the skip acts only in prefill.
- **`KV_HOT_POSITIONS=524288`**, our setting of #1277's packed-KV hot ring (default 32,768 positions): more KV rows stay
  on the GPU. Depth ABBA (test D31, one prompt per length per arm): 300K 36.92 / 37.12 → 35.99 / 35.88 ms per round
  (−1.09), 150K 31.91 / 32.10 → 31.70 / 31.81 (−0.25), identical output. Adoption boot (D38): KV pool still 2,076,870
  tokens, prefix-cache test 3 of 3 PASS, no tracebacks.
- **`INDEX_TILED=1`, ours** ([engine/production/0052-index-tiled.patch](../engine/production/0052-index-tiled.patch),
  adopted 2026-11-04, test D48): the decode indexer's scoring kernel replaced by a register-tiled persistent kernel in
  a separate library, `v41idx.so` (`VLLM_V41_INDEX_TILED_LIB`; `v41k.so` is untouched). It walks only the live 64-key
  blocks and stages the query once per block, where the old kernel launched a block per 32 keys of capacity. Bitwise by
  construction (the same fp32 multiply-add chain per dot product and the same epilogue). Checks before the A/B: GPU
  matrix 51,090 cases, 0 mismatches; compute-sanitizer memcheck and racecheck 0 errors. MEASURED, depth ABBA (OFF ON
  ON2 OFF2, T=0, 512 tokens):

  | context | OFF | ON | change | pairs | A/A |
  |---|---:|---:|---:|---:|---:|
  | 150,000 tokens | 29.98 ms | 27.88 ms | −7.0 % | −2.10 / −1.73 | +0.08 |
  | 300,000 tokens | 34.33 ms | 29.62 ms | −13.7 % | −4.71 / −4.57 | +0.10 |

  Texts identical in every arm (139 and 89 rounds in each). Short context: ABBA means +0.067, +0.069, −0.006, −0.001 ms
  per round (average +0.032): not detectable, so the short-context headline is unchanged. Adopted on the depth win.
- **`INDEX_FUSE=ilp4`, ours** ([engine/production/0053-index-fuse.patch](../engine/production/0053-index-fuse.patch),
  adopted 2026-11-04, test D52R2): the prefill indexer scored each all-reduce tile as `torch.mm`, `relu_`, `mul_` and
  `sum(1)`, writing an fp16 score tile once and reading it three times. Our kernel (`v41pidx.so`,
  `VLLM_V41_INDEX_FUSE_LIB`) computes the per-rank head sums of a block of tiles in one launch with `mma.m8n8k4`
  scores kept in registers; every tile then goes through the same all-reduce, and one top-k launch covers the block.
  Ideas: 1Cat [#1280](https://github.com/1CatAI/1Cat-vLLM/pull/1280) (Peuqui) and
  [#1282](https://github.com/1CatAI/1Cat-vLLM/pull/1282), and philbert440's fused SM70 indexer; none of them reaches
  V4.1's path, so this is new code. The knob value names the FP32 order of the 8-head sum. The GPU check found no order
  that is bitwise-identical to today's `torch.mm` + `sum` path (`ilp4`: 1 mismatch; the others 1,984-2,528), so the
  test ran `ilp4` under the near-tie gate (first attempt D52R: correct, not bitwise). MEASURED, depth A/B (OFF ON ON2
  OFF2, one prompt per length per arm, V1 runner):

  | prompt | first token OFF / OFF2 | first token ON / ON2 | change | output |
  |---|---:|---:|---:|---|
  | 32,718 tokens | 19.945 / 20.166 s | 20.148 / 20.065 s | +0.3 %, noise | identical (sha) |
  | 150,038 tokens | 85.127 / 86.161 s | 81.323 / 81.626 s | −4.9 % | identical |
  | 299,227 tokens | 174.113 / 176.795 s | 158.994 / 158.416 s | −9.5 % | identical |

  Decode ABBA: +0.013, +0.011, +0.033, +0.003 ms per round (average +0.015), not detectable; T=1 texts 11 of 11 the
  same; greedy gate 8 of 8 identical. Activation lines on all 8 workers in the ON arms, none in the OFF arms. Adopted
  on the prefill win.

### Drafter and model runner (adopted 2026-11-04)

- **`DRAFT_MP_SHARD=1`, ours** ([engine/production/0054-draft-mp-shard.patch](../engine/production/0054-draft-mp-shard.patch),
  test D53R2, adoption D53A2): the drafter's `main_proj` was a replicated linear layer, so every rank of the drafter's
  board read the full 5,120 x 15,360 FP8 weight (78.6 MB) every round. Now each rank computes its quarter of the output
  columns with the same split-K as the full call and the results are all-gathered. An output element depends only on
  its input row, its weight row and the split, so the result is bitwise the replicated one. Prefill (more than 8 rows)
  keeps the replicated call. MEASURED, ABBAABBA, decode-only ms per round, 8 pairs: −0.081, −0.176, −0.108, −0.091,
  −0.128, −0.261, −0.068, −0.128 (average **−0.130**; 8 of 8 faster, one-sided sign test p = 0.5^8 ≈ 0.004). Every arm
  bitwise-identical (T=0 3 of 3, T=1 12 of 12, greedy 8 of 8; A/A identical). The queue's automatic rule called it
  "not detectable" (its win bar wants a larger effect) and rolled it back. **We adopted it by hand**: it is
  bitwise-identical, so it carries no quality risk, every pair was faster, and the isolated drafter step agreed (841.7
  → 640.7 µs, MEASURED in the kit's GPU check). The adoption boot logged the sharded path on all 4 drafter workers
  after one warm-up request. The same patch carries a second switch, `DRAFT_GEMV2` (a bitwise FP8 mat-vec); it stays
  off (see Did not work).
- **Model Runner V2, `VLLM_USE_V2_MODEL_RUNNER=1`** ([engine/production/0055-mrv2.patch](../engine/production/0055-mrv2.patch),
  tests D54, D54R and D54A; production since 2026-11-04 16:38Z). vLLM's newer model runner, as carried in 1Cat-vLLM,
  with 1Cat [#1221](https://github.com/1CatAI/1Cat-vLLM/pull/1221)'s DSpark path. Our port adds a DeepSeek-V4.1 model
  state, the DSpark speculator for V4.1, the pipeline commit hooks, a fix for dummy and capture batches (they must
  carry positions 0..n-1 for V4.1's Engram hash, which crashed the first port's boot) and the prefill-skip hook (without
  it the 150K first token was 105.5 s instead of about 83 s). Scheduling stays synchronous. MEASURED:

  | test | kit | decode-only ms per round, ON − OFF (ABBA means) | output |
  |---|---|---|---|
  | D54R, 19 keys (17 + the tiled scorer) | capture fix, no skip hook | −2.849, −2.823, −2.884, −2.839 (average −2.849) | bitwise, all arms |
  | D54A, the 22-key production set | capture fix + skip hook (production) | −2.735, −2.809, −2.756, −2.736 (average **−2.759**; 95 % interval −2.898..−2.620) | bitwise, all arms; A/A identical |

  D54A tok/s, same window: V1 arms T=0 120.5 / 120.2, T=1 121.8 / 122.0; MRV2 arms T=0 **134.2 / 135.0**, T=1
  **136.6 / 136.4**. The first D54 run passed every text check but its gate failed on a rounding artifact in the
  checker (top-20 probability mass summing to 1.0000001); the checker was fixed and the saved run passed when re-judged.
  Depth (D54A, single runs, compared with V1 runs from other windows, so ESTIMATED): 150K first token 82.77 s, 26.65 ms
  per round; 32K first token 19.37 s, **28.02 ms per round against 26.96 on the V1 runner**. The same-window depth sweep
  D55 (MEASURED, production set, V1 against MRV2, one prompt per length, two arms each) confirmed both: MRV2 − V1 was
  −2.59 / −2.87 ms per round at 2K, −2.78 / −2.85 at 8K, −2.67 / −2.67 at 16K, **+1.41 / +1.44 at 32K** and
  −2.70 / −2.94 at 64K. Only the 32K prompt is slower; its cause is open. Adopted on the decode win and the 150K result,
  which match the long prompts this build is for. One behaviour differs: a T>0 request that asks for logprobs uses MRV2's rejection sampler
  instead of our keyed draws, so its text follows the same distribution but is not the same sample as on V1. Every MRV2
  boot logs it.
- With all 17 switches, two arms before the PCIe-switch move (D39): T=0 118.3 / 118.5 tok/s, T=1 119.9 / 120.5 tok/s;
  decode-only 25.45 / 25.34 and 25.35 / 25.27 ms per round. After the move, one production boot (2026-11-03): **T=0
  119.0 tok/s, T=1 120.8 tok/s**, decode-only 25.30 / 25.20 ms per round, greedy gate PASS. MEASURED.
- With the 22-key set on the V1 runner (D54A OFF arms, 2026-11-04): T=0 120.5 / 120.2 tok/s, T=1 121.8 / 122.0;
  decode-only 24.98 / 24.98 and 24.98 / 24.92 ms per round. With Model Runner V2 on top, today's production set (D54A ON
  arms): **T=0 134.2 / 135.0 tok/s, T=1 136.6 / 136.4**, decode-only 22.26 / 22.22 and 22.17 / 22.19 ms per round.
  MEASURED. A full benchmark of the production boot follows the test queue.
- **Harness v2** (D39): greedy references re-recorded on the deterministic stack (three identical runs), a decode-only
  round metric, and a measured A/A spread under 0.1 ms per round (T=0 −0.096, T=1 −0.077 ms per round decode-only).

## Did not work

| change | result | why |
|---|---|---|
| Expert top-p pruning (0rand TensorFold `TF_DSV41_EXPERT_TOPP`, 0.85) | 78 tok/s, greedy FAIL | the divergence is inherent: it drops experts the target would use |
| Async scheduling under PP2 + speculative decoding | 90.5 tok/s, 34.1 ms on the first try; later runs crashed at request end (invalid sampled token ids) | the request-end guard below fixes the crash |
| V1 async with a request-end guard (D41) | ABBA decode-only, 2 pairs each at T=0 and T=1: +1.586, +1.940, +1.565, +1.622 ms per round, average **+1.678** (95 % interval +1.539..+1.817); depth +1.62 ms at 2K, +1.18 at 32K; texts identical; 20-request soak with aborts: 0 crashes | rejected: detectably slower. The re-port of 1Cat's newer model runner (MRV2) is the next attempt |
| TP8: one 8-way tensor-parallel group across both boards (D36 probe) | no-go: best modeled round 24.65 ms against the 22.0 ms bar | the 8-way all-reduce across the boards measured 30.8 µs against 5.28 µs for 4-way inside one board |
| Indexer overlap in prefill (D37 a) | first token −0.1 / +0.3 / −0.1 % at 32K / 150K / 300K, bitwise | neutral |
| 16,384-token prefill chunks (D37 b) | first token +17.5 % at 32K, +5.6 % at 150K, −1.2 % at 300K; near-tie gate FAIL at 32K and 150K | slower and changes numerics |
| Prefill chunk 4,096, re-gated on the v2 reference (D43) | near-tie gate FAIL: 6 of 8 identical; the 7K and 22K prompts moved a confident token (top-2 gaps 0.31 and 0.78 nats, bar 0.1) | the chunk size changes long-prompt numerics |
| Suggested dense-kernel tiling config, re-run (D43R) | near-tie gate FAIL: 2 of 8 identical, 1 near-tie, 5 fail (gaps up to 1.56 nats) | matches the earlier 2 of 8; closed |
| CPU pinning to physical cores (D43R) | ABBAABBA decode-only, 8 pairs: average +0.079 ms per round (95 % interval −0.020..+0.177); texts identical | not adopted: rules out a gain of ~0.05 ms or more |
| Side stream for the hyper-connection mixing step (`MIX_STREAM`, D33C) | numerics passed; GPU micro-benchmark below the win bar at 1 and 6 tokens per step, smaller stand-ins lost 0.19-0.73 ms; graph-topology check failed (7 mix-to-sublayer edges) | not a real fork and join in the captured graph; parked until a new design |
| Engram rows cached in spare GPU memory ("hot Engram in HBM") | not built | sized from 52 profiled rounds: all host Engram work costs ~0.12 ms per round; a partial cache removes nothing because a round needs all 288 rows; fully resident is 103 GiB against ~44 GiB free on the stage-1 board |
| Gate-column router variant (`GATE_COLS`) | slower at 2+ tokens per step (6 tokens: 18.12 vs 14.82 µs) | — |
| Fused layer transition, v1 and v2 | v1 slower; v2 26.8 vs 16.53 µs for the pair it replaces | the hyper-connection mixing step is ~11.4 of the 16.5 µs; a side-stream version is in testing |
| L1 activation prefetch + evict-first weights | neutral (−0.04 ms) | the expert kernels run at 24 % occupancy and stall on long scoreboard, not on memory |
| 19 expert-kernel variants | all bit-clean, none beat production; half-warp variants 25-30 % slower | issue- and latency-bound; this led to the instruction diet |
| L2 warm-up of the next weight matrix on a side graph branch | lost | branches overlapped, but the warm-up stretched to 21-28 µs beside the main kernel; best case 2.4-4 µs per projection |
| Deeper dense-kernel prefetch (`DMV_X_DEEP`) | lost, bitwise over 3,648 runs | every variant 1.2-5 µs slower; the existing double buffer is enough |
| MoE sum folded into the all-reduce, env-only | +0.28 ms | V4.1's 61,440-byte message is not admitted to the push path and falls back to pull; a rebuilt admission is in testing |
| Spin-loop wait in the broadcast queue | +0.04..+0.09 ms | — |
| 200 W instead of 150 W per card | −0.06 ms, neutral | the clamp acts mostly outside decode; an older 200 W gain came from the higher clock ceiling |
| 3 or 4 drafts per round | refused at boot | the DSpark checkpoint's block size is 5 |
| Suggested tiling config for the dense kernel | no gain; greedy 2 of 8 plus near-ties | re-run on the v2 gate above |
| FP8 tuning set | neutral | — |
| Expert "wave" down kernel (`EXPERT_WAVE`, test D45R4; [T06](../engine/in-testing/T06-expert-wave-v41k.patch)) | ABBAABBA decode-only, 8 pairs: +0.273, +0.268, +0.161, +0.189, +0.172, +0.089, +0.371, +0.205 ms per round, average **+0.216** (95 % interval +0.118..+0.314); gate PASS, T=1 texts the same; A/A +0.044 / +0.011 | rejected: detectably slower. Its earlier runs (D45, D45R-D45R3) stopped in their own checks: a ptxas parser, a stale build cache, sanitizer memory; each was fixed |
| Split-K tensor-core decode attention (`ATTN_HMMA=2`, 64 keys, D47R2) | ABBA means −0.156, −0.164, −0.116, −0.137 (average −0.143), not detectable; near-tie gate FAIL: a confident token moved in 6 of 8 rows, logprob drift at 318 of 326 positions, KL mean 0.0058 (max 0.25) | rejected on quality. GPU checks were clean after a racecheck fix (one `__syncwarp`); 32 keys not tried, same numerics |
| FP16-packed shared-expert down kernel (`SHARED_DOWN`, D49R) | near-tie gate FAIL: a confident token moved, KL max 0.17; decode 25.30 → 25.15 ms per round | rejected on quality |
| Fused layer transition without the early path (`FTNE`, D50R2) | ABBAABBA, 8 pairs, average +0.020 ms per round (95 % interval −0.078..+0.118); identical 8 of 8, texts 11 of 11 | neutral; not adopted |
| Probabilistic sharded drafts for thinking mode (D46; [T04](../engine/in-testing/T04-psample-shard.patch), as in 1Cat #183) | four variants at T=1: +0.05..+0.15 accepted drafts per round, but +0.5..+1.55 ms per round, so −3.1 to +0.6 % tok/s (three of the four 95 % intervals span 0; the fourth is below 0) | the extra drafter work eats the acceptance gain |
| Draft temperature 1.2 / 0.85 (D46) | T=1 −2.9 % tok/s / about 0 | – |
| At most 3 verified drafts per round (`dspark_max_verification_tokens: 3`, D46) | T=0 −2.09 ms per round but −0.877 accepted drafts per round: −14.5 % tok/s | shorter rounds do not pay for the lost drafts |
| Bitwise FP8 drafter mat-vec (`DRAFT_GEMV2`, D53R) | both drafter switches together: identical, average −0.069 ms per round, 7 of 8 pairs faster, not detectable; isolated drafter step 780.1 µs both, 627.8 µs sharding only, 828.2 µs before | slower than the sharding alone; off |
| Lookup-free IQ1_M expert repack | no-go before a build: 360 → 344 instructions per 256 weights (−4.4 % against a 20 % gate), +35.7 % bytes | not worth the memory; dropped |
| Asynchronous scheduling on Model Runner V2 (D54R, D54A) | against V1: −2.872 / −2.860 ms per round; against synchronous MRV2: −0.085..−0.117 (D54A), no verdict run; bitwise | about 0.4 %; it needs its own serving profile; off for now |

Prefill chunk: 8,192 kept. 4,096 saved 5.6 % of first-token time at 32K, 1.8 % at 64K and nothing at 128K (greedy 6 of 8
plus 2 near-ties), then failed the approved near-tie gate on its re-test (above); 2,048 and 16,384 were slower; above
16,384 the model refuses.

On 2026-11-03 every lever that was not adopted was re-reviewed for a build or deploy defect that could void its result.
None was found. Two verdicts were reopened instead: the router floor (its old result was one unpaired arm on a
different base; re-tested and kept, above) and the all-reduce push path (a port gap; in testing).

## In testing

The rest of the queue (D51R4, D44R5, the concurrency window, the final benchmark and D40): [roadmap.md](roadmap.md).
