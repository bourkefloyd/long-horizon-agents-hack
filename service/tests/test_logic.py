from datetime import UTC, datetime, timedelta

from app.logic import fold_events
from app.models import CampaignState, EventType, SignalEvent


NOW = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)


def event(variant_id: str, event_type: EventType, age_hours: int) -> SignalEvent:
    return SignalEvent(
        campaign_id="campaign-1",
        variant_id=variant_id,
        event_type=event_type,
        timestamp=NOW - timedelta(hours=age_hours),
    )


def test_fold_accumulates_fresh_events_and_builds_brief() -> None:
    state = CampaignState(campaign_id="campaign-1")
    events = [
        event("variant-a", EventType.IMPRESSION, 2),
        event("variant-a", EventType.COMPLETE, 2),
        event("variant-b", EventType.IMPRESSION, 1),
        event("variant-b", EventType.SKIP, 1),
    ]

    result = fold_events(state, events, now=NOW, window=timedelta(hours=24))

    assert result.state.variants == ["variant-a", "variant-b"]
    assert result.state.counts["variant-a"][EventType.COMPLETE] == 1
    assert result.state.counts["variant-b"][EventType.SKIP] == 1
    assert result.state.dropped == 0
    assert result.next_day_brief.keep_variant_id == "variant-a"
    assert result.state.decisions[-1].winner_variant_id == "variant-a"


def test_fold_drops_stale_events_without_counting_them() -> None:
    state = CampaignState(campaign_id="campaign-1")
    events = [
        event("variant-a", EventType.IMPRESSION, 24),
        event("variant-old", EventType.CTA_TAP, 25),
    ]

    result = fold_events(state, events, now=NOW, window=timedelta(hours=24))

    assert result.state.variants == ["variant-a"]
    assert "variant-old" not in result.state.counts
    assert result.state.counts["variant-a"][EventType.IMPRESSION] == 1
    assert result.state.dropped == 1


def test_fold_preserves_compact_counts_across_days() -> None:
    state = CampaignState(campaign_id="campaign-1")
    first = fold_events(
        state,
        [event("variant-a", EventType.IMPRESSION, 2)],
        now=NOW,
        window=timedelta(hours=24),
    )

    second = fold_events(
        first.state,
        [event("variant-a", EventType.CTA_TAP, 1)],
        now=NOW,
        window=timedelta(hours=24),
    )

    assert second.state.counts["variant-a"][EventType.IMPRESSION] == 1
    assert second.state.counts["variant-a"][EventType.CTA_TAP] == 1
    assert len(second.state.decisions) == 2
