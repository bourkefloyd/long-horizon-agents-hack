import json
from copy import deepcopy
from threading import Lock
from typing import Any, Protocol

from .models import Campaign, CampaignState, SignalEvent

CAMPAIGN_PREFIX = "campaigns/"


class CampaignStore(Protocol):
    """Persistence boundary; Firestore or Cloud SQL can replace this store later."""

    def append_event(self, event: SignalEvent) -> None: ...

    def drain_events(self, campaign_id: str) -> list[SignalEvent]: ...

    def get_state(self, campaign_id: str) -> CampaignState: ...

    def save_state(self, state: CampaignState) -> None: ...

    def list_campaigns(self) -> list[Campaign]: ...

    def get_campaign(self, campaign_id: str) -> Campaign | None: ...

    def save_campaign(self, campaign: Campaign) -> None: ...

    @property
    def backend(self) -> str: ...


class InMemoryCampaignStore:
    backend = "memory"

    def __init__(self) -> None:
        self._events: dict[str, list[SignalEvent]] = {}
        self._states: dict[str, CampaignState] = {}
        self._campaigns: dict[str, Campaign] = {}
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

    def list_campaigns(self) -> list[Campaign]:
        with self._lock:
            campaigns = [campaign.model_copy() for campaign in self._campaigns.values()]
        return sorted(campaigns, key=lambda campaign: campaign.created_at, reverse=True)

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        with self._lock:
            campaign = self._campaigns.get(campaign_id)
            return campaign.model_copy() if campaign else None

    def save_campaign(self, campaign: Campaign) -> None:
        with self._lock:
            self._campaigns[campaign.id] = campaign.model_copy()


class GcsCampaignStore(InMemoryCampaignStore):
    """Campaign records live as `campaigns/<id>.json` in a GCS bucket.

    Signals and folded state stay in memory: they are ephemeral demo traffic, while the
    campaign list must survive Cloud Run restarts and be visible to other tooling.
    """

    backend = "gcs"

    def __init__(self, bucket: Any) -> None:
        super().__init__()
        self._bucket = bucket

    @classmethod
    def from_bucket_name(cls, bucket_name: str) -> "GcsCampaignStore":
        from google.cloud import storage

        client = storage.Client()
        return cls(client.bucket(bucket_name))

    def list_campaigns(self) -> list[Campaign]:
        campaigns: list[Campaign] = []
        for blob in self._bucket.list_blobs(prefix=CAMPAIGN_PREFIX):
            if not blob.name.endswith(".json"):
                continue
            campaigns.append(Campaign.model_validate_json(blob.download_as_bytes()))
        return sorted(campaigns, key=lambda campaign: campaign.created_at, reverse=True)

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        blob = self._bucket.blob(_object_name(campaign_id))
        if not blob.exists():
            return None
        return Campaign.model_validate_json(blob.download_as_bytes())

    def save_campaign(self, campaign: Campaign) -> None:
        blob = self._bucket.blob(_object_name(campaign.id))
        blob.cache_control = "no-cache"
        blob.upload_from_string(
            json.dumps(campaign.model_dump(mode="json"), indent=2),
            content_type="application/json",
        )


def _object_name(campaign_id: str) -> str:
    return f"{CAMPAIGN_PREFIX}{campaign_id}.json"
