from src.tools.portfolio_tools import (
    build_portfolio_insights,
    calculate_stress_scenarios,
    calculate_portfolio_volatility,
    calculate_portfolio_summary,
    load_portfolio,
    save_portfolio,
    suggest_rebalancing,
)


def test_balanced_profile_uses_a_transparent_target_mix():
    insights = build_portfolio_insights({"risk_profile": "Balanced", "horizon_years": 10}, "AAPL")

    assert insights["target_allocation"] == {"Stocks": 60, "Bonds": 30, "Cash": 10}
    assert insights["concentration_status"] == "Within guardrail"


def test_concentrated_stock_requests_review():
    insights = build_portfolio_insights({"existing_ticker_weight": 0.12, "proposed_weight": 0.10}, "AAPL")

    assert insights["concentration_status"] == "Review"
    assert any("20%" in alert for alert in insights["alerts"])


def test_portfolio_summary_calculates_return_dividends_and_allocations():
    summary = calculate_portfolio_summary([
        {
            "ticker": "AAPL",
            "company": "Apple",
            "sector": "Technology",
            "asset_type": "Stocks",
            "shares": 10,
            "purchase_price": 100,
            "current_price": 120,
            "total_dividends": 15,
        },
        {
            "ticker": "BND",
            "company": "Bond ETF",
            "sector": "Fixed Income",
            "asset_type": "Bonds",
            "shares": 10,
            "purchase_price": 100,
            "current_price": 100,
            "total_dividends": 5,
        },
    ])

    assert summary["total_cost"] == 2000
    assert summary["total_value"] == 2200
    assert summary["total_dividends"] == 20
    assert summary["total_return"] == 220
    assert summary["company_allocations"]["AAPL"] == 1200 / 2200
    assert summary["asset_type_allocations"]["Stocks"] == 1200 / 2200


def test_portfolio_volatility_uses_weighted_holding_volatility_fallback():
    volatility = calculate_portfolio_volatility([
        {"ticker": "AAPL", "shares": 1, "current_price": 75, "annual_volatility": 0.20},
        {"ticker": "BND", "shares": 1, "current_price": 25, "annual_volatility": 0.08},
    ])

    expected = ((0.75 * 0.20) ** 2 + (0.25 * 0.08) ** 2) ** 0.5
    assert volatility == expected


def test_portfolio_volatility_annualizes_historical_returns():
    volatility = calculate_portfolio_volatility([
        {"ticker": "AAPL", "shares": 1, "current_price": 100, "historical_returns": [0.01, -0.01, 0.02, -0.02]},
        {"ticker": "BND", "shares": 1, "current_price": 100, "historical_returns": [0.005, 0.0, 0.005, 0.0]},
    ])

    portfolio_returns = [0.0075, -0.005, 0.0125, -0.01]
    expected = __import__("statistics").stdev(portfolio_returns) * (252 ** 0.5)
    assert volatility == expected


def test_stress_scenarios_apply_asset_specific_shocks():
    scenarios = calculate_stress_scenarios([
        {"ticker": "AAPL", "asset_type": "Stocks", "shares": 1, "current_price": 100},
        {"ticker": "BND", "asset_type": "Bonds", "shares": 1, "current_price": 100},
        {"ticker": "CASH", "asset_type": "Cash", "shares": 1, "current_price": 100},
    ])
    by_name = {item["scenario"]: item for item in scenarios}

    assert set(by_name) == {
        "Market falls 10%",
        "Interest rates increase",
        "Company earnings decline",
        "Negative news appears",
    }
    assert by_name["Market falls 10%"]["estimated_change"] == -13.0
    assert by_name["Interest rates increase"]["estimated_change"] == -7.0
    assert by_name["Company earnings decline"]["estimated_change"] == -8.0
    assert by_name["Negative news appears"]["estimated_change"] == -6.0


def test_concentration_and_rebalancing_suggestions_are_transparent():
    summary = calculate_portfolio_summary([
        {"ticker": "AAPL", "sector": "Technology", "asset_type": "Stocks", "shares": 8, "purchase_price": 100, "current_price": 100},
        {"ticker": "BND", "sector": "Fixed Income", "asset_type": "Bonds", "shares": 2, "purchase_price": 100, "current_price": 100},
    ])

    assert summary["concentration_status"] == "Review"
    assert summary["concentration_alerts"]
    suggestions = suggest_rebalancing(summary, "Balanced")
    assert any(item["asset_type"] == "Bonds" and item["action"] == "Increase" for item in suggestions)


def test_portfolio_storage_is_scoped_to_user(tmp_path):
    path = tmp_path / "portfolios.json"
    save_portfolio("alice", [{"ticker": "AAPL", "shares": 1, "purchase_price": 100, "current_price": 110}], path)
    save_portfolio("bob", [{"ticker": "MSFT", "shares": 2, "purchase_price": 100, "current_price": 105}], path)

    assert [item["ticker"] for item in load_portfolio("alice", path)] == ["AAPL"]
    assert [item["ticker"] for item in load_portfolio("bob", path)] == ["MSFT"]
    assert load_portfolio("unknown", path) == []