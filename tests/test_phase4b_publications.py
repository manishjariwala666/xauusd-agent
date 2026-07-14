from decimal import Decimal
from pathlib import Path
import pytest
from services.admin_publications_api import AnnouncementPayload, ResultPayload
from services.admin_publications_service import calculate_points

ROOT=Path(__file__).parents[1]
def test_deterministic_buy_sell_points():
    assert calculate_points("BUY","2300.100000","2312.400000")==Decimal("12.300000")
    assert calculate_points("SELL","2300.100000","2288.400000")==Decimal("11.700000")
def test_invalid_prices_rejected():
    with pytest.raises(ValueError): calculate_points("BUY","0","4")
def test_migration_is_additive_and_reversible():
    forward=(ROOT/"migrations/019_announcements_verified_results.sql").read_text();back=(ROOT/"migrations/019_announcements_verified_results.rollback.sql").read_text()
    assert "ALTER TABLE public.content_items" in forward and "CREATE TABLE IF NOT EXISTS public.verified_results" in forward
    assert "verified_results_publish_gate" in forward and "DROP TABLE IF EXISTS public.verified_results" in back
def test_public_queries_are_privacy_minimized():
    src=(ROOT/"services/admin_publications_service.py").read_text()
    public=src[src.index("def list_public_results"):]
    for forbidden in ("verified_by","created_by","updated_by","evidence_notes","compliance_notes","storage_path","public_url"):
        assert forbidden not in public
def test_admin_routes_require_existing_auth_helpers():
    src=(ROOT/"services/admin_publications_api.py").read_text()
    assert "_require_bff" in src and "_require_identity" in src and "admin_auth_audit_events" in (ROOT/"services/admin_publications_service.py").read_text()
def test_percentage_claims_are_database_blocked():
    sql=(ROOT/"migrations/019_announcements_verified_results.sql").read_text()
    assert "result_percentage IS NULL" in sql
def test_public_pages_have_one_h1_and_no_evidence_url():
    pages=["app/announcements/page.tsx","app/announcements/[slug]/page.tsx","app/results/page.tsx","app/results/[publicId]/page.tsx"]
    for page in pages:
        source=(ROOT/"public-web"/page).read_text()
        assert source.count("<h1") == 1
        assert "storage_path" not in source and "evidence_url" not in source
def test_public_details_reuse_share_controls():
    assert "ShareControls" in (ROOT/"public-web/app/announcements/[slug]/page.tsx").read_text()
    assert "ShareControls" in (ROOT/"public-web/app/results/[publicId]/page.tsx").read_text()
