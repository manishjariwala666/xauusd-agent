import inspect

from services import admin_seo_api


def test_all_seo_routes_revalidate_admin_identity():
    source = inspect.getsource(admin_seo_api)
    for route in [
        '/content/{content_id}/seo', '/content/{content_id}/seo/validate',
        '/content/{content_id}/seo/score', '/seo/issues', '/seo/summary',
    ]:
        assert route in source
    assert "_require_bff(bff_secret)" in source
    assert "_require_identity(_bearer_token(authorization))" in source
    assert "model_dump(exclude_none=True)" in source


def test_seo_api_sanitizes_service_failures():
    source = inspect.getsource(admin_seo_api._safe)
    assert "SEO service is temporarily unavailable." in source
    assert "LOGGER.exception" in source
    assert "str(exc)" not in source.split("except Exception")[1]
