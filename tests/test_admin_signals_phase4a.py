"""Fast Phase 4A signal validation and architecture checks."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from services import admin_signals_api, admin_signals_service
from services.admin_signals_api import SignalPayload


ROOT = Path(__file__).resolve().parents[1]


def valid(**changes):
    values = {
        "symbol": "XAUUSD", "direction": "BUY", "entry_price": "2350.123456",
        "stop_loss": "2340", "target_1": "2360", "target_2": "2370",
        "analysis_summary": "Synthetic validation signal.",
    }
    values.update(changes)
    return SignalPayload(**values)


def test_financial_values_use_decimal_and_bounded_precision() -> None:
    payload = valid()
    assert isinstance(payload.entry_price, Decimal)
    with pytest.raises(ValidationError):
        valid(entry_price="2350.1234567")


@pytest.mark.parametrize("changes", [
    {"stop_loss": "2351"}, {"target_1": "2349"}, {"target_1": "2370", "target_2": "2360"},
])
def test_buy_level_validation(changes) -> None:
    with pytest.raises(ValidationError): valid(**changes)


@pytest.mark.parametrize("changes", [
    {"direction": "SELL", "stop_loss": "2340", "target_1": "2330"},
    {"direction": "SELL", "stop_loss": "2360", "target_1": "2365"},
    {"direction": "SELL", "stop_loss": "2360", "target_1": "2330", "target_2": "2340"},
])
def test_sell_level_validation(changes) -> None:
    with pytest.raises(ValidationError): valid(**changes)


def test_scheduling_and_expiry_validation() -> None:
    now = datetime.now(timezone.utc)
    with pytest.raises(ValidationError): valid(publication_status="SCHEDULED")
    with pytest.raises(ValidationError): valid(publication_status="SCHEDULED", scheduled_at=now + timedelta(hours=2), expires_at=now + timedelta(hours=1))


def test_lifecycle_matrix_rejects_unsafe_transitions() -> None:
    assert "PUBLISH" in admin_signals_service.ALLOWED_TRANSITIONS["DRAFT"]
    assert "TARGET_HIT" not in admin_signals_service.ALLOWED_TRANSITIONS["DRAFT"]
    assert "DELETE" not in admin_signals_service.ALLOWED_TRANSITIONS["ACTIVE"]
    assert admin_signals_service.ALLOWED_TRANSITIONS["TRASHED"] == {"RESTORE", "DELETE"}


def test_admin_routes_revalidate_identity_and_sanitize_errors() -> None:
    source = inspect.getsource(admin_signals_api)
    for route in ("/admin/signals", "/duplicate", "/transition"):
        assert route in source
    assert '"trash":"TRASH"' in source and '"restore":"RESTORE"' in source
    assert "_require_bff(secret)" in source
    assert "_require_identity(_bearer_token(authorization))" in source
    assert "Signals service is temporarily unavailable." in source
    assert "LOGGER.exception" in source


def test_bff_requires_csrf_and_has_a_narrow_allowlist() -> None:
    route = (ROOT / "admin-web/app/api/admin/signals/[...path]/route.ts").read_text()
    assert "verifyCsrfToken" in route
    assert "allowedPath" in route
    assert "X-Admin-BFF-Key" in route
    assert "ADMIN_SESSION_COOKIE" in route


def test_public_signal_pages_have_one_h1_and_ordered_headings() -> None:
    index = (ROOT / "public-web/app/signals/page.tsx").read_text()
    detail = (ROOT / "public-web/app/signals/[publicId]/page.tsx").read_text()
    assert index.count("<h1") == 1
    assert detail.count("<h1") == 1
    assert detail.index("<h1") < detail.index("<h2") < detail.index("<h3")
    heading_ids = ["signal-levels", "signal-analysis", "technical-context", "astrology-context", "signal-risk"]
    assert len(heading_ids) == len(set(heading_ids))
    assert all(f'id="{heading_id}"' in detail for heading_id in heading_ids)


def test_public_contract_does_not_select_internal_identity_or_audit_fields() -> None:
    source = inspect.getsource(admin_signals_service.list_public_signals)
    fields = source.split('fields = "', 1)[1].split('"', 1)[0]
    assert "created_by" not in fields
    assert "updated_by" not in fields
    assert "audit" not in fields
    assert "id," not in fields.replace("public_id,", "")
