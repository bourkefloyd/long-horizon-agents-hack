#!/usr/bin/env bash
# Keep only the newest K run logs in .lh/log/. Older ones are deleted from the
# tree; git history still has them. The agent is told which runs are about to
# fall off (they are in its context this run) so it can fold anything worth
# keeping into state.md Decisions/Dropped.
# Usage: prune-logs.sh [K]
set -euo pipefail

KEEP="${1:-5}"
DIR=".lh/log"
[ -d "$DIR" ] || exit 0

ls "$DIR"/*.md 2>/dev/null | sed 's#.*/##; s/\.md$//' | sort -rn | tail -n "+$((KEEP + 1))" | while read -r id; do
  echo "prune-logs: dropping $DIR/$id.md"
  rm -f "$DIR/$id.md"
done
echo "prune-logs: $(ls "$DIR"/*.md 2>/dev/null | wc -l | tr -d ' ') log(s) kept (K=$KEEP)"
