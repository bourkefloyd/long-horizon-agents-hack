from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .http import post_json
from .models import NewsStory


SENSITIVE_TERMS = {
    "assault",
    "crash",
    "crime",
    "dead",
    "death",
    "disaster",
    "fire",
    "homicide",
    "lawsuit",
    "murder",
    "politics",
    "shooting",
    "storm",
    "tragedy",
    "war",
}


class NimbleClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def search_recent_local_news(self, market: str, limit: int = 10) -> list[NewsStory]:
        if not self.api_key:
            raise RuntimeError("NIMBLE_API_KEY is required unless --mock-news is used.")

        query = (
            f"viral local news stories in {market} from the past week. "
            "Prioritize widely shared community, culture, sports, food, events, weather-light, "
            "entertainment, and human-interest stories. Avoid tragedy, violent crime, politics, "
            "lawsuits, disasters, and health emergencies."
        )
        payload = post_json(
            f"{self.base_url}/v2/search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "focus": "news",
                "max_results": limit,
                "search_depth": "standard",
            },
            timeout=45,
        )
        return normalize_nimble_results(payload)


def normalize_nimble_results(payload: dict[str, Any]) -> list[NewsStory]:
    candidates = (
        payload.get("results")
        or payload.get("items")
        or payload.get("data")
        or payload.get("organic_results")
        or []
    )
    stories: list[NewsStory] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or item.get("name") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        snippet = str(item.get("snippet") or item.get("description") or item.get("summary") or "").strip()
        source = str(item.get("source") or item.get("publisher") or item.get("domain") or "").strip()
        published_at = str(item.get("published_at") or item.get("date") or item.get("published") or "").strip()
        if not title or not url:
            continue
        brand_safe = is_brand_safe(title, snippet)
        stories.append(
            NewsStory(
                title=title,
                url=url,
                source=source,
                published_at=published_at,
                snippet=snippet,
                relevance_score=score_relevance(title, snippet),
                virality_score=score_virality(title, snippet),
                brand_safe=brand_safe,
                raw=item,
            )
        )
    return stories


def is_brand_safe(title: str, snippet: str) -> bool:
    text = f"{title} {snippet}".lower()
    return not any(term in text for term in SENSITIVE_TERMS)


def score_relevance(title: str, snippet: str) -> float:
    text = f"{title} {snippet}".lower()
    score = 0.5
    for term in ("local", "bay area", "san francisco", "community", "neighborhood", "downtown"):
        if term in text:
            score += 0.1
    return min(score, 1.0)


def score_virality(title: str, snippet: str) -> float:
    text = f"{title} {snippet}".lower()
    score = 0.4
    for term in ("viral", "trending", "fans", "crowd", "record", "sold out", "popular", "tiktok"):
        if term in text:
            score += 0.12
    return min(score, 1.0)


def mock_stories(market: str) -> list[NewsStory]:
    today = datetime.now(UTC).date().isoformat()
    return [
        NewsStory(
            title=f"{market} food festival draws huge weekend crowds",
            url="https://example.com/local-food-festival",
            source="Mock Local News",
            published_at=today,
            snippet="A lively neighborhood food event became one of the area's most shared local stories.",
            relevance_score=0.9,
            virality_score=0.8,
        ),
        NewsStory(
            title=f"{market} baseball fans celebrate a dramatic late-game win",
            url="https://example.com/local-sports-win",
            source="Mock Sports Desk",
            published_at=today,
            snippet="Fans shared clips from a dramatic finish and packed local hangouts after the game.",
            relevance_score=0.85,
            virality_score=0.85,
        ),
        NewsStory(
            title=f"New public art installation becomes a selfie spot in {market}",
            url="https://example.com/public-art",
            source="Mock Culture",
            published_at=today,
            snippet="A colorful public art installation is trending as a cheerful photo backdrop.",
            relevance_score=0.82,
            virality_score=0.75,
        ),
        NewsStory(
            title=f"{market} students launch a playful citywide scavenger hunt",
            url="https://example.com/scavenger-hunt",
            source="Mock Community",
            published_at=today,
            snippet="The lighthearted challenge is spreading across campuses and local social feeds.",
            relevance_score=0.8,
            virality_score=0.78,
        ),
        NewsStory(
            title=f"Local bakery collab sells out in minutes across {market}",
            url="https://example.com/bakery-collab",
            source="Mock Food",
            published_at=today,
            snippet="A limited-time collaboration had people lining up and sharing photos online.",
            relevance_score=0.88,
            virality_score=0.82,
        ),
    ]
