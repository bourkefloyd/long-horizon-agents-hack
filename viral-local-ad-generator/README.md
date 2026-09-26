# Viral Local Ad Generator

Generate local-news-reactive playable/video ad concepts from:

- an advertising campaign script
- a media market, such as "San Francisco"
- five recent local stories found with Nimble
- five FLUX 3 video prompts/jobs per story

The normal workflow is staged: discover local outlets first, discover and store stories from those outlets, inspect `stories.json` / `news.md`, then generate ad scripts/prompts, then optionally submit video jobs.

## Why This Exists

The core loop is:

1. Search for local news outlets in a media market.
2. Search recent web news stories from/prioritizing those outlets.
3. Rank/filter for recency, local relevance, virality signals, and brand safety.
4. Sanitize each story into an ad-safe story frame/reference.
5. Turn each sanitized story into five ad angles tied back to the campaign script.
6. Convert each angle into a 10-second video commercial script.
7. Optionally submit those scripts/prompts to Black Forest Labs FLUX 3 Video.
8. Save every outlet, story, sanitized story, script, prompt, and generation job as JSON for review and testing.

## Setup

```bash
cd viral-local-ad-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Then edit `.env`:

```bash
NIMBLE_API_KEY=...
BFL_API_KEY=...
TINYBIRD_TOKEN=...
```

If Nimble is only available inside Codex via OAuth/MCP, keep using `--mock-news` until we wire this standalone CLI to the MCP client path.

Tinybird logging is optional but enabled automatically when `TINYBIRD_TOKEN` is present. The default workspace host is set for the GCP `europe-west2` region:

```bash
TINYBIRD_BASE_URL=https://api.europe-west2.gcp.tinybird.co
TINYBIRD_DATASOURCE=events
```

## Usage

Step 1: discover/store local news outlets.

```bash
viral-local-ads \
  discover-outlets \
  --market "San Francisco" \
  --max-outlets 8 \
  --output runs/sf-outlets
```

This writes:

```text
runs/sf-outlets/outlets.json
runs/sf-outlets/outlets.md
```

Step 2: discover/store news from those outlets.

```bash
viral-local-ads \
  discover-news \
  --market "San Francisco" \
  --outlets runs/sf-outlets/outlets.json \
  --max-stories 1 \
  --output runs/sf-news
```

This writes:

```text
runs/sf-news/stories.json
runs/sf-news/news.md
```

If you omit `--outlets`, `discover-news` automatically runs outlet discovery first and saves `outlets.json` / `outlets.md` beside `stories.json`.

Step 3: generate the ad script and FLUX prompt from saved news.

```bash
viral-local-ads \
  generate-ad \
  --campaign examples/new-bigmac-test.txt \
  --market "San Francisco" \
  --stories runs/sf-news/stories.json \
  --max-videos 1 \
  --output runs/sf-ad
```

This writes:

```text
runs/sf-ad/concepts.json
runs/sf-ad/input_webpages.json
runs/sf-ad/input_webpages.md
runs/sf-ad/sanitized_stories.json
runs/sf-ad/sanitized_stories.md
runs/sf-ad/summary.md
runs/sf-ad/run.json
```

Step 4: submit FLUX 3 Video jobs.

```bash
viral-local-ads \
  generate-video \
  --concepts runs/sf-ad/concepts.json \
  --poll \
  --output runs/sf-video
```

Generated video links are saved under:

```text
runs/<run-name>/video_links/
```

If you also want local downloads, add `--download-media`. Downloaded files are saved under:

```text
runs/<run-name>/videos/
```

Step 5 (website campaigns): stage scripts for the ad CDN.

The website queues a campaign as a task issue whose body contains a fenced ```json block with the campaign record
(`id`, `name`, `brief`, `vertical`, `geo`, `audience`, `dims`). `stage-cdn` accepts that record as a JSON file or the raw
issue body, uses `brief` as the campaign script and `geo` as the market, and writes one folder per variant under
`cdn/staging/<campaign_id>/<variant>/` with `script.txt` and a `meta.json` in the layout described in `docs/cdn.md`.
Only `dims: "9:16"` is accepted. Nothing is published until the staged folder is reviewed and merged to `main`.

The brief doubles as the CTA when it is already an invitation ("Come try our famous kouign Amann" ends the ad as-is);
otherwise the CTA is `Try <brief> today.` unless the brief contains an explicit `CTA:` marker. Generic headlines are
quoted in hooks and voiceover (`the headline "<title>"`) rather than spliced into a sentence.

Variant angles follow the brief: `local moment hook` is always first, then angles the brief signals (`late-night`,
`after the show` promote `late-night payoff`; `lunch` promotes `quick lunch rescue`; `BART`, `commute` promote
`commuter craving`), then the remaining canonical angles. A late-night taqueria brief therefore stages
`03-late-night-payoff` instead of `03-fan-celebration`.

```bash
viral-local-ads \
  stage-cdn \
  --campaign-record examples/sf-coffee-launch.json \
  --stories runs/sf-news/stories.json \
  --max-stories 1 \
  --max-videos 3 \
  --output runs/sf-coffee-launch \
  --staging ../cdn/staging
```

This writes:

```text
../cdn/staging/sf-coffee-launch/campaign.json
../cdn/staging/sf-coffee-launch/01-local-moment-hook/{meta.json,script.txt}
../cdn/staging/sf-coffee-launch/02-commuter-craving/{meta.json,script.txt}
../cdn/staging/sf-coffee-launch/03-fan-celebration/{meta.json,script.txt}
```

You can still use the one-shot flow when you do not need a checkpoint:

```bash
viral-local-ads \
  run \
  --campaign examples/new-bigmac-test.txt \
  --market "San Francisco" \
  --mock-news \
  --dry-run \
  --max-stories 1 \
  --max-videos 1 \
  --output runs/one-shot-test
```

## Brand Safety

The generator avoids obviously sensitive news angles by default, including violent crime, death, disaster, lawsuits, politics, health emergencies, and personal tragedy. Before any creative is generated, each raw story is converted into a sanitized story frame/reference that removes publisher logos, private names, famous brands, celebrities, and endorsement-sensitive phrasing. The goal is to borrow local context and timing, not exploit painful events or imply a news subject endorses the advertiser.

## Run Logging

Every CLI command writes a complete local event log to:

```text
runs/<run-name>/logs/ad_gen_events.ndjson
```

When `TINYBIRD_TOKEN` is set, each event is also sent to the Tinybird Events API datasource named by `TINYBIRD_DATASOURCE`. The deployed datasource is defined in `tinybird/datasources/events.datasource`. Events include CLI args, run settings, Nimble requests/responses, outlet/story selection, sanitizer input/output, generated scripts/prompts, brand-safety validation, BFL submit/poll responses, video links, and artifact paths. This can send campaign text, story data, prompts, and provider responses to Tinybird; configure the token only when that data transfer is intended. Remote delivery is best-effort and bounded by a short timeout; local NDJSON remains the source of truth.

Event rows use this shape:

```json
{
  "event_id": "...",
  "timestamp": "2026-09-25T21:47:56.399617+00:00",
  "run_id": "...",
  "command": "generate-ad",
  "stage": "ad_generation",
  "event_type": "output",
  "status": "ok",
  "payload_json": "{...}",
  "context_json": "{...}"
}
```

API keys and tokens are never written to the logs; only key-presence booleans are recorded.

Each command also emits explicit lifecycle events:

```text
run_status.started
run_status.completed
run_status.failed
```

If a run starts but fails before completion, the `run_status.failed` event includes the failed stage, error type, traceback, and a suggested fix. At the beginning of each new command, the CLI checks the previous local run log; if the previous run failed or never reached completion, it prints the suggested fix and logs a `preflight.previous_run.failure_detected` warning event before continuing.

## Campaign Memory And Spend Guards

Separately from the verbose run log, `run`, `generate-video`, and `stage-cdn` keep a compact per-campaign memory in the shared `agent_events` Tinybird datasource (see `../tinybird/README.md`; env `TINYBIRD_API_KEY`, `TINYBIRD_HOST`). One small event per stage: `run_started`, `nimble_query`, `story_ranked`, `script_generated`, `bfl_submit`, `bfl_ready`, `error`, `run_finished`, each with `campaign_id`, `variant_id` where it applies, and `cost_usd` when known (`NIMBLE_QUERY_COST_USD`, `BFL_VIDEO_COST_USD`).

- `--campaign-id` sets the key (default: `LH_CAMPAIGN_ID`, the campaign file stem, or the output folder; `stage-cdn` uses the record id).
- Any exception or non-2xx from Nimble or BFL emits an `error` event with the step and message, marks the run failed in `run_finished`, and halts before further spend. There are no retries and no next variant unless `--continue-on-error` is passed (per-variant BFL steps only; Nimble and brand-guard failures always halt).
- At start the CLI reads prior events for the campaign and skips any variant that already reached `bfl_ready`, so re-runs do not re-spend. Skipped variants get `bfl_job.skipped = true` in `concepts.json`.
- Without `TINYBIRD_API_KEY` nothing is sent, but the guards still apply.

## Current API Notes

- Nimble search uses `POST https://sdk.nimbleway.com/v2/search` with `Authorization: Bearer $NIMBLE_API_KEY`.
- BFL FLUX 3 video uses `POST https://api.bfl.ai/v1/flux-3-video` with `x-key: $BFL_API_KEY`.
- BFL jobs are async: submit, then poll the returned `polling_url`.
- Tinybird logging uses `POST $TINYBIRD_BASE_URL/v0/events?name=$TINYBIRD_DATASOURCE` with `Authorization: Bearer $TINYBIRD_TOKEN`.
