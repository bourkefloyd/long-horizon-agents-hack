from __future__ import annotations

import json
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class PipelineLogger:
    output_dir: Path
    command: str
    tinybird_token: str = ""
    tinybird_base_url: str = "https://api.europe-west2.gcp.tinybird.co"
    tinybird_datasource: str = "ad_gen_events"
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    context: dict[str, Any] = field(default_factory=dict)
    current_stage: str = field(default="cli", init=False)

    def __post_init__(self) -> None:
        self.local_path = self.output_dir / "logs" / "ad_gen_events.ndjson"
        self.local_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def tinybird_enabled(self) -> bool:
        return bool(self.tinybird_token and self.tinybird_datasource and self.tinybird_base_url)

    def emit(
        self,
        stage: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        status: str = "ok",
    ) -> None:
        if stage not in {"cli", "run_status", "preflight.previous_run"}:
            self.current_stage = stage
        event = self.make_event(stage, event_type, payload or {}, status)
        line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with self.local_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
        if self.tinybird_enabled:
            self.send_to_tinybird(line)

    def emit_run_started(self) -> None:
        self.emit(
            "run_status",
            "started",
            {
                "run_id": self.run_id,
                "output_dir": str(self.output_dir),
                "command": self.command,
            },
        )

    def emit_run_completed(self, result: dict[str, Any] | None = None) -> None:
        self.emit(
            "run_status",
            "completed",
            {
                "run_id": self.run_id,
                "output_dir": str(self.output_dir),
                "command": self.command,
                "result": result or {},
            },
        )

    def emit_run_failed(self, error: BaseException, stage: str | None = None) -> None:
        self.emit(
            "run_status",
            "failed",
            {
                "run_id": self.run_id,
                "output_dir": str(self.output_dir),
                "command": self.command,
                "failed_stage": stage or self.current_stage,
                "error_type": type(error).__name__,
                "error": str(error),
                "suggested_fix": suggest_fix_for_error(error),
                "traceback": traceback.format_exc(),
            },
            status="error",
        )

    def make_event(
        self,
        stage: str,
        event_type: str,
        payload: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        safe_payload = redact_secrets(payload)
        return {
            "event_id": uuid.uuid4().hex,
            "timestamp": now,
            "run_id": self.run_id,
            "command": self.command,
            "stage": stage,
            "event_type": event_type,
            "status": status,
            "payload_json": json.dumps(safe_payload, ensure_ascii=False, default=str),
            "context_json": json.dumps(redact_secrets(self.context), ensure_ascii=False, default=str),
        }

    def send_to_tinybird(self, ndjson_line: str) -> None:
        query = urllib.parse.urlencode({"name": self.tinybird_datasource})
        request = urllib.request.Request(
            f"{self.tinybird_base_url}/v0/events?{query}",
            data=ndjson_line.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.tinybird_token}",
                "Content-Type": "application/x-ndjson",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            self._write_tinybird_error(error.code, detail)
        except urllib.error.URLError as error:
            self._write_tinybird_error("url_error", str(error))
        except (TimeoutError, OSError) as error:
            self._write_tinybird_error("network_error", str(error))
        finally:
            elapsed_ms = round((time.time() - started) * 1000)
            metrics_path = self.output_dir / "logs" / "tinybird_metrics.ndjson"
            with metrics_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"elapsed_ms": elapsed_ms, "datasource": self.tinybird_datasource}) + "\n")

    def _write_tinybird_error(self, code: int | str, detail: str) -> None:
        path = self.output_dir / "logs" / "tinybird_errors.ndjson"
        error_event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "code": code,
            "detail": detail,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(error_event, ensure_ascii=False) + "\n")


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lower = str(key).lower()
            if lower == "api_key_presence":
                redacted[key] = redact_secrets(item)
            elif any(secret_word in lower for secret_word in ("api_key", "authorization", "token", "x-key", "secret")):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def suggest_fix_for_error(error: BaseException | str) -> str:
    text = str(error).lower()
    error_type = type(error).__name__ if isinstance(error, BaseException) else ""
    if "nimble_api_key" in text or "nimble" in text and "required" in text:
        return "Check that NIMBLE_API_KEY is present in .env, or rerun with --mock-news for a local test."
    if "bfl_api_key" in text or "bfl" in text and "required" in text:
        return "Check that BFL_API_KEY is present in .env before using --generate."
    if "tinybird" in text or "data source" in text or "datasource" in text:
        return "Check TINYBIRD_TOKEN, TINYBIRD_BASE_URL, and TINYBIRD_DATASOURCE, then confirm the datasource is deployed."
    if "request moderated" in text or "content moderated" in text:
        return "Review the generated video prompt for brand names, public figures, sensitive topics, or publisher references, then rerun after sanitizing."
    if "generated creative references famous brands" in text:
        return "Inspect concepts.json for blocked brand terms and adjust the sanitizer or campaign text before submitting to BFL."
    if "timed out" in text or error_type == "TimeoutError":
        return "Poll the saved BFL polling_url again, or rerun generate-video with a longer timeout."
    if "http 401" in text or "http 403" in text:
        return "Check the relevant API token permissions and region/base URL."
    if "http 404" in text:
        return "Check the configured endpoint, datasource name, or saved run path."
    if "no such file" in text or "not found" in text:
        return "Check that the input file paths exist and that you are running from the project directory."
    return "Open the run log, find the run_status.failed event, and inspect the failed_stage, error_type, and traceback fields."
