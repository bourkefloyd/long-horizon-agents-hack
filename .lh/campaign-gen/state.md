# state: campaign-gen

## Goal

Build and harden Thomas's campaign generation agent: turn Nimble research into brand-safe hooks and scripts, then produce bounded
BFL briefs and reviewable campaign artifacts under `cdn/staging/<campaign_id>/` without leaking credentials.

## Current plan

1. Next `Campaign:` issue: save the body to `/tmp`, run `stage-cdn --campaign-record <file> --mock-news --max-videos 3 --staging ../cdn/staging` unless a real brand-safe story exists.
2. Fix `sanitizer._generic_topic_from_title`: strip a leading market name and lowercase the topic so hooks stop repeating the market; tests first in `tests/test_sanitizer.py`.
3. Add a `make_campaign_info` branch only when a real brief falls to the `featured offer` default; each branch needs a test in `tests/test_prompts.py`.
4. After `/approve` on live search: `discover-news` once for the campaign geo with `--max-stories 1`, key from env only; feed its `stories.json` into `stage-cdn`.
5. BFL video for staged variants only via `approval-request.md`; it spends money.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, saved `stories.json`, or live `NimbleClient` POST `/v2/search` (Bearer from env).
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`, `stage-cdn`.
- **Outputs:** `stories.json`/`news.md`; `concepts.json`/`summary.md`/`run.json`; `video_links/`; staged `cdn/staging/<id>/<NN-angle>/{meta.json,script.txt}` + `campaign.json`.
- **Contracts:** `NewsStory`; `VideoAdConcept` (9:16, duration ≤10); `CampaignRecord` (id safe-chars, brief, geo, dims must be 9:16) in `staging.py`, loads JSON or issue body ```json block.
- **Prompts:** `make_campaign_info` branches: game, sandwich (matches `sandwi`, so "sandwitch" too; CTA "Tap the link and order your sandwich now." when brief says link), frappe, coffee, pottery.
- **Tests:** `tests/` (unittest, offline): agent_memory, event_logger, prompts (24 tests). `checks.sh` runs them, the mock dry run, and `stage-cdn` on `examples/sf-coffee-launch.json`.
- Issue #57: `sf-coffee-launch` 01-local-moment-hook, 02-commuter-craving, 03-fan-celebration staged as scripts; a human later added creative.mp4/poster.jpg and set media_type video.
- Issue #80: `san-ramon-sandwitch-shop` 01-local-moment-hook, 02-commuter-craving, 03-fan-celebration staged as `media_type: script`, geo "San Ramon CA", 9:16, duration 10, no key in output.
- `.lh/owners.json` `campaign-gen` is `tbarrios`.

## Open

- #80 used `--mock-news` (story "San Ramon CA food festival draws huge weekend crowds", example.com URL, source "Mock Local News"): no San Ramon story exists offline and live Nimble needs approval.
- Variant 01 hook for #80 is clunky: "San Ramon CA is already talking about this: San Ramon CA's local moment about San Ramon CA food festival ..."; sanitizer passes raw titles through.
- `stage-cdn` overwrites `meta.json`/`script.txt` in place; re-running it on `sf-coffee-launch` would clobber the human-added video meta. Do not re-stage ids that already have media.
- `VideoAdConcept.duration_seconds` defaults to 8 while scripts and `bfl_payload.duration` are 10; staging uses the payload value.
- `stage-cdn` never deletes stale variant folders; re-running with fewer variants leaves old ones in place.
- `split_campaign_and_cta` strips the trailing period from explicit `CTA:` text; test documents it rather than changing behavior.
- README `--staging ../cdn/staging` is relative to `viral-local-ad-generator/`; LH runs use `/tmp` for run artifacts, not `runs/`.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents emulate its steps with allowed Python commands when fixing code.
- Target renamed from `nimble` to `campaign-gen`; Nimble remains one research tool in the research → scripts → BFL briefs pipeline.
- One live Nimble search per approval: discover only, no BFL spend, no schema change; secrets never in state, logs, or PR artifacts.
- Website campaign issues: `brief` is the campaign script, `geo` the market, `dims` must be 9:16; write only under `cdn/staging/<id>/`; do not invent ids or "fix" misspelled ids.
- Staged variants ship as `media_type: script` with no BFL call; merge to `main` is the publish gate (`publish-assets.yml` on `cdn/staging/**`), so no approval-request file.
- #80: added the sandwich prompt branch instead of shipping "Try Casual sandwitch lovers buy now link today." as the CTA; a brief that hits the default branch is not reviewable output.
- Mock stories are acceptable for a campaign issue when no real brand-safe story for the geo exists; `campaign.json` records the mock source so reviewers can see it.
- Unit tests are now part of `checks.sh`; new prompt or sanitizer behavior lands with tests in the same run.
- #57 story source: the lowriding story from `cdn/staging/local-news-20260925/run.json` (real Nimble result, brand_safe, no person names) rather than mock news.
- Marketing output schema unchanged; `stage-cdn` is additive. Approval-request file is stripped before commit; issue title comes from its first line.
- Prior `nimble` runs (#19, #26) were on composer-2.5; #33, #57, #80 on Claude Fable 5.1, so smoke results are not model-comparable.

## Dropped

- Web-target runs (#39 titles, #42 router test, #53 status comment) touched only `web/` and `.lh/web/`; nothing for campaign-gen.
- Prior smoke runs (#26, #33) refreshed state only; no product diff to carry.
- Sample run folders under `viral-local-ad-generator/runs/` and the committed `src/**/__pycache__` stay as they are, not copied into agent state.
- Other stories in `local-news-20260925/run.json` (athlete fine, startup cafes, marmots) skipped: SF-only and named people/companies or trademarked event; none fit San Ramon.
- `cdn/publish.py` offline validation skipped this run: `google-cloud-storage`/`jsonschema` are not installed; required fields were checked directly against `cdn/manifest.schema.json`.
