# state: campaign-gen

## Goal

Build and harden Thomas's campaign generation agent: turn Nimble research into brand-safe hooks and scripts, then produce bounded
BFL briefs and reviewable campaign artifacts under `cdn/staging/<campaign_id>/` without leaking credentials.

## Current plan

1. Next campaign issue: save body to `/tmp`, run `stage-cdn --campaign-record <file> --stories <file> --max-videos 3`; validate via `publish.py` staged_ads + schema.
2. Improve `sanitizer._generic_topic_from_title`: variant 01 hooks read "local story about <raw title>" and can carry real names. Add `tests/` (unittest) first.
3. After `/approve` on live search: `discover-news` once for the campaign geo with `--max-stories 1`, key from env only; feed its `stories.json` into `stage-cdn`.
4. BFL video for staged variants (poster/creative.mp4) only via `approval-request.md`; it spends money.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, saved `stories.json`, or live `NimbleClient` POST `/v2/search` (Bearer from env).
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`, `stage-cdn`.
- **Outputs:** `stories.json`/`news.md`; `concepts.json`/`summary.md`/`run.json`; `video_links/`; staged `cdn/staging/<id>/<NN-angle>/{meta.json,script.txt}` + `campaign.json`.
- **Contracts:** `NewsStory`; `VideoAdConcept` (9:16, duration ≤10); `CampaignRecord` (id safe-chars, brief, geo, dims must be 9:16) in `staging.py`, loads JSON or issue body ```json block.
- **Prompts:** `make_campaign_info` branches: `game` (phone-screen shot, download CTA) > bakery (`morning bun|pastry|bakery|croissant`) > `frappe` > `coffee` > generic.
- **Checks:** `checks.sh` compiles, checks env-only creds, mock dry run, `stage-cdn --mock-news` on `examples/sf-coffee-launch.json`, validates 2 meta.json files.
- Issue #57: staged `sf-coffee-launch` 01-local-moment-hook, 02-commuter-craving, 03-fan-celebration (media_type `script`).
- Issue #66: staged `tartine-weekend-buns` same three variants + `campaign.json`; bakery branch gives pastry product shot and CTA "Grab one warm before the weekend gets going."
- #66 verified offline: every checks.sh step emulated in Python, coffee fixture CTA unchanged, 18 staged ads (3 new) pass `cdn/manifest.schema.json` via `publish.py`.
- `.lh/owners.json` `campaign-gen` is `tbarrios`.

## Open

- Sanitizer passes raw titles through; "San Francisco's local story about San Francisco celebrates culture of lowriding" repeats in #57 and #66 variant 01.
- Bakery/game branches are keyword heuristics with fixed CTAs; a brief mixing coffee and pastry picks bakery. A Liquid call could replace this later.
- `VideoAdConcept.duration_seconds` defaults to 8 while scripts and `bfl_payload.duration` are 10; staging uses the payload value.
- Live Nimble path still needs human-approved one-shot discovery; #57 and #66 reused a committed brand-safe story instead of a new call.
- `stage-cdn` never deletes stale variant folders; re-running with fewer variants leaves old ones in place.
- Angles 04/05 (quick lunch rescue, late-night payoff) never ship at `--max-videos 3`; hooks 02/03 ignore the story and only vary by market.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents emulate its steps with allowed Python commands when changing code.
- Target renamed from `nimble` to `campaign-gen`; Nimble remains one research tool in the research → scripts → BFL briefs pipeline.
- One live Nimble search per approval: discover only, no BFL spend, no schema change; secrets never in state, logs, or PR artifacts.
- Website campaign issues: `brief` is the campaign script, `geo` the market, `dims` must be 9:16; write only under `cdn/staging/<id>/`; do not invent ids or `issue_url`.
- Staged variants ship as `media_type: script` with no BFL call; merge to `main` is the publish gate (`publish-assets.yml` on `cdn/staging/**`), so no approval-request file.
- Story source for #57 and #66: the lowriding story from `cdn/staging/local-news-20260925/run.json` (real Nimble result, brand_safe, Mission Street, no person names).
- #66 scope kept to staging plus one `make_campaign_info` branch (same pattern as the #57 `game` branch); sanitizer rewrite deferred so it ships with tests.
- Marketing output schema unchanged; `stage-cdn` is additive. Approval-request file is stripped before commit; issue title comes from its first line.
- The advertiser's own brand in a brief (e.g. Tartine) is not a famous-brand leak; `brand_guard` only screens story-derived text and generated creative.
- Prior `nimble` runs (#19, #26) were on composer-2.5; #33, #57, #66 on Claude Fable 5.1, so smoke results are not model-comparable.

## Dropped

- Web-target runs (#39 titles, #42 router test, #53 status comment) touched only `web/` and `.lh/web/`; nothing for campaign-gen.
- Prior smoke runs (#26, #33) refreshed state only; no product diff to carry.
- Sample run folders under `viral-local-ad-generator/runs/` and `src/**/__pycache__` are gitignored; run artifacts for #66 lived in `/tmp` only.
- Other stories in `local-news-20260925/run.json` (athlete fine, startup cafes, marmots) skipped: named people/companies or trademarked event.
- Mock stories for #66 rejected: a real Mission Street story fits Dolores Park better than "food festival" placeholders.
