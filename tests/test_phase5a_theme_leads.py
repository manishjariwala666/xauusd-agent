from pathlib import Path

import pytest
from pydantic import ValidationError

from services.admin_leads_api import PublicLeadPayload
from services.admin_leads_service import _url

ROOT = Path(__file__).resolve().parents[1]


def valid_payload(**changes):
    values = {"name":"Test Operator","business_email":"operator@example.test","country":"India","business_type":"SaaS","requested_services":["n8n Workflows"],"project_description":"A bounded integration test project description.","primary_problem":"Manual operational handoffs.","expected_outcome":"A reviewed and observable workflow.","budget_range":"Not decided","preferred_timeline":"Flexible / planning","preferred_contact_method":"EMAIL","consent":True}
    values.update(changes); return PublicLeadPayload(**values)


def test_public_payload_has_bounded_validation():
    assert valid_payload().consent is True
    with pytest.raises(ValidationError): valid_payload(business_email="not-an-email", project_description="short")
    with pytest.raises(ValidationError): valid_payload(requested_services=[])


@pytest.mark.parametrize("value", ["javascript:alert(1)", "data:text/plain,test", "http://example.test", "https://user:pass@example.test"])
def test_unsafe_website_urls_are_rejected(value):
    with pytest.raises(ValueError): _url(value)


def test_theme_is_pre_hydrated_persistent_and_system_aware():
    layout=(ROOT/"public-web/app/layout.tsx").read_text(); switcher=(ROOT/"public-web/components/theme-switcher.tsx").read_text(); css=(ROOT/"public-web/app/globals.css").read_text()
    assert "vr-theme" in layout and "prefers-color-scheme: dark" in layout
    assert "localStorage" in switcher and 'value="auto"' in switcher and "addEventListener" in switcher
    assert 'html[data-theme="dark"]' in css and "color-scheme:dark" in css
    assert "--theme-heading:#f4f0e6" in css
    assert "--theme-secondary:#d4dde5" in css
    assert "--theme-placeholder:#91a2b0" in css
    assert 'html[data-theme="dark"] input::placeholder' in css
    assert 'html[data-theme="dark"] .article-body p' in css
    assert 'html[data-theme="dark"] .footer-risk p' in css
    assert "prefers-reduced-motion" in css


def test_automation_page_heading_metadata_and_form_security():
    page=(ROOT/"public-web/app/automation-services/page.tsx").read_text(); form=(ROOT/"public-web/components/automation-enquiry-form.tsx").read_text(); route=(ROOT/"public-web/app/api/automation-enquiries/route.ts").read_text()
    assert page.count("<h1") == 1
    assert page.index("<h1") < page.index("<h2") < page.index("<h3")
    assert "BreadcrumbList" in page and '"@type":"Service"' in page
    assert "website_confirm" in form and "consent" in form and "maxLength" in form
    assert "timingSafeEqual" in route and 'request.headers.get("origin")' in route and 'request.headers.get("x-forwarded-host")' in route and "30_000" in route


def test_lead_migration_is_reversible_private_and_decimal_free():
    sql=(ROOT/"migrations/020_automation_service_leads.sql").read_text(); rollback=(ROOT/"migrations/020_automation_service_leads.rollback.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS public.automation_service_leads" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "REVOKE ALL" in sql
    assert "public_reference UUID" in sql and "consent_recorded_at" in sql
    assert "DROP TABLE IF EXISTS public.automation_service_leads" in rollback


def test_admin_lead_routes_use_existing_security_and_audit_model():
    api=(ROOT/"services/admin_leads_api.py").read_text(); service=(ROOT/"services/admin_leads_service.py").read_text(); bff=(ROOT/"admin-web/lib/lead-bff.ts").read_text()
    assert "_require_bff" in api and "_require_identity" in api
    assert "verifyCsrfToken" in bff and "ADMIN_SESSION_COOKIE" in bff and "X-Admin-BFF-Key" in bff
    assert "admin_auth_audit_events" in service


def test_public_submission_contract_exposes_no_admin_fields():
    api=(ROOT/"services/admin_leads_api.py").read_text(); payload=api[api.index("class PublicLeadPayload"):api.index("class LeadUpdatePayload")]
    for forbidden in ("status", "assigned_to", "internal_notes", "deleted_at"):
        assert forbidden not in payload


def test_responsive_automation_layout_has_overflow_safeguards():
    css=(ROOT/"public-web/app/globals.css").read_text()
    assert ".automation-page" in css and "min-width:0" in css
    assert "@media(max-width:860px)" in css and "@media(max-width:600px)" in css
    assert "overflow-x: clip" in css
