#!/usr/bin/env bash
# verify.sh [--static | --activation LOG | --live]: checks of the 4-card fork.
#   --static          no GPU: env filled in, model files present, engine imports from the venv, v41k ops present,
#                     the rendered yaml is TP4/PP1 with the 4-card settings, the src tree is still the series end
#   --activation LOG  server log: every adopted lever logged its activation line on all four ranks, and no
#                     fallback/mismatch line appeared (run after at least one T=0 and one T=1 request)
#   --live (default)  running server on DS41_HOST:DS41_PORT: /health, /v1/models, one T=0 reply, then --activation
#                     on $FORK_HOME/run/$NAME.log
set -uo pipefail
FORK=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=configs/4card.env
source "$FORK/configs/4card.env"
NAME=${NAME:-serve-4card} ENGINE_PY=${ENGINE_PY:-$FORK_HOME/.venv/bin/python}
bad=0
ok() { echo "OK    $*"; }
no() { echo "FAIL  $*"; bad=1; }

activation() {  # activation LOG
  local log=$1 n p
  [[ -s "$log" ]] || { no "no log $log"; return; }
  # pattern|minimum count (per-rank lines appear once on each of the four TP ranks)
  while IFS='|' read -r p n; do
    [[ -z "$p" ]] && continue
    c=$(sed -E 's/\x1b\[[0-9;]*m//g' "$log" | grep -acF -- "$p")
    if (( c >= n )); then ok "activation x$c: $p"; else no "activation x$c (want >= $n): $p"; fi
  done <<'EOF'
V4.1 packed KV: max_len|4
V4.1 index reduce bank (TOK1103)|4
VLLM_V41_PLAN_FUSE=1: expert plan built in q8_plan|4
VLLM_V41_EXPERT_FAST=1: routed experts on v41k gate_up_fast and down_rows_fast|4
VLLM_V41_FUSE_ATTN_PREP=1:|4
VLLM_V41_FUSE_ATTN_POST=1:|4
VLLM_V41_MARKOV_SHARD=1: greedy drafts score vocabulary rows|4
V4.1 coupled local verify (VLLM_V41_COUPLED_LOCAL): vocabulary shard|4
EOF
  # lines that mean a lever fell back, disagreed with its reference path, or is misconfigured for PP=1
  while IFS= read -r p; do
    [[ -z "$p" ]] && continue
    c=$(sed -E 's/\x1b\[[0-9;]*m//g' "$log" | grep -acF -- "$p")
    if (( c == 0 )); then ok "absent: $p"; else no "present x$c: $p"; fi
  done <<'EOF'
VLLM_V41_INDEX_REDUCE=1 needs
VLLM_V41_INDEX_REDUCE=1 but
VLLM_V41_DMV_X=1 but
v41k library is missing
coupled shard self-check: drafts differ
coupled local verify: output differs
VLLM_V41_PP_KEEP_BATCH=1 active
gathered logits only
Traceback (most recent call last)
EOF
  # same-session prefix hit (needs the smoke's session check): informational
  for p in "V4.1 restore_prefix: first session hit" "VLLM_V41_HOT_REFILL=1 active"; do
    c=$(sed -E 's/\x1b\[[0-9;]*m//g' "$log" | grep -acF -- "$p")
    echo "INFO  x$c: $p"
  done
}

static() {
  for v in DS41_GGUF DS41_BASE DS41_ENGRAM DS41_DSPARK DS41_GPUS; do
    [[ "${!v}" == *__SET_ME__* ]] && no "$v not set" || ok "$v set"
  done
  for f in "$DS41_GGUF" "$DS41_ENGRAM" "$VLLM_V41K_LIB"; do [[ -s "$f" ]] && ok "file $f" || no "missing $f"; done
  for d in "$DS41_BASE" "$DS41_DSPARK"; do [[ -d "$d" ]] && ok "dir $d" || no "missing $d"; done
  local end; end=$(grep -v '^#' "$FORK/SERIES.tsv" | tail -1 | cut -f4)
  if [[ -d "$FORK_HOME/src/.git" ]]; then
    [[ "$(git -C "$FORK_HOME/src" write-tree | cut -c1-12)" == "$end" ]] && ok "src tree $end" || no "src tree is not $end"
  else
    echo "INFO  no $FORK_HOME/src checkout (ENGINE_PY=$ENGINE_PY)"
  fi
  if [[ -x "$ENGINE_PY" ]]; then
    (cd / && CUDA_VISIBLE_DEVICES="" "$ENGINE_PY" -I - "$VLLM_V41K_LIB" "$FORK/configs/serve-4card.yaml.in") <<'PYEOF' || bad=1
import sys, vllm, vllm._C, vllm._C_gguf, torch, yaml
assert vllm.__file__.startswith(sys.prefix), "vllm imported from " + vllm.__file__
print("OK    vllm", vllm.__version__)
torch.ops.load_library(sys.argv[1])
need = ["q8_plan", "gate_up7p", "gate_up_fast", "down_rows_fast", "dmv13_x", "index_reduce_live", "peer_gather"]
miss = [n for n in need if not hasattr(torch.ops.v41k, n)]
print(("FAIL  v41k ops missing: " + " ".join(miss)) if miss else "OK    v41k ops " + " ".join(need))
y = yaml.safe_load(open(sys.argv[2]).read().replace("@", "x"))
want = {"tensor-parallel-size": 4, "pipeline-parallel-size": 1, "max-num-seqs": 1, "max-model-len": 524288,
        "no-async-scheduling": True, "enable-prefix-caching": True}
bad = [k for k, v in want.items() if y.get(k) != v]
print(("FAIL  yaml " + " ".join(bad)) if bad else "OK    yaml TP4 PP1 seqs1 524288 sync prefix")
sys.exit(1 if miss or bad else 0)
PYEOF
  else
    no "no engine python at $ENGINE_PY"
  fi
}

live() {
  local base="http://$DS41_HOST:$DS41_PORT"
  curl -sf -m 10 "$base/health" >/dev/null && ok "/health" || no "/health"
  curl -sf -m 10 "$base/v1/models" | grep -q "\"$DS41_SERVED_NAME\"" && ok "/v1/models lists $DS41_SERVED_NAME" || no "/v1/models"
  local r
  r=$(curl -sf -m 300 "$base/v1/chat/completions" -H 'Content-Type: application/json' -d "{\"model\":\"$DS41_SERVED_NAME\",\
\"messages\":[{\"role\":\"user\",\"content\":\"What is 2+2? Answer with one number.\"}],\"temperature\":0,\"max_tokens\":8,\
\"chat_template_kwargs\":{\"thinking\":false}}")
  grep -q '"completion_tokens"' <<< "$r" && ok "T=0 chat reply" || no "T=0 chat reply"
  activation "$FORK_HOME/run/$NAME.log"
}

case ${1:---live} in
  --static) static ;;
  --activation) activation "${2:?usage: verify.sh --activation LOG}" ;;
  --live) live ;;
  *) echo "usage: verify.sh [--static | --activation LOG | --live]" >&2; exit 2 ;;
esac
(( bad == 0 )) && echo "verify: PASS" || echo "verify: FAIL"
exit $bad
