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

def test_publication_indexes_use_bounded_responsive_layout():
    announcements = (ROOT / "public-web/app/announcements/page.tsx").read_text()
    results = (ROOT / "public-web/app/results/page.tsx").read_text()
    css = (ROOT / "public-web/app/globals.css").read_text()
    for source in (announcements, results):
        assert 'className="publication-page"' in source
        assert 'className="publication-filters"' in source
        assert 'className="publication-grid"' in source
        assert source.count("<h1") == 1
    assert ".publication-grid {" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert ".publication-card h2" in css and "font-size: clamp(" in css
    assert "overflow-wrap: anywhere" in css and "word-break: normal" in css
    assert "@media (max-width: 860px)" in css
    assert "@media (max-width: 360px)" in css

def test_publication_filters_have_accessible_focus_and_mobile_stack():
    css = (ROOT / "public-web/app/globals.css").read_text()
    assert ".publication-filters input:focus-visible" in css
    assert ".publication-filters select:focus-visible" in css
    assert ".publication-filters button" in css
    assert ".publication-filters { grid-template-columns: 1fr;" in css
