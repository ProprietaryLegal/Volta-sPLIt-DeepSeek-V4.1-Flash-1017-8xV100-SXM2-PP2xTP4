#!/usr/bin/env python3
"""Read-only thread census of the DeepSeek server (PIN1). Reads /proc only; never sets affinity.

Walks every descendant process of ROOT_PID (the api_server, or the tmux pane's shell). It samples each thread twice,
INTERVAL seconds apart, and prints one JSON object with, for every thread:
  pid, tid, process name (comm of the thread-group leader), thread comm, last CPU (stat field 39), CPU % over the
  interval (utime + stime delta), read_bytes delta from /proc/<pid>/task/<tid>/io (Engram's native pread threads
  show up here during a cold prefill), and the allowed-CPU list.
Plus a per-CPU sum of the sampled threads' CPU %, so a pin plan can be checked against where the load really runs.
No command lines, environment or memory contents are read or printed.

  python3 tools/proc_census.py ROOT_PID [--interval 5] [--min-cpu 1.0]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

HZ = os.sysconf("SC_CLK_TCK")


def children(pid: int) -> list[int]:
    out = []
    for task in Path(f"/proc/{pid}/task").glob("*"):
        try:
            out += [int(x) for x in (task / "children").read_text().split()]
        except OSError:
            pass
    return out


def tree(root: int) -> list[int]:
    seen, todo = [], [root]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.append(p)
        todo += children(p)
    return sorted(seen)


def stat_fields(path: Path) -> tuple[str, list[str]]:
    raw = path.read_text()
    comm = raw[raw.index("(") + 1: raw.rindex(")")]
    return comm, raw[raw.rindex(")") + 2:].split()     # fields from 3 (state) onward


def sample(pids: list[int]) -> dict[tuple[int, int], dict[str, object]]:
    rows: dict[tuple[int, int], dict[str, object]] = {}
    for pid in pids:
        try:
            pname = Path(f"/proc/{pid}/comm").read_text().strip()
            tids = [int(t.name) for t in Path(f"/proc/{pid}/task").iterdir()]
        except OSError:
            continue
        for tid in tids:
            base = Path(f"/proc/{pid}/task/{tid}")
            try:
                comm, f = stat_fields(base / "stat")
                allowed = next(line.split(":", 1)[1].strip() for line in (base / "status").read_text().splitlines()
                               if line.startswith("Cpus_allowed_list:"))
                try:
                    rb = int(next(line.split()[1] for line in (base / "io").read_text().splitlines()
                                  if line.startswith("read_bytes:")))
                except (OSError, StopIteration):
                    rb = None
            except (OSError, ValueError, StopIteration):
                continue
            rows[(pid, tid)] = {"pid": pid, "tid": tid, "process": pname, "thread": comm,
                                "ticks": int(f[11]) + int(f[12]), "cpu": int(f[36]), "read_bytes": rb,
                                "allowed": allowed}
    return rows


def census(root: int, interval: float, min_cpu: float) -> dict[str, object]:
    pids = tree(root)
    a = sample(pids)
    t0 = time.monotonic()
    time.sleep(interval)
    b = sample(pids)
    dt = time.monotonic() - t0
    threads, per_cpu = [], {}
    for key, r in b.items():
        if key not in a:
            continue
        pct = round(100.0 * (r["ticks"] - a[key]["ticks"]) / HZ / dt, 1)        # type: ignore[operator]
        rb = None if r["read_bytes"] is None or a[key]["read_bytes"] is None else \
            r["read_bytes"] - a[key]["read_bytes"]                              # type: ignore[operator]
        per_cpu[r["cpu"]] = round(per_cpu.get(r["cpu"], 0.0) + pct, 1)
        if pct >= min_cpu or (rb or 0) > 0:
            threads.append({k: r[k] for k in ("pid", "tid", "process", "thread", "cpu", "allowed")} |
                           {"cpu_pct": pct, "read_bytes_delta": rb})
    threads.sort(key=lambda x: -x["cpu_pct"])                                   # type: ignore[operator]
    return {"root": root, "processes": len(pids), "threads_total": len(b), "interval_s": round(dt, 2),
            "loadavg": Path("/proc/loadavg").read_text().split()[:3],
            "per_cpu_pct": dict(sorted(per_cpu.items())), "threads": threads}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root_pid", type=int)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--min-cpu", type=float, default=1.0)
    args = ap.parse_args()
    print(json.dumps(census(args.root_pid, args.interval, args.min_cpu), indent=1))


if __name__ == "__main__":
    main()
