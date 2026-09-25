# state: web

## Goal

Maintain a responsive Next.js campaign console where an operator can inspect bounded variant counts, A/A noise, decisions,
dropped events, and the next-day creative brief, with reliable API states and accessible controls.

## Current plan

1. Keep the star site icon served by the App Router metadata file for the console and the ad feed.
2. Improve one operator-visible campaign behavior or state at a time while keeping the existing API proxy boundary.
3. Keep mobile and desktop layouts, loading/empty/error feedback, keyboard controls, and status announcements clear.
4. Run lint, production build, and `.lh/web/checks.sh` before publishing each focused change.

## Done

- `web/` contains the Next.js App Router console, typed campaign contract, shadcn/ui primitives, API proxy routes, and Cloud Run container.
- Deterministic web checks install from lockfile, lint, and build.
- Long-horizon workflow, state contract, and this target's prompt exist.
- A star mark at `web/app/icon.svg` and `web/app/favicon.ico` is the favicon for every route under the shared root layout.

## Open

- Which signals are real inputs (impressions, view-through, CTR, conversions) versus derived; confirm with the marketing schema owner.

## Decisions

- Mock ad platform and video generation behind adapters; the loop must run with zero external calls.
- A/A results are always shown next to A/B so the operator can see the noise floor.
- Browser actions use same-origin Next.js route handlers, which proxy to the configured campaign service.
- Issue #44 asked for a marketing-site favicon and suggested a star; one mark covers the console and feed.
- `favicon.ico` replaces the Next.js default tab icon; `icon.svg` is the same star for browsers that prefer SVG.

## Dropped

- The scaffold decision and stub-check plan are complete and no longer need tracking.
- Smoke-test wording that the first agent run had not happened; a later dispatch already reached this target.
- Other targets' run logs (nimble, campaign-gen); they do not change the web console.
