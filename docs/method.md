# Method

How a speed change is measured and decided on this build.

## Labels

- **MEASURED**: observed on our host, with a date and conditions.
- **ESTIMATED**: arithmetic or a model built on measurements.
- **UPSTREAM CLAIM**: someone else's published figure, which we have not reproduced.

## The unit: ms per verify round

A round is one target verification step: the target checks the drafted tokens and emits one token plus every accepted
draft. Throughput per request is R = (1 + E[A]) / C, where E[A] is the accepted drafts per round and C the round
time. Acceptance moves with the text, so tok/s moves with the prompt set. Round time is the engine-speed measure, and
every lever is decided on it.

## The A/B harness

- Every arm reboots the server on the current production stack, with or without the lever, and sends untimed warm-up
  requests first (there is no compile cache; the first request of a boot JIT-compiles about ten Triton kernels).
- T=0: 3 x 1,024-token greedy requests. T=1: a seeded 12-prompt sampled set.
- Arms run in ABBA order (OFF, ON, ON, OFF). Small levers run ABBAABBA (eight arms).
- Prompts are paired across arms when their texts are identical; paired noise is about 0.05 ms.
- No compilation, build or other load runs during a measurement arm.

## Verdict

- **WIN**: average ≤ −0.15 ms per round, no pair above +0.05 ms, and the T=1 texts the same.
- **Upstream-backed rule**: a change with a reputable published speedup that runs without errors, keeps outputs exact,
  and tests inconclusive (average ≤ +0.05 ms) stays on. Our own experiments do not get this exception.
- The second harness version (in use from 2026-11-03) times decode only, excluding the first-token time that had been
  folded into ms per round (about 1.2-1.4 ms per round), and gives a three-way verdict with the measured A/A spread.

## Detection power, and drift

The A/A spread (the same configuration measured twice) was about 0.12 ms per comparison. With that spread, a true
−0.15 ms lever passes the WIN rule about 40 % of the time, and a −0.25 ms lever about 90 %. A small lever that "loses"
was not detected; that does not prove it has no effect. In the 2026-11-03 afternoon session the A/A drift grew to
+0.5..+0.8 ms for reasons not yet known, which is why the router-floor result (−0.165 ms) is called inconclusive. A
new A/A measurement is scheduled.

## Gates

- **Greedy identity**: 8 greedy prompts compared byte for byte with a reference. A near-tie (two candidate tokens
  within a small logit margin, decided by a last-bit difference) is reported separately, under a rule fixed in advance.
- **Kernel changes**: single-GPU and TP4 bitwise checks over every changed layer and shape, then compute-sanitizer
  memcheck, racecheck and synccheck, before any server arm.
- **Switch off = unchanged**: a CPU test and an AST comparison show the default path is the old code.
- **Activation**: every ON arm must log the lever's activation line on all 8 workers, and every OFF arm none.

## Why outputs are exact

The target verifies every draft with the speculative-sampling acceptance rule (coupled keyed draws at T>0), so the text
has the target's distribution whatever the drafter proposes. Restarts at T=1 can differ in a token where two
candidates are within a last-bit logit difference; those were traced token by token and none came from a lever.
