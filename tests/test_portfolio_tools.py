from src.tools.portfolio_tools import build_portfolio_insights


def test_balanced_profile_uses_a_transparent_target_mix():
    insights = build_portfolio_insights({"risk_profile": "Balanced", "horizon_years": 10}, "AAPL")

    assert insights["target_allocation"] == {"Stocks": 60, "Bonds": 30, "Cash": 10}
    assert insights["concentration_status"] == "Within guardrail"


def test_concentrated_stock_requests_review():
    insights = build_portfolio_insights({"existing_ticker_weight": 0.12, "proposed_weight": 0.10}, "AAPL")

    assert insights["concentration_status"] == "Review"
    assert any("20%" in alert for alert in insights["alerts"])
