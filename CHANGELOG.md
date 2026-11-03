# Changelog

## 2026-11-03: first publication

- Volta sPLIt production stack: PP2 x TP4 port of 1Cat-vLLM #1277 plus eleven adopted levers and the expert-kernel
  instruction diet. ~118 tok/s decode, thinking off (ESTIMATED from measured deltas); ~114 MEASURED before the diet;
  84.6-87.3 tok/s on DGX sPLIce's benchmark, thinking high (MEASURED).
- Published: the 49-patch series and four-card fork, the production diet patch, seven patches in testing, serving
  configs, the A/B harness, the 2026-11-03 queue log, and our previous build's record under `previous-build/`.
- In testing: D35-D47 (see docs/roadmap.md). Next updates: after the current queue, with the head-to-head benchmark
  against DGX sPLIce.
