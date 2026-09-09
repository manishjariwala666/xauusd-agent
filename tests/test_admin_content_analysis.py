from services.admin_content_analysis import _similarity, analyse_content


def test_content_quality_metrics() -> None:
    body = """## Gold market context

Gold risk management requires planning. Read our [risk guide](/blog/risk-guide).

### Position sizing

Use a defined process and avoid emotional decisions.
"""
    result = analyse_content(
        title="Gold Risk Management",
        slug="gold-risk-management",
        body=body,
        focus_keyword="gold risk management",
    )
    assert result["word_count"] > 0
    assert result["headings"]["h2"] == 1
    assert result["headings"]["h3"] == 1
    assert result["internal_links"] == 1
    assert result["reading_time_minutes"] >= 1
    assert isinstance(result["checks"], list)


def test_body_h1_and_repeated_sentence_detection() -> None:
    repeated = "This sentence is intentionally long enough to be detected as repeated content."
    result = analyse_content(
        title="Title",
        slug="Title",
        body=f"# Wrong H1\n\n{repeated}\n\n{repeated}",
    )
    checks = {item["code"]: item for item in result["checks"]}
    assert checks["body_h1"]["passed"] is False
    assert checks["slug_lowercase"]["passed"] is False
    assert result["repeated_sentences"]


def test_similarity_prioritises_related_content() -> None:
    close = _similarity(
        "Gold market risk management and position sizing",
        "Gold market risk management with position sizing",
    )
    unrelated = _similarity(
        "Gold market risk management and position sizing",
        "Kitchen vastu placement and bathroom direction",
    )
    assert close > unrelated
    assert close > 60
