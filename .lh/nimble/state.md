# state: nimble

## Goal

Keep Thomas's viral local ad CLI documented and CI-safe: campaign text and media market drive story discovery (mock or Nimble), then bounded review artifacts—trusted story URLs,
brand-safe VideoAdConcept rows—without secrets in output or state.

## Current plan

1. After `/approve`, run `discover-news` once with `--market "San Francisco"`, `--max-stories 1`, no `--mock-news`; key only via env; check `stories.json` URLs and `brand_safe`.
2. Before `viral-local-ad-generator/` edits, mirror checks offline: compileall, mock `run --dry-run` with `examples/new-bigmac-test.txt`, validate `run.json` and duration ≤10.
3. Replace `.lh/owners.json` `nimble` placeholder with Thomas's GitHub login when known so approval issues assign correctly.

## Done

- **Consume:** `--campaign` file; `--market`; `--mock-news`, `--story-*`, or live POST `/v2/search` (Bearer from env); generation uses campaign + `stories.json`; optional `BFL_API_KEY`.
- **Produce:** discovery → `stories.json`, `news.md`; ads → `concepts.json`, `summary.md`; full run → `run.json`; BFL may add `video_links/`, `videos/`.
- **Models:** `NewsStory` (title, url, scores, brand_safe); `VideoAdConcept` (hook, script, video_script, prompts, 9:16, duration_seconds, bfl fields).
- **Pipeline:** `select_stories` + `brand_guard`; sensitive-term filtering in `nimble_client`; CLI commands `run`, `discover-news`, `generate-ad`, `generate-video`.
- Issue #19: re-read core modules; agent ran compileall + mock dry-run; no application code changed.

## Open

- Live Nimble not in deterministic checks; needs one approved `discover-news` smoke with repo secret.
- `.lh/owners.json` nimble is still `REPLACE_WITH_THOMAS_GITHUB_LOGIN`.

## Decisions

- Agent runs avoid git/gh/bash; CI runs `checks.sh`; agents may use Python compileall and mock CLI when validating fixes.
- Approval covers one live discover call: no BFL, no schema change, no publishing; never log keys or env dumps.
- `approval-request.md` stripped before commit; first line is the approval issue title.

## Dropped

- Re-adding identical I/O bullets each run once Done captures contracts; keep state compact.
- `viral-local-ad-generator/runs/` sample folders stay reference data, not agent artifacts.
