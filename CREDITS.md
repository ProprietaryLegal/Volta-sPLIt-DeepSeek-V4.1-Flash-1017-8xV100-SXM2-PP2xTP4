# Credits

Volta sPLIt is our build: the PP2 x TP4 port, the lever stack, the kernels, the harness and the measurements are PLI
Labs' work ([our upstream contributions](docs/upstream-contributions.md)). It stands on the projects below. Each is
credited where its code or ideas are used. If you build on this repository, please credit them too. If we have missed
or misdescribed anyone's contribution, please open an issue and we will correct it. Authors were checked on GitHub on
2026-11-03.

## Model and weights

- **DeepSeek** ([deepseek-ai/DeepSeek-V4.1-Flash-1017](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017),
  MIT): the model, the DSpark speculative drafter (served as released, FP8), the config and tokenizer, and the Engram
  design. Revision `1bae0e10`.
- **ISTA-DASLab** ([DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF),
  MIT): the GSQ-RCO quantization we serve, IQ2_XXS experts and IQ4_NL Engram, revision `ad1e8991`. The quality figures
  quoted on this page are theirs.
- **ggml** ([ggml-org/ggml](https://github.com/ggml-org/ggml), MIT): the GGUF container and the IQ quantization formats.

## Engine

- **1CatAI** ([1CatAI/1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM), Apache-2.0): the SM70 vLLM fork.
  - **yangzhuxinyzx**: [#1277](https://github.com/1CatAI/1Cat-vLLM/pull/1277), the DeepSeek-V4.1-Flash package for 4x
    V100 (512K packed KV, the `v41k` kernels, DSpark), which this build ports to two boards and extends; also
    [#183](https://github.com/1CatAI/1Cat-vLLM/pull/183) (probabilistic DSpark drafting, the reference for a test in our
    queue), [#344](https://github.com/1CatAI/1Cat-vLLM/pull/344) and [#1338](https://github.com/1CatAI/1Cat-vLLM/pull/1338).
  - **Peuqui**: [#1263](https://github.com/1CatAI/1Cat-vLLM/pull/1263) (do not resend a request's token history every
    decode step), which our keep-batch lever ports to the V1 runner under PP2; series patches #1344, #1345, #1294, #1293,
    #1273, #1282; and [#1221](https://github.com/1CatAI/1Cat-vLLM/pull/1221) (DSpark for the new model runner).
  - **squibloads**: issue [#1341](https://github.com/1CatAI/1Cat-vLLM/issues/1341) (stale hot-ring rows after a prefix
    hit) and its test design, which our hot-refill port and our prefix-cache tests follow; series patches #1328, #1325.
  - **Leonccaa** (#1304-#1309, #1314-#1318), **andrewleech** (#1319, #1320, #1321), **SabaTech-dev** (#1322),
    **elight** (#1300): open pull requests carried in our patch series (0003-0027) so the tree rebuilds exactly.
  - 1Cat main at `6db9c81` (series patch 0002).
- **vLLM** ([vllm-project/vllm](https://github.com/vllm-project/vllm), Apache-2.0): the serving engine underneath.

## Ideas we ported

- **TensorFold** ([Elevatormusic/TensorFold](https://github.com/Elevatormusic/TensorFold), Apache-2.0):
  [#25](https://github.com/Elevatormusic/TensorFold/pull/25), coupled sampled DSpark drafts, first ported in our DGX
  sPLIce work and adopted here; and the expert top-p pruning (0rand) we tested and did not adopt.
- **Phil Tompkins** ([philbert440/deepseek-v4.1-v100](https://github.com/philbert440/deepseek-v4.1-v100), Apache-2.0):
  the replay-rows design behind the prefill skip in testing; and the engine and EXL3 pack
  ([philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100](https://huggingface.co/philbert440/DeepSeek-V4.1-Flash-1017-EXL3-franken-v100))
  our previous build ran on ([previous-build/](previous-build/)). Its 1Cat pull request
  [#1243](https://github.com/1CatAI/1Cat-vLLM/pull/1243) (rivetphilbot) stacks on our #1031.
- **Dennis Vertzyas** ([dnv2003/v100-skinny](https://github.com/dnv2003/v100-skinny)): Volta kernel and bandwidth
  findings (the ~879 GB/s read ceiling). Cited and linked; no code copied.
- **DGX sPLIce** ([our sister build](https://github.com/ProprietaryLegal/DGX-sPLIce-DeepSeek-V4.1-Flash-2xDGX-Spark-2xRTX3090-drafter-x86-offload)):
  the plan fusion, router floor, coupled-draft sharding, gate set and benchmark tools.
- **NVIDIA**: compute-sanitizer (memcheck, racecheck, synccheck), run on every kernel change before its A/B.
