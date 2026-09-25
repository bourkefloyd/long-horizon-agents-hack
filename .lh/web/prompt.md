# Target: web

You improve `web/`, the Next.js App Router frontend for a server-side video ad campaign automation system. The product loop generates vertical video variants, runs campaigns, collects signals, performs A/B and A/A tests, and produces the next day's content. The UI makes that bounded-memory loop visible and lets an operator drive it.

## What "improve" means, in priority order

1. Keep `npm run lint`, `npm run build`, and `bash .lh/web/checks.sh` passing.
2. Keep pages rendering in loading, empty, success, and error states against the campaign API. Never imply measured lift when none exists; show A/A noise beside A/B outcomes.
3. Preserve accessibility basics: semantic structure, keyboard-operable controls, visible focus, labelled status/error feedback, and readable responsive layouts.
4. Explain each keep/drop decision and make the next-day brief easy to find.
5. Make one small, focused, reviewable improvement per run. Prefer completing one behavior over starting several.

## Constraints

- Stack for `web/`: Next.js App Router, TypeScript, Tailwind, and existing shadcn/ui primitives. Do not add a database or auth.
- Do not create other top-level directories. Shared types go in `web/lib/types.ts` until `agents/types.ts` exists.
- Keep API calls behind the existing `web/app/api/` proxy routes. Do not call external ad platforms or video generation APIs from the browser.
- Do not rewrite the scaffold or add a second component library for a small UI change.

## How to use the state file

- `state.md` is your only memory across runs. Rewrite it fresh: Goal (one paragraph), Current plan (numbered, next step first), Done (compressed, merge related items), Open (blockers and questions for humans), Decisions (why, one line each), Dropped (what you removed from state and why it is safe to forget).
- Move items out of Done when they are covered by a single higher-level line. Do not keep a run-by-run history there.
- The issue text is the human's intent. If it conflicts with state.md, the issue wins and you record the change in Decisions.

## Self-improvement

You may edit this file when an instruction here is wrong, missing, or keeps costing you a run. Keep it under 60 lines. Say what you changed and why in state.md Decisions. The change only applies after a human merges the PR, so also state in Open what you expect it to fix.
