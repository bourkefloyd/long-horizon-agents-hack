#!/usr/bin/env bash
# Deterministic, offline checks for Thomas's Nimble-backed ad generator.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
APP="$ROOT/viral-local-ad-generator"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cd "$APP"

echo "checks(nimble): compile Python sources"
PYTHONPYCACHEPREFIX="$TMP_DIR/pycache" python3 -m compileall -q src

echo "checks(nimble): verify environment-only Nimble credentials"
python3 - <<'PY'
from pathlib import Path

config = Path("src/viral_local_ad_generator/config.py").read_text(encoding="utf-8")
client = Path("src/viral_local_ad_generator/nimble_client.py").read_text(encoding="utf-8")
assert 'os.getenv("NIMBLE_API_KEY", "")' in config
assert '"Authorization": f"Bearer {self.api_key}"' in client
PY

echo "checks(nimble): run offline mock-news dry run"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m viral_local_ad_generator.cli run \
  --campaign examples/new-bigmac-test.txt \
  --market "San Francisco" \
  --mock-news \
  --dry-run \
  --max-stories 1 \
  --max-videos 1 \
  --output "$TMP_DIR/run"

echo "checks(nimble): validate bounded marketing concept output"
python3 - "$TMP_DIR/run/run.json" <<'PY'
import json
import os
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert payload["market"] == "San Francisco"
assert payload["story_count"] == len(payload["stories"]) == 1
assert payload["concept_count"] == len(payload["concepts"]) == 1

story = payload["stories"][0]
assert all(story.get(key) not in (None, "") for key in ("title", "url"))
assert story["brand_safe"] is True

concept = payload["concepts"][0]
required = (
    "story_title",
    "story_url",
    "angle",
    "hook",
    "script",
    "video_script",
    "visual_prompt",
    "audio_prompt",
    "negative_prompt",
    "bfl_payload",
)
assert all(concept.get(key) not in (None, "") for key in required)
assert concept["aspect_ratio"] == "9:16"
assert concept["duration_seconds"] <= 10
assert concept["bfl_payload"]["duration"] <= 10
assert concept["bfl_payload"]["aspect_ratio"] == "9:16"

serialized = json.dumps(payload)
key = os.environ.get("NIMBLE_API_KEY", "")
assert not key or key not in serialized
PY

echo "checks(nimble): ok"
