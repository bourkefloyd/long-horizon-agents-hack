"""Campaign-scoped event memory backed by Tinybird (scripts/tb_events.py).

The generator emits one small event per stage (run_started, nimble_query, story_ranked,
script_generated, bfl_submit, bfl_ready, error, run_finished) keyed by campaign_id, and
reads prior events at start so re-runs skip variants that already reached bfl_ready.
Memory is best-effort: it never raises into the pipeline. Disabled when TINYBIRD_API_KEY
is missing or the helper cannot be loaded.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .models import VideoAdConcept
from .staging import variant_id_for

AGENT_NAME = "campaign-gen"
DEFAULT_HELPER = Path(__file__).resolve().parents[3] / "scripts" / "tb_events.py"


class MemoryClient(Protocol):
    def emit(
        self,
        campaign_id: str,
        agent: str,
        event_type: str,
        payload: Any = None,
        run_id: str | None = None,
        variant_id: str | None = None,
        cost_usd: float | None = None,
    ) -> str: ...

    def read(self, campaign_id: str, since: Any = None, agent: str | None = None, limit: int = 200) -> list[dict[str, Any]]: ...


class PipelineHalt(RuntimeError):
    """Raised after an `error` event so the pipeline stops before further spend."""

    def __init__(self, step: str, error: BaseException) -> None:
        super().__init__(f"{step} failed: {type(error).__name__}: {error}")
        self.step = step
        self.original = error


def load_helper(path: Path | None = None) -> MemoryClient | None:
    helper_path = path or Path(os.getenv("TB_EVENTS_PATH", str(DEFAULT_HELPER)))
    if not helper_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("tb_events", helper_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module  # type: ignore[return-value]


class NullClient:
    """Used when TINYBIRD_API_KEY is absent: guards still work, nothing is sent."""

    def emit(self, *args: Any, **kwargs: Any) -> str:
        return ""

    def read(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return []


def create_memory(
    campaign_id: str,
    client: MemoryClient | None = None,
    run_id: str | None = None,
    continue_on_error: bool = False,
) -> AgentMemory:
    if client is None:
        client = (load_helper() if os.getenv("TINYBIRD_API_KEY") else None) or NullClient()
    return AgentMemory(
        campaign_id=campaign_id,
        client=client,
        run_id=run_id or uuid.uuid4().hex[:12],
        continue_on_error=continue_on_error,
    )


def env_cost(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass
class AgentMemory:
    campaign_id: str
    client: MemoryClient
    run_id: str
    agent: str = AGENT_NAME
    continue_on_error: bool = False
    errors: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float = 0.0
    _prior: list[dict[str, Any]] | None = field(default=None, init=False, repr=False)

    def emit(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        variant_id: str | None = None,
        cost_usd: float | None = None,
    ) -> None:
        if cost_usd:
            self.cost_usd += cost_usd
        try:
            self.client.emit(
                self.campaign_id,
                self.agent,
                event_type,
                payload or {},
                self.run_id,
                variant_id=variant_id,
                cost_usd=cost_usd,
            )
        except Exception as error:  # memory must never break generation
            print(f"agent memory: could not emit {event_type}: {error}", file=sys.stderr)

    def prior_events(self) -> list[dict[str, Any]]:
        if self._prior is None:
            try:
                self._prior = list(self.client.read(self.campaign_id, agent=self.agent, limit=1000))
            except Exception as error:
                print(f"agent memory: could not read prior events: {error}", file=sys.stderr)
                self._prior = []
        return self._prior

    def completed_variants(self) -> set[str]:
        return {
            str(event["variant_id"])
            for event in self.prior_events()
            if event.get("event_type") == "bfl_ready" and event.get("variant_id")
        }

    def already_done(self, concept: VideoAdConcept) -> bool:
        return variant_id_for(concept) in self.completed_variants()

    def error(self, step: str, error: BaseException, variant_id: str | None = None) -> None:
        record = {"step": step, "error_type": type(error).__name__, "message": str(error)[:500]}
        self.errors.append(record)
        self.emit("error", record, variant_id=variant_id)

    @property
    def failed(self) -> bool:
        return bool(self.errors)

    @property
    def enabled(self) -> bool:
        return not isinstance(self.client, NullClient)

    def finish(self, summary: dict[str, Any] | None = None) -> None:
        self.emit(
            "run_finished",
            {
                "status": "failed" if self.failed else "ok",
                "errors": self.errors,
                "total_cost_usd": round(self.cost_usd, 6),
                **(summary or {}),
            },
        )


def guard(
    memory: AgentMemory | None,
    step: str,
    error: BaseException,
    variant_id: str | None = None,
    allow_continue: bool = True,
) -> None:
    """Record `error` for `step`, then halt (no retry, no next variant).

    Returns instead of raising only when the run was started with --continue-on-error
    and the step is per-variant (`allow_continue`), so later variants may still run.
    """
    if isinstance(error, PipelineHalt) or memory is None:
        raise error
    memory.error(step, error, variant_id=variant_id)
    if allow_continue and memory.continue_on_error:
        return
    raise PipelineHalt(step, error) from error
