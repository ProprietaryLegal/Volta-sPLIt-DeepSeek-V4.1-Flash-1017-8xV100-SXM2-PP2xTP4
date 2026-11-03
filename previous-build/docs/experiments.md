# Experiments

One entry per idea we tried or scoped on the V100 host, with its verdict. Labels: **MEASURED** (on our host),
**ESTIMATED** (arithmetic or a model), **UPSTREAM** (someone else's figure). All server arms ran at DDR4-2666, a
1425 MHz graphics-clock cap and 180 W per card unless stated, against the baseline described in [method.md](method.md).
The promotion rule and the gates are in [method.md](method.md#promotion-rule).

| ID | idea | verdict |
|---|---|---|
| [ER1](#er1-engram-tables-resident-in-host-ram) | Engram tables resident in host RAM | **promoted** (production) |
| [MP1](#mp1-staged-exl3-moe-prefill-kernel) | staged EXL3 MoE prefill kernel | **promoted** (production) |
| [Q0](#q0-baseline-under-the-gates) | baseline of production under the gates | closed (the control) |
| [ML1](#ml1-max-model-len-1048576-x-2-against-327680-x-3) | 1M x 2 against 327,680 x 3 | closed: no prefill difference |
| [AUD1](#aud1-in-memory-prefix-reuse) | in-memory prefix reuse | won |
| [GMU1](#gmu1-grow-the-kv-pool) | grow the KV pool | not promoted (two arms); closed |
| [DEP1](#dep1-adaptive-draft-depth-p_min) | adaptive draft depth (`p_min`) | lost |
| [ER1-LA](#er1-la-engram-lookahead) | Engram lookahead during prefill | lost |
| [PC1](#pc1-prefill-chunk-2048) | prefill chunk 2,048 | lost |
| [DLANE1](#dlane1-engine-decode-lane-switch) | the engine's decode-lane switch | not promoted |
| [OPS1](#ops1-bounded-startup-warm-up) | bounded warm-up after start | inconclusive |
| [PIN1](#pin1-engram-io-thread-placement) | Engram IO thread placement | closed (moot) |
| [PROF1](measurements.md#where-a-decode-step-goes-2026-11-01-profiled) | profile one decode step on every rank | measured; decode study done; exact changes **PENDING** server timing |
| [KMOE1](#kmoe1-next-steps-for-the-moe-prefill-kernel) | next MoE prefill kernel steps; 1Cat #1335 | lost: #1335 n/a; B / C / X bit-identical, no net gain |
| [MA1V](#ma1v-kv-capacity-audit) | what the KV pool number means | analysis done; hold-stress measured: 71.5 % peak, 0 preemptions |
| [MC1](#mc1-persistent-prefix-tier) | prefix tier that survives restarts | port design done; first check: warm hits not always byte-identical (open) |
| [RE1](#re1-engram-from-another-host-over-rdma) | Engram served over RDMA | parked (no RDMA NIC) |
| [DR1](#dr1-rtx-3090-drafter-host) | RTX 3090 drafter host | parked (hardware) |
| [CLK1](#clk1-sm-clock-lock) | SM clock lock under 180 W | proposed |
| [UPS1](#ups1-port-survey-of-the-sister-projects-upstream-items) | port survey of DGX sPLIce's upstream items | proposed; folded into the [survey](survey.md) |

## ER1: Engram tables resident in host RAM

**Question.** When first installed, the host had 196 GiB of RAM, so the engine read the Engram tables from NVMe through
the page cache (`VLLM_DS41_ENGRAM_RESIDENT=0`). After a RAM upgrade to 8 x 32 GB, does the engine's own default,
resident tables, pay?

**Evidence first.** On 2026-10-31 the same prompts ran 20-40 % faster in prefill when their Engram rows were already in
the page cache, and a truly cold Engram cost ~18.6 s (1.68x) at 75K (MEASURED, [measurements](measurements.md)).

**Result (MEASURED, 2026-11-01 01:51-02:17 UTC, seeds 106-111).**

| cell | baseline | resident | change, 95 % CI |
|---|---|---|---|
| cold 75K first token | 46.00 s | **26.94 s** | **−41.4 %** (−46.5, −34.8) |
| cold prefill tok/s | 1,656 | 2,785 | +68.1 % (+51.9, +86.9) |
| warm 75K first token | 27.02 s | 27.10 s | +0.3 % (−0.6, +1.7) |
| decode tok/s, cold / warm cells | 42.15 / 40.91 | 46.41 / 44.78 | +10.1 / +9.4 % (CI spans 0) |
| decode beside a cold 75K prefill | 18.2 tok/s, gap 2.10 s | 29.5 tok/s, gap 1.21 s | |
| that prefill's first token | 104.3 s | 53.6 s | −48.6 % |
| 3 x ~300K wall | 476 s | 368 s | 0 preemptions in both |

Greedy 16 / 16 byte-identical; functional checks 15 / 15. With the rows in RAM, cold equals warm (26.7-27.2 s on every
seed). Decode beside a prefill gains most, because the prefill no longer waits on NVMe while the decode shares its
steps.

**Cost.** The four stage-0 ranks load 45.78 GiB each, one at a time, in 20.8-27.3 s per rank (1.80-2.36 GB/s,
`O_DIRECT`, 32 threads). About 208 GiB of ~251 GiB stays held. The engine refuses a rank unless its tables plus 32 GiB
are available, so a start needs ~241 GiB available with the server stopped.

**Verdict: promoted.** In production since 2026-11-01 05:19 UTC ([decisions](decisions.md)).

## MP1: staged EXL3 MoE prefill kernel

**Question.** The engine's tiled EXL3 MoE prefill pass takes 7.6-8.0 ms per layer per rank at T = 1,016, 5.2-5.5x its
HBM floor (MEASURED with `ncu`). The engine's own design note (`docs/moe_prefill_persistent.md`) proposes cooperative
coalesced loads into a shared-memory ring. Does step 1 of that design pay, and keep outputs bit-identical?

**Diagnosis (MEASURED, `ncu`, layer 5).** Occupancy 18.5-24.7 %, DRAM 15-26 % (nowhere near HBM-bound), L1/TEX 81-87 %,
top stall L1TEX long scoreboard. The scattered 16-bit trellis-word loads saturate the L1/TEX path. Verdict against the
design's go/no-go: GO.

**Step 1 ([patch 0003](../patches/0003-mp1-exl3-tiled-smem-staging.patch)).** Each warp loads CH k-tiles of trellis
words at a time with coalesced 128-bit `__ldg` into registers, one chunk ahead, stores them to a per-warp shared-memory
ring, and each lane then gathers the words it would have read from global memory. Decode, MMA order, k summation order
and the cross-warp reduction are unchanged, so outputs are bit-identical. The 64-row tile stays on the upstream path
(staging was slower there at every chunk size). Behind `VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1`, default off.

**Kernel result (MEASURED, one card, no server).** Gate −9.1..−12.3 %, down −7.5..−13.2 %, bit-identical every run
([table](measurements.md#kernel-level-staged-exl3-moe-prefill-2026-10-31-one-card-no-server)). The staged kernel's
achieved occupancy fell to 18.5 % from 24.5 % (MT16), and shared-load bank conflicts appeared; see KMOE1.

**Server result (MEASURED, 2026-11-01 04:33 UTC boot, rebuilt `_C`, Engram from NVMe, seeds 230-235).**

| gate | result |
|---|---|
| greedy against the baseline | 16 / 16 byte-identical, 0 near-ties (two prompts of 7,345 and 22,251 tokens run full chunks through the kernel) |
| functional checks | 15 / 15 |
| warm 75K first token | **26.39 s vs 27.02 s, −2.33 % (CI −3.15, −1.50)**; per seed 26.01-26.76 s |
| warm prefill tok/s | 2,843 vs 2,774, +2.5 % (CI +1.7, +3.4) |
| cold 75K first token | 47.37 vs 46.00 s, CI −11..+20 %: NVMe noise, moot once Engram is resident |
| ms per verify round | 71.3-73.4 vs 71.7: unchanged (decode does not use the tiled kernel) |
| 3 x 300K | 3 / 3, 0 preemptions, wall 498.4 s, peak KV 35 % |

**Build.** `_C` rebuilt from the pinned tag with 0003 applied (CMake + Ninja, RelWithDebInfo, `TORCH_CUDA_ARCH_LIST=7.0`,
gcc-14, CUDA 12.8). 81 steps, 16 minutes cold, 77 s incremental. Two configure errors, both fixed: the SM70 FA2 prefill
option had to be off (`-DVLLM_SM70_79T_PREFILL=OFF`, which affects only that target), and the build had no network, so
CUTLASS 4.5.0 headers from an installed copy were passed explicitly (upstream pins 4.4.2). See
[patches/README.md](../patches/README.md#rebuilding-_c).

**Verdict: promoted** (step 1). In production since 2026-11-01 05:19 UTC with resident Engram. The author's design
target (~2.5-3 ms per layer) needs the later steps; they are KMOE1.

## Q0: baseline under the gates

**What.** The reference every arm compares against: production's configuration with Engram from NVMe, measured under
the full gate set on one boot (2026-11-01 00:36-01:32 UTC, DDR4-2666, 1425 MHz cap, 180 W). Greedy reference recorded
three times (all identical), functional checks 15 / 15, private task suite 41 of 46, cold / warm 75K 46.00 / 27.02 s,
decode beside a prefill and stress run. An earlier Q0 at uncapped clocks and DDR4-3200 (2026-10-31) is in
[measurements](measurements.md#2026-10-31-q0-baseline-uncapped-clocks-ddr4-3200-327680-x-3-kv-927004).

**Verdict: closed.** Production (FINAL) passes every gate against it; its own run set is now the reference for future
arms, while the greedy references stay Q0's.

## ML1: max-model-len 1,048,576 x 2 against 327,680 x 3

**Question.** Does the shorter context make prefill faster?

**Result (MEASURED 2026-10-31).** No. Cold 327K prefill 1,916-2,327 tok/s (first token 32.2-39.1 s) matches 1M's
1,895-2,226. The faster 327K runs had warm Engram rows in the page cache.

**Verdict: closed.** Production stays at 327,680 x 3 for concurrency, not speed.

## AUD1: in-memory prefix reuse

**Question.** Does the engine's in-memory prefix cache reuse a long prompt when the same prompt (or the same document
with another question) comes again, and does `cache_salt` isolate requests?

**Result (MEASURED, three seeds of ~75K tokens).**

| cell | first token / prefix hits |
|---|---|
| A first request, salt S | 26.91-30.38 s / 0 |
| B same prompt, same salt | **0.61-0.73 s / 74,752** (99.5 %) |
| C same document, other question, same salt | 0.68-0.70 s / 74,752 on two seeds; **one miss** (26.91 s / 0) |
| D same prompt, different salt | 26.92-26.96 s / 0 |
| E / F same prompt, no salt, first / second | 26.87-27.03 s / 0, then 0.61-0.70 s / 74,752 |

**Verdict: won.** The same salt (or none) shares; a different salt shares nothing. One open question: the cell-C miss
on one seed (the same document string, a different trailing question, the same salt). Reuse lives in GPU memory only
and does not survive a restart (that is MC1).

## GMU1: grow the KV pool

**Question.** At boot the pool is 927,004 tokens, short of 3 x 327,680 = 983,040 on paper. Can it grow without cost?

- **GMU1-p: CUDA-graph memory estimate off** (`VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=0`, forwarded by
  [patch 0002](../patches/0002-gmu1-cudagraph-sizes-and-profiler-switch.patch)). MEASURED: KV 1,194,319 tokens (3.64x)
  and a 3 x 327,000 load ran clean, but decode came out −3.6 / −4.6 % tok/s and +9-13 % per verify round (78-81 ms).
  **Not promoted.**
- **GMU1-t: trimmed capture list `[1..12,16,18]` plus memory utilisation 0.945** (the launcher's cap; patch 0002's
  `DS41_CUDAGRAPH_SIZES`). MEASURED: KV 936,683 (+1.0 %); greedy 12 / 16 identical plus 4 near-ties. **Not promoted.**

**Verdict: closed.** The 927,004-token pool is accepted as is. What the number means, and the real capacity, is MA1V.

## DEP1: adaptive draft depth (p_min)

**Question.** The engine can truncate each request's DSpark draft at the first position whose drafter probability is
below `VLLM_DS41_DSPARK_PMIN` (with `..._PMIN_MAX_BATCH` and `VLLM_DS41_ATTN_PRECAPTURE_SHAPES=verify_b1all`). For a
lone request, truncation pays only if a verify row at B = 1 costs more than ~2-3 ms, 5-7 % of a round (ESTIMATED from
the author's acceptance-by-position table). The author writes that verification stays exact.

**Result (MEASURED, `p_min` 0.3).** Greedy check FAIL: 6 / 16 identical, 8 near-ties (0.59-0.77 nats), 2 divergences
over 0.9 nats (one prompt, 1.15 nats at token 42); 5 of 8 prompts diverge, the same way in both runs, so the change is
deterministic. Decode +3.2 to +6.7 % with CIs spanning 0. `p_min` 0.5 was not run (it truncates harder).

**Verdict: lost.**

## ER1-LA: Engram lookahead

**Question.** With Engram not resident, does a 1,024-token Engram lookahead during prefill hide NVMe reads?

**Result (MEASURED).** Cold 75K first token 58.03 s against 46.00 (+26.2 %, CI +0.7..+55.2); warm unchanged; greedy
identical. The cold cells are confounded: other workloads came back on the host during this arm (load average
11.4-13.6 against 6.4-10.7 for the control), and Engram reads share the NVMe with their IO.

**Verdict: lost**, and moot under resident Engram, where the engine ignores lookahead.

## PC1: prefill chunk 2,048

**Question.** Do larger prefill chunks (1,024 → 2,048 → 4,096 batched tokens) speed prefill?

**Result (MEASURED).** 2,048-token chunks cut the boot KV pool from 927,004 to 385,363 tokens (1.18x at 327,680; the
gate needs at least 655,360). The speed reading was inconclusive. 4,096 was not tried.

**Verdict: lost** on memory.

## DLANE1: engine decode-lane switch

**Question.** The engine has an off-by-default switch, `VLLM_DS41_DECODE_LANE` (needs `VLLM_DS41_FOLD_DRAFTS=1`,
which is on). Its docstring says a decoder rides only every other step while a prefill shares the PP batch queue and
claims 2·max(s0, s1)/(s0 + s1) for the decoder. Does it lift decode beside a prefill (29.6 tok/s in production)?

**Result (MEASURED, 2026-11-01, against production).** Greedy 16 / 16 identical; functional checks 15 / 15. Cold / warm
first token +0.41 / +0.59 % (CIs include 0); warm prefill tok/s −0.72 % (CI −1.76..−0.02); warm decode +8.4 % (CI
−5.9..+25.3, inconclusive); decode beside a prefill 28.9 tok/s against production's 29.55.

**Verdict: not promoted.** Production's adaptive sliced prefill already gives the decoder its steps.

## OPS1: bounded startup warm-up

**Question.** Does a short warm-up after each start (waves of 1, 2, 3 concurrent requests, raw completions, 32 tokens
each, a fresh salt per request, a hard deadline) remove a first-request penalty?

**Result (MEASURED).** Three restarts, the warm-up on in one of them (clean in 5.3 s): no first-request penalty
above the cold spread in any.
Code: [tools/warmup.py](../tools/warmup.py), [tools/warmup.sh](../tools/warmup.sh).

**Verdict: inconclusive, not promoted.** Under resident Engram the cold-row cost it targeted is gone.

## PIN1: Engram IO thread placement

**Question.** Do the Engram IO threads compete with the server's CPU threads, so that pinning them to their own L3
slice helps cold prefill?

**Result (MEASURED).** A read-only thread census ([tools/proc_census.py](../tools/proc_census.py)) during a cold cell:
the IO threads run at 1-5 % CPU each. Under resident Engram there are no IO threads in the request path. The A/B with
[tools/pin_io.py](../tools/pin_io.py) was not run.

**Verdict: closed (moot).**

## KMOE1: next steps for the MoE prefill kernel

2026-11-01. Code reading and offline builds, then one card for timing and `ncu` (no server).

- **A. 1Cat [#1335](https://github.com/1CatAI/1Cat-vLLM/issues/1335) (32-slot grouped EXL3 GEMV) does not apply here.**
  With the launcher's defaults, every MoE pass of 128 tokens or more takes the row-tiled kernel (16 / 32 / 64-row tiers;
  experts of 160 rows or more go through reconstruct + cuBLAS). The grouped kernel (at most 8 slots) runs only for
  passes of 2-127 tokens: verify rounds and a prompt's tail chunk, at most 127 of 75,000 prompt tokens (≤ 0.17 %,
  ESTIMATED). #1335's crossover is ~384 tokens (UPSTREAM), so it would not take those passes either. No port.
- **C. The staged kernel's bank conflicts have one cause.** For K = 4 experts, tile 1 of each staged k-tile starts
  exactly 32 words after tile 0, so each of the six gathers is a 2-way conflict. A bank model reproduces MP1's `ncu`
  counts (predicted 6.29 M shared-load requests and 1.38 M conflicts against 6.00 M and 1.16 M MEASURED). Padding tile 1
  by 2 words removes it; only pads of 2 mod 4 are conflict-free, which is why a 1-word stagger did nothing. The
  cross-warp reduction buffer has a separate 4-way store conflict, fixed with 33-float rows. Layout-only, so
  bit-identical by construction. ESTIMATED ~15 % fewer shared-load wavefronts; time effect unknown, likely 0-4 % of the
  MT16 / MT32 kernel.
- **B. Staging on the 64-row tile** (synchronous chunks, no prefetch registers): built; predicted neutral (0 ± 3 %).
- **X. Activation layout.** Per k-tile, the 64-row tile issues 16 activation loads of 16 bytes, each touching 8
  different 128-byte lines, against ~5 trellis loads (SASS, MEASURED static counts). So the activation loads, not the
  trellis words, are the likely cause of the 81-87 % L1/TEX load. A variant that reads activations from a k-octet-major
  copy (one 16-byte load covers 8 consecutive rows) is built in the harness; bit-identical.

**Result (MEASURED, one card; stage-0 layers 5, 12 and 27, T = 512 and 1,016, gate and down projections).** Every
variant is bit-identical to production (`torch.equal` on every covered row). Speed against production per tier,
summed over the three layers: C 0.94-0.95x on the 16-row tier and 1.00-1.02x on the 32-row tier (the 33-float
reduction rows and the new code path cost more than the bank-conflict pad saves); B 0.88-0.97x on the 64-row tier;
X 1.20x on the 32-row tier (+15-27 % per layer) but 0.81-0.86x on the 16-row tier and 0.71x on the 64-row tier,
and its activation copy doubles the time of `pre_rows`. The 64-row tier carries 54 % of the tiled-kernel time, the
16-row tier 30 % and the 32-row tier 17 % (32K profile). The larger lever is outside the kernels: after each
layer's routing plan the host waits for the GPU, a median 156 µs of GPU idle per layer and 103 ms over the 26
prefill chunks of a 32K prompt on stage 0 (MEASURED from the profile). A bit-identical fix is designed, not written.

**Verdict: lost** (no server arm). The variants are not in `patches/`.

## MA1V: KV capacity audit

Offline analysis of the production boot log, 2026-11-01; details in [kv-capacity.md](kv-capacity.md). The binding rank
is a stage-1 rank (the second pipeline stage; 7,279 blocks); each request is charged 1,280 compressed blocks plus a 1,293-block sliding-window
reserve that three requests can never all use at once. ESTIMATED real capacity: ~1.43M tokens of full-length requests.
A PP layer rebalance makes it worse (one layer moves ~1.1-1.2 GiB per rank against a 0.06-0.16 GiB gap between
stages, so 19 / 21 or 21 / 19 shrinks the pool to ~110-190K tokens, ESTIMATED).

**Result (MEASURED, 2026-11-01).** Three 314,728-token requests resident at once: peak KV use 71.5 %, 0 preemptions,
~960K tokens resident; real capacity ESTIMATED ~1.34-1.47M tokens
([kv-capacity.md](kv-capacity.md#the-measurement-2026-11-01)).

## MC1: persistent prefix tier

**Question.** DGX sPLIce reads long prompts back from an NVMe tier after a restart (150K-token prompt: 2.58 s against
58.6 s of prefill, MEASURED there). Can the same work under PP2 x TP4 here?

**Status.** Port design done (2026-11-01; code reading and offline building blocks, no server). The design ports, but
the stock vLLM file tier cannot be used as is: under PP2 it would store misaligned rows, and it would write ~71 GiB
per 150K-token prefix. A compact format needs ~269 MiB for the same prefix, and a reload takes 0.5-1.2 s plus the
uncached suffix against ~52 s cold (all ESTIMATED). Five engine issues must be fixed first, among them block hashes
that are reseeded at every start. ESTIMATED 17.5-24.5 working days (3.5-5 weeks), with 3-5 restart windows for
gates.

**First check (MEASURED 2026-11-01, requests only).** Cold against cold: 8 / 8 byte-identical. A warm in-memory hit
against cold: 2 identical, 3 near-ties, 0 differing, of 5 valid pairs; 3 more warm requests reused nothing because a
guard in the engine's decoder replay dropped the cached prefix
([measurements](measurements.md#prefix-cache-identity-warm-hit-against-cold)). Open finding, under investigation; the
port's byte-identity gate depends on it.

## RE1: Engram from another host over RDMA

**Question.** Serve the Engram tables from another host over a 40 Gb/s RDMA link, as DGX sPLIce does, instead of
holding ~208 GiB here.

**Status: parked.** This host has no RDMA-capable NIC (MEASURED), and resident Engram made it unnecessary.

## DR1: RTX 3090 drafter host

**Question.** Run the DSpark drafter on a pair of RTX 3090s in another host, as DGX sPLIce does.

**Result.** The drafter proxy and its circuit breaker work on this host's CPU (225 of 227 offline tests pass, 2
skipped, 0 fail). No GPU arm: there is no 10 GbE link between the hosts (1 GbE only), the 3090 pair serves the other
deployment, and one input is missing (the local drafter's propose time per round).

**Status: parked.**

## CLK1: SM clock lock

**Question.** Does locking the SM clock under the 180 W limit (instead of a cap) help decode or prefill? Clocks and
power are set outside the experiments; the 1425 MHz cap stays until that changes.

**Status: proposed**, not measured.

## UPS1: port survey of the sister project's upstream items

**Question.** Which of DGX sPLIce's adopted upstream patches apply to the SM70 engine?

**Status: proposed**; its scope is now covered by the [survey](survey.md).
