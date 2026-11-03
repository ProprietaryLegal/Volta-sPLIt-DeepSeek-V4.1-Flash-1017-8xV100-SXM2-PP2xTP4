"""CPU-only tests for tools/warmup.py (OPS1): request contract, cache guard, deadline, no text disclosure."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("warmup", HERE / "warmup.py")
assert SPEC and SPEC.loader
warmup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(warmup)
IDLE = 'vllm:num_requests_running{model_name="m"} 0\nvllm:num_requests_waiting{model_name="m"} 0'


def reply(count: int = 32, reason: str = "length", prompt_tokens: int = 5041, cached: int | None = 0) -> str:
    usage: dict[str, object] = {"prompt_tokens": prompt_tokens, "completion_tokens": count}
    if cached is not None:
        usage["prompt_tokens_details"] = {"cached_tokens": cached}
    return json.dumps({"usage": usage, "choices": [{"text": "DO NOT DISCLOSE", "finish_reason": reason,
                                                    "stop_reason": None}]})


class WarmupTest(unittest.TestCase):
    def test_payload_contract(self) -> None:
        body = warmup.payload('quoted"model', "salt", 1, 0)
        self.assertEqual(json.loads(json.dumps(body)), body)
        self.assertEqual(body["min_tokens"], body["max_tokens"])
        self.assertTrue(body["ignore_eos"])
        self.assertNotIn("messages", body)
        self.assertNotIn("priority", body)          # production runs FCFS
        self.assertNotEqual(body["cache_salt"], warmup.payload("m", "salt", 1, 0)["cache_salt"])

    def test_shapes_match_three_sequences(self) -> None:
        self.assertEqual(warmup.SHAPES, (1, 2, 3))

    def test_wrong_output_fails_without_text(self) -> None:
        for raw in (reply(1, "stop"), reply(32, "stop"), '{"error": "DO NOT DISCLOSE"}'):
            with self.assertRaises(ValueError) as err:
                warmup.summary(raw)
            self.assertNotIn("DO NOT DISCLOSE", str(err.exception))

    def test_any_cache_hit_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "cached"):
            warmup.summary(reply(cached=64))
        self.assertIsNone(warmup.summary(reply(cached=None))["cached_tokens"])

    def test_idle_fails_closed(self) -> None:
        for raw in ("", "vllm:num_requests_running 0", "vllm:num_requests_running NaN\nvllm:num_requests_waiting 0",
                    "vllm:num_requests_running 1\nvllm:num_requests_waiting 0"):
            with self.assertRaises(ValueError):
                warmup.idle(raw)

    def test_all_waves_without_network(self) -> None:
        bodies: list[dict[str, object]] = []

        def read(path: str, body: dict[str, object] | None) -> str:
            if body is None:
                self.assertEqual(path, "/metrics")
                return IDLE
            bodies.append(body)
            return reply()

        out = io.StringIO()
        with patch.object(warmup, "urlopen", side_effect=AssertionError("network forbidden")), redirect_stdout(out):
            waves = warmup.run("m", read)
        self.assertEqual(len(bodies), 6)
        self.assertEqual(len({str(b["prompt"]) for b in bodies}), 6)
        self.assertEqual(len({str(b["cache_salt"]) for b in bodies}), 6)
        self.assertEqual([w["concurrency"] for w in waves], [1, 2, 3])
        self.assertNotIn("DO NOT DISCLOSE", out.getvalue())

    def test_long_wave_must_exceed_chunk_and_floor(self) -> None:
        for prompt_tokens, chunk in ((4096, 1024), (5041, 8192)):
            def read(path: str, body: dict[str, object] | None, pt: int = prompt_tokens) -> str:
                return IDLE if body is None else reply(prompt_tokens=pt)
            with self.assertRaisesRegex(ValueError, "floor"), redirect_stdout(io.StringIO()):
                warmup.run("m", read, chunk=chunk)

    def test_long_prompt_is_long_and_decode_waves_short(self) -> None:
        self.assertGreater(len(str(warmup.payload("m", "s", 1, 0)["prompt"])), 20000)
        self.assertLess(len(str(warmup.payload("m", "s", 3, 0)["prompt"])), 200)

    def test_foreign_work_stops_before_post(self) -> None:
        def read(path: str, body: dict[str, object] | None) -> str:
            self.assertIsNone(body)
            return "vllm:num_requests_running 1\nvllm:num_requests_waiting 0"
        with self.assertRaises(ValueError):
            warmup.run("m", read)

    def test_deadline(self) -> None:
        posts: list[object] = []

        def read(path: str, body: dict[str, object] | None) -> str:
            if body is None:
                return IDLE
            posts.append(body)
            return reply()
        with self.assertRaisesRegex(ValueError, "deadline"):
            warmup.run("m", read, warmup.time.monotonic() - 1)
        self.assertEqual(posts, [])
        clock = [0.0]

        def slow(path: str, body: dict[str, object] | None) -> str:
            if body is None:
                return IDLE
            clock[0] += 60.0
            return reply()
        with patch.object(warmup.time, "monotonic", side_effect=lambda: clock[0]), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "before the concurrency-3 wave"):
                warmup.run("m", slow, 119.0)
        self.assertEqual(warmup.request_timeout(warmup.time.monotonic() + 1000), warmup.TIMEOUT)

    def test_wrapper_kills_a_hung_helper(self) -> None:
        with tempfile.TemporaryDirectory() as fake:
            shim = Path(fake) / "python3"
            shim.write_text("#!/bin/sh\ntrap '' TERM\nwhile :; do sleep 1; done\n")
            shim.chmod(0o755)
            env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}", "DS41_WARMUP_HARD_S": "1"}
            t0 = warmup.time.monotonic()
            done = subprocess.run(["bash", str(HERE / "warmup.sh"), "8000", "x"], env=env, capture_output=True,
                                  timeout=30)
            self.assertNotEqual(done.returncode, 0)
            self.assertLess(warmup.time.monotonic() - t0, 15)


if __name__ == "__main__":
    unittest.main()
