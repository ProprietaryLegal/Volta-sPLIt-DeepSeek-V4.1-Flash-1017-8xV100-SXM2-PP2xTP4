# Changelog

## 2026-11-03 (evening): post-move production baseline, prefill skip and hot ring adopted

- **Hero numbers are now MEASURED**: one production boot with all 17 switches, T=0 **119.0 tok/s**, T=1 **120.8 tok/s**
  (2.25 accepted drafts per round), decode-only 25.30 / 25.20 ms per round, greedy gate PASS. They replace the ESTIMATED
  ~118 / ~121.
- Hardware: one PCIe switch card moved; each of the four switches now has its own CPU root complex at Gen3 x16 (each
  GPU still x8 to its switch). Decode unchanged within noise; long-prompt first token about 2 % sooner (1-3 runs per
  side).
- Adopted: prefill skip `PREFILL_SKIP_ROWS=3072` (first token −20.6 % at 150K, −31.5 % at 300K, identical output; patch
  moved to `engine/production/0051-prefill-skip.patch`) and the 524,288-position GPU hot ring `KV_HOT_POSITIONS`.
  300K first token now 178.0 s (was 263.9 s).
- Did not work: TP8 across both boards (no-go), 16,384-token chunks, V1 async with a request-end guard (+1.678 ms per
  round), chunk 4,096 and dense tiling (near-tie gate), CPU pinning (+0.079 ms), side-stream mixing (parked); indexer
  overlap neutral; hot Engram in GPU memory sized and not built. Harness v2 published (A/A under 0.1 ms per round).
- Two requests at once: boot failed, and its boot diagnostic failed too; rolled back cleanly.
- Queue now: D44-D55 (all-reduce push path, expert wave kernel, thinking acceptance, tensor-core decode attention, tiled
  index scorer, shared-expert down, fused transition, prefill GEMM and index scorer, drafter sharding, MRV2 re-port,
  IQ1_M repack), then the concurrency switch, decode by text type and a legal benchmark.
- `evidence/queue-log.txt` refreshed through the post-move baseline.

## 2026-11-03: first publication

- Volta sPLIt production stack: PP2 x TP4 port of 1Cat-vLLM #1277 plus eleven adopted levers and the expert-kernel
  instruction diet. ~118 tok/s decode, thinking off (ESTIMATED from measured deltas); ~114 MEASURED before the diet;
  84.6-87.3 tok/s on the long-context benchmark's legal prompt, thinking high (MEASURED).
- Published: the 49-patch series and four-card fork, the production diet patch, seven patches in testing, serving
  configs, the A/B harness, the 2026-11-03 queue log, and our previous build's record under `previous-build/`.
- In testing: D35-D47 (see docs/roadmap.md). Next updates: after the current queue.
