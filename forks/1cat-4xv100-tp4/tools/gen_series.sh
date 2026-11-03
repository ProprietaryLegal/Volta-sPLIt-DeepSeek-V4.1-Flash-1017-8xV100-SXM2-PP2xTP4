#!/usr/bin/env bash
# gen_series.sh V41PKG_REPO SERIES_IN OUT_DIR: maintainers only. Cut the 4-card patch series from the V41PKG 1Cat fork.
# SERIES_IN has one tab-separated row per patch: name, from, to, group, knob, note (# lines skipped). Each patch is
# `git diff FROM TO` (first-parent ranges of the V41PKG branch, so applying the series in order rebuilds TO's tree
# exactly). Writes OUT_DIR/patches/NAME and OUT_DIR/SERIES.tsv with the 12-hex tree id each patch must leave
# (install.sh checks it with git write-tree). No --full-index and no --binary: the series has no binary files, and
# abbreviated index lines keep 40-hex ids out of the repository.
set -euo pipefail
repo=${1:?V41PKG repo} in=${2:?series.in} out=${3:?out dir}
mkdir -p "$out/patches"
{
  printf '# patch\tfrom\tto\ttree_after\tgroup\tknob\tnote\n'
  prev_to=""
  while IFS=$'\t' read -r name from to group knob note; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    [[ -z "$prev_to" || "$(git -C "$repo" rev-parse "$from")" == "$(git -C "$repo" rev-parse "$prev_to")" ]] \
      || { echo "gen_series: $name starts at $from, not at the previous patch's end $prev_to" >&2; exit 1; }
    if git -C "$repo" diff --numstat "$from" "$to" | awk '$1 == "-" {bad = 1} END {exit !bad}'; then
      echo "gen_series: $name has a binary file" >&2; exit 1
    fi
    git -C "$repo" -c diff.noprefix=false -c diff.mnemonicPrefix=false -c core.quotePath=true \
      diff --no-color --no-ext-diff --find-renames "$from" "$to" > "$out/patches/$name"
    [[ -s "$out/patches/$name" ]] || { echo "gen_series: $name is empty" >&2; exit 1; }
    tree=$(git -C "$repo" rev-parse "$to^{tree}"); tree=${tree:0:12}
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$from" "$to" "$tree" "$group" "$knob" "$note"
    prev_to=$to
  done < "$in"
} > "$out/SERIES.tsv"
echo "gen_series: $(grep -vc '^#' "$out/SERIES.tsv") patches, $(du -sh "$out/patches" | cut -f1)"
