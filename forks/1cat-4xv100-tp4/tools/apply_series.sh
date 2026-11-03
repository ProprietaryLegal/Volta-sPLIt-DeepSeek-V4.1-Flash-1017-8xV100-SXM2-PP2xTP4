#!/usr/bin/env bash
# apply_series.sh SRC: apply the 4-card patch series to a 1Cat-vLLM checkout at 899e9ed33, in SERIES.tsv order.
# Each patch goes in with `git apply --index`; afterwards `git write-tree` must equal the patch's tree_after
# (12 hex), so the finished tree is byte-for-byte the V41PKG commit the series was cut from. Idempotent: a checkout
# whose index tree already equals a patch's tree_after resumes after that patch. Exit 1 on the first mismatch.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
src=${1:?usage: apply_series.sh SRC}
base=899e9ed33
git -C "$src" rev-parse --verify -q "$base^{commit}" >/dev/null || { echo "apply_series: $src has no commit $base" >&2; exit 1; }
[[ "$(git -C "$src" rev-parse HEAD)" == "$(git -C "$src" rev-parse "$base^{commit}")" ]] \
  || { echo "apply_series: $src HEAD is not $base" >&2; exit 1; }
git -C "$src" diff --quiet || { echo "apply_series: $src has unstaged changes" >&2; exit 1; }
current=$(git -C "$src" write-tree); current=${current:0:12}
mapfile -t rows < <(grep -v '^#' "$here/SERIES.tsv")
start=0
for i in "${!rows[@]}"; do  # resume: the last patch whose tree is the current index tree
  IFS=$'\t' read -r _ _ _ tree _ <<< "${rows[$i]}"
  [[ "$tree" == "$current" ]] && start=$((i + 1))
done
(( start == 0 )) && [[ "$current" != "$(git -C "$src" rev-parse "$base^{tree}" | cut -c1-12)" ]] \
  && { echo "apply_series: index tree $current is neither $base nor any patch's tree_after" >&2; exit 1; }
for ((i = start; i < ${#rows[@]}; i++)); do
  IFS=$'\t' read -r name _ to tree _ <<< "${rows[$i]}"
  git -C "$src" -c apply.whitespace=nowarn apply --index "$here/patches/$name" \
    || { echo "FAILED   $name (git apply)" >&2; exit 1; }
  got=$(git -C "$src" write-tree); got=${got:0:12}
  [[ "$got" == "$tree" ]] || { echo "TREE     $name left tree $got, want $tree (V41PKG $to)" >&2; exit 1; }
  echo "applied  $name  tree $got"
done
echo "apply_series: ${#rows[@]} patches; tree $(git -C "$src" write-tree | cut -c1-12) = V41PKG $(cut -f3 <<< "${rows[-1]}")"
