#!/usr/bin/env python3
"""Compare two arms' speed.json files under our promotion rule (docs/method.md).

  python3 tools/compare_speed.py <control speed.json> <candidate speed.json> [--json out.json]

For each cell (cold, warm) and metric (ttft_s, prefill_tok_s, decode_tok_s): means, the candidate's change in %, and a
95 % bootstrap CI of that change (unpaired: arms are separate restarts with disjoint seeds; 20,000 resamples, fixed
seed). Promotion: cold TTFT better by >= 2 % with the CI excluding 0, and decode not more than 3 % worse.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from pathlib import Path
from typing import Any

METRICS = (("ttft_s", -1), ("prefill_tok_s", 1), ("decode_tok_s", 1))   # sign: +1 = higher is better


def boot_ci(a: list[float], b: list[float], n: int = 20000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    diffs = []
    for _ in range(n):
        ma = statistics.mean(rng.choice(a) for _ in a)
        mb = statistics.mean(rng.choice(b) for _ in b)
        diffs.append((mb - ma) / ma * 100)
    diffs.sort()
    return diffs[int(0.025 * n)], diffs[int(0.975 * n) - 1]


def compare(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"control": control["label"], "candidate": candidate["label"]}
    for cell in ("cold", "warm"):
        ca = [r for r in control["rows"] if r["cell"] == cell]
        cb = [r for r in candidate["rows"] if r["cell"] == cell]
        if not ca or not cb:
            continue
        row: dict[str, Any] = {"n": [len(ca), len(cb)]}
        for metric, sign in METRICS:
            a = [float(r[metric]) for r in ca]
            b = [float(r[metric]) for r in cb]
            change = (statistics.mean(b) - statistics.mean(a)) / statistics.mean(a) * 100
            lo, hi = boot_ci(a, b)
            row[metric] = {"control_mean": round(statistics.mean(a), 2), "candidate_mean": round(statistics.mean(b), 2),
                           "change_pct": round(change, 2), "ci95_pct": [round(lo, 2), round(hi, 2)],
                           "better": (change * sign) > 0, "ci_excludes_0": lo > 0 or hi < 0}
        out[cell] = row
    cold = out.get("cold", {})
    if cold:
        t = cold["ttft_s"]
        d = cold["decode_tok_s"]
        gain = -t["change_pct"]
        out["promote_speed"] = gain >= 2 and t["ci_excludes_0"] and d["change_pct"] >= -3
        out["rule"] = "cold TTFT >= 2 % better with 95 % CI excluding 0; decode not more than 3 % worse"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("control", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    res = compare(json.loads(a.control.read_text()), json.loads(a.candidate.read_text()))
    print(json.dumps(res, indent=1))
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
