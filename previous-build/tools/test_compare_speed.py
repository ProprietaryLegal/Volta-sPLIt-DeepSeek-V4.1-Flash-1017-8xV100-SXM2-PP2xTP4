"""CPU-only tests for tools/compare_speed.py: change, bootstrap CI and the promotion rule on synthetic speed files."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("compare_speed", HERE / "compare_speed.py")
assert SPEC and SPEC.loader
cs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cs)


def arm(label: str, cold: list[float], warm: list[float], decode: float = 42.0) -> dict:
    rows = []
    for cell, ttfts in (("cold", cold), ("warm", warm)):
        for t in ttfts:
            rows.append({"cell": cell, "ttft_s": t, "prefill_tok_s": 75000 / t, "decode_tok_s": decode})
    return {"label": label, "rows": rows}


class CompareSpeedTest(unittest.TestCase):
    def test_clear_win_is_promoted(self) -> None:
        control = arm("control", [46.0, 44.0, 48.0, 45.0, 47.0, 46.0], [27.0, 27.1, 27.0, 26.9, 27.0, 27.1])
        cand = arm("cand", [26.0, 25.8, 26.1, 25.9, 26.0, 25.7], [25.8, 25.7, 25.8, 25.7, 25.8, 25.7])
        res = cs.compare(control, cand)
        self.assertLess(res["cold"]["ttft_s"]["change_pct"], -40)
        self.assertTrue(res["cold"]["ttft_s"]["ci_excludes_0"])
        self.assertTrue(res["promote_speed"])

    def test_noise_is_not_promoted(self) -> None:
        control = arm("control", [46.0, 40.0, 52.0, 38.0, 50.0, 44.0], [27.0] * 6)
        cand = arm("cand", [45.0, 41.0, 51.0, 39.0, 49.0, 45.0], [27.0] * 6)
        res = cs.compare(control, cand)
        self.assertFalse(res["cold"]["ttft_s"]["ci_excludes_0"])
        self.assertFalse(res["promote_speed"])

    def test_decode_regression_blocks_promotion(self) -> None:
        control = arm("control", [46.0] * 3 + [45.0] * 3, [27.0] * 6, decode=42.0)
        cand = arm("cand", [40.0] * 3 + [39.0] * 3, [26.0] * 6, decode=38.0)
        res = cs.compare(control, cand)
        self.assertTrue(res["cold"]["ttft_s"]["ci_excludes_0"])
        self.assertLess(res["cold"]["decode_tok_s"]["change_pct"], -3)
        self.assertFalse(res["promote_speed"])


if __name__ == "__main__":
    unittest.main()
