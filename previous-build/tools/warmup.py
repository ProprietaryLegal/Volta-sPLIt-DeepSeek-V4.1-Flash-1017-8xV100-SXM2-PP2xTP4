#!/usr/bin/env python3
"""Bounded startup warm-up for the V100 DeepSeek server (OPS1); importing this module sends nothing.

Port of DGX sPLIce's `offload/launch/warmup.py`:
- waves of 1, 2, 3 concurrent requests (production's MAX_NUM_SEQS is 3);
- wave 1 is a long raw-completion prompt that must be longer than the prefill chunk
  (DS41_MAX_BATCHED_TOKENS, default 1024) and longer than 4,096 tokens, so full and partial chunks run for PC1's
  chunk sizes as well;
- every request carries a fresh cache_salt and its own prefix, and any prefix-cache hit fails the warm-up;
- 32 tokens per request (ignore_eos);
- raw /v1/completions, so no chat, reasoning or tool parser is involved;
- an overall deadline (DS41_WARMUP_DEADLINE_S, default 150 s);
- it refuses to start a wave unless /metrics shows 0 running and 0 waiting.

Output is aggregate only (token counts, elapsed); generated text is never printed.
  python3 tools/warmup.py --port 8000 --model deepseek-v4.1-flash
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
import time
from threading import Barrier
from typing import Callable, cast
from urllib.request import Request, urlopen
import uuid

BUDGET = 32
SHAPES = (1, 2, 3)
TIMEOUT = 90
LONG_FLOOR = 4096
DEADLINE_S = float(os.environ.get("DS41_WARMUP_DEADLINE_S", "150"))
CHUNK = int(os.environ.get("DS41_MAX_BATCHED_TOKENS", "1024"))
Reader = Callable[[str, "dict[str, object] | None"], str]


def obj(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return cast(dict[str, object], value)


def payload(model: str, salt: str, wave: int, index: int) -> dict[str, object]:
    prompt = f"Internal startup {salt} wave {wave} stream {index}.\n"
    prompt += "".join(
        f"Paragraph {i}. The system reads a numbered record and checks each entry against its stored value. "
        for i in range(240 if wave == 1 else 1)
    )
    return {"model": model, "prompt": prompt, "temperature": 0, "n": 1,
            "max_tokens": BUDGET, "min_tokens": BUDGET, "ignore_eos": True,
            "stop": [], "stop_token_ids": [], "stream": False,
            "cache_salt": f"{salt}-{wave}-{index}-{uuid.uuid4().hex}"}


def summary(raw: str) -> dict[str, object]:
    data = obj(json.loads(raw))
    usage = obj(data.get("usage"))
    count = usage.get("completion_tokens")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("warm-up requires exactly one completion per request")
    choice = obj(choices[0])
    reason = choice.get("finish_reason")
    stop = choice.get("stop_reason")
    result: dict[str, object] = {
        "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": count,
        "cached_tokens": obj(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        "finish_reason": reason if reason in ("length", "stop") else "unexpected",
        "stop_reason": stop if type(stop) is int or stop is None else "string-present",
    }
    if type(count) is not int or count != BUDGET or reason != "length" or stop is not None:
        raise ValueError("warm-up output contract failed: " + json.dumps(result, sort_keys=True))
    cached = result["cached_tokens"]
    if cached is not None and cached != 0:
        raise ValueError("warm-up request reused cached tokens: " + json.dumps(result, sort_keys=True))
    return result


def idle(raw: str) -> None:
    for name in ("vllm:num_requests_running", "vllm:num_requests_waiting"):
        values = []
        for line in raw.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0].split("{")[0] == name:
                values.append(float(fields[1]))
        if not values or any(not math.isfinite(v) or v != 0 for v in values):
            raise ValueError(f"warm-up refused: {name} missing, invalid or nonzero")


def request_timeout(end: float) -> float:
    left = end - time.monotonic()
    if left <= 0:
        raise ValueError(f"warm-up deadline {DEADLINE_S:.0f} s reached")
    return min(float(TIMEOUT), left)


def run(model: str, read: Reader, end: float | None = None, chunk: int = CHUNK) -> list[dict[str, object]]:
    end = time.monotonic() + DEADLINE_S if end is None else end
    salt = uuid.uuid4().hex
    waves = []
    for size in SHAPES:
        if time.monotonic() >= end:
            raise ValueError(f"warm-up deadline {DEADLINE_S:.0f} s reached before the concurrency-{size} wave")
        idle(read("/metrics", None))
        gate = Barrier(size)

        def one(index: int) -> dict[str, object]:
            request = payload(model, salt, size, index)
            gate.wait(timeout=5)
            result = summary(read("/v1/completions", request))
            if size == 1:
                tokens = result["prompt_tokens"]
                if type(tokens) is not int or tokens <= max(chunk, LONG_FLOOR):
                    raise ValueError(f"warm-up long prompt ({tokens} tokens) is not longer than the "
                                     f"{max(chunk, LONG_FLOOR)}-token floor")
            return result

        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=size) as pool:
            results = list(pool.map(one, range(size)))
        wave = {"warmup": "completed", "concurrency": size, "elapsed_s": round(time.monotonic() - start, 3),
                "requests": results}
        waves.append(wave)
        print(json.dumps(wave, sort_keys=True), flush=True)
    if time.monotonic() > end:
        raise ValueError(f"warm-up finished after its {DEADLINE_S:.0f} s deadline")
    return waves


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("invalid port")
    end = time.monotonic() + DEADLINE_S

    def read(path: str, body: dict[str, object] | None) -> str:
        request = Request(f"http://127.0.0.1:{args.port}{path}",
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=request_timeout(end)) as response:
            return response.read(1 << 20).decode()

    t0 = time.monotonic()
    try:
        run(args.model, read, end)
    except Exception as exc:  # HTTP error strings carry the status, not the body
        parser.exit(1, f"warm-up FAILED ({type(exc).__name__}): {exc}\n")
    print(json.dumps({"warmup": "done", "total_s": round(time.monotonic() - t0, 3)}), flush=True)


if __name__ == "__main__":
    main()
