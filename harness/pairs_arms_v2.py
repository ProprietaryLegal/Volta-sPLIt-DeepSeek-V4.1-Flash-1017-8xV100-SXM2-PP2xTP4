#!/usr/bin/env python3
"""pairs_arms_v2.py [--metric legacy|dec] [--from-out] DIR LABEL_A LABEL_B [LABEL_C LABEL_D ...]
(harness1103, 11-03; advrev H2). Paired per-prompt ms/round deltas between arms, as pairs_arms.py, plus a decode-only
metric for arms run with ab_t1_v2.py.

  --metric legacy (default)  wall time / rounds, exactly pairs_arms.py: on the same logs the output is byte-identical
                             (identity proof in README-v2-harness.md).
  --metric dec               dec_s / rounds from the v2 fields (first -> last streamed token; TTFT and teardown out).
                             Every label must be a v2 arm; a v1 arm is refused, never mixed.
  --from-out                 read DIR/ab-<LABEL>-tput.out and ab-<LABEL>-t1.out instead of the newest
                             DIR/ab-<LABEL>-2026*.log (same lines; the .out files are rewritten when a label re-runs).

Labels come in pairs (X Y -> Y minus X). T=0 pairs p0..p2; T=1 pairs t1-01..t1-11 (t1-00 dropped, as v1). For T=1 it
prints how many prompts are the same output: by token ids (toksha) when both arms are v2, else by text sha.
Works for ABBA (OFF ON OFF2 ON2 ...) and ABBAABBA (... OFF3 ON3 OFF4 ON4) label lists alike."""
import glob, re, statistics as st, sys

args = sys.argv[1:]
metric, from_out = "legacy", False
while args and args[0].startswith("--"):
    a = args.pop(0)
    if a == "--metric":
        metric = args.pop(0)
    elif a.startswith("--metric="):
        metric = a.split("=", 1)[1]
    elif a == "--from-out":
        from_out = True
    else:
        sys.exit(f"unknown option {a}")
if metric not in ("legacy", "dec") or len(args) < 3:
    sys.exit(__doc__)
D = args[0]

T0_RE = re.compile(r"TPUT (p\d) tokens (\d+) ([\d.]+) s .* rounds (\d+) ")
T1_RE = re.compile(r"T1 (t1-\d+) tokens (\d+) ([\d.]+) s .* rounds (\d+) .* sha (\w+)")
DEC_RE = re.compile(r" dec_s ([\d.]+) dec-ms/round \S+ toksha (\w+)")


def lines_of(label):
    if from_out:
        files = [f for f in (f"{D}/ab-{label}-tput.out", f"{D}/ab-{label}-t1.out") if glob.glob(f)]
        if not files:
            sys.exit(f"no .out for {label}")
        return [line for f in files for line in open(f)]
    files = sorted(glob.glob(f"{D}/ab-{label}-2026*.log"))
    if not files:
        sys.exit(f"no log for {label}")
    return list(open(files[-1]))


def load(label):
    t0, t1 = {}, {}
    for line in lines_of(label):
        dm = DEC_RE.search(line)
        dec, toksha = (float(dm[1]), dm[2]) if dm else (None, None)
        m = T0_RE.match(line)
        if m:
            t0[m[1]] = (float(m[3]), int(m[4]), None, dec, toksha)
        m = T1_RE.match(line)
        if m:
            t1[m[1]] = (float(m[3]), int(m[4]), m[5], dec, toksha)   # " toksha" never matches " sha "
    if metric == "dec":
        missing = [k for d in (t0, t1) for k, v in d.items() if v[3] is None]
        if missing or not (t0 or t1):
            sys.exit(f"{label}: no dec_s on {missing or 'any line'}: not a v2 (ab_t1_v2.py) arm; use --metric legacy")
    return t0, t1


def per_round(v):
    return (v[3] if metric == "dec" else v[0]) / v[1]


labels = args[1:]
arms = {l: load(l) for l in labels}
for i in range(0, len(labels) - 1, 2):
    x, y = labels[i], labels[i + 1]
    for which, name, skip in ((0, "T0", ()), (1, "T1", ("t1-00",))):
        X, Y = arms[x][which], arms[y][which]
        keys = [k for k in X if k in Y and k not in skip and X[k][1] and Y[k][1]]
        if not keys:
            continue
        ds = [1e3 * (per_round(Y[k]) - per_round(X[k])) for k in keys]
        if all(X[k][4] and Y[k][4] for k in keys):   # both v2: same output = same token ids
            same = sum(1 for k in keys if X[k][4] == Y[k][4])
        else:
            same = sum(1 for k in keys if X[k][2] and X[k][2] == Y[k][2])
        tag = f" texts same {same}/{len(keys)}" if which == 1 else ""
        unit = "ms/round" if metric == "legacy" else "ms/round-dec"
        print(f"{name} {y} - {x}: mean {st.mean(ds):+.3f} {unit}, negative {sum(d < 0 for d in ds)}/{len(ds)}{tag}")
