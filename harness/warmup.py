#!/usr/bin/env python3
"""warmup.py URL: untimed warm-up after a boot (main, 11-03; REVIEW1103 F1/F2). The served config has no compile
cache (CompilationMode NONE), but the first request of every boot JITs ~10 Triton kernels (index top-k, routing,
gather) and the first T=1 request JITs the coupled-draft path; that spike sat inside t1-00 and skewed T1 TOTALs.
Sends one T=0 chat request (thinking off) and one seeded T=1 request (top_p 1, thinking on), 128 tokens each.
Prints WARMUP OK or WARMUP FAILED; exit status 1 on failure."""
import json, sys, time, urllib.request
URL = sys.argv[1]
REQS = [{"messages": [{"role": "user", "content": "List five uses of a paperclip."}], "temperature": 0,
         "max_tokens": 128, "ignore_eos": True, "chat_template_kwargs": {"thinking": False}},
        {"messages": [{"role": "user", "content": "What is 17 times 23? Think it through."}], "temperature": 1.0,
         "top_p": 1.0, "seed": 7, "max_tokens": 128}]
try:
    for i, r in enumerate(REQS):
        body = json.dumps(dict(model="deepseek-v4.1-flash", **r)).encode()
        t0 = time.time()
        out = json.load(urllib.request.urlopen(urllib.request.Request(
            URL + "/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=600))
        print(f"WARMUP req{i} tokens {out['usage']['completion_tokens']} {time.time() - t0:.2f} s", flush=True)
    print("WARMUP OK")
except Exception as e:
    print(f"WARMUP FAILED {type(e).__name__}: {str(e)[:200]}")
    sys.exit(1)
