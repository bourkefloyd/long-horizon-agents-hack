from copy import deepcopy
from threading import Lock
from typing import Protocol

from .models import CampaignState, SignalEvent


class CampaignStore(Protocol):
    """Persistence boundary; Firestore or Cloud SQL can replace this store later."""

    def append_event(self, event: SignalEvent) -> None: ...

    def drain_events(self, campaign_id: str) -> list[SignalEvent]: ...

    def get_state(self, campaign_id: str) -> CampaignState: ...

    def save_state(self, state: CampaignState) -> None: ...


class InMemoryCampaignStore:
    def __init__(self) -> None:
        self._events: dict[str, list[SignalEvent]] = {}
        self._states: dict[str, CampaignState] = {}
        self._lock = Lock()

    def append_event(self, event: SignalEvent) -> None:
        with self._lock:
            self._events.setdefault(event.campaign_id, []).append(event.model_copy())

    def drain_events(self, campaign_id: str) -> list[SignalEvent]:
        with self._lock:
            return self._events.pop(campaign_id, [])

    def get_state(self, campaign_id: str) -> CampaignState:
        with self._lock:
            state = self._states.get(campaign_id, CampaignState(campaign_id=campaign_id))
            return deepcopy(state)

    def save_state(self, state: CampaignState) -> None:
        with self._lock:
            self._states[state.campaign_id] = deepcopy(state)
