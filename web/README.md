# Long Horizon campaign console

Next.js operator console for the server-side vertical video campaign loop.

## Run locally

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=https://lh-campaign-service-row663omlq-uc.a.run.app npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app proxies campaign
requests through its own route handlers, avoiding browser CORS coupling.

## Demo feed

Open [`/feed`](http://localhost:3000/feed) for the vertical ad demo. The five
examples are script-backed previews derived from `content/ads/scripts.json`;
the source content describes generated videos but does not include the media
files or stable hosted URLs.

Each visible ad emits one impression per browser session. Script dwell is
treated as a 10-second creative, with q25/q50/q75/complete signals at
2.5/5/7.5/10 seconds and a skip when the ad is left before 2.5 seconds. The
state card reads folded campaign state from the service, so newly accepted
signals appear after the campaign decision step.

## Environment

`NEXT_PUBLIC_API_BASE_URL` is the campaign service origin. For local development,
use:

```bash
NEXT_PUBLIC_API_BASE_URL=https://lh-campaign-service-row663omlq-uc.a.run.app
```

## Deploy

Pushes to `main` that touch `web/**` run `deploy-web.yml`. It builds the
standalone image from `web/Dockerfile`, pushes it to Artifact Registry, and
deploys Cloud Run service `CLOUD_RUN_WEB_SERVICE` (or `lh-web` when unset).

For a local container:
`docker build --build-arg NEXT_PUBLIC_API_BASE_URL=https://lh-campaign-service-row663omlq-uc.a.run.app -t lh-web .`
