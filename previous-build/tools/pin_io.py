#!/usr/bin/env python3
"""PIN1: pin or unpin the Engram IO threads of a DeepSeek server you started. Dry run by default.

The IO threads are the server-tree threads that read from disk during a cold prefill: `read_bytes_delta > 0` in a
census taken by tools/proc_census.py while a cold cell runs. Only those thread IDs change affinity, through
`os.sched_setaffinity(tid, cpus)`, which acts on one thread on Linux. Nothing else in the process changes, and nothing
outside the census's tree.

  python3 tools/pin_io.py CENSUS.json --cpus 9-11,21-23            # print the plan
  python3 tools/pin_io.py CENSUS.json --cpus 9-11,21-23 --apply    # pin
  python3 tools/pin_io.py CENSUS.json --unpin --apply              # back to each thread's census affinity
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def cpu_set(text: str) -> set[int]:
    out: set[int] = set()
    for part in text.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out


def io_threads(census: dict) -> list[dict]:
    return [t for t in census["threads"] if (t.get("read_bytes_delta") or 0) > 0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("census", type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cpus")
    g.add_argument("--unpin", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    census = json.loads(args.census.read_text())
    rows = io_threads(census)
    if not rows:
        print("no IO threads in the census (was a cold cell running?)")
        return 2
    for t in rows:
        target = cpu_set(t["allowed"]) if args.unpin else cpu_set(args.cpus)
        base = Path(f"/proc/{t['pid']}/task/{t['tid']}")
        try:   # same thread as in the census (a TID can be reused after a restart)
            alive = (base / "comm").read_text().strip() == t.get("thread", (base / "comm").read_text().strip())
        except OSError:
            alive = False
        print(json.dumps({"pid": t["pid"], "tid": t["tid"], "process": t["process"], "from": t["allowed"],
                          "to": ",".join(map(str, sorted(target))), "alive": alive, "applied": args.apply and alive}))
        if args.apply and alive:
            os.sched_setaffinity(t["tid"], target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
