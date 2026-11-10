# A/B harness

The scripts that decided every lever on this page. They boot the server for each arm, warm it, run the measurement,
check activation lines and greedy identity, and pair the arms. Method and verdict rules: [docs/method.md](../docs/method.md).

## Set up

The scripts use four placeholders. Export them before running anything:

```bash
export ENGINE_HOME=/path/to/engine      # venv, source tree (src-pp2), run directory (run-pp2), models/, engram/
export BENCH_DIR=$ENGINE_HOME/bench5    # this directory: scripts, arm outputs, the state log pp2-go.state
export MODEL_HOME=/path/to/models       # HF config/tokenizer (base/), generated DSpark drafter folder (dspark-v41/), gguf/
export QUALITY_TOOLS=/path/to/quality   # greedy reference compare; not published (see below)
```

`dspark-v41/` must be generated once with `prepare_dspark` ([docs/production.md](../docs/production.md#prepare-the-drafter-folder-required)).
The scripts boot `$ENGINE_HOME/run-pp2/$PROFILE`; the default is `serve-pp2.yaml`, the published profile
([engine/configs/serve-pp2.yaml](../engine/configs/serve-pp2.yaml)) with its placeholders substituted. The logs under
`evidence/` show our host's name for the same file, `serve-v41pkg-pp2.yaml`.

The prompt sets are not published (we publish no prompt corpora). Supply your own: T=0 throughput uses the built-in
prompts of `ab_tput.py`; T=1 needs a JSONL of `{"id", "prompt", "seed", "temperature", "top_p", "max_tokens"}`
records; the greedy identity gate needs your own reference outputs recorded with `rerecord-greedy-ref-v2.sh`.

## Files

| file | what it does |
|---|---|
| `serve-pp2.sh`, `stop-pp2.sh` | boot and stop the PP2 x TP4 server with extra `VAR=VAL` switches |
| `warmup.py` | untimed warm-up requests (the first request of a boot JIT-compiles Triton kernels) |
| `ab-arm.sh`, `ab-arm-t1.sh` | v1 arm: boot, warm, T=0 throughput (`ab_tput.py`), T=1 seeded set (`ab_t1.py`), greedy gate |
| `ab-arm-t1-v2.sh`, `arm-checks-v2.sh`, `ab_t1_v2.py` | v2 arm: decode-only timing, provenance and activation lines, token-id identity |
| `ab-depth-arm.sh`, `ab-depth-arm-v2.sh`, `ab_depth.py` | decode by context depth |
| `arm-checks.sh`, `act-check-v2.sh` | shared checks: activation counts, tracebacks |
| `pairs_arms.py`, `pairs_arms_v2.py` | pair the arms prompt by prompt and print ms/round deltas |
| `win.py`, `win3.py` | verdicts: v1 WIN rule; v2 three-way verdict with detection power |
| `aa_spread_v2.py` | A/A spread from warm-up ABBA batches |
| `rerecord-greedy-ref-v2.sh` | records the greedy references the gate compares against |
| `trace_diverge.py` | token-by-token divergence trace for a pair of outputs (near-tie analysis) |
| `queue-d34.sh` | an example queue: build, check, sanitize, ABBA and adopt the expert-kernel diet |
| [README-v2-harness.md](README-v2-harness.md) | the v2 design notes: what each v1 defect was and how v2 fixes it |

The state log of the 2026-11-03 queue these scripts wrote is in [evidence/queue-log.txt](../evidence/queue-log.txt).
