#!/usr/bin/env bash
# Rebase the current LH agent branch onto the base branch so its PR never
# conflicts just because main moved. The only conflict this resolves on its
# own is .lh/<target>/state.md, via merge-state.sh (base keeps Goal, Current
# plan, Open, Decisions; Done and Dropped bullets are unioned) followed by the
# state contract check. Anything else aborts the rebase and leaves the branch
# exactly as it was, so the caller can still publish and let a human look.
#
# Usage: rebase-onto-base.sh <base-ref, e.g. origin/main> [state-max-lines]
# Exit 0: branch is on top of base (rebased or already there).
# Exit 1: rebase aborted; branch unchanged. Reason printed as a ::warning::.
set -euo pipefail

BASE="${1:?base ref (e.g. origin/main)}"
MAX="${2:-80}"
BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"

in_rebase() {
  local dir
  dir="$(git rev-parse --git-path rebase-merge)"
  [ -d "$dir" ] || [ -d "$(git rev-parse --git-path rebase-apply)" ]
}

if git merge-base --is-ancestor "$BASE" HEAD; then
  echo "rebase: already on top of $BASE"
  exit 0
fi

if git -c core.editor=true rebase "$BASE"; then
  echo "rebase: clean onto $BASE"
  exit 0
fi

steps=0
while in_rebase; do
  steps=$((steps + 1))
  if [ "$steps" -gt 50 ]; then
    echo "::warning::rebase: gave up after $steps conflict rounds; publishing without rebase"
    git rebase --abort
    exit 1
  fi

  conflicts="$(git diff --name-only --diff-filter=U)"
  others="$(printf '%s\n' "$conflicts" | grep -vE '^\.lh/[a-z0-9-]+/state\.md$' || true)"
  if [ -z "$conflicts" ] || [ -n "$others" ]; then
    echo "::warning::rebase: conflict outside state.md, publishing without rebase:"
    printf '%s\n' "$conflicts" | sed 's/^/    /'
    git rebase --abort
    exit 1
  fi

  for f in $conflicts; do
    # Stage 2 is the base side, stage 3 is the agent commit being replayed.
    git show ":2:$f" > "$TMP/state.ours.md"
    git show ":3:$f" > "$TMP/state.theirs.md"
    bash "$BIN/merge-state.sh" "$TMP/state.ours.md" "$TMP/state.theirs.md" > "$f"
    if ! bash "$BIN/check-state.sh" "$f" "$MAX"; then
      echo "::warning::rebase: merged $f breaks the state contract; publishing without rebase"
      git rebase --abort
      exit 1
    fi
    git add "$f"
    echo "rebase: auto-resolved $f"
  done

  if git diff --cached --quiet; then
    git rebase --skip || true
  else
    git -c core.editor=true rebase --continue || true
  fi
done

echo "rebase: on top of $BASE after resolving state.md"
exit 0
