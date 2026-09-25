# state: nimble

## Goal

Keep Thomas's local-news-reactive ad generator reliable: trusted Nimble inputs become bounded, brand-safe marketing concepts and
10-second vertical video scripts that satisfy the documented JSON contract without exposing credentials.

## Current plan

1. Validate the existing mock-news dry run and its marketing concept output on every LH run.
2. Tighten the output contract and add focused tests before changing generation behavior.
3. Exercise live Nimble discovery only in an explicitly requested task with `NIMBLE_API_KEY` available.

## Done

- Thomas's Python CLI exists under `viral-local-ad-generator/` with staged discovery, concept generation, and optional BFL submission.
- The target has deterministic offline checks using mock news and a one-video dry run.

## Open

- Thomas's GitHub login is not known; replace the placeholder in `.lh/owners.json` so approval issues assign directly to him.
- The Nimble client's live request path is not exercised by deterministic checks because that would spend quota and require network access.

## Decisions

- Default checks are offline and never need API credentials.
- Spending money, changing the marketing output schema, or publishing content requires an approval request.
- Secrets stay in environment variables and must never appear in state, logs, generated artifacts, issues, or terminal output.

## Dropped

- Historical sample runs are not copied into agent state; they remain available in git under `viral-local-ad-generator/runs/`.
