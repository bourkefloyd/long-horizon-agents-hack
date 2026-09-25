from __future__ import annotations

import re

from .brand_guard import find_famous_brand_terms
from .models import NewsStory, SanitizedStory


def sanitize_stories_for_ad(market: str, stories: list[NewsStory]) -> list[SanitizedStory]:
    return [sanitize_story_for_ad(market, story) for story in stories]


def sanitize_story_for_ad(market: str, story: NewsStory) -> SanitizedStory:
    text = f"{story.title} {story.snippet}".lower()
    notes: list[str] = []

    if any(term in text for term in ("raising cane", "taco bell", "in-n-out")):
        frame = f"a {market} food-and-neighborhood story about a new restaurant opening near the waterfront"
        reference = f"{market}'s waterfront restaurant-opening story"
        notes.append("restaurant_brand_neutralized")
    elif any(term in text for term in ("lantern stories", "chinatown", "grant avenue")):
        frame = f"a {market} culture story about a Chinatown lantern display celebrating local history"
        reference = f"{market}'s Chinatown lantern-display story"
        notes.append("publisher_and_private_names_neutralized")
    elif any(term in text for term in ("usher", "gwen stefani", "dreamfest", "salesforce", "oracle")):
        frame = f"a {market} entertainment story about a large local concert gathering"
        reference = f"{market}'s large local concert-gathering story"
        notes.append("celebrity_and_brand_neutralized")
    elif any(term in text for term in ("ripley", "odditorium", "tourist attraction", "fisherman's wharf")):
        frame = f"a {market} story about a longtime waterfront tourist attraction closing"
        reference = f"{market}'s longtime waterfront attraction-closing story"
        notes.append("attraction_brand_neutralized")
    elif any(term in text for term in ("ftx", "bankman-fried", "ellison", "crypto", "fraud")):
        frame = f"a {market} tech-world story about a business-money dispute and an unexpected new hire"
        reference = f"{market}'s business-money dispute and unexpected-hire story"
        notes.append("legal_and_financial_names_neutralized")
    elif any(term in text for term in ("lawsuit", "foreclosure", "scandal", "detained", "ice")):
        topic = _generic_topic_from_title(story.title)
        frame = f"a {market} local news story about {topic}"
        reference = f"{market}'s local story about {topic}"
        notes.append("sensitive_terms_generalized")
    else:
        topic = _generic_topic_from_title(story.title)
        frame = f"a {market} local story about {topic}"
        reference = f"{market}'s local story about {topic}"
        notes.append("publisher_suffix_removed")

    frame, reference, fallback_note = _enforce_brand_safe_story_text(market, frame, reference)
    if fallback_note:
        notes.append(fallback_note)

    return SanitizedStory(
        original_title=story.title,
        original_url=story.url,
        sanitized_frame=frame,
        sanitized_reference=reference,
        sanitization_notes=notes,
        raw_story=story.to_dict(),
    )


def _generic_topic_from_title(title: str) -> str:
    topic = re.sub(r"\s+[|-]\s+.*$", "", title).strip()
    topic = re.sub(r"\s+[–—]\s+.*$", "", topic).strip()
    topic = re.sub(r"\s+", " ", topic)
    return topic or "a local community moment"


def _enforce_brand_safe_story_text(
    market: str,
    frame: str,
    reference: str,
) -> tuple[str, str, str | None]:
    blocked = find_famous_brand_terms(f"{frame} {reference}")
    if not blocked:
        return frame, reference, None
    return (
        f"a {market} local culture and community story",
        f"{market}'s local culture-and-community story",
        f"fallback_removed_famous_brand_terms:{','.join(sorted(blocked))}",
    )
