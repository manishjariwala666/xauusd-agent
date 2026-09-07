from fastapi.testclient import TestClient

import services.admin_content_studio_api as api
from backend import app


def test_live_seo_preview_uses_unsaved_body(monkeypatch):
    monkeypatch.setattr(api, "_require_bff", lambda value: None)
    monkeypatch.setattr(api, "_bearer_token", lambda value: "token")
    monkeypatch.setattr(api, "_require_identity", lambda value: object())

    body = "XAUUSD market structure " * 320
    client = TestClient(app)

    response = client.post(
        "/admin/content-studio/seo-preview",
        headers={
            "Authorization": "Bearer token",
            "X-Admin-BFF-Key": "test",
        },
        json={
            "title": "XAUUSD Market Structure and Risk Control",
            "slug": "xauusd-market-structure",
            "excerpt": "Understand XAUUSD market structure and disciplined risk control.",
            "body": body,
            "meta_title": "XAUUSD Market Structure & Risk Control Guide",
            "meta_description": (
                "Understand XAUUSD market structure, gold-market drivers and "
                "disciplined risk-control principles for informed analysis."
            ),
            "focus_keyword": "XAUUSD market structure",
            "canonical_url": "https://venusrealm.net/blog/xauusd-market-structure",
            "featured_image": "https://venusrealm.net/media/gold.webp",
            "featured_media_id": 1,
            "featured_image_alt": "XAUUSD market structure chart",
            "internal_links": ["/blog"],
            "open_graph": {
                "title": "XAUUSD Market Structure Guide",
                "description": "Gold-market structure and disciplined risk control.",
                "media_id": 1,
            },
            "twitter_card": {
                "title": "XAUUSD Market Structure Guide",
                "description": "Gold-market structure and disciplined risk control.",
                "media_id": 1,
                "card_type": "summary_large_image",
            },
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["saved"] is False
    assert result["word_count"] >= 300
    assert "content_too_short" not in {
        issue["code"] for issue in result["issues"]
    }
