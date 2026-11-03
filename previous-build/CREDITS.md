# Credits

This deployment is mostly other people's work, configured, measured and patched in a few places. Every project below
is credited where its code or ideas are used. If you build on this repository, please credit them too. If we have
missed or misdescribed anyone's contribution, please open an issue and we will correct it.

## Model

- **DeepSeek** ([deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017),
  MIT): the model, the DSpark speculative drafter and the Engram design and tables. The two Engram shards we load
  (`model-00047/00048-of-00048.safetensors`) come from revision `1bae0e10`.
- **Phil Tompkins** ([philbert440](https://github.com/philbert440)):
  [DeepSeek-V4.1-Flash-1017-EXL3-franken-v100](https://huggingface.co/philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100)
  @ `99d85a46`, the EXL3 pack we serve, with its per-expert donor choice and the official DSpark blocks. Every quality
  number here is, in substance, a measurement of that pack.

## Engine and launcher

- **Phil Tompkins** ([philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100), Apache-2.0):
  the engine, the V100 launcher (`v100/serve_ds41.sh`), the SM70 kernels (EXL3 MoE, fused indexer, attention, the
  custom all-reduce), resident and NVMe Engram, the DSpark integration, and the design note for the persistent MoE
  prefill kernel whose first step our patch 0003 implements. Tag `ds41-vision-20261025b`, commit `23cec6a9`.
- **1CatAI** ([1CatAI/1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM), Apache-2.0): the SM70 vLLM fork the engine is
  built on, and the pull requests and issues our [survey](docs/survey.md) reviews.
- **vLLM** ([vllm-project/vllm](https://github.com/vllm-project/vllm), Apache-2.0): the serving engine underneath.
- **turboderp** ([turboderp-org/exllamav3](https://github.com/turboderp-org/exllamav3), MIT): the EXL3 format and
  trellis coding.
- **NVIDIA CUTLASS** (BSD-3-Clause): headers used to build `_C`; not vendored.

## Ideas and measurements we borrowed

- **DGX sPLIce** ([our sister deployment](https://github.com/ProprietaryLegal/DGX-sPLIce-DeepSeek-V4.1-Flash-2xDGX-Spark-2xRTX3090-drafter-x86-offload)):
  the gate set, the warm-up that `tools/warmup.py` ports, the persistent prefix tier design, and several survey items.
- The upstream authors cited in [docs/survey.md](docs/survey.md): 1Cat contributors (including squibloads for #1335),
  Brontir's NInferno (#166), lxe's volta, Mia-AiLab's EAQ build, and the authors of the papers listed there.
