# Production: exactly what serves

As of 2026-11-01 05:19 UTC (the final start of the 2026-11-01 optimization round). Every value below is MEASURED from
that boot's log or read from the deployed configuration, unless labelled otherwise.

## Pin

| | value |
|---|---|
| Engine | [philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100) tag `ds41-vision-20261025b`, commit `23cec6a9fcd1d8face54c178fced8b4300628ae5` |
| Wheel | `1cat_vllm-1.5.2.dev1149+ds41vision1025b` (prebuilt SM70), with `vllm/_C.abi3.so` replaced by our rebuild that contains [patch 0003](../patches/0003-mp1-exl3-tiled-smem-staging.patch) |
| Patches | [0001](../patches/0001-numa-single-node.patch) single NUMA node; [0002](../patches/0002-gmu1-cudagraph-sizes-and-profiler-switch.patch) KV-experiment switches (inert unless set); [0003](../patches/0003-mp1-exl3-tiled-smem-staging.patch) staged MoE prefill (in the rebuilt `_C`) |
| Weights | [philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100](https://huggingface.co/philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100) @ `99d85a46`, 92 files |
| Engram | DeepSeek's `model-00047/00048-of-00048.safetensors` from `deepseek-ai/DeepSeek-V4.1-Flash-1017` @ `1bae0e10` |
| Layout | PP2 x TP4: stage 0 on one NVLink quad board, stage 1 on the other, pinned by GPU UUID; 20 + 20 layers |
| Drafter | DSpark, in the pack; k = 5 |
| Context | 327,680 tokens per request (prompt + output) |
| Concurrency | at most 3 sequences |
| KV pool | 927,004 tokens; "maximum concurrency for 327,680 tokens per request: 2.83x" (boot log) |
| Batched tokens | `--max-num-batched-tokens 1024`; prefix caching on |
| Engram | RAM-resident: 4 x 45.78 GiB, one table set per stage-0 rank, loaded in 24.9-33.8 s per rank; MemAvailable 242.6 GiB before the load and 36.9 GiB after |
| MoE prefill | staged EXL3 tiled kernel on: `VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1` |
| NUMA | all ranks on node 0 (the host has one) |
| Host tuning | off (`DS41_HOST_TUNING=0`): no launcher clock lock, no CPU governor change |
| Clocks and power | 1425 MHz graphics-clock cap, 180 W per card; set outside the launcher |
| Host memory | 8 x 32 GB at DDR4-2666; EDAC 0 / 0 at start |
| Toolkit | CUDA 12.8 beside the system's 12.6 (`CUDA_HOME=/usr/local/cuda-12.8`), gcc-14 / g++-14 |
| API | OpenAI-compatible, served name `deepseek-v4.1-flash`, port 8000 |
| Thinking | off by default; `chat_template_kwargs: {"thinking": true}` turns it on (upstream chat template) |

## Environment, on top of the engine's defaults

```bash
export DS41_SERVED_NAME=deepseek-v4.1-flash DS41_PORT=8000
export DS41_GPUS_A="<four UUIDs of board 1>" DS41_GPUS_C="<four UUIDs of board 2>"
export CUDA_HOME=/usr/local/cuda-12.8 CC=gcc-14 CXX=g++-14
export VLLM_DS41_ENGRAM_RESIDENT=1
export VLLM_DS41_MOE_EXL3_PREFILL_SMEM=1
export DS41_HOST_TUNING=0
export DS41_MAX_MODEL_LEN=327680
export DS41_MAX_NUM_SEQS_OVERRIDE=3
```

Everything else is the engine launcher's default (`v100/serve_ds41.sh`), including `VLLM_DS41_PP_PREFILL_PIPELINE=1`,
the prefill kernel switches and their thresholds (`..._PREFILL_MIN_TOKENS` 128, `..._PREFILL_CHUNK` 1024,
`PREFILL_DENSE_MIN` 160), and synchronous scheduling.

## Gates passed at the final start (MEASURED, 2026-11-01 05:19-06:07 UTC)

| gate | result |
|---|---|
| greedy check against the baseline's references | 16 / 16 byte-identical, 0 near-ties |
| functional API checks | 15 / 15 |
| private task suite | same score as the baseline (41 of 46 both; nothing lost or gained) |
| 75K first token, cold / warm (seeds 190-195) | 25.81 s / 25.75 s (baseline 46.00 / 27.02) |
| decode beside a cold 75K prefill (seed 36) | 37.8 → 29.6 tok/s, longest gap 0.62 s; that prefill 50.6 s |
| 3 x ~300K stress (seed 58) | 3 / 3, wall 355.5 s, 0 preemptions, peak KV 50 %, max card power 206.8 W, lowest host MemAvailable 37.7 GiB |
| thinking on, warm (seeds 196-201) | first token 26.01 s, decode 31.44 tok/s, 71.84 ms per round |
| EDAC | 0 UE / 0 CE before and after |

## Start requirements

- **Host RAM.** The engine refuses a stage-0 rank unless its tables plus 32 GiB are available, so a resident start on
  this ~251 GiB host needs about **241 GiB available with the server stopped**. Other workloads on the host must give
  that memory back before a start; we use a small request / go / loaded handshake with them.
- **EDAC.** Read the memory controller's `ue_count` / `ce_count` before and after every start. Any new uncorrected
  error keeps the server down ([hardware notes](hardware-notes.md)).
- With the server up, ~208 GiB stays held (tables 4 x 45.78 = 183.1 GiB plus the server), leaving ~32-40 GiB for
  everything else on the host.

## Memory note (MEASURED 2026-11-01)

With the resident server up, swap grew from 1.46 GiB to 6.2 GiB over the first hour: +2.2 GiB during the table load,
+2.1 GiB when other workloads resumed, +0.3 GiB during a full checkpoint verification (390 GB of reads). The swapped
pages belonged to other services and to idle worker heap; none were in the table mappings (`smaps`), and the
out-of-memory killer never ran. The production speed cells read cold = warm (25.8 s), so the tables did not page.

## Rollback

With the server stopped:

- **Staged MoE prefill off:** reinstall the wheel's original `_C.abi3.so` and unset `VLLM_DS41_MOE_EXL3_PREFILL_SMEM`.
- **Resident Engram off:** `VLLM_DS41_ENGRAM_RESIDENT=0`. No RAM requirement; cold 75K first token goes back to ~46 s.

## History

| date (UTC) | change |
|---|---|
| 2026-10-31 | First install at the upstream defaults, 1,048,576 tokens x 2 sequences (KV 1,055,580); Engram from NVMe, because the host then had 196 GiB of RAM. |
| 2026-10-31 17:59 | Restarted at 327,680 x 3 (more concurrent requests; the shorter context did not change prefill speed). |
| 2026-10-31 19:03 | Clock cap lifted (uncapped boost under 180 W); the Q0 baseline ran at these clocks. |
| 2026-10-31 21:45 | Clock cap restored to 1425 MHz after PCIe resets; one board replaced; server held down for a DIMM fault. |
| 2026-11-01 00:36 | Back up with the memory at DDR4-2666; same configuration (the baseline used by every 2026-11-01 arm). |
| 2026-11-01 05:19 | Production: resident Engram + staged MoE prefill on the rebuilt `_C`. |
