#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-venusrealm-ai-20260715}"
REGION="${REGION:-asia-south1}"
JOB_NAME="${JOB_NAME:-venusrealm-signal-agent}"
SCHEDULER_NAME="${SCHEDULER_NAME:-venusrealm-signal-agent-every-5m}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short=12 HEAD)}"
LIVE_DELIVERY_APPROVED="${LIVE_DELIVERY_APPROVED:-NO}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command '$1' not found" >&2
    exit 1
  }
}

require_cmd gcloud
require_cmd git

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
if [[ "$ACTIVE_PROJECT" != "$PROJECT_ID" ]]; then
  echo "ERROR: active gcloud project '$ACTIVE_PROJECT' does not match expected '$PROJECT_ID'" >&2
  exit 1
fi

CURRENT_IMAGE="$(gcloud run jobs describe "$JOB_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(spec.template.spec.template.spec.containers[0].image)')"

if [[ -z "$CURRENT_IMAGE" ]]; then
  echo "ERROR: could not read current image for Cloud Run job '$JOB_NAME'" >&2
  exit 1
fi

SCHEDULER_DETAILS="$(gcloud scheduler jobs describe "$SCHEDULER_NAME" \
  --project "$PROJECT_ID" \
  --location "$REGION" \
  --format='yaml(name,state,schedule,timeZone,httpTarget.uri)' 2>/dev/null || true)"

IMAGE_BASE="${CURRENT_IMAGE%@*}"
IMAGE_BASE="${IMAGE_BASE%:*}"
NEW_IMAGE="${IMAGE_BASE}:${IMAGE_TAG}"

echo "Verified project:   $PROJECT_ID"
echo "Verified region:    $REGION"
echo "Verified job:       $JOB_NAME"
echo "Current image:      $CURRENT_IMAGE"
echo "Proposed image:     $NEW_IMAGE"
echo "Scheduler details:"
printf '%s\n' "${SCHEDULER_DETAILS:-UNKNOWN}"

gcloud builds submit . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --config cloudbuild.signal-job.yaml \
  --substitutions "_IMAGE=$NEW_IMAGE"

echo "STAGED_IMAGE=$NEW_IMAGE"

if [[ "$LIVE_DELIVERY_APPROVED" != "YES" ]]; then
  echo "STAGED_ONLY=YES"
  echo "Production activation skipped: Cloud Run update/execution can lead to live Telegram/WhatsApp delivery." >&2
  echo "Set LIVE_DELIVERY_APPROVED=YES only after explicit controlled live-delivery approval." >&2
  exit 0
fi

gcloud run jobs update "$JOB_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$NEW_IMAGE"

gcloud run jobs execute "$JOB_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --wait

gcloud scheduler jobs describe "$SCHEDULER_NAME" \
  --project "$PROJECT_ID" \
  --location "$REGION" \
  --format='yaml(name,state,schedule,timeZone,httpTarget.uri)'

echo "DEPLOYED_IMAGE=$NEW_IMAGE"
echo "SIGNAL_JOB_EXECUTION=SUCCESS"
