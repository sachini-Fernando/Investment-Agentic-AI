from src.pipeline.market_data import validate_price_history
from src.tools import data_tools


def test_validate_price_history_removes_invalid_rows_and_sorts():
	records = validate_price_history([
		{"date": "2026-01-03", "close": 103, "high": 104, "low": 102},
		{"date": "2026-01-01", "close": None, "high": 101, "low": 99},
		{"date": "2026-01-02", "close": 102, "high": 90, "low": 95},
		{"date": "2026-01-03", "close": 104, "high": 105, "low": 103},
	])

	assert [record["date"] for record in records] == ["2026-01-03"]
	assert records[0]["close"] == 104.0


def test_fetch_stock_data_prefers_yfinance_and_tracks_fallback_sources(monkeypatch):
	monkeypatch.setattr(data_tools._INGESTION, "fetch_yfinance_snapshot", lambda ticker: {
		"ticker": ticker,
		"current_price": 100,
		"currency": "USD",
		"exchange": "NASDAQ",
		"market_status": "Open",
		"quote_timestamp": "2026-09-11T10:00:00+00:00",
	})
	monkeypatch.setattr(data_tools._INGESTION, "fetch_alpha_vantage_quote", lambda ticker: {
		"current_price": 99,
		"open": 98,
	})

	result = data_tools.fetch_stock_data("AAPL")

	assert result["current_price"] == 100
	assert result["open"] == 98
	assert result["sources_used"] == ["yfinance", "alpha_vantage"]
	assert result["source"] == "yfinance + alpha_vantage"
	assert result["data_timestamp"] == "2026-09-11T10:00:00+00:00"
	assert result["currency"] == "USD"
	assert result["exchange"] == "NASDAQ"