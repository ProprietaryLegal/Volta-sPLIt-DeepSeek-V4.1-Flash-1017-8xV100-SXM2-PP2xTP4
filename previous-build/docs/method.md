# Method: how every number here was measured

## Labels

- **MEASURED**: measured on our host, with date and conditions.
- **ESTIMATED**: arithmetic or a model; never put in a results table as if measured.
- **UPSTREAM**: someone else's figure (engine author, 1Cat, DGX sPLIce), quoted with its source.

## Conditions

Every result carries its condition label. From the 2026-11-01 boot on: **"DDR4-2666, 1425 MHz cap, 180 W"**. Earlier
sections (DDR4-3200; 1425 MHz cap or uncapped clocks) are kept but are not directly comparable, because host-memory
bandwidth (up to ~17 % lower at DDR4-2666, ESTIMATED from the transfer rate) affects Engram, prefill-from-host and
CPU-side numbers, and the clock cap affects everything on the GPU.

Other CPU workloads ran on the host during some arms (a batch job and test suites); the GPUs ran only this server. No
other traffic reached the server during a measurement.

## Speed cells

- **Prompts.** ~75,000-token prompts built from a fixed corpus of public long-form documents, one per seed; output
  capped at 2,048 tokens. Each arm uses its own unseen seeds (different prompts of the same size), six per speed cell.
  The corpus and the prompt builder are not published.
- **No prefix reuse.** Every request carries a fresh `cache_salt`; prefix-cache hits were 0 in every timing cell
  (checked from the server's counters).
- **Cold** = the host page cache dropped (`sync; echo 3 > /proc/sys/vm/drop_caches`) before the request, so
  non-resident Engram rows come from NVMe. **Warm** = the same prompt again with a new salt: the KV is recomputed and
  the Engram rows are already cached.
- **First token (TTFT)** = time to the first streamed token. Prefill tok/s = prompt tokens / TTFT.
- **Decode tok/s** is measured on the streamed output. It depends on the DSpark drafter's acceptance on the generated
  text, so six-seed means move by ±10 % and their CIs usually span 0.
- **ms per verify round** = 1000 x (accepted tokens per draft + 1) / decode tok/s, from the server's speculative
  decoding counters over the cell. This is the stable engine-speed measure: 0.3 ms spread across boots.

## Other cells

- **Decode beside a prefill (dbp).** A 3,000-token decode stream runs; 10 s later a cold ~75K-token prefill is
  submitted beside it. Reported: decode rate before and during the prefill, the longest gap between decode tokens, and
  that prefill's TTFT.
- **Stress.** Three ~300,000-token prompts submitted at once, 256 output tokens each. Reported: wall time, each TTFT,
  preemptions, peak KV use, peak card power, lowest host MemAvailable.
- **Thinking on.** The warm cell with `chat_template_kwargs: {"thinking": true}`.

## Gates

A change must pass all of these against the baseline before it can serve:

- **Greedy check.** A fixed set of prompts (8 prompts, run twice: 16 checks; two of them long enough to run full
  prefill chunks) at temperature 0, compared byte for byte with references recorded on the baseline boot (three
  recording runs, all identical). A non-identical output is classified by its first divergent token: a **near-tie**
  when both token IDs are in the top-20 logprobs and within 0.9 nats of each other and of the top token, otherwise a
  **divergence**. Production requires 16 / 16 byte-identical for a change that claims to be exact.
- **Functional check.** 15 API checks: chat, streaming, JSON mode, a tool round trip, `tool_choice=required`,
  thinking on / off / default, five reasoning efforts, a 900-word repetition check, 32K three-needle recall.
- **Private task suite.** Our own longer tasks, scored against the baseline (41 of 46 on the baseline). Not published:
  its prompts are private.
- **Stress.** 3 x ~300K completes with 0 preemptions.
- **EDAC.** The memory controller's `ue_count` / `ce_count` are read before and after every arm and every start. Any
  new uncorrected error stops all GPU and RAM-heavy work and leaves the server down; more than 10 new corrected errors
  in one arm also stops the run.

## Promotion rule

A speed change is promoted when its target cell (cold or warm 75K first token) is at least 2 % better with the 95 % CI
excluding 0, decode is not more than 3 % worse, and every gate above passes. CIs are unpaired 95 % bootstraps
(20,000 resamples, fixed seed) of the change in the mean, because arms are separate restarts with disjoint seeds:
[tools/compare_speed.py](../tools/compare_speed.py). Its `promote_speed` flag covers a cold-target change; for a
warm-target change, read the same rule off its warm row. One arm is one restart with one change.

## What is not published, and why

- The prompt corpus, the prompt builder, the request runner and the greedy references: the references are generated
  text, and the runner embeds the corpus and private paths.
- The private task suite (private prompts).
- Raw logs and generated text. Every number is in [evidence/](../evidence/) as JSON instead.

What is published: the comparison tool, the warm-up and thread-census tools, the kernel harness behind patch 0003, and
the data-boundary scan ([tools/](../tools/), [patches/](../patches/)).
