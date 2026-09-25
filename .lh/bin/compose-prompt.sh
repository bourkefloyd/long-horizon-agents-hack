#!/usr/bin/env bash
# Build the exact prompt one run sees. Nothing else is in context:
#   prompt.md, the issue text, state.md, the last K run logs, the guardrails.
# Usage: compose-prompt.sh <target> <issue-file-or-missing> <keep-logs> <state-max-lines> [instruction]
set -euo pipefail

TARGET="${1:?target}"
ISSUE_FILE="${2:-}"
KEEP="${3:-5}"
MAX="${4:-80}"
INSTRUCTION="${5:-}"
DIR=".lh/$TARGET"

cat <<EOF
You are the long-horizon agent for target "$TARGET" in this repository, running headless in GitHub Actions.

# Hard rules (enforced outside you; breaking them fails the run)
- Do NOT run git or gh. Do NOT create branches, commit, push, open PRs, or comment. A later deterministic step does all of that.
- Only edit files. Never touch .github/, .cursor/, .lh/bin/, .lh/log/, or any .env file.
- Do not run rm, curl, wget, bash, sh. You may run ls, cat, head, tail, wc, grep, find, node, npm.
- Rewrite $DIR/state.md from scratch every run. Keep exactly these H2 sections in this order: Goal, Current plan, Done, Open, Decisions, Dropped. Max $MAX lines, max 200 chars per line. No log, no history, no dates. If you break this, your state.md is thrown away and the previous one is restored.
- Fold anything worth keeping from the run logs below into Decisions or Dropped; logs older than the last $KEEP are deleted.
- You may edit $DIR/prompt.md (your own instructions) if you have a concrete reason. Say why in state.md Decisions. It takes effect only after a human merges the PR.
- Finish with a short plain-text summary (under 15 lines): what changed, what the next run should do.

# Target instructions ($DIR/prompt.md)

$(cat "$DIR/prompt.md")

# Current state ($DIR/state.md)

$(cat "$DIR/state.md")
EOF

if [ -n "$ISSUE_FILE" ] && [ -f "$ISSUE_FILE" ]; then
  echo
  echo "# Issue driving this work"
  echo
  head -c 12000 "$ISSUE_FILE"
  echo
fi

if [ -n "$INSTRUCTION" ]; then
  echo
  echo "# One-shot instruction for this run (from the trigger)"
  echo
  printf '%s\n' "$INSTRUCTION" | head -c 4000
fi

echo
echo "# Last run logs (newest first, at most $KEEP)"
echo
if [ -n "$(find .lh/log -maxdepth 1 -name '*.md' -type f 2>/dev/null)" ]; then
  find .lh/log -maxdepth 1 -name '*.md' -type f | sed 's#.*/##; s/\.md$//' | sort -rn | head -n "$KEEP" | while read -r id; do
    echo "--- .lh/log/$id.md ---"
    head -c 3000 ".lh/log/$id.md"
    echo
  done
else
  echo "(none yet; this is the first run)"
fi
