import math

from src.tools.quant_tools import calculate_risk_metrics, calculate_technical_indicators

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


