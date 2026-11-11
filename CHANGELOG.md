# Changelog

## 2026-11-11: data-boundary scan fix

`tools/check_data_boundary.sh` could miss a credential-shaped string in a file larger than about 64 KB. It piped each
file into `grep -q` under `pipefail`; grep exits at its first match, the sender dies of SIGPIPE, and the script read
that as "no match". MEASURED with a fake token at the top of a 240 KB file: missed 10 of 10 before, refused 10 of 10
after, in `--tree` and `--staged` mode; a clean 240 KB file is still accepted. The file body now goes to a temporary
file first. The tree published before this fix was rescanned with a plain recursive grep: no credential pattern in its
176 files. If you reuse this script, take the fixed version.

## 2026-11-11: three chat slots, system notes in place, top-k segments of 1,024

Four items were tested on the production host (2026-11-10 22:54Z to 2026-11-11 01:23Z, clock ceiling 1,477 MHz), each
against a rule written before its data. Three were adopted at 01:28Z; detail and tables in
[docs/levers.md](docs/levers.md#after-the-checkpoint-adopted-2026-11-11).

- **Three chat slots** (`max-num-seqs: 3`). MEASURED, three chats of 60K, 100K and 150K tokens taking turns: cache hits
  on return 0 of 6 → 6 of 6, first token 20.6-49.2 s → 0.57-0.88 s; a lone request is not slower (132.1 → 132.0 tok/s);
  near-tie gate PASS, every row identical. Requests still run one at a time. The slots run on multi-request engine work
  later than the checkpoint, which is not published here: the published tree serves one slot.
- **System notes keep their place** (`VLLM_V41_SYSTEM_IN_PLACE=1`, new
  `engine/production/0058-system-notes-in-place.patch`). A system message added in the middle of a chat on the Messages
  endpoint no longer moves to the front of the prompt and throws the cache away: cached tokens 0 → 31,248 of 31,300,
  first token of the next turn 11.2 s → 0.51 s, the note obeyed 10 of 10 either way.
- **Top-k segments of 1,024** (`VLLM_V41_TOPK_SEG=1024`, new `engine/production/0059-topk-segment-width.patch`). Decode
  round −0.17 ms at 8K, −0.31 at 32K, −0.33 at 64K, −0.40 at 128K against the baseline before the windows; outputs
  byte-identical. The first window missed our depth rule by 0.01 ms and a repeat window, fixed in writing first, passed
  by 0.01 ms; both are published.
- **Not adopted:** the router with 8 warps instead of 4. Average −0.027 ms per round (95 % −0.125..+0.071): neutral.
- `rec.env` has 32 keys (the checkpoint's 30 and these two). The speed tables on the front page are still the
  checkpoint's of 2026-11-05; they were not re-measured.
- 0058 and 0059 were measured on our production tree and cut here against the published tree, where they apply and
  compile (trees `1ee8ad2755b4`, `e082b9540245`); they were not run on the published tree.
- `evidence/queue-log.txt` is unchanged: these windows were not queue items.

## 2026-11-10: install guide fixes (issue #1)

- **The drafter folder must be generated.** `docs/production.md` listed `dspark-v41/` as three downloaded shards. It
  also needs its own `config.json` and index, written by #1277's `benchmarks.deepseek_v41.prepare_dspark`; the guide
  now gives the layout and the command. A folder with only the shards fails at boot with
  `'DeepseekV41Config' object has no attribute 'hidden_size'` or
  `num_speculative_tokens:5 must be divisible by n_predict=3`. MEASURED: the script's output is byte-identical to the
  config and index production serves from. The four-card fork's README points to the same step.
- **Harness default profile.** The harness scripts defaulted to `serve-v41pkg-pp2.yaml`, our host's name for the
  profile published as `engine/configs/serve-pp2.yaml`. They now default to `serve-pp2.yaml`.
- No engine or measurement change.

## 2026-11-05: the checkpoint build (30 keys), speed by kind of text at 1K-256K

- **New headline, MEASURED** (context sweep, 135 requests, thinking off, greedy): decode depends on the kind of text.
  Code 215 tok/s after a 1K prompt and 160 at 256K; structured (JSON) 203 and 180; legal 118 and 103; prose 89 and 84;
  chat 95 and 81. Prompt reading 830-950 tok/s at 1K, 1,900 at 32K, 2,200 at 128K and 256K, the same for every kind.
  First token 17 s at 32K, 59 s at 128K, 119 s at 256K. Thinking on: code 106-144 tok/s, JSON 131-177. These replace the
  single 134.2 / 136.6 tok/s headline.
- Adopted the all-reduce push for V4.1's message size (test D44R5, `engine/production/0056-allreduce-sum2-push.patch`):
  −0.180 ms per round (ABBAABBA, 95 % −0.278..−0.081).
- Adopted the NCCL host hand-off between the boards (`NCCL_P2P_LEVEL=NVL`): first token −13.4 % at 32K, −14.2 % at
  128K, bitwise.
- Adopted the SM70 prefill expert GEMM (test D51, `0057-prefill-iq-gemm.patch`, `v41prefmoe`): first token −4.1 % at
  32K, −4.3 % at 150K, −2.4 % at 300K, near-tie gate PASS.
- `rec.env` now has 30 keys. This is the checkpoint build: it is frozen, and new work is built and tested on a separate
  4-GPU test machine.
- Quality (MEASURED): LegalBench 0.716 balanced accuracy over 22 tasks; MMLU-Pro 79.9 % (700-item subset);
  HumanEval+ pass@1 89.6 % plus, 94.5 % base; fidelity to the original model 89.0 % top-1 agreement on the general
  panel and 92.5 % on the legal panel (KL lower bound 0.132 and 0.156). Thinking off, greedy.
- Did not work: fused prefill attention in exact-softmax mode (lever A mode 2): first token −11 % but near-tie gate FAIL;
  a bitwise mode 3 is ready on the test machine.
- Removed sections that no longer describe this build (the four-card table and the old long-prompt tables).
- `evidence/queue-log.txt` extended through the checkpoint.

## 2026-11-04 (afternoon): Model Runner V2, fused prefill index scorer and drafter sharding adopted

- **New headline, MEASURED** (test D54A, the production set, two arms): T=0 **134.2 / 135.0 tok/s**, T=1 **136.6 / 136.4
  tok/s**, decode-only 22.26 / 22.22 and 22.17 / 22.19 ms per round. It replaces 119.0 / 120.8. The production boot itself
  is benchmarked after the queue.
- Adopted Model Runner V2 (`VLLM_USE_V2_MODEL_RUNNER=1`, our DeepSeek-V4.1 port, `engine/production/0055-mrv2.patch`):
  −2.759 ms per round (95 % −2.898..−2.620), bitwise in every arm. In production since 16:38Z.
- Adopted the fused prefill index scorer (`VLLM_V41_INDEX_FUSE=ilp4`, `0053-index-fuse.patch`, `v41pidx.so`; D52R2):
  first token −4.9 % at 150K and −9.5 % at 300K (300K now about 159 s), near-tie gate PASS, output identical.
- Adopted drafter projection sharding (`VLLM_V41_DRAFT_MP_SHARD=1`, `0054-draft-mp-shard.patch`; D53R2, by hand in
  D53A2): −0.130 ms per round, 8 of 8 pairs faster, bitwise.
- `rec.env` now has 23 keys.
- Did not work: expert wave kernel (D45R4, +0.216 ms), split-K tensor-core attention (D47R2) and the shared-expert down
  kernel (D49R) on the near-tie gate, fused transition (D50R2, neutral), sharded probabilistic drafts and draft
  temperatures (D46), the bitwise FP8 drafter mat-vec (stays off), the IQ1_M repack (no-go before a build).
- Depth sweep D55 (MEASURED, same window): Model Runner V2 is 2.6-2.9 ms per round faster than V1 at 2K, 8K, 16K and
  64K, and about 1.4 ms slower at the 32K prompt. The 32K cause is open.
- Withdrawn: the V1 two-request build (D42). Concurrency is being rebuilt on Model Runner V2 and waits for its window.
- In the queue: D51R4, D44R5, the concurrency window, the final benchmark, D40.
- `evidence/queue-log.txt` extended through D55.

## 2026-11-04: tiled decode index scorer adopted; no cross-hardware comparisons

- Adopted `VLLM_V41_INDEX_TILED=1` (D48), our register-tiled decode index scorer (`engine/production/0052-index-tiled.patch`,
  `v41idx.so`): decode round at 150K 29.98 → 27.88 ms (−7.0 %), at 300K 34.33 → 29.62 ms (−13.7 %), MEASURED, bitwise,
  texts identical. Short context not detectable (+0.03 ms); headline unchanged at 119.0 / 120.8 tok/s.
- Removed every comparison with builds on other hardware: not comparable. The long-context rows keep
  their V100 numbers.

## 2026-11-03 (evening): post-move production baseline, prefill skip and hot ring adopted

- **Hero numbers are now MEASURED**: one production boot with all 17 switches, T=0 **119.0 tok/s**, T=1 **120.8 tok/s**
  (2.25 accepted drafts per round), decode-only 25.30 / 25.20 ms per round, greedy gate PASS. They replace the ESTIMATED
  ~118 / ~121.
- Hardware: one PCIe switch card moved; each of the four switches now has its own CPU root complex at Gen3 x16 (each
  GPU still x8 to its switch). Decode unchanged within noise; long-prompt first token about 2 % sooner (1-3 runs per
  side).
- Adopted: prefill skip `PREFILL_SKIP_ROWS=3072` (first token −20.6 % at 150K, −31.5 % at 300K, identical output; patch
  moved to `engine/production/0051-prefill-skip.patch`) and the 524,288-position GPU hot ring `KV_HOT_POSITIONS`.
  300K first token now 178.0 s (was 263.9 s).
- Did not work: TP8 across both boards (no-go), 16,384-token chunks, V1 async with a request-end guard (+1.678 ms per
  round), chunk 4,096 and dense tiling (near-tie gate), CPU pinning (+0.079 ms), side-stream mixing (parked); indexer
  overlap neutral; hot Engram in GPU memory sized and not built. Harness v2 published (A/A under 0.1 ms per round).
- Two requests at once: boot failed, and its boot diagnostic failed too; rolled back cleanly.
- Queue now: D44-D55 (all-reduce push path, expert wave kernel, thinking acceptance, tensor-core decode attention, tiled
  index scorer, shared-expert down, fused transition, prefill GEMM and index scorer, drafter sharding, MRV2 re-port,
  IQ1_M repack), then the concurrency switch, decode by text type and a legal benchmark.
- `evidence/queue-log.txt` refreshed through the post-move baseline.

## 2026-11-03: first publication

- Volta sPLIt production stack: PP2 x TP4 port of 1Cat-vLLM #1277 plus eleven adopted levers and the expert-kernel
  instruction diet. ~118 tok/s decode, thinking off (ESTIMATED from measured deltas); ~114 MEASURED before the diet;
  84.6-87.3 tok/s on the long-context benchmark's legal prompt, thinking high (MEASURED).
- Published: the 49-patch series and four-card fork, the production diet patch, seven patches in testing, serving
  configs, the A/B harness, the 2026-11-03 queue log, and our previous build's record under `previous-build/`.
- In testing: D35-D47 (see docs/roadmap.md). Next updates: after the current queue.
