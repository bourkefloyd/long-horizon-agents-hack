from datetime import UTC, datetime, timedelta

from .models import (
    CampaignState,
    Decision,
    DecisionResult,
    EventType,
    NextDayBrief,
    SignalEvent,
)

MAX_DECISIONS = 30


def _empty_counts() -> dict[EventType, int]:
    return {event_type: 0 for event_type in EventType}


def _score(counts: dict[EventType, int]) -> float:
    impressions = max(counts[EventType.IMPRESSION], 1)
    positive = (
        counts[EventType.COMPLETE]
        + 3 * counts[EventType.CTA_TAP]
        + 8 * counts[EventType.INSTALL]
    )
    return (positive - counts[EventType.SKIP]) / impressions


def fold_events(
    state: CampaignState,
    events: list[SignalEvent],
    *,
    now: datetime,
    window: timedelta,
) -> DecisionResult:
    """Fold fresh events into bounded campaign state and discard stale raw events."""
    cutoff = now - window
    fresh_events = [event for event in events if event.timestamp >= cutoff]
    state.dropped += len(events) - len(fresh_events)

    for event in fresh_events:
        if event.variant_id not in state.counts:
            state.variants.append(event.variant_id)
            state.counts[event.variant_id] = _empty_counts()
        state.counts[event.variant_id][event.event_type] += 1

    winner = (
        max(state.variants, key=lambda variant_id: _score(state.counts[variant_id]))
        if state.variants
        else None
    )
    if winner is None:
        rationale = f"No fresh signals were available; dropped {state.dropped} stale events total."
        instruction = "Collect initial traffic before generating the next creative batch."
    else:
        rationale = (
            f"Selected {winner} by weighted engagement per impression; "
            f"dropped {state.dropped} stale events total."
        )
        instruction = (
            f"Use Black Forest Labs to generate 9:16 variants from {winner}'s hook. "
            "Change one creative dimension and retain an A/A control pair."
        )

    state.decisions = (
        state.decisions
        + [Decision(decided_at=now, winner_variant_id=winner, rationale=rationale)]
    )[-MAX_DECISIONS:]

    return DecisionResult(
        state=state,
        next_day_brief=NextDayBrief(
            campaign_id=state.campaign_id,
            keep_variant_id=winner,
            instruction=instruction,
        ),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)
