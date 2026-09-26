# state: campaign-gen

## Goal

Build and harden Thomas's campaign generation agent: turn Nimble research into brand-safe hooks and scripts, then produce bounded
BFL briefs and reviewable campaign artifacts under `cdn/staging/<campaign_id>/` without leaking credentials.

## Current plan

1. Next `Campaign:` issue: save the issue body to a temp file, build `stories.json` from a committed brand-safe story, run `stage-cdn --max-videos 3 --staging ../cdn/staging`.
2. Make `stage-cdn` idempotent: skip or merge variants whose `meta.json` already has `media_type: video`/`poster_file`, and prune stale variant folders. Tests first.
3. Name guard for generic headlines: titles like "49ers' <player> fined..." still pass through quoted; add a person-name/team heuristic or a curated skip list before staging such stories.
4. Per-vertical product branches are piling up in `make_campaign_info` (game, sandwich, taco, frappe, coffee, pastry, pottery); consider a small keyword table before adding the next one.
5. After `/approve` on live search: `discover-news` once for the campaign geo with `--max-stories 1`, key from env only; feed its `stories.json` into `stage-cdn`.
6. BFL video for staged variants (creative.mp4/poster) only via `approval-request.md`; it spends money.

## Done

- **Inputs:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, saved `stories.json`, or live `NimbleClient` POST `/v2/search` (Bearer from env).
- **Pipeline:** discover → `generate_ads_from_stories` (prompts + `brand_guard`) → optional BFL; CLI: `run`, `discover-news`, `generate-ad`, `generate-video`, `stage-cdn`.
- **Outputs:** `stories.json`/`news.md`; `concepts.json`/`summary.md`/`run.json`; `video_links/`; staged `cdn/staging/<id>/<NN-angle>/{meta.json,script.txt}` + `campaign.json`.
- **Contracts:** `NewsStory`; `VideoAdConcept` (9:16, duration ≤10); `CampaignRecord` (id safe-chars, brief, geo, dims must be 9:16) in `staging.py`, loads JSON or issue body ```json block.
- **Prompts:** `make_campaign_info` branches: game, sandwich, taco (al pastor/trompo/taqueria/burrito), frappe, coffee, pastry, pottery, generic. CTA split before the 220-char phrase cap.
- **Angles:** `order_angles(brief)` keeps `local moment hook` first, promotes `commuter craving` (BART/commute), `quick lunch rescue` (lunch), `late-night payoff` (late-night/after the show).
- **Hooks:** `make_default_cta` reuses imperative briefs as the CTA; explicit `CTA:` wins; late-night payoff hook ends with the campaign product instead of "something refreshing".
- **Sanitizer:** generic and sensitive titles render as `the headline "<cleaned title>"` / `a <market> local moment behind the headline "..."`; publisher suffix and trailing punctuation stripped.
- **Tests:** `tests/test_prompts.py` (campaign info, angle order, truncation), `tests/test_sanitizer.py`, memory/logger tests; 41 total; `checks.sh` runs `unittest discover -s tests`.
- **Checks:** `checks.sh` compiles sources, asserts env-only Nimble creds, runs `run --mock-news --dry-run` and `stage-cdn --mock-news` (sf-coffee-launch fixture), validates 2 meta.json.
- Issue #57: staged `sf-coffee-launch` 01-03 as scripts; later enriched outside this agent with creative.mp4/poster.jpg and weight 2.
- Issue #80: staged `san-ramon-sandwitch-shop` 01-03 (sandwich branch); Issue #81: staged `b-patiserie-award-winning-french-pastries-in-pac-2` 01-03 (pastry branch).
- Issue #86: staged `mission-taqueria-late-night-al-pastor` 01-local-moment-hook, 02-commuter-craving, 03-late-night-payoff (media_type script, CTA "Order ahead and skip the line").
- `.lh/owners.json` `campaign-gen` is `tbarrios`.

## Open

- `stage-cdn` overwrites `meta.json`; re-running it on `sf-coffee-launch` or `tartine-weekend-buns` would reset `media_type: video`, `poster_file`, `weight: 2` back to script values.
- `stage-cdn` never deletes stale variant folders; re-running with fewer variants or a brief that reorders angles leaves old `03-*` folders in place.
- Quoted headlines still carry whatever names the title has; story choice (not the sanitizer) is the current guard against person names.
- `VideoAdConcept.duration_seconds` defaults to 8 while scripts and `bfl_payload.duration` are 10; staging uses the payload value.
- Live Nimble path still needs human-approved one-shot discovery; #57, #80, #81, #86 all reused the committed lowriding story instead of a new call.
- Long briefs are echoed whole as `Campaign message:` in `script.txt`; a shorter product line for the 4-7s beat would read better on screen.
- Pastry branch sits after the coffee branch, so a bakery brief that mentions coffee renders the coffee product shot.
- Voiceover at 0-2s nests double quotes: `"... talking about the headline "<title>"."`; single quotes or an em dash would be cleaner.

## Decisions

- LH agent runs must not use git/gh/bash; CI runs `checks.sh`; agents emulate its steps with allowed Python commands when fixing code.
- Target renamed from `nimble` to `campaign-gen`; Nimble remains one research tool in the research → scripts → BFL briefs pipeline.
- One live Nimble search per approval: discover only, no BFL spend, no schema change; secrets never in state, logs, or PR artifacts.
- Website campaign issues: `brief` is the campaign script, `geo` the market, `dims` must be 9:16; write only under `cdn/staging/<id>/`; do not invent ids; `issue_url` stays as given.
- Staged variants ship as `media_type: script` with no BFL call; merge to `main` is the publish gate (`publish-assets.yml` on `cdn/staging/**`), so no approval-request file.
- Story source for #57/#80/#81/#86: lowriding story from `cdn/staging/local-news-20260925/run.json` (real Nimble result, brand_safe, no person names, Mission Street fits #86).
- Headline quoting chosen over noun-phrase rewriting: no NLP dependency, grammatical for any headline shape, and the raw title stays reviewable in `script.txt`.
- Brief-aware angle order (#86): a late-night brief would otherwise stage three daytime angles under `--max-videos 3`. Angle set and meta.json fields unchanged, so no schema change.
- Angle promotion is keyword-only and leaves existing briefs (game, sandwich, pastry, frappe) in canonical order; asserted by tests so staged folders do not silently renumber.
- Human/other-agent edits to staged `meta.json` (video media, weights) are authoritative; this agent must not regenerate those folders without an explicit issue asking for it.
- Approval-request file is stripped before commit; issue title comes from its first line. No `prompt.md` change this run.
- Prior `nimble` runs (#19, #26) were on composer-2.5; #33, #57, #80, #81, #86 on Claude Fable 5.1, so smoke results are not model-comparable.

## Dropped

- Web-target runs (#39 titles, #42 router test, #53 status comment) touched only `web/` and `.lh/web/`; nothing for campaign-gen.
- Prior smoke runs (#26, #33) refreshed state only; no product diff to carry.
- Sample run folders under `viral-local-ad-generator/runs/` and `cdn/staging/*/run.json` (other pipeline's format) stay in git, not copied into agent state.
- Other stories in `local-news-20260925/run.json` (athlete fine, startup cafes, marmots) skipped: named people/companies or trademarked event.
- Run artifacts for #80, #81, #86 (`run.json`, `concepts.json`, sanitized stories) written to temp dirs, not committed; staged folder plus `campaign.json` is the reviewable record.
- `src/viral_local_ad_generator/__pycache__` predates these runs and is gitignored; not touched.
