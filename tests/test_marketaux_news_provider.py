from services.marketaux_news_provider import (
    _score,
    _themes,
)


def test_gold_macro_headline_scores_high():
    title = (
        "Gold advances as mild US inflation data "
        "puts Fed rate hike in doubt"
    )

    assert _score(title) >= 5

    themes = _themes(title)

    assert "GOLD" in themes
    assert "FED" in themes
    assert "INFLATION" in themes


def test_gold_reserve_company_false_positive_is_blocked():
    title = (
        "Gold Reserve Announces Intention to Make "
        "Further Settlement Offers"
    )

    assert _score(title) == 0


def test_us_jobs_is_relevant_macro_context():
    title = "US unemployment claims rise but remain at healthy level"

    assert _score(title) >= 2
    assert "JOBS" in _themes(title)


def test_treasury_dollar_context_is_detected():
    title = "Treasury yields climb as US dollar strengthens"

    themes = _themes(title)

    assert "YIELDS" in themes
    assert "USD" in themes
