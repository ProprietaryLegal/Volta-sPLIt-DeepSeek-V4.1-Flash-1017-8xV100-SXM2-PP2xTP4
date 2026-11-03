# Roadmap and pending results

What is being measured or built now, and where each result will land. A **PENDING** slot is filled in place when its
measurement finishes; nothing marked PENDING is a result yet. Slots marked done keep their result here. Status as of
2026-11-01.

## Pending results

### Where the 71.5 ms verify round goes (profile MEASURED; decode study done)

- **Profile (MEASURED 2026-11-01):** [measurements.md](measurements.md#where-a-decode-step-goes-2026-11-01-profiled).
  At one stream a step is 70.0 ms: ~29 ms of kernels on stage 0, then ~32 ms on stage 1, one after the other, plus
  ~9-13 ms of launch, host and hand-off gaps. Routed MoE is ~11 ms; small torch ops plus gaps are roughly a third of
  the step; dense GEMMs at verify width ~15 ms. At three streams stage 0's all-reduce averages 29.2 ms per step,
  mostly ranks waiting for each other: one 3.7 s host stall (~15.7 ms per step of the mean), host skew at the step's
  first all-reduce (~6 ms) and expert-load imbalance (~4.4 ms), MEASURED.
- **Decode study (done 2026-11-01, trace reading):** the round is not bandwidth-bound. Its HBM-byte floor is ~12 ms
  (ESTIMATED: backbone, LM-head and drafter bytes at 830 GB/s) against 70.0 ms MEASURED, and the routed experts run
  at ~78 % of the HBM roofline (ESTIMATED). The rest is per-kernel cost (~2,370 kernels in each stage's forward per round, 85 %
  under 16 µs), latency-bound GEMVs and attention at verify width, the two stages running one after the other, and
  ~9 ms of host time with every GPU idle (MEASURED, profiled). Launch overhead is already hidden, so only fewer
  kernels help. Async scheduling is not an option: the engine's attention forbids it with speculative decoding.
- **Result:** three exact changes are written: two fusions (MoE routing glue, norm tails), bit-identical on one card,
  and stage 0's input preparation computed once per batch, identical on the CPU (MEASURED). ESTIMATED savings:
  −2.2..−2.4, −1.5..−1.8 and −0.6..−1.0 ms per round; together 4.3-5.2 ms, a round of 70 → ~65-66 ms (+6.5-8 % tok/s;
  up to ~62 ms if the routing fusion saves its whole in-place bucket). None is tested in serving yet: server timing
  under the gates, one change per arm, **PENDING**. Patch text will be added to `patches/` only after a measured win.
- **Dropped or separate (ESTIMATED):** CUDA graphs for the sampler and drafter-head tail are dropped: re-measured,
  those windows are already 92-95 % GPU-busy, so the saving is at most ~0.2 ms. Pinning each GPU worker to its own
  cores (a launcher setting) is estimated at 0-1 ms per step at one stream and 2-4.5 ms at three, outside the total
  above; it needs its own serving arm. Larger levers exist that are not bit-exact (fused hyper-connection mixes with
  inexact norms, FP8 dense GEMMs, tensor-core decode attention, a better `wo_a` GEMM). They change numerics, so they
  would have to pass a quality measurement instead of the byte-identity gate; none is scheduled.

### MoE prefill, next step (kernel variants timed 2026-11-01: no win)

- **Kernel variants (MEASURED, one card):** C, B and X are bit-identical, but none is faster on the tiers that carry
  the time ([KMOE1](experiments.md#kmoe1-next-steps-for-the-moe-prefill-kernel)). No server arm.
- **Next:** remove the host sync after each layer's MoE routing plan (median 156 µs of GPU idle per layer, ~4 ms per
  1,016-token prefill chunk on stage 0, MEASURED). Designed to be bit-identical; not written.
- **Result:** PENDING for the host-sync fix.

### Real KV capacity (MEASURED 2026-11-01)

- **What:** three ~315K-token requests resident at once; peak KV use and preemptions
  ([kv-capacity.md](kv-capacity.md#the-measurement-2026-11-01)).
- **Predicted (ESTIMATED):** 72-76 % peak use, 0 preemptions; real capacity ~1.43M tokens.
- **Result:** three 314,728-token requests resident at once peaked at 71.5 % KV use with 0 preemptions (~960K tokens
  resident). The full 983,040-token load would use ~73 % and real capacity is ~1.34-1.47M tokens (both ESTIMATED).

### Concurrent identity (PENDING)

- **What:** the 16 greedy checks re-run while two fresh ~150K-token requests generate beside each one (both must still
  be running when the comparison ends), labelled IDENTICAL / NEAR-TIE / DIFFERS under the gate's rule; then a ~300K
  synthetic needle with three codes at the start, middle and end.
- **Result:** PENDING.

### Context sweep and llama-benchy (MEASURED 2026-11-01)

- **What:** first token and decode across context lengths, prefix refill, one to three concurrent streams, decode
  beside prefill and the speculative-decoding counters, plus [llama-benchy](https://pypi.org/project/llama-benchy/) on
  production so the numbers can be set beside other published V100 and DGX Spark builds.
- **Result:** prefill holds ~3,300 tok/s from 32K to 75K tokens and is ~10 % lower at 300K. An exact repeat, or a new
  tail on the same cached 75K prefix, answers in ~0.5 s instead of ~23 s. With three 32K requests at once the third
  waits ~30 s for its first token. llama-benchy on book text: 37-46 tok/s decode for one stream at depths 0-65K. The
  sweep's synthetic-text decode rates (82-87 tok/s) are a best case for the drafter, not typical decode. Tables:
  [measurements.md](measurements.md#2026-11-01-production-second-session).

### Persistent prefix tier (design done; first check: open finding)

- **What:** port DGX sPLIce's restart-surviving prefix tier to PP2 x TP4. The port design is done
  ([MC1](experiments.md#mc1-persistent-prefix-tier)): ESTIMATED 17.5-24.5 working days; a 150K-token prefix would
  reload in 0.5-1.2 s against ~52 s cold (ESTIMATED).
- **First check (MEASURED 2026-11-01):** cold against cold 8 / 8 byte-identical; a warm in-memory hit against cold
  2 identical, 3 near-ties, 0 differing of 5 valid pairs; 3 more warm requests reused nothing because a guard in the
  engine's decoder replay dropped the cached prefix
  ([measurements](measurements.md#prefix-cache-identity-warm-hit-against-cold)).
- **Result:** open finding; the root cause is under investigation, then the check is rerun.

### Expert-usage counters (PENDING)

- **What:** per-layer, per-expert routing counters behind a default-off engine patch, written once per serve. They are
  the input for spending expert bits by measured routing frequency (survey item 12). Built and tested offline; not
  installed yet.
- **Result:** PENDING.

### 1Cat GLM changes that may port (done 2026-11-01, code reading)

- **What:** 1Cat's GLM pull requests and issues since September (38 PRs, 17 issues) and the 1Cat commits that touch
  files this engine also changed, read against the engine snapshot.
- **Result:** nothing large to pull. The engine already has, or goes beyond, each GLM optimization worth having: its
  EXL3 MoE kernel is a superset of 1Cat [#1102](https://github.com/1CatAI/1Cat-vLLM/pull/1102), and it has fused
  hyper-connections, a fused indexer scorer, register-resident sparse-MLA prefill, drafter CUDA graphs and a small-N
  GEMV for the router and shared experts. The GLM correctness bugs (#1327/#1328, #1330, #1331, #1332, #1337, #656,
  #1324) do not apply: the engine avoids each code path or already handles the case.
- **Small follow-ups:** Triton recompiles a kernel mid-request here as in 1Cat
  [#1326](https://github.com/1CatAI/1Cat-vLLM/issues/1326) (MEASURED: 15 cached variants of one kernel, seven first
  compiled on 2026-11-01 with the server up); a default-off, Python-only fix is written, not yet measured (ESTIMATED
  ~0.1 s on an occasional step; cleaner benchmark tails). Two conditional ports: 1Cat
  [#1265](https://github.com/1CatAI/1Cat-vLLM/pull/1265) (fewer drafter prefill tokens on prefix hits) and
  [#1267](https://github.com/1CatAI/1Cat-vLLM/pull/1267) (fewer sampler host syncs when clients send top-k and top-p
  together).

## Next, in order

1. Server arms for the three exact decode changes from the decode study, one change per arm, under the full gates.
2. The MoE host-sync fix (Python only), then one server arm under the full gates if it wins.
3. Requests-only tests on production, no restart: concurrent identity, and a rerun of the prefix-cache identity check
   once the dropped hits are understood.
4. Expert-usage counters (built, not installed), the input for spending expert bits by routing frequency.
5. The PCIe Gen3 x4 probe in a maintenance window.

## Not planned

CUDA 13 or drivers past R580; quantized K cache; approximate speculative decoding; NCCL tuning; CPU KV offload; the
remote Engram and remote drafter variants until the hardware they need exists. Reasons: [survey.md](survey.md).
