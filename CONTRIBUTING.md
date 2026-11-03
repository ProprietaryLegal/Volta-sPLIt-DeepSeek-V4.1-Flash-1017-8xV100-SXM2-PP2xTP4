# Contributing

Bug reports, measurements on other V100 hosts, corrections to our numbers or credits, and pull requests are all welcome.

## Reporting a bug

Open a [bug report](https://github.com/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-SXM2-PP2xTP4/issues/new?template=bug_report.yml). Include the series tree you built
(`tools/apply_series.sh` prints it), whether patch 0050 is applied, your `rec.env` switches, the engine log lines around
the failure, and your GPU, clock and power settings. Please remove addresses, host names and anything from your prompts
that you would not post publicly.

Problems in the engine itself belong upstream: [1CatAI/1Cat-vLLM](https://github.com/1CatAI/1Cat-vLLM).

## Reporting a measurement

Open a [performance report](https://github.com/ProprietaryLegal/Volta-sPLIt-DeepSeek-V4.1-Flash-1017-8xV100-SXM2-PP2xTP4/issues/new?template=performance_report.yml) with ms per round and
tok/s in the shape [docs/method.md](docs/method.md) describes (T=0 / T=1, prompt sizes, ABBA order), the GPU clock cap
and power limit, and what else ran on the machine. Token counts and timings only, never prompt or generated text.

A number goes into the README or `docs/` only if it is MEASURED, with its date, configuration and conditions, or labelled
ESTIMATED with the arithmetic shown.

## Pull requests

- One change per pull request, with the reason in the description.
- A change that affects serving needs a before-and-after on V100 hardware under the gates in [docs/method.md](docs/method.md)
  (greedy byte identity at least), or a clear statement that it has none yet; we can run it on ours.
- Keep the engine's licence and headers on any file you modify; add new sources to [CREDITS.md](CREDITS.md) and [NOTICE](NOTICE).
- Do not add prompts, outputs, logs or caches from real use.

By contributing you agree that your contribution is licensed under Apache-2.0, like the rest of the original code.
