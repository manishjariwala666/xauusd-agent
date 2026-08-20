from services.master_ai_intent_resolver import resolve_master_ai_intent


PROMPT = """Create ONE real SEO blog DRAFT using ai_blog_agent.

Topic:
Gold Trading Strategy for XAUUSD: How to Identify Buy and Sell Setups

Requirements:
- DRAFT only. Never publish.
- 1400–1600 words.
- Target audience: USA beginner and intermediate gold/XAUUSD traders.
- Choose one relevant high-search-volume primary keyword.
- Include H2/H3 structure, practical examples, FAQ and trading risk disclaimer.

Images:
- Create/select 1 featured image.
- Include 1–2 relevant inline images where supported.

SEO:
- internal link suggestions
- FAQ/schema-ready content

Execute the real ai_blog_agent now.

Return ONLY the verified execution result:
- DRAFT_ID
- TITLE
- PRIMARY_KEYWORD
- WORD_COUNT
- FEATURED_IMAGE
- INLINE_IMAGE_COUNT
- STATUS
- PREVIEW_LINK

Do not simulate execution.
If execution fails or is blocked, return the real failure status and reason.
"""


def test_rich_blog_execution_prompt_wins_over_status_output_field():
    proposal = resolve_master_ai_intent(PROMPT)

    assert proposal.status == "RESOLVED"
    assert proposal.action == "run_blog_agent"
    assert proposal.agent_key == "ai_blog_agent"
    assert proposal.risk.value == "LOW_RISK"
    assert proposal.parameters["publish"] is False
    assert proposal.parameters["include_image"] is True
    assert proposal.parameters["include_faq"] is True
    assert proposal.parameters["include_schema"] is True
    assert proposal.parameters["include_internal_links"] is True
    assert proposal.parameters["include_risk_disclaimer"] is True
    assert proposal.parameters["target_word_min"] == 1400
    assert proposal.parameters["target_word_max"] == 1600
    assert proposal.parameters["location"] == "USA"
    assert proposal.parameters["target_audience"].startswith("USA beginner")
    assert proposal.parameters["topic"] == (
        "Gold Trading Strategy for XAUUSD: How to Identify Buy and Sell Setups"
    )


def test_plain_agent_status_still_routes_to_diagnostics():
    proposal = resolve_master_ai_intent("Master AI agent status check karo")
    assert proposal.action == "read_agent_status"
    assert proposal.status == "RESOLVED"
