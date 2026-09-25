#!/usr/bin/env bash
# Merge two versions of a long-horizon state.md without a human.
#
# The base branch (main) owns the direction of a target, so its Goal, Current
# plan, Open, and Decisions sections win outright. The agent branch only adds
# to the record of what happened, so its Done and Dropped bullets are unioned
# into the base version (base bullets first, then new agent bullets, exact
# duplicates removed after trimming whitespace).
#
# During `git rebase <base>` the index stage 2 is the base side and stage 3 is
# the commit being replayed, which matches the argument order here.
#
# Usage: merge-state.sh <ours: base/main state.md> <theirs: agent state.md> > merged.md
# The caller re-runs check-state.sh on the result; this script does not cap lines.
set -euo pipefail

OURS="${1:?ours state file (base branch version)}"
THEIRS="${2:?theirs state file (agent branch version)}"
for f in "$OURS" "$THEIRS"; do
  [ -f "$f" ] || { echo "merge-state: missing file $f" >&2; exit 1; }
done

awk '
BEGIN {
  n_order = split("## Goal|## Current plan|## Done|## Open|## Decisions|## Dropped", order, "|")
  union["## Done"] = 1
  union["## Dropped"] = 1
}
FNR == 1 { fi++; sec = "" }
/^## / {
  sec = $0
  sub(/[[:space:]]+$/, "", sec)
  next
}
{
  line = $0
  sub(/[[:space:]]+$/, "", line)
  if (sec == "") {
    # Text before the first section (the "# state: <target>" title) comes from ours.
    if (fi == 1) { pre_n++; pre[pre_n] = line }
    next
  }
  count[fi, sec]++
  body[fi, sec, count[fi, sec]] = line
}
function print_trimmed(f, s,   i, first, last) {
  first = 0; last = 0
  for (i = 1; i <= count[f, s]; i++) {
    if (body[f, s, i] != "") { if (!first) first = i; last = i }
  }
  if (!first) return 0
  for (i = first; i <= last; i++) print body[f, s, i]
  return 1
}
function print_union(s,   f, i, key, printed) {
  delete seen
  printed = 0
  for (f = 1; f <= 2; f++) {
    for (i = 1; i <= count[f, s]; i++) {
      key = body[f, s, i]
      gsub(/^[[:space:]]+/, "", key)
      if (key == "" || (key in seen)) continue
      seen[key] = 1
      print body[f, s, i]
      printed++
    }
  }
  return printed
}
END {
  last = 0
  for (i = 1; i <= pre_n; i++) if (pre[i] != "") last = i
  for (i = 1; i <= last; i++) print pre[i]
  for (k = 1; k <= n_order; k++) {
    s = order[k]
    if (k > 1 || last > 0) print ""
    print s
    print ""
    if (s in union) print_union(s)
    else print_trimmed(1, s)
  }
}
' "$OURS" "$THEIRS"
