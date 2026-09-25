"""Stage generated concepts as CDN variants under cdn/staging/<campaign_id>/<variant_id>/.

The layout and meta.json contract are documented in docs/cdn.md. Publishing to the bucket is a
separate, human-approved step (merge to main); this module only writes reviewable files.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import NewsStory, VideoAdConcept
from .prompts import make_campaign_info

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SUPPORTED_DIMS = "9:16"
STAGING_AGENT = "viral-local-ad-generator"
FENCED_JSON = re.compile(r"```json\s*(?P<body>\{.*?\})\s*```", re.DOTALL)


@dataclass
class CampaignRecord:
    id: str
    name: str = ""
    brief: str = ""
    vertical: str = ""
    geo: str = ""
    audience: str = ""
    dims: str = SUPPORTED_DIMS
    issue_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CampaignRecord":
        fields = {"id", "name", "brief", "vertical", "geo", "audience", "dims", "issue_url"}
        record = cls(**{key: value for key, value in payload.items() if key in fields})
        record.validate()
        return record

    def validate(self) -> None:
        if not isinstance(self.id, str) or not SAFE_ID.fullmatch(self.id):
            raise ValueError("campaign id must use only letters, numbers, dot, dash, or underscore")
        if not str(self.brief).strip():
            raise ValueError(f"campaign {self.id!r} has an empty brief")
        if not str(self.geo).strip():
            raise ValueError(f"campaign {self.id!r} has an empty geo (market)")
        if self.dims != SUPPORTED_DIMS:
            raise ValueError(
                f"campaign {self.id!r} asks for dims {self.dims!r}; only {SUPPORTED_DIMS} is supported by the "
                "generator and the CDN manifest"
            )


def load_campaign_record(path: Path) -> CampaignRecord:
    """Read a campaign record from a JSON file or from an issue body containing a ```json block."""
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if stripped.startswith("{"):
        payload = json.loads(stripped)
    else:
        match = FENCED_JSON.search(text)
        if not match:
            raise ValueError(f"{path} contains neither a JSON object nor a fenced ```json block")
        payload = json.loads(match.group("body"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return CampaignRecord.from_dict(payload)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "variant"


def variant_id_for(concept: VideoAdConcept) -> str:
    return f"{concept.variant_index:02d}-{slugify(concept.angle)}"


def stage_campaign_variants(
    record: CampaignRecord,
    stories: list[NewsStory],
    concepts: list[VideoAdConcept],
    staging_root: Path,
    generated_at: str | None = None,
) -> list[Path]:
    """Write one <variant>/ folder per concept plus a campaign.json index. Returns the variant folders."""
    record.validate()
    if not concepts:
        raise ValueError(f"campaign {record.id!r} has no concepts to stage")
    generated_at = generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    campaign = make_campaign_info(record.brief)
    stories_by_url = {story.url: story for story in stories}
    campaign_dir = staging_root / record.id
    campaign_dir.mkdir(parents=True, exist_ok=True)

    variant_dirs: list[Path] = []
    variant_ids: list[str] = []
    for concept in concepts:
        if concept.aspect_ratio != record.dims:
            raise ValueError(
                f"concept variant {concept.variant_index} is {concept.aspect_ratio}, campaign dims are {record.dims}"
            )
        variant_id = variant_id_for(concept)
        if not SAFE_ID.fullmatch(variant_id):
            raise ValueError(f"variant id {variant_id!r} is not a safe directory name")
        variant_dir = campaign_dir / variant_id
        variant_dir.mkdir(parents=True, exist_ok=True)
        story = stories_by_url.get(concept.story_url)
        (variant_dir / "script.txt").write_text(render_script(record, concept, story), encoding="utf-8")
        meta = build_meta(record, concept, campaign["cta"], generated_at)
        (variant_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        variant_dirs.append(variant_dir)
        variant_ids.append(variant_id)

    index = {
        "campaign": record.to_dict(),
        "market": record.geo,
        "generated_at": generated_at,
        "agent": STAGING_AGENT,
        "stories": [
            {
                "title": story.title,
                "url": story.url,
                "source": story.source,
                "published_at": story.published_at,
                "brand_safe": story.brand_safe,
            }
            for story in stories
        ],
        "variants": variant_ids,
    }
    (campaign_dir / "campaign.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return variant_dirs


def build_meta(record: CampaignRecord, concept: VideoAdConcept, cta: str, generated_at: str) -> dict[str, Any]:
    variant_id = variant_id_for(concept)
    targeting: dict[str, Any] = {}
    if record.audience.strip():
        targeting["audience"] = [record.audience.strip()]
    targeting["geo"] = [record.geo.strip()]
    targeting["weight"] = 1
    targeting["active"] = True
    duration = concept.bfl_payload.get("duration", concept.duration_seconds)
    return {
        "id": f"{record.id}-{variant_id}",
        "hook": concept.hook,
        "cta": cta,
        "media_type": "script",
        "media_file": "script.txt",
        "script_file": "script.txt",
        "duration_s": int(duration),
        "aspect": record.dims,
        "targeting": targeting,
        "source": {
            "agent": STAGING_AGENT,
            "generated_at": generated_at,
            "brief_ref": record.issue_url or f"campaign:{record.id}",
        },
    }


def render_script(record: CampaignRecord, concept: VideoAdConcept, story: NewsStory | None) -> str:
    lines = [
        f"{record.name or record.id} - variant {concept.variant_index} ({concept.angle}) - {record.dims} vertical ad",
        f"Brief: {record.brief}",
    ]
    if record.vertical:
        lines.append(f"Vertical: {record.vertical}")
    if record.audience:
        lines.append(f"Audience: {record.audience}")
    if story is not None:
        source = f"{story.source}; " if story.source else ""
        lines.append(f"Local moment: {story.title} ({source}{story.url})")
    lines.extend(["", f"HOOK: {concept.hook}", "", concept.video_script, ""])
    lines.append("Unofficial spec work for a hackathon experiment; not affiliated with or endorsed by anyone in the story.")
    return "\n".join(lines) + "\n"
