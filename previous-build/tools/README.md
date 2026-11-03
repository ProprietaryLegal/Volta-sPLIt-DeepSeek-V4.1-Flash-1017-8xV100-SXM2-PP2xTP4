# Tools

Small, standard-library tools we used on the V100 deployment. None of them needs a GPU to test.

| file | what it does | used by |
|---|---|---|
| [`compare_speed.py`](compare_speed.py) | compares two arms' speed files: per cell (cold, warm) and metric (TTFT, prefill tok/s, decode tok/s), the change in % with an unpaired 95 % bootstrap CI (20,000 resamples, fixed seed), and the promotion flag for a cold-target change (cold TTFT at least 2 % better with the CI excluding 0, decode not more than 3 % worse); for a warm-target change such as MP1, apply the same rule to the warm row it prints ([method.md](../docs/method.md#promotion-rule)) | every arm |
| [`warmup.py`](warmup.py), [`warmup.sh`](warmup.sh) | bounded startup warm-up: waves of 1, 2, 3 concurrent raw completions, 32 tokens each, a fresh `cache_salt` per request, refuses to start a wave unless the server is idle, a deadline plus a hard process bound; prints aggregates only | [OPS1](../docs/experiments.md#ops1-bounded-startup-warm-up) |
| [`proc_census.py`](proc_census.py) | read-only thread census of a server's process tree from `/proc`: per-thread CPU %, last CPU, read bytes, allowed CPUs; never reads command lines, environment or memory | [PIN1](../docs/experiments.md#pin1-engram-io-thread-placement) |
| [`pin_io.py`](pin_io.py) | pins or unpins the threads a census marked as reading from disk; dry run by default | PIN1 (not run) |
| [`check_data_boundary.sh`](check_data_boundary.sh) | refuses weights, archives, `*.jsonl`, private directories, files over 1 MiB and credential patterns in a git tree or the index | before every publication |

`compare_speed.py` expects speed files of the form
`{"label": "...", "rows": [{"cell": "cold"|"warm", "ttft_s": ..., "prefill_tok_s": ..., "decode_tok_s": ...}, ...]}`.
Our request runner that writes them is not published (it embeds our prompt corpus), but any runner that writes that
shape works.

```bash
python3 tools/compare_speed.py control.json candidate.json --json compare.json
python3 tools/warmup.py --port 8000 --model deepseek-v4.1-flash
python3 tools/proc_census.py <api server pid> --interval 5
python3 -I -m unittest discover -s tools -p 'test_*.py' -v
python3 -I -m pytest -p no:cacheprovider tools/test_proc_census.py   # 3 pytest-style tests (proc_census, pin_io)
bash tools/check_data_boundary.sh --tree HEAD
```
