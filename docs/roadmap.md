# Roadmap and test queue

Status on 2026-11-05. The production server runs the **2026-11-05 checkpoint** (30 keys, one request at a time;
[production.md](production.md)). We measure and use the checkpoint as it stands. Build and test work for the next
changes runs on a separate 4x V100-SXM2-32GB test machine (two NVLink pairs) that cannot hold the whole model; a change
returns to the production host only for its final serving window. Nothing here is a result until its row says so.

## Done (2026-11-03/05)

D1-D34R: the levers in [levers.md](levers.md#adopted), among them the expert-kernel instruction diet (D34, −0.871 ms per
round) and the router floor (D34R, inconclusive, kept as upstream-backed). Then:

| # | test | result |
|---|---|---|
| D35 | Prefill skip, `PREFILL_SKIP_ROWS=3072` | **ADOPTED**: first token −8.8 / −20.6 / −31.5 % at 32K / 150K / 300K, identical output |
| D36 | TP8 feasibility probe | **NO-GO**: modeled 24.65 ms per round against the 22.0 ms bar; 8-way all-reduce 30.8 µs against 5.28 µs 4-way |
| D37 | Prefill profile; indexer overlap; 16,384-token chunks | overlap neutral (bitwise); 16,384 chunks lost (+17.5 % first token at 32K, gate FAIL); token-blocked mixing dropped for time |
| D38 | Larger GPU hot ring, `KV_HOT_POSITIONS=524288` | **ADOPTED**: KV pool 2,076,870 tokens, prefix-cache test 3 of 3 |
| D39 | Harness v2 | references published; A/A under 0.1 ms per round |
| D33C | Side-stream mixing step | parked: micro-benchmark below the bar, topology check failed |
| D41 | V1 async with a request-end guard | rejected: +1.678 ms per round slower, crash-free |
| D42 | Two requests at once, `MULTI_SEQ` | boot failed; diagnostic D42R boot failed too, rolled back cleanly |
| D43/D43R | chunk 4,096; dense tiling; CPU pinning | chunk 4,096 and tiling rejected by the near-tie gate; pinning not adopted (+0.079 ms) |
| D48 | Tiled decode index scorer, `INDEX_TILED` (2026-11-04) | **ADOPTED**: decode round −7.0 % at 150K (29.98 → 27.88 ms), −13.7 % at 300K (34.33 → 29.62 ms), bitwise, texts identical; short context not detectable |
| PB1103 | Production baseline after the PCIe-switch move | **T=0 119.0 tok/s, T=1 120.8 tok/s**; decode-only 25.30 / 25.20 ms per round; long-prompt first token about 2 % lower than before the move |
| D46 | Thinking-mode acceptance: probabilistic sharded drafts; draft temperature 1.2 / 0.85; at most 3 verified drafts | not adopted: +0.05..+0.15 accepted drafts per round cost +0.5..+1.55 ms per round (−3.1 to +0.6 % tok/s); temperature 1.2 −2.9 %, 0.85 about 0; 3 drafts −14.5 % |
| D47/D47R2 | Split-K tensor-core decode attention, `ATTN_HMMA=2` | rejected: −0.143 ms per round, not detectable; near-tie gate FAIL (a confident token moved in 6 of 8 rows) |
| D49/D49R | FP16-packed shared-expert down kernel, `SHARED_DOWN` | rejected: near-tie gate FAIL (KL max 0.17) |
| D50/D50R2 | Fused layer transition without the early path | neutral: +0.020 ms per round (95 % −0.078..+0.118), identical; not adopted |
| D52/D52R2 | Fused prefill index scorer, `INDEX_FUSE=ilp4` | **ADOPTED**: first token −4.9 % at 150K (85.6 → 81.5 s), −9.5 % at 300K (175.5 → 158.7 s), 32K and decode not detectable; near-tie gate PASS, output identical |
| D53R2, D53A2 | Drafter `main_proj` sharding, `DRAFT_MP_SHARD` | **ADOPTED by hand** after the queue's rule called it not detectable: −0.130 ms per round, 8 of 8 pairs faster, bitwise; `DRAFT_GEMV2` stays off (slower together, −0.069) |
| D54, D54R, D54A | Model Runner V2 (our DeepSeek-V4.1 port), synchronous | **ADOPTED** (production since 16:38Z): −2.759 ms per round (95 % −2.898..−2.620), **T=0 134.2 / 135.0 tok/s, T=1 136.6 / 136.4**, bitwise; 150K first token 82.77 s; 32K round 28.02 ms against 26.96 on V1 (open, see D55) |
| D45-D45R4 | Expert "wave" down kernel, `EXPERT_WAVE` | rejected: +0.216 ms per round (95 % +0.118..+0.314), detectably slower; the earlier runs stopped in their own checks |
| IQ1_M repack | Lookup-free IQ1_M experts in spare GPU memory (was D55) | no-go before a build: −4.4 % instructions against a 20 % gate, +35.7 % bytes |
| D55 | Depth sweep, V1 runner against MRV2, production set, 2K-64K | report-only, MEASURED: MRV2 −2.59..−2.94 ms per round at 2K, 8K, 16K and 64K; **+1.41 / +1.44 at 32K**; tokens per round the same |
| D44R5 | All-reduce push path for V4.1's message size, `SUM2_PUSH_ANY` (2026-11-04 evening) | **ADOPTED**: −0.180 ms per round (ABBAABBA, 95 % −0.278..−0.081), T=1 texts 11 of 11; patch 0056 |
| D40 | Four-card fork smoke on one board | boot failed (2026-11-04); the four-card series predates patches 0052-0057 and is not current ([four-card.md](four-card.md)) |
| Lever G | `NCCL_P2P_LEVEL=NVL` (2026-11-05) | **ADOPTED**: first token −13.4 % at 32K, −14.2 % at 128K; output identical; decode unchanged |
| D51 (R4, R5) | SM70 prefill IQ GEMM for the routed experts, `PREFILL_IQ_GEMM` | **ADOPTED** (2026-11-05): first token −4.1 % at 32K, −4.3 % at 150K, −2.4 % at 300K; generated tokens identical; near-tie gate PASS on install, 8 of 8 identical; patch 0057. D51R4 had stopped on a missing profiler event; R5 qualified it |
| Lever A, mode 2 | Fused prefill attention (2026-11-05) | **not installed**: first token −11.4 % at 32K, −10.4 % at 128K, but NUMERICS-GATE FAIL (identical 1 of 8, KL mean 0.0109) |
| CONC | Two and three requests at once on Model Runner V2 | not in the checkpoint. The conc2 crash on a lone 32K request was found and fixed; a prefill-budget correction makes conc2/conc3 output match single-request output exactly (49,152 generated positions); a deployable aggregate gain is not established yet |
| BENCH | Benchmark of the checkpoint (2026-11-05) | speed and LegalBench done ([measurements.md](measurements.md#checkpoint-benchmark-2026-11-05), [quality.md](quality.md)); context sweep and the remaining quality tests in progress |
Details: [levers.md](levers.md), [measurements.md](measurements.md).

## Next (on the test machine first)

None of these is a result. Each returns to the production host only for its final serving window.

| item | what it is | status |
|---|---|---|
| Lever A, mode 3 | the fused prefill attention with production's summation order, so its output is bitwise production's | built; bitwise-identical to production's attention on every synthetic case tried (40 shapes across both stages, 17 to 8,192 tokens, context 0 to 300K, and all 256 final-chunk shapes), sanitizers clean; ESTIMATED from mode 2's window: first token −11 to −14 % at 32K and −10 to −13 % at 128K. Needs a serving window on real weights |
| Prefill expert GEMM follow-ups | measuring the D51 kernel on the real production shapes (ordinary 8,188-token chunks and the tail), mixed tile sizes, padding | in progress |
| Concurrency | conc2/conc3 on Model Runner V2 with the budget correction; the aim is more combined tok/s for 2-3 long-context requests | in progress |
| MRV2 at 32K | the decode round at the 32K prompt is slower than on V1 (D55); cause open (INCONCLUSIVE) | open |
| Decode kernels that failed the near-tie gate | `ATTN_HMMA` (D47R2), `SHARED_DOWN` (D49R): find the element-level difference and whether a bitwise form keeps the speed | open |

## Quality, after the speed benchmarks

- KL divergence and top-1 agreement against the original (unquantized) model, on the served path: pending.
- MMLU-Pro and HumanEval+: pending. LegalBench is done ([quality.md](quality.md)).
- **Asynchronous scheduling on MRV2**: built and bitwise in D54R/D54A; MEASURED −0.085..−0.117 ms per round against
  synchronous MRV2, no verdict run. It needs its own serving profile; not in production.
