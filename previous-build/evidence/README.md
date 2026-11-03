# Evidence

Every published number as JSON, with its date, conditions, seeds and configuration. Token counts and timings only:
no prompts, no generated text, no logs.

| file | what |
|---|---|
| [`2026-11-01-final/results.json`](2026-11-01-final/results.json) | the 2026-11-01 optimization round: baseline, every arm (promoted or not), production, the 2026-10-31 runs, the kernel-level numbers and the decode-step profile |
| [`2026-11-01-interim/results.json`](2026-11-01-interim/results.json) | the interim file first published in [deepseek-v4-flash-v100](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100) (baseline and resident-Engram arm), unchanged |

Labels follow [docs/method.md](../docs/method.md): fields are MEASURED unless they say ESTIMATED. The `pending` list
names the measurements still running; finished ones are added to `2026-11-01-final/results.json`.
