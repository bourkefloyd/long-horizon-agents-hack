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
4. Turn each story into five ad angles tied back to the campaign script.
5. Convert each angle into a 10-second video commercial script.
6. Optionally submit those scripts/prompts to Black Forest Labs FLUX 3 Video.
7. Save every outlet, story, script, prompt, and generation job as JSON for review and testing.

## Setup

```bash
cd /Users/thomasbarrios/Documents/Codex/2026-09-25/viral-local-ad-generator
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Then edit `.env`:

```bash
NIMBLE_API_KEY=...
BFL_API_KEY=...
```

If Nimble is only available inside Codex via OAuth/MCP, keep using `--mock-news` until we wire this standalone CLI to the MCP client path.

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

The generator avoids obviously sensitive news angles by default, including violent crime, death, disaster, lawsuits, politics, health emergencies, and personal tragedy. The goal is to borrow local context and timing, not exploit painful events or imply a news subject endorses the advertiser.

## Current API Notes

- Nimble search uses `POST https://sdk.nimbleway.com/v2/search` with `Authorization: Bearer $NIMBLE_API_KEY`.
- BFL FLUX 3 video uses `POST https://api.bfl.ai/v1/flux-3-video` with `x-key: $BFL_API_KEY`.
- BFL jobs are async: submit, then poll the returned `polling_url`.
