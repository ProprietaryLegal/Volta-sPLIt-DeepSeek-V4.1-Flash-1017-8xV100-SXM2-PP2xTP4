"""CPU-only test of tools/proc_census.py on this test's own process tree (a busy child and a reading thread)."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("proc_census", HERE / "proc_census.py")
assert SPEC and SPEC.loader
pc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pc)


def test_census_sees_busy_child_and_reader() -> None:
    busy = subprocess.Popen([sys.executable, "-c", "import time\nt=time.time()\nwhile time.time()-t<6: pass"])
    stop = threading.Event()
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(os.urandom(8 << 20))
        name = f.name

    def reader() -> None:   # O_DIRECT is not portable; drop-free reads may hit the page cache (read_bytes may be 0)
        while not stop.is_set():
            with open(name, "rb") as g:
                while g.read(1 << 20):
                    pass

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    try:
        time.sleep(0.3)
        out = pc.census(os.getpid(), 1.0, 1.0)
    finally:
        stop.set()
        busy.kill()
        busy.wait()
        os.unlink(name)
    assert out["processes"] >= 2
    pids = {t["pid"] for t in out["threads"]}
    assert busy.pid in pids, out["threads"]
    hot = next(t for t in out["threads"] if t["pid"] == busy.pid)
    assert hot["cpu_pct"] > 50
    assert set(hot) == {"pid", "tid", "process", "thread", "cpu", "allowed", "cpu_pct", "read_bytes_delta"}
    assert sum(out["per_cpu_pct"].values()) > 50


def test_tree_of_missing_pid_is_just_root() -> None:
    assert pc.tree(2 ** 22 + 7) == [2 ** 22 + 7]


def test_pin_io_plan_and_apply_on_own_thread(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("pin_io", HERE / "pin_io.py")
    assert spec and spec.loader
    pin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pin)
    assert pin.cpu_set("0-2,12-14") == {0, 1, 2, 12, 13, 14}
    assert pin.cpu_set("5") == {5}
    ready, stop, tid = threading.Event(), threading.Event(), []

    def idle() -> None:
        tid.append(threading.get_native_id())
        ready.set()
        stop.wait(10)

    th = threading.Thread(target=idle)
    th.start()
    ready.wait(5)
    orig = ",".join(map(str, sorted(os.sched_getaffinity(tid[0]))))
    comm = Path(f"/proc/{os.getpid()}/task/{tid[0]}/comm").read_text().strip()
    census = {"threads": [{"pid": os.getpid(), "tid": tid[0], "process": "py", "thread": comm, "allowed": orig,
                           "read_bytes_delta": 4096},
                          {"pid": os.getpid(), "tid": threading.get_native_id(), "process": "py", "allowed": "0-1",
                           "read_bytes_delta": 0}]}
    f = tmp_path / "c.json"
    f.write_text(json.dumps(census))
    one = sorted(os.sched_getaffinity(0))[:1]
    try:
        r = subprocess.run([sys.executable, str(HERE / "pin_io.py"), str(f), "--cpus", str(one[0])],
                           capture_output=True, text=True)
        assert r.returncode == 0 and '"applied": false' in r.stdout
        assert len(os.sched_getaffinity(tid[0])) > 1 or os.cpu_count() == 1   # dry run changed nothing
        r = subprocess.run([sys.executable, str(HERE / "pin_io.py"), str(f), "--cpus", str(one[0]), "--apply"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert os.sched_getaffinity(tid[0]) == set(one)
        assert len(os.sched_getaffinity(0)) > 1 or os.cpu_count() == 1           # the reading thread only
        r = subprocess.run([sys.executable, str(HERE / "pin_io.py"), str(f), "--unpin", "--apply"],
                           capture_output=True, text=True)
        assert r.returncode == 0 and os.sched_getaffinity(tid[0]) == pin.cpu_set(orig)
        stale = dict(census, threads=[dict(census["threads"][0], thread="not-this-thread")])
        f.write_text(json.dumps(stale))
        r = subprocess.run([sys.executable, str(HERE / "pin_io.py"), str(f), "--cpus", str(one[0]), "--apply"],
                           capture_output=True, text=True)
        assert '"applied": false' in r.stdout and os.sched_getaffinity(tid[0]) == pin.cpu_set(orig)
    finally:
        stop.set()
        th.join()
