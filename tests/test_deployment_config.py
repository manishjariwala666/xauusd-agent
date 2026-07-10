"""Deployment configuration invariants that must not regress."""

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    with (ROOT / name).open("rb") as file:
        return tomllib.load(file)


def test_railway_api_uses_injected_port_and_healthcheck() -> None:
    config = _load("railway.toml")
    deploy = config["deploy"]
    assert "$PORT" in deploy["startCommand"]
    assert deploy["healthcheckPath"] == "/health"
    assert deploy["restartPolicyType"] == "ON_FAILURE"


def test_railway_worker_uses_dedicated_process() -> None:
    config = _load("railway.worker.toml")
    deploy = config["deploy"]
    assert deploy["startCommand"] == "python worker.py"
    assert "healthcheckPath" not in deploy


def test_environment_template_contains_all_config_keys() -> None:
    template = (ROOT / ".env.example").read_text(encoding="utf-8")
    required = {
        "DATABASE_URL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "JWT_SECRET",
        "APP_BASE_URL",
        "BACKEND_BASE_URL",
        "TELEGRAM_WEBHOOK_SECRET",
        "MASTER_AI_TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ADMIN_USER_ID",
        "TELEGRAM_ADMIN_USER_IDS",
        "MASTER_AI_ALLOW_NATURAL_COMMANDS",
        "WHATSAPP_ACCESS_TOKEN",
        "META_APP_SECRET",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_SHEET_ID",
    }
    keys = {
        line.split("=", 1)[0]
        for line in template.splitlines()
        if line and not line.startswith("#") and "=" in line
    }
    assert required <= keys


def test_scheduled_agent_requires_runtime_validation_gate() -> None:
    workflow = (ROOT / ".github/workflows/auto_news.yml").read_text(
        encoding="utf-8"
    )

    assert "id: validate_runtime" in workflow
    assert (
        "steps.preflight.outputs.ready == 'true' && "
        "steps.validate_runtime.outputs.ready == 'true'"
    ) in workflow
    assert "JWT_SECRET must contain at least 32 characters." in workflow
    assert "TELEGRAM_BOT_TOKEN must be a BotFather token" in workflow
    assert "GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}" in workflow
    assert "check_secret GOOGLE_SHEET_ID" in workflow
