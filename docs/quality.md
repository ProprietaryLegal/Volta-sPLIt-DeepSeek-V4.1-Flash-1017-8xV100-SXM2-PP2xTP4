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

## This build (the 2026-11-05 checkpoint)

### LegalBench (MEASURED 2026-11-05)

Official LegalBench base prompts and scoring: exact match after the official normalization, balanced accuracy,
checked against HazyResearch's `evaluation.py`. Greedy, thinking off, 1,292 items over 22 tasks (up to 60 per task),
0 errors, median prompt 522 tokens. The prompt asks for the label only, on the first line. The answer read is the label
the reply commits to (a bare label line or an answer line; the last one wins; otherwise a first line that opens with a
label). A reply that commits to no label scores as wrong: 4 such replies, all in `proa`.

| category (mean of its tasks) | balanced accuracy |
|---|---:|
| issue (2 tasks) | 0.614 |
| rule (3) | 0.693 |
| conclusion (6) | 0.722 |
| interpretation (6) | 0.777 |
| rhetoric (5) | 0.690 |
| **all 22 tasks** | **0.716** |

| task | n | balanced accuracy |
|---|---:|---:|
| corporate_lobbying | 60 | 0.728 |
| learned_hands_divorce | 60 | 0.500 |
| citation_prediction_classification | 60 | 0.734 |
| international_citizenship_questions | 60 | 0.619 |
| nys_judicial_ethics | 60 | 0.726 |
| abercrombie | 60 | 0.803 |
| diversity_3 | 60 | 0.778 |
| hearsay | 60 | 0.751 |
| personal_jurisdiction | 50 | 0.857 |
| successor_liability | 47 | 0.165 |
| ucc_v_common_law | 60 | 0.976 |
| contract_nli_explicit_identification | 60 | 0.818 |
| contract_qa | 60 | 1.000 |
| cuad_audit_rights | 60 | 0.764 |
| insurance_policy_interpretation | 60 | 0.530 |
| proa | 60 | 0.900 |
| sara_entailment | 60 | 0.652 |
| definition_classification | 60 | 0.879 |
| function_of_decision_section | 60 | 0.445 |
| legal_reasoning_causality | 55 | 0.963 |
| oral_argument_question_purpose | 60 | 0.209 |
| overruling | 60 | 0.955 |

`successor_liability` is scored by the official exact-match rule, which is order-sensitive: 15 replies named the gold
set of exceptions, 5 of them in a different order from the gold list, and those score as wrong (a diagnostic, not a
score change).

### KL divergence against the original model (served path)

**PENDING.** KL divergence and top-1 agreement of the served build against the original DeepSeek-V4.1-Flash-1017,
teacher-forced on fixed panels with the original model's reference logits.

### MMLU-Pro and HumanEval+

**PENDING.**

### Other checks
- **Functional**: needle retrieval at ~450K and ~498K tokens found 6 of 6 needles in 4 of 4 runs; prefix-cache hits at
  36K-500K returned the same text as cold runs.
- **Speed changes**: every adopted lever is bitwise-identical or passes the near-tie gate ([method](method.md#gates));
  the 2026-11-05 prefill expert GEMM passed it with 8 of 8 identical and KL 0.0. The drafter changes speed, not the
  output distribution.
