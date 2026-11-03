#!/usr/bin/env python3
"""trace_diverge.py A.tsv B.tsv: first divergence between two VLLM_V41_COUPLED_TRACE runs (main, 11-03).

Columns (Sparks d25af68): step, row, key_lo16, out_pos, sampled, winner, runner_up, margin, winner_logit_hex,
runner_logit_hex, fused_eq_torch. Per (key, out_pos) the LAST line in file order is the verification that emitted the
token. Per key (one request = one prompt) prints: tokens compared, the first position whose winner/runner logit bits
differ, the first position whose sampled token differs, and at that position both runs' winner, runner-up, margin and
logit hex. A divergence with identical logit bits at every earlier position and at the position itself = real bug.
"""
import sys


def load(path):
    last, order, fused_bad = {}, [], 0
    for line in open(path):
        f = line.rstrip("\n").split("\t")
        if len(f) < 11:
            continue
        key, pos = int(f[2]), int(f[3])
        if f[10].strip() not in ("1", "True", "true"):
            fused_bad += 1
        if key not in last:
            last[key] = {}
            order.append(key)
        last[key][pos] = {"sampled": int(f[4]), "win": int(f[5]), "run": int(f[6]), "margin": float(f[7]),
                          "wl": f[8], "rl": f[9]}
    return last, order, fused_bad


def main():
    a, order_a, bad_a = load(sys.argv[1])
    b, order_b, bad_b = load(sys.argv[2])
    print(f"keys A {len(order_a)} B {len(order_b)}; fused!=torch lines A {bad_a} B {bad_b}")
    for i, key in enumerate(order_a):
        if key not in b:
            print(f"req {i} key {key}: missing in B")
            continue
        pa, pb = a[key], b[key]
        common = sorted(set(pa) & set(pb))
        first_bits = next((p for p in common if pa[p]["sampled"] == pb[p]["sampled"]
                           and (pa[p]["wl"], pa[p]["rl"]) != (pb[p]["wl"], pb[p]["rl"])), None)
        first_tok = next((p for p in common if pa[p]["sampled"] != pb[p]["sampled"]), None)
        if first_tok is None:
            print(f"req {i} key {key}: {len(common)} positions, tokens identical; first logit-bit change at {first_bits}")
            continue
        x, y = pa[first_tok], pb[first_tok]
        earlier_bits = first_bits is not None and first_bits < first_tok
        same_bits_here = (x["wl"], x["rl"]) == (y["wl"], y["rl"]) and x["win"] == y["win"]
        verdict = ("BUG? identical logits, different token" if same_bits_here and not earlier_bits and x["win"] != y["win"]
                   else "numerics (logit bits moved first)" if earlier_bits or not same_bits_here else "check")
        print(f"req {i} key {key}: first token diff at pos {first_tok} of {len(common)}; first logit-bit change at "
              f"{first_bits}; A win {x['win']} run {x['run']} margin {x['margin']} {x['wl']} {x['rl']} | "
              f"B win {y['win']} run {y['run']} margin {y['margin']} {y['wl']} {y['rl']} -> {verdict}")


if __name__ == "__main__":
    main()
