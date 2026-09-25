# state: web

## Goal

Maintain a responsive Next.js campaign console where an operator can inspect bounded variant counts, A/A noise, decisions, dropped events, and the next-day creative brief, with reliable API states and accessible controls.

## Current plan

1. Improve one operator-visible campaign behavior or state at a time while keeping the existing API proxy boundary.
2. Keep mobile and desktop layouts, loading/empty/error feedback, keyboard controls, and status announcements clear.
3. Run lint, production build, and `.lh/web/checks.sh` before publishing each focused change.

## Done

- `web/` contains the Next.js App Router console, typed campaign contract, shadcn/ui primitives, API proxy routes, and Cloud Run container.
- Deterministic web checks install from lockfile, lint, and build.

## Open

- Which signals are real inputs (impressions, view-through, CTR, conversions) versus derived; confirm with the marketing schema owner.

## Decisions

- Mock ad platform and video generation behind adapters; the loop must run with zero external calls.
- A/A results are always shown next to A/B so the operator can see the noise floor.
- Browser actions use same-origin Next.js route handlers, which proxy to the configured campaign service.

## Dropped

- The scaffold decision and stub-check plan are complete and no longer need tracking.
