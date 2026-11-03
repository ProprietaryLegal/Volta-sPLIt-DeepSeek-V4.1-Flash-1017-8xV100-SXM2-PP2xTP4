#!/usr/bin/env python3
"""ab_depth.py URL LABEL OUT.jsonl [LENS] [REPS] [GEN]: decode rate at long context on the PP2 server (main, 11-03).

For the owner 11-03 "Try async at 32 64k tokens". Public text only (the vLLM docs Markdown under src-pp2/docs), a fresh
nonce per request (prefix-cache miss), lengths calibrated with /tokenize. Streams /v1/completions (raw prompt),
T=0, ignore_eos, GEN tokens (default 512). Decode rate = (completion tokens - 1) / (last token - first token);
spec rounds and accepted drafts from /metrics deltas. Prints one line per request; writes JSON lines to OUT.
"""
import glob, hashlib, json, os, sys, time, urllib.request, uuid

MODEL = "deepseek-v4.1-flash"
TEXT_DIR = "${ENGINE_HOME}/src-pp2/docs"


def post(url, body):
    return urllib.request.urlopen(urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=1800)


def corpus(need_chars):
    parts, n = [], 0
    for path in sorted(glob.glob(os.path.join(TEXT_DIR, "**", "*.md"), recursive=True)):
        try:
            t = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        parts.append(t)
        n += len(t)
        if n >= need_chars:
            break
    text = "\n\n".join(parts)
    while len(text) < need_chars:
        text = text + "\n\n" + text
    return text


def count(base, text):
    with post(base + "/tokenize", {"model": MODEL, "prompt": text}) as r:
        return int(json.load(r)["count"])


def calibrate(base, text, target):
    chars = target * 4
    n = 0
    for _ in range(6):
        n = count(base, text[:chars])
        if abs(n - target) <= max(8, target // 200):
            break
        chars = max(64, int(chars * target / max(n, 1)))
    return text[:chars], n


def metrics(base):
    t = urllib.request.urlopen(base + "/metrics", timeout=30).read().decode()
    v = {}
    for line in t.splitlines():
        for k in ("vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_accepted_tokens_total"):
            if line.startswith(k + "{"):
                v[k] = float(line.split()[-1])
    return v


def run(base, prompt, gen):
    body = {"model": MODEL, "prompt": prompt, "max_tokens": gen, "temperature": 0, "stream": True,
            "stream_options": {"include_usage": True}, "ignore_eos": True}
    t0 = time.perf_counter()
    first = last = None
    text, usage = [], None
    with post(base + "/v1/completions", body) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            obj = json.loads(data)
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                if ch.get("text"):
                    now = time.perf_counter()
                    first = first or now
                    last = now
                    text.append(ch["text"])
    return t0, first, last, "".join(text), usage or {}


def nonce(length, rep):
    """Same prompt for the same (length, rep) in every arm (servers restart per arm, so no prefix-cache hit);
    DEPTH_NONCE=random restores the old per-request uuid."""
    if os.environ.get("DEPTH_NONCE") == "random":
        return uuid.uuid4().hex
    return hashlib.sha256(f"depth-{length}-{rep}".encode()).hexdigest()[:32]


def main():
    base, label, out = sys.argv[1], sys.argv[2], sys.argv[3]
    lens = [int(x) for x in (sys.argv[4] if len(sys.argv) > 4 else "32768,65536").split(",")]
    reps = int(sys.argv[5]) if len(sys.argv) > 5 else 2
    gen = int(sys.argv[6]) if len(sys.argv) > 6 else 512
    text = corpus(max(lens) * 6)
    with open(out, "a") as f:
        for L in lens:
            body, _ = calibrate(base, text, L - 16)
            for rep in range(reps):
                a = metrics(base)
                t0, first, last, out_text, usage = run(base, f"[run {nonce(L, rep)}]\n" + body, gen)
                b = metrics(base)
                n = usage.get("completion_tokens", 0)
                rounds = b.get("vllm:spec_decode_num_drafts_total", 0) - a.get("vllm:spec_decode_num_drafts_total", 0)
                acc = (b.get("vllm:spec_decode_num_accepted_tokens_total", 0)
                       - a.get("vllm:spec_decode_num_accepted_tokens_total", 0))
                dec = (last - first) if first and last else 0.0
                rec = {"label": label, "target": L, "rep": rep, "prompt_tokens": usage.get("prompt_tokens"),
                       "tokens": n, "ttft_s": round(first - t0, 3) if first else None, "decode_s": round(dec, 3),
                       "decode_tok_s": round((n - 1) / dec, 2) if dec else None, "rounds": rounds, "accepted": acc,
                       "ms_round": round(dec * 1e3 / max(rounds, 1), 2),
                       "sha": hashlib.sha256(out_text.encode()).hexdigest()[:12]}
                f.write(json.dumps(rec) + "\n")
                f.flush()
                print(f"DEPTH {label} L={L} rep {rep}: prompt {rec['prompt_tokens']} TTFT {rec['ttft_s']} s "
                      f"decode {rec['decode_tok_s']} tok/s rounds {rounds:.0f} tok/round {n / max(rounds, 1):.2f} "
                      f"ms/round {rec['ms_round']} sha {rec['sha']}", flush=True)


if __name__ == "__main__":
    main()
