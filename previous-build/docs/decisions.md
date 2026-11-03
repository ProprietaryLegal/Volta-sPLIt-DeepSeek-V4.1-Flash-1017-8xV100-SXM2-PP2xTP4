# Decisions

A digest of the architecture decision records we keep for the V100 deployment, in order. Each one records the options,
the choice and the evidence. Two records about scheduling other workloads that share the host are internal and not
summarised here.

| # | date | decision | why |
|---|---|---|---|
| 0002 | 2026-10-31 | Engram tables read from NVMe through the page cache, not resident | The host had 196 GiB of RAM at first install; resident tables need ~241 GiB available. Superseded by 0011. |
| 0003 | 2026-10-31 | CUDA 12.8 toolkit installed beside 12.6; the system default stays 12.6 | The wheel needs CUDA 12.8 at runtime (Engram reader, TileLang JIT) and gcc-14 (UPSTREAM); other model servers and builds on the host use the 12.6 default. The launcher sets `CUDA_HOME=/usr/local/cuda-12.8`, `CC=gcc-14`, `CXX=g++-14`. Guard: R580 is the last driver branch for Volta, and CUDA 13 drops sm_70, so no upgrade may move the host past R580 / CUDA 12.x. |
| 0004 | 2026-10-31 | Launcher host tuning off; single NUMA node | The launcher's tuning locks clocks at 1530 MHz and changes the CPU governor, against the host's power and clock ceiling. The host has one NUMA node, so [patch 0001](../patches/0001-numa-single-node.patch) binds all ranks to node 0. |
| 0005 | 2026-10-31 | Maximum request 327,680 tokens, at most three sequences | More concurrent requests instead of 1M-token context; prefill speed was the same ([ML1](experiments.md#ml1-max-model-len-1048576-x-2-against-327680-x-3)). KV 927,004 at boot. |
| 0008 | 2026-10-31 | Clock cap lifted (boost toward 1530 MHz under the 180 W limit) | We lifted the 1425 MHz ceiling; power limits stayed. The Q0 baseline ran at these clocks. Superseded by 0009 the same evening. |
| 0009 | 2026-10-31 | One GPU board replaced, 1425 MHz cap restored, server held down for a DIMM fault | PCIe completion-timeout resets under load with uncapped clocks; a board with a burn mark at its power connection was removed; one memory channel reported uncorrected ECC errors at DDR4-3200. |
| 0010 | 2026-11-01 | Host memory at DDR4-2666; EDAC rule for every arm | At DDR4-2666 the same eight DIMMs pass three rounds of a 200 GiB x 5-pattern probe with 0 errors. Every number from this boot on carries the label "DDR4-2666, 1425 MHz cap, 180 W". Any new uncorrected error stops GPU work. |
| 0011 | 2026-11-01 | Production serves with RAM-resident Engram; every start takes a RAM handshake | [ER1](experiments.md#er1-engram-tables-resident-in-host-ram): cold 75K −41.4 %, greedy identical. Costs ~208 GiB of host RAM while up and ~241 GiB available at start. |
| 0012 | 2026-11-01 | Staged EXL3 MoE prefill in production through a rebuilt `_C` | [MP1](experiments.md#mp1-staged-exl3-moe-prefill-kernel): warm 75K −2.33 % (CI −3.15..−1.50), greedy identical. The rebuilt library is pinned by hash; rollback reinstalls the wheel's original. |

## Standing rules that came out of these

- **One change per restart.** Every arm is one restart with one change against the baseline, under the full gates
  ([method](method.md)).
- **Label the conditions.** Memory clock, clock cap and power limit go with every number.
- **EDAC before and after.** Any new uncorrected memory error keeps the server down.
- **The host's power and clock ceiling is set outside every experiment.** No experiment changes it; [CLK1](experiments.md#clk1-sm-clock-lock)
  is a proposal, not yet decided.
- **Never past R580 / CUDA 12.x** on this host (Volta support ends there).
