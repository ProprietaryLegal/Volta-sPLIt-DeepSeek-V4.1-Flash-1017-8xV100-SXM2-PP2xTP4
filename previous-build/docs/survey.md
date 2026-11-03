# Survey of upstream ideas (2026-11-01)

What we found in 1CatAI's 1Cat-vLLM, the Volta kernel projects, DGX sPLIce (our sister deployment) and the wider web
that might make this deployment faster, longer or more trustworthy, and what has happened to each idea since. Every
gain below is UPSTREAM or ESTIMATED unless marked MEASURED.

Baseline at the time of the survey (MEASURED, production): 75K first token 25.81 s cold / 25.75 s warm; decode
~41-42 tok/s single stream; 29.6 tok/s beside a cold 75K prefill; ~71.5 ms per verify round; KV 927,004 tokens.

## Ranked candidates and their status

| # | candidate | axis | evidence | status on this host |
|---|---|---|---|---|
| 1 | Audit reserved buffers (workspace, indexer prefill buffer) the way 1Cat [#1275](https://github.com/1CatAI/1Cat-vLLM/pull/1275) did | context | UPSTREAM: indexer buffer 1.29 GiB → 33 MiB at 262K; workspace 4 → 1 GiB | folded into the [KV capacity audit](kv-capacity.md); the pool is accepted as is |
| 2 | Profile the 71.5 ms verify round | decode | no breakdown of the round existed | **profiled**: the stages run one after the other (~29 + ~32 ms of kernels), routed MoE ~11 of 70 ms, small ops plus gaps about a third ([measurements](measurements.md#where-a-decode-step-goes-2026-11-01-profiled)); decode study done (not bandwidth-bound; exact decode changes **PENDING** server timing, [roadmap](roadmap.md)) |
| 3 | 1Cat [#1335](https://github.com/1CatAI/1Cat-vLLM/issues/1335): EXL3 grouped MoE kernel with 32 slots instead of 8 | prefill | UPSTREAM +28-29 % prefill on GLM-5.3 EXL3 (4x V100 TP4), bitwise equal | **does not apply**: every pass of 128+ tokens already takes the row-tiled kernel ([KMOE1](experiments.md#kmoe1-next-steps-for-the-moe-prefill-kernel)) |
| 4 | The engine's `VLLM_DS41_DECODE_LANE` switch (found while reading the source) | decode beside prefill | its docstring claims 2·max(s0, s1)/(s0 + s1) for the decoder | **not promoted**: no gain ([DLANE1](experiments.md#dlane1-engine-decode-lane-switch)) |
| 5 | Check that concurrent requests do not change each other's outputs (bugs like 1Cat [#1330](https://github.com/1CatAI/1Cat-vLLM/issues/1330), [#1331](https://github.com/1CatAI/1Cat-vLLM/issues/1331), [#1327](https://github.com/1CatAI/1Cat-vLLM/issues/1327)) | quality | the greedy gate runs one stream; UPSTREAM GLM-5.3: a live request's index keys were wiped under concurrent long prefills | those GLM code paths do not apply here (code reading); the test on our host is written, **PENDING** |
| 6 | Forced `tool_choice` probe | correctness | DGX sPLIce hit HTTP 500 on forced tool calls until a launch flag | passes here: `tool_choice=required` is in the 15 functional checks |
| 7 | The GPU that links at PCIe Gen3 x4 | hardware | MEASURED idle; never characterised | probe proposed ([hardware notes](hardware-notes.md)) |
| 8 | Small-M dense GEMMs at verify widths: 1Cat [#1273](https://github.com/1CatAI/1Cat-vLLM/pull/1273) (grouped `wo_a`, tuning freeze), [NInferno #166](https://github.com/Brontir/NInferno/pull/166) (Volta HMMA for T = 5-16) | decode | UPSTREAM −4 ms per decode step (59 → 55) on DeepSeek-V4; 34 → 23 ms per round on another model | profiled: dense GEMMs at verify width are ~15 ms of a 70 ms step; a #1273-style `wo_a` GEMM is ESTIMATED ~3 ms per round but not bit-exact, so it would need a quality measurement ([roadmap](roadmap.md)) |
| 9 | Draft depth 4 at three streams; re-judge adaptive depth with a near-tie rule | decode | DGX sPLIce and another local deployment preferred shallower drafts | adaptive depth lost on identity ([DEP1](experiments.md#dep1-adaptive-draft-depth-p_min)) |
| 10 | Draft spans copied from the prompt beside DSpark (suffix / prompt-lookup hybrid) | decode | UPSTREAM 2.4x (prompt lookup, summarisation), 2.8x (vLLM n-gram, CNN/DM) | an offline copy-rate estimate comes first |
| 11 | Persistent prefix tier that survives restarts | first token on repeated long prompts | DGX sPLIce: 150K-token prompt back in 2.58 s instead of 58.6 s, in production there | port design done, ESTIMATED 3.5-5 weeks ([MC1](experiments.md#mc1-persistent-prefix-tier)); first check: in-memory warm hits are not always byte-identical to cold (open finding) |
| 12 | Spend expert bits by measured routing frequency (lxe/volta tiers, EAQ, per-expert donor choice) | quality | UPSTREAM EAQ v1: KL 0.0137 against 0.01545 for another 2.9 bpw build (short context) | needs expert-usage counts first; changes numerics, so it is judged on quality, not identity |
| 13 | Long-prefill indexer epilogue and mHC row staging (1Cat [#1280](https://github.com/1CatAI/1Cat-vLLM/pull/1280), [#1325](https://github.com/1CatAI/1Cat-vLLM/pull/1325)) ported into the engine's own fused kernels | prefill at 150-327K | UPSTREAM −16.7 % / −22.2 % at 178K / 287K (epilogue alone); +7 % prefill (row staging) | only if the engine's fused kernels share the inefficiency; not checked |
| 14 | PP send overlapping the next eager step (1Cat [#1294](https://github.com/1CatAI/1Cat-vLLM/pull/1294)) | prefill | UPSTREAM −0.9..−3.9 % at PP2 | ESTIMATED ≤ 2 % at 75K (prefill is already pipelined), below the promotion bar |
| 15 | GLM-side optimisations in 1Cat that touch shared SM70 files | various | 38 GLM PRs and 17 issues read against the engine snapshot | **nothing large to pull**: the engine already has each one worth having; a small Triton-recompile fix is written, not measured ([roadmap](roadmap.md#1cat-glm-changes-that-may-port-done-2026-11-01-code-reading)) |

## Dead ends, with the reason

| candidate | why not here |
|---|---|
| 1Cat [#1263](https://github.com/1CatAI/1Cat-vLLM/pull/1263): skip resending token history under PP | the engine's scheduler already omits it when PP and async scheduling are both on; the PR targets the V2 runner |
| 1Cat [#1222](https://github.com/1CatAI/1Cat-vLLM/pull/1222): cuBLAS decode indexer above 131,072 tokens | a DeepSeek-V4 path; this engine runs its own fused decode indexer, and UPSTREAM decode is flat from 8K (51.0) to 128K (52.6 tok/s) |
| 1Cat [#1282](https://github.com/1CatAI/1Cat-vLLM/pull/1282): tensor-core Triton prefill routes | needs a patched Triton (stock Triton has no Volta tensor-core `tl.dot`) and targets paths this engine replaces; the opt-in commits alone gave −0.5..−0.8 % |
| 1Cat [#1279](https://github.com/1CatAI/1Cat-vLLM/pull/1279) and #1282's host all-reduce (TP over PCIe without P2P) | TP4 here is inside an NVLink board |
| 1Cat [#1276](https://github.com/1CatAI/1Cat-vLLM/pull/1276): lookahead block hashes for EAGLE / MTP prefix hits | DSpark is excluded; on DeepSeek-V4 it lowered DSpark acceptance with no TTFT gain |
| 1Cat [#1284](https://github.com/1CatAI/1Cat-vLLM/pull/1284): keep the all-reduce out-of-place by default | fixes a regression from #1277, which this engine predates |
| Issue [#1332](https://github.com/1CatAI/1Cat-vLLM/issues/1332): SM70 fp16 GEMM wrong in the last N % 32 columns | UPSTREAM: no engine impact (dense prep rejects N % 32 ≠ 0); keep in mind for any new dense shape |
| exllamav3 [#404](https://github.com/turboderp-org/exllamav3/pull/404): Volta EXL3 GEMV | matches the 1Cat path within noise (UPSTREAM); 1Cat's EXL3 kernels are already Volta-tuned |
| [lxe/volta](https://github.com/lxe/volta) as a whole engine | needs one 8-GPU NVLink mesh and ~400 GB RAM; this host is two NVLink quads over PCIe with ~251 GiB. UPSTREAM fidelity KL 0.127 / 84.1 % same-token against franken's KL 0.0358 / 95.79 % (different references and panels, but a large gap) |
| Quantized K cache below the engine's format | our own [V4 Flash notes](https://huggingface.co/ProprietaryLegal/DeepSeek-V4-Flash-V100/blob/main/RESEARCH-NOTES.md): q8_0 K produced fluent nonsense with healthy HTTP 200s (llama.cpp); f16 KV was also faster |
| NCCL tuning for the PP hop | ESTIMATED < 0.2 % per round: a few hidden-state rows per round; a prefill chunk's ~8 MB is noise against a ~330 ms chunk |
| vLLM CPU KV offload / LMCache | gains are throughput beyond HBM at high concurrency; this host runs at most 3 sequences with ~38 GiB host RAM free under resident Engram |
| Approximate speculative decoding | lossy by design; fails the greedy-identity gate |
| Packed FP4 KV with a GPU hot ring (1Cat [#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277)) | designed for GGUF / TP4 expert offload; little host RAM to spare here |
| Tree verification for the DeepSeek-V4 drafter (arXiv 2609.24698) | no code; research watch only |
| 1Cat issue [#1336](https://github.com/1CatAI/1Cat-vLLM/issues/1336): sampler host sync | ESTIMATED ≤ 0.2 % at 71.5 ms rounds; not worth a restart |
| CUDA 13 or a driver past R580 | CUDA 13 drops sm_70 and R580 is the last Volta branch; no speed claim found for 12.9 |

## Hardware asks that came out of the survey

- Probe, then inspect or reseat, the GPU that links at Gen3 x4.
- One 10 GbE link to the host with the RTX 3090s, which clears the first blocker of the remote drafter
  ([DR1](experiments.md#dr1-rtx-3090-drafter-host)).
- Keep watching a GPU that dropped off the bus in earlier records and is clean today.
