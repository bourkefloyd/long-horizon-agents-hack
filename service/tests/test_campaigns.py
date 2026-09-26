import urllib.error
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import derive, main
from app.github import issue_body
from app.models import Campaign
from app.store import GcsCampaignStore, InMemoryCampaignStore

SF_COFFEE = {
    "name": "SF Coffee Launch",
    "brief": "Casual mobile game cross-promo for SF coffee lovers",
    "vertical": "Mobile games",
    "geo": "San Francisco",
    "audience": "Coffee lovers, 21-40",
}


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setattr(main, "store", InMemoryCampaignStore())
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    def offline(*args: object, **kwargs: object) -> object:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(derive.urllib.request, "urlopen", offline)
    return TestClient(main.app)


def test_create_list_and_get_campaign(client: TestClient) -> None:
    created = client.post("/campaigns", json=SF_COFFEE)
    assert created.status_code == 201
    campaign = created.json()
    assert campaign["id"] == "sf-coffee-launch"
    assert campaign["status"] == "draft"
    assert campaign["dims"] == "9:16"
    assert campaign["issue_url"] is None

    listed = client.get("/campaigns")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == ["sf-coffee-launch"]

    detail = client.get("/campaigns/sf-coffee-launch")
    assert detail.status_code == 200
    body = detail.json()
    assert body["name"] == "SF Coffee Launch"
    assert body["state"]["campaign_id"] == "sf-coffee-launch"
    assert body["state"]["variants"] == []


def test_duplicate_names_get_unique_ids(client: TestClient) -> None:
    first = client.post("/campaigns", json=SF_COFFEE).json()
    second = client.post("/campaigns", json=SF_COFFEE).json()
    assert first["id"] == "sf-coffee-launch"
    assert second["id"] == "sf-coffee-launch-2"


def test_missing_campaign_is_404(client: TestClient) -> None:
    assert client.get("/campaigns/nope").status_code == 404
    assert client.post("/campaigns/nope/queue").status_code == 404


def test_queue_without_token_marks_queued_without_issue(client: TestClient) -> None:
    client.post("/campaigns", json=SF_COFFEE)

    queued = client.post("/campaigns/sf-coffee-launch/queue")

    assert queued.status_code == 200
    body = queued.json()
    assert body["campaign"]["status"] == "queued"
    assert body["campaign"]["issue_url"] is None
    assert "GITHUB_TOKEN" in body["message"]


def test_queue_with_token_opens_issue_once(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    calls: list[tuple[str, str]] = []

    def fake_create(campaign: Campaign, *, token: str, repository: str) -> str:
        calls.append((token, repository))
        return f"https://github.com/{repository}/issues/99"

    monkeypatch.setattr(main, "create_campaign_issue", fake_create)
    client.post("/campaigns", json=SF_COFFEE)

    queued = client.post("/campaigns/sf-coffee-launch/queue").json()
    again = client.post("/campaigns/sf-coffee-launch/queue").json()

    assert calls == [("test-token", "bourkefloyd/long-horizon-agents-hack")]
    assert queued["campaign"]["status"] == "queued"
    assert queued["campaign"]["issue_url"].endswith("/issues/99")
    assert again["message"].startswith("Already queued")


def test_issue_body_carries_campaign_json_and_staging_path() -> None:
    campaign = Campaign(
        id="sf-coffee-launch",
        created_at=datetime(2026, 9, 25, 21, 0, tzinfo=UTC),
        **SF_COFFEE,
    )
    body = issue_body(campaign)
    assert "```json" in body
    assert '"id": "sf-coffee-launch"' in body
    assert "cdn/staging/sf-coffee-launch/" in body


class FakeBlob:
    def __init__(self, bucket: "FakeBucket", name: str) -> None:
        self.bucket = bucket
        self.name = name
        self.cache_control: str | None = None

    def exists(self) -> bool:
        return self.name in self.bucket.objects

    def download_as_bytes(self) -> bytes:
        return self.bucket.objects[self.name]

    def upload_from_string(self, data: str, content_type: str) -> None:
        assert content_type == "application/json"
        self.bucket.objects[self.name] = data.encode()


class FakeBucket:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self, name)

    def list_blobs(self, prefix: str) -> list[FakeBlob]:
        return [FakeBlob(self, name) for name in self.objects if name.startswith(prefix)]


def test_gcs_store_round_trips_campaign_json() -> None:
    bucket = FakeBucket()
    store = GcsCampaignStore(bucket)
    campaign = Campaign(
        id="sf-coffee-launch",
        created_at=datetime(2026, 9, 25, 21, 0, tzinfo=UTC),
        **SF_COFFEE,
    )

    assert store.get_campaign("sf-coffee-launch") is None
    store.save_campaign(campaign)

    assert "campaigns/sf-coffee-launch.json" in bucket.objects
    assert store.get_campaign("sf-coffee-launch") == campaign
    assert store.list_campaigns() == [campaign]
    assert store.backend == "gcs"
