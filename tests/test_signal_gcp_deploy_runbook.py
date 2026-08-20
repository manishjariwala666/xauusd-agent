from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_signal_gcp_deploy_uses_verified_existing_job_and_image_path() -> None:
    script = (ROOT / "scripts" / "deploy_signal_cloud_run_job.sh").read_text(
        encoding="utf-8"
    )
    cloudbuild = (ROOT / "cloudbuild.signal-job.yaml").read_text(encoding="utf-8")

    assert 'PROJECT_ID="${PROJECT_ID:-venusrealm-ai-20260715}"' in script
    assert 'REGION="${REGION:-asia-south1}"' in script
    assert 'JOB_NAME="${JOB_NAME:-venusrealm-signal-agent}"' in script
    assert 'SCHEDULER_NAME="${SCHEDULER_NAME:-venusrealm-signal-agent-every-5m}"' in script
    assert 'gcloud run jobs describe "$JOB_NAME"' in script
    assert 'CURRENT_IMAGE=' in script
    assert 'IMAGE_BASE="${CURRENT_IMAGE%@*}"' in script
    assert '--config cloudbuild.signal-job.yaml' in script
    assert 'gcloud run jobs update "$JOB_NAME"' in script
    assert 'gcloud run jobs execute "$JOB_NAME"' in script
    assert 'gcloud scheduler jobs describe "$SCHEDULER_NAME"' in script
    assert 'Dockerfile.signal-job' in cloudbuild
    assert 'Dockerfile\n' not in cloudbuild
