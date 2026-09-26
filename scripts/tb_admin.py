#!/usr/bin/env python3
"""Fallback deployer for Classic Tinybird workspaces (no `tb deploy`).

Reads tinybird/datasources/*.datasource and tinybird/pipes/*.pipe and creates
the same resources through the REST API. Forward workspaces reject these calls;
the workflow tries `tb deploy` first and only runs this on failure.

Usage: TINYBIRD_API_KEY=... TINYBIRD_HOST=... tb_admin.py apply
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tinybird"


def _call(method: str, path: str, form: dict[str, str] | None = None) -> tuple[int, dict]:
    host = (os.environ.get("TINYBIRD_HOST") or "https://api.tinybird.co").rstrip("/")
    body = urllib.parse.urlencode(form).encode() if form else None
    request = urllib.request.Request(
        f"{host}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {os.environ['TINYBIRD_API_KEY']}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
            return response.status, (json.loads(text) if text else {})
    except urllib.error.HTTPError as exc:
        text = exc.read().decode(errors="replace")
        try:
            return exc.code, json.loads(text)
        except ValueError:
            return exc.code, {"error": text[:300]}


def _block(text: str, keyword: str) -> str:
    match = re.search(rf"^{keyword} >\n((?:[ \t]+.*\n?)+)", text, re.MULTILINE)
    if not match:
        raise SystemExit(f"missing {keyword} block")
    return "\n".join(line.strip() for line in match.group(1).splitlines()).strip()


def _setting(text: str, keyword: str) -> str | None:
    match = re.search(rf'^{keyword} "([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def apply_datasource(path: Path) -> None:
    text = path.read_text()
    name = path.stem
    status, _ = _call("GET", f"/v0/datasources/{name}")
    if status == 200:
        print(f"datasource {name}: exists")
        return
    form = {
        "name": name,
        "format": "ndjson",
        "schema": _block(text, "SCHEMA").replace("\n", " "),
        "engine": _setting(text, "ENGINE") or "MergeTree",
    }
    sorting_key = _setting(text, "ENGINE_SORTING_KEY")
    if sorting_key:
        form["engine_sorting_key"] = sorting_key
    status, body = _call("POST", "/v0/datasources", form)
    if status not in (200, 201):
        raise SystemExit(f"datasource {name}: {status} {body}")
    print(f"datasource {name}: created")


def apply_pipe(path: Path) -> None:
    text = path.read_text()
    name = path.stem
    sql = _block(text, "SQL")
    status, existing = _call("GET", f"/v0/pipes/{name}")
    if status == 200:
        _call("DELETE", f"/v0/pipes/{name}")
    status, body = _call("POST", "/v0/pipes", {"name": name, "sql": sql})
    if status not in (200, 201):
        raise SystemExit(f"pipe {name}: {status} {body}")
    node_id = body["nodes"][0]["id"]
    host = (os.environ.get("TINYBIRD_HOST") or "https://api.tinybird.co").rstrip("/")
    request = urllib.request.Request(
        f"{host}/v0/pipes/{name}/endpoint",
        data=node_id.encode(),
        method="PUT",
        headers={"Authorization": f"Bearer {os.environ['TINYBIRD_API_KEY']}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"pipe {name}: publish failed {exc.code} {exc.read().decode(errors='replace')[:300]}")
    print(f"pipe {name}: published")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "apply":
        print(__doc__)
        return 2
    for path in sorted((ROOT / "datasources").glob("*.datasource")):
        apply_datasource(path)
    for path in sorted((ROOT / "pipes").glob("*.pipe")):
        apply_pipe(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
