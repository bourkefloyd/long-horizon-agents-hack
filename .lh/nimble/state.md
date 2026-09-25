# state: nimble

## Goal

Document and harden Thomas's viral local ad CLI: campaign text plus a media market drive Nimble discovery (or mock news), then bounded JSON artifacts for review—stories with trusted URLs, brand-safe
VideoAdConcept rows (hooks, scripts, FLUX/BFL payloads)—without credentials in output.

## Current plan

1. After `/approve` on the live-search request, run `discover-news` once for San Francisco with `--max-stories 1`; key only from env; check `stories.json` URLs and `brand_safe`.
2. Before edits under `viral-local-ad-generator/`, mirror checks offline: compileall, mock `run --dry-run`, validate `run.json` story/concept fields and duration caps.
3. Set `.lh/owners.json` `nimble` to Thomas's GitHub login when known so approval issues assign to him directly.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, or live `NimbleClient` POST `/v2/search` (Bearer from env); optional `BFL_API_KEY` for video.
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`.
- **Outputs:** `stories.json` and `news.md` (discovery); `concepts.json`, `summary.md`, `run.json` (generation); `video_links/` (and optional `videos/`) when BFL poll/submit runs.
- **Contracts:** `NewsStory` (title, url, scores, brand_safe); `VideoAdConcept` with hook, script, video_script, prompts, 9:16, duration ≤10; checks assert single-story mock dry-run payload.
- Issue #19: reviewed `viral-local-ad-generator/` I/O; no application code changed this run.

## Open

- Live Nimble path is not run in deterministic checks (quota/network); needs human-approved one-shot discovery.
- `nimble` owner in `.lh/owners.json` is still a placeholder.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents validate with allowed Python commands when fixing code.
- One live Nimble search per approval: discover only, no BFL spend, no schema change, no publishing; secrets never in state, logs, or PR artifacts.
- Approval-request file is stripped before commit; issue title comes from its first line.

## Dropped

- Prior smoke run only refreshed state after reading `nimble_client`, `pipeline`, `cli`, and brand-safety paths—no product diff.
- Sample run folders under `viral-local-ad-generator/runs/` stay in git, not copied into agent state.
