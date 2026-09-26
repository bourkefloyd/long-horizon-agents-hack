# Local Liquid models over Cloudflare tunnels

The hackathon demo runs Liquid's LFM2 models on a Mac with `llama-server` and exposes each OpenAI-compatible endpoint through an ephemeral Cloudflare Quick Tunnel:

- `LFM2-1.2B-Q4_K_M.gguf` on `127.0.0.1:8081`
- `LFM2-VL-1.6B-Q8_0.gguf` plus `mmproj-LFM2-VL-1.6B-Q8_0.gguf` on `127.0.0.1:8082`

Cloud Run reads the tunnel addresses from `LIQUID_TEXT_BASE_URL` and `LIQUID_VISION_BASE_URL`. The campaign service's `GET /liquid/health` endpoint checks the text server's `/v1/models` endpoint.

## One-time setup

```bash
brew install tmux llama.cpp cloudflared
mkdir -p ~/models/liquid
curl -fL -o ~/models/liquid/LFM2-1.2B-Q4_K_M.gguf \
  https://huggingface.co/LiquidAI/LFM2-1.2B-GGUF/resolve/main/LFM2-1.2B-Q4_K_M.gguf
curl -fL -o ~/models/liquid/LFM2-VL-1.6B-Q8_0.gguf \
  https://huggingface.co/LiquidAI/LFM2-VL-1.6B-GGUF/resolve/main/LFM2-VL-1.6B-Q8_0.gguf
curl -fL -o ~/models/liquid/mmproj-LFM2-VL-1.6B-Q8_0.gguf \
  https://huggingface.co/LiquidAI/LFM2-VL-1.6B-GGUF/resolve/main/mmproj-LFM2-VL-1.6B-Q8_0.gguf
```

Set `LFM_DIR` to use another model directory. Set `LLAMA_SERVER` to the executable, or `LLAMA_BIN` to the directory containing it, when it is not on `PATH`.

## Start or restart the demo

```bash
./scripts/liquid-local.sh
```

The script recreates four tmux sessions: `liquid-text`, `liquid-vision`, `tunnel-text`, and `tunnel-vision`. It waits for both local servers, prints both public URLs, and prints the two `gcloud run services update` commands needed to re-point `lh-campaign-service` and `lh-web`.

Cloudflare Quick Tunnel URLs are ephemeral. They change after a tunnel restart or reboot, so run the newly printed `gcloud` commands every time. Updating environment variables creates a new Cloud Run revision but does not alter revision tags such as `demo`.

## Verify

```bash
curl http://127.0.0.1:8081/v1/models
curl "$LIQUID_TEXT_BASE_URL/v1/models"
curl https://lh-campaign-service-row663omlq-uc.a.run.app/liquid/health
```

Inspect logs with `tmux capture-pane -pt liquid-text` or attach interactively with `tmux attach -t liquid-text`.
