# Ad asset CDN

Ad creatives live in the public-read, uniform-access GCS bucket
`lh-ads-assets-205515555985` in `us-central1`. The current delivery URL is
`https://storage.googleapis.com/lh-ads-assets-205515555985/`; the ad database is
[manifest.json](https://storage.googleapis.com/lh-ads-assets-205515555985/manifest.json)
and its contract is [`cdn/manifest.schema.json`](../cdn/manifest.schema.json).
Hashed creative objects are cached for one year as immutable, while the manifest
is cached for 60 seconds. Browser `GET` and `HEAD` requests are allowed by the
bucket CORS policy.

Objects use this layout:

```text
ads/<campaign_id>/<variant_id>/<name>.<content-hash>.<extension>
manifest.json
manifest.schema.json
```

## Publish an agent output

Create one folder at `cdn/staging/<campaign>/<variant>/`. Put the generated
media in that folder and add a `meta.json`. `media_file` is required;
`poster_file` is optional; `script_file` reads a text asset into the manifest's
`script` field. The directory names become `campaign_id` and `variant_id`.

```json
{
  "id": "launch-fast-hook",
  "hook": "Your ads should learn overnight.",
  "cta": "See the winner",
  "media_type": "video",
  "media_file": "creative.mp4",
  "poster_file": "poster.png",
  "duration_s": 15,
  "aspect": "9:16",
  "targeting": {
    "audience": ["founders"],
    "geo": ["US"],
    "weight": 1,
    "active": true
  },
  "source": {
    "agent": "bfl-video",
    "generated_at": "2026-09-25T20:00:00Z",
    "brief_ref": "briefs/launch.md"
  }
}
```

Commit the staging folder and merge it to `main`. The `Publish ad assets`
workflow authenticates with Workload Identity Federation, hashes every staged
asset into its object name, uploads it with immutable caching, validates the
merged manifest against the JSON Schema, and replaces any prior manifest entry
with the same `id`. This is the path for Thomas's Nimble scripts, BFL video
outputs, and later playable bundles.

To publish from a trusted machine instead, use Application Default Credentials
or point `GOOGLE_APPLICATION_CREDENTIALS` at a deployer key:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r cdn/requirements.txt
ADS_BUCKET=lh-ads-assets-205515555985 python cdn/publish.py
```

The GitHub deployer
`lh-github-deployer@long-horizon-agents-hack.iam.gserviceaccount.com` has
`roles/storage.objectAdmin` on this bucket only. It does not need project-wide
storage administration.

## Site consumption

`web/lib/ads.ts` fetches `NEXT_PUBLIC_ADS_MANIFEST_URL`, defaulting to the live
manifest above. `pickAd(manifest, context)` filters inactive or unmatched ads
and performs a weighted pick. The Cloud Run web build receives the URL from the
repository variable `ADS_MANIFEST_URL`.

## Upgrade paths

For a custom domain, TLS, edge caching, and cache invalidation, put this bucket
behind an external Application Load Balancer with a backend bucket, enable
Cloud CDN on that backend, and point the manifest environment variable at the
new hostname; content-hashed object URLs can remain immutable. If targeting
needs queries, transactions, or an editor workflow, replace `manifest.json`
with Firestore, or use a Notion database with the same columns and a small sync
job that emits the same manifest contract; the site helper can keep consuming
that contract while the source of truth changes.
