src/tests/test_llm_tools.py
from src.tools.llm_tools import GeminiRecommendationEngine, generate_investment_recommendation

class _FakeResponse:
    text = """
    {
      "recommendation": "BUY",
      "confidence": 0.84,
      "summary": "Signals are broadly constructive.",
      "reasoning": ["Sentiment is positive.", "RSI is neutral.", "Risk is manageable."],
      "decision_factors": [
        {"signal": "sentiment", "impact": "positive", "evidence": "0.52", "action": "supports upside"}
      ],
      "risk_notes": ["Execution risk remains."],
      "upside_catalysts": ["Improving revenue growth"],
      "downside_catalysts": ["Macro volatility"]
    }
    """

class _FakeModel:
    def generate_content(self, prompt, generation_config=None):
        return _FakeResponse()

def test_generate_investment_recommendation_parses_gemini_json(monkeypatch):
    monkeypatch.setattr(GeminiRecommendationEngine, "_build_model", lambda self: _FakeModel())

    result = generate_investment_recommendation(
        {
            "ticker": "AAPL",
            "sentiment_score": 0.5,
            "technical_indicators": {"RSI": 45},
            "risk_metrics": {"Sharpe_ratio": 1.2},
            "price_forecast": {"forecast_7d": 110, "current_price": 100},
            "fundamental_analysis": {"pe_analysis": {"valuation": "Fair"}},
        }
    )

    assert result["recommendation"] == "BUY"
    assert result["confidence"] == 0.84
    assert "Sentiment is positive." in result["reasoning"]
    assert result["source"] == "gemini"
