# Target: campaign-gen

You improve Thomas's campaign generator in `viral-local-ad-generator/`. It is a dependency-free Python 3.11 CLI that uses
Nimble Search to discover recent local stories, filters and ranks them for relevance, virality, and brand safety, then emits
marketing concepts, hooks, 10-second vertical video scripts, FLUX prompts, and optional BFL video jobs.
Upcoming work includes BFL video generation and Liquid model calls.

## How to run it

- Deterministic target check: `bash .lh/campaign-gen/checks.sh`.
- Offline one-shot run: from `viral-local-ad-generator/`, set `PYTHONPATH=src` and run
  `python3 -m viral_local_ad_generator.cli run --campaign examples/new-bigmac-test.txt --market "San Francisco" --mock-news --dry-run --max-stories 1 --max-videos 1 --output <temporary-directory>`.
- Live discovery uses `NIMBLE_API_KEY` from the environment. Never put the key in arguments, files, generated output, state, logs, or
  messages, and never print environment variables or request headers. Do not add a `.env` file.

## What "improve" means, in priority order

1. `bash .lh/campaign-gen/checks.sh` passes offline: Python sources compile, scripts run, and the bounded marketing concept JSON validates.
2. Live Nimble requests use only `NIMBLE_API_KEY` from the environment and preserve trusted source URLs without exposing credentials.
3. Marketing output remains small and reviewable: valid stories and concepts, usable hooks, complete video scripts, safe prompts, and
   stable required fields. Add tests before changing the schema.
4. Brand-safety checks reject sensitive stories and famous-brand leakage while retaining useful local context.
5. Make one coherent, reviewable change per run. Do not edit `web/` or `service/`.

## Website campaigns

The website's `POST /campaigns/{id}/queue` opens a task issue titled `Campaign: <name>` whose body contains a fenced ```json block
with the campaign record (`id`, `name`, `brief`, `vertical`, `geo`, `audience`, `dims`). When the task issue contains such a block,
generate for that campaign: use `brief` as the campaign script, `geo` as the market, honor `dims`, and write every staged output under
`cdn/staging/<campaign_id>/<variant>/` with a `meta.json` per variant (see `docs/cdn.md`) so the feed can filter by `campaign_id`.
Do not invent a different campaign id and do not write outside that folder. Publishing to the CDN still requires human approval.

## Human approval

Do not spend money, change the marketing output schema, or publish content without a human decision. Instead, include the proposed
code change and write `.lh/campaign-gen/approval-request.md`. Its first non-empty line is a short, non-secret summary for the issue title;
the rest may contain a concise rationale, but no credentials, tokens, customer data, or unpublished content. A deterministic step
removes this request file before commit, opens an approval issue linked to the PR, and waits for an assignee to comment `/approve`.
An approval request must accompany a real proposed change that can be reviewed in a PR.

## State and self-improvement

Rewrite `state.md` from scratch every run using its six fixed sections and keep it compact. The issue is the current task and wins
over stale state. You may improve this prompt when a concrete instruction is wrong or repeatedly costly; record why in Decisions.
