from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from .brand_guard import find_famous_brand_terms
from .http import post_json
from .models import NewsOutlet, NewsStory


SENSITIVE_TERMS = {
    "alcohol",
    "assault",
    "boozy",
    "crash",
    "crime",
    "dead",
    "death",
    "disaster",
    "diagnosed",
    "disease",
    "donate",
    "donation",
    "fire",
    "fundraising",
    "help us",
    "health",
    "homicide",
    "hospital",
    "hiv",
    "lawsuit",
    "medical",
    "murder",
    "newsletter",
    "politics",
    "shooting",
    "storm",
    "tragedy",
    "war",
}

OUTLET_DIRECTORY_DOMAINS = {
    "eddies-list.com",
    "library.usfca.edu",
    "news.feedspot.com",
    "w3newspapers.com",
    "en.wikipedia.org",
    "yelp.com",
}

OUTLET_DIRECTORY_TITLE_TERMS = {
    "directory",
    "library",
    "list",
    "mass media",
    "newspapers online",
    "top 10",
    "top 25",
    "websites",
}


class NimbleClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def search_local_news_outlets(self, market: str, limit: int = 8) -> list[NewsOutlet]:
        if not self.api_key:
            raise RuntimeError("NIMBLE_API_KEY is required unless --mock-news is used.")

        query = (
            f"local news outlets and news websites that primarily cover {market}. "
            "Return official local publishers, city news sites, public radio, newspapers, TV news, "
            "neighborhood news, and local digital outlets. Avoid national aggregators, tourism sites, "
            "wire services, and generic directories."
        )
        payload = post_json(
            f"{self.base_url}/v2/search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "query": query,
                "focus": "general",
                "max_results": limit,
                "search_depth": "standard",
            },
            timeout=45,
        )
        return normalize_nimble_outlets(payload)[:limit]

    def search_recent_local_news(
        self,
        market: str,
        limit: int = 10,
        outlets: list[NewsOutlet] | None = None,
    ) -> list[NewsStory]:
        if not self.api_key:
            raise RuntimeError("NIMBLE_API_KEY is required unless --mock-news is used.")

        outlet_clause = ""
        if outlets:
            source_bits = []
            for outlet in outlets[:8]:
                label = outlet.domain or outlet.name
                if label:
                    source_bits.append(f"site:{label}" if "." in label else label)
            if source_bits:
                outlet_clause = " Only return results from these local source domains: " + " OR ".join(source_bits) + "."

        query = (
            f"popular local news stories in {market} published in the past week in {datetime.now(UTC).year}. "
            "Prioritize widely shared community, culture, sports, food, events, weather-light, "
            "entertainment, and human-interest stories. Avoid tragedy, violent crime, politics, "
            "lawsuits, disasters, health stories, disease stories, and medical stories."
            f"{outlet_clause}"
        )
        payload = post_json(
            f"{self.base_url}/v2/search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "query": query,
                "focus": "general",
                "max_results": limit,
                "search_depth": "standard",
            },
            timeout=45,
        )
        stories = normalize_nimble_results(payload)
        if outlets:
            domains = {outlet.domain for outlet in outlets if outlet.domain}
            stories = [story for story in stories if normalize_domain(story.url) in domains]
        return stories


def normalize_nimble_outlets(payload: dict[str, Any]) -> list[NewsOutlet]:
    candidates = (
        payload.get("results")
        or payload.get("items")
        or payload.get("data")
        or payload.get("organic_results")
        or []
    )
    outlets: list[NewsOutlet] = []
    seen_domains: set[str] = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        name = str(item.get("title") or item.get("name") or "").strip()
        url = str(item.get("url") or item.get("link") or "").strip()
        snippet = str(item.get("snippet") or item.get("description") or item.get("summary") or "").strip()
        if not name or not url:
            continue
        domain = normalize_domain(url)
        if not domain or domain in seen_domains:
            continue
        if is_outlet_directory(name, domain):
            for outlet in extract_outlets_from_directory_item(item):
                if outlet.domain and outlet.domain not in seen_domains and not is_outlet_directory(outlet.name, outlet.domain):
                    seen_domains.add(outlet.domain)
                    outlets.append(outlet)
            continue
        seen_domains.add(domain)
        outlets.append(
            NewsOutlet(
                name=name,
                url=url,
                domain=domain,
                snippet=snippet,
                raw=item,
            )
        )
    return outlets


def extract_outlets_from_directory_item(item: dict[str, Any]) -> list[NewsOutlet]:
    text = "\n".join(
        str(item.get(key) or "")
        for key in ("content", "snippet", "description", "summary")
    )
    outlets: list[NewsOutlet] = []
    patterns = [
        re.compile(r"(?P<name>[A-Z][A-Za-z0-9 .&'»:-]{2,80})\s+\*\*Media Outlet\*\*\s+(?P<url>https?://[^\s)]+)"),
        re.compile(r"-\s+\*\*(?P<name>[^:*]{2,80}):?\*\*\s+(?P<url>https?://[^\s)]+)"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(text):
            name = cleanup_outlet_name(match.group("name"))
            url = match.group("url").rstrip(".,")
            domain = normalize_domain(url)
            if not name or not domain:
                continue
            outlets.append(
                NewsOutlet(
                    name=name,
                    url=url,
                    domain=domain,
                    snippet="Extracted from local outlet directory result.",
                    raw={"extracted_from": item.get("url") or item.get("link") or item.get("title")},
                )
            )
    return outlets


def cleanup_outlet_name(name: str) -> str:
    cleaned = " ".join(name.replace("»", "-").split())
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = cleaned.strip(" -:")
    return cleaned


def is_outlet_directory(name: str, domain: str) -> bool:
    lower_name = name.lower()
    if domain in OUTLET_DIRECTORY_DOMAINS:
        return True
    return any(term in lower_name for term in OUTLET_DIRECTORY_TITLE_TERMS)


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
        brand_safe = is_brand_safe(title, snippet, url)
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


def normalize_domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def is_brand_safe(title: str, snippet: str, url: str = "") -> bool:
    text = f"{title} {snippet}".lower()
    freshness_text = f"{title} {url}".lower()
    return (
        not any(term in text for term in SENSITIVE_TERMS)
        and not has_old_year(freshness_text)
    )


def has_old_year(text: str) -> bool:
    current_year = datetime.now(UTC).year
    for match in re.finditer(r"\b(20\d{2})\b", text):
        if int(match.group(1)) < current_year:
            return True
    return False


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
