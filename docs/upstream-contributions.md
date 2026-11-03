# Our upstream contributions

Pull requests we wrote for upstream projects, with authorship checked on GitHub on 2026-11-03 (`gh pr list --author`).
"PLI Labs (founder)" marks pull requests opened from the personal GitHub account of PLI Labs' founder;
"ProprietaryLegal" is PLI Labs' organization account. Work by
other people that this build uses is in [CREDITS.md](../CREDITS.md), not here.

## 1CatAI/1Cat-vLLM

| PR | author | state | title |
|---|---|---|---|
| [#651](https://github.com/1CatAI/1Cat-vLLM/pull/651) | ProprietaryLegal | **merged** 2026-09-26 (opened 2026-09-17) | [Model][SM70] Accept DFlash embed replica across split load_weights calls |
| [#1031](https://github.com/1CatAI/1Cat-vLLM/pull/1031) | PLI Labs (founder) | open (2026-10-07) | [Model][SM70] DeepSeek-V4.1-Flash on V100: PP3xTP4 (12 GPUs, 256K) and PP2xTP4 (8 GPUs) |
| [#1030](https://github.com/1CatAI/1Cat-vLLM/pull/1030) | PLI Labs (founder) | open (2026-10-07) | [Kernel][SM70] Generalise the MXFP4 MoE geometry and add skinny split-K 4/6/9/12/18 |
| [#1021](https://github.com/1CatAI/1Cat-vLLM/pull/1021) | PLI Labs (founder) | open (2026-10-07) | [Kernel][SM70] Keep 32x32 UE8M0 block-FP8 dense weights in FP8 on Volta |
| [#100](https://github.com/1CatAI/1Cat-vLLM/pull/100) | PLI Labs (founder) | closed, not merged (2026-07-10) | Fix GPTQ/compressed-tensors WNA16 on sm_70 (V100): auto-detect Volta Marlin, actionable errors |
| [#96](https://github.com/1CatAI/1Cat-vLLM/pull/96) | PLI Labs (founder) | closed, not merged (2026-07-03) | sm70/V100: fail loudly when torch<2.10 skips _C_stable_libtorch; tolerate UUID-form CUDA_VISIBLE_DEVICES; add sm_70 build guide |

### What each one does, and what it means for this build

- **#1031: DeepSeek-V4.1-Flash on V100 from the official checkpoint.** A new `vllm/models/deepseek_v41/` package with
  SM70 code: 12 GPUs as PP3 x TP4 (up to 256K) and 8 GPUs as PP2 x TP4; FP32 hyper-connection math; FP16 records that
  hold the model's QAT values exactly; MXFP4 experts on skinny kernels; Engram rows read in place from the checkpoint;
  only legal stage cuts accepted (20 for PP2). It worked out the multi-board pipeline layout, the split at layer 20 and the stage contract that this build's PP2 x TP4 port of #1277 follows. Its
  branch is at [ProprietaryLegal/1Cat-vLLM](https://github.com/ProprietaryLegal/1Cat-vLLM/tree/feat/deepseek-v41-sm70);
  patches, launch scripts and results at [ProprietaryLegal/deepseek-v4.1-flash-sm70](https://huggingface.co/ProprietaryLegal/deepseek-v4.1-flash-sm70).
- **#1030: MXFP4 MoE geometry and skinny split-K.** Lets the SM70 MXFP4 MoE path accept V4.1's expert geometry instead of
  only V4's. Part of the native-weights route (#1031 is stacked on it). This build serves the GGUF route, so it does not
  run this code.
- **#1021: block-FP8 dense weights kept in FP8 on Volta.** An opt-in FP8 group-32 path for V4.1's 32 x 32 UE8M0 dense
  weights. Native-weights route; not used here. Kernels and measurements:
  [ProprietaryLegal/sm70-fp8-block32-kernels](https://huggingface.co/ProprietaryLegal/sm70-fp8-block32-kernels).
- **#651 (merged): DFlash embedding replica across split `load_weights` calls.** An SM70 drafter-loading fix, merged into
  1Cat-vLLM and so part of the engine this build runs on.
- **#96 and #100 (closed):** early V100 build and quantization fixes. Not merged; listed for completeness.

## In this repository

Our own engine work for this build is published here rather than upstream so far: the PP2 x TP4 port of #1277 and the
lever stack ([forks/1cat-4xv100-tp4/](../forks/1cat-4xv100-tp4/), patches 0001 and 0028-0049; a few are our ports of
other people's designs, credited per lever in [levers.md](levers.md)), the expert-kernel diet
([engine/production/](../engine/production/)) and the changes in testing ([engine/in-testing/](../engine/in-testing/)).
Patches 0002-0027 of the series are other people's upstream work (1Cat main and open PRs), carried so the tree rebuilds
exactly; they are credited in [CREDITS.md](../CREDITS.md).

## v100-skinny

[dnv2003/v100-skinny](https://github.com/dnv2003/v100-skinny) is Dennis Vertzyas' work (its only contributor), with no
licence file. It is not ours: we cite its Volta bandwidth and kernel findings and link to it, and copy none of its code.
The ProprietaryLegal account holds a mirror of it for reference.
