# Cloud Run service

The FastAPI service keeps raw signals in process, folds fresh events into compact campaign state, and drops stale events at decision time. The store is deliberately replaceable; this slice does not add Firestore or Cloud SQL.

## GitHub configuration

In **Settings → Secrets and variables → Actions**, add these repository variables:

- `GCP_PROJECT_ID`: the Google Cloud project ID shown by `gcloud projects list`.
- `GCP_REGION`: the Cloud Run and Artifact Registry region, for example `us-central1`.
- `CLOUD_RUN_SERVICE`: the service name, for example `campaign-loop`.
- `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`: the runtime service account email printed below.
- `ARTIFACT_REGISTRY_REPOSITORY`: the Docker repository name created below, for example `campaign-services`.
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: the full provider resource name printed by the command below.
- `GCP_SERVICE_ACCOUNT`: the deployer service account email printed below.
- `CLOUD_RUN_PUBLIC` (optional): set to `false` to require authenticated Cloud Run invocations. When unset or any value other than `false`, deploy adds `--allow-unauthenticated` for the hackathon demo.

Workload Identity Federation needs no GitHub secret. As a less secure fallback only, add repository secret `GCP_SA_KEY` containing the complete service-account JSON key. When that fallback is used, omit one or both WIF variables.

## One-time Google Cloud setup

Run the following as a project administrator, changing only the first three values if desired:

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export AR_REPOSITORY="campaign-services"
export DEPLOYER_NAME="github-cloud-run"
export RUNTIME_NAME="campaign-loop-runtime"
export POOL="github"
export PROVIDER="long-horizon-agents-hack"
export GITHUB_REPO="bourkefloyd/long-horizon-agents-hack"

gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  iamcredentials.googleapis.com sts.googleapis.com

gcloud artifacts repositories create "$AR_REPOSITORY" \
  --repository-format=docker --location="$REGION"

gcloud iam service-accounts create "$DEPLOYER_NAME" \
  --display-name="GitHub Cloud Run deployer"
gcloud iam service-accounts create "$RUNTIME_NAME" \
  --display-name="Campaign loop runtime"
export DEPLOYER_SA="${DEPLOYER_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export RUNTIME_SA="${RUNTIME_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role="roles/run.admin"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role="roles/artifactregistry.writer"

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:${DEPLOYER_SA}" \
  --role="roles/iam.serviceAccountUser"

export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
gcloud iam workload-identity-pools create "$POOL" \
  --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL}/attribute.repository/${GITHUB_REPO}"

gcloud iam workload-identity-pools providers describe "$PROVIDER" \
  --location=global --workload-identity-pool="$POOL" --format='value(name)'
echo "$DEPLOYER_SA"
echo "$RUNTIME_SA"
```

Put the last three values in `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, and `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`. The workflow builds in GitHub Actions, pushes to Artifact Registry, and deploys to Cloud Run. By default (`CLOUD_RUN_PUBLIC` unset), the service allows unauthenticated invocation so the browser frontend can reach it.

For the JSON-key fallback, create a key with `gcloud iam service-accounts keys create /tmp/gcp-sa-key.json --iam-account="$DEPLOYER_SA"`, save its full contents as `GCP_SA_KEY`, then securely delete the local file. Prefer WIF because it has no long-lived key.

## Run locally

```bash
cd service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m pytest
uvicorn app.main:app --reload --port 8080
```

Check `http://127.0.0.1:8080/health`; `/healthz` is also available. Signal timestamps must include a timezone, and `POST /campaigns/{id}/decide` accepts an optional `window_hours` query parameter (default `24`).
