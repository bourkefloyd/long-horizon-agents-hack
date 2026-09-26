#!/usr/bin/env bash
set -euo pipefail

LFM_DIR="${LFM_DIR:-$HOME/models/liquid}"
LLAMA_SERVER="${LLAMA_SERVER:-${LLAMA_BIN:+$LLAMA_BIN/llama-server}}"
LLAMA_SERVER="${LLAMA_SERVER:-$(command -v llama-server || true)}"
PROJECT_ID="${GCP_PROJECT_ID:-long-horizon-agents-hack}"
REGION="${GCP_REGION:-us-central1}"

TEXT_MODEL="$LFM_DIR/LFM2-1.2B-Q4_K_M.gguf"
VISION_MODEL="$LFM_DIR/LFM2-VL-1.6B-Q8_0.gguf"
VISION_MMPROJ="$LFM_DIR/mmproj-LFM2-VL-1.6B-Q8_0.gguf"
TEXT_LOG="${TMPDIR:-/tmp}/liquid-tunnel-text.log"
VISION_LOG="${TMPDIR:-/tmp}/liquid-tunnel-vision.log"

for command in tmux cloudflared curl; do
  command -v "$command" >/dev/null || {
    echo "Missing required command: $command" >&2
    exit 1
  }
done

[[ -x "$LLAMA_SERVER" ]] || {
  echo "llama-server not found; install it with: brew install llama.cpp" >&2
  exit 1
}

for model in "$TEXT_MODEL" "$VISION_MODEL" "$VISION_MMPROJ"; do
  [[ -f "$model" ]] || {
    echo "Missing model: $model" >&2
    exit 1
  }
done

start_tmux() {
  local session="$1"
  shift
  local shell_command
  # macOS ships bash 3.2, where `printf -v` inside a function corrupts the script parser.
  shell_command=$(printf '%q ' "$@")
  tmux kill-session -t "=$session" 2>/dev/null || true
  tmux new-session -d -s "$session" "$shell_command"
  # Keep the pane (and its logs) around if the process dies, so failures are inspectable.
  tmux set-option -t "=$session" remain-on-exit on >/dev/null 2>&1 || true
}

wait_for_server() {
  local port="$1"
  local i
  for ((i = 0; i < 180; i++)); do
    if curl -fsS "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "llama-server on port $port did not become healthy" >&2
  return 1
}

wait_for_tunnel() {
  local log="$1"
  local i url
  for ((i = 0; i < 60; i++)); do
    url="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' "$log" 2>/dev/null | tail -1 || true)"
    if [[ -n "$url" ]]; then
      printf '%s' "$url"
      return 0
    fi
    sleep 1
  done
  echo "cloudflared did not publish a URL; inspect $log" >&2
  return 1
}

start_tmux liquid-text "$LLAMA_SERVER" \
  -m "$TEXT_MODEL" --port 8081 --host 127.0.0.1 -t 4 -c 4096 --no-webui
start_tmux liquid-vision "$LLAMA_SERVER" \
  -m "$VISION_MODEL" --mmproj "$VISION_MMPROJ" \
  --port 8082 --host 127.0.0.1 -t 4 -c 4096 --no-webui

wait_for_server 8081
wait_for_server 8082

: >"$TEXT_LOG"
: >"$VISION_LOG"
start_tmux tunnel-text cloudflared tunnel --no-autoupdate \
  --url http://127.0.0.1:8081 --logfile "$TEXT_LOG"
start_tmux tunnel-vision cloudflared tunnel --no-autoupdate \
  --url http://127.0.0.1:8082 --logfile "$VISION_LOG"

TEXT_URL="$(wait_for_tunnel "$TEXT_LOG")"
VISION_URL="$(wait_for_tunnel "$VISION_LOG")"

cat <<EOF
Liquid is running in tmux sessions:
  liquid-text    http://127.0.0.1:8081
  liquid-vision  http://127.0.0.1:8082
  tunnel-text    $TEXT_URL
  tunnel-vision  $VISION_URL

Quick-tunnel URLs are ephemeral and change whenever a tunnel restarts.

Re-point Cloud Run:
gcloud run services update lh-campaign-service --project "$PROJECT_ID" --region "$REGION" --update-env-vars "LIQUID_TEXT_BASE_URL=$TEXT_URL,LIQUID_VISION_BASE_URL=$VISION_URL"
gcloud run services update lh-web --project "$PROJECT_ID" --region "$REGION" --update-env-vars "LIQUID_TEXT_BASE_URL=$TEXT_URL,LIQUID_VISION_BASE_URL=$VISION_URL"
EOF
