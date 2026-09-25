#!/usr/bin/env bash
# Verify a long-horizon state file keeps its contract:
#   - exactly the six fixed sections, in order
#   - no other H2 headings
#   - at most MAX lines (default 80)
#   - no line longer than 200 chars (a compact state is not a dump)
# Usage: check-state.sh <state.md> [max-lines]
# Exit 0 if valid, 1 with reasons on stdout otherwise.
set -u

FILE="${1:?state file}"
MAX="${2:-80}"
EXPECTED=("## Goal" "## Current plan" "## Done" "## Open" "## Decisions" "## Dropped")

fail=0
say() { echo "state-check: $*"; }

if [ ! -f "$FILE" ]; then
  say "missing file $FILE"
  exit 1
fi

lines=$(wc -l < "$FILE" | tr -d ' ')
if [ "$lines" -gt "$MAX" ]; then
  say "over cap: $lines lines > $MAX"
  fail=1
fi

long=$(awk 'length($0) > 200 {c++} END {print c+0}' "$FILE")
if [ "$long" -gt 0 ]; then
  say "$long line(s) longer than 200 chars"
  fail=1
fi

found_list=$(grep -E '^## ' "$FILE" | sed 's/[[:space:]]*$//')
expected_list=$(printf '%s\n' "${EXPECTED[@]}")
if [ "$found_list" != "$expected_list" ]; then
  say "sections must be exactly, in order: $(printf '%s; ' "${EXPECTED[@]}")"
  say "found: $(printf '%s' "$found_list" | tr '\n' ';' | sed 's/;/; /g')"
  fail=1
fi

if grep -qiE '^(## )?(log|history|run [0-9]+|changelog)' "$FILE"; then
  say "state.md must not contain a log/history section; that belongs in .lh/log/"
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  say "ok ($lines/$MAX lines)"
fi
exit "$fail"
