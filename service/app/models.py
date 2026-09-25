from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class EventType(StrEnum):
    IMPRESSION = "impression"
    Q25 = "q25"
    Q50 = "q50"
    Q75 = "q75"
    COMPLETE = "complete"
    SKIP = "skip"
    CTA_TAP = "cta_tap"
    INSTALL = "install"


class SignalEvent(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=128)
    variant_id: str = Field(min_length=1, max_length=128)
    event_type: EventType
    timestamp: AwareDatetime


class NoiseFloor(BaseModel):
    status: str = "not_estimated"
    absolute_rate_difference: float | None = None
    note: str = "A/A noise floor will be estimated after paired control traffic."


class Decision(BaseModel):
    decided_at: datetime
    winner_variant_id: str | None
    rationale: str


class CampaignState(BaseModel):
    campaign_id: str
    variants: list[str] = Field(default_factory=list)
    counts: dict[str, dict[EventType, int]] = Field(default_factory=dict)
    aa_noise_floor: NoiseFloor = Field(default_factory=NoiseFloor)
    decisions: list[Decision] = Field(default_factory=list)
    dropped: int = 0


class NextDayBrief(BaseModel):
    campaign_id: str
    keep_variant_id: str | None
    instruction: str


class DecisionResult(BaseModel):
    state: CampaignState
    next_day_brief: NextDayBrief
