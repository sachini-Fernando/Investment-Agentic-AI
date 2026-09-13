from datetime import datetime, timezone

from src.tools.alerts import evaluate_alerts


NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def base_state():
    return {
        "ticker": "AAPL",
        "stock_data": {"current_price": 110.0, "previous_close": 100.0},
        "historical_prices": [],
        "technical_indicators": {"RSI": 75.0},
        "news_articles": [],
        "company_info": {},
        "sentiment_score": 0.0,
        "investor_profile": {},
        "portfolio_insights": {},
    }


def alert_types(state, rules=None):
    return {item["type"] for item in evaluate_alerts(state, rules, NOW)}


def test_price_target_rsi_large_move_and_allocation_alerts():
    state = base_state()
    state["investor_profile"] = {"existing_ticker_weight": 0.08, "proposed_weight": 0.05}
    rules = {
        "price_target": {"enabled": True, "target": 105, "direction": "above"},
    }

    assert {"price_target", "rsi_overbought", "large_price_move", "portfolio_allocation"} <= alert_types(state, rules)


def test_negative_news_requires_recent_negative_article():
    state = base_state()
    state["sentiment_score"] = -0.7
    state["news_articles"] = [{
        "title": "Company reports a major loss",
        "published_at": "2026-09-12T10:00:00+00:00",
    }]

    assert "negative_news" in alert_types(state)


def test_earnings_alert_supports_upcoming_earnings_date():
    state = base_state()
    state["company_info"] = {"earnings_date": "2026-09-18"}

    assert "earnings_announcement" in alert_types(state)


def test_oversold_and_downward_target_alerts():
    state = base_state()
    state["stock_data"] = {"current_price": 90.0, "previous_close": 100.0}
    state["technical_indicators"] = {"RSI": 25.0}
    rules = {
        "price_target": {"enabled": True, "target": 95, "direction": "below"},
        "large_move": {"enabled": False},
        "portfolio_allocation": {"enabled": False},
    }

    assert {"price_target", "rsi_oversold"} <= alert_types(state, rules)


def test_missing_data_does_not_create_false_alerts():
    state = {"ticker": "AAPL"}

    assert evaluate_alerts(state, now=NOW) == []