"""Proxy the Tinybird `campaign_events` pipe so the web app never holds the token."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["events"])

DEFAULT_TINYBIRD_HOST = "https://api.tinybird.co"


def tinybird_token() -> str | None:
    return os.environ.get("TINYBIRD_API_KEY", "").strip() or None


def tinybird_host() -> str:
    return (os.environ.get("TINYBIRD_HOST") or DEFAULT_TINYBIRD_HOST).rstrip("/")


def _pipe(name: str, params: dict[str, str | int | None], token: str) -> dict:
    clean = {key: value for key, value in params.items() if value is not None}
    url = f"{tinybird_host()}/v0/pipes/{name}.json?{urllib.parse.urlencode(clean)}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": "lh-campaign-service"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


@router.get("/campaigns/{campaign_id}/events", response_model=None)
def campaign_events(
    campaign_id: str,
    since: str | None = Query(default=None, description="ISO-8601 lower bound on ts"),
    agent: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> JSONResponse:
    """Recent agent events for a campaign from Tinybird. Fails soft when unconfigured."""
    token = tinybird_token()
    if token is None:
        return JSONResponse(content={"configured": False, "campaign_id": campaign_id, "events": []})

    try:
        body = _pipe(
            "campaign_events",
            {"campaign_id": campaign_id, "since": since, "agent": agent, "limit": limit},
            token,
        )
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        return JSONResponse(
            status_code=502,
            content={
                "configured": True,
                "campaign_id": campaign_id,
                "events": [],
                "error": f"Tinybird returned {exc.code}: {detail}",
            },
        )
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return JSONResponse(
            status_code=502,
            content={"configured": True, "campaign_id": campaign_id, "events": [], "error": str(exc)},
        )

    return JSONResponse(
        content={
            "configured": True,
            "campaign_id": campaign_id,
            "events": body.get("data", []),
            "rows": body.get("rows", len(body.get("data", []))),
        }
    )
