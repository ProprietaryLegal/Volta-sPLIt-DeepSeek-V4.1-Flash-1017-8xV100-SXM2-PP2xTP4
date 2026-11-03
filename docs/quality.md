# Quality

## The weights

DeepSeek-V4.1-Flash-1017 as released has FP8 dense weights and FP4 routed experts. This build serves ISTA-DASLab's
GSQ-RCO GGUF pack ([model card](https://huggingface.co/ISTA-DASLab/DeepSeek-V4.1-Flash-1017-GSQ-RCO-GGUF), revision
`ad1e8991`): routed experts in IQ2_XXS (2.00 bits per weight averaged over the 551.9B-parameter backbone, 138.24 GB),
the Engram tables in IQ4_NL (4.5 bits per weight, 110.60 GB). The DSpark drafter is DeepSeek's own FP8 head from the
1017 release.

UPSTREAM CLAIM (ISTA-DASLab, reasoning effort 50, against the unquantized release):

| variant | AIME25 | GPQA-Diamond | LiveCodeBench v6 | recovery |
|---|---:|---:|---:|---:|
| base (FP8 / FP4) | 100.00 | 90.91 | 89.71 | 100.0 % |
| IQ2_XXS (served here) | 100.00 | 90.91 | 89.71 | 100.0 % |

These benchmarks are small (AIME25 is 30 problems), so they can hide small losses.

## This build

- **Not measured yet**: token-level fidelity (KL divergence and top-1 agreement against the unquantized 1017 model)
  of this engine. Planned, with the same harness, reference logits and panels used for DGX sPLIce, so the two builds can
  be read side by side.
- **Functional**: needle retrieval at ~450K and ~498K tokens found 6 of 6 needles in 4 of 4 runs; prefix-cache hits at
  36K-500K returned the same text as cold runs.
- **Speed changes**: every adopted lever is bitwise-identical or passes the greedy identity gate ([method](method.md#gates)).
  None changes what the model computes; the drafter changes speed, not the output distribution.
