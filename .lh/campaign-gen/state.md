# state: campaign-gen

## Goal

Build and harden Thomas's campaign generation agent: turn Nimble research into brand-safe hooks and scripts, then produce bounded
BFL briefs and reviewable campaign artifacts under `cdn/staging/<campaign_id>/` without leaking credentials.

## Current plan

1. Issue #57 delivered as scripts (media_type `script`). Next campaign issue: run `stage-cdn` with the issue body as `--campaign-record`; keep `--max-videos 3`.
2. Improve `sanitizer._generic_topic_from_title`: hooks currently read "local story about <raw title>" and can carry real names (e.g. athlete titles). Add tests first.
3. After `/approve` on live search: `discover-news` once for the campaign geo with `--max-stories 1`, key from env only; feed its `stories.json` into `stage-cdn`.
4. BFL video for staged variants (poster/creative.mp4) only via `approval-request.md`; it spends money.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, saved `stories.json`, or live `NimbleClient` POST `/v2/search` (Bearer from env).
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`, `stage-cdn`.
- **Outputs:** `stories.json`/`news.md`; `concepts.json`/`summary.md`/`run.json`; `video_links/`; staged `cdn/staging/<id>/<NN-angle>/{meta.json,script.txt}` + `campaign.json`.
- **Contracts:** `NewsStory`; `VideoAdConcept` (9:16, duration ≤10); `CampaignRecord` (id safe-chars, brief, geo, dims must be 9:16) in `staging.py`, loads JSON or issue body ```json block.
- **Prompts:** `make_campaign_info` has a `game` branch (phone-screen product shot, CTA "Download the game and play on your next break.") ahead of coffee/frappe.
- **Checks:** `checks.sh` also runs `stage-cdn --mock-news` on `examples/sf-coffee-launch.json` and validates 2 meta.json files (fields, ids, media exists, no key).
- Issue #57: staged `sf-coffee-launch` variants 01-local-moment-hook, 02-commuter-craving, 03-fan-celebration; validated via `publish.py` staged_ads + schema offline.
- `.lh/owners.json` `campaign-gen` is `tbarrios`.

## Open

- Sanitizer passes raw titles through; "San Francisco's local story about San Francisco celebrates..." is clunky and can leak person names from titles.
- `VideoAdConcept.duration_seconds` defaults to 8 while scripts and `bfl_payload.duration` are 10; staging uses the payload value.
- Live Nimble path still needs human-approved one-shot discovery; #57 reused a committed brand-safe story instead of a new call.
- `stage-cdn` never deletes stale variant folders; re-running with fewer variants leaves old ones in place.
- README `--staging ../cdn/staging` is relative to `viral-local-ad-generator/`; the LH run used `/tmp` for run artifacts, not `runs/`.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents validate with allowed Python commands when fixing code.
- Target renamed from `nimble` to `campaign-gen`; Nimble remains one research tool in the research → scripts → BFL briefs pipeline.
- One live Nimble search per approval: discover only, no BFL spend, no schema change; secrets never in state, logs, or PR artifacts.
- Website campaign issues: `brief` is the campaign script, `geo` the market, `dims` must be 9:16; write only under `cdn/staging/<id>/`; do not invent ids.
- Staged variants ship as `media_type: script` with no BFL call; merge to `main` is the publish gate (`publish-assets.yml` on `cdn/staging/**`), so no approval-request file.
- #57 story source: the lowriding story from `cdn/staging/local-news-20260925/run.json` (real Nimble result, brand_safe, no person names) rather than mock news.
- Marketing output schema unchanged; `stage-cdn` is additive. Approval-request file is stripped before commit; issue title comes from its first line.
- Prior `nimble` runs (#19, #26) were on composer-2.5; #33 and #57 on Claude Fable 5.1, so smoke results are not model-comparable.

## Dropped

- Web-target runs (#39 titles, #42 router test, #53 status comment) touched only `web/` and `.lh/web/`; nothing for campaign-gen.
- Prior smoke runs (#26, #33) refreshed state only; no product diff to carry.
- Sample run folders under `viral-local-ad-generator/runs/` stay in git, not copied into agent state.
- Other stories in `local-news-20260925/run.json` (athlete fine, startup cafes, marmots) skipped: named people/companies or trademarked event.
