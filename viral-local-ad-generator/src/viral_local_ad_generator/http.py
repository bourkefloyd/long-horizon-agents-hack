from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    return _open_json(request, timeout)


def get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    return _open_json(request, timeout)


def download_file(url: str, path: Path, timeout: int = 120) -> None:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            path.write_bytes(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {request.full_url}: {detail}") from error


def _open_json(request: urllib.request.Request, timeout: int) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {request.full_url}: {detail}") from error
    return json.loads(body)
