# Hack plan: Long Horizon Agents Hackathon

Friday 25 September 2026, San Francisco. Detail and sources: [docs/research/](docs/research/).

## Goal

An agent that creates video ad campaigns at X by Y (9:16 mobile vertical by default), runs them with A/B and A/A tests, collects the engagement signals, and uses the results to generate the next day's content, carrying one compact mutable campaign state day over day (what ran, what won, what was dropped, the A/A noise floor) and dropping raw stale events. Everything runs server-side; Liquid, Jev, or a plain bandit are the decision options.

**Assumptions.** Signals are impression, watch time, quartiles, skip, mute, CTA tap, install. Decisions happen between impressions and between days, not inside the creative. Content comes from the Black Forest Labs FLUX 3 video and image API ([research](docs/research/on-device-game-decisions.md#what-the-same-introduction-offers-besides-action)). A/A runs first so an A/B lift is not trusted below the noise floor. Nothing is measured yet.

## Team

- **Thomas:** marketing schema, Nimble process producing video scripts and hooks; later maybe campaign generation with Meta.
- **Bourke:** Long Horizon infrastructure in GitHub: web, agents, RSI (to define).
- **Aayush:** content generation: video variants and end cards.

## Milestones (Pacific)

| Target | Milestone |
| --- | --- |
| 11:00 | Kickoff. Research and this plan committed. |
| 12:45 | Schema v0 (Thomas). Placeholder clips (Aayush). Campaign state and daily loop skeleton (Bourke). |
| 13:30 | Lunch. First FLUX 3 video jobs already submitted. |
| 14:30 | Scripts and hooks (Thomas). Real variants and end cards (Aayush). A/A and A/B assignment, signal ingest, decision step, kept-vs-dropped panel (Bourke). |
| 15:30 | Feature freeze. Day-1 to day-2 loop runs end to end on simulated signals. Rehearse twice. |
| 16:30 | Submission. Tag `v0.1-submission`. |
| 17:00 | Demos and judging. |
| 19:00 | Awards. |

Not before 16:30: Meta upload, Nimble-to-Meta campaign generation, Jev without a key in hand, Tinybird, RSI definition, any claimed lift.

## Demo (60 seconds)

- Day 1 state on screen: two variants, an A/A pair, empty cohort rows.
- Simulated day of impressions streams in; panel folds raw ticks into per-variant counts and greys out what it drops.
- A/A shows the noise floor; the A/B lift is judged against it, not against zero.
- Agent decides: keep the winning hook, drop the loser, and writes tomorrow's generation brief; day-1 raw events are gone, the compact row remains.
- Day 2 variants appear from that brief. "That row is the whole memory of the campaign."

## Risks

- FLUX 3 jobs slow or credits short: placeholders are in the build by 12:45; generate short cuts first.
- No real traffic: signals are simulated and labelled as such; no lift is claimed.
- Scope creep toward uploads or new tools: anything not in the milestones waits until after 17:00.

## Changed from earlier drafts

The research docs were written for a playable ad with an on-device model. The product is now server-side video ad campaigns; read those docs for the tooling (Liquid, Jev, BFL) and ignore the playable and on-device framing.
