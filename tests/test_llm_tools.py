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
"""
Unit tests for LLM tools and Gemini recommendation engine.

This test suite covers:
1. Gemini API integration (with mocking)
2. JSON response parsing
3. Heuristic fallback when Gemini is unavailable
4. Edge cases and error handling
5. Decision factors, risk notes, and catalysts extraction
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.tools.llm_tools import (
    GeminiRecommendationEngine,
    generate_investment_recommendation,
    _safe_json_loads,
    _normalize_recommendation,
    _normalize_confidence,
    _heuristic_synthesis,
    GEMINI_AVAILABLE
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_payload():
    """Sample payload for testing."""
    return {
        "ticker": "AAPL",
        "user_query": "Should I buy this stock?",
        "stock_data": {
            "current_price": 178.50,
            "volume": 50000000,
            "market_cap": "2.8T",
            "high_52w": 199.62,
            "low_52w": 143.90
        },
        "company_info": {
            "sector": "Technology",
            "pe_ratio": 28.5,
            "dividend_yield": 0.005,
            "market_cap": 2800000000000
        },
        "technical_indicators": {
            "RSI": 45.3,
            "MACD": "bullish",
            "SMA_50": 172.50,
            "SMA_200": 165.20
        },
        "price_forecast": {
            "current_price": 178.50,
            "forecast_7d": 185.00,
            "forecast_30d": 190.00
        },
        "sentiment_score": 0.42,
        "sentiment_confidence": 0.75,
        "news_summary": "Apple reported strong earnings with services revenue growing 15%.",
        "key_events": ["Earnings beat", "New product launch"],
        "risk_metrics": {
            "volatility": 0.22,
            "Sharpe_ratio": 1.2,
            "max_drawdown": -0.15,
            "var_95": -0.032
        },
        "fundamental_analysis": {
            "pe_analysis": {"valuation": "Fair", "insights": ["P/E in line with sector"]},
            "profitability": {"rating": "Good", "insights": ["High margins"]}
        },
        "market_context": {
            "trend": "bullish",
            "sector_performance": "strong"
        }
    }


@pytest.fixture
def fake_gemini_response():
    """Mock Gemini response."""
    return """
    {
      "recommendation": "BUY",
      "confidence": 0.84,
      "summary": "Signals are broadly constructive.",
      "reasoning": ["Sentiment is positive.", "RSI is neutral.", "Risk is manageable."],
      "decision_factors": [
        {
          "signal": "sentiment",
          "impact": "positive",
          "evidence": "0.52",
          "action": "supports upside"
        },
        {
          "signal": "technical",
          "impact": "neutral",
          "evidence": "RSI=45.3",
          "action": "neutral technical signals"
        },
        {
          "signal": "risk",
          "impact": "positive",
          "evidence": "Sharpe=1.2",
          "action": "good risk-adjusted returns"
        }
      ],
      "risk_notes": ["Execution risk remains.", "Macro volatility"],
      "upside_catalysts": ["Improving revenue growth", "New product pipeline"],
      "downside_catalysts": ["Macro volatility", "Competition risk"]
    }
    """


# ============================================================================
# TEST: RESPONSE PARSING UTILITIES
# ============================================================================

class TestResponseParsing:
    """Test JSON parsing utilities."""
    
    def test_safe_json_loads_valid_json(self):
        """Test parsing valid JSON."""
        json_str = '{"recommendation": "BUY", "confidence": 0.8}'
        result = _safe_json_loads(json_str)
        assert result["recommendation"] == "BUY"
        assert result["confidence"] == 0.8
    
    def test_safe_json_loads_with_markdown(self):
        """Test parsing JSON with markdown code blocks."""
        json_str = '```json\n{"recommendation": "BUY"}\n```'
        result = _safe_json_loads(json_str)
        assert result["recommendation"] == "BUY"
    
    def test_safe_json_loads_invalid_json(self):
        """Test parsing invalid JSON returns empty dict."""
        json_str = "This is not JSON"
        result = _safe_json_loads(json_str)
        assert result == {}
    
    def test_safe_json_loads_empty_string(self):
        """Test parsing empty string returns empty dict."""
        result = _safe_json_loads("")
        assert result == {}
    
    def test_normalize_recommendation_valid(self):
        """Test valid recommendation normalization."""
        assert _normalize_recommendation("BUY") == "BUY"
        assert _normalize_recommendation("SELL") == "SELL"
        assert _normalize_recommendation("HOLD") == "HOLD"
    
    def test_normalize_recommendation_invalid(self):
        """Test invalid recommendation normalization."""
        assert _normalize_recommendation("") == "HOLD"
        assert _normalize_recommendation("STRONG BUY") == "BUY"
        assert _normalize_recommendation("WEAK SELL") == "SELL"
        assert _normalize_recommendation("NEUTRAL") == "HOLD"
        assert _normalize_recommendation(None) == "HOLD"
    
    def test_normalize_confidence_valid(self):
        """Test valid confidence normalization."""
        assert _normalize_confidence(0.84) == 0.84
        assert _normalize_confidence(0.5) == 0.5
        assert _normalize_confidence(1.5) == 1.0  # Cap at 1.0
        assert _normalize_confidence(-0.5) == 0.0  # Floor at 0.0
    
    def test_normalize_confidence_invalid(self):
        """Test invalid confidence normalization."""
        assert _normalize_confidence("not a number") == 0.5
        assert _normalize_confidence(None) == 0.5


# ============================================================================
# TEST: HEURISTIC FALLBACK
# ============================================================================

class TestHeuristicFallback:
    """Test heuristic fallback when Gemini is unavailable."""
    
    def test_heuristic_synthesis_buy_signal(self, sample_payload):
        """Test heuristic generates BUY recommendation."""
        # Modify payload for strong BUY signals
        payload = sample_payload.copy()
        payload["sentiment_score"] = 0.8
        payload["technical_indicators"] = {"RSI": 25}  # Oversold
        payload["risk_metrics"] = {"Sharpe_ratio": 1.5}
        payload["price_forecast"] = {
            "current_price": 100,
            "forecast_7d": 115
        }
        
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "BUY"
        assert result["confidence"] >= 0.5
        assert result["source"] == "heuristic"
        assert len(result["reasoning"]) > 0
        assert len(result["decision_factors"]) > 0
    
    def test_heuristic_synthesis_sell_signal(self, sample_payload):
        """Test heuristic generates SELL recommendation."""
        payload = sample_payload.copy()
        payload["sentiment_score"] = -0.8
        payload["technical_indicators"] = {"RSI": 75}  # Overbought
        payload["risk_metrics"] = {"Sharpe_ratio": -0.5}
        payload["price_forecast"] = {
            "current_price": 100,
            "forecast_7d": 85
        }
        
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "SELL"
        assert result["confidence"] >= 0.5
        assert result["source"] == "heuristic"
    
    def test_heuristic_synthesis_hold_signal(self, sample_payload):
        """Test heuristic generates HOLD recommendation."""
        payload = sample_payload.copy()
        payload["sentiment_score"] = 0.0
        payload["technical_indicators"] = {"RSI": 50}
        payload["risk_metrics"] = {"Sharpe_ratio": 0.5}
        payload["price_forecast"] = {
            "current_price": 100,
            "forecast_7d": 102
        }
        
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "HOLD"
        assert result["source"] == "heuristic"
    
    def test_heuristic_synthesis_missing_data(self):
        """Test heuristic with minimal data."""
        payload = {"ticker": "AAPL"}
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "HOLD"
        assert result["confidence"] == 0.45  # Default low confidence
        assert "Insufficient strong signals" in result["reasoning"][0]


# ============================================================================
# TEST: GEMINI RECOMMENDATION ENGINE
# ============================================================================

class TestGeminiRecommendationEngine:
    """Test the main recommendation engine."""
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = GeminiRecommendationEngine()
        assert engine.model_name == "gemini-1.5-flash"
        assert engine.temperature == 0.2
        assert engine.max_output_tokens == 1024
    
    def test_engine_build_prompt(self, sample_payload):
        """Test prompt building."""
        engine = GeminiRecommendationEngine()
        prompt = engine.build_prompt(sample_payload)
        
        # Check prompt contains all key sections
        assert "Ticker: AAPL" in prompt
        assert "Current Price: $178.5" in prompt
        assert "RSI: 45.3" in prompt
        assert "Sentiment Score: 0.42" in prompt
        assert "Sharpe Ratio: 1.2" in prompt
        assert "BUY|SELL|HOLD" in prompt
    
    def test_engine_generate_without_gemini(self, sample_payload):
        """Test engine falls back to heuristic when Gemini unavailable."""
        with patch('src.tools.llm_tools.GEMINI_AVAILABLE', False):
            engine = GeminiRecommendationEngine()
            result = engine.generate(sample_payload)
            assert result["source"] == "heuristic"
            assert "recommendation" in result
            assert "confidence" in result
    
    def test_engine_generate_with_gemini_failure(self, sample_payload):
        """Test engine falls back to heuristic when Gemini fails."""
        engine = GeminiRecommendationEngine()
        
        # Mock Gemini to fail
        with patch.object(engine, '_model', None):
            result = engine.generate(sample_payload)
            assert result["source"] == "heuristic"
    
    def test_engine_parse_gemini_response(self, fake_gemini_response):
        """Test parsing Gemini response."""
        engine = GeminiRecommendationEngine()
        parsed = engine._parse_gemini_response(fake_gemini_response)
        
        assert parsed["recommendation"] == "BUY"
        assert parsed["confidence"] == 0.84
        assert "Sentiment is positive." in parsed["reasoning"]
        assert len(parsed["decision_factors"]) == 3
        assert len(parsed["risk_notes"]) == 2
        assert len(parsed["upside_catalysts"]) == 2
        assert len(parsed["downside_catalysts"]) == 2
    
    def test_engine_parse_gemini_response_invalid(self):
        """Test parsing invalid Gemini response."""
        engine = GeminiRecommendationEngine()
        parsed = engine._parse_gemini_response("Not JSON")
        
        # Should return empty dict or default values
        assert parsed.get("recommendation") is None or parsed == {}


# ============================================================================
# TEST: INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for the full recommendation pipeline."""
    
    def test_generate_investment_recommendation_parses_gemini_json(self, monkeypatch):
        """Test full recommendation generation with mock Gemini."""
        
        class FakeResponse:
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
        
        class FakeModel:
            def generate_content(self, prompt, generation_config=None):
                return FakeResponse()
        
        # Mock the model building
        def mock_build_model(self):
            return FakeModel()
        
        monkeypatch.setattr(GeminiRecommendationEngine, "_build_model", mock_build_model)
        
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
        assert len(result["risk_notes"]) > 0
        assert len(result["upside_catalysts"]) > 0
        assert len(result["downside_catalysts"]) > 0
    
    def test_generate_investment_recommendation_with_heuristic_fallback(self):
        """Test fallback to heuristic when Gemini is unavailable."""
        
        # Mock Gemini as unavailable
        with patch('src.tools.llm_tools.GEMINI_AVAILABLE', False):
            result = generate_investment_recommendation(
                {
                    "ticker": "AAPL",
                    "sentiment_score": 0.5,
                    "technical_indicators": {"RSI": 45},
                    "risk_metrics": {"Sharpe_ratio": 1.2},
                    "price_forecast": {"forecast_7d": 110, "current_price": 100}
                }
            )
            
            assert result["source"] == "heuristic"
            assert "recommendation" in result
            assert "confidence" in result
    
    def test_generate_investment_recommendation_with_empty_payload(self):
        """Test recommendation generation with empty payload."""
        result = generate_investment_recommendation({})
        
        # Should handle gracefully
        assert "recommendation" in result
        assert "confidence" in result
        assert result["source"] in ["heuristic", "gemini"]


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_gemini_response_missing_fields(self, monkeypatch):
        """Test handling of Gemini response with missing fields."""
        
        class FakeResponse:
            text = """
            {
              "recommendation": "BUY"
              // Missing confidence, reasoning, etc.
            }
            """
        
        class FakeModel:
            def generate_content(self, prompt, generation_config=None):
                return FakeResponse()
        
        def mock_build_model(self):
            return FakeModel()
        
        monkeypatch.setattr(GeminiRecommendationEngine, "_build_model", mock_build_model)
        
        result = generate_investment_recommendation({
            "ticker": "AAPL",
            "sentiment_score": 0.5
        })
        
        # Should provide defaults
        assert result["recommendation"] == "BUY"
        assert result["confidence"] == 0.5  # Default confidence
        assert result["summary"] != ""  # Default summary
    
    def test_gemini_response_malformed_json(self, monkeypatch):
        """Test handling of malformed JSON response."""
        
        class FakeResponse:
            text = "This is not JSON at all"
        
        class FakeModel:
            def generate_content(self, prompt, generation_config=None):
                return FakeResponse()
        
        def mock_build_model(self):
            return FakeModel()
        
        monkeypatch.setattr(GeminiRecommendationEngine, "_build_model", mock_build_model)
        
        result = generate_investment_recommendation({
            "ticker": "AAPL",
            "sentiment_score": 0.5
        })
        
        # Should fall back to heuristic
        assert result["source"] == "heuristic"
    
    def test_gemini_api_timeout(self, monkeypatch):
        """Test handling of Gemini API timeout."""
        
        class FakeModel:
            def generate_content(self, prompt, generation_config=None):
                raise Exception("API timeout")
        
        def mock_build_model(self):
            return FakeModel()
        
        monkeypatch.setattr(GeminiRecommendationEngine, "_build_model", mock_build_model)
        
        result = generate_investment_recommendation({
            "ticker": "AAPL"
        })
        
        # Should fall back to heuristic
        assert result["source"] == "heuristic"
    
    def test_extreme_sentiment_values(self):
        """Test handling of extreme sentiment values."""
        payload = {
            "ticker": "AAPL",
            "sentiment_score": 0.99,
            "sentiment_confidence": 0.99
        }
        
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "BUY"  # Very positive
        assert result["confidence"] == 0.95  # Max confidence
    
    def test_extreme_rsi_values(self):
        """Test handling of extreme RSI values."""
        # Oversold
        payload = {
            "ticker": "AAPL",
            "technical_indicators": {"RSI": 15}
        }
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "BUY"  # Oversold = bullish
        
        # Overbought
        payload["technical_indicators"] = {"RSI": 85}
        result = _heuristic_synthesis(payload)
        assert result["recommendation"] == "SELL"  # Overbought = bearish


# ============================================================================
# TEST: DECISION FACTORS EXTRACTION
# ============================================================================

class TestDecisionFactors:
    """Test decision factors extraction."""
    
    def test_decision_factors_are_present(self, sample_payload):
        """Test that decision factors are properly extracted."""
        result = _heuristic_synthesis(sample_payload)
        assert "decision_factors" in result
        assert len(result["decision_factors"]) > 0
        
        # Check each factor has required fields
        for factor in result["decision_factors"]:
            assert "signal" in factor
            assert "impact" in factor
            assert "evidence" in factor
            assert "action" in factor
    
    def test_risk_notes_are_present(self, sample_payload):
        """Test that risk notes are properly extracted."""
        result = _heuristic_synthesis(sample_payload)
        assert "risk_notes" in result
    
    def test_catalysts_are_present(self, sample_payload):
        """Test that catalysts are properly extracted."""
        result = _heuristic_synthesis(sample_payload)
        assert "upside_catalysts" in result
        assert "downside_catalysts" in result
        # Should be lists even if empty
        assert isinstance(result["upside_catalysts"], list)
        assert isinstance(result["downside_catalysts"], list)


# ============================================================================
# TEST: PERFORMANCE
# ============================================================================

class TestPerformance:
    """Performance tests for the recommendation engine."""
    
    def test_heuristic_fallback_performance(self):
        """Test heuristic fallback executes quickly."""
        import time
        
        payload = {
            "ticker": "AAPL",
            "sentiment_score": 0.5,
            "technical_indicators": {"RSI": 45},
            "risk_metrics": {"Sharpe_ratio": 1.2},
            "price_forecast": {"forecast_7d": 110, "current_price": 100}
        }
        
        start = time.time()
        for _ in range(100):  # 100 iterations
            _heuristic_synthesis(payload)
        end = time.time()
        
        # Should complete 100 iterations in under 1 second
        assert (end - start) < 1.0, f"Took {end - start:.2f} seconds"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])