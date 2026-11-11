# Levers

Every speed change we tried on this build, with its source and its measured result. A lever is a `VLLM_V41_*` switch
that defaults off; with the switch off, the code path is unchanged (proved by a CPU test and an AST comparison). Numbers
are ms per verify round, ABBA averages on the A/B harness ([method](method.md)), 2026-11-03 to 2026-11-05, unless
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

### All-reduce, pipeline hand-off and prefill experts (adopted 2026-11-04/05; the 2026-11-05 checkpoint)

- **All-reduce push path for V4.1's MoE sum, `VLLM_V41_SUM2_PUSH_ANY=1`** with `VLLM_SM70_MOE_ADD_ALLREDUCE=1` and
  `VLLM_SM70_TP4_PUSH_ALLREDUCE_SMALL_MESSAGES=1` (ours on 1Cat's custom all-reduce;
  [engine/production/0056-allreduce-sum2-push.patch](../engine/production/0056-allreduce-sum2-push.patch), formerly
  in-testing T03; test D44R5, 2026-11-04 evening). Folding the shared + routed expert sum into the TP4 all-reduce lost
  0.28 ms as an env-only switch, because V4.1's 61,440-byte message was not admitted to the push path and fell back to
  pull. The rebuilt admission lets it in. MEASURED, ABBAABBA decode-only ms per round, 8 pairs: −0.034, −0.067,
  −0.138, +0.003, −0.062, −1.062, −0.056, −0.021, average **−0.180** (95 % interval −0.278..−0.081); T=1 texts 11 of 11
  the same; A/A +0.069 (T=0) and +0.031 (T=1). Earlier runs D44-D44R4 had stopped in their own build, check and deploy
  steps.
- **Lever G, `NCCL_P2P_LEVEL=NVL`** (environment only; installed 2026-11-05 14:06Z). NCCL uses peer-to-peer transfers
  only between GPUs on the same NVLink board, so the pipeline hand-off from board B to board C takes NCCL's host path.
  A step timer on the stage-1 board found the later prefill chunks waiting on the hand-off: later-chunk forward median
  4,176 ms in production against 3,429 ms with the setting (MEASURED, 2026-11-05, timer arms). Its window (OFF ON ON2
  OFF2, one prompt per length per arm, MEASURED): first token at 32,718 tokens 18.99 / 19.41 s → **16.67 / 16.57 s**
  (−13.4 % of the means), at 131,419 tokens 69.05 / 71.48 s → **60.34 / 60.27 s** (−14.2 %); greedy output identical
  (sha) in every arm; decode 28.10 / 27.95 against 27.74 / 27.88 ms per round at 32K, A/A +0.053 (not a decode lever).
- **SM70 prefill IQ GEMM for the routed experts, `VLLM_V41_PREFILL_IQ_GEMM=1`, `TILES=5,4,4,4,4,4`, `GRID=0`** (ours;
  [engine/production/0057-prefill-iq-gemm.patch](../engine/production/0057-prefill-iq-gemm.patch) and its `v41prefmoe`
  library; test D51, installed 2026-11-05 15:12Z). Prompt reading on the first pipeline stage was 44 % expert FFN, routed and shared
  (MEASURED profile, 131K prompt). The kernel keeps 1Cat's SM70 operand decoders, FP32 HMMA mainloop and FP16 epilogue
  (OpenMMLab TurboMind code carried by 1Cat) and replaces the scheduling: compact per-expert member tiles, a tile family
  of 4 and 8 warps, and one tile choice frozen per codec and role. Decode (at most 6 tokens per step) never enters it.
  MEASURED:
  - micro-benchmark on real routing histograms (153,600 captured rows): 35,601 µs (current kernels) → **29,693 µs**
    (−16.6 %); the exact and tuned old paths 35,114 and 35,052 µs;
  - FP64 matrix: within bound in every case, 504 of 1,280 cases bit-identical, at most 48 ulp, relative L2 at most
    6.5e-5 (so not bitwise: it went through the near-tie gate); compute-sanitizer memcheck, racecheck and synccheck
    clean on single-GPU and on each TP4 worker;
  - serving window (OFF ON ON2 OFF2, before lever G): first token **−4.1 % at 32,768** tokens (20.40 → 19.57 s),
    **−4.3 % at 150,000** (82.41 → 78.86 s), **−2.4 % at 300,000** (161.77 → 157.86 s); generated tokens identical at
    every length; decode time ratio 0.9998 (T=0) and 0.9987 (T=1), not a decode lever;
  - install on the production set with lever G: near-tie gate PASS, identical 8 of 8, KL 0.0 over 1,215 positions;
    activation census on all 8 workers; long-prompt output sha unchanged (32,768 → `cdf3cf45c3cf`, 131,072 →
    `e70897e7b29e`).
- **Checkpoint benchmark** (2026-11-05, all 30 keys): [measurements.md](measurements.md#checkpoint-benchmark-2026-11-05).

### After the checkpoint (adopted 2026-11-11)

Three changes, tested on the production host from 2026-11-10 22:54Z to 2026-11-11 01:23Z and adopted in one step at
01:28Z. Each acceptance rule was written down before its data. The GPU clock ceiling was 1,477 MHz (150 W per card)
during these windows, lower than on 2026-11-05, so compare inside a window and not with the tables above. Every prompt
is generated filler text.

- **Three chat slots (`max-num-seqs: 3`).** With one slot the server kept one chat's prompt cache, so when long chats
  took turns every return read its whole prompt again. MEASURED, three chats of 60K, 100K and 150K tokens taking turns
  for three rounds: one slot, 6 returns, 0 cache hits, first token 20.6 / 32.9 / 49.2 s; three slots, **6 of 6 hits,
  first token 0.57-0.88 s**. A lone request is not slower: 132.1 → 132.0 tok/s, 21.80 → 21.78 ms per decode round.
  Chats of 150K, 150K and 480K tokens held together: 3 of 3 hits (0.91 / 0.86 / 2.24 s against 49.3 / 49.3 / 170.1 s
  cold); least free memory on a card 7,228 MiB. A fourth chat takes the slot used longest ago (four chats over three
  slots: 0 of 4 hits, as forecast); a chat that was pushed out pays one cold read and is cached again on its next turn
  (MEASURED on the adopted server). Near-tie gate on the rotation's turns (cached follow-ups against cold reads of the
  same prompt in one boot, 6 rows with one slot and 6 with three): every row identical, PASS.
  - What it is not: a throughput claim. Requests still run one at a time on our host; the slots keep caches.
  - The slots run on our multi-request engine work of 2026-11-06/07. That work is later than the checkpoint and is
    **not in this repository's patches**: the published tree serves one slot.
  - Limit of the gate: its rows are filler text through the completion endpoint. On chat-template turns a cached reply
    can differ from a cold read of the same turn: 2 of 4 turns differed in one check on the one-slot server as it was
    before this change. So the slots did not introduce it; they raise how often a turn is served from cache. A second
    check that recorded token probabilities found every compared row identical, but only 1 of its 4 returns was served
    from cache. The size of those differences and their cause are not measured yet.
- **System notes keep their place, `VLLM_V41_SYSTEM_IN_PLACE=1`** (ours;
  [engine/production/0058-system-notes-in-place.patch](../engine/production/0058-system-notes-in-place.patch)). On the
  Messages endpoint, a system message that arrives after the first turn (an agent harness adds such notes in the middle
  of a chat) was moved to the front of the prompt. Every token after the front then shifted and the chat read its whole
  prompt again. With the switch the note stays where the client sent it, which the DeepSeek-V4.1 encoding renders
  natively. MEASURED on a 31,267-token chat with a note added before turn 2: cached tokens 0 → **31,248 of 31,300**;
  first token of turn 2 **11.2 s → 0.51 s**; the note was obeyed 10 of 10 times with the switch on and 10 of 10 off;
  chats without such a note returned the same replies with the patched file and the switch unset (3 of 3). Unset or 0
  is the old behaviour; any other value stops the server at start.
- **Top-k segments of 1,024, `VLLM_V41_TOPK_SEG=1024`** (ours;
  [engine/production/0059-topk-segment-width.patch](../engine/production/0059-topk-segment-width.patch)). Each decode
  round selects the top entries of the index score row. The row was cut into segments of 8,192 scores; segments of
  1,024 run more of that work in parallel. The selection is the same for every width. MEASURED in two windows of four
  arms, two prompts per length, decode ms per round, ON minus OFF per pair (A/A in brackets):

  | prompt | window 1 (OFF ON ON2 OFF2) | window 2 (ON OFF OFF2 ON2) |
  |---|---|---|
  | 8,192 | −0.38, −0.32 (+0.03, +0.08) | −0.34, −0.34 (−0.15, −0.16) |
  | 32,768 | −0.32, −0.32 (+0.05, +0.05) | −0.57, −0.34 (+0.03, +0.26) |
  | 65,536 | −0.33, −0.48 (+0.11, −0.05) | −0.32, −0.08 (−0.13, +0.11) |
  | 131,072 | −0.20, −0.46 (+0.21, −0.04) | −0.16, −0.19 (−0.03, −0.05) |

  All 16 pairs are faster; every output is byte-identical in every arm and to the baseline taken before the windows;
  first token unchanged. Our rule for adoption looked at 131,072 only and asked for both pairs at or below −0.15 and
  larger than the A/A drift. Window 1 missed it by 0.01 ms (−0.20 against a drift of +0.21). We then fixed one repeat
  window in writing, with the arm order reversed, and it passed by 0.01 ms on its smaller pair. Both windows are shown
  for that reason. After adoption, one arm on the installed set against the baseline before the windows (same prompts,
  outputs identical 8 of 8): **−0.17 ms per round at 8K, −0.31 at 32K, −0.33 at 64K, −0.40 at 128K** (22.37 → 22.20,
  27.46 → 27.16, 23.13 → 22.80, 24.70 → 24.31; differences taken before rounding). That is 0.8 to 1.6 % of a round; a short prompt shows no change
  (21.81 ms per decode round against 21.78-21.80 before).
- Not adopted in the same session: the router with 8 warps instead of 4 ([Did not work](#did-not-work)).
- 0058 and 0059 were measured on our production tree, which holds the later multi-request work. The published patches
  are the same changes cut against the published tree: they apply and compile there (trees `1ee8ad2755b4` and
  `e082b9540245`), and the changed lines are the same except one comment. They were not run on the published tree.

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
| MoE sum folded into the all-reduce, env-only | +0.28 ms | V4.1's 61,440-byte message was not admitted to the push path and fell back to pull; the rebuilt admission (0056) was adopted on 2026-11-04 (above) |
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
| Fused prefill attention, lever A mode 2 (2026-11-05 window, on the production set with lever G; a port of philbert440's SM70 sparse prefill attention) | first token 32,768 tokens 16.68 / 16.71 → 14.78 / 14.83 s (−11.4 %), 131,072 tokens 60.27 / 60.67 → 54.26 / 54.11 s (−10.4 %); two-to-three-request serial cohorts +5 to +13 % aggregate; NUMERICS-GATE FAIL: identical 1 of 8, a confident token moved (first at a top-2 gap of 0.406 nats), KL mean 0.0109 over 366 positions | not installed: it changes output. Its kernel matches production's attention on 99.4 % of elements (at most 1 ulp); the difference is the order of the score sums. A summation-order-exact version (mode 3) is being prepared on our test machine |
| Asynchronous scheduling on Model Runner V2 (D54R, D54A) | against V1: −2.872 / −2.860 ms per round; against synchronous MRV2: −0.085..−0.117 (D54A), no verdict run; bitwise | about 0.4 %; it needs its own serving profile; off for now |
| Router with 8 warps instead of 4 (`ROUTE_WARPS=8`, 2026-11-11) | ABBAABBA, 8 pairs, decode ms per round: +0.037, −0.027, −0.061, −0.002, −0.083, −0.068, +0.036, −0.050, average **−0.027** (95 % interval −0.125..+0.071); texts identical 11 of 11 in every pair | neutral on this host; the setting stays 4 |

Prefill chunk: 8,192 kept. 4,096 saved 5.6 % of first-token time at 32K, 1.8 % at 64K and nothing at 128K (greedy 6 of 8
plus 2 near-ties), then failed the approved near-tie gate on its re-test (above); 2,048 and 16,384 were slower; above
16,384 the model refuses.

On 2026-11-03 every lever that was not adopted was re-reviewed for a build or deploy defect that could void its result.
None was found. Two verdicts were reopened instead: the router floor (its old result was one unpaired arm on a
different base; re-tested and kept, above) and the all-reduce push path (a port gap; rebuilt and adopted on 2026-11-04,
above).

## In testing

What comes after the 2026-11-05 checkpoint: [roadmap.md](roadmap.md).
