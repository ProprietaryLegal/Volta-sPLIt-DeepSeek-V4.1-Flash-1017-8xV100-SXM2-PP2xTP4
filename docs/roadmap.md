# Roadmap and test queue

Status on 2026-11-04, about 17:15Z. The production server is up on the 23-key set. The queue runs one test at a time on the production host; each test boots its own arms and
restores the production stack when it finishes. Nothing here is a result until its row says so.

## Done (2026-11-03/04)

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
Details: [levers.md](levers.md), [measurements.md](measurements.md).

## In the queue

In order. Estimates are the lanes' figures before the test, labelled ESTIMATED; none is a result.

| # | test | patch | what decides it | expectation |
|---|---|---|---|---|
| D51R4 | Tensor-core prefill routed-expert GEMM, `PREFILL_IQ_GEMM` (D51R3 stopped on a check-script limit; fixed) | – | near-tie gate; first token at 32K / 150K / 300K; report only | micro-benchmark MEASURED 30,989 µs against 38,270 (−19 %); end to end not measured |
| D44R5 | All-reduce push path for V4.1's message size, `SUM2_PUSH_ANY` (D44-D44R4 stopped in their build, check and deploy steps; each was fixed) | [T03](../engine/in-testing/T03-allreduce-sum2-push.patch) | v2 ABBAABBA | ESTIMATED −0.08..−0.15 ms per round |
| CONC | Two and three requests at once on Model Runner V2 (`single`, `conc2`, `conc3`); replaces the withdrawn V1 build (D42) | – | single-request identity; combined tok/s at 2 and 3 requests; lone-request cost | CPU tests pass; one boot crash found in review and fixed; not measured |
| BENCH | Final benchmark of the production set: tok/s at T=0 and T=1, plus first token and decode at 32K and 150K | – | one production boot with the full set | – |
| D40 | Four-card fork smoke on one board | [forks/](../forks/1cat-4xv100-tp4/) | greedy identity, activation lines | queued after BENCH |

## After the queue

- **Decode by text type** (code, structured, chat, prose) and a legal benchmark.
- **Token-level fidelity**: KL divergence and top-1 agreement against the unquantized model.
- **Asynchronous scheduling on MRV2**: built and bitwise in D54R/D54A; MEASURED −0.085..−0.117 ms per round against
  synchronous MRV2, no verdict run. It needs its own serving profile; not in production.
- **MRV2 at 32K**: the decode round there is slower than on V1 (see D55); a device trace of the block-table gather and
  padding comes first.
