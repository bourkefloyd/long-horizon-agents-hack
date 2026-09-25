import json
import os
import re
import urllib.error
import urllib.request
from datetime import timedelta
from threading import Lock

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .derive import resolve_campaign
from .github import (
    GitHubIssueError,
    create_campaign_issue,
    github_repository,
    github_token,
)
from .logic import fold_events, utc_now
from .models import (
    Campaign,
    CampaignCreate,
    CampaignDetail,
    CampaignPublic,
    CampaignState,
    CampaignStatus,
    DecisionResult,
    QueueResult,
    SignalEvent,
)
from .store import CampaignStore, GcsCampaignStore, InMemoryCampaignStore


def build_store() -> CampaignStore:
    bucket_name = os.environ.get("ADS_BUCKET", "").strip()
    if bucket_name:
        return GcsCampaignStore.from_bucket_name(bucket_name)
    return InMemoryCampaignStore()


app = FastAPI(title="Campaign Loop Service", version="0.2.0")
store: CampaignStore = build_store()
decision_lock = Lock()
campaign_lock = Lock()

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


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:48] or "campaign"


def _unique_campaign_id(name: str) -> str:
    base = _slugify(name)
    candidate = base
    suffix = 2
    while store.get_campaign(candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _require_campaign(campaign_id: str) -> Campaign:
    campaign = store.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign '{campaign_id}' was not found.",
        )
    return campaign


@app.get("/health")
def health() -> dict[str, str]:
    return _health_payload()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return _health_payload()


@app.get("/health/store")
def store_health() -> dict[str, str | bool]:
    return {"backend": store.backend, "github_token": github_token() is not None}


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


@app.post("/campaigns", response_model=Campaign, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate) -> Campaign:
    with campaign_lock:
        campaign = Campaign(
            id=_unique_campaign_id(payload.name),
            created_at=utc_now(),
            **payload.model_dump(),
        )
        store.save_campaign(campaign)
    return campaign


@app.get("/campaigns", response_model=list[CampaignPublic])
def list_campaigns() -> list[CampaignPublic]:
    return [resolve_campaign(campaign) for campaign in store.list_campaigns()]


@app.get("/campaigns/{campaign_id}", response_model=CampaignDetail)
def get_campaign(campaign_id: str) -> CampaignDetail:
    campaign = resolve_campaign(_require_campaign(campaign_id))
    return CampaignDetail(**campaign.model_dump(), state=store.get_state(campaign_id))


@app.post("/campaigns/{campaign_id}/queue", response_model=QueueResult)
def queue_campaign(campaign_id: str) -> QueueResult:
    """Hand the campaign to the campaign-gen LH agent by opening its task issue."""
    with campaign_lock:
        campaign = _require_campaign(campaign_id)
        if campaign.issue_url:
            return QueueResult(
                campaign=campaign,
                message=f"Already queued; the campaign-gen agent is working from {campaign.issue_url}.",
            )

        token = github_token()
        if token is None:
            campaign.status = CampaignStatus.QUEUED
            store.save_campaign(campaign)
            return QueueResult(
                campaign=campaign,
                message=(
                    "Queued locally, but no GITHUB_TOKEN is configured, so the "
                    "campaign-gen issue was not opened. Mount the LH_GITHUB_TOKEN "
                    "secret and queue again."
                ),
            )

        try:
            issue_url = create_campaign_issue(
                campaign, token=token, repository=github_repository()
            )
        except GitHubIssueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not open the campaign-gen issue: {exc}",
            ) from exc

        campaign.status = CampaignStatus.QUEUED
        campaign.issue_url = issue_url
        store.save_campaign(campaign)
    return QueueResult(
        campaign=campaign,
        message=f"Queued. The campaign-gen agent will pick up {issue_url}.",
    )


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
