# Changelog

## 2026-11-01: second update

- KV hold-stress: three 314,728-token requests resident at once, peak KV use 71.5 %, 0 preemptions.
- Context sweep, prefix-cache refill, concurrency, decode beside a prefill and llama-benchy on production, with the
  synthetic-text and book-text decode rates kept apart.
- Prefix-cache identity check: cold runs are deterministic; warm in-memory hits are not always byte-identical (open
  finding, under investigation).
- Decode study: final estimate for the exact changes, 70 → ~65-66 ms per round (ESTIMATED); the sampler CUDA-graph
  idea is dropped.
- Still PENDING: server timing of the exact decode changes, the MoE host-sync fix, concurrent identity, expert-usage
  counters.

## 2026-11-01: first publication

- Master page for the V100 deployment: production configuration, every measurement, every experiment with its verdict,
  decision digest, upstream survey, method, KV capacity audit, hardware notes and roadmap.
- Patches 0001 (single NUMA node), 0002 (KV-experiment switches) and 0003 (staged EXL3 MoE prefill) with the 0003
  kernel harness; 0001, 0003 and the harness are byte-identical to the copies in deepseek-v4-flash-v100.
- Tools: `compare_speed.py` (with new CPU tests), `warmup.py` / `warmup.sh`, `proc_census.py`, `pin_io.py`,
  `check_data_boundary.sh`.
- Evidence: `evidence/2026-11-01-final/results.json` (every 2026-11-01 arm and production) and the earlier interim
  file, unchanged.
- Results finished on 2026-11-01: the decode-step profile (one stream, three streams, ~32K context) and the decode
  study; the MoE prefill kernel variants (timed on one card, no win); the persistent prefix tier port design; the 1Cat
  GLM survey.
- PENDING slots in docs/roadmap.md: server timing of the decode fusions, MoE host-sync fix, KV hold-stress, concurrent
  identity, context sweep and llama-benchy, the prefix tier's first check, expert-usage counters.

## Production history (for reference)

| date (UTC) | change |
|---|---|
| 2026-10-31 | First install at 1,048,576 x 2 (KV 1,055,580), Engram from NVMe |
| 2026-10-31 17:59 | 327,680 x 3 (KV 927,004) |
| 2026-10-31 19:03 | Clock cap lifted (uncapped boost under 180 W) |
| 2026-10-31 21:45 | 1425 MHz cap restored, one GPU board replaced, server held for a DIMM fault |
| 2026-11-01 00:36 | Back up at DDR4-2666 (baseline) |
| 2026-11-01 05:19 | Production: resident Engram + staged MoE prefill (rebuilt `_C`) |
