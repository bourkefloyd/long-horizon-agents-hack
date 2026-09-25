#!/usr/bin/env python3
"""Tinybird event memory for agents. Standard library only.

    from tb_events import emit, read
    emit("sf-coffee-launch", "campaign-gen", "variant_generated", {"hook": "..."}, run_id, variant_id="v1", cost_usd=0.02)
    rows = read("sf-coffee-launch", since="2026-09-25T00:00:00Z")

Env: TINYBIRD_API_KEY (required), TINYBIRD_HOST (default https://api.tinybird.co).

CLI:
    tb_events.py detect-host            # prints TINYBIRD_HOST=<host> for the token's region
    tb_events.py emit <campaign> <agent> <event_type> [json_payload]
    tb_events.py read <campaign> [--since ISO] [--agent NAME]
    tb_events.py summary <campaign>
    tb_events.py seed [campaign]        # six demo events for campaign-gen
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

DATASOURCE = "agent_events"
DEFAULT_HOST = "https://api.tinybird.co"
REGION_HOSTS = (
    "https://api.tinybird.co",
    "https://api.us-east.tinybird.co",
    "https://api.us-west-2.aws.tinybird.co",
    "https://api.us-east.aws.tinybird.co",
    "https://api.eu-central-1.aws.tinybird.co",
    "https://api.europe-west2.gcp.tinybird.co",
    "https://api.northamerica-northeast2.gcp.tinybird.co",
    "https://api.eu-west-1.aws.tinybird.co",
    "https://api.ap-east-1.aws.tinybird.co",
    "https://api.ap-southeast-2.aws.tinybird.co",
)


class TinybirdError(RuntimeError):
    pass


def _host() -> str:
    return (os.environ.get("TINYBIRD_HOST") or DEFAULT_HOST).rstrip("/")


def _token() -> str:
    token = os.environ.get("TINYBIRD_API_KEY", "").strip()
    if not token:
        raise TinybirdError("TINYBIRD_API_KEY is not set")
    return token


def _request(
    method: str,
    url: str,
    *,
    token: str,
    body: bytes | None = None,
    content_type: str | None = None,
    timeout: float = 20,
) -> tuple[int, str]:
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "lh-tb-events"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def _ts(value: datetime | str | None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    return value


def emit(
    campaign_id: str,
    agent: str,
    event_type: str,
    payload: Any = None,
    run_id: str | None = None,
    variant_id: str | None = None,
    cost_usd: float | None = None,
    *,
    ts: datetime | str | None = None,
    wait: bool = False,
) -> str:
    """Append one event via the Events API. Returns the run_id used."""
    run_id = run_id or os.environ.get("LH_RUN_ID") or uuid.uuid4().hex[:12]
    row = {
        "ts": _ts(ts),
        "campaign_id": campaign_id,
        "agent": agent,
        "run_id": run_id,
        "event_type": event_type,
        "variant_id": variant_id,
        "payload": json.dumps(payload if payload is not None else {}, separators=(",", ":")),
        "cost_usd": cost_usd,
    }
    query = urllib.parse.urlencode({"name": DATASOURCE, **({"wait": "true"} if wait else {})})
    status, text = _request(
        "POST",
        f"{_host()}/v0/events?{query}",
        token=_token(),
        body=(json.dumps(row) + "\n").encode(),
        content_type="application/x-ndjson",
    )
    if status not in (200, 202):
        raise TinybirdError(f"Events API returned {status}: {text[:300]}")
    return run_id


def _pipe(name: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    clean = {key: value for key, value in params.items() if value is not None}
    url = f"{_host()}/v0/pipes/{name}.json?{urllib.parse.urlencode(clean)}"
    status, text = _request("GET", url, token=_token())
    if status != 200:
        raise TinybirdError(f"Pipe {name} returned {status}: {text[:300]}")
    return json.loads(text).get("data", [])


def read(
    campaign_id: str,
    since: datetime | str | None = None,
    agent: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Recent events for a campaign (newest first) from the campaign_events pipe."""
    if isinstance(since, datetime):
        since = _ts(since)
    return _pipe(
        "campaign_events",
        {"campaign_id": campaign_id, "since": since, "agent": agent, "limit": limit},
    )


def summary(campaign_id: str) -> list[dict[str, Any]]:
    """Per-agent, per-event_type counts and cost from the campaign_summary pipe."""
    return _pipe("campaign_summary", {"campaign_id": campaign_id})


PROBES = (
    "/v0/sql?" + urllib.parse.urlencode({"q": "SELECT 1 FORMAT JSON"}),
    "/v0/datasources",
    "/v0/pipes",
    "/v0/tokens",
    "/v0/user/workspaces",
    "/v0/workspaces",
)


def _safe_error(text: str, token: str) -> str:
    """Short error message with the token (which Tinybird echoes back) removed."""
    try:
        message = str(json.loads(text).get("error", text))
    except (ValueError, AttributeError):
        message = text
    message = message.replace(token, "[token]")
    message = re.sub(r"(?i)invalid token\b.*", "invalid token [redacted]", message, flags=re.DOTALL)
    return message[:100]


def token_info(token: str | None = None) -> dict[str, Any]:
    """Non-secret facts about the token: length, shape, whitespace, and JWT claims minus ids."""
    raw = os.environ.get("TINYBIRD_API_KEY", "") if token is None else token
    info: dict[str, Any] = {
        "length": len(raw),
        "stripped_length": len(raw.strip()),
        "has_surrounding_whitespace": raw != raw.strip(),
        "prefix": raw.strip()[:2],
        "dots": raw.strip().count("."),
        "looks_like_tinybird_jwt": raw.strip().startswith("p.") and raw.strip().count(".") >= 2,
    }
    parts = raw.strip().split(".")
    if info["looks_like_tinybird_jwt"] and len(parts) >= 3:
        import base64

        try:
            payload = parts[2] if parts[1] == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" else parts[1]
            padded = payload + "=" * (-len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(padded))
            info["claim_keys"] = sorted(claims)
            for key in ("host", "region", "exp"):
                if key in claims:
                    info[f"claim_{key}"] = claims[key]
        except (ValueError, UnicodeDecodeError):
            info["claim_keys"] = "undecodable"
    return info


def detect_host(token: str | None = None, *, verbose: bool = False) -> str | None:
    """Return the first region host where any read probe accepts the token, or None.

    Tokens carry different scopes, so several endpoints are tried per host. Only
    status codes and short error bodies are printed; never the token.
    """
    token = token or _token()
    for host in REGION_HOSTS:
        for probe in PROBES:
            try:
                status, text = _request("GET", f"{host}{probe}", token=token, timeout=10)
            except (OSError, urllib.error.URLError) as exc:
                if verbose:
                    print(f"{host}{probe.split('?')[0]} -> {exc}", file=sys.stderr)
                continue
            if verbose:
                print(f"{host}{probe.split('?')[0]} -> {status} {_safe_error(text, token)}", file=sys.stderr)
            if status == 200:
                return host
    return None


def seed(campaign_id: str = "sf-coffee-launch") -> str:
    """Emit the six demo events a campaign-gen run would produce."""
    run_id = f"seed-{uuid.uuid4().hex[:8]}"
    start = datetime.now(timezone.utc) - timedelta(minutes=6)
    events: list[tuple[str, dict[str, Any], str | None, float | None]] = [
        ("run_started", {"market": "San Francisco", "issue": "Campaign: SF Coffee Launch"}, None, None),
        ("nimble_query", {"query": "san francisco coffee news this week", "stories": 5}, None, 0.004),
        ("variant_generated", {"hook": "Fog rolls in, espresso rolls out.", "format": "9x16 video"}, "v1", 0.03),
        ("variant_generated", {"hook": "Your Muni delay deserves a better latte.", "format": "9x16 video"}, "v2", 0.03),
        ("variant_generated", {"hook": "Ferry Building mornings, now with oat milk.", "format": "1x1 image"}, "v3", 0.01),
        ("run_finished", {"variants": 3, "staged_under": f"cdn/staging/{campaign_id}/"}, None, 0.074),
    ]
    for index, (event_type, payload, variant_id, cost) in enumerate(events):
        emit(
            campaign_id,
            "campaign-gen",
            event_type,
            payload,
            run_id,
            variant_id=variant_id,
            cost_usd=cost,
            ts=start + timedelta(minutes=index),
            wait=True,
        )
    return run_id


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    command, args = argv[0], argv[1:]
    if command == "token-info":
        print(json.dumps(token_info(), indent=2))
        return 0
    if command == "detect-host":
        if "--verbose" in args:
            print("token info: " + json.dumps(token_info()), file=sys.stderr)
        host = detect_host(verbose="--verbose" in args)
        if host is None:
            print("no Tinybird region accepted TINYBIRD_API_KEY", file=sys.stderr)
            return 1
        print(f"TINYBIRD_HOST={host}")
        return 0
    if command == "emit":
        if len(args) < 3:
            print("usage: emit <campaign> <agent> <event_type> [json_payload]", file=sys.stderr)
            return 2
        payload = json.loads(args[3]) if len(args) > 3 else {}
        print(emit(args[0], args[1], args[2], payload))
        return 0
    if command == "read":
        if not args:
            print("usage: read <campaign> [--since ISO] [--agent NAME]", file=sys.stderr)
            return 2
        options = dict(zip(args[1::2], args[2::2]))
        rows = read(args[0], since=options.get("--since"), agent=options.get("--agent"))
        print(json.dumps(rows, indent=2))
        return 0
    if command == "summary":
        if not args:
            print("usage: summary <campaign>", file=sys.stderr)
            return 2
        print(json.dumps(summary(args[0]), indent=2))
        return 0
    if command == "seed":
        print(seed(args[0] if args else "sf-coffee-launch"))
        return 0
    print(f"unknown command {command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(_cli(sys.argv[1:]))
    except TinybirdError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
