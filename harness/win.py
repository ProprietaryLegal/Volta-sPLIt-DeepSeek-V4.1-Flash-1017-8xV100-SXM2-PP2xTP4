#!/usr/bin/env python3
"""win.py: read pairs_arms.py output for labels OFF ON OFF2 ON2 OFF OFF2 on stdin; print WIN or LOSE (main, 11-03).
WIN needs: the four ON-minus-OFF means average <= -0.15 ms/round, none above +0.05, and both T1 pairs with all texts same."""
import re, sys
rows = [l for l in sys.stdin.read().splitlines() if l.startswith(("T0 ", "T1 "))]
on = [r for r in rows if re.match(r"T[01] \S+-ON2? - \S+-OFF2?:", r)]
means = [float(re.search(r"mean ([+-][\d.]+)", r)[1]) for r in on]
t1 = [r for r in on if r.startswith("T1")]
same = all((m := re.search(r"texts same (\d+)/(\d+)", r)) and m[1] == m[2] for r in t1)
ok = len(means) == 4 and len(t1) == 2 and sum(means) / 4 <= -0.15 and max(means) <= 0.05 and same
print(("WIN" if ok else "LOSE") + f" means {means} avg {sum(means)/max(len(means),1):+.3f} t1-texts-same {same}")
