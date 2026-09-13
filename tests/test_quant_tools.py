import math

from src.tools.quant_tools import (
    calculate_risk_metrics,
    calculate_technical_indicators,
    fallback_forecast,
    perform_fundamental_analysis,
)

def _sample_prices():
    return [
        {"date": f"2026-01-{day:02d}", "open": 100 + day, "high": 101 + day, "low": 99 + day, "close": 100 + day, "volume": 1000 + day}
        for day in range(1, 80)
    ]

def test_calculate_technical_indicators_returns_core_fields():
    indicators = calculate_technical_indicators(_sample_prices())

    assert "SMA_20" in indicators
    assert "MACD" in indicators
    assert "RSI" in indicators
    assert "Bollinger_Bands" in indicators
    assert indicators["Bollinger_Bands"]["upper"] >= indicators["Bollinger_Bands"]["lower"]

def test_calculate_risk_metrics_returns_core_fields():
    metrics = calculate_risk_metrics(_sample_prices())

    assert "volatility" in metrics
    assert "Sharpe_ratio" in metrics
    assert "VaR_95" in metrics
    assert math.isfinite(metrics["volatility"])


def test_fallback_forecast_returns_prediction_path_for_ranges():
    forecast = fallback_forecast(_sample_prices(), forecast_days=30)

    assert len(forecast["all_forecasts"]) == 30
    assert forecast["forecast_7d"] == forecast["all_forecasts"][6]
    assert forecast["forecast_30d"] == forecast["all_forecasts"][-1]
    assert min(forecast["all_forecasts"]) <= max(forecast["all_forecasts"])


def test_fundamental_analysis_returns_complete_company_metrics():
    result = perform_fundamental_analysis(
        {
            "pe_ratio": 20,
            "peg_ratio": 1.2,
            "pb_ratio": 4,
            "dividend_yield": 0.02,
            "quarterly_revenue_growth": 0.12,
            "earnings_growth": 0.18,
        },
        {
            "income_statement": {"total_revenue": 1000, "net_income": 150},
            "balance_sheet": {"total_assets": 2000, "total_liabilities": 600, "shareholders_equity": 1400},
            "cash_flow": {"free_cash_flow": 120, "operating_cash_flow": 180, "capital_expenditure": -60},
        },
    )

    assert result["growth_metrics"]["revenue_growth"] == 0.12
    assert result["growth_metrics"]["earnings_growth"] == 0.18
    assert result["cash_flow_metrics"]["free_cash_flow"] == 120
    assert result["balance_sheet"]["debt_to_equity"] == 600 / 1400
    assert result["valuation_metrics"]["price_to_book"] == 4
    assert result["financial_health"]["score"] is not None
    assert result["financial_health"]["metrics_scored"] == 5


