import json
import urllib.error
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import derive, main
from app.derive import MemoryCache
from app.models import Campaign, CampaignStatus
from app.store import InMemoryCampaignStore

MANIFEST = "https://storage.googleapis.com/lh-ads-assets-205515555985/manifest.json"
ISSUE = "https://github.com/bourkefloyd/long-horizon-agents-hack/issues/57"
ISSUE_API = "https://api.github.com/repos/bourkefloyd/long-horizon-agents-hack/issues/57"
TIMELINE_API = f"{ISSUE_API}/timeline?per_page=100"
CREATED = datetime(2026, 9, 25, 21, 0, tzinfo=UTC)


class _Response:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode()

    def read(self, *_args: object) -> bytes:
        return self._body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _ad(campaign_id: str, *, active: bool, ad_id: str) -> dict[str, object]:
    return {
        "id": ad_id,
        "campaign_id": campaign_id,
        "targeting": {"active": active, "weight": 1},
    }


def _manifest(*ads: dict[str, object]) -> dict[str, object]:
    return {"version": 1, "updated_at": "2026-09-25T00:00:00Z", "ads": list(ads)}


def _coffee_ads() -> list[dict[str, object]]:
    return [
        _ad("sf-coffee-launch", active=True, ad_id="sf-coffee-launch-01"),
        _ad("sf-coffee-launch", active=True, ad_id="sf-coffee-launch-02"),
        _ad("sf-coffee-launch", active=True, ad_id="sf-coffee-launch-03"),
    ]


def _issue(*labels: str) -> dict[str, object]:
    return {"labels": [{"name": label} for label in labels]}


def _pull(state: str) -> dict[str, object]:
    return {
        "event": "cross-referenced",
        "source": {
            "type": "issue",
            "issue": {
                "state": state,
                "pull_request": {"url": "https://api.github.com/repos/o/r/pulls/9"},
            },
        },
    }


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "store", InMemoryCampaignStore())
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("ADS_MANIFEST_URL", raising=False)
    return TestClient(main.app)


def _seed(status: CampaignStatus, **overrides: object) -> None:
    payload = {
        "id": "sf-coffee-launch",
        "name": "SF Coffee Launch",
        "brief": "Casual mobile game cross-promo for SF coffee lovers",
        "vertical": "Mobile games",
        "geo": "San Francisco",
        "audience": "Coffee lovers, 21-40",
        "status": status,
        "created_at": CREATED,
        "issue_url": ISSUE,
    }
    payload.update(overrides)
    main.store.save_campaign(Campaign(**payload))


def _routes(monkeypatch: pytest.MonkeyPatch, routes: dict[str, object]) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def urlopen(request: object, timeout: float | None = None) -> _Response:
        url = request.full_url  # type: ignore[attr-defined]
        authorization = request.get_header("Authorization")  # type: ignore[attr-defined]
        calls.append({"url": url, "timeout": timeout, "authorization": authorization})
        if url not in routes:
            raise AssertionError(f"unexpected fetch {url}")
        spec = routes[url]
        if isinstance(spec, BaseException):
            raise spec
        return _Response(spec)

    monkeypatch.setattr(derive.urllib.request, "urlopen", urlopen)
    return calls


def _read(client: TestClient) -> tuple[dict[str, object], dict[str, object]]:
    listed = client.get("/campaigns")
    detail = client.get("/campaigns/sf-coffee-launch")
    assert listed.status_code == 200
    assert detail.status_code == 200
    items = listed.json()
    body = detail.json()
    assert [item["id"] for item in items] == ["sf-coffee-launch"]
    assert body["state"]["campaign_id"] == "sf-coffee-launch"
    for payload in (items[0], body):
        assert payload["feed_url"] == "/feed?campaign=sf-coffee-launch"
    assert items[0]["status"] == body["status"]
    assert items[0]["ads_count"] == body["ads_count"]
    return items[0], body


def test_draft_stays_draft_even_when_manifest_has_active_ads(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _routes(monkeypatch, {MANIFEST: _manifest(*_coffee_ads())})
    _seed(CampaignStatus.DRAFT)

    listed, _detail = _read(client)

    assert listed["status"] == "draft"
    assert listed["ads_count"] == 3
    assert [call["url"] for call in calls] == [MANIFEST]
    assert calls[0]["timeout"] == 3


def test_active_manifest_ads_derive_live_without_writing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(
                *_coffee_ads(),
                _ad("other", active=True, ad_id="other-1"),
                _ad("sf-coffee-launch", active=False, ad_id="paused"),
            )
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "live"
    assert listed["ads_count"] == 3
    assert [call["url"] for call in calls] == [MANIFEST]
    assert main.store.get_campaign("sf-coffee-launch").status == CampaignStatus.QUEUED


def test_review_label_derives_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(_ad("sf-coffee-launch", active=False, ad_id="paused")),
            ISSUE_API: _issue("lh:review", "lh:running"),
            TIMELINE_API: [],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "review"
    assert listed["ads_count"] == 0


def test_linked_open_pull_request_derives_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(),
            ISSUE_API: _issue("lh:campaign-gen"),
            TIMELINE_API: [
                {
                    "event": "cross-referenced",
                    "source": {"type": "issue", "issue": {"state": "open"}},
                },
                _pull("open"),
            ],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "review"


def test_closed_pull_request_does_not_derive_review(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(),
            ISSUE_API: _issue(),
            TIMELINE_API: [_pull("closed")],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "queued"


def test_running_label_derives_generating(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(_ad("demo", active=True, ad_id="demo-1")),
            ISSUE_API: _issue("lh:running"),
            TIMELINE_API: [],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "generating"
    assert listed["ads_count"] == 0


def test_missing_signals_keep_stored_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {MANIFEST: _manifest(), ISSUE_API: _issue(), TIMELINE_API: []},
    )
    _seed(CampaignStatus.QUEUED, issue_url=None)

    listed, _detail = _read(client)

    assert listed["status"] == "queued"
    assert listed["ads_count"] == 0


def test_manifest_failure_falls_back_and_still_checks_github(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: urllib.error.URLError("manifest down"),
            ISSUE_API: _issue("lh:running"),
            TIMELINE_API: [],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "generating"
    assert listed["ads_count"] == 0


def test_github_failure_falls_back_to_stored_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(),
            ISSUE_API: urllib.error.URLError("github down"),
        },
    )
    _seed(CampaignStatus.GENERATING)

    listed, _detail = _read(client)

    assert listed["status"] == "generating"
    assert listed["ads_count"] == 0


def test_broken_manifest_json_falls_back_to_stored_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(monkeypatch, {MANIFEST: {"version": 1}})
    _seed(CampaignStatus.QUEUED, issue_url=None)

    listed, _detail = _read(client)

    assert listed["status"] == "queued"
    assert listed["ads_count"] == 0


def test_github_token_is_sent_when_present_and_omitted_otherwise(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    calls = _routes(
        monkeypatch,
        {MANIFEST: _manifest(), ISSUE_API: _issue(), TIMELINE_API: []},
    )
    _seed(CampaignStatus.QUEUED)

    client.get("/campaigns/sf-coffee-launch")
    authed = [call for call in calls if str(call["url"]).startswith("https://api.github.com/")]
    assert authed
    assert {call["authorization"] for call in authed} == {"Bearer test-token"}

    derive.cache.clear()
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    calls.clear()
    client.get("/campaigns/sf-coffee-launch")
    anon = [call for call in calls if str(call["url"]).startswith("https://api.github.com/")]
    assert anon
    assert {call["authorization"] for call in anon} == {None}


def test_manifest_url_and_fetches_are_cached_for_sixty_seconds(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    custom = "https://cdn.example/manifest.json"
    monkeypatch.setenv("ADS_MANIFEST_URL", custom)
    clock = {"now": 1000.0}
    monkeypatch.setattr(derive, "cache", MemoryCache(ttl=60, clock=lambda: clock["now"]))
    calls = _routes(
        monkeypatch,
        {
            custom: _manifest(*_coffee_ads()),
            ISSUE_API: _issue("lh:running"),
            TIMELINE_API: [],
        },
    )
    _seed(CampaignStatus.QUEUED, id="sf-coffee-launch")
    main.store.save_campaign(
        Campaign(
            id="second",
            name="Second",
            brief="Another brief",
            vertical="Mobile games",
            geo="San Francisco",
            audience="Coffee lovers, 21-40",
            status=CampaignStatus.QUEUED,
            created_at=CREATED,
            issue_url=ISSUE,
        )
    )

    first = client.get("/campaigns")
    assert first.status_code == 200
    by_id = {item["id"]: item["status"] for item in first.json()}
    assert by_id == {"sf-coffee-launch": "live", "second": "generating"}
    manifest_calls = [call for call in calls if call["url"] == custom]
    github_calls = [call for call in calls if call["url"] != custom]
    assert len(manifest_calls) == 1
    assert len(github_calls) == 2

    clock["now"] = 1059.0
    client.get("/campaigns")
    assert len([call for call in calls if call["url"] == custom]) == 1
    assert len([call for call in calls if call["url"] != custom]) == 2

    clock["now"] = 1060.0
    client.get("/campaigns")
    assert len([call for call in calls if call["url"] == custom]) == 2
    assert {call["timeout"] for call in calls} == {3}


def test_connected_open_pull_request_counts_as_linked(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _routes(
        monkeypatch,
        {
            MANIFEST: _manifest(),
            ISSUE_API: _issue(),
            TIMELINE_API: [
                {
                    "event": "connected",
                    "source": {
                        "issue": {
                            "state": "open",
                            "pull_request": {"url": "https://api.github.com/repos/o/r/pulls/3"},
                        }
                    },
                }
            ],
        },
    )
    _seed(CampaignStatus.QUEUED)

    listed, _detail = _read(client)

    assert listed["status"] == "review"
