#!/usr/bin/env python3
"""smoke_client.py URL MODEL OUTDIR [--reference FILE]: GPU smoke of the 4-card fork's server (stdlib only).

Public prompts only; everything generated goes to OUTDIR (outside the repository), never into the repo.
  warm      one untimed short request (graphs, cold experts)
  greedy    T=0, thinking off, 3 prompts x 192 tokens, each sent twice: the two runs must be token-identical (GREEDY
            PASS/FAIL). With --reference (an earlier greedy.json), the first divergence from it is classed NEAR-TIE
            when the reference's top-2 log-probability gap there is under 0.9 nats, else DIFF (report only).
  tput      T=0 3 x 1024 tokens and T=1 (seeded) 2 x 1024 tokens, ignore_eos: tok/s, rounds, tokens/round and
            ms/round from /metrics deltas (vllm:spec_decode_num_drafts_total = one verify round per draft batch).
  session   a two-turn chat whose second prompt extends the first, to trigger the same-session prefix hit
            (restore_prefix and the #1341 hot refill log their first hit).
Prints one summary line per check (GREEDY, TPUT T0, TPUT T1, SESSION) and writes OUTDIR/greedy.json + smoke.json.
"""
import argparse, json, os, sys, time, urllib.request

GREEDY_PROMPTS = [
    "List the planets of the solar system in order from the Sun, with one sentence about each.",
    "Explain how binary search works and give its time complexity.",
    "Write a short Python function that returns the n-th Fibonacci number iteratively, with a docstring.",
]
TPUT_PROMPTS = [
    "Write a detailed 900-word essay on the history of the printing press.",
    "Explain, step by step and with examples, how a hash table works and how collisions are resolved.",
    "Write a Python module that parses CSV files, validates each row against a schema, and reports errors. "
    "Include docstrings and tests.",
]


def post(url, body, timeout=900):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def metrics(base):
    text = urllib.request.urlopen(base + "/metrics", timeout=30).read().decode()
    out = {}
    for line in text.splitlines():
        for k in ("vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_accepted_tokens_total"):
            if line.startswith(k + "{") or line.startswith(k + " "):
                out[k] = out.get(k, 0.0) + float(line.split()[-1])
    return out


def chat(base, model, messages, max_tokens, temperature=0.0, seed=None, logprobs=False, ignore_eos=False):
    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "chat_template_kwargs": {"thinking": False}}
    if seed is not None:
        body["seed"] = seed
    if ignore_eos:
        body["ignore_eos"] = True
    if logprobs:
        body["logprobs"] = True
        body["top_logprobs"] = 2
    return post(base + "/v1/chat/completions", body)


def tokens_of(resp):
    rows = (resp["choices"][0].get("logprobs") or {}).get("content") or []
    out = []
    for r in rows:
        tops = sorted((t["logprob"] for t in r.get("top_logprobs") or []), reverse=True)
        gap = tops[0] - tops[1] if len(tops) > 1 else None
        out.append({"t": r["token"], "lp": r["logprob"], "gap": gap})
    return out


def greedy(base, model, ref):
    runs, ok = [], True
    for i, p in enumerate(GREEDY_PROMPTS):
        a = tokens_of(chat(base, model, [{"role": "user", "content": p}], 192, logprobs=True))
        b = tokens_of(chat(base, model, [{"role": "user", "content": p}], 192, logprobs=True))
        same = [x["t"] for x in a] == [x["t"] for x in b]
        ok &= same and len(a) > 0
        line = f"greedy p{i}: {len(a)} tokens, repeat {'IDENTICAL' if same else 'DIFFERS'}"
        if ref is not None and i < len(ref):
            r = ref[i]
            k = next((j for j, (x, y) in enumerate(zip(a, r)) if x["t"] != y["t"]), None)
            if k is None and len(a) == len(r):
                line += "; reference IDENTICAL"
            elif k is None:
                line += f"; reference same prefix, length {len(a)} vs {len(r)}"
            else:
                gap = r[k]["gap"]
                kind = "NEAR-TIE" if gap is not None and gap < 0.9 else "DIFF"
                line += f"; reference {kind} at token {k} (reference top-2 gap {gap})"
        print(line, flush=True)
        runs.append(a)
    return ok, runs


def tput(base, model, temperature, n, seed=None):
    tot_t = tot_n = tot_r = tot_a = 0.0
    for i in range(n):
        p = TPUT_PROMPTS[i % len(TPUT_PROMPTS)]
        m0, t0 = metrics(base), time.time()
        r = chat(base, model, [{"role": "user", "content": p}], 1024, temperature=temperature,
                 seed=None if seed is None else seed + i, ignore_eos=True)
        dt, m1 = time.time() - t0, metrics(base)
        k = r["usage"]["completion_tokens"]
        rounds = m1.get("vllm:spec_decode_num_drafts_total", 0) - m0.get("vllm:spec_decode_num_drafts_total", 0)
        acc = (m1.get("vllm:spec_decode_num_accepted_tokens_total", 0)
               - m0.get("vllm:spec_decode_num_accepted_tokens_total", 0))
        tot_t += dt; tot_n += k; tot_r += rounds; tot_a += acc
        print(f"tput T{temperature:g} p{i}: {k} tokens {dt:.2f} s {k / dt:.1f} tok/s rounds {rounds:.0f} "
              f"tok/round {k / max(rounds, 1):.2f} acc/round {acc / max(rounds, 1):.2f} "
              f"ms/round {dt * 1e3 / max(rounds, 1):.1f}", flush=True)
    return {"tokens": tot_n, "seconds": round(tot_t, 3), "tok_s": round(tot_n / tot_t, 2),
            "tok_round": round(tot_n / max(tot_r, 1), 3), "acc_round": round(tot_a / max(tot_r, 1), 3),
            "ms_round": round(tot_t * 1e3 / max(tot_r, 1), 2)}


def session(base, model):
    m = [{"role": "user", "content": "Name three rivers in Europe and one fact about each."}]
    a = chat(base, model, m, 96)["choices"][0]["message"]["content"] or ""
    m += [{"role": "assistant", "content": a}, {"role": "user", "content": "Now name two more."}]
    b = chat(base, model, m, 64)
    return {"turn1_chars": len(a), "turn2_tokens": b["usage"]["completion_tokens"],
            "turn2_cached": ((b["usage"].get("prompt_tokens_details") or {}).get("cached_tokens"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("model"); ap.add_argument("outdir")
    ap.add_argument("--reference")
    ap.add_argument("--skip", default="", help="comma list of checks to skip: greedy,tput,session")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    skip = set(filter(None, a.skip.split(",")))
    ref = json.load(open(a.reference)) if a.reference else None
    out = {"url": a.url}
    t0 = time.time(); chat(a.url, a.model, [{"role": "user", "content": "Say hello."}], 16)
    print(f"WARM first request {time.time() - t0:.1f} s", flush=True)
    ok = True
    if "greedy" not in skip:
        g_ok, runs = greedy(a.url, a.model, ref)
        json.dump(runs, open(os.path.join(a.outdir, "greedy.json"), "w"))
        print(f"GREEDY {'PASS' if g_ok else 'FAIL'} (repeat identity, {len(runs)} prompts)", flush=True)
        out["greedy_pass"] = g_ok; ok &= g_ok
    if "tput" not in skip:
        out["t0"] = tput(a.url, a.model, 0.0, 3)
        print("TPUT T0 " + json.dumps(out["t0"]), flush=True)
        out["t1"] = tput(a.url, a.model, 1.0, 2, seed=1)
        print("TPUT T1 " + json.dumps(out["t1"]), flush=True)
    if "session" not in skip:
        out["session"] = session(a.url, a.model)
        print("SESSION " + json.dumps(out["session"]), flush=True)
    json.dump(out, open(os.path.join(a.outdir, "smoke.json"), "w"), indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
