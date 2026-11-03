# v2 A/B harness (2026-11-03)

This harness fixes the defects that an adversarial review of v1 found (H1 to H6 and M1 to M4).

- Every v1 file is unchanged: `ab-arm.sh`, `ab-arm-t1.sh`, `ab-depth-arm.sh`, `arm-checks.sh`, `ab_t1.py`, `ab_tput.py`, `pairs_arms.py`, `win.py` and `warmup.py`. The queued D32 to D37 windows still use them.
- The v2 files are new siblings in bench5.
- Nothing in v2 has run on the GPU yet. Every test so far ran against a stub server on another port, or replayed the existing bench5 logs read-only (see "Dry tests" below).

## Files

| file | what it does | fixes |
|---|---|---|
| `ab_t1_v2.py` | One streamed client for T1 (same arguments as `ab_t1.py`), T0 (`--tput URL N OUT`, replaces `ab_tput.py`) and `--compare`. For each request it records `ttft_s`, `dec_s` and `ms_round_dec` (first to last streamed token, divided by rounds), the generated token ids, `tok_sha` and the text sha (v1 formula). The v1 line prefix is unchanged and the v2 fields are appended. Printed lines carry numbers and shas only, never text. | H2, M1; token ids follow-up |
| `pairs_arms_v2.py` | Same as `pairs_arms.py`. Adds `--metric legacy` (the default; byte-identical to v1) or `--metric dec` (refuses v1 arms), and `--from-out`. On v2 arms, "texts same" is decided by token ids. | H2 |
| `win3.py` | Three-way verdict: WIN, LOSE, or NEUTRAL-or-UNDETECTED (sub-label NEUTRAL, UNDETECTED or TEXTS-DIFFER). Also prints an ACTION line (ADOPT, REJECT, KEEP-ON(upstream), PORT-GAP, NOT-ADOPTED or INVALID-BATCH) using `--upstream REF`, `--bundle-only` and `--gate`. It reports the detection power and the 95 % interval, supports `--design abba\|abbaabba` and `--order` to print the run order, and writes `--json`. | M2, M3, H4 |
| `aa_spread_v2.py` | Computes the A/A noise of the warm-up ABBA batches in bench5. Read-only; `--metric dec` once dec arms exist. | M3 |
| `arm-checks-v2.sh` | Shared v2 helpers: `warm`, `need_line`, `invalid`, `boot` and `split_args`. Also `prov` (H5), `activation` (H3) and `gate_v2` (H1). | H1, H3, H5 |
| `ab-arm-t1-v2.sh` | Same arm flow as `ab-arm-t1.sh`, but runs the v2 client and the v2 gate, and writes a provenance line and an activation count. `SKIP_T1=1` gives the `ab-arm.sh` flow. | H1, H2, H3, H5 |
| `ab-depth-arm-v2.sh` | `ab-depth-arm.sh` plus the provenance line and the activation count. `ab_depth.py` is unchanged because it is already decode-only. | H3, H5 |
| `act-check-v2.sh` | `OFF ON`: exits 0 only when the activation counts of the two arms differ. | H3 |
| `rerecord-greedy-ref-v2.sh` | H1 runner, for an owner-scheduled GPU window. **Not run.** | H1, M4 |
| (not published) | void-verdict lines for the state log | H6 |

## How new queues call it

The arm arguments work as in v1 (`VAR=VAL` arguments are the server env). The harness variables `GATE`, `NUMERICS`, `ACT_GREP`, `ACT_EXPECT`, `SKIP_T1` and `SKIP_GREEDY` can be given either as arguments or in the environment. `split_args` keeps them out of the server env.

```bash
O=${BENCH_DIR}
# ABBA (levers expected > 0.2 ms); labels must be NEW (a label used by a v1 arm is refused)
for c in OFF ON ON2 OFF2; do
  case $c in ON*) X="$FULL VLLM_V41_ROUTE_FAST=1 ACT_EXPECT=on";; *) X="$FULL ACT_EXPECT=off";; esac
  bash $O/ab-arm-t1-v2.sh RF2-$c $X "ACT_GREP=<a line only the ON path prints>" || break
done
python3 -I $O/pairs_arms_v2.py --metric dec $O RF2-OFF RF2-ON RF2-OFF2 RF2-ON2 RF2-OFF RF2-OFF2 \
  | python3 -I $O/win3.py --upstream "Sparks a6dc6f4" --gate PASS --json $O/win3-RF2.json
bash $O/act-check-v2.sh RF2-OFF RF2-ON          # 0 = the activation grep discriminates
# ABBAABBA (levers expected <= 0.2 ms): run order from win3, then 8 labels to pairs_arms_v2
python3 -I $O/win3.py --order abbabaab RF2      # RF2-OFF RF2-ON RF2-ON2 RF2-OFF2 RF2-ON3 RF2-OFF3 RF2-OFF4 RF2-ON4
python3 -I $O/pairs_arms_v2.py --metric dec $O RF2-OFF RF2-ON RF2-OFF2 RF2-ON2 RF2-OFF3 RF2-ON3 RF2-OFF4 RF2-ON4 \
  | python3 -I $O/win3.py --design abbaabba
```

**Gate.**
- `GATE=auto` is the default.
  - It runs the **approved** gate once `greedy-ref-v2.env` exists (written only by the H1 runner): `quality.neartie check --runs 1 --gap 0.10 --kl-max 0.02` against the REC reference and lp-reference.
  - Until then it runs the **legacy** gate: the v1 check against the old IDX=0 reference at 0.9 nats.
- `GATE=both` runs both. `GATE=none` (or `SKIP_GREEDY=1`) skips the gate.
- `NUMERICS=1` adds `--require-drift`. A numerics-changing knob that moves no logprob then reports NO-EFFECT, meaning it did not reach the engine.
- Each arm writes `AB <label> GATE <mode> PASS|FAIL|NO-EFFECT|ERROR rc=<n>` to its log and to `pp2-go.state`. Feed the ON arms' result to `win3.py --gate`.

**State lines that v2 arms add:**
- `AB <label> PROV so=<sha16> sodir=<build dir> pyvllm=<sha16 of every deployed vllm .py> harness=<sha16>`. A deploy that missed site-packages, as in D28, shows up as an unchanged `pyvllm`.
- `AB <label> ACT n=<count> pat=<sha8> expect=on|off|any`.
- None of these lines contains a `QUEUE-` string, so no queue grep can match them.

**Never pair a v1 arm with a v2 arm.**
- A streamed request is a different request: the API server sends one chunk per step.
- `pairs_arms_v2.py --metric dec` refuses v1 arms.
- `ab-arm-t1-v2.sh` refuses a label whose `ab-<label>-tput.out` came from v1.

## win3 rules and the A/A spread (MEASURED, legacy metric)

`aa_spread_v2.py` computed the noise over 9 warm-up ABBA batches (AR, EF, FP, FU, GU, P13, PF, PW, SP): 36 A/A comparisons, each an OFF2-OFF or ON2-ON pair. These are the same comparisons the review used, and the numbers reproduce its table:

| group | n | mean | sd | max \|.\| | \|.\| > 0.15 |
|---|---:|---:|---:|---:|---:|
| T0 A/A | 18 | +0.009 | 0.119 | 0.231 | 5 |
| T1 A/A | 18 | -0.081 | 0.120 | 0.323 | 4 |
| T1 ON2-ON | 9 | -0.118 | 0.118 | 0.283 | 3 |
| all | 36 | -0.036 | 0.126 | 0.323 | 9 |

**Noise model.**
- The T0 and T1 A/A deltas from the same comparison correlate with rho = +0.264.
- sd(avg) = 0.126 x sqrt((1 + rho) / n_means). That gives **0.071 for ABBA** (4 means) and **0.050 for ABBAABBA** (8 means).
- These are the defaults in `win3.py` (`--aa-sd 0.126 --aa-rho 0.264`).
- No dec-metric A/A data exists yet. Until it does, `win3` uses these legacy numbers for dec arms and says so.

**Verdicts.**
- **WIN** keeps the existing rule exactly: average <= -0.15 ms/round, no mean above +0.05, all T1 texts the same, and the full set of means.
- **LOSE** is the mirror rule: average >= +0.15 and no mean below -0.05.
- Everything else is **NEUTRAL-or-UNDETECTED**:
  - **NEUTRAL**: the 95 % interval lies inside ±0.15.
  - **UNDETECTED**: the interval reaches ±0.15.
  - **TEXTS-DIFFER**: the speed meets WIN, but a T1 text differs.

**Detection power** of the WIN rule (MEASURED noise model, Monte Carlo, ESTIMATED):

| design | true 0 | -0.10 | -0.15 | -0.20 | -0.25 |
|---|---:|---:|---:|---:|---:|
| ABBA (pair rule = WIN) | 2 % | 23 % | 48 % | 74 % | 91 % |
| ABBAABBA (pair rule = WIN) | 0 % | 13 % | 42 % | 75 % | 92 % |
| ABBAABBA `--max-rule block` (not adopted) | 0 % | 16 % | 50 % | 84 % | 98 % |

**What the power table means:**
- Under the unchanged WIN rule, ABBAABBA buys three things:
  - position balance (the ON2-ON T1 offset of -0.118, about 3 SE);
  - near-zero false WINs;
  - an interval narrow enough for NEUTRAL to become reachable (|avg| <= ~0.05).
- It does **not** buy more power at -0.15. The "no mean above +0.05" test gets stricter with 8 means.
- `--max-rule block` applies the +0.05 ceiling to each 4-mean ABBA block average instead of to each mean. That raises power at -0.20 from 75 % to 84 %. It is a different WIN definition, so it needs the owner's approval before any queue uses it.

**Replay** of the 9 real batches: win3 agrees with win.py on all 4 WINs (EF, FP, GU, P13) and on AR = LOSE (+0.284). FU (+0.034), PF (-0.038), PW (-0.062) and SP (+0.069) become **NEUTRAL-or-UNDETECTED UNDETECTED**. win.py had called all four "LOSE". None of them has an upstream speed claim, so the ACTION is NOT-ADOPTED either way; the outcome does not change.

**the owner 11-01 rule** (upstream-backed + runs without errors + inconclusive = keep ON):
- `--upstream REF` turns a NEUTRAL-or-UNDETECTED result into `KEEP-ON(upstream ...)`.
- `--bundle-only` gives `PORT-GAP` instead. That is S11 (MOE_ADD_ALLREDUCE).
- `--gate FAIL` always gives REJECT.

**Known conflict, not changed here.** At T=1, a numerics-changing lever (near-tie gate) produces different T1 texts. So the kept WIN rule can never pass it. `win3` labels that case TEXTS-DIFFER and asks for an owner decision. It does not relax the rule.

## H1: re-record the greedy reference (`rerecord-greedy-ref-v2.sh`, not run)

**When:** a GPU window after `QUEUE-D37 done`.
- Without `REC_ENV` it refuses to run before then.
- It derives the REC stack the same way `queue-d37.sh` does: FULL, plus the D33/D34/D34R/D35 keeps, plus the D37 final keeps and the D37 profile.
- Passing `REC_ENV=... PROFILE=...` overrides that. `NO_BOOT=1` uses the running server, and the caller asserts that it is REC.

**Command:**
```bash
bash ${BENCH_DIR}/rerecord-greedy-ref-v2.sh REFV2
```

**Steps:**
1. Stop and boot REC (Engram kept), then warm up and write the provenance line.
2. `quality.greedy record --runs 3`. All 3 runs must be byte-identical. If they are not, nothing is published and the exit code is 1. That outcome would itself be a finding: the stack is non-deterministic.
3. `quality.neartie record --runs 2`. The lp-reference must reproduce the reference text with logprobs on.
4. Validation:
   - `greedy check --strict` must give 8/8 IDENTICAL;
   - `neartie check` must give PASS with near-tie 0 and fail 0;
   - informational only: the old reference at 0.9 nats, which should show the known row 7 0.1094 near-tie.
5. Publish `greedy-ref-v2.env` (`REF_V2`, `LP_V2`, stack, profile, .so sha) via `.new` + `mv`, and add a line to `greedy-ref-v2.history`. If validation fails, it writes `greedy-ref-v2.candidate-<ts>.env` instead and publishes nothing.

**Safety and output:**
- The new reference goes in fresh `<UTC>-greedy-REFV2` and `<UTC>-neartie-NTREFV2` folders beside the old `20261103T002941Z-greedy-B5PP2-g1` in `run-pp2/quality-runs`. The old folder is only read.
- State lines are `REREC-V2 ...`. The log is `bench5/rerec-<label>-<ts>.log`.
- The script leaves the server up on REC.

**GPU minutes (ESTIMATED from the PW-OFF arm and NT0 record timings):**

| step | minutes |
|---|---:|
| stop + boot | ~3.5 |
| warm-up | 0.1 |
| record, 3 x ~0.6 | ~1.9 |
| neartie record, 2 x ~0.7 | ~1.4 |
| strict check | ~0.6 |
| neartie check | ~0.7 |
| old-reference check | ~0.9 |
| **total** | **about 10 (schedule 15)** |

**Per-arm cost after H1.** The approved gate (`neartie check --runs 1`, ~0.7 min) replaces the legacy check (~0.6 min), so an arm costs about the same.

## H2 validation still owed (GPU, ~15 min, after H1 or alone)

1. Run one A/A pair with `ab-arm-t1-v2.sh DM-OFF $FULL` and `DM-OFF2 $FULL`.
2. Run `pairs_arms_v2.py --metric dec` and `--metric legacy` on the pair. The dec A/A delta should be no larger than the legacy one.
3. Run `aa_spread_v2.py --metric dec`. Once there are enough dec A/A pairs, pass its sd and rho to `win3.py`.
4. Cross-check: on one fresh arm, `ms_round_dec` must sit within 0.1 ms of `ab_depth.py` at a matched length. One `ab-depth-arm-v2.sh` arm with `LENS=2048 REPS=2` on the same boot gives the comparison.
5. The definition is ms_round_dec = (last − first streamed token) / rounds, not / (rounds − 1). Every bench5 record has tokens = 1 + rounds + accepted (MEASURED), so the first token comes from prefill and is not a spec round. ab_depth.py uses the same definition.

## Migration plan

1. **Running and queued windows (D32 to D37)** keep v1. No v1 file was touched.
2. **New queues** use `ab-arm-t1-v2.sh`, `ab-depth-arm-v2.sh` and `pairs_arms_v2.py --metric dec | win3.py`.
   - Use fresh labels.
   - Use ABBAABBA (or the ABBA+BAAB order) for levers expected at <= 0.2 ms (S15 ROUTE_FAST).
3. **H1 and the H2 validation** each need a GPU window (~15 min each; they can share one boot if H1 runs first). Until H1 publishes, v2 arms gate with the legacy check, and their log says `gate=legacy`.
4. **Old verdicts are not rewritten.** win.py, pairs_arms.py and every past state line stay as they are.
   - The replay table above is a reading aid. It is not a re-verdict.
   - `void-verdicts-v2.txt` holds the H6 lines for the owner to append to `pp2-go.state` when no queue is writing.
5. **Retire v1** only after the H2 validation passes. Retiring means stop using it; the files stay.

## H3 to H6 status

| item | done here (v2 files) | still open, with effort |
|---|---|---|
| H3 activation lines | `ACT_GREP` / `ACT_EXPECT` count per arm, INVALID on a missing or unexpected line; `act-check-v2.sh` OFF vs ON | SP and RF print no line at all. A one-line `logger.info` per knob in the engine is an engine-tree edit plus a deploy to both trees (~30 min dev + a boot). For RF, the report's in-venv `_FAST` import check is the cheaper proof (~5 min, CPU, owner). Each queue author still has to pick a discriminating pattern (AR's "sum2 22" is not one). |
| H4 ABBAABBA | `win3 --design abbaabba`, `--order abbaabba\|abbabaab`, power table | Whether to adopt `--max-rule block` is an owner/the owner decision. |
| H5 provenance | `.so` sha16 + build dir + deployed-vllm digest + harness sha on every v2 arm | Adding `prov` to each new queue's BASECHECK is 1 line per queue. Syncing the gu1103 sources into src-pp2 (M6) edits the engine source tree: owner, ~15 min, with no queue running. A provenance stamp beside each built .so is a build-script change, ~10 min. |
| H6 void verdicts | `void-verdicts-v2.txt` drafted (D28 VOID, the original D30 never ran, D7 has no .so verdict to void) | Appending it is the owner's job, ~1 min, between queues. |

## Dry tests (2026-11-03, scratch `/path/to/out`)

- **Stub server.** `stub_server.py` ran on port 18911 (never 18042). It reproduces the real accounting: first token from prefill, then rounds, so tokens = 1 + rounds + accepted. It also has near-tie, confident-swap and non-deterministic modes.
  - `stub-serve.sh` and `stub-stop.sh` stand in for serve/stop.
  - Every output, state and quality-run path pointed at scratch through the `V2_*` overrides.
- **Arm flow.** Legacy gate, approved gate, ACT on/off/INVALID and v1-label refusal all behaved as designed.
  - A stub ON arm 0.3 ms/round faster gave dec means -0.26 to -0.30, so WIN.
  - A TTFT-only change (+0.25 s TTFT, same round time) gave legacy +0.75 (T0) / +8.4 (T1) ms/round but dec 0.00 / +0.02. That is the H2 bias removed.
- **Approved gate cases:**
  - near-tie at 0.05 nats: PASS, 2 near-ties, KL 3e-6;
  - confident swap: FAIL, "baseline top-2 gap 4.98";
  - no drift with `NUMERICS=1`: NO-EFFECT.
- **H1 runner:**
  - refuses before D37 is done;
  - a non-deterministic stack gives FAIL with nothing published;
  - a deterministic stack publishes;
  - the D37-derived env and profile came out right.
- **Replay over real bench5 (read-only).**
  - `pairs_arms_v2.py --metric legacy` is byte-identical to `pairs_arms.py` on 20 label sets (the 10 ABBA batches incl. DMVX, as lever and A/A sets). That includes D23 AR avg +0.284 and D25 PW avg -0.062.
  - `--metric dec` refuses the v1 arms.
  - `aa_spread_v2.py` reproduces the review's A/A table.
  - `ab_t1_v2.py --compare` works on v1 jsonl (text-sha basis).
  - `--from-out` matches the logs, except for DMVX, which has no `ab-DMVX-*-tput.out` files (its T0 lines exist only in the logs).
