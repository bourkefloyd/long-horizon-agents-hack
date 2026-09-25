"""Derive campaign status on read from the CDN manifest and GitHub issue.

Draft stays draft. Any other stored status becomes live when the manifest has an
active ad for the campaign, review when the issue is labeled ``lh:review`` or has
a linked open pull request, and generating when the issue is labeled ``lh:running``.
Otherwise the stored status is returned. Manifest and GitHub failures fall back
to that stored status and never fail the request.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable

from .github import github_token
from .models import Campaign, CampaignPublic, CampaignStatus

DEFAULT_MANIFEST_URL = (
    "https://storage.googleapis.com/lh-ads-assets-205515555985/manifest.json"
)
FETCH_TIMEOUT_SECONDS = 3
CACHE_TTL_SECONDS = 60
REVIEW_LABEL = "lh:review"
RUNNING_LABEL = "lh:running"

_ISSUE_URL = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/"
    r"issues/(?P<number>[0-9]+)/?$"
)
_MISS = object()
Opener = Callable[..., Any]


class MemoryCache:
    """Process-local TTL cache. Values may be None; that is a stored failure."""

    def __init__(
        self,
        ttl: float = CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl = ttl
        self._clock = clock
        self._lock = Lock()
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        now = self._clock()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return _MISS
            expires, value = item
            if now >= expires:
                self._items.pop(key, None)
                return _MISS
            return value

    def set(self, key: str, value: Any) -> None:
        expires = self._clock() + self.ttl
        with self._lock:
            self._items[key] = (expires, value)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


cache = MemoryCache()


@dataclass(frozen=True)
class IssueSignals:
    labels: frozenset[str]
    has_open_linked_pr: bool


def manifest_url() -> str:
    configured = os.environ.get("ADS_MANIFEST_URL", "").strip()
    return configured or DEFAULT_MANIFEST_URL


def fetch_json(
    url: str,
    *,
    headers: dict[str, str],
    timeout: float = FETCH_TIMEOUT_SECONDS,
    opener: Opener | None = None,
) -> Any:
    request = urllib.request.Request(url, headers=headers)
    open_url = opener or urllib.request.urlopen
    with open_url(request, timeout=timeout) as response:
        return json.load(response)


def _github_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lh-campaign-service",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _manifest_headers() -> dict[str, str]:
    return {"Accept": "application/json", "User-Agent": "lh-campaign-service"}


def get_manifest_ads(opener: Opener | None = None) -> list[dict[str, Any]] | None:
    """Return manifest ads, or None when the manifest cannot be read."""
    url = manifest_url()
    cached = cache.get(f"manifest:{url}")
    if cached is not _MISS:
        return cached

    try:
        payload = fetch_json(url, headers=_manifest_headers(), opener=opener)
    except (OSError, urllib.error.URLError, ValueError):
        cache.set(f"manifest:{url}", None)
        return None

    ads = payload.get("ads") if isinstance(payload, dict) else None
    if not isinstance(ads, list):
        cache.set(f"manifest:{url}", None)
        return None
    cache.set(f"manifest:{url}", ads)
    return ads


def _parse_issue_url(issue_url: str) -> tuple[str, str, str] | None:
    match = _ISSUE_URL.match(issue_url.strip())
    if match is None:
        return None
    return match.group("owner"), match.group("repo"), match.group("number")


def _labels(issue: dict[str, Any]) -> frozenset[str]:
    raw = issue.get("labels") or []
    if not isinstance(raw, list):
        return frozenset()
    names: set[str] = set()
    for label in raw:
        if isinstance(label, str):
            names.add(label)
        elif isinstance(label, dict) and isinstance(label.get("name"), str):
            names.add(label["name"])
    return frozenset(names)


def _is_open_pull_request(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    state = node.get("state")
    if not isinstance(state, str) or state.lower() != "open":
        return False
    return bool(node.get("pull_request"))


def _has_open_linked_pr(timeline: Any) -> bool:
    if not isinstance(timeline, list):
        return False
    for event in timeline:
        if not isinstance(event, dict):
            continue
        if event.get("event") not in {"cross-referenced", "connected"}:
            continue
        source = event.get("source")
        if not isinstance(source, dict):
            continue
        if _is_open_pull_request(source.get("issue")) or _is_open_pull_request(source):
            return True
    return False


def get_issue_signals(
    issue_url: str,
    *,
    token: str | None,
    opener: Opener | None = None,
) -> IssueSignals | None:
    """Return issue labels and linked-PR state, or None when GitHub cannot be read."""
    key = f"issue:{'auth' if token else 'anon'}:{issue_url}"
    cached = cache.get(key)
    if cached is not _MISS:
        return cached

    parsed = _parse_issue_url(issue_url)
    if parsed is None:
        cache.set(key, None)
        return None

    owner, repo, number = parsed
    headers = _github_headers(token)
    api = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    try:
        issue = fetch_json(api, headers=headers, opener=opener)
    except (OSError, urllib.error.URLError, ValueError):
        cache.set(key, None)
        return None
    if not isinstance(issue, dict):
        cache.set(key, None)
        return None

    has_open_pr = False
    try:
        timeline = fetch_json(f"{api}/timeline?per_page=100", headers=headers, opener=opener)
        has_open_pr = _has_open_linked_pr(timeline)
    except (OSError, urllib.error.URLError, ValueError):
        has_open_pr = False

    signals = IssueSignals(labels=_labels(issue), has_open_linked_pr=has_open_pr)
    cache.set(key, signals)
    return signals


def _active_count(ads: list[dict[str, Any]] | None, campaign_id: str) -> int:
    if ads is None:
        return 0
    count = 0
    for ad in ads:
        if not isinstance(ad, dict) or ad.get("campaign_id") != campaign_id:
            continue
        targeting = ad.get("targeting")
        if isinstance(targeting, dict) and targeting.get("active") is True:
            count += 1
    return count


def present_campaign(
    campaign: Campaign,
    *,
    ads: list[dict[str, Any]] | None,
    signals: IssueSignals | None,
) -> CampaignPublic:
    count = _active_count(ads, campaign.id)
    status = campaign.status
    if campaign.status != CampaignStatus.DRAFT:
        if ads is not None and count >= 1:
            status = CampaignStatus.LIVE
        elif signals is not None and (
            REVIEW_LABEL in signals.labels or signals.has_open_linked_pr
        ):
            status = CampaignStatus.REVIEW
        elif signals is not None and RUNNING_LABEL in signals.labels:
            status = CampaignStatus.GENERATING
    data = campaign.model_dump()
    data["status"] = status
    data["ads_count"] = count
    data["feed_url"] = f"/feed?campaign={campaign.id}"
    return CampaignPublic(**data)


def resolve_campaign(
    campaign: Campaign,
    opener: Opener | None = None,
) -> CampaignPublic:
    ads = get_manifest_ads(opener=opener)
    signals = None
    live = campaign.status != CampaignStatus.DRAFT and _active_count(ads, campaign.id) >= 1
    if not live and campaign.status != CampaignStatus.DRAFT and campaign.issue_url:
        signals = get_issue_signals(campaign.issue_url, token=github_token(), opener=opener)
    return present_campaign(campaign, ads=ads, signals=signals)
