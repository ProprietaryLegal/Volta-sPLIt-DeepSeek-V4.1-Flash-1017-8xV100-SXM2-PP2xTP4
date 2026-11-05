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

MEASURED 2026-11-05 on the checkpoint build: how closely the served model's next-token distribution follows the original
DeepSeek-V4.1-Flash-1017, position by position, on fixed text.

Method: sudoingX's `p4_kld.py` approach. The reference logits were computed once from the original release with
DeepSeek's reference implementation: for every scored position, the original model's top-128 tokens with their
log-probabilities and the log-likelihood of the true next token. Two panels: sudoingX's general panel (199
conversations in 8 domains) and our legal panel (210 sequences). Each panel sequence was sent as token IDs to the
running server (greedy, `prompt_logprobs` = 20, no prefix-cache hits), one request at a time.

- **top-1 agreement**: the served model's most likely next token is the original's most likely next token. Exact.
- **NLL**: mean negative log-likelihood of the true next token, original vs served. Exact.
- **KL divergence, lower bound**: KL(original || served), computed over the tokens that appear in both the original's
  top-128 and the served top-20, plus one bucket for the rest. Merging tokens into one bucket can only lower the KL, so
  this is a lower bound; the true value is at least this.

| panel | positions | top-1 agreement | KL, lower bound (mean) | KL p99 | NLL original | NLL served |
|---|---:|---:|---:|---:|---:|---:|
| general (8 domains) | 254,846 | **89.0 %** | **0.132** | 1.71 | 0.470 | 0.564 |
| legal | 71,080 | **92.5 %** | **0.156** | 3.00 | 0.197 | 0.301 |

| general panel domain | positions | top-1 | KL lower bound |
|---|---:|---:|---:|
| code | 165,450 | 90.6 % | 0.094 |
| long | 16,457 | 90.9 % | 0.112 |
| math | 10,625 | 89.4 % | 0.090 |
| agentic | 16,686 | 87.5 % | 0.162 |
| multilingual | 8,620 | 85.7 % | 0.300 |
| knowledge | 14,093 | 84.2 % | 0.216 |
| writing | 4,939 | 83.9 % | 0.283 |
| chat | 17,976 | 80.8 % | 0.309 |

| legal panel domain | positions | top-1 | KL lower bound |
|---|---:|---:|---:|
| tools | 3,608 | 99.2 % | 0.016 |
| extraction | 2,674 | 97.1 % | 0.064 |
| preservation | 15,065 | 96.1 % | 0.070 |
| hallucination | 2,322 | 92.9 % | 0.126 |
| drafting | 26,971 | 92.3 % | 0.159 |
| authority | 16,261 | 91.2 % | 0.133 |
| general | 4,179 | 77.3 % | 0.736 |

What this measures is the quantization, not the speed work: the experts are served at IQ2_XXS (about 2 bits per weight),
and every speed change is bitwise-identical or passes the near-tie gate. The gap is largest on open-ended text (chat,
writing, multilingual) and smallest on code, tool calls and extraction.

### MMLU-Pro and HumanEval+

MEASURED 2026-11-05 on the checkpoint build, through the running server, thinking off, greedy, one request at a time.

| benchmark | score | items | errors | replies cut at the token limit |
|---|---:|---:|---:|---:|
| MMLU-Pro (exact match) | **79.9 %** ±1.5 | 700 | 0 | 11 |
| HumanEval+ pass@1, plus tests | **89.6 %** (147 of 164) | 164 | 0 | 2 |
| HumanEval+ pass@1, base tests | 94.5 % (155 of 164) | 164 | 0 | 2 |

- **MMLU-Pro**: lm-eval's `mmlu_pro` task, 5-shot chain of thought with its own answer extraction, temperature 0,
  up to 2,048 output tokens. A subset: the first 50 test items of each of the 14 subjects in dataset order
  (`--limit 50`), so 700 of the 12,032. ±1.5 is lm-eval's standard error.
- **HumanEval+**: EvalPlus, all 164 problems, temperature 0, up to 768 output tokens, scored in EvalPlus's sandbox
  against the base tests and the extended "plus" tests.
- With thinking on the scores may be higher; we have not run that yet.

### Other checks
- **Functional**: needle retrieval at ~450K and ~498K tokens found 6 of 6 needles in 4 of 4 runs; prefix-cache hits at
  36K-500K returned the same text as cold runs.
- **Speed changes**: every adopted lever is bitwise-identical or passes the near-tie gate ([method](method.md#gates));
  the 2026-11-05 prefill expert GEMM passed it with 8 of 8 identical and KL 0.0. The drafter changes speed, not the
  output distribution.
