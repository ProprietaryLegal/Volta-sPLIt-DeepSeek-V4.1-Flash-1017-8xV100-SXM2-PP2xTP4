# Four cards

> **Not current (2026-11-05).** The four-card series below predates the production patches 0052-0057 (tiled and fused
> index scorers, drafter sharding, Model Runner V2, the all-reduce push path and the prefill expert GEMM), so it does
> not reproduce the 2026-11-05 checkpoint, and its four-GPU smoke test (D40, 2026-11-04) failed to boot. The section was
> taken off the front page for now; this page stays as the record of what was built.

The engine of this build packaged for a single 4x V100-SXM2-32GB NVLink board: TP4, PP=1, all 40 layers on every rank,
the layout 1Cat #1277 itself targets. Everything is in [forks/1cat-4xv100-tp4/](../forks/1cat-4xv100-tp4/); its README
is the full reference.

- **What it is:** a 49-patch series against #1277 (`899e9ed33`) that rebuilds our source tree exactly (tree
  `b0d692425297`, checked by `tools/apply_series.sh`), a serving profile, a lever environment, and install, start, stop,
  verify and smoke scripts.
- **Levers:** every adopted lever works at PP=1 except keep-batch, which is a no-op without pipeline stages (code trace,
  not a GPU run). The expert-kernel diet applies to the same tree ([engine/production/](../engine/production/)) but is not
  in the four-card profile yet.
- **Memory:** every expert resident is impossible on four cards (the routed experts alone are 132.07 GB, UPSTREAM), so
  the profile keeps #1277's cold-expert share of 0.33, served from host memory. ESTIMATED host RAM: about 165 GB; plan for
  192 GB or more.
- **What to expect:** MEASURED on one board of our host with #1277 and no levers (2026-11-02): warm decode 27.8 ms per
  round; warm real text 30.8 ms, 97.1 tok/s; fresh text 116.7 ms, 25.0 tok/s, limited by cold-expert fetches over our
  shared Gen3 x16 uplink. ESTIMATED with the levers: a warm round of about 24-25 ms and the coupled-draft T=1 gain; fresh
  text moves far less.
- **Status: GPU-unverified.** Built and CPU-tested on 2026-11-03 (37 test files plus a new PP=1 test; three stale
  fixtures fail on the production tree as well). The four-GPU smoke test (D40, 2026-11-04) failed at boot; the series
  will be rebuilt on the current patches before it is tried again
  ([roadmap](roadmap.md)).
