# Levers

Every speed change we tried on this build, with its source and its measured result. A lever is a `VLLM_V41_*` switch
that defaults off; with the switch off, the code path is unchanged (proved by a CPU test and an AST comparison). Numbers
are ms per verify round, ABBA averages on the A/B harness ([method](method.md)), 2026-11-03, unless labelled. Negative
is faster.

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
  ([Elevatormusic/TensorFold#25](https://github.com/Elevatormusic/TensorFold/pull/25)), ported first in our DGX sPLIce
  work. The drafter and the verifier share keyed Gumbel draws, so drafts agree with the target far more often at T>0.
  T=1 acceptance 1.85 → 2.25 per round, +14 % tok/s, about 0.3 ms of overhead, no T=0 cost. Exact.
- **`MARKOV_SHARD=1`** (ours), **`COUPLED_SHARD=1`, `COUPLED_LOCAL=1`** (DGX sPLIce ports): the draft head and the
  coupled sampler work on vocabulary shards, inside a captured graph. −0.2 ms at T=0; −0.23 ms and −0.12..−0.24 ms at
  T=1 (11 of 11 prompts).
- The six levers above together: T=0 29.55 ms (~105.8 tok/s, +6.7 %); T=1 30.0 ms (~108.4 tok/s, +23 %).

### Kernels and host path

- **`PLAN_FUSE=1`** (DGX sPLIce port): the expert routing plan is built inside the q8 quantize launch. T=0 −0.37/−0.36
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
- **`ROUTE_FAST=1`, `ROUTE_WARPS=4`** (router floor, DGX sPLIce port): average −0.165 ms (T=0 −0.18/−0.60, T=1
  +0.28/−0.15). That is inside the session's measured drift, so it is **not** a significant win. Greedy output bitwise,
  no errors. Kept on under our rule for upstream-backed changes that are correct and inconclusive.

## Did not work

| change | result | why |
|---|---|---|
| Expert top-p pruning (0rand TensorFold `TF_DSV41_EXPERT_TOPP`, 0.85) | 78 tok/s, greedy FAIL | the divergence is inherent: it drops experts the target would use |
| Async scheduling under PP2 + speculative decoding | 90.5 tok/s, 34.1 ms on the first try; later runs crashed at request end (invalid sampled token ids) | the crash stands; parked until 1Cat's newer model runner is ported |
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
| Suggested tiling config for the dense kernel | no gain; greedy 2 of 8 plus near-ties | — |
| FP8 tuning set | neutral | — |

Prefill chunk: 8,192 kept. 4,096 saved 5.6 % of first-token time at 32K, 1.8 % at 64K and nothing at 128K (greedy 6 of 8
plus 2 near-ties); 2,048 and 16,384 were slower; above 16,384 the model refuses.

On 2026-11-03 every lever that was not adopted was re-reviewed for a build or deploy defect that could void its result.
None was found. Two verdicts were reopened instead: the router floor (its old result was one unpaired arm on a
different base; re-tested and kept, above) and the all-reduce push path (a port gap; in testing).

## In testing

The prefill skip (D35) measured −8.6 / −20.4 / −31.3 % first-token time at 32K / 150K / 300K with identical output in its
first repetition ([measurements](measurements.md#prefill-skip-in-testing-2026-11-03)). The larger GPU hot ring won its A/B
(300K −1.09 ms per round, 150K −0.25) and awaits its adoption check. The side-stream mixing step failed its single-GPU
check and was not deployed. The rest of the queue, D36-D47: [roadmap.md](roadmap.md).
