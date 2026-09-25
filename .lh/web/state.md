# state: web

## Goal

Maintain a responsive Next.js campaign console where an operator can inspect bounded variant counts, A/A noise, decisions, and dropped events.
The next-day creative brief stays easy to find, with reliable API states and accessible controls.

## Current plan

1. Show the campaign state's next-day brief in the ad-state column without implying lift, still behind the API proxy.
2. Keep the feed scroller and the ad-state column independently scrollable, including on short and mobile viewports.
3. Keep loading, empty, error, and A/A noise feedback clear. Run lint and the production build when application code changes.

## Done

- `web/` is the Next.js console: typed campaign contract, shadcn/ui primitives, API proxy routes, and a Cloud Run container. Checks install from the lockfile, lint, and build.
- Document title is LH Marketing; the feed tab reads Ad Demo Feed · LH Marketing.
- Issues #42 and #53 were state-only updates; campaign-gen work stayed on that target.
- Issue #56: the creative frame keeps a viewport height, and the ad-state column scrolls instead of clipping cards that shrink.

## Open

- Which signals are real inputs (impressions, view-through, CTR, conversions) versus derived; confirm with the marketing schema owner.

## Decisions

- Mock ad platform and video generation behind adapters; the loop must run with zero external calls.
- A/A results are always shown next to A/B so the operator can see the noise floor.
- Browser actions use same-origin Next.js route handlers, which proxy to the configured campaign service.
- Issue #56: state cards are flex children with overflow hidden, so they shrank and clipped. `shrink-0` inside a bounded column lets that column scroll.
- The ad frame used `min(..., 100%)`. The percentage collapsed the creative to a few pixels, so its content could not be seen or scrolled. The frame height is now `calc(100svh-5.5rem)`.
- Snap is `lg`-only so phone layouts can scroll the state cards that sit under each creative. Arrow keys aimed at the state column are not hijacked.
- Issues #42 and #53 asked for state-only updates, so `web/` and `prompt.md` were left unchanged on those runs.

## Dropped

- Scaffold, stub-check, and first-run notes are complete.
- Other-target logs (campaign-gen #33, nimble #26 and #19, dispatch smoke) do not change web work.
- Duplicate workflow and dispatch Done lines were merged earlier and are not repeated.
