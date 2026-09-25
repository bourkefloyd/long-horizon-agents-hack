# state: campaign-gen

## Goal

Build and harden Thomas's campaign generation agent: turn Nimble research into brand-safe hooks and scripts, then produce bounded
BFL briefs and reviewable campaign artifacts under `cdn/staging/<campaign_id>/` without leaking credentials.

## Current plan

1. Next `Campaign:` issue: save the issue body to a temp file, build `stories.json` from a committed brand-safe story, run `stage-cdn --max-videos 3 --staging ../cdn/staging`.
2. Make `stage-cdn` idempotent: skip or merge variants whose `meta.json` already has `media_type: video`/`poster_file`, and prune stale variant folders. Tests first.
3. Name guard for generic headlines: titles like "49ers' <player> fined..." still pass through quoted; add a person-name/team heuristic or a curated skip list before staging such stories.
4. After `/approve` on live search: `discover-news` once for the campaign geo with `--max-stories 1`, key from env only; feed its `stories.json` into `stage-cdn`.
5. BFL video for staged variants (creative.mp4/poster) only via `approval-request.md`; it spends money.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, saved `stories.json`, or live `NimbleClient` POST `/v2/search` (Bearer from env).
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`, `stage-cdn`.
- **Outputs:** `stories.json`/`news.md`; `concepts.json`/`summary.md`/`run.json`; `video_links/`; staged `cdn/staging/<id>/<NN-angle>/{meta.json,script.txt}` + `campaign.json`.
- **Contracts:** `NewsStory`; `VideoAdConcept` (9:16, duration ≤10); `CampaignRecord` (id safe-chars, brief, geo, dims must be 9:16) in `staging.py`, loads JSON or issue body ```json block.
- **Prompts:** `make_campaign_info` branches: game, frappe, coffee, pastry (kouign/croissant/bakery), pottery, generic. `make_default_cta` reuses imperative briefs ("Come try ...") as the CTA.
- **Sanitizer:** generic and sensitive titles render as `the headline "<cleaned title>"` / `a <market> local moment behind the headline "..."`; publisher suffix and trailing punctuation stripped.
- **Tests:** `tests/test_prompts.py`, `tests/test_sanitizer.py` (+ existing memory/logger tests, 24 total); `checks.sh` runs `unittest discover -s tests` before the mock dry run.
- **Checks:** `checks.sh` compiles sources, asserts env-only Nimble creds, runs `run --mock-news --dry-run` and `stage-cdn --mock-news` (sf-coffee-launch fixture), validates 2 meta.json.
- Issue #57: staged `sf-coffee-launch` 01-local-moment-hook, 02-commuter-craving, 03-fan-celebration as scripts; later enriched outside this agent with creative.mp4/poster.jpg.
- Issue #81: staged `b-patiserie-award-winning-french-pastries-in-pac-2` variants 01-03 (media_type script, CTA "Come try our famous kouign Amann.") + `campaign.json`.
- `.lh/owners.json` `campaign-gen` is `tbarrios`.

## Open

- `stage-cdn` overwrites `meta.json`; re-running it on `sf-coffee-launch` or `tartine-weekend-buns` would reset `media_type: video`, `poster_file`, `weight: 2` back to script values.
- `stage-cdn` never deletes stale variant folders; re-running with fewer variants leaves old ones in place.
- Quoted headlines still carry whatever names the title has; story choice (not the sanitizer) is the current guard against person names.
- `VideoAdConcept.duration_seconds` defaults to 8 while scripts and `bfl_payload.duration` are 10; staging uses the payload value.
- Live Nimble path still needs human-approved one-shot discovery; #57 and #81 reused the committed lowriding story instead of a new call.
- Story fit is weak for non-food angles: a French pastry campaign paired with a lowriding headline is coherent but generic; live discovery per campaign would improve relevance.
- Pastry branch sits after the coffee branch, so a bakery brief that mentions coffee renders the coffee product shot.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents emulate its steps with allowed Python commands when fixing code.
- Target renamed from `nimble` to `campaign-gen`; Nimble remains one research tool in the research → scripts → BFL briefs pipeline.
- One live Nimble search per approval: discover only, no BFL spend, no schema change; secrets never in state, logs, or PR artifacts.
- Website campaign issues: `brief` is the campaign script, `geo` the market, `dims` must be 9:16; write only under `cdn/staging/<id>/`; do not invent ids; `issue_url` stays as given.
- Staged variants ship as `media_type: script` with no BFL call; merge to `main` is the publish gate (`publish-assets.yml` on `cdn/staging/**`), so no approval-request file.
- Story source for #57 and #81: the lowriding story from `cdn/staging/local-news-20260925/run.json` (real Nimble result, brand_safe, no person names). Lantern story rejected: snippet names people.
- Headline quoting chosen over noun-phrase rewriting: no NLP dependency, grammatical for any headline shape, and the raw title stays reviewable in `script.txt`.
- Imperative-brief CTA fixes "Try Come try ... today."; explicit `CTA:` marker still wins; game branch keeps its fixed CTA. Marketing output schema unchanged; `stage-cdn` remains additive.
- Human/other-agent edits to staged `meta.json` (video media, weights) are authoritative; this agent must not regenerate those folders without an explicit issue asking for it.
- Approval-request file is stripped before commit; issue title comes from its first line.
- Prior `nimble` runs (#19, #26) were on composer-2.5; #33, #57, #81 on Claude Fable 5.1, so smoke results are not model-comparable.

## Dropped

- Web-target runs (#39 titles, #42 router test, #53 status comment) touched only `web/` and `.lh/web/`; nothing for campaign-gen.
- Prior smoke runs (#26, #33) refreshed state only; no product diff to carry.
- Sample run folders under `viral-local-ad-generator/runs/` and `cdn/staging/*/run.json` (other pipeline's format) stay in git, not copied into agent state.
- Other stories in `local-news-20260925/run.json` (athlete fine, startup cafes, marmots) skipped: named people/companies or trademarked event.
- Issue #81 run artifacts (`run.json`, `concepts.json`, sanitized stories) written to a temp dir, not committed; staged folder plus `campaign.json` is the reviewable record.
