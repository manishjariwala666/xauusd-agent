from services.admin_seo_validation import safe_https_url, validate_and_score, validate_faq, validate_schema


def content(**updates):
    value = {"slug": "gold-market-guide", "title": "Gold market guide", "excerpt": "gold market guide " * 30, "body": "gold market guide " * 350, "status": "published", "is_public": True, "featured_image": "https://example.test/gold.jpg", "featured_image_alt": "Gold chart", "internal_links": ["/learn"]}
    value.update(updates); return value


def payload(**updates):
    value = {"meta_title": "Gold Market Guide for Disciplined Traders", "meta_description": "Learn a practical gold market process with risk controls, repeatable analysis, and clear decision points for disciplined traders every day.", "focus_keyword": "gold market guide", "canonical_url": "https://example.test/gold-market-guide", "robots_index": True, "robots_follow": True, "sitemap_included": True, "internal_links": ["/learn"], "open_graph": {"title": "Gold guide", "description": "A practical guide", "image": "https://example.test/og.jpg"}, "twitter_card": {"title": "Gold guide", "description": "A practical guide", "image": "https://example.test/x.jpg", "card_type": "summary_large_image"}, "faq": [], "schema_jsonld": {"@type": "Article"}}
    value.update(updates); return value


def test_safe_urls_require_https_and_approved_origin():
    allowed = {"https://example.test"}
    assert safe_https_url("https://example.test/path", allowed)
    assert not safe_https_url("http://example.test/path", allowed)
    assert not safe_https_url("javascript:alert(1)", allowed)
    assert not safe_https_url("https://evil.test/path", allowed)


def test_score_is_deterministic_and_explains_deductions():
    first = validate_and_score(payload(), content(), approved_origins={"https://example.test"})
    second = validate_and_score(payload(), content(), approved_origins={"https://example.test"})
    assert first == second
    assert 0 <= first["score"] <= 100
    assert first["score"] == 100 - sum(issue["points_lost"] for issue in first["issues"])


def test_invalid_canonical_and_sitemap_are_errors():
    result = validate_and_score(payload(canonical_url="data:text/html,bad"), content(status="draft"), approved_origins={"https://example.test"})
    assert not result["valid"]
    codes = {issue["code"] for issue in result["issues"] if issue["severity"] == "error"}
    assert {"canonical_valid", "indexing_sitemap_inconsistent"} <= codes


def test_faq_and_schema_reject_executable_content():
    assert validate_faq([{"question": "Safe?", "answer": "<script>alert(1)</script>"}])
    assert validate_faq([{"question": "", "answer": "Answer"}])
    assert validate_schema({"@type": "ExecutableThing"})
    assert validate_schema({"@type": "Article", "name": "javascript:alert(1)"})
    assert not validate_schema({"@type": "FAQPage", "mainEntity": []})


def test_media_asset_can_authorize_local_social_image():
    value = payload(open_graph={"title": "Gold", "description": "Guide", "image": "http://local.test/image", "media_id": 4})
    result = validate_and_score(value, content(), approved_origins={"https://example.test"})
    assert "open_graph_incomplete" not in {issue["code"] for issue in result["issues"]}
