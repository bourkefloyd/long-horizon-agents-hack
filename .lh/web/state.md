# state: web

## Goal

Ship the web surface for server-side video ad campaign automation: an operator sees generated video variants, running campaigns,
collected signals, A/B and A/A test verdicts, and the next day's content plan, with every keep/drop decision explained.
Mock adapters for ad platforms and video generation; real interfaces defined.

## Current plan

1. Wait for a human issue labeled `lh:web` that says whether to scaffold `web/` (Next.js, TypeScript, Tailwind) or work on an existing tree.
2. Define `web/lib/types.ts`: Variant, Campaign, Signal, TestVerdict (A/B and A/A), NextDayPlan.
3. Build the mock daily loop as pure functions, then the UI pages: campaigns, variants, tests, next day.
4. Replace the checks.sh stub with build and lint once `web/` exists.

## Done

- Long-horizon workflow, state contract, and this target's prompt exist.
- workflow_dispatch reached the agent step (concurrency smoke test).

## Open

- `web/` does not exist yet. No scaffold until an issue asks for it.
- Which signals are real inputs (impressions, view-through, CTR, conversions) versus derived; confirm with the marketing schema owner.

## Decisions

- Mock ad platform and video generation behind adapters; the loop must run with zero external calls.
- A/A results are always shown next to A/B so the operator can see the noise floor.

## Dropped

- Done line "first run has not happened"; superseded by successful agent run.
