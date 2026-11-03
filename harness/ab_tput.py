#!/usr/bin/env python3
"""ab_tput.py URL [N]: decode throughput on the PP2 server. Public prompts, T=0, thinking off, ignore_eos,
1024 tokens each; prints tok/s, rounds, tokens/round, ms/round from /metrics deltas (one request at a time)."""
import json, sys, time, urllib.request
URL = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
PROMPTS = ["Write a detailed 900-word essay on the history of the printing press.",
           "Explain, step by step and with examples, how a hash table works and how collisions are resolved.",
           "Write a Python module that parses CSV files, validates each row against a schema, and reports errors. Include docstrings and tests."]
def metrics():
    t = urllib.request.urlopen(URL + "/metrics", timeout=30).read().decode()
    v = {}
    for line in t.splitlines():
        for k in ("vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_accepted_tokens_total"):
            if line.startswith(k + "{"): v[k] = float(line.split()[-1])
    return v
tot_t = tot_n = tot_r = 0
for i in range(N):
    p = PROMPTS[i % len(PROMPTS)]
    body = json.dumps({"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": p}], "temperature": 0,
                       "max_tokens": 1024, "ignore_eos": True, "chat_template_kwargs": {"thinking": False}}).encode()
    a = metrics(); t0 = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(URL + "/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=600))
    dt = time.time() - t0; b = metrics()
    n = r["usage"]["completion_tokens"]
    rounds = b.get("vllm:spec_decode_num_drafts_total", 0) - a.get("vllm:spec_decode_num_drafts_total", 0)
    acc = b.get("vllm:spec_decode_num_accepted_tokens_total", 0) - a.get("vllm:spec_decode_num_accepted_tokens_total", 0)
    tot_t += dt; tot_n += n; tot_r += rounds
    print(f"TPUT p{i % len(PROMPTS)} tokens {n} {dt:.2f} s {n/dt:.1f} tok/s rounds {rounds:.0f} tok/round {n/max(rounds,1):.2f} acc/round {acc/max(rounds,1):.2f} ms/round {dt*1e3/max(rounds,1):.1f}", flush=True)
print(f"TPUT TOTAL {tot_n} tokens {tot_t:.2f} s {tot_n/tot_t:.1f} tok/s tok/round {tot_n/max(tot_r,1):.2f} ms/round {tot_t*1e3/max(tot_r,1):.1f}")
