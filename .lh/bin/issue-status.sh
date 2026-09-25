#!/usr/bin/env bash
# Maintain one status comment per run on the issue that owns the run. The
# comment is created at start and edited in place at each milestone, so the
# issue thread gets a single, always-current entry instead of a comment per
# step. All writes use GITHUB_TOKEN, whose events do not re-trigger workflows.
#
# Usage:
#   issue-status.sh init "<header markdown>"     creates the comment, prints its id
#   issue-status.sh update <status> "<line>"     sets the Status line, appends a
#                                                timestamped bullet, edits the comment
#
# Env: GH_TOKEN, GITHUB_REPOSITORY, ISSUE_NUMBER, STATUS_FILE (local body copy),
#      STATUS_COMMENT_ID (required for update; falls back to a new comment).
set -euo pipefail

cmd=${1:-}
[ $# -ge 1 ] || { echo "usage: issue-status.sh init|update ..." >&2; exit 2; }
shift
: "${GITHUB_REPOSITORY:?}" "${ISSUE_NUMBER:?}" "${STATUS_FILE:?}"
api="repos/${GITHUB_REPOSITORY}/issues"
now() { date -u +%H:%MZ; }

case "$cmd" in
  init)
    header=${1:?header required}
    {
      printf '%s\n\n' "$header"
      echo "Status: **running**"
      echo
      echo "- $(now) started"
    } > "$STATUS_FILE"
    gh api -X POST "${api}/${ISSUE_NUMBER}/comments" -F body=@"$STATUS_FILE" --jq .id
    ;;
  update)
    status=${1:?status required}
    line=${2:?line required}
    case "$status" in
      *[!a-z]*) echo "status must be a lowercase word, got '$status'" >&2; exit 2 ;;
    esac
    [ -f "$STATUS_FILE" ] || { echo "Status: **${status}**"; echo; } > "$STATUS_FILE"
    { sed "s|^Status: .*|Status: **${status}**|" "$STATUS_FILE"; printf -- '- %s %s\n' "$(now)" "$line"; } > "${STATUS_FILE}.tmp"
    mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
    if [ -n "${STATUS_COMMENT_ID:-}" ]; then
      gh api -X PATCH "${api}/comments/${STATUS_COMMENT_ID}" -F body=@"$STATUS_FILE" --jq .id >/dev/null
    else
      gh api -X POST "${api}/${ISSUE_NUMBER}/comments" -F body=@"$STATUS_FILE" --jq .id
    fi
    ;;
  *)
    echo "unknown command '$cmd'" >&2; exit 2 ;;
esac
