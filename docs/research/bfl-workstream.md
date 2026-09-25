# BFL workstream: 9:16 ad variants from GitHub Actions

Read 25 September 2026 from [docs.bfl.ai](https://docs.bfl.ai) (Markdown mirror `docs.bfl.ml`, live `https://api.bfl.ai/openapi.json`), the [black-forest-labs GitHub org](https://github.com/black-forest-labs), and the event pages ([tokensand.com](https://tokensand.com/horizonagentshack), [Luma](https://luma.com/horizonagentshack)). Model, pricing, async flow, URL expiry, and licensing background is already in the "Black Forest Labs" section of [on-device-game-decisions.md](on-device-game-decisions.md); this note only adds what the Actions pipeline needs and cites that section where it overlaps.

**Short version.** BFL ships an official remote MCP server, an official Python client, and an official agent-skills repo, but none of them is the right tool for a headless GitHub Actions job. Use plain REST: `POST https://api.bfl.ai/v1/flux-3-video` with `"aspect_ratio": "9:16"`, poll `polling_url` to `Ready`, download at once. Let the Cursor agent write a brief; let a deterministic step spend the money.

## 1. MCP server and SDKs

| What | Name / repo | Install | Auth | Fit for Actions |
| --- | --- | --- | --- | --- |
| Official remote MCP server | [FLUX MCP](https://docs.bfl.ai/api_integration/mcp_integration), repo [black-forest-labs/flux-mcp](https://github.com/black-forest-labs/flux-mcp) (MIT), URL `https://mcp.bfl.ai`, listed on the MCP Registry as `io.github.black-forest-labs/flux-mcp` | Cursor: add `{"mcpServers":{"FLUX":{"url":"https://mcp.bfl.ai"}}}` to `.cursor/mcp.json` or `~/.cursor/mcp.json`; Claude Code: `claude mcp add --transport http FLUX https://mcp.bfl.ai`; stdio-only clients: `npx -y mcp-remote https://mcp.bfl.ai` | **OAuth only.** Browser sign-in, pick the billed org, tokens refresh. The docs' own agent prompt says: "Do not complete OAuth through an embedded or automated browser, and never ask me for an API key." | No. No API-key or service-token mode is documented, so it cannot be wired to a repo secret. Tools it exposes: `generate_image`, `generate_video` (1–4 clips, `t2v`/`i2v`/`v2v`, 5–20 s, `9:16` supported, `hd`/`fhd` only), `enhance_video`, `generate_variations`, `vto`, `get_history`, `get_credits`, `list_skills`, `get_skill`. Good for a human on a laptop exploring prompts before the hack loop starts. |
| Official Python client | [black-forest-labs/blackforest](https://github.com/black-forest-labs/blackforest) (Apache 2.0), PyPI `blackforest` 0.1.3 | `pip install blackforest`; `from blackforest import BFLClient`; `BFLClient(api_key=...).generate("flux-pro-1.1", inputs)` | API key | Weak. The README's supported-model list stops at FLUX.1-era endpoints (`flux-pro-1.1`, `flux-kontext-pro`, fill/expand/canny/depth). No `flux-3-video`, no FLUX.2 named. Last push June 2026. Do not build the video path on it. |
| Official agent skills | [black-forest-labs/skills](https://github.com/black-forest-labs/skills) (MIT). Skills: `bfl-api`, `flux-image-best-practices`, `flux-3-video` (router), `flux-3-generate`, `flux-3-product-ads`, `flux-3-prompt-doctor`, `flux-3-cinematic-inserts`, `flux-3-keyframes-continuation`, `flux-3-audio-dialogue`, `flux-3-archival-formats` | `npx skills add black-forest-labs/skills --skill flux-3-video` (or `bfl-api`, `flux-3-product-ads`); also a Claude Code plugin marketplace | None; they are Markdown | Yes, as **prompting guidance for the agent step**, not as a runtime. `flux-3-product-ads` is literally "assemble a finished product ad: voiceover, action-to-word sync, QC gates". `flux-3-generate` documents the exact poll statuses and the `429` semantics used below. |
| TypeScript / other SDKs | None in the org. The `bfl-api` skill ships sample `python-client.py` and `typescript-client.ts` files, which are examples, not packages. | — | — | — |

**Plain REST path (what the pipeline uses).** Base `https://api.bfl.ai` (or `api.eu.bfl.ai` / `api.us.bfl.ai`), header `x-key: $BFL_API_KEY`, `Content-Type: application/json`. Submit returns `{id, polling_url, cost}`; always poll the returned `polling_url` (the docs say this is required on the global endpoint). Poll statuses (from the `StatusResponse` enum in `/v1/get_result`): `Pending`, `Reasoning`, `Generating` (keep polling); `Ready` (done); `Error`, `Request Moderated`, `Content Moderated`, `Task not found` (terminal failures). Key creation: dashboard.bfl.ai → API → Keys → Add Key; it is shown once. Credits: 1 credit = $0.01; `402` when empty; `429` at 24 active tasks.

## 2. Calling it from GitHub Actions

**Secret name.** `BFL_API_KEY`. That is the variable every BFL doc page, skill, and README uses, so keep it verbatim. Set with `gh secret set BFL_API_KEY --repo bourkefloyd/long-horizon-agents-hack`.

**Shape.** A separate workflow, `content-gen.yml`, so the existing reusable `lh-run.yml` (which deliberately exposes only `CURSOR_API_KEY` to the agent step and no other secret) does not change. It runs the deterministic generator against a brief file that the agent produced on the PR branch, uploads the media as an Actions artifact, and commits only the small manifest and images back. Video renders take minutes (BFL says "long clips up to about an hour"), so the job gets a generous timeout and polls at 6 s, the interval the `flux-3-generate` skill recommends.

### Minimal curl (one 9:16 draft video)

Copied from the video quickstart and the image-generation polling loop, with the 9:16 fields from the API reference added.

```bash
# requires: curl, jq; env: BFL_API_KEY
submit=$(curl -s -X POST https://api.bfl.ai/v1/flux-3-video \
  -H "x-key: $BFL_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "mode": "t2v",
    "prompt": "Vertical phone-framed ad: a runner laces neon shoes at dawn on a wet street, camera pushes in, upbeat percussion, title \"Run Further\" in bold white type in the top third.",
    "aspect_ratio": "9:16",
    "duration": 8,
    "resolution": "hd",
    "generate_audio": true,
    "draft": true
  }')
echo "$submit"                                   # {"id": "...", "polling_url": "...", "cost": <credits>}
polling_url=$(jq -r .polling_url <<< "$submit")

while true; do
  sleep 6
  result=$(curl -s "$polling_url" -H "x-key: $BFL_API_KEY")
  status=$(jq -r .status <<< "$result")
  echo "Status: $status"
  case "$status" in
    Ready) break ;;
    Error|"Request Moderated"|"Content Moderated"|"Task not found") echo "$result"; exit 1 ;;
  esac
done

url=$(jq -r '.result.sample // .result.samples[0]' <<< "$result")
curl -sL -o hero-a.mp4 "$url"                    # signed URL: ~2 h for video, 10 min for images
```

For a 9:16 **image** end card, swap the endpoint and body: `POST /v1/flux-2-pro` with `{"prompt": "...", "width": 1080, "height": 1920, "output_format": "jpeg"}` (the schema only constrains `width`/`height` to a minimum of 64; the docs' own portrait example is 1440 × 2048). Same poll loop; download within 10 minutes.

### Runnable Python generator (stdlib only)

`bfl_generate.py` reads a brief with N variants, submits each, polls, downloads every returned sample, and writes `manifest.json` with the task id, quoted and settled cost in credits, seed, and file paths. It was exercised end-to-end against a local mock of the submit → `Pending` → `Generating` → `Ready` → signed-URL flow; every field in the sample brief was checked against the live `openapi.json` schemas (`Flux3VideoT2VInputs`, `Flux2Inputs`; both reject unknown fields with `422`).

```python
#!/usr/bin/env python3
"""Render every variant in a brief through the BFL API, then download the results.
brief.json: {"variants": [{"id": "...", "endpoint": "flux-3-video"|"flux-2-pro", "body": {...}}]}
Bodies are sent verbatim; only use fields from the BFL API reference (schema is strict, 422 otherwise)."""
import json, os, sys, time, urllib.parse, urllib.request

API = os.environ.get("BFL_API_BASE", "https://api.bfl.ai")
KEY = os.environ["BFL_API_KEY"]
POLL_SECONDS = float(os.environ.get("BFL_POLL_SECONDS", "6"))
MAX_WAIT_SECONDS = float(os.environ.get("BFL_MAX_WAIT_SECONDS", "3600"))
TERMINAL_FAIL = {"Error", "Request Moderated", "Content Moderated", "Task not found", "Failed"}

def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"x-key": KEY, "Content-Type": "application/json", "accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def submit(endpoint, body):
    for attempt in range(20):
        try:
            return call("POST", f"{API}/v1/{endpoint}", body)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(30); continue          # concurrency full; no task created
            if e.code == 503: time.sleep(10 * (attempt + 1)); continue
            print(e.read().decode(), file=sys.stderr); raise
    raise SystemExit("submit: gave up after repeated 429/503")

def poll(polling_url):
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            r = call("GET", polling_url)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503): time.sleep(30); continue    # task exists; never resubmit
            raise
        status = r.get("status")
        if status == "Ready": return r
        if status in TERMINAL_FAIL: raise SystemExit(f"task failed: {status}: {json.dumps(r)[:500]}")
    raise SystemExit("poll: timed out")

def result_urls(result):
    # Docs show result.sample; the flux-3-generate skill says video may arrive as result.samples (list).
    urls = [u for u in result.get("samples", []) if isinstance(u, str)] if isinstance(result.get("samples"), list) else []
    if isinstance(result.get("sample"), str) and result["sample"] not in urls: urls.append(result["sample"])
    return urls

def download(url, path):
    with urllib.request.urlopen(url, timeout=300) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20): f.write(chunk)

def main(brief_path, out_dir):
    brief = json.load(open(brief_path)); os.makedirs(out_dir, exist_ok=True); manifest = []
    for v in brief["variants"]:
        sub = submit(v["endpoint"], v["body"])
        print(f"[{v['id']}] submitted id={sub['id']} quoted_cost_credits={sub.get('cost')}")
        res = poll(sub["polling_url"]); result = res.get("result") or {}
        urls = result_urls(result)
        if not urls: raise SystemExit(f"[{v['id']}] Ready but no sample URL: {json.dumps(res)[:500]}")
        files = []
        for i, u in enumerate(urls):
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or (".mp4" if "video" in v["endpoint"] else ".jpg")
            path = os.path.join(out_dir, f"{v['id']}{'' if i == 0 else f'-{i}'}{ext}")
            download(u, path); files.append({"path": path, "bytes": os.path.getsize(path)})
        manifest.append({"id": v["id"], "endpoint": v["endpoint"], "task_id": sub["id"],
                         "settled_cost_credits": res.get("cost"), "seed": result.get("seed"),
                         "body": v["body"], "files": files, "draft_caches": result.get("draft_caches")})
        print(f"[{v['id']}] ready -> {[f['path'] for f in files]} settled_cost_credits={res.get('cost')}")
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variants": manifest}, f, indent=2)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "brief.json", sys.argv[2] if len(sys.argv) > 2 else "out")
```

Sample `brief.json` (both bodies validated against the live schema):

```json
{
  "campaign": "2026-09-26",
  "variants": [
    { "id": "hero-a", "endpoint": "flux-3-video",
      "body": { "mode": "t2v",
                "prompt": "Vertical phone-framed ad. A runner laces up neon shoes at dawn on a wet city street, camera pushes in, upbeat percussion, on-screen title \"Run Further\" in bold white sans-serif at the top third.",
                "aspect_ratio": "9:16", "duration": 8, "resolution": "hd", "generate_audio": true, "draft": true } },
    { "id": "endcard-a", "endpoint": "flux-2-pro",
      "body": { "prompt": "Vertical mobile ad end card, neon running shoe on dark wet asphalt, bold white title \"Run Further\", a \"Download now\" pill at the bottom, #39FF14 accent.",
                "width": 1080, "height": 1920, "output_format": "jpeg" } }
  ]
}
```

### Workflow: `.github/workflows/content-gen.yml`

```yaml
name: Content generation (BFL)

on:
  workflow_dispatch:
    inputs:
      ref:
        description: "Branch holding .lh/content/brief.json (usually the lh/... PR branch)"
        required: true
        type: string
  # Optional: chain automatically after the agent run finishes.
  # workflow_run:
  #   workflows: ["LH web", "LH agents"]
  #   types: [completed]

permissions:
  contents: write

jobs:
  render:
    runs-on: ubuntu-latest
    timeout-minutes: 90            # full-quality FLUX 3 renders take minutes each
    concurrency:
      group: content-gen-${{ inputs.ref }}
      cancel-in-progress: false    # cancelling mid-poll wastes paid renders
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.ref }}

      - name: Render variants from the agent's brief
        env:
          BFL_API_KEY: ${{ secrets.BFL_API_KEY }}
        run: |
          test -f .lh/content/brief.json || { echo "::error::no brief on this branch"; exit 1; }
          python3 .lh/bin/bfl_generate.py .lh/content/brief.json "$RUNNER_TEMP/out"
          cat "$RUNNER_TEMP/out/manifest.json"

      - name: Upload media as an artifact (video stays out of git)
        uses: actions/upload-artifact@v4
        with:
          name: content-${{ github.run_id }}
          path: ${{ runner.temp }}/out
          retention-days: 14

      - name: Commit manifest and images (deterministic)
        run: |
          mkdir -p .lh/content/out
          cp "$RUNNER_TEMP"/out/manifest.json .lh/content/out/
          find "$RUNNER_TEMP/out" -type f \( -name '*.jpeg' -o -name '*.jpg' -o -name '*.png' -o -name '*.webp' \) -exec cp {} .lh/content/out/ \;
          git config user.name "lh-bot"
          git config user.email "lh-bot@users.noreply.github.com"
          git add .lh/content/out
          git diff --cached --quiet && { echo "nothing to commit"; exit 0; }
          git commit -m "content: rendered $(jq '.variants | length' .lh/content/out/manifest.json) variants (run ${{ github.run_id }})" \
                     -m "artifact: content-${{ github.run_id }}"
          git push origin "HEAD:${{ inputs.ref }}"
```

Notes on the job:

- The signed `result.sample` URL is downloaded inside the same step that saw `Ready`, so the 10-minute (image) and ~2-hour (video) windows are never a concern. The `flux-3-generate` skill adds that the `se=` query parameter on the URL is the authoritative expiry, and that its authors observed roughly one hour in practice, so do not park URLs between steps.
- MP4s go to the Actions artifact, not git. If the demo needs them in the repo, use Git LFS or commit only the winner. Images and the manifest are small enough to commit.
- Rate limit: 24 active tasks per org. The script serialises variants, which stays well under it. Parallelise up to ~8 with a thread pool if the day's batch grows, and keep the `429` handling (submit `429` = nothing was created, retry; poll `429` = task exists, back off).
- Cost tracking for free: the submit response carries `cost` (quoted credits) and the `Ready` response carries settled `cost`. The manifest records both, so the next day's agent run can see yesterday's spend without a billing API call.
- BFL also supports `webhook_url`/`webhook_secret` on the image endpoints (not in the `flux-3-video` schema). Actions has no inbound URL, so polling is the right fit here.

## 3. Parameters for 9:16 mobile video and cost per variant

From the [video page](https://docs.bfl.ai/flux_3/flux3_video) and `openapi.json`:

| Field | Values | Note |
| --- | --- | --- |
| `aspect_ratio` | `auto` (default), `21:9`, `2:1`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16`; the OpenAPI enum also lists `9:21` (not on the docs page) | Use `9:16`. "X by Y as parameter" maps to this enum on video; arbitrary ratios are not accepted, so pick the closest and crop server-side if a placement needs an exact size. |
| `duration` | integer 5–20 s, or `auto` (default). `v2v` is 5–15 s. | 6–10 s fits a vertical ad. |
| `resolution` | `hd` (default), `fhd`, `qhd`, `uhd` | 9:16 delivered sizes: `hd` 704 × 1280, `fhd` 1088 × 1920, `qhd` 1440 × 2560, `uhd` 2176 × 3840. Dimensions are multiples of 32, so `fhd` is 1088 wide, not 1080; crop if a network requires exactly 1080 × 1920. The upsampled classes are the same shot as `hd`, only larger. |
| `generate_audio` | bool, default `true` | Keep on; the ad's VO and SFX come from the same call. |
| `draft` | bool, default `false` | `true` renders a fast `hd` preview plus a `draft_cache`; `mode: "draft_enhance"` with that cache re-renders the identical shot at full quality (default `fhd`). Drafts reject any resolution other than `hd`. |
| `mode` | `t2v`, `i2v` (+`keyframes`), `v2v` (+`start_video`), `draft_enhance` (+`draft_cache`) | `i2v` from a brand still keeps product identity across variants; `keyframes` takes a URL or base64, one image, `[start, end]`, or up to ten `[seconds, image]` pairs. |
| `safety_tolerance` | 0–4, default 2 | Ads with people: leave at 2. |
| `version` | `latest` | — |
| Output | 24 fps MP4, audio muxed | Result URL expires ~2 h after `Ready`. |

**Cost per 9:16 variant** at the published per-second rates ([pricing](https://docs.bfl.ai/quick_start/pricing)): `t2v`/`i2v` $0.17/s `hd`, $0.29/s `fhd`, $0.40/s `qhd`, $0.80/s `uhd`, draft $0.06/s; `v2v` $0.41 / $0.53 / $0.65 / $0.95 / draft $0.12.

| Variant | 5 s | 8 s | 10 s | 15 s |
| --- | --- | --- | --- | --- |
| Draft (`hd` preview) | $0.30 | $0.48 | $0.60 | $0.90 |
| Full `hd` 704 × 1280 | $0.85 | $1.36 | $1.70 | $2.55 |
| Full `fhd` 1088 × 1920 | $1.45 | $2.32 | $2.90 | $4.35 |
| Full `qhd` 1440 × 2560 | $2.00 | $3.20 | $4.00 | $6.00 |
| `v2v` continuation `hd` | $2.05 | $3.28 | $4.10 | (max 15 s) $6.15 |

Images for end cards and thumbnails, FLUX.2 megapixel pricing: `flux-2-pro` from $0.03 (first MP 3¢, +1.5¢/MP), so a 1080 × 1920 card (2.07 MP) is about $0.046; `flux-2-klein-4b` from $0.014 (+0.1¢/MP), about $0.015 for the same size; `flux-2-flex` (typography) from $0.05; `flux-2-max` from $0.07. Video edit (`/v1/flux-tools/video-edit-v1`) is $0.03/s of output.

Worked day: 8 draft variants × 8 s ($3.84) + 2 winners enhanced at `fhd` 8 s (~$4.64, assuming `draft_enhance` bills at the full-render rate; the pricing page does not list it separately, so read the `cost` field on submit) + 8 `flux-2-pro` end cards ($0.37) ≈ **$9 per day of content**. A $20 top-up covers the hack.

## 4. Where BFL sits relative to the Cursor agent step

**Recommendation: the agent writes the brief; a deterministic step spends the credits.** Do not let `agent -p --force` call BFL directly.

Reasons, in order of weight:

1. **Secrets boundary already exists.** `lh-run.yml` gives the agent step only `CURSOR_API_KEY` and no git credentials, on purpose. Handing it `BFL_API_KEY` would make a prompt-injected or looping agent able to spend real money, and the FLUX MCP server offers no headless auth anyway (browser OAuth only, see §1).
2. **Latency does not belong in an LLM turn.** A full render is minutes; BFL warns "long clips up to about an hour". Polling from inside an agent burns tokens, risks the CLI's own timeouts, and produces nothing the agent can judge (it cannot watch the MP4). A `python3` step polls for free.
3. **Idempotency and cost control.** A deterministic step can enforce a per-run credit cap, dedupe by brief hash, record quoted vs settled `cost`, retry `429`/`503` correctly, and never double-submit. The `flux-3-generate` skill's warning that a poll-`429` resubmit "pays for a second render" is exactly the mistake an agent will make.
4. **It matches the Cursor docs' "restricted autonomy" pattern** already used by `lh-run.yml`: agent edits files, CI does the side effects.
5. **The state file stays honest.** The agent's long-horizon memory (`.lh/content/state.md`) should hold *what to make and why* (hypotheses, last results, which variant won); the manifest written by CI holds *what was made and what it cost*. Merging the two would bloat state with URLs that expire in two hours.

How it plugs in:

- Add a third target, `content`, under `.lh/` with `prompt.md`, `state.md`, `checks.sh`, exactly as `web` and `agents`. `prompt.md` instructs the agent to read `state.md`, the last manifest, and the previous day's signals (whatever the Nimble/Tinybird workstream publishes into the repo), then rewrite `.lh/content/brief.json` with N variants that each change one dimension (hook, product angle, colour, VO line) so the A/B test is interpretable, plus one duplicated variant for the A/A control.
- `checks.sh` for `content` validates the brief deterministically: parses as JSON, every `body` only uses allowed keys, `aspect_ratio` is `9:16` unless the brief says otherwise, `duration` is 5–20, drafts are `hd`, total quoted cost from a local rate table is under the day's cap. That is the gate before CI spends anything.
- `content-gen.yml` (above) runs after the agent's PR branch exists, renders, uploads, commits the manifest, and the next agent run reads the manifest.
- Give the agent BFL's own prompting guidance by vendoring `skills/flux-3-product-ads`, `flux-3-audio-dialogue`, and `flux-image-best-practices` from [black-forest-labs/skills](https://github.com/black-forest-labs/skills) into `.cursor/skills/` (or paste their `SKILL.md` into `prompt.md`). MIT licensed.
- If a human wants to explore prompts interactively before the loop starts, the FLUX MCP server in Cursor desktop (OAuth) is the right tool; the CI path stays REST.

## 5. Hackathon credits, keys, or MCP offer

Neither event page says anything about BFL credits, keys, or an MCP offer. [tokensand.com/horizonagentshack](https://tokensand.com/horizonagentshack) lists schedule and submission rules only. [luma.com/horizonagentshack](https://luma.com/horizonagentshack) lists Black Forest Labs among five backers ("Frontier AI for visual intelligence") and names Frederic Boesel (Founding Member, BFL) as speaker and judge, but publishes no credit, promo code, or key process. A web search found no public announcement either. Plan on a self-funded key: create an account at dashboard.bfl.ai, add $10–20 (BFL's own suggestion for experimenting), create a project-scoped key, and ask Frederic Boesel in person whether an event credit exists.

## Aayush: content generation, one-day milestones

Times are Pacific and follow the event's 11:00 kickoff and 16:30 deadline.

1. **11:00–11:30 — Key and smoke test.** Create the BFL account, add $20 of credits, create a project key, `gh secret set BFL_API_KEY`. Run the curl block in §2 once locally with `"draft": true`, 5 s, 9:16 (about $0.30) and confirm an MP4 downloads. Ask Frederic Boesel about event credits.
2. **11:30–12:15 — Generator in the repo.** Commit `.lh/bin/bfl_generate.py` and `.github/workflows/content-gen.yml` from §2. Dispatch it against a hand-written `.lh/content/brief.json` with one draft video and one `flux-2-pro` end card. Success: artifact contains both files, `manifest.json` is committed, settled cost visible in the log.
3. **12:15–13:00 — `content` target for the agent.** Add `.lh/content/{prompt.md,state.md,checks.sh}`. `checks.sh` validates the brief and enforces a per-run credit cap (start at 1,000 credits = $10). Vendor the `flux-3-product-ads` and `flux-image-best-practices` skills. Trigger one `lh-run` with `target: content` and confirm the agent rewrites `brief.json` with 4 variants that each change one dimension plus one A/A duplicate, and that `checks.sh` passes.
4. **13:30–14:30 — First real batch.** Run `content-gen.yml` on the agent's brief: 4–6 drafts at 8 s (about $3). Pick winners by eye, add `draft_enhance` entries for two of them at `fhd`, render (about $5). Hand the MP4 artifact and end cards to whoever owns campaign delivery and signal collection.
5. **14:30–15:30 — Close the loop.** Agree the signals file format with the signals workstream (impressions, taps, completion per variant id). Update `prompt.md` so the agent reads yesterday's manifest and signals, keeps the winner as tomorrow's control, and proposes the next variants. Run the loop end to end once: agent → brief → checks → render → manifest → agent.
6. **15:30–16:15 — Demo cut and submission.** Record the Actions run, the brief diff, the manifest with costs, and the 9:16 clips playing on a phone frame. Write the BFL section of the README: REST only, why the agent does not hold the key, cost per day. Freeze at 16:15; submit by 16:30.
7. **Stretch, only if steps 1–5 are green by 15:00.** `i2v` from a fixed brand still for product consistency across variants; `flux-2-flex` for typography-heavy end cards; parallel submits (up to 8) in the generator.
