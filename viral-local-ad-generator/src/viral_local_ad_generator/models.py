from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class NewsStory:
    title: str
    url: str
    source: str = ""
    published_at: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    virality_score: float = 0.0
    brand_safe: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NewsStory":
        fields = {
            "title",
            "url",
            "source",
            "published_at",
            "snippet",
            "relevance_score",
            "virality_score",
            "brand_safe",
            "raw",
        }
        return cls(**{key: value for key, value in payload.items() if key in fields})


@dataclass
class VideoAdConcept:
    story_title: str
    story_url: str
    variant_index: int
    angle: str
    hook: str
    script: str
    video_script: str
    visual_prompt: str
    audio_prompt: str
    negative_prompt: str
    duration_seconds: int = 8
    aspect_ratio: str = "9:16"
    bfl_payload: dict[str, Any] = field(default_factory=dict)
    bfl_job: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VideoAdConcept":
        fields = {
            "story_title",
            "story_url",
            "variant_index",
            "angle",
            "hook",
            "script",
            "video_script",
            "visual_prompt",
            "audio_prompt",
            "negative_prompt",
            "duration_seconds",
            "aspect_ratio",
            "bfl_payload",
            "bfl_job",
        }
        return cls(**{key: value for key, value in payload.items() if key in fields})
