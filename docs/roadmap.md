# Roadmap and test queue

Status on 2026-11-03. The queue runs one test at a time on the production host; each test boots its own arms and
restores the production stack when it finishes. Nothing here is a result until its row says so.

## Done today (adopted)

D1-D34R: the levers in [levers.md](levers.md#adopted), last of all the expert-kernel instruction diet (D34, −0.871 ms per
round) and the router floor (D34R, inconclusive, kept as upstream-backed).

## In the queue

| # | test | patch | what decides it | status |
|---|---|---|---|---|
| D35 | Prefill skip, `PREFILL_SKIP_ROWS=3072` | [T01](../engine/in-testing/T01-prefill-skip.patch) | identical output; first-token time at 32K/150K/300K | first repetition MEASURED: −8.6/−20.4/−31.3 %, identical; second repetition running |
| D36 | TP8 feasibility probe | [T05](../engine/in-testing/T05-tp8-probe.patch) | P2P on 32 cross-board pairs, kernels, 8-way all-reduce; go only if the modeled round is ≤ 22.0 ms | pre-test ESTIMATE: no-go |
| D37 | Prefill profile + ABBA of indexer overlap, 16,384-token chunks, token-blocked mixing | – | ABBA on first-token time | queued |
| D38 | Adopt the larger GPU hot ring, `KV_HOT_POSITIONS=524288` | – | KV pool ≥ 2,000,000 tokens; repeat-prompt identity | A/B MEASURED won (300K −1.09 ms, 150K −0.25); adoption check queued |
| D39 | Second-version harness: re-record greedy references, A/A spread, decode-only metric cross-check | – | three identical greedy runs | queued |
| D41 | V1 async scheduling on PP2 with a request-end guard | – | ABBA, soak, depth 2K/32K; report only | queued |
| D42 | Two requests at once, `MULTI_SEQ` | [T07](../engine/in-testing/T07-multi-seq-two-requests.patch) | bitwise; no single-request regression; scheduling policy sweep | ESTIMATED ~1.85x combined at two requests |
| D43 | Env-only switches: dense tiling, CPU pinning, chunk 4,096 vs 8,192 | – | v2 harness ABBAABBA | queued |
| D44 | All-reduce push path for V4.1's message size, `SUM2_PUSH_ANY` | [T03](../engine/in-testing/T03-allreduce-sum2-push.patch) | v2 ABBAABBA | ESTIMATED −0.08..−0.15 ms |
| D45 | Expert "wave" down kernel, `EXPERT_WAVE` | [T06](../engine/in-testing/T06-expert-wave-v41k.patch) | GPU bitwise checks, sanitizers, v2 ABBAABBA | ESTIMATED −0.3..−0.8 ms |
| D46 | Thinking-mode acceptance: probabilistic drafts, sharded; draft temperature 1.2 / 0.85 | [T04](../engine/in-testing/T04-psample-shard.patch) | T=1 acceptance and ms/round | queued |
| D47 | Split-K tensor-core decode attention, `ATTN_HMMA=2` | – | near-tie numerics gate, v2 ABBA | queued |
| D40 | Four-card fork smoke on one board | [forks/](../forks/1cat-4xv100-tp4/) | greedy identity, activation lines, sync vs async | queued last |

A side stream for the hyper-connection mixing step ([T02](../engine/in-testing/T02-mix-stream.patch), D33) did not reach
its A/B: its single-GPU check failed with a CUDA kernel error on 2026-11-03, so it was not deployed. It goes back to its
author for a fix.

## After the queue

- **Head-to-head benchmark against DGX sPLIce**: the same tools on both builds on the same day, including per-text-type
  decode (code, structured, chat, prose) and a legal benchmark.
- **Token-level fidelity**: KL divergence and top-1 agreement against the unquantized model, with DGX sPLIce's panels.
- **Long-context decode**: a register-tiled replacement for the indexer's scoring kernel, bitwise and behind a switch.
  ESTIMATED 1.3-2.0 ms per round at 150K, 2.7-4.2 ms at 300K, about 0.3 ms at every length.
- **1Cat's newer model runner (MRV2)**: parity with today's synchronous path first, then asynchronous rounds; a one-step
  lookahead design (not built) is where an ESTIMATED −1.2 to −1.8 ms per round would come from.
