import json
from io import BytesIO

from fastapi.testclient import TestClient

from app import events
from app.main import app

client = TestClient(app)


def test_events_fail_soft_without_token(monkeypatch) -> None:
    monkeypatch.delenv("TINYBIRD_API_KEY", raising=False)

    response = client.get("/campaigns/sf-coffee-launch/events")

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "campaign_id": "sf-coffee-launch",
        "events": [],
    }


def test_events_proxy_pipe(monkeypatch) -> None:
    monkeypatch.setenv("TINYBIRD_API_KEY", "test-token")
    monkeypatch.setenv("TINYBIRD_HOST", "https://api.example.test/")
    seen: dict[str, str] = {}

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.close()

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        row = {"ts": "2026-09-25 22:00:00", "event_type": "run_started"}
        return FakeResponse(json.dumps({"data": [row], "rows": 1}).encode())

    monkeypatch.setattr(events.urllib.request, "urlopen", fake_urlopen)

    response = client.get("/campaigns/sf-coffee-launch/events?since=2026-09-25T00:00:00Z&agent=campaign-gen")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["events"][0]["event_type"] == "run_started"
    assert seen["auth"] == "Bearer test-token"
    assert seen["url"].startswith("https://api.example.test/v0/pipes/campaign_events.json?")
    assert "campaign_id=sf-coffee-launch" in seen["url"]
    assert "agent=campaign-gen" in seen["url"]
