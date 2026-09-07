from fastapi.testclient import TestClient

import services.admin_content_studio_api as api
import services.ai_provider as provider_module
from backend import app


def test_ai_suggestions_are_review_only_and_cleaned(monkeypatch):
    monkeypatch.setattr(api, "_require_bff", lambda value: None)
    monkeypatch.setattr(api, "_bearer_token", lambda value: "token")
    monkeypatch.setattr(api, "_require_identity", lambda value: object())

    monkeypatch.setattr(
        provider_module.AIProvider,
        "generate_json",
        lambda self, **kwargs: {
            "title_suggestions": [
                "Gold Market Structure Guide",
                "XAUUSD Risk Control Guide",
                "Gold Trading Structure",
                "Understanding XAUUSD",
                "Disciplined Gold Analysis",
            ],
            "seo_title": "XAUUSD Market Structure and Risk Guide",
            "meta_description": (
                "Understand XAUUSD structure, key gold-market drivers "
                "and disciplined risk control for better-informed analysis."
            ),
            "focus_keyword": "XAUUSD market structure",
            "secondary_keywords": ["gold analysis", "risk control"],
            "slug": "xauusd-market-structure-guide",
            "excerpt": "A practical guide to gold-market structure.",
            "image_alt": "XAUUSD market structure and risk-control chart",
            "faq": [
                {
                    "question": "What drives XAUUSD?",
                    "answer": "Rates, the dollar and risk sentiment.",
                }
            ],
            "improved_body": "<h2>Market structure</h2><p>Useful body.</p>",
            "open_graph_title": "XAUUSD Market Structure Guide",
            "open_graph_description": "A practical gold-market guide.",
            "twitter_title": "XAUUSD Market Structure Guide",
            "twitter_description": "Gold analysis and risk control.",
            "schema_jsonld": {"@type": "Article"},
        },
    )

    response = TestClient(app).post(
        "/admin/content-studio/ai-suggestions",
        headers={
            "Authorization": "Bearer token",
            "X-Admin-BFF-Key": "test",
        },
        json={
            "request": "complete_seo",
            "title": "Current title",
            "body": "<p>Current body</p>",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["saved"] is False
    assert len(result["title_suggestions"]) == 5
    assert result["focus_keyword"] == "XAUUSD market structure"
    assert result["faq"][0]["question"] == "What drives XAUUSD?"
