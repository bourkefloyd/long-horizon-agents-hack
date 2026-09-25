#!/usr/bin/env python3
"""Nimble web search -> fact rows for ad scripts (IDEAS.md hand-off).

Each result becomes one row with its source URL and an expiry, so stale facts drop out of scripts
instead of piling up. Key from NIMBLE_API_KEY.

    python3 content/ads/nimble.py "San Francisco viral local news this week" --focus news --days 5
    python3 content/ads/nimble.py "Sightglass Coffee San Francisco" --days 30

Writes/updates content/ads/facts.json and prints the rows it kept.
"""

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTS = HERE / "facts.json"
URL = "https://sdk.nimbleway.com/v2/search"


def search(query, focus="general", max_results=5, time_range=None):
    key = os.environ.get("NIMBLE_API_KEY")
    if not key:
        raise SystemExit("Set NIMBLE_API_KEY in the environment.")
    body = {"query": query, "max_results": max_results, "search_depth": "lite", "focus": focus}
    if time_range:
        body["time_range"] = time_range
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def keep(rows, days):
    """Merge new rows into facts.json, dropping expired ones. Returns (kept, dropped)."""
    now = dt.datetime.now(dt.timezone.utc)
    old = json.loads(FACTS.read_text()) if FACTS.exists() else []
    live = [r for r in old if dt.datetime.fromisoformat(r["expires_at"]) > now]
    dropped = [r for r in old if r not in live]
    seen = {r["source"] for r in live}
    for r in rows:
        if r["source"] not in seen:
            live.append(r)
    FACTS.write_text(json.dumps(live, indent=1, ensure_ascii=False))
    return live, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--focus", default="general")
    ap.add_argument("--days", type=int, default=7, help="how long these facts stay usable")
    ap.add_argument("--max", type=int, default=5)
    a = ap.parse_args()
    res = search(a.query, a.focus, a.max, "week" if a.focus == "news" else None)
    now = dt.datetime.now(dt.timezone.utc)
    rows = [{"kind": "nimble_search", "query": a.query, "fact": f"{x.get('title', '')}: {x.get('description', '')}".strip(": "),
             "source": x.get("url"), "retrieved_at": now.isoformat(timespec="seconds"),
             "expires_at": (now + dt.timedelta(days=a.days)).isoformat(timespec="seconds"), "via": "Nimble"}
            for x in res.get("results", []) if x.get("url")]
    live, dropped = keep(rows, a.days)
    json.dump({"request_id": res.get("request_id"), "new": rows, "dropped": len(dropped), "live": len(live)},
              sys.stdout, indent=1, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
