#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-}"
REGION="${2:-asia-south1}"
REPO="${3:-manishjariwala666/xauusd-agent}"

if [ -z "$PROJECT_ID" ]; then
  echo "Usage: bash scripts/bootstrap_google_cloud.sh <GCP_PROJECT_ID> [REGION] [OWNER/REPO]" >&2
  exit 2
fi

for command in gcloud gh; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "$command is required." >&2
    exit 2
  fi
done

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
if [ -z "$PROJECT_NUMBER" ]; then
  echo "Unable to resolve Google Cloud project number." >&2
  exit 1
fi

DEPLOYER_NAME="venusrealm-github-deployer"
RUNTIME_NAME="venusrealm-runtime"
DEPLOYER_SA="$DEPLOYER_NAME@$PROJECT_ID.iam.gserviceaccount.com"
RUNTIME_SA="$RUNTIME_NAME@$PROJECT_ID.iam.gserviceaccount.com"
POOL_ID="github"
PROVIDER_ID="xauusd-agent"

gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com serviceusage.googleapis.com run.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com secretmanager.googleapis.com --project "$PROJECT_ID"

if ! gcloud iam service-accounts describe "$DEPLOYER_SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$DEPLOYER_NAME" --display-name="VenusRealm GitHub deployer" --project "$PROJECT_ID"
fi
if ! gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$RUNTIME_NAME" --display-name="VenusRealm Cloud Run runtime" --project "$PROJECT_ID"
fi

if ! gcloud iam workload-identity-pools describe "$POOL_ID" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL_ID" --location=global --display-name="GitHub Actions" --project "$PROJECT_ID"
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" --workload-identity-pool="$POOL_ID" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --workload-identity-pool="$POOL_ID" \
    --location=global \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='$REPO'" \
    --project "$PROJECT_ID"
fi

POOL_NAME="$(gcloud iam workload-identity-pools describe "$POOL_ID" --location=global --project "$PROJECT_ID" --format='value(name)')"
PROVIDER_NAME="$(gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" --workload-identity-pool="$POOL_ID" --location=global --project "$PROJECT_ID" --format='value(name)')"
MEMBER="principalSet://iam.googleapis.com/$POOL_NAME/attribute.repository/$REPO"

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" --project "$PROJECT_ID" --role roles/iam.workloadIdentityUser --member "$MEMBER" >/dev/null

for role in roles/run.admin roles/artifactregistry.admin roles/cloudscheduler.admin roles/secretmanager.admin roles/serviceusage.serviceUsageAdmin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$DEPLOYER_SA" --role "$role" --condition=None >/dev/null
done

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" --project "$PROJECT_ID" --member "serviceAccount:$DEPLOYER_SA" --role roles/iam.serviceAccountUser >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member "serviceAccount:$RUNTIME_SA" --role roles/secretmanager.secretAccessor --condition=None >/dev/null

gh variable set GCP_PROJECT_ID --repo "$REPO" --body "$PROJECT_ID"
gh variable set GCP_REGION --repo "$REPO" --body "$REGION"
gh variable set GCP_ARTIFACT_REPOSITORY --repo "$REPO" --body "venusrealm"
gh variable set GCP_API_SERVICE --repo "$REPO" --body "venusrealm-api"
gh variable set GCP_WORKER_JOB --repo "$REPO" --body "venusrealm-worker"
gh variable set GCP_SCHEDULER_JOB --repo "$REPO" --body "venusrealm-worker-every-minute"
gh variable set GCP_RUNTIME_SERVICE_ACCOUNT --repo "$REPO" --body "$RUNTIME_SA"
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$REPO" --body "$PROVIDER_NAME"
gh variable set GCP_DEPLOYER_SERVICE_ACCOUNT --repo "$REPO" --body "$DEPLOYER_SA"

echo
echo "Google Cloud identity bootstrap complete."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Runtime service account: $RUNTIME_SA"
echo "Workload Identity provider: $PROVIDER_NAME"
echo
echo "NEXT REQUIRED STEP:"
echo "Create Secret Manager secret DATABASE_URL with the VALID production PostgreSQL URL."
echo "Do not reuse the current malformed GitHub DATABASE_URL secret."
echo
echo "Example:"
echo "  printf '%s' '<VALID_POSTGRES_URL>' | gcloud secrets create DATABASE_URL --data-file=- --replication-policy=automatic --project '$PROJECT_ID'"
echo "If DATABASE_URL already exists, use:"
echo "  printf '%s' '<VALID_POSTGRES_URL>' | gcloud secrets versions add DATABASE_URL --data-file=- --project '$PROJECT_ID'"
