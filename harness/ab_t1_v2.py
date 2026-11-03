#!/usr/bin/env python3
"""ab_t1_v2.py: streamed A/B client for the PP2 server with decode-only timing (harness1103, 11-03; advrev H2/M1).

  ab_t1_v2.py URL PROMPTS.jsonl OUT.jsonl     seeded T>0 run of a prompt set (drop-in for ab_t1.py; thinking on)
  ab_t1_v2.py --tput URL [N] [OUT.jsonl]      T=0 throughput run (drop-in for ab_tput.py; thinking off, ignore_eos, 1024)
  ab_t1_v2.py --compare A.jsonl B.jsonl       token-exact compare of two T1 runs (no text printed)

Why v2: ab_t1.py / ab_tput.py divide the whole request wall time by the spec rounds, so "ms/round" carries TTFT and
teardown (about 0.40 s per request, 1.2-1.4 ms per round at these lengths; advrev M1). v2 streams the reply with
return_token_ids and timestamps every chunk that carries generated token ids:
  ttft_s        first token chunk - request start (prefill + first sample; reported separately)
  dec_s         last token chunk - first token chunk
  ms_round_dec  dec_s * 1e3 / rounds
The first token comes from the prefill step and is not a spec round: in every bench5 record so far
tokens = 1 + rounds + accepted (MEASURED over t1-*.jsonl and depth-*.jsonl), so the span first -> last token covers
exactly `rounds` verify rounds. ab_depth.py uses the same definition, so the two are directly comparable (H2 gate:
ms_round_dec within 0.1 ms of ab_depth.py at the same length on one fresh arm).
The legacy figure (wall s / rounds) is still printed in the same place, so pairs_arms.py (v1) parses v2 lines too; but a
streamed request is not the same request as a non-streamed one, so never pair a v2 arm with a v1 arm.

Per request it also stores the generated token ids (exact compare, tok_sha = sha256 of the id list) and the text sha
(same formula as ab_t1.py: reasoning + NUL + content). Printed lines carry numbers and shas only, never text.
Line format (v1 prefix unchanged, v2 fields appended; pairs_arms_v2.py reads both):
  T1 t1-01 tokens 580 4.12 s 140.9 tok/s rounds 144 acc/round 3.02 ms/round 28.6 sha <16> ttft 0.412 dec_s 3.702 dec-ms/round 25.71 toksha <16> ids ok
  TPUT p0 tokens 1024 12.84 s 79.7 tok/s rounds 479 tok/round 2.14 acc/round 1.14 ms/round 26.8 ttft 0.401 dec_s 12.436 dec-ms/round 25.96 toksha <16> ids ok
"""
import hashlib, json, sys, time, urllib.request

MODEL = "deepseek-v4.1-flash"
TPUT_PROMPTS = ["Write a detailed 900-word essay on the history of the printing press.",
                "Explain, step by step and with examples, how a hash table works and how collisions are resolved.",
                "Write a Python module that parses CSV files, validates each row against a schema, and reports errors. "
                "Include docstrings and tests."]   # = ab_tput.py PROMPTS (public, synthetic)


def metrics(url):
    t = urllib.request.urlopen(url + "/metrics", timeout=30).read().decode()
    v = {}
    for line in t.splitlines():
        for k in ("vllm:spec_decode_num_drafts_total", "vllm:spec_decode_num_accepted_tokens_total"):
            if line.startswith(k + "{") or line.startswith(k + " "):
                v[k] = v.get(k, 0.0) + float(line.split()[-1])
    return v


def stream_chat(url, body, timeout=900):
    """POST a streamed chat completion; return timing, token ids, text parts, usage, finish reason."""
    body = dict(body, model=MODEL, stream=True, stream_options={"include_usage": True}, return_token_ids=True)
    req = urllib.request.Request(url + "/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.perf_counter()
    first = last = None
    ids, reasoning, content, usage, finish, chunks, text_first = [], [], [], None, None, 0, None
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            obj = json.loads(data)
            if obj.get("error"):
                raise RuntimeError(f"stream error: {str(obj['error'])[:200]}")
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                now = time.perf_counter()
                d = ch.get("delta") or {}
                rs = d.get("reasoning_content") or d.get("reasoning") or ""
                ct = d.get("content") or ""
                tid = ch.get("token_ids") or []
                if rs:
                    reasoning.append(rs)
                if ct:
                    content.append(ct)
                if (rs or ct) and text_first is None:
                    text_first = now
                if tid:
                    ids.extend(int(x) for x in tid)
                    chunks += 1
                    first = first or now
                    last = now
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    t_end = time.perf_counter()
    return {"t0": t0, "first": first, "last": last, "end": t_end, "ids": ids, "reasoning": "".join(reasoning),
            "content": "".join(content), "usage": usage or {}, "finish": finish, "chunks": chunks,
            "text_first": text_first}


def measure(url, body):
    a = metrics(url)
    s = stream_chat(url, body)
    b = metrics(url)
    n = int(s["usage"].get("completion_tokens") or 0)
    rounds = b.get("vllm:spec_decode_num_drafts_total", 0) - a.get("vllm:spec_decode_num_drafts_total", 0)
    acc = (b.get("vllm:spec_decode_num_accepted_tokens_total", 0)
           - a.get("vllm:spec_decode_num_accepted_tokens_total", 0))
    wall = s["end"] - s["t0"]
    # no token ids streamed (server ignored return_token_ids): fall back to text chunks, and say so
    first, last, basis = s["first"], s["last"], "ids"
    if first is None:
        first, last, basis = s["text_first"], s["end"], "text"
    dec = (last - first) if first is not None and last is not None else None
    text = s["reasoning"] + "\x00" + s["content"]
    ids_ok = basis == "ids" and len(s["ids"]) == n
    return {"tokens": n, "s": round(wall, 3), "ttft_s": round(first - s["t0"], 3) if first is not None else None,
            "dec_s": round(dec, 3) if dec is not None else None, "rounds": rounds, "accepted": acc,
            "ms_round": round(wall * 1e3 / max(rounds, 1), 2),
            "ms_round_dec": round(dec * 1e3 / rounds, 2) if dec is not None and rounds > 0 else None,
            "token_ids": s["ids"], "tok_sha": hashlib.sha256(json.dumps(s["ids"]).encode()).hexdigest()[:16],
            "sha": hashlib.sha256(text.encode()).hexdigest()[:16], "finish": s["finish"], "chunks": s["chunks"],
            "timing_basis": basis, "ids_complete": ids_ok, "text": text, "wall_exact": wall,
            "dec_exact": dec}


def v2_tail(rec):
    dm = f"{rec['ms_round_dec']:.2f}" if rec["ms_round_dec"] is not None else "nan"
    return (f" ttft {rec['ttft_s'] if rec['ttft_s'] is not None else 'nan'} dec_s "
            f"{rec['dec_s'] if rec['dec_s'] is not None else 'nan'} dec-ms/round {dm} toksha {rec['tok_sha']} "
            f"ids {'ok' if rec['ids_complete'] else 'INCOMPLETE-' + rec['timing_basis']}")


def totals(recs):
    t = sum(r["wall_exact"] for r in recs)
    n = sum(r["tokens"] for r in recs)
    rr = sum(r["rounds"] for r in recs)
    ok = [r for r in recs if r["dec_exact"] is not None and r["rounds"] > 0]
    d = sum(r["dec_exact"] for r in ok)
    dr = sum(r["rounds"] for r in ok)
    tt = [r["ttft_s"] for r in recs if r["ttft_s"] is not None]
    return t, n, rr, d, dr, tt


def run_t1(url, prompts, out):
    rows = [json.loads(line) for line in open(prompts) if line.strip()]
    recs = []
    with open(out, "w") as f:
        for p in rows:
            rec = measure(url, {"messages": [{"role": "user", "content": p["prompt"]}], "temperature": p["temperature"],
                                "top_p": p["top_p"], "seed": p["seed"], "max_tokens": p["max_tokens"]})
            rec = {"id": p["id"], "v": 2, **rec}
            recs.append(rec)
            f.write(json.dumps({k: v for k, v in rec.items() if k not in ("wall_exact", "dec_exact")}) + "\n")
            f.flush()
            n, dt, rounds, acc = rec["tokens"], rec["wall_exact"], rec["rounds"], rec["accepted"]
            print(f"T1 {p['id']} tokens {n} {dt:.2f} s {n / dt:.1f} tok/s rounds {rounds:.0f} "
                  f"acc/round {acc / max(rounds, 1):.2f} ms/round {dt * 1e3 / max(rounds, 1):.1f} sha {rec['sha']}"
                  + v2_tail(rec), flush=True)
    t, n, rr, d, dr, tt = totals(recs)
    acc = sum(r["accepted"] for r in recs)
    print(f"T1 TOTAL {n} tokens {t:.2f} s {n / t:.1f} tok/s acc/round {acc / max(rr, 1):.2f} "
          f"tok/round {n / max(rr, 1):.2f} ms/round {t * 1e3 / max(rr, 1):.1f} "
          f"dec-ms/round {d * 1e3 / max(dr, 1):.2f} ttft-mean {sum(tt) / max(len(tt), 1):.3f} "
          f"ids-complete {sum(r['ids_complete'] for r in recs)}/{len(recs)}")


def run_tput(url, n_req, out=None):
    recs = []
    f = open(out, "w") if out else None
    for i in range(n_req):
        p = TPUT_PROMPTS[i % len(TPUT_PROMPTS)]
        rec = measure(url, {"messages": [{"role": "user", "content": p}], "temperature": 0, "max_tokens": 1024,
                            "ignore_eos": True, "chat_template_kwargs": {"thinking": False}})
        rec = {"id": f"p{i % len(TPUT_PROMPTS)}", "v": 2, **rec}
        recs.append(rec)
        if f:
            f.write(json.dumps({k: v for k, v in rec.items() if k not in ("wall_exact", "dec_exact", "text")}) + "\n")
            f.flush()
        n, dt, rounds, acc = rec["tokens"], rec["wall_exact"], rec["rounds"], rec["accepted"]
        print(f"TPUT {rec['id']} tokens {n} {dt:.2f} s {n / dt:.1f} tok/s rounds {rounds:.0f} "
              f"tok/round {n / max(rounds, 1):.2f} acc/round {acc / max(rounds, 1):.2f} "
              f"ms/round {dt * 1e3 / max(rounds, 1):.1f}" + v2_tail(rec), flush=True)
    if f:
        f.close()
    t, n, rr, d, dr, tt = totals(recs)
    print(f"TPUT TOTAL {n} tokens {t:.2f} s {n / t:.1f} tok/s tok/round {n / max(rr, 1):.2f} "
          f"ms/round {t * 1e3 / max(rr, 1):.1f} dec-ms/round {d * 1e3 / max(dr, 1):.2f} "
          f"ttft-mean {sum(tt) / max(len(tt), 1):.3f} ids-complete {sum(r['ids_complete'] for r in recs)}/{len(recs)}")


def compare(a_path, b_path):
    """Token-exact when both runs stored token ids (v2), else text sha (v1). Prints ids and indices only."""
    a = {r["id"]: r for r in map(json.loads, open(a_path))}
    b = {r["id"]: r for r in map(json.loads, open(b_path))}
    diff = []
    for k in a:
        if k not in b:
            diff.append(k)
            continue
        ia, ib = a[k].get("token_ids"), b[k].get("token_ids")
        same = (ia == ib) if ia is not None and ib is not None else a[k]["sha"] == b[k]["sha"]
        if not same:
            diff.append(k)
    basis = "token ids" if all("token_ids" in r for r in list(a.values()) + list(b.values())) else "text sha"
    print(f"T1 COMPARE ({basis}) {len(a)} vs {len(b)} prompts: "
          + ("MATCH" if not diff and len(a) == len(b) else f"DIFFER {diff}"))
    for k in diff:
        ia, ib = a[k].get("token_ids"), (b.get(k) or {}).get("token_ids")
        if ia is None or ib is None:
            continue
        j = next((i for i in range(min(len(ia), len(ib))) if ia[i] != ib[i]), min(len(ia), len(ib)))
        print(f"T1 DIVERGE {k} at token {j} of {len(ia)}/{len(ib)} ({100 * j / max(len(ia), 1):.0f} %)")
    return 0 if not diff and len(a) == len(b) else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    if len(sys.argv) > 1 and sys.argv[1] == "--tput":
        run_tput(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3, sys.argv[4] if len(sys.argv) > 4 else None)
        return
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    run_t1(sys.argv[1], sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    main()
