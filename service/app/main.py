import json
import os
import urllib.error
import urllib.request
from datetime import timedelta
from threading import Lock

from fastapi import FastAPI, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .logic import fold_events, utc_now
from .models import CampaignState, DecisionResult, SignalEvent
from .store import CampaignStore, InMemoryCampaignStore

app = FastAPI(title="Campaign Loop Service", version="0.1.0")
store: CampaignStore = InMemoryCampaignStore()
decision_lock = Lock()

# Demo scope: allow the browser frontend to call this in-memory API without credentials.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _health_payload() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return _health_payload()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return _health_payload()


@app.get("/liquid/health", response_model=None)
def liquid_health() -> JSONResponse:
    base_url = os.environ.get("LIQUID_TEXT_BASE_URL", "").rstrip("/")
    if not base_url:
        return JSONResponse(content={"status": "not configured", "models": []})

    try:
        with urllib.request.urlopen(f"{base_url}/v1/models", timeout=10) as response:
            payload = json.load(response)
        models = [
            model["id"]
            for model in payload.get("data", [])
            if isinstance(model, dict) and isinstance(model.get("id"), str)
        ]
        return JSONResponse(content={"status": "ok", "models": models})
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"status": "unavailable", "models": [], "error": str(exc)},
        )


@app.post("/signals", status_code=status.HTTP_202_ACCEPTED)
def ingest_signal(event: SignalEvent) -> dict[str, str]:
    store.append_event(event)
    return {"status": "accepted"}


@app.get("/campaigns/{campaign_id}/state", response_model=CampaignState)
def get_campaign_state(campaign_id: str) -> CampaignState:
    return store.get_state(campaign_id)


@app.post("/campaigns/{campaign_id}/decide", response_model=DecisionResult)
def decide_campaign(
    campaign_id: str,
    window_hours: int = Query(default=24, ge=1, le=168),
) -> DecisionResult:
    # Keep drain/fold/save together for this process. A durable store can implement
    # the equivalent boundary as a transaction.
    with decision_lock:
        events = store.drain_events(campaign_id)
        state = store.get_state(campaign_id)
        result = fold_events(
            state,
            events,
            now=utc_now(),
            window=timedelta(hours=window_hours),
        )
        store.save_state(result.state)
    return result
