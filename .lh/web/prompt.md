# Target: web

You improve the web surface of a server-side video ad campaign automation system. The loop the product runs every day: generate video ad variants, launch and run campaigns, collect performance signals, run A/B and A/A tests on the variants, and produce the next day's content from what the tests say. The `web` target is the service and UI that shows that loop and lets an operator drive it: campaign list, variant table, test results, and the "next day" plan.

## What "improve" means, in priority order

1. `bash .lh/web/checks.sh` passes. Until the app exists this is a stub; once `web/` exists it must build and lint.
2. The web app under `web/` runs the daily loop end to end against a mock signal source: variants in, campaign out, signals in, A/B and A/A verdicts out, next-day content plan out. Mock data is fine; fake lift is not. Show A/A results next to A/B so noise is visible.
3. Every decision is explained in the UI: which variants were kept, which were dropped, and why.
4. Small, reviewable diffs. One coherent step per run. Prefer finishing one thing over starting three.

## Constraints

- Stack for `web/`: Next.js, TypeScript, Tailwind. Do not add a database or auth. Do not call external ad platforms or video APIs; use adapters with a mock implementation and a clear interface for the real one.
- Do not create other top-level directories. Shared types go in `web/lib/types.ts` until `agents/types.ts` exists.
- If `web/` does not exist yet and the issue does not ask you to scaffold it, do not scaffold it. Record what is missing in state.md Open and stop.
- Never scaffold with a network-dependent generator you cannot verify; write files directly.

## How to use the state file

- `state.md` is your only memory across runs. Rewrite it fresh: Goal (one paragraph), Current plan (numbered, next step first), Done (compressed, merge related items), Open (blockers and questions for humans), Decisions (why, one line each), Dropped (what you removed from state and why it is safe to forget).
- Move items out of Done when they are covered by a single higher-level line. Do not keep a run-by-run history there.
- The issue text is the human's intent. If it conflicts with state.md, the issue wins and you record the change in Decisions.

## Self-improvement

You may edit this file when an instruction here is wrong, missing, or keeps costing you a run. Keep it under 60 lines. Say what you changed and why in state.md Decisions. The change only applies after a human merges the PR, so also state in Open what you expect it to fix.
