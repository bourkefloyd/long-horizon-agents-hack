from __future__ import annotations

import re

from .models import VideoAdConcept


FAMOUS_BRAND_TERMS = (
    "amazon",
    "apple",
    "big mac",
    "burger king",
    "coca-cola",
    "coke",
    "costco",
    "dunkin",
    "facebook",
    "google",
    "instagram",
    "kfc",
    "mcdonald",
    "meta",
    "nike",
    "pepsi",
    "starbucks",
    "target",
    "tesla",
    "tiktok",
    "walmart",
    "wendy's",
    "youtube",
)


def validate_no_famous_brands(concepts: list[VideoAdConcept]) -> None:
    violations: list[str] = []
    for concept in concepts:
        fields = {
            "hook": concept.hook,
            "script": concept.script,
            "video_script": concept.video_script,
            "visual_prompt": concept.visual_prompt,
            "audio_prompt": concept.audio_prompt,
            "negative_prompt": concept.negative_prompt,
            "bfl_prompt": str(concept.bfl_payload.get("prompt", "")),
        }
        for field_name, value in fields.items():
            blocked = find_famous_brand_terms(value)
            if blocked:
                violations.append(
                    f"variant {concept.variant_index} {field_name}: {', '.join(sorted(blocked))}"
                )
    if violations:
        details = "\n".join(f"- {violation}" for violation in violations)
        raise ValueError(f"Generated creative references famous brands:\n{details}")


def find_famous_brand_terms(text: str) -> set[str]:
    lower = text.lower()
    found = set()
    for term in FAMOUS_BRAND_TERMS:
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            found.add(term)
    return found
