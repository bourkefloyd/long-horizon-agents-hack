# state: web

## Goal

Maintain a responsive Next.js campaign console titled LH Marketing where an operator can inspect bounded variant counts,
A/A noise, decisions, dropped events, and the next-day creative brief, with reliable API states and accessible controls.

## Current plan

1. Improve one operator-visible campaign behavior or state at a time while keeping the existing API proxy boundary.
2. Keep mobile and desktop layouts, loading/empty/error feedback, keyboard controls, and status announcements clear.
3. Run lint, production build, and `.lh/web/checks.sh` before publishing each focused change.

## Done

- Document title is LH Marketing; the feed route uses the root title template so its tab reads Ad Demo Feed · LH Marketing.
- `web/` contains the Next.js App Router console, typed campaign contract, shadcn/ui primitives, API proxy routes, and Cloud Run container.
- Deterministic web checks install from lockfile, lint, and build.
- Long-horizon workflow, state contract, and this target's prompt exist; workflow_dispatch reached the agent step.

## Open

- Which signals are real inputs (impressions, view-through, CTR, conversions) versus derived; confirm with the marketing schema owner.

## Decisions

- Issue #39 sets the browser title to LH Marketing; a title template keeps child routes branded without a second product name.
- Mock ad platform and video generation behind adapters; the loop must run with zero external calls.
- A/A results are always shown next to A/B so the operator can see the noise floor.
- Browser actions use same-origin Next.js route handlers, which proxy to the configured campaign service.

## Dropped

- Nimble and campaign-gen run logs do not change the web console and are safe to forget here.
- The scaffold decision, stub-check plan, and "first run has not happened" note are complete.
