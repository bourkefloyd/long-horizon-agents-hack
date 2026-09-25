# Long Horizon campaign console

Next.js operator console for the server-side vertical video campaign loop.

## Run locally

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=https://lh-campaign-service-row663omlq-uc.a.run.app npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app proxies campaign
requests through its own route handlers, avoiding browser CORS coupling.

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
