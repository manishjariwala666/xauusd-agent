from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_signal_deploy_stages_image_before_live_activation_gate() -> None:
    source = (ROOT / "scripts" / "deploy_signal_cloud_run_job.sh").read_text(
        encoding="utf-8"
    )

    gate = 'if [[ "$LIVE_DELIVERY_APPROVED" != "YES" ]]; then'
    build = "gcloud builds submit ."
    update = 'gcloud run jobs update "$JOB_NAME"'
    execute = 'gcloud run jobs execute "$JOB_NAME"'

    assert 'LIVE_DELIVERY_APPROVED="${LIVE_DELIVERY_APPROVED:-NO}"' in source
    assert gate in source
    assert "STAGED_IMAGE=$NEW_IMAGE" in source
    assert "STAGED_ONLY=YES" in source
    assert "Production activation skipped" in source
    assert source.index(build) < source.index(gate)
    assert source.index(gate) < source.index(update)
    assert source.index(gate) < source.index(execute)
