# engine/

| path | what it is |
|---|---|
| [production/0050-expert-diet.patch](production/0050-expert-diet.patch) | our expert-kernel instruction diet (`VLLM_V41_EXPERT_DIET`), on top of the 49-patch series |
| [production/0051-prefill-skip.patch](production/0051-prefill-skip.patch) | our prefill skip (`VLLM_V41_PREFILL_SKIP_ROWS`), on top of 0050; adopted 2026-11-03 |
| [in-testing/](in-testing/) | patches for the changes in the test queue; not production |
| [configs/](configs/) | serving profile, engine environment, start script, production lever set (`rec.env`) |

## Build the production engine

```bash
git clone https://github.com/1CatAI/1Cat-vLLM src-pp2 && cd src-pp2
git checkout 899e9ed33                      # the #1277 merge
bash ../forks/1cat-4xv100-tp4/tools/apply_series.sh .     # 49 patches; checks tree b0d692425297
git apply ../engine/production/0050-expert-diet.patch     # tree 4447483248bb (git write-tree after git add -A)
git apply ../engine/production/0051-prefill-skip.patch    # tree 32d4a9d9b0c1
# vLLM: build into a venv with the pins in forks/1cat-4xv100-tp4/configs/requirements-venv.txt
# v41k: on the serving machine, against that venv's torch
cd benchmarks/deepseek_v41/v41k && TORCH_CUDA_ARCH_LIST=7.0 python build.py
```

`forks/1cat-4xv100-tp4/install.sh` automates the clone, series, venv, wheel and `v41k` steps for the 4-card profile; the
same tree serves the 8-GPU profile. Build `v41k.so` on the machine that serves: it is a torch C++ extension, and its ABI is
tied to the venv's torch.

## The diet patch

The expert kernels were issue-bound (profiling: about 7 instructions per weight byte at decode, 0.46 issued per cycle).
The diet re-plans the IQ2/IQ1 unpack and dot-product instruction streams of `gate_up_fast` and `down_rows_fast`
(`v41k_diet.cuh`), selected by `VLLM_V41_EXPERT_DIET` (bit 1: gate/up, bit 2: down; production uses 3). With the switch
unset the old kernels run. The patch includes `expert_diet_check.py` (GPU bitwise check against the reference kernels)
and `diet_dectest.cpp` (host emulation of the decode). MEASURED 2026-11-03: ABBA average −0.871 ms per round; T=1 texts
11/11; greedy 7/8 plus one known near-tie; compute-sanitizer memcheck, racecheck and synccheck 0 errors.
