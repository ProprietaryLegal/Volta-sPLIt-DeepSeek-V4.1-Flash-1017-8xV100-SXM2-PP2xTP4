# KV capacity: what "927,004 tokens" means

Offline audit of the production boot log (2026-11-01, KV 927,004, "maximum concurrency for 327,680 tokens per request:
2.83x"), plus a hold-stress run on production (below). Labels: MEASURED (read from the boot log, or measured in
the hold-stress), DERIVED (computed from logged values and the engine's allocation rules), ESTIMATED (a model, not
measured).

## Summary

- The pool is accepted as is for production. It is not a gate, and no restart is spent on growing it.
- **MEASURED 2026-11-01: three 314,728-token requests resident at once peaked at 71.5 % of the pool, with 0
  preemptions** (~960K tokens resident). The largest load production accepts, 3 x 327,680 = 983,040 tokens, would use
  ~73 % (ESTIMATED). Real capacity is ESTIMATED at ~1.34-1.47M tokens, in line with the ~1.43M paper estimate below.

## Why the boot-log number understates capacity

- **The binding rank is a stage-1 rank (the second pipeline stage; 7,279 blocks), not rank 0.** The "Available KV cache memory 1.62 GiB" line in
  the log is the first rank's. Ranks differ because whole experts are placed per rank: free KV plus expert bytes agree
  within 0.07 GiB across stage 1 (MEASURED / DERIVED from the boot log).
- **Each request is charged 2,573 blocks:** 1,280 compressed blocks plus a 1,293-block sliding-window reserve
  (cdiv(127 + 2 x max_num_batched_tokens, 32) + 1 = 69 pages per group). DERIVED; it reproduces the logged figure on
  three boots.
- **Three requests never all use that reserve at once**, so 3 x 327,680 peaks at about 5,358 of 7,279 blocks (74 %),
  ESTIMATED.
- Before the hold-stress below, no stress run had held all three at full length at once: prefills are serial and
  stress outputs are 256 tokens. Peak use was 50 % in production's stress run.

## Earlier attempts to grow the pool

| arm | change | KV tokens | why not promoted |
|---|---|---:|---|
| GMU1-p | CUDA-graph memory estimate off | 1,194,319 (3.64x) | +9-13 % per verify round |
| GMU1-t | capture list `[1..12,16,18]`, utilisation 0.945 | 936,683 (+1.0 %) | greedy 12 / 16 identical + 4 near-ties |
| PC1 | prefill chunk 2,048 | 385,363 | the pool shrank |

## Options scoped but not run (ESTIMATED)

| option | expected pool | note |
|---|---:|---|
| utilisation 0.947 | ~1,011,700 | above the launcher's 0.945 cap |
| prefill chunk 768 | ~1.05-1.13M | smaller sliding-window reserve; prefill speed to measure |
| RoPE cache host-pinned | +822 blocks | engine change |
| PP layer rebalance 19 / 21 | ~110-170K (the pool shrinks) | rejected: one layer moves ~1.1-1.2 GiB per rank against a 0.06-0.16 GiB gap between stages, so the receiving stage runs out |
| PP layer rebalance 21 / 19 | ~130-190K (the pool shrinks) | rejected for the same reason; keep 20 / 20 |
| drafter on its own GPU, 20 / 20 | ~947.8K (+20.8K) | stage 0 then binds; needs a drafter-placement feature the engine does not have |
| drafter on its own GPU, 19 / 21 | ~1.4-1.6M | same feature, plus a PCIe hop for hidden states every verify round |

## The measurement (2026-11-01)

Requests only, no restart: three ~315K-token synthetic prompts (temperature 0, thinking off, fresh salts,
`ignore_eos`, 12,000 output tokens each), so that all three are resident when the last prefill ends. Metrics are
sampled every two seconds: peak `kv_cache_usage` (maximum across replicated PP / TP gauges), running / waiting gauges,
preemptions. Predicted: 72-76 % peak use, 0 preemptions. A run that never shows all three running after the last
prefill is inconclusive. If peak use stays below 100 %, the run shows the workload fits; it does not give a saturation
ceiling, because compressed and sliding-window allocation make linear extrapolation unreliable.

**Result (MEASURED, 2026-11-01 09:56-10:10 UTC, production).**

- Three requests of 314,728 prompt tokens each (944,184 in all), all three running together after the last prefill:
  yes. 0 preemptions, 0 HTTP errors.
- Peak KV use 71.5 % (the engine's `kv_cache_usage_perc`), 654 s into the run, with three running and the third
  prefill 4 s from done. Resident tokens at the peak: ~325K + ~322K + ~313K = ~960K (DERIVED from each request's
  first-token time and mean decode rate).
- The full 983,040-token load would use ~73 % (ESTIMATED), with no preemption.
- Real capacity (ESTIMATED): ~1.34M tokens by straight-line scaling (960K / 0.715), ~1.47M from the slope between the
  one-request sample (30.6 % at 80 s) and the peak. The paper estimate above was ~1.43M. The boot-log 927,004 figure
  under-counts real capacity, as the audit predicted.
- The run did not saturate the pool, so it gives a lower bound (at least ~960K resident), not the ceiling. Reaching
  100 % would need more than three concurrent requests, which production does not allow.
