from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .http import download_file, get_json, post_json


class BFLClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url

    def submit_flux3_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("BFL_API_KEY is required when --generate is used.")

        return post_json(
            f"{self.base_url}/v1/flux-3-video",
            headers={
                "accept": "application/json",
                "x-key": self.api_key,
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout=60,
        )

    def poll(self, polling_url: str, timeout_seconds: int = 900, interval_seconds: float = 2.0) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            result = get_json(polling_url, timeout=30)
            status = result.get("status")
            if status in {"Ready", "Error", "Failed", "Request Moderated", "Content Moderated"}:
                return result
            time.sleep(interval_seconds)
        raise TimeoutError(f"Timed out waiting for BFL job at {polling_url}")

    def download_video_result(self, result: dict[str, Any], output_path: Path) -> str:
        video_url = find_media_url(result)
        if not video_url:
            raise RuntimeError("BFL result did not include a downloadable media URL.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        download_file(video_url, output_path)
        return str(output_path)


def find_media_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("video", "sample", "url", "media_url", "output", "file"):
            value = payload.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        for value in payload.values():
            found = find_media_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = find_media_url(item)
            if found:
                return found
    return None
