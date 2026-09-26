# Tinybird agent event memory

Append-only memory for content-generation agents: every run emits small events
(`run_started`, `nimble_query`, `variant_generated`, `run_finished`, ...) to the
`agent_events` datasource and reads them back per campaign instead of carrying an
ever-growing transcript.

Env vars: `TINYBIRD_API_KEY` (workspace token), `TINYBIRD_HOST` (region API host,
default `https://api.tinybird.co`; `python3 scripts/tb_events.py detect-host` prints the right one).

## Usage

Python (stdlib only, `scripts/tb_events.py`):

```python
from tb_events import emit, read
emit("sf-coffee-launch", "campaign-gen", "variant_generated", {"hook": "..."}, run_id, variant_id="v1", cost_usd=0.03)
rows = read("sf-coffee-launch", since="2026-09-25T00:00:00Z")
```

Node, server-side only (`web/lib/tinybird.ts`):

```ts
import { emit, read } from "@/lib/tinybird";
await emit("sf-coffee-launch", "campaign-gen", "variant_generated", { hook }, runId, "v1", 0.03);
const rows = await read("sf-coffee-launch", "2026-09-25T00:00:00Z");
```

Shell one-liner for an agent run:

```bash
python3 scripts/tb_events.py emit sf-coffee-launch campaign-gen run_started '{"issue": 42}'
```

## Resources

| Resource | Kind | Params |
| --- | --- | --- |
| `agent_events` | datasource, sorted by `(campaign_id, ts)` | — |
| `campaign_events` | endpoint `GET $TINYBIRD_HOST/v0/pipes/campaign_events.json` | `campaign_id` (required), `since`, `agent`, `limit` |
| `campaign_summary` | endpoint `GET $TINYBIRD_HOST/v0/pipes/campaign_summary.json` | `campaign_id` (required) |

The campaign service proxies the first pipe at `GET /campaigns/{id}/events` and
returns `{"configured": false}` when no token is mounted.

## Deploy

`.github/workflows/tinybird-deploy.yml` runs on pushes to `tinybird/**` and on
demand (inputs: `seed` demo events, `sync_gcp_secret` into Secret Manager). It
uses `tb --cloud deploy` and falls back to the Classic REST API via
`scripts/tb_admin.py`.
