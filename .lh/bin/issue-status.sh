#!/usr/bin/env bash
# Maintain one status comment per run on the issue that owns the run. The
# comment is created at start and edited in place at each milestone, so the
# issue thread gets a single, always-current entry instead of a comment per
# step. All writes use GITHUB_TOKEN, whose events do not re-trigger workflows.
#
# Every milestone bullet carries how long the phase since the previous
# milestone took and the total elapsed time, e.g.
#   - 23:05Z agent finished; 8 file(s) changed · +5m 41s · 6m 02s elapsed
# `finish` additionally appends a phase breakdown and, when GITHUB_RUN_ID is
# set, a collapsed per-step timing table read from the Actions jobs API.
#
# Usage:
#   issue-status.sh init "<header markdown>"     creates the comment, prints its id
#   issue-status.sh update <status> "<line>"     sets the Status line, appends a
#                                                timestamped bullet, edits the comment
#   issue-status.sh finish <status> "<line>"     update + timing summary (final call)
#
# Env: GH_TOKEN, GITHUB_REPOSITORY, ISSUE_NUMBER, STATUS_FILE (local body copy),
#      STATUS_COMMENT_ID (required for update; falls back to a new comment),
#      GITHUB_RUN_ID (optional; enables the per-step table in `finish`).
# Milestone epochs live in "${STATUS_FILE}.marks" (tab-separated: epoch, line).
set -euo pipefail

cmd=${1:-}
[ $# -ge 1 ] || { echo "usage: issue-status.sh init|update|finish ..." >&2; exit 2; }
shift
: "${GITHUB_REPOSITORY:?}" "${ISSUE_NUMBER:?}" "${STATUS_FILE:?}"
api="repos/${GITHUB_REPOSITORY}/issues"
MARKS="${STATUS_FILE}.marks"
now() { date -u +%H:%MZ; }
epoch() { date -u +%s; }

# fmt_dur <seconds> -> "42s" | "5m 41s" | "1h 03m"
fmt_dur() {
  local s=$1
  if [ "$s" -lt 60 ]; then printf '%ds' "$s"
  elif [ "$s" -lt 3600 ]; then printf '%dm %02ds' $((s / 60)) $((s % 60))
  else printf '%dh %02dm' $((s / 3600)) $((s % 3600 / 60)); fi
}

first_mark() { [ -s "$MARKS" ] && head -n1 "$MARKS" | cut -f1 || true; }
last_mark() { [ -s "$MARKS" ] && tail -n1 "$MARKS" | cut -f1 || true; }

# mark <line> -> records the milestone and prints the timing suffix for its bullet.
mark() {
  local line=$1 t suffix="" first last
  t=$(epoch); first=$(first_mark); last=$(last_mark)
  if [ -n "$last" ]; then
    suffix=" · +$(fmt_dur $((t - last)))"
    [ -n "$first" ] && suffix="${suffix} · $(fmt_dur $((t - first))) elapsed"
  fi
  printf '%s\t%s\n' "$t" "$line" >> "$MARKS"
  printf '%s' "$suffix"
}

# Phase breakdown from the marks file: "Timing: agent finished +5m 41s · checks +21s · ... — total 6m 30s".
phase_summary() {
  [ -s "$MARKS" ] || return 0
  awk -F'\t' '
    function dur(s) { return s < 60 ? s "s" : (s < 3600 ? int(s / 60) "m " sprintf("%02d", s % 60) "s" : int(s / 3600) "h " sprintf("%02d", (s % 3600) / 60) "m") }
    function short(l) { sub(/[;:(].*$/, "", l); sub(/[[:space:]]+$/, "", l); return l }
    NR == 1 { first = $1; prev = $1; next }
    { out = out (out ? " · " : "") short($2) " +" dur($1 - prev); prev = $1 }
    END { if (NR > 1) print "Timing: " out " — total " dur(prev - first) }
  ' "$MARKS"
}

# Per-step table for this run from the Actions jobs API (best effort, never fatal).
step_table() {
  [ -n "${GITHUB_RUN_ID:-}" ] || return 0
  local rows
  rows=$(gh api "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs" --paginate --jq '
    [.jobs[] | select(.name | test("^Post |^Complete job$|^Set up job$") | not) | .steps[]
      | select(.conclusion != "skipped" and (.name | test("^Post |^Complete job$|^Set up job$") | not))
      | {name, status, conclusion,
         secs: (if .started_at then ((.completed_at // (now | todate)) | fromdate) - (.started_at | fromdate) else null end)}
      | select(.secs == null or .secs >= 1 or .conclusion != "success")]
    | .[] | "| \(.name) | \(if .secs == null then "-" elif .secs < 60 then "\(.secs)s" else "\(.secs / 60 | floor)m \(.secs % 60 | tostring | if length < 2 then "0" + . else . end)s" end) | \(if .status != "completed" then "running" else .conclusion end) |"
  ' 2>/dev/null) || return 0
  [ -n "$rows" ] || return 0
  printf '\n<details><summary>Step timings</summary>\n\n| step | took | result |\n|---|---|---|\n%s\n\n</details>\n' "$rows"
}

push_body() {
  if [ -n "${STATUS_COMMENT_ID:-}" ]; then
    gh api -X PATCH "${api}/comments/${STATUS_COMMENT_ID}" -F body=@"$STATUS_FILE" --jq .id >/dev/null
  else
    gh api -X POST "${api}/${ISSUE_NUMBER}/comments" -F body=@"$STATUS_FILE" --jq .id
  fi
}

# set_status_and_append <status> <bullet-line> [extra markdown...]
set_status_and_append() {
  local status=$1 line=$2 suffix
  case "$status" in
    *[!a-z]*) echo "status must be a lowercase word, got '$status'" >&2; exit 2 ;;
  esac
  [ -f "$STATUS_FILE" ] || { echo "Status: **${status}**"; echo; } > "$STATUS_FILE"
  suffix=$(mark "$line")
  { sed "s|^Status: .*|Status: **${status}**|" "$STATUS_FILE"; printf -- '- %s %s%s\n' "$(now)" "$line" "$suffix"; } > "${STATUS_FILE}.tmp"
  mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
}

case "$cmd" in
  init)
    header=${1:?header required}
    rm -f "$MARKS"
    {
      printf '%s\n\n' "$header"
      echo "Status: **running**"
      echo
      echo "- $(now) started$(mark started)"
    } > "$STATUS_FILE"
    gh api -X POST "${api}/${ISSUE_NUMBER}/comments" -F body=@"$STATUS_FILE" --jq .id
    ;;
  update)
    set_status_and_append "${1:?status required}" "${2:?line required}"
    push_body
    ;;
  finish)
    set_status_and_append "${1:?status required}" "${2:?line required}"
    summary=$(phase_summary)
    [ -n "$summary" ] && printf '\n%s\n' "$summary" >> "$STATUS_FILE"
    step_table >> "$STATUS_FILE" || true
    push_body
    ;;
  *)
    echo "unknown command '$cmd'" >&2; exit 2 ;;
esac
