# Patches in testing

Not production. Each is in the 2026-11-03 test queue ([docs/roadmap.md](../../docs/roadmap.md)); results will be added
when its test finishes. Every switch defaults off.

| patch | switch | queue | applies to | what it is |
|---|---|---|---|---|
| `T01-prefill-skip.patch` | `VLLM_V41_PREFILL_SKIP_ROWS` | D35 | the series end tree (`b0d692425297`) | early prefill chunks skip stage-2 layers 21-39, which hold only 128-wide window rings, for rows they cannot reach. Design reference: philbert440/deepseek-v4.1-v100's replay rows |
| `T02-mix-stream.patch` | `VLLM_V41_MIX_STREAM` | D33 | series end | the hyper-connection mixing step on a side stream |
| `T03-allreduce-sum2-push.patch` | `VLLM_V41_SUM2_PUSH_ANY` | D44 | series end | admits V4.1's 61,440-byte MoE-sum message to the custom all-reduce push path |
| `T04-psample-shard.patch` | `VLLM_V41_PSAMPLE_SHARD` | D46 | series end | probabilistic drafts (as in 1Cat #183), sharded and graph-captured |
| `T05-tp8-probe.patch` | probe only | D36 | series end | a one-window feasibility probe of TP8 across both boards |
| `T06-expert-wave-v41k.patch` | `VLLM_V41_EXPERT_WAVE` | D45 | the `v41k/` directory after 0050 (paths relative to it) | a rolled, four-rows-per-block expert down kernel, bitwise by construction |
| `T07-multi-seq-two-requests.patch` | `VLLM_V41_MULTI_SEQ` | D42 | its own base, V41PKG `b9b0bc8e4` (before the #1341 refill, patch 0048); not the series end | per-request state split so two requests share the pipeline |

MEASURED 2026-11-03 with `git apply --check`: T01-T05 apply on the series end tree, T06 applies in the production `v41k/`
directory. T07 does not apply on the series end (it conflicts in `vllm/envs.py` and re-adds a test file 0048 added);
MEASURED: it applies on its own base `b9b0bc8e4`; it will be rebased if it is adopted.
