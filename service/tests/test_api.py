from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_alias_returns_ok() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liquid_health_reports_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("LIQUID_TEXT_BASE_URL", raising=False)

    response = client.get("/liquid/health")

    assert response.status_code == 200
    assert response.json() == {"status": "not configured", "models": []}
