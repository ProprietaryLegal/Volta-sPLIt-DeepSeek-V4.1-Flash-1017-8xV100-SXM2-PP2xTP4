# engine/

| path | what it is |
|---|---|
| [production/0050-expert-diet.patch](production/0050-expert-diet.patch) | our expert-kernel instruction diet (`VLLM_V41_EXPERT_DIET`), on top of the 49-patch series |
| [production/0052-index-tiled.patch](production/0052-index-tiled.patch) | our tiled decode index scorer (`VLLM_V41_INDEX_TILED`) and its `v41idx` library, on top of 0051; adopted 2026-11-04 |
| [production/0051-prefill-skip.patch](production/0051-prefill-skip.patch) | our prefill skip (`VLLM_V41_PREFILL_SKIP_ROWS`), on top of 0050; adopted 2026-11-03 |
| [production/0053-index-fuse.patch](production/0053-index-fuse.patch) | our fused prefill index scorer (`VLLM_V41_INDEX_FUSE`) and its `v41pidx` library, on top of 0052; adopted 2026-11-04 |
| [production/0054-draft-mp-shard.patch](production/0054-draft-mp-shard.patch) | drafter projection sharding (`VLLM_V41_DRAFT_MP_SHARD`, on) and the bitwise FP8 drafter mat-vec (`VLLM_V41_DRAFT_GEMV2`, off) with its `v41draft` library, on top of 0053; adopted 2026-11-04 |
| [production/0055-mrv2.patch](production/0055-mrv2.patch) | our DeepSeek-V4.1 port of Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER`), on top of 0054; adopted 2026-11-04 |
| [in-testing/](in-testing/) | patches for the changes in the test queue; not production |
| [configs/](configs/) | serving profile, engine environment, start script, production lever set (`rec.env`) |

## Build the production engine

```bash
git clone https://github.com/1CatAI/1Cat-vLLM src-pp2 && cd src-pp2
git checkout 899e9ed33                      # the #1277 merge
bash ../forks/1cat-4xv100-tp4/tools/apply_series.sh .     # 49 patches; checks tree b0d692425297
git apply ../engine/production/0050-expert-diet.patch     # tree 4447483248bb (git write-tree after git add -A)
git apply ../engine/production/0051-prefill-skip.patch    # tree 32d4a9d9b0c1
git apply ../engine/production/0052-index-tiled.patch     # tree 4760febd4fe7
git apply ../engine/production/0053-index-fuse.patch      # tree 421c427444a4
git apply ../engine/production/0054-draft-mp-shard.patch  # tree 09cf8cc28b7b
git apply ../engine/production/0055-mrv2.patch            # tree e85291152ae9
(cd benchmarks/deepseek_v41/v41idx && TORCH_CUDA_ARCH_LIST=7.0 python build.py)   # v41idx.so
(cd benchmarks/deepseek_v41/v41pidx && TORCH_CUDA_ARCH_LIST=7.0 python build.py)  # v41pidx.so
# v41draft.so (benchmarks/deepseek_v41/v41draft) is only needed for DRAFT_GEMV2, which production leaves off
# vLLM: build into a venv with the pins in forks/1cat-4xv100-tp4/configs/requirements-venv.txt
# v41k: on the serving machine, against that venv's torch
cd benchmarks/deepseek_v41/v41k && TORCH_CUDA_ARCH_LIST=7.0 python build.py
```

`forks/1cat-4xv100-tp4/install.sh` automates the clone, series, venv, wheel and `v41k` steps for the 4-card profile; the
same tree serves the 8-GPU profile. Build `v41k.so` on the machine that serves: it is a torch C++ extension, and its ABI is
tied to the venv's torch.

## Where the 2026-11-04 patches come from

Each patch is a diff of the published tree before it against the files that production runs.

- **0053** comes from the deployed payload of our indexer kit (kit commit `2c6bc886b`). **0054** comes from the deployed
  payload of our drafter kit (kit commit `9df1b282f`). Both kits were built on the serving host's own work trees, so
  there is no public branch for them. Their GPU check scripts stayed with the kits and are not in the patches.
- **0055** is the 14 runtime files of our branch `v41pkg/mrv2skip1104` at `5b32a7675583`, which are the files that were
  deployed. The branch also holds 28 test and tool files, which are not included.
- MEASURED 2026-11-04: after 0053-0055, 25 of the 26 files they touch are byte-identical to the deployed files. The 26th,
  `v41pidx/build.py`, differs in one docstring line, where we replaced our host's name.

## The diet patch

The expert kernels were issue-bound (profiling: about 7 instructions per weight byte at decode, 0.46 issued per cycle).
The diet re-plans the IQ2/IQ1 unpack and dot-product instruction streams of `gate_up_fast` and `down_rows_fast`
(`v41k_diet.cuh`), selected by `VLLM_V41_EXPERT_DIET` (bit 1: gate/up, bit 2: down; production uses 3). With the switch
unset the old kernels run. The patch includes `expert_diet_check.py` (GPU bitwise check against the reference kernels)
and `diet_dectest.cpp` (host emulation of the decode). MEASURED 2026-11-03: ABBA average −0.871 ms per round; T=1 texts
11/11; greedy 7/8 plus one known near-tie; compute-sanitizer memcheck, racecheck and synccheck 0 errors.
