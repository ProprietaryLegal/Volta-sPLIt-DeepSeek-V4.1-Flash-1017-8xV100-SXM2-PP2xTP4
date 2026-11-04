# Roadmap and test queue

Status on 2026-11-03, about 23:00Z. The queue runs one test at a time on the production host; each test boots its own arms and
restores the production stack when it finishes. Nothing here is a result until its row says so.

## Done today (adopted)

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

Details: [levers.md](levers.md), [measurements.md](measurements.md).

## In the queue

In order. Estimates are the lanes' figures before the test, labelled ESTIMATED; none is a result. D44-D47 ran on
2026-11-03/04 and none was adopted; their results will be added in the next update.

| # | test | patch | what decides it | expectation |
|---|---|---|---|---|
| D44 | All-reduce push path for V4.1's message size, `SUM2_PUSH_ANY` | [T03](../engine/in-testing/T03-allreduce-sum2-push.patch) | v2 ABBAABBA | ESTIMATED −0.08..−0.15 ms per round |
| D45 | Expert "wave" down kernel, `EXPERT_WAVE` | [T06](../engine/in-testing/T06-expert-wave-v41k.patch) | GPU bitwise checks, sanitizers, v2 ABBAABBA | ESTIMATED −0.3..−0.8 ms |
| D46 | Thinking-mode acceptance: probabilistic drafts, sharded; draft temperature 1.2 / 0.85 | [T04](../engine/in-testing/T04-psample-shard.patch) | T=1 acceptance and ms per round; report only | – |
| D47 | Split-K tensor-core decode attention, `ATTN_HMMA=2` | – | near-tie gate, v2 ABBA | – |
| D49 | FP16-packed shared-expert down kernel, `SHARED_DOWN` | – | near-tie gate, ABBAABBA | – |
| D50 | Fused layer transition without the early path, `FUSE_TRANSITION_NO_EARLY` | – | bitwise, ABBAABBA | ESTIMATED ~0.12 ms, under the win bar |
| D51 | Tensor-core prefill routed-expert GEMM, `PREFILL_IQ_GEMM` | – | near-tie gate; first token at 32K / 150K / 300K; report only | – |
| D52 | Fused prefill index scorer, `INDEX_FUSE` | – | bitwise; first token | ESTIMATED −5..−9 % at 150K, −8..−14 % at 300K |
| D53 | Drafter `main_proj` sharding + bitwise FP8 mat-vec, `DRAFT_MP_SHARD`, `DRAFT_GEMV2` | – | token-exact vs OFF, ABBAABBA | ESTIMATED −0.3..−0.5 ms together |
| D54 | 1Cat's newer model runner (MRV2), re-port after the D32 boot failure | – | parity with the synchronous path first | in build |
| D55 | Lookup-free IQ1_M expert repack in spare GPU memory | – | bitwise, ABBA | in build |
| D40 | Four-card fork smoke on one board | [forks/](../forks/1cat-4xv100-tp4/) | greedy identity, activation lines | queued |

Then: a concurrency on/off switch for production (two requests at once, when it boots).

## After the queue

- **Decode by text type** (code, structured, chat, prose) and a legal benchmark.
- **Token-level fidelity**: KL divergence and top-1 agreement against the unquantized model.
- **Asynchronous rounds on MRV2** (after D54's parity): a one-step lookahead design (not built) is where an ESTIMATED
  −1.2 to −1.8 ms per round would come from.
