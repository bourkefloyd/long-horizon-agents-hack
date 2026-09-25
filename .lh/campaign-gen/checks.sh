#!/usr/bin/env bash
# Deterministic, offline checks for Thomas's campaign generator.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
APP="$ROOT/viral-local-ad-generator"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cd "$APP"

echo "checks(campaign-gen): compile Python sources"
PYTHONPYCACHEPREFIX="$TMP_DIR/pycache" python3 -m compileall -q src

echo "checks(campaign-gen): verify environment-only Nimble credentials"
python3 - <<'PY'
from pathlib import Path

config = Path("src/viral_local_ad_generator/config.py").read_text(encoding="utf-8")
client = Path("src/viral_local_ad_generator/nimble_client.py").read_text(encoding="utf-8")
assert 'os.getenv("NIMBLE_API_KEY", "")' in config
assert '"Authorization": f"Bearer {self.api_key}"' in client
PY

echo "checks(campaign-gen): run offline unit tests"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q

echo "checks(campaign-gen): run offline mock-news dry run"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m viral_local_ad_generator.cli run \
  --campaign examples/new-bigmac-test.txt \
  --market "San Francisco" \
  --mock-news \
  --dry-run \
  --max-stories 1 \
  --max-videos 1 \
  --output "$TMP_DIR/run"

echo "checks(campaign-gen): validate bounded marketing concept output"
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

echo "checks(campaign-gen): stage a website campaign record under cdn/staging layout"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m viral_local_ad_generator.cli stage-cdn \
  --campaign-record examples/sf-coffee-launch.json \
  --mock-news \
  --max-stories 1 \
  --max-videos 2 \
  --output "$TMP_DIR/stage-run" \
  --staging "$TMP_DIR/staging"

echo "checks(campaign-gen): validate staged meta.json files"
python3 - "$TMP_DIR/staging" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

staging = Path(sys.argv[1])
safe_id = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
metas = sorted(staging.glob("*/*/meta.json"))
assert len(metas) == 2, [str(path) for path in metas]
assert {path.parent.parent.name for path in metas} == {"sf-coffee-launch"}
index = json.loads((staging / "sf-coffee-launch" / "campaign.json").read_text(encoding="utf-8"))
assert index["campaign"]["id"] == "sf-coffee-launch"
assert index["variants"] == [path.parent.name for path in metas]

key = os.environ.get("NIMBLE_API_KEY", "")
for meta_path in metas:
    variant_dir = meta_path.parent
    assert safe_id.fullmatch(variant_dir.name)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    for field in ("id", "hook", "cta", "media_type", "media_file", "aspect", "targeting", "source"):
        assert meta.get(field) not in (None, ""), (meta_path, field)
    assert meta["id"] == f"sf-coffee-launch-{variant_dir.name}"
    assert meta["media_type"] == "script"
    assert (variant_dir / meta["media_file"]).is_file()
    assert (variant_dir / meta["script_file"]).read_text(encoding="utf-8").strip()
    assert meta["aspect"] == "9:16"
    assert 0 < meta["duration_s"] <= 10
    assert meta["targeting"]["weight"] > 0 and meta["targeting"]["active"] is True
    assert meta["targeting"]["geo"] == ["San Francisco"]
    assert meta["source"]["agent"] and meta["source"]["generated_at"].endswith("Z")
    serialized = json.dumps(meta) + (variant_dir / "script.txt").read_text(encoding="utf-8")
    assert not key or key not in serialized
PY

echo "checks(campaign-gen): ok"
