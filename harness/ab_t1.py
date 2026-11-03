#!/usr/bin/env python3
"""ab_t1.py URL PROMPTS.jsonl OUT.jsonl: seeded T>0 run of a synthetic prompt set on the PP2 server (main, 11-03).

One request at a time. Per prompt: chat completion with the file's temperature / top_p / seed / max_tokens (thinking
on, the server default), sha256 of reasoning + content (exactness compare between arms), completion tokens, wall
time, and spec-decode rounds / accepted drafts from /metrics deltas. Prints per-prompt and TOTAL lines; writes OUT.
Compare two runs: ab_t1.py --compare A.jsonl B.jsonl (prints MATCH or the differing ids).
"""
import hashlib, json, sys, time, urllib.request


def compare(a_path, b_path):
    a = {r["id"]: r for r in map(json.loads, open(a_path))}
    b = {r["id"]: r for r in map(json.loads, open(b_path))}
    diff = [k for k in a if k not in b or a[k]["sha"] != b[k]["sha"]]
    print(f"T1 COMPARE {len(a)} vs {len(b)} prompts: " + ("MATCH" if not diff and len(a) == len(b) else f"DIFFER {diff}"))
    for k in diff:  # first differing character, when both runs stored text (11-03 and later)
        ta, tb = a[k].get("text"), (b.get(k) or {}).get("text")
        if ta is None or tb is None:
            continue
        i = next((j for j in range(min(len(ta), len(tb))) if ta[j] != tb[j]), min(len(ta), len(tb)))
        print(f"T1 DIVERGE {k} at char {i} of {len(ta)}/{len(tb)} ({100 * i / max(len(ta), 1):.0f} %): "
              f"{ta[max(0, i - 40):i]!r} | {ta[i:i + 25]!r} vs {tb[i:i + 25]!r}")
    return 0 if not diff and len(a) == len(b) else 1


def metrics(url):
    t = urllib.request.urlopen(url + "/metrics", timeout=30).read().decode()
    v = {}
    for line in t.splitlines():
        for k in ("vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_accepted_tokens_total"):
            if line.startswith(k + "{"):
                v[k] = float(line.split()[-1])
    return v


def main():
    if sys.argv[1] == "--compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    url, prompts, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows = [json.loads(line) for line in open(prompts) if line.strip()]
    tot_t = tot_n = tot_r = tot_a = 0
    with open(out, "w") as f:
        for p in rows:
            body = json.dumps({"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": p["prompt"]}],
                               "temperature": p["temperature"], "top_p": p["top_p"], "seed": p["seed"],
                               "max_tokens": p["max_tokens"]}).encode()
            a = metrics(url)
            t0 = time.time()
            r = json.load(urllib.request.urlopen(urllib.request.Request(
                url + "/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=900))
            dt = time.time() - t0
            b = metrics(url)
            msg = r["choices"][0]["message"]
            text = (msg.get("reasoning_content") or msg.get("reasoning") or "") + "\x00" + (msg.get("content") or "")
            n = r["usage"]["completion_tokens"]
            rounds = b.get("vllm:spec_decode_num_drafts_total", 0) - a.get("vllm:spec_decode_num_drafts_total", 0)
            acc = (b.get("vllm:spec_decode_num_accepted_tokens_total", 0)
                   - a.get("vllm:spec_decode_num_accepted_tokens_total", 0))
            rec = {"id": p["id"], "sha": hashlib.sha256(text.encode()).hexdigest()[:16], "tokens": n,
                   "s": round(dt, 3), "rounds": rounds, "accepted": acc,
                   "finish": r["choices"][0].get("finish_reason"), "text": text}
            f.write(json.dumps(rec) + "\n")
            f.flush()
            tot_t += dt; tot_n += n; tot_r += rounds; tot_a += acc
            print(f"T1 {p['id']} tokens {n} {dt:.2f} s {n / dt:.1f} tok/s rounds {rounds:.0f} "
                  f"acc/round {acc / max(rounds, 1):.2f} ms/round {dt * 1e3 / max(rounds, 1):.1f} sha {rec['sha']}",
                  flush=True)
    print(f"T1 TOTAL {tot_n} tokens {tot_t:.2f} s {tot_n / tot_t:.1f} tok/s acc/round {tot_a / max(tot_r, 1):.2f} "
          f"tok/round {tot_n / max(tot_r, 1):.2f} ms/round {tot_t * 1e3 / max(tot_r, 1):.1f}")


if __name__ == "__main__":
    main()
