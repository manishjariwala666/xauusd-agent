from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_signal_deploy_requires_explicit_live_delivery_approval() -> None:
    source = (ROOT / "scripts" / "deploy_signal_cloud_run_job.sh").read_text(
        encoding="utf-8"
    )

    gate = 'if [[ "$LIVE_DELIVERY_APPROVED" != "YES" ]]; then'
    build = "gcloud builds submit ."
    update = 'gcloud run jobs update "$JOB_NAME"'
    execute = 'gcloud run jobs execute "$JOB_NAME"'

    assert 'LIVE_DELIVERY_APPROVED="${LIVE_DELIVERY_APPROVED:-NO}"' in source
    assert gate in source
    assert "production signal deployment can cause live Telegram/WhatsApp delivery" in source
    assert source.index(gate) < source.index(build)
    assert source.index(gate) < source.index(update)
    assert source.index(gate) < source.index(execute)
