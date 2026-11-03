# Hardware notes (observed on this one host)

These are observations about our host, not claims about the engine or about V100s in general.

## The host

| | |
|---|---|
| GPUs | 8x V100-SXM2-32GB on two NVLink quad boards; TP4 inside a board over NVLink, the PP hop between boards over PCIe |
| CPU | AMD Ryzen Threadripper PRO 3945WX, 12 cores / 24 threads, one NUMA node |
| Memory | 8 x 32 GB DDR4 RDIMM, run at DDR4-2666 (MemTotal ~251 GiB); 196 GiB before the 2026-10-31 upgrade |
| Power and clocks | 180 W limit per card; graphics clock capped at 1425 MHz (a host setting; no experiment changes it) |
| Driver / toolkit | NVIDIA 580.159.03 (R580, the last branch with Volta support); CUDA 12.8 beside the system's 12.6 |

## PCIe completion-timeout resets

Two host resets left ACPI BERT records of a fatal PCIe error at the root port that feeds a GPU board, AER uncorrectable
status `0x00004000` (Completion Timeout): on 2026-10-22 (180 W limit, clocks up to 1477 MHz) and on 2026-10-31 (180 W
limit, SM clocks uncapped). Two more resets that evening (one after a hang) left no BERT record.

Per-card `power.draw` readings above the 180 W limit were seen with uncapped clocks (192-232 W, 1 Hz, 2026-10-31) and
also under the 1425 MHz cap (196-217 W on earlier days; 196-212 W in 500 ms samples during the 2026-11-01 baseline arm;
206.8 W peak during the production stress run). Our inference, not proven: a board stops answering on its PCIe link
under load transients.

A GPU board whose motherboard power connection showed a burn mark was taken out of the host on 2026-10-31, and the
1425 MHz cap was restored. Since the 2026-11-01 boot (1425 MHz cap, 180 W) no reset has occurred through every arm and
production.

## Uncorrected DDR4 ECC errors, mitigated by a lower memory clock

At DDR4-3200, one DIMM channel reported four uncorrected ECC errors on 2026-10-31: three during the first load of the
392 GiB checkpoint (two workers were killed with SIGBUS and the engine failed to start) and one in a CPU-only 110 GiB
memory probe. With the memory clock set to DDR4-2666 (same DIMMs), three rounds of a 200 GiB x 5-pattern probe passed
with 0 mismatches and EDAC 0 UE / 0 CE, and EDAC stayed at 0 / 0 through every 2026-11-01 arm and the production start.
The DIMM was not replaced; the lower clock is a mitigation. Host-memory bandwidth at DDR4-2666 is up to ~17 % lower
(ESTIMATED from the transfer rate), so resident-Engram and other host-memory numbers are not comparable with DDR4-3200
ones.

Rule since then: EDAC `ue_count` / `ce_count` before and after every arm and every start; any new uncorrected error
keeps the server down.

## One GPU links at PCIe Gen3 x4

At idle, one GPU on the second board reports a PCIe Gen3 x4 link where the others report x8, with 0 replays (MEASURED,
2026-11-01). Its effect on the PP hop or on the boot-time checkpoint stream has not been probed. A pinned host-to-device
and device-to-host bandwidth test per card, and an inspection or reseat, are proposed.

## Memory pressure under resident Engram

With ~208 GiB held by the server, ~32-40 GiB is left for everything else on the host. Swap grew by ~4.7 GiB in the
first hour, all of it other services' pages and idle worker heap, none of it the table mappings (see
[production](production.md#memory-note-measured-2026-11-01)). A workload that needs more than what is left will push
more into swap; we watch MemAvailable every 15 s.
