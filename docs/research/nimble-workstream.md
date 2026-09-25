# Nimble workstream (Thomas): marketing schema, Nimble process, scripts

Scope: use Nimble (nimbleway.com, "Web data your agents can trust") inside the GitHub Actions LH pipeline to pull competitor, trend and audience signals, and turn them into a small marketing schema that feeds vertical-video script generation. Everything below is from [docs.nimbleway.com](https://docs.nimbleway.com), [github.com/Nimbleway](https://github.com/Nimbleway), [nimbleway.com/pricing](https://www.nimbleway.com/pricing), and the two event pages. No invented endpoints; every call is copied from the docs.

## 1. What Nimble offers

Base URL `https://sdk.nimbleway.com`. Auth on every REST call: `Authorization: Bearer $NIMBLE_API_KEY` (key from Settings → API Keys in the Nimble Platform). SDKs read `NIMBLE_API_KEY` automatically. Only successful requests are billed.

| Product | Endpoint / entry point | What it returns | Published price |
| --- | --- | --- | --- |
| Search | `POST /v2/search` (sync) | Live web search; `results[]` of `title, url, description, content, metadata`. Params: `query`, `search_depth` (`lite`/`standard`), `full_content`, `focus` (`general`, `news`, `coding`, `academic`, `shopping`, `social`, `geo`, `location`, or a list of subagent names like `["amazon_serp","reddit_discover_posts"]`), `time_range` (`hour`..`year`) or `start_date`/`end_date`, `include_domains`/`exclude_domains` (max 50), `country`, `locale`, `max_results` (1–100), `output_format`. Focus modes require `search_depth: "lite"`. | lite $1.10/1k, standard $5.00/1k, `full_content` +$1.00/1k URLs |
| SERP | `POST /v2/serp` (+ async, batch) | Structured Google results: `google_search`, `google_aio`, `google_news`, `google_images`, `google_maps_search`/`place`/`reviews`. Entities include `OrganicResult`, `RelatedQuestion`, `RelatedSearch`, `AnswerBox`, `TopStory`, `AIOverview`. Options: `num_results` 1–100, `time`, `device: "mobile"`, `ads_optimization` (more sponsored results; needs JS rendering). SDK/CLI only, not in MCP or skills. | Billed under Extraction Tools, $1.00/1k URLs |
| Extract | `POST /v2/extract` (+ `/extract/async`, `/extract/batch`) | Any URL → `html`, `markdown`, `links`, `headers`, screenshots, network capture; optional `parser` (parsing schema with CSS/XPath/JSON selectors), `render: true` for JS, stealth mode, geo targeting. | $1.00/1k URLs |
| Extract Templates | `POST /v2/extract/templates/run` (+ async, batch); `GET /v2/extract/templates` to list; `GET /v2/extract/templates/{name}` for input/output schema | Nimble-maintained parsers for popular sites. Public catalog today: e-commerce (`amazon_pdp`, `amazon_serp`, `amazon_category`, `walmart_pdp`, `walmart_search`, `target_pdp`, `best_buy_pdp`, `home_depot_pdp`), search (`google_search`, `google_maps_search`, `google_search_aio`), social (`tiktok_account`, `facebook_page`, `youtube_shorts`), LLM answers (`chatgpt`, `gemini`, `perplexity`, `grok`). No Apple App Store or Google Play template is listed. Custom templates can be generated (`POST /v2/extract/templates/generations`, 100/day). | $3.00/1k runs |
| Map / Crawl | `POST /v2/map`, `POST /v2/crawl` | URL discovery; whole-site extraction (async, `crawl_id`). | $1.00/1k URLs |
| Web Search Agents (Agent API v2) | `POST /v2/agents/runs` (one-shot), `POST /v2/agents` (persistent agent with `skill`, `goals`, `sources`, `output_schema`, `effort`), poll `GET /v2/agents/{agent_id}/runs/{run_id}`, fetch `GET .../result`; optional SSE `.../events` | Async research run. Output `type: "text"` or `type: "json"` (when `output_schema` is set) plus a `trust` report: per-claim `confidence`, `reasoning`, `citations[]` with URL and verbatim excerpts. Templates: `business-discovery`, `company-discovery`, `gtm-lead-discovery`, `open-positions-search`, `social-media-monitor`. Result returns 409 while still running, 422 on failure. | Per task by effort: low $0.025 (10–30 s), med $0.10 (1–3 min), high $0.50 (5–15 min, default), x-high $2.00, max custom |
| Media | `POST /v2/media/download` (+ async) | Download images/video/docs to storage. | $2.00/GB |
| Jobs | `/v2/jobs...` | Scheduled template runs delivered to S3/Databricks. | Plan feature |
| Residential proxy | `ip.nimbleway.com:7000` connection string | Geo-targeted IPs. | $5.30/GB |
| MCP server | `https://mcp.nimbleway.com/mcp` (Streamable HTTP; OAuth 2.1 PKCE or `Authorization: Bearer` header) | Tools prefixed `nimble_`: Search, Extract, Map, Crawl, Extract Template, Web Search Agent. SERP, Media, Jobs are SDK/CLI only. | Same API billing |
| SDKs / CLI | `pip install nimble_python`, `npm i @nimble-way/nimble-js`, `go get github.com/Nimbleway/nimble-go`, `npm i -g @nimble-way/nimble-cli` | Python has sync + `AsyncNimble`, typed errors (`RateLimitError` on 429), 2 retries and 3 min timeout by default. | — |
| Plugin / Agent Skills | [Nimbleway/agent-skills](https://github.com/Nimbleway/agent-skills) for Claude Code, Cursor, Codex | Skills incl. a **Marketing** skill (competitor positioning snapshots, delta mode, battlecards) and SEO skill (keyword research). | — |

Free tier and limits as published: **5,000 free requests per month, no credit card** ("Access to all APIs"; docs pricing page phrases it as "5,000 free web pages"). Default rate limit for all accounts: **83 QPS (5,000 QPM)** per API key across drivers `vx6/vx8/vx10`; 429 returns `{"status":"failed","msg":"Rate limit exceeded"}` and responses carry `ratelimit-limit` / `ratelimit-remaining` headers. 402 means trial quota exhausted. Paid plans start at $2,500/mo (Data Services) but PAYG per-request pricing above works without a plan.

## 2. Best fits for the marketing use

Candidate uses and what covers them:

| Need | Nimble tool | Notes |
| --- | --- | --- |
| Competitor ad research | Web Search Agent (research, `output_schema`) + Extract on competitor landing pages | No ad-library template exists; `facebook_page` template gives page info, not ads. SERP `ads_optimization` surfaces Google sponsored results, not Meta/TikTok ads. |
| Trend and hook discovery | Search with `focus: "social"` or `"news"`, `time_range: "day"/"week"`; Extract Templates `tiktok_account`, `youtube_shorts` for a named competitor's short-form output | Search `social` focus is WSA-backed (metadata `agent_name`), returns trending social content. |
| App store listings | Extract (`render: true`, `formats: ["markdown"]` or a `parser`) on the listing URL | No App Store / Play template. Markdown output is enough for an LLM to pull title, subtitle, feature bullets, rating. |
| Review mining | Web Search Agent with `output_schema` (rows: `quote`, `sentiment`, `theme`, `source_url`), or SERP `google_maps_reviews` for local apps | Agent output cites every cell; that is the "trust" story for the demo. |
| Keyword and audience signals | SERP `google_search` (`RelatedQuestion`, `RelatedSearch`, `device: "mobile"`) and Search `lite` | Cheapest signal source ($1/1k). |

**Pick 1: Search API (`POST /v2/search`).** Synchronous, one call, $1.10/1k at `lite`, and it is the only Nimble product whose parameters map directly onto "what is being said about X this week": `time_range`, `focus: "social"|"news"`, `include_domains` (reddit, tiktok, youtube, producthunt), `country`. Perfect for a nightly Actions job: fast enough to finish inside a step, cheap enough to run per audience per day, and the output shape (`title/url/description/content`) is trivially normalized into `hooks[]` and `trend_signals[]`. It fits the long-horizon framing too: the same query set re-run daily gives a delta the agent can reason about without a growing history.

**Pick 2: Web Search Agent (`POST /v2/agents/runs` with `output_schema`).** This is Nimble's differentiator versus a plain scraper: it returns JSON in the exact shape we ask for, and every field comes with citations and a confidence grade. Use it for the slow, expensive signals that only need refreshing every few days: competitor angles (positioning, claims, CTAs across 3–4 competitors), review mining (themes and verbatim complaints), and app-store copy comparison. Because it is async (minutes at `med`/`high`), run it in a separate scheduled job that writes `competitor_angles[]` and `pain_points[]` into the schema, and let the daily Search job fill the fast fields. `agent_name` gives a persistent agent with memory across runs, which is a nice hook for the "agent that improves over days" narrative. Cost: $0.10–0.50 per task.

Why not Extract Templates as a top pick: `tiktok_account` and `youtube_shorts` are useful for pulling a named competitor's recent short-form videos (captions = hooks), but the input parameters must be checked live via `GET /v2/extract/templates/tiktok_account`, they cost 3× per run, and they need a known account handle. Add them on day 2 if time allows.

## 3. Minimal GitHub Actions job

Secret: `NIMBLE_API_KEY` (repo → Settings → Secrets → Actions). The job fetches one source (Search, social focus, last 7 days), normalizes it with `jq` into a small JSON file the LH agent reads, and commits it. Follows the repo's LH rule that only deterministic steps run git.

```yaml
# .github/workflows/nimble-signals.yml
name: Nimble signals
on:
  schedule:
    - cron: "0 13 * * *"   # daily, 06:00 PT
  workflow_dispatch:
    inputs:
      query:
        description: Search query
        default: "habit tracker app tiktok hooks"
permissions:
  contents: write
concurrency: nimble-signals
jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Search Nimble (social focus, last week)
        env:
          NIMBLE_API_KEY: ${{ secrets.NIMBLE_API_KEY }}
          QUERY: ${{ inputs.query || 'habit tracker app tiktok hooks' }}
        run: |
          set -euo pipefail
          mkdir -p .lh/marketing/signals
          curl -sS --fail -X POST 'https://sdk.nimbleway.com/v2/search' \
            --header "Authorization: Bearer $NIMBLE_API_KEY" \
            --header 'Content-Type: application/json' \
            --data-raw "$(jq -n --arg q "$QUERY" '{
              query: $q,
              focus: "social",
              search_depth: "lite",
              time_range: "week",
              max_results: 20,
              country: "US"
            }')" > /tmp/nimble-raw.json
          jq --arg q "$QUERY" --arg d "$(date -u +%F)" '{
            source: "nimble.search",
            query: $q,
            fetched_at: $d,
            request_id: .request_id,
            items: [ .results[] | {
              title, url, snippet: .description,
              agent: (.metadata.agent_name // .metadata.entity_type // null)
            } ]
          }' /tmp/nimble-raw.json > ".lh/marketing/signals/$(date -u +%F).json"
          cp ".lh/marketing/signals/$(date -u +%F).json" .lh/marketing/signals/latest.json
      - name: Commit signals
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add .lh/marketing/signals
          git diff --cached --quiet || git commit -m "signals: nimble search $(date -u +%F)"
          git push
```

Request body, endpoint, headers and parameter names are exactly those on the Search docs page (`query`, `focus`, `search_depth`, `time_range`, `max_results`, `country`). Focus modes only work with `search_depth: "lite"`, and `time_range` cannot be combined with `start_date`/`end_date`.

Python equivalent for the same step (official SDK, from the docs), if the pipeline prefers a script under `scripts/`:

```python
import json, os, datetime
from nimble_python import Nimble

nimble = Nimble(api_key=os.environ["NIMBLE_API_KEY"])
query = os.environ.get("QUERY", "habit tracker app tiktok hooks")
result = nimble.search(query=query, focus="social", search_depth="lite",
                       time_range="week", max_results=20, country="US")
out = {
    "source": "nimble.search", "query": query,
    "fetched_at": datetime.date.today().isoformat(),
    "request_id": result.request_id,
    "items": [{"title": r.title, "url": r.url, "snippet": r.description}
              for r in result.results],
}
os.makedirs(".lh/marketing/signals", exist_ok=True)
json.dump(out, open(".lh/marketing/signals/latest.json", "w"), indent=2)
```

Second job (slow lane, every 3 days or `workflow_dispatch`): the Web Search Agent competitor pass. Same auth. Documented flow is create → poll while `is_active` → fetch `/result`:

```bash
RUN=$(curl -sS --fail -X POST 'https://sdk.nimbleway.com/v2/agents/runs' \
  --header "Authorization: Bearer $NIMBLE_API_KEY" \
  --header 'Content-Type: application/json' \
  --data @agent-request.json)          # {"agent_name": "...", "input": "...", "output_schema": {...}}
RUN_ID=$(echo "$RUN" | jq -r .id); AGENT_ID=$(echo "$RUN" | jq -r .web_search_agent_id)
until [ "$(curl -sS "https://sdk.nimbleway.com/v2/agents/$AGENT_ID/runs/$RUN_ID" \
  --header "Authorization: Bearer $NIMBLE_API_KEY" | jq -r .is_active)" = "false" ]; do sleep 15; done
curl -sS "https://sdk.nimbleway.com/v2/agents/$AGENT_ID/runs/$RUN_ID/result" \
  --header "Authorization: Bearer $NIMBLE_API_KEY" > .lh/marketing/signals/competitors.json
```

`agent-request.json` uses `agent_name: "lh-competitor-watch"` (persistent agent, memory across runs), `input` describing the 3 competitors and asking for positioning, claims, CTAs and top review complaints, and an `output_schema` that is a subset of the marketing schema below (object root, `type: ["string","null"]` for nullable fields, no `format`/`pattern` keywords; max depth 5, max 100 properties). Set the job `timeout-minutes: 20`; `high` effort is documented at 5–15 minutes, `med` at 1–3.

## 4. Proposed marketing schema

One file the agent rewrites each cycle: `.lh/marketing/schema.json`. It is the input to script generation and the place where test results feed back. Kept small on purpose; each array is capped so the state never grows unbounded.

```json
{
  "version": 1,
  "product": { "name": "", "one_liner": "", "platforms": ["ios", "android"] },
  "generated_at": "2026-09-25",
  "audience": {
    "segment": "",
    "pains": ["", ""],
    "desires": ["", ""],
    "language": ["", ""]
  },
  "hooks": [
    { "id": "h1", "text": "", "type": "question|contrast|proof|curiosity", "source_url": "", "confidence": "high|medium|low" }
  ],
  "claims": [
    { "id": "c1", "text": "", "evidence_url": "", "confidence": "high|medium|low" }
  ],
  "competitor_angles": [
    { "competitor": "", "positioning": "", "cta": "", "weakness": "", "source_url": "" }
  ],
  "script_beats": [
    { "beat": "hook", "seconds": 2, "text": "" },
    { "beat": "problem", "seconds": 4, "text": "" },
    { "beat": "solution", "seconds": 6, "text": "" },
    { "beat": "proof", "seconds": 4, "text": "" },
    { "beat": "cta", "seconds": 2, "text": "" }
  ],
  "cta": { "text": "", "destination": "app_store|play_store|landing" },
  "test_plan": {
    "variables": ["hook", "cta"],
    "variants": [ { "id": "v1", "hook": "h1", "cta": "c1" } ],
    "control": "v1"
  },
  "signals_used": [ ".lh/marketing/signals/2026-09-25.json", ".lh/marketing/signals/competitors.json" ]
}
```

Rules for Thomas's process: `hooks`, `claims`, `competitor_angles` carry `source_url` and `confidence` copied from Nimble (Search gives URLs; Web Search Agent gives per-claim `confidence` and citations), so every line in a script is traceable. Caps: 8 hooks, 5 claims, 4 competitor angles, 5 beats. `script_beats` is the direct input to the video generation step (5 beats ≈ 15–20 s vertical). `test_plan.variants` is what the campaign runner reads to build A/B (different `hook`) and A/A (same hook twice) arms; results write back as `hooks[].performance` on the next cycle, then the agent prunes losers.

## 5. Hackathon credits or keys

Neither event page mentions credits or API keys. [tokensand.com/horizonagentshack](https://tokensand.com/horizonagentshack) lists only schedule and submission rules (public GitHub repo, demo video, tools used, team contacts; deadline 4:30 PM PT). [luma.com/horizonagentshack](https://luma.com/horizonagentshack) lists Nimble as a sponsor ("Web data your agents can trust") and names **Yaniv Markovski, Head of Ecosystem Engineering @ Nimble**, as speaker and judge, with no credit offer in the text. A web search for a Nimble hackathon or startup credit program found nothing published.

Practical path: sign up at the Nimble Platform for the **free 5,000 requests/month, no card** tier (enough for the whole day at `lite` search plus a handful of agent runs), and ask Yaniv on site whether sponsor credits or an uplift exist. Store the key as the `NIMBLE_API_KEY` Actions secret; the docs recommend one key per project so it can be revoked after the event.

## One-day milestones for Thomas

1. **Key and smoke test.** Sign up, create `NIMBLE_API_KEY`, add as repo secret. Run the curl Search call locally with `focus: "social"`; confirm 200 and `results[]`. Check `GET /v2/extract/templates/tiktok_account` to record its input params for later.
2. **Signals job green.** Add `.github/workflows/nimble-signals.yml` as above; `workflow_dispatch` once; confirm `.lh/marketing/signals/latest.json` committed. Three queries max (product category, competitor name, "why I deleted X app").
3. **Schema v1 committed.** Write `.lh/marketing/schema.json` with the shape in section 4, filled by hand for the demo product, plus a 20-line `prompt.md` telling the LH agent how to turn `signals/*.json` into `hooks`, `claims`, `script_beats`.
4. **Competitor pass.** One Web Search Agent run at `med` effort with `output_schema` limited to `competitor_angles` and `pains`; save the trust report; paste two cited claims into the schema. This is the "trusted web data" moment for the demo.
5. **First scripts.** Agent run produces 3 variants (2 hooks + 1 A/A duplicate) from the schema; hand them to the video generation workstream in the `script_beats` format.
6. **Feedback loop stub.** Define where campaign results land (`hooks[].performance`) and the prune rule (drop hooks below control after N impressions). Even mocked numbers close the loop for the demo video.
7. **Later, if time:** Meta campaign generation reading `test_plan.variants`; `tiktok_account` / `youtube_shorts` templates for a named competitor's captions; Nimble MCP server for interactive research in Cursor.

## Sources

- Docs home and index: https://docs.nimbleway.com, https://docs.nimbleway.com/llms.txt
- Quickstart (auth, SDKs, every product): https://docs.nimbleway.com/nimble-sdk/getting-started/quickstart
- Search guide and OpenAPI: https://docs.nimbleway.com/nimble-sdk/web-tools/search, https://docs.nimbleway.com/api-reference/search/search
- SERP: https://docs.nimbleway.com/nimble-sdk/web-tools/serp
- Extract Templates and Gallery: https://docs.nimbleway.com/nimble-sdk/web-tools/extract/template, https://docs.nimbleway.com/nimble-sdk/agentic/agent-gallery
- Web Search Agents quickstart and output schema limits: https://docs.nimbleway.com/nimble-sdk/web-search-agents/quickstart, https://docs.nimbleway.com/nimble-sdk/web-search-agents/use-cases/dataset-building
- MCP server and integration paths: https://docs.nimbleway.com/integrations/mcp-server/mcp-server, https://docs.nimbleway.com/integrations/overview
- Marketing skill: https://docs.nimbleway.com/integrations/agent-skills/web-search-skills/marketing
- Rate limits and status codes: https://docs.nimbleway.com/nimble-sdk/admin/rate-limits
- Pricing: https://www.nimbleway.com/pricing, https://docs.nimbleway.com/nimble-sdk/admin/pricing
- GitHub org: https://github.com/Nimbleway (agent-skills, cookbook, nimble-python, nimble-cli, langchain-nimble)
- Event pages: https://tokensand.com/horizonagentshack, https://luma.com/horizonagentshack
