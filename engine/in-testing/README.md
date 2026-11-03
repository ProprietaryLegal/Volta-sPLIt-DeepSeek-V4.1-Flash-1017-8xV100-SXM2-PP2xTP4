# Patches in testing

Not production. Each is in the 2026-11-03 test queue ([docs/roadmap.md](../../docs/roadmap.md)); results will be added
when its test finishes. Every switch defaults off.

| patch | switch | queue | applies to | what it is |
|---|---|---|---|---|
| `T02-mix-stream.patch` | `VLLM_V41_MIX_STREAM` | D33 (parked) | series end | the hyper-connection mixing step on a side stream; parked 2026-11-03 (micro-benchmark below the bar, topology check failed) |
| `T03-allreduce-sum2-push.patch` | `VLLM_V41_SUM2_PUSH_ANY` | D44 | series end | admits V4.1's 61,440-byte MoE-sum message to the custom all-reduce push path |
| `T04-psample-shard.patch` | `VLLM_V41_PSAMPLE_SHARD` | D46 | series end | probabilistic drafts (as in 1Cat #183), sharded and graph-captured |
| `T05-tp8-probe.patch` | probe only | D36 (no-go) | series end | a one-window feasibility probe of TP8 across both boards; no-go 2026-11-03 (modeled 24.65 ms per round against 22.0) |
| `T06-expert-wave-v41k.patch` | `VLLM_V41_EXPERT_WAVE` | D45 | the `v41k/` directory after 0050 (paths relative to it) | a rolled, four-rows-per-block expert down kernel, bitwise by construction |
| `T07-multi-seq-two-requests.patch` | `VLLM_V41_MULTI_SEQ` | D42 | its own base, V41PKG `b9b0bc8e4` (before the #1341 refill, patch 0048); not the series end | per-request state split so two requests share the pipeline |

The prefill skip (formerly T01) was adopted on 2026-11-03 and moved to
[../production/0051-prefill-skip.patch](../production/0051-prefill-skip.patch).

MEASURED 2026-11-03 with `git apply --check`: T01-T05 apply on the series end tree, T06 applies in the production `v41k/`
directory. T07 does not apply on the series end (it conflicts in `vllm/envs.py` and re-adds a test file 0048 added);
MEASURED: it applies on its own base `b9b0bc8e4`; it will be rebased if it is adopted.
