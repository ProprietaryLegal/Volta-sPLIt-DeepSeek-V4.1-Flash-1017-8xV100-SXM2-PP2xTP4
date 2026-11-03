#!/usr/bin/env python3
"""win3.py: three-way A/B verdict from pairs_arms.py / pairs_arms_v2.py output on stdin (harness1103, 11-03; advrev M2,
M3, H2, H4). Replaces the binary win.py for new queues; win.py and its past verdicts are left as they are.

  pairs_arms_v2.py --metric dec bench5 X-OFF X-ON X-OFF2 X-ON2 X-OFF X-OFF2 | win3.py [options]
  pairs_arms_v2.py --metric dec bench5 X-OFF X-ON X-OFF2 X-ON2 X-OFF3 X-ON3 X-OFF4 X-ON4 | win3.py --design abbaabba
  win3.py --order abba|abbaabba|abbabaab X      print the arm labels in run order and exit

Lever lines are "T0|T1 <x>-ON<n> - <x>-OFF<n>: mean ..." (ABBA: 2 pairs -> 4 means; ABBAABBA: 4 pairs -> 8 means).
A/A lines (OFFn - OFF, ONn - ON) are echoed as the in-batch noise check.

Verdict (first word of the first output line):
  WIN                    = the existing win.py rule, unchanged: average of the lever means <= -0.15 ms/round, no mean
                           above +0.05, every T1 pair with all texts the same, and the expected number of means.
  LOSE                   = the mirror rule: average >= +0.15 and no mean below -0.05 (detectably slower).
  NEUTRAL-or-UNDETECTED  = everything else, with a sub-label from the A/A noise model:
      NEUTRAL     the 95 % interval of the average lies inside (-0.15, +0.15): a WIN-sized effect is excluded;
      UNDETECTED  the interval reaches -0.15 or +0.15: an effect of WIN size can not be excluded. Most small-lever
                  "LOSE" labels from win.py are this (advrev M3); "undetected" is not "absent".
Action (second line), the owner 11-01 rule "upstream-backed + works without errors + inconclusive = keep ON":
  WIN -> ADOPT; LOSE -> REJECT; --gate FAIL -> REJECT (correctness is never relaxed);
  NEUTRAL-or-UNDETECTED + --upstream REF -> KEEP-ON(upstream) (only if the arm ran without errors: --gate PASS|NA);
  NEUTRAL-or-UNDETECTED + --upstream REF --bundle-only -> PORT-GAP (qualified upstream only inside a bundle);
  NEUTRAL-or-UNDETECTED, no upstream -> NOT-ADOPTED (re-run as ABBAABBA if the expected size is <= 0.2 ms).

Noise model (--aa-sd, --aa-rho): each lever pair gives a T0 and a T1 mean; single-comparison sd = aa-sd, corr(T0, T1) =
aa-rho, pairs independent, so sd(avg) = aa-sd * sqrt((1 + aa-rho) / n_means). Defaults are MEASURED by
aa_spread_v2.py over the 9 warm-up ABBA batches in bench5 (AR EF FP FU GU P13 PF PW SP; 36 A/A comparisons; legacy
metric; 2026-11-03): sd 0.126 (T0 0.119, T1 0.120), rho +0.264 -> sd(avg) 0.071 (ABBA) / 0.050 (ABBAABBA).
For --metric dec arms there is no A/A data yet: the legacy numbers are used and the output says so; re-run
aa_spread_v2.py --metric dec once a dec A/A pair exists and pass its numbers.
Detection power (the WIN rule under this model, 20000 draws, fixed seed) is printed with every verdict:
  ABBA      P(WIN) at true 0 / -0.10 / -0.15 / -0.20 / -0.25 ms:  2 / 23 / 48 / 74 / 91 %
  ABBAABBA  same, pair rule (unchanged WIN definition):            0 / 13 / 42 / 75 / 92 %
  ABBAABBA  --max-rule block (ceiling on each ABBA block average):  0 / 16 / 50 / 84 / 98 %
  Under the unchanged rule ABBAABBA buys position balance, fewer false WINs and a tighter interval (NEUTRAL becomes
  reachable), not more power at -0.15: the "no mean above +0.05" test gets stricter with 8 means.
TEXTS-DIFFER (sub-label): the speed meets WIN but a T1 pair has differing texts.
"""
import argparse, json, math, random, re, sys

AA_SD, AA_RHO = 0.126, 0.264          # aa_spread_v2.py, legacy metric, 9 batches / 36 A/A comparisons, 2026-11-03
WIN_AVG, WIN_MAX = -0.15, 0.05
EXPECT = {"abba": 4, "abbaabba": 8}
ORDERS = {"abba": ["OFF", "ON", "ON2", "OFF2"],
          "abbaabba": ["OFF", "ON", "ON2", "OFF2", "OFF3", "ON3", "ON4", "OFF4"],
          # ABBA then BAAB: each condition runs once in every arm position class (advrev M3 position effect)
          "abbabaab": ["OFF", "ON", "ON2", "OFF2", "ON3", "OFF3", "OFF4", "ON4"]}


def maxes(means, max_rule):
    """Values the +0.05 ceiling applies to: every mean (pair, the win.py rule) or each ABBA block's average (block)."""
    if max_rule == "pair":
        return means
    return [sum(means[i:i + 4]) / len(means[i:i + 4]) for i in range(0, len(means), 4)]


def rule(means, t1_same, n_expect, max_rule="pair"):
    avg = sum(means) / len(means)
    return len(means) == n_expect and avg <= WIN_AVG and max(maxes(means, max_rule)) <= WIN_MAX and t1_same


def power(delta, n_means, sd, rho, max_rule="pair", draws=20000, seed=1103):
    """P(WIN rule passes) when every lever mean has expectation `delta` (texts assumed same)."""
    rnd = random.Random(seed)
    k = n_means // 2
    c = math.sqrt(max(0.0, 1 - rho * rho))
    wins = 0
    for _ in range(draws):
        ms = []
        for _ in range(k):
            z0, z1 = rnd.gauss(0, 1), rnd.gauss(0, 1)
            ms += [delta + sd * z0, delta + sd * (rho * z0 + c * z1)]
        wins += sum(ms) / len(ms) <= WIN_AVG and max(maxes(ms, max_rule)) <= WIN_MAX
    return wins / draws


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", choices=sorted(EXPECT), help="default: inferred from the number of lever means")
    ap.add_argument("--upstream", metavar="REF", help="upstream source backing the lever (PR/issue/commit)")
    ap.add_argument("--bundle-only", action="store_true", help="upstream qualified it only inside a bundle")
    ap.add_argument("--gate", choices=["PASS", "FAIL", "NA"], default="NA",
                    help="correctness gate of the ON arms (greedy/neartie); FAIL forces REJECT")
    ap.add_argument("--max-rule", choices=["pair", "block"], default="pair",
                    help="pair (default) = the win.py WIN rule. block = the +0.05 ceiling on each ABBA block's average "
                         "(more power for ABBAABBA; NOT the adopted WIN definition, needs the owner's approval)")
    ap.add_argument("--aa-sd", type=float, default=AA_SD)
    ap.add_argument("--aa-rho", type=float, default=AA_RHO)
    ap.add_argument("--json", metavar="OUT", help="also write the verdict as JSON")
    ap.add_argument("--order", nargs=2, metavar=("DESIGN", "LEVER"), help="print arm labels in run order and exit")
    a = ap.parse_args()
    if a.order:
        if a.order[0] not in ORDERS:
            sys.exit(f"--order design must be one of {sorted(ORDERS)}")
        print(" ".join(f"{a.order[1]}-{c}" for c in ORDERS[a.order[0]]))
        return 0

    text = sys.stdin.read().splitlines()
    rows = [l for l in text if l.startswith(("T0 ", "T1 "))]
    lever = [r for r in rows if re.match(r"T[01] \S+-ON\d* - \S+-OFF\d*:", r)]
    aa = [r for r in rows if re.match(r"T[01] \S+-(ON|OFF)\d* - \S+-(ON|OFF)\d*:", r) and r not in lever]
    means = [float(re.search(r"mean ([+-][\d.]+)", r)[1]) for r in lever]
    t1 = [r for r in lever if r.startswith("T1")]
    t1_same = bool(t1) and all((m := re.search(r"texts same (\d+)/(\d+)", r)) and m[1] == m[2] for r in t1)
    metric = "dec" if any("ms/round-dec" in r for r in lever) else "legacy"
    n = len(means)
    design = a.design or {4: "abba", 8: "abbaabba"}.get(n)
    problems = []
    if design is None:
        problems.append(f"{n} lever means (need 4 for ABBA or 8 for ABBAABBA)")
        design = "abba"
    n_expect = EXPECT[design]
    if n != n_expect:
        problems.append(f"{n} lever means, design {design} needs {n_expect}")
    if len(t1) * 2 != n:
        problems.append(f"{len(t1)} T1 pairs for {n} means (every pair needs T0 and T1)")

    avg = sum(means) / n if n else float("nan")
    se = a.aa_sd * math.sqrt((1 + a.aa_rho) / max(n, 1))
    lo, hi = avg - 1.96 * se, avg + 1.96 * se
    if n and not problems and rule(means, t1_same, n_expect, a.max_rule):
        verdict, sub = "WIN", ""
    elif n and not problems and avg >= -WIN_AVG and min(means) >= -WIN_MAX:
        verdict, sub = "LOSE", ""
    else:
        verdict = "NEUTRAL-or-UNDETECTED"
        sub = "NEUTRAL" if (lo > WIN_AVG and hi < -WIN_AVG and not problems) else "UNDETECTED"
        if n and not problems and not t1_same and rule(means, True, n_expect, a.max_rule):
            sub = "TEXTS-DIFFER"   # fast enough for WIN, blocked only by the T1 text rule
    if a.gate == "FAIL":
        action = "REJECT (correctness gate FAIL; never relaxed)"
    elif verdict == "WIN":
        action = "ADOPT"
    elif verdict == "LOSE":
        action = "REJECT (detectably slower)"
    elif problems:
        action = "INVALID-BATCH (fix the arms; no verdict)"
    elif sub == "TEXTS-DIFFER":
        action = ("NOT-ADOPTED (speed meets WIN but T1 texts differ: an exact lever is broken; a numerics-changing "
                  "lever needs the approved near-tie gate and an owner decision, the WIN rule cannot pass it)")
    elif a.upstream and a.bundle_only:
        action = f"PORT-GAP (upstream {a.upstream} qualified it only inside a bundle; not adopted alone, not blocking)"
    elif a.upstream:
        action = (f"KEEP-ON(upstream {a.upstream}; the owner 11-01: upstream-backed, inconclusive; valid only if it ran "
                  f"without errors{'' if a.gate == 'PASS' else ' and passes the correctness gate'})")
    else:
        action = ("NOT-ADOPTED (" + ("no WIN-sized effect" if sub == "NEUTRAL" else "undetected, not absent")
                  + ("; re-run as ABBAABBA if expected <= 0.2 ms" if design == "abba" else "") + ")")
    pw = {d: power(d, n_expect, a.aa_sd, a.aa_rho, a.max_rule) for d in (0.0, -0.10, -0.15, -0.20, -0.25)}
    print(f"{verdict}{' ' + sub if sub else ''} means {means} avg {avg:+.3f} max {max(means) if means else float('nan'):+.3f} "
          f"t1-texts-same {t1_same} design {design} metric {metric}{'' if a.max_rule == 'pair' else ' max-rule block'}")
    print(f"ACTION {action}")
    print(f"NOISE sd(avg) {se:.3f} (aa-sd {a.aa_sd}, rho {a.aa_rho}{', legacy A/A used for dec' if metric == 'dec' and a.aa_sd == AA_SD else ''}); "
          f"95% interval of avg [{lo:+.3f}, {hi:+.3f}]")
    print(f"POWER ({a.max_rule} rule) P(WIN) at true " + ", ".join(f"{d:+.2f}: {100 * p:.0f}%" for d, p in pw.items()))
    for r in aa:
        print(f"A/A {r}")
    for p in problems:
        print(f"PROBLEM {p}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"verdict": verdict, "sub": sub, "action": action, "means": means, "avg": avg,
                       "t1_texts_same": t1_same, "design": design, "metric": metric, "se": se, "ci95": [lo, hi],
                       "power": {str(k): v for k, v in pw.items()}, "upstream": a.upstream,
                       "bundle_only": a.bundle_only, "gate": a.gate, "problems": problems, "aa_lines": aa}, f, indent=1)
    return 0 if verdict == "WIN" else (1 if verdict == "LOSE" else 2)


if __name__ == "__main__":
    sys.exit(main())
