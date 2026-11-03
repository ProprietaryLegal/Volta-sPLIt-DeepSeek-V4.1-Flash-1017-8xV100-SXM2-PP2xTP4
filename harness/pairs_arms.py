#!/usr/bin/env python3
"""pairs_arms.py DIR LABEL_A LABEL_B [LABEL_C LABEL_D ...]: paired per-prompt ms/round deltas between A/B arms
(main, 11-03; after REVIEW1103 F1, adapted from its s8.py). Reads DIR/ab-<LABEL>-*.log (latest per label). Labels come in
pairs (X Y -> Y minus X). T=0 pairs p0..p2; T=1 pairs t1-01..t1-11 (t1-00 dropped: first-request JIT in older arms).
For T=1 it also prints how many prompt texts match (sha); deltas are exact pairs only when texts match.
Paired noise floor on identical texts was ~0.05-0.07 ms (REVIEW1103)."""
import glob, re, statistics as st, sys
D = sys.argv[1]
def load(label):
    files = sorted(glob.glob(f"{D}/ab-{label}-2026*.log"))
    if not files:
        sys.exit(f"no log for {label}")
    t0, t1 = {}, {}
    for line in open(files[-1]):
        m = re.match(r"TPUT (p\d) tokens (\d+) ([\d.]+) s .* rounds (\d+) ", line)
        if m: t0[m[1]] = (float(m[3]), int(m[4]), None)
        m = re.match(r"T1 (t1-\d+) tokens (\d+) ([\d.]+) s .* rounds (\d+) .* sha (\w+)", line)
        if m: t1[m[1]] = (float(m[3]), int(m[4]), m[5])
    return t0, t1
labels = sys.argv[2:]
arms = {l: load(l) for l in labels}
for i in range(0, len(labels) - 1, 2):
    x, y = labels[i], labels[i + 1]
    for which, name, skip in ((0, "T0", ()), (1, "T1", ("t1-00",))):
        X, Y = arms[x][which], arms[y][which]
        keys = [k for k in X if k in Y and k not in skip and X[k][1] and Y[k][1]]
        if not keys:
            continue
        ds = [1e3 * (Y[k][0] / Y[k][1] - X[k][0] / X[k][1]) for k in keys]
        same = sum(1 for k in keys if X[k][2] and X[k][2] == Y[k][2])
        tag = f" texts same {same}/{len(keys)}" if which == 1 else ""
        print(f"{name} {y} - {x}: mean {st.mean(ds):+.3f} ms/round, negative {sum(d < 0 for d in ds)}/{len(ds)}{tag}")
