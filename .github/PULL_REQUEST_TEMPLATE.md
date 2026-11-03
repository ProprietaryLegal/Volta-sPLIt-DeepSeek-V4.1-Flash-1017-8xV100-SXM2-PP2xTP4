## What and why

## How it was tested

- [ ] On V100 hardware: before and after under the gates in docs/method.md (ms per round, greedy byte identity)
- [ ] CPU tests: `python3 -m pytest -q -p no:cacheprovider forks/1cat-4xv100-tp4/tests`
- [ ] Not measured on V100 yet (say so; we can run it)

## Checklist

- [ ] Modified engine files keep their licence and headers; CREDITS.md and NOTICE updated if a new source is used
- [ ] No prompts, outputs, logs, caches, addresses or host names from real use
- [ ] Numbers added to docs are MEASURED, with date, configuration and conditions, or labelled ESTIMATED
