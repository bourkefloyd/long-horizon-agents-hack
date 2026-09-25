from datetime import timedelta
from threading import Lock

from fastapi import FastAPI, Query, status

from .logic import fold_events, utc_now
from .models import CampaignState, DecisionResult, SignalEvent
from .store import CampaignStore, InMemoryCampaignStore

app = FastAPI(title="Campaign Loop Service", version="0.1.0")
store: CampaignStore = InMemoryCampaignStore()
decision_lock = Lock()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


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
