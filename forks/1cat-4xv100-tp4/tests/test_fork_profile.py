"""CPU checks of the 4-card fork's profile: the env/yaml carry the PP=1 classification, the series is contiguous and
clean, the README lists every lever, and every script parses. No GPU, no network, no engine import."""
import os
import re
import subprocess

FORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# knob -> value the 4-card env must export (adopted levers on; PP_KEEP_BATCH off because it is a no-op at PP=1)
ADOPTED = {
    "VLLM_V41_INDEX_REDUCE": "1", "VLLM_V41_DMV_X": "1", "VLLM_V41_COUPLED_DRAFTS": "1",
    "VLLM_V41_COUPLED_DRAFT_TEMP": "1.0", "VLLM_V41_MARKOV_SHARD": "1", "VLLM_V41_COUPLED_SHARD": "1",
    "VLLM_V41_COUPLED_LOCAL": "1", "VLLM_V41_PLAN_FUSE": "1", "VLLM_V41_EXPERT_FAST": "1",
    "VLLM_V41_FUSE_ATTN_PREP": "1", "VLLM_V41_FUSE_ATTN_POST": "1", "VLLM_V41_DOWN_ROWS": "1",
    "VLLM_V41_SESSION_PREFIX": "1", "VLLM_V41_PACKED_KV": "1", "VLLM_V41_INDEX_TILE_MB": "32",
    "VLLM_V41_HOT_REFILL": "1", "VLLM_V41_RING_REACH": "124",
}
PP1_OFF = {"VLLM_V41_PP_KEEP_BATCH": "0"}
PENDING = ["VLLM_V41_ASYNC", "VLLM_V41_MIX_STREAM", "VLLM_V41_EXPERT_DIET", "VLLM_V41_PREFILL_SKIP_ROWS",
           "VLLM_USE_V2_MODEL_RUNNER", "VLLM_V41_MULTI_SEQ", "VLLM_V41_KV_HOT_POSITIONS"]
LOST = ["VLLM_V41_PRUNE_TOPP", "VLLM_V41_FUSE_TRANSITION", "VLLM_V41_GATE_COLS", "VLLM_V41_ROUTE_FAST"]


def read(rel):
    with open(os.path.join(FORK, rel), encoding="utf-8") as f:
        return f.read()


def sourced_env():
    """The environment a clean shell has after sourcing configs/4card.env (with a stray pending knob preset)."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": "/nonexistent", "VLLM_V41_ASYNC": "1"}
    out = subprocess.run(["bash", "-c", 'source "$1" && env -0', "_", os.path.join(FORK, "configs/4card.env")],
                         env=env, capture_output=True, check=True).stdout.decode()
    return dict(kv.split("=", 1) for kv in out.split("\0") if "=" in kv)


def test_env_exports_adopted_levers_and_pp1_classification():
    env = sourced_env()
    for k, v in {**ADOPTED, **PP1_OFF}.items():
        assert env.get(k) == v, (k, env.get(k), v)
    assert env.get("CUDA_DEVICE_ORDER") == "PCI_BUS_ID"
    assert env["VLLM_V41K_LIB"].endswith("/src/benchmarks/deepseek_v41/v41k/build/v41k.so")


def test_env_leaves_pending_and_lost_levers_off():
    env = sourced_env()
    for k in PENDING + LOST:
        assert k not in env, k  # VLLM_V41_ASYNC preset above must be unset by the env file
    text = read("configs/4card.env")
    for k in PENDING:
        assert re.search(rf"^# .*{k}", text, re.M), f"no commented hook for {k}"
        assert not re.search(rf"^\s*export\s+{k}=", text, re.M), k


def test_env_model_paths_are_placeholders():
    text = read("configs/4card.env")
    for k in ("DS41_GGUF", "DS41_BASE", "DS41_ENGRAM", "DS41_DSPARK", "DS41_GPUS"):
        assert re.search(rf"^{k}=\$\{{{k}:-__SET_ME__", text, re.M), k


def test_yaml_template_is_tp4_pp1_sync_without_key():
    text = read("configs/serve-4card.yaml.in")
    for line in ("tensor-parallel-size: 4", "pipeline-parallel-size: 1", "max-model-len: 524288", "max-num-seqs: 1",
                 "no-async-scheduling: true", "enable-prefix-caching: true", "no-disable-custom-all-reduce: true",
                 "num_speculative_tokens: 5", "expert_cache_host_storage: shared_original",
                 "expert_cache_offload_fraction: @DS41_OFFLOAD@", "kv-cache-memory-bytes: 268435456"):
        assert re.search(rf"^\s*{re.escape(line)}$", text, re.M), line
    assert "api-key" not in text and "api_key" not in text
    fields = set(re.findall(r"@([A-Z0-9_]+)@", text))
    assert fields == {"DS41_GGUF", "DS41_BASE", "DS41_ENGRAM", "DS41_DSPARK", "DS41_SERVED_NAME", "DS41_HOST",
                      "DS41_PORT", "DS41_OFFLOAD"}
    start = read("start.sh")
    for f in fields:
        assert f"@{f}@" in start, f"start.sh does not fill @{f}@"


def test_series_is_contiguous_from_1277_and_clean():
    rows = [r.split("\t") for r in read("SERIES.tsv").splitlines() if r and not r.startswith("#")]
    assert rows[0][1] == "899e9ed33"
    for a, b in zip(rows, rows[1:]):
        assert a[2] == b[1], (a[0], b[0])
    hexrun = re.compile(r"[0-9a-f]{40,}")
    for name, *_rest in rows:
        path = os.path.join(FORK, "patches", name)
        assert os.path.getsize(path) < 1 << 20, name
        with open(path, encoding="utf-8", errors="replace") as f:
            assert not hexrun.search(f.read()), name
    assert len({r[3] for r in rows}) == len(rows)
    assert all(re.fullmatch(r"[0-9a-f]{12}", r[3]) for r in rows)
    assert sorted(os.listdir(os.path.join(FORK, "patches"))) == sorted(r[0] for r in rows)


def test_readme_lists_every_lever_and_marks_gpu_unverified():
    text = read("README.md")
    for k in list(ADOPTED) + list(PP1_OFF) + PENDING:
        assert k in text, k
    assert "GPU-unverified" in text
    assert "smoke-4card.sh" in text


def test_scripts_parse():
    for rel in ("install.sh", "start.sh", "stop.sh", "verify.sh", "smoke-4card.sh", "tools/apply_series.sh",
                "tools/gen_series.sh", "v41k/build_v41k.sh"):
        subprocess.run(["bash", "-n", os.path.join(FORK, rel)], check=True)
    compile(read("smoke_client.py"), "smoke_client.py", "exec")  # no __pycache__ in the tree


def test_smoke_refuses_the_production_port():
    text = read("smoke-4card.sh")
    assert "PROD_PORT=18042" in text
    assert re.search(r'listening "\$PROD_PORT" && refuse', text)
    assert "--query-compute-apps=pid" in text
    assert re.search(r"^DS41_PORT=\$\{DS41_PORT:-18044\}$", read("configs/4card.env"), re.M)
