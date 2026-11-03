#!/usr/bin/env python3
"""aa_spread_v2.py [--metric legacy|dec] [--json OUT] [DIR]: A/A noise of the bench5 ABBA batches (harness1103, 11-03;
advrev M3). Read-only over DIR (default: this bench5).

Batches: every prefix X with logs ab-X-OFF, ab-X-ON, ab-X-ON2, ab-X-OFF2 that ran T0 and T1 and whose first arm started
at or after 20261103T055304Z (arm-checks.sh with warm-up; earlier arms had first-request JIT inside t1-00).
For each batch the same-condition deltas OFF2-OFF and ON2-ON are computed exactly as pairs_arms.py does (T0 p0..p2,
T1 t1-01..t1-11), and so are the lever deltas ON-OFF and ON2-OFF2. Prints:
  per-batch rows, A/A mean / sd / max|.| / count above 0.15 for T0, T1, ON2-ON and OFF2-OFF,
  the T0-T1 correlation of A/A deltas from the same comparison (rho; used for the 4- or 8-mean average),
  and the sd of the ABBA (4 means) and ABBAABBA (8 means) averages under that model.
win3.py takes its default --aa-sd / --aa-rho from this output (see the constants there)."""
import glob, json, math, os, re, statistics as st, sys

args = sys.argv[1:]
metric, jout = "legacy", None
while args and args[0].startswith("--"):
    a = args.pop(0)
    if a == "--metric":
        metric = args.pop(0)
    elif a == "--json":
        jout = args.pop(0)
    else:
        sys.exit(__doc__)
D = args[0] if args else os.path.dirname(os.path.abspath(__file__))
SINCE = "20261103T055304Z"
T0_RE = re.compile(r"TPUT (p\d) tokens (\d+) ([\d.]+) s .* rounds (\d+) ")
T1_RE = re.compile(r"T1 (t1-\d+) tokens (\d+) ([\d.]+) s .* rounds (\d+) .* sha (\w+)")
DEC_RE = re.compile(r" dec_s ([\d.]+) dec-ms/round ")


def newest(label):
    f = sorted(glob.glob(f"{D}/ab-{label}-2026*.log"))
    return f[-1] if f else None


def load(path):
    t0, t1 = {}, {}
    for line in open(path):
        dm = DEC_RE.search(line)
        for rx, dst in ((T0_RE, t0), (T1_RE, t1)):
            m = rx.match(line)
            if m:
                s = float(dm[1]) if (metric == "dec" and dm) else (float(m[3]) if metric == "legacy" else None)
                if s is not None:
                    dst[m[1]] = (s, int(m[4]), m[5] if rx is T1_RE else None)
    return t0, t1


def delta(X, Y, skip):
    keys = [k for k in X if k in Y and k not in skip and X[k][1] and Y[k][1]]
    if not keys:
        return None, 0, 0
    ds = [1e3 * (Y[k][0] / Y[k][1] - X[k][0] / X[k][1]) for k in keys]
    same = sum(1 for k in keys if X[k][2] and X[k][2] == Y[k][2])
    return st.mean(ds), same, len(keys)


batches = []
for off2 in sorted(glob.glob(f"{D}/ab-*-OFF2-2026*.log")):
    x = re.match(r".*/ab-(.+)-OFF2-2026", off2)[1]
    paths = {c: newest(f"{x}-{c}") for c in ("OFF", "ON", "ON2", "OFF2")}
    if not all(paths.values()):
        continue
    if os.path.basename(paths["OFF"]).split("-")[-1][:-4] < SINCE:
        continue
    arms = {c: load(p) for c, p in paths.items()}
    if not all(arms[c][0] and arms[c][1] for c in arms):
        continue
    row = {"batch": x}
    for which, name, skip in ((0, "T0", ()), (1, "T1", ("t1-00",))):
        A = {c: arms[c][which] for c in arms}
        row[f"{name}_aa_off"], _, _ = delta(A["OFF"], A["OFF2"], skip)
        row[f"{name}_aa_on"], _, _ = delta(A["ON"], A["ON2"], skip)
        row[f"{name}_lever_1"], s1, n1 = delta(A["OFF"], A["ON"], skip)
        row[f"{name}_lever_2"], s2, n2 = delta(A["OFF2"], A["ON2"], skip)
        if name == "T1":
            row["t1_same"] = f"{s1}/{n1},{s2}/{n2}"
    batches.append(row)

if not batches:
    sys.exit("no ABBA batch with T0+T1 logs found")


def summ(v):
    v = [x for x in v if x is not None]
    return {"n": len(v), "mean": st.mean(v), "sd": st.stdev(v) if len(v) > 1 else float("nan"),
            "max_abs": max(abs(x) for x in v), "above_0.15": sum(abs(x) > 0.15 for x in v)}


t0 = [b["T0_aa_off"] for b in batches] + [b["T0_aa_on"] for b in batches]
t1 = [b["T1_aa_off"] for b in batches] + [b["T1_aa_on"] for b in batches]
groups = {"T0 A/A": t0, "T1 A/A": t1, "T1 ON2-ON": [b["T1_aa_on"] for b in batches],
          "T1 OFF2-OFF": [b["T1_aa_off"] for b in batches], "all A/A": t0 + t1}
out = {"metric": metric, "dir": D, "since": SINCE, "batches": batches, "groups": {k: summ(v) for k, v in groups.items()}}
pairs = [(a, b) for a, b in zip(t0, t1) if a is not None and b is not None]
ma, mb = st.mean(p[0] for p in pairs), st.mean(p[1] for p in pairs)
cov = sum((a - ma) * (b - mb) for a, b in pairs) / (len(pairs) - 1)
rho = cov / (st.stdev(p[0] for p in pairs) * st.stdev(p[1] for p in pairs))
sd = out["groups"]["all A/A"]["sd"]
out["rho_t0_t1"] = rho
# k comparisons, each giving a T0 and a T1 mean with corr rho: var(avg of 2k) = sd^2 (1 + rho) / (2k)
out["sd_avg_abba"] = sd * math.sqrt((1 + rho) / 4)
out["sd_avg_abbaabba"] = sd * math.sqrt((1 + rho) / 8)

print(f"AA SPREAD metric {metric}: {len(batches)} batches ({', '.join(b['batch'] for b in batches)}), "
      f"{len(t0) + len(t1)} A/A comparisons")
for b in batches:
    print(f"AA {b['batch']}: T0 OFF2-OFF {b['T0_aa_off']:+.3f} ON2-ON {b['T0_aa_on']:+.3f} | T1 OFF2-OFF "
          f"{b['T1_aa_off']:+.3f} ON2-ON {b['T1_aa_on']:+.3f} | lever T0 {b['T0_lever_1']:+.3f} {b['T0_lever_2']:+.3f} "
          f"T1 {b['T1_lever_1']:+.3f} {b['T1_lever_2']:+.3f} same {b['t1_same']}")
for k, g in out["groups"].items():
    print(f"AA {k:12s} n {g['n']:2d} mean {g['mean']:+.3f} sd {g['sd']:.3f} max|.| {g['max_abs']:.3f} "
          f"|.|>0.15 {g['above_0.15']}/{g['n']}")
print(f"AA rho(T0,T1) {rho:+.3f}; sd single {sd:.3f}; sd of avg: ABBA (4 means) {out['sd_avg_abba']:.3f}, "
      f"ABBAABBA (8 means) {out['sd_avg_abbaabba']:.3f}")
if jout:
    with open(jout + ".new", "w") as f:
        json.dump(out, f, indent=1)
    os.replace(jout + ".new", jout)
