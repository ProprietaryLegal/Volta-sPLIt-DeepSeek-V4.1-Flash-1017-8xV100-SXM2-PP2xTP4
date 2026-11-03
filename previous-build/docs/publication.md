# Publication notes

What this repository was assembled from, what was left out, and the conventions it follows.

## Sources

- Our private deployment repository for the V100 host: production state, benchmark tables, decision records,
  experiment records, patches 0001-0003 and the tools in `tools/`.
- Our internal survey of upstream ideas and the analyses of KV capacity, the MoE kernel, the decode-lane switch
  and the decode-step profile, all dated 2026-11-01.
- The interim report already public in
  [deepseek-v4-flash-v100](https://github.com/ProprietaryLegal/deepseek-v4-flash-v100): its patches, harness and
  evidence file are reused byte for byte.

[`.publication/SOURCE.json`](../.publication/SOURCE.json) lists every file and where it came from.

## Left out, and why

| left out | why |
|---|---|
| The launcher wrapper, environment files, manifest and start / stop / verify scripts | private paths, GPU UUIDs and hash pins of the host; the settings that matter are in [production.md](production.md) |
| The request runner, greedy check, functional check and the private task suite | they embed our prompt corpus, private prompts and reference outputs; the protocol is in [method.md](method.md) |
| Raw logs, speed files, generated text and greedy references | generated text and host details; every number is in [evidence/](../evidence/) |
| Experiment runners, arm scripts and hand-run test packages | private paths and addresses; the pending tests are described in [roadmap.md](roadmap.md) |
| The KMOE1 kernel variants and the expert-usage counters | the variants were timed and did not win ([experiments.md](experiments.md#kmoe1-next-steps-for-the-moe-prefill-kernel)); the counters are not measured yet |
| Two decision records about other workloads sharing the host | internal scheduling, not about the engine |
| Hash pins of the rebuilt `_C` and of private files | they identify private builds, not anything a reader can reproduce |

## Conventions

- **Machine names.** The host is "the V100 host" or "our host"; other machines are named by role ("the host with the
  RTX 3090s"). The sister repositories follow the same rule.
- **Labels.** MEASURED, ESTIMATED, UPSTREAM, as in [method.md](method.md). PENDING marks a result that is not in yet.
- **Conditions.** Every number carries its memory clock, GPU clock cap and power limit.
- **No outputs.** No prompt or generated text, from real use or from benchmarks, is published.

## Checks run before publication

- `tools/check_data_boundary.sh --tree HEAD` (weights, archives, `*.jsonl`, private directories, files over 1 MiB,
  credential patterns).
- Our pre-publication scan for host names, private paths and addresses, e-mail addresses, credentials and internal
  process names, over every file.
- `git apply --check` of patches 0001-0003, in order, against the pinned engine commit.
- The CPU tests in `tools/`.
