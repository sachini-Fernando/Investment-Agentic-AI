"""
LLM synthesis utilities for recommendation generation with Google Gemini.

This module provides:
- GeminiRecommendationEngine: Main engine for generating recommendations
- Heuristic fallback when Gemini is unavailable
- Structured prompt engineering
- JSON response parsing with validation
- Decision factors, risk notes, and catalysts extraction
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from loguru import logger

# ============================================================================
# GEMINI AVAILABILITY CHECK
# ============================================================================

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai is not available. Falling back to heuristic recommendations.")

# ============================================================================
# RESPONSE PARSING UTILITIES
# ============================================================================

def _safe_json_loads(text: str) -> Dict[str, Any]:
    """
    Safely parse JSON from text, handling markdown code blocks and malformed JSON.
    
    Args:
        text: Raw text potentially containing JSON
        
    Returns:
        Parsed dictionary or empty dict on failure
    """
    if not text:
        return {}

    # Remove markdown code blocks
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Extract JSON object using braces
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"JSON parsing failed: {e}")
        return {}

def _normalize_recommendation(value: Optional[str]) -> str:
    """
    Normalize recommendation string to BUY/SELL/HOLD.
    
    Args:
        value: Raw recommendation string
        
    Returns:
        Normalized recommendation
    """
    if not value:
        return "HOLD"
    
    value = value.strip().upper()
    
    if value in {"BUY", "SELL", "HOLD"}:
        return value
    if "BUY" in value:
        return "BUY"
    if "SELL" in value:
        return "SELL"
    
    return "HOLD"

def _normalize_confidence(value: Any) -> float:
    """
    Normalize confidence value to 0.0-1.0 range.
    
    Args:
        value: Raw confidence value
        
    Returns:
        Normalized confidence
    """
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.5
    
    return max(0.0, min(1.0, confidence))

# ============================================================================
# HEURISTIC FALLBACK ENGINE
# ============================================================================

def _heuristic_synthesis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate recommendation using rule-based logic when Gemini is unavailable.
    
    This serves as a fallback mechanism that uses a weighted scoring system
    across multiple signals to produce a recommendation.
    
    Args:
        payload: Dictionary containing all agent outputs
        
    Returns:
        Recommendation dictionary with reasoning
    """
    # Extract signals
    sentiment = payload.get("sentiment_score")
    rsi = (payload.get("technical_indicators") or {}).get("RSI")
    sharpe = (payload.get("risk_metrics") or {}).get("Sharpe_ratio")
    forecast = (payload.get("price_forecast") or {}).get("forecast_7d")
    current = (payload.get("price_forecast") or {}).get("current_price")
    pe_valuation = ((payload.get("fundamental_analysis") or {}).get("pe_analysis") or {}).get("valuation")

    score = 0
    rationale: List[str] = []
    decision_factors: List[Dict[str, str]] = []

    # === 1. SENTIMENT ANALYSIS ===
    if sentiment is not None:
        if sentiment > 0.25:
            score += 1
            rationale.append(f"News sentiment is positive at {sentiment:.2f}.")
            decision_factors.append({
                "signal": "sentiment",
                "impact": "positive",
                "evidence": f"{sentiment:.2f}",
                "action": "Positive sentiment supports bullish outlook"
            })
        elif sentiment < -0.25:
            score -= 1
            rationale.append(f"News sentiment is negative at {sentiment:.2f}.")
            decision_factors.append({
                "signal": "sentiment",
                "impact": "negative",
                "evidence": f"{sentiment:.2f}",
                "action": "Negative sentiment suggests caution"
            })
        else:
            rationale.append(f"News sentiment is neutral at {sentiment:.2f}.")
            decision_factors.append({
                "signal": "sentiment",
                "impact": "neutral",
                "evidence": f"{sentiment:.2f}",
                "action": "Neutral sentiment provides no directional bias"
            })

    # === 2. TECHNICAL ANALYSIS ===
    if rsi is not None:
        if rsi < 30:
            score += 1
            rationale.append(f"RSI at {rsi:.1f} suggests oversold conditions.")
            decision_factors.append({
                "signal": "technical",
                "impact": "positive",
                "evidence": f"RSI={rsi:.1f}",
                "action": "Oversold conditions may indicate a buying opportunity"
            })
        elif rsi > 70:
            score -= 1
            rationale.append(f"RSI at {rsi:.1f} suggests overbought conditions.")
            decision_factors.append({
                "signal": "technical",
                "impact": "negative",
                "evidence": f"RSI={rsi:.1f}",
                "action": "Overbought conditions suggest caution"
            })
        else:
            rationale.append(f"RSI at {rsi:.1f} is in a neutral zone.")
            decision_factors.append({
                "signal": "technical",
                "impact": "neutral",
                "evidence": f"RSI={rsi:.1f}",
                "action": "Neutral technical signals"
            })

    # === 3. RISK-ADJUSTED RETURNS ===
    if sharpe is not None:
        if sharpe > 1.0:
            score += 1
            rationale.append(f"Sharpe ratio of {sharpe:.2f} indicates favorable risk-adjusted returns.")
            decision_factors.append({
                "signal": "risk",
                "impact": "positive",
                "evidence": f"Sharpe={sharpe:.2f}",
                "action": "Good risk-adjusted returns support investment"
            })
        elif sharpe < 0.0:
            score -= 1
            rationale.append(f"Sharpe ratio of {sharpe:.2f} indicates weak risk-adjusted returns.")
            decision_factors.append({
                "signal": "risk",
                "impact": "negative",
                "evidence": f"Sharpe={sharpe:.2f}",
                "action": "Poor risk-adjusted returns warrant caution"
            })

    # === 4. PRICE FORECAST ===
    if forecast and current and current > 0:
        upside = ((forecast - current) / current) * 100
        if upside > 5:
            score += 1
            rationale.append(f"7-day forecast implies {upside:.1f}% upside.")
            decision_factors.append({
                "signal": "forecast",
                "impact": "positive",
                "evidence": f"upside={upside:.1f}%",
                "action": "Forecast suggests price appreciation"
            })
        elif upside < -5:
            score -= 1
            rationale.append(f"7-day forecast implies {upside:.1f}% downside.")
            decision_factors.append({
                "signal": "forecast",
                "impact": "negative",
                "evidence": f"downside={abs(upside):.1f}%",
                "action": "Forecast suggests price decline"
            })

    # === 5. FUNDAMENTAL ANALYSIS ===
    if isinstance(pe_valuation, str):
        if pe_valuation.lower() == "undervalued":
            score += 1
            rationale.append("Fundamentals suggest the stock looks undervalued.")
            decision_factors.append({
                "signal": "fundamental",
                "impact": "positive",
                "evidence": "Undervalued",
                "action": "Valuation supports buying opportunity"
            })
        elif pe_valuation.lower() == "overvalued":
            score -= 1
            rationale.append("Fundamentals suggest the stock looks overvalued.")
            decision_factors.append({
                "signal": "fundamental",
                "impact": "negative",
                "evidence": "Overvalued",
                "action": "Valuation suggests caution"
            })

    # === DECISION ===
    if score >= 2:
        recommendation = "BUY"
    elif score <= -2:
        recommendation = "SELL"
    else:
        recommendation = "HOLD"

    confidence = min(0.95, 0.45 + (abs(score) * 0.15))
    
    if not rationale:
        rationale.append("Insufficient strong signals for a high-conviction decision.")

    return {
        "recommendation": recommendation,
        "confidence": round(confidence, 2),
        "reasoning": rationale,
        "decision_factors": decision_factors,
        "summary": "Heuristic synthesis used because Gemini was unavailable.",
        "risk_notes": ["Heuristic fallback used - consider consulting Gemini for more detailed analysis."],
        "upside_catalysts": [],
        "downside_catalysts": [],
        "raw_response": None,
        "source": "heuristic",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# GEMINI RECOMMENDATION ENGINE
# ============================================================================

@dataclass
class GeminiRecommendationEngine:
    """
    Builds a transparent BUY / SELL / HOLD recommendation from all agent outputs.
    
    Features:
    - Structured prompt engineering
    - JSON response parsing with validation
    - Heuristic fallback when Gemini is unavailable
    - Decision factors, risk notes, catalysts extraction
    
    Example:
        >>> engine = GeminiRecommendationEngine()
        >>> result = engine.generate(payload)
        >>> print(result["recommendation"])
        BUY
    """

    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 1024
    top_p: float = 0.95
    top_k: int = 40

    def __post_init__(self) -> None:
        """Load configuration from environment variables."""
        self.model_name = os.getenv("GEMINI_MODEL", self.model_name)
        self.temperature = float(os.getenv("GEMINI_TEMPERATURE", self.temperature))
        self.max_output_tokens = int(os.getenv("GEMINI_MAX_TOKENS", self.max_output_tokens))
        self._model = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the Gemini model with API key."""
        if not GEMINI_AVAILABLE:
            logger.warning("Gemini not available: missing google-generativeai package")
            return

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("Gemini not available: GOOGLE_API_KEY not set")
            return

        try:
            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini model initialized: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self._model = None

    def is_available(self) -> bool:
        """Check if Gemini is available and configured."""
        return self._model is not None and GEMINI_AVAILABLE

    def build_prompt(self, payload: Dict[str, Any]) -> str:
        """
        Build a structured prompt for Gemini.
        
        Args:
            payload: Dictionary containing all agent outputs
            
        Returns:
            Complete prompt string
        """
        # System instruction
        prompt = (
            "You are an institutional equity analyst with 20+ years of experience.\n"
            "Synthesize all available signals into a single investment recommendation.\n\n"
            
            "CRITICAL RULES:\n"
            "1. Use ONLY the evidence provided below\n"
            "2. Do NOT invent facts, prices, or events not in the context\n"
            "3. Be explicit about why each signal supports or weakens the decision\n"
            "4. If data is missing or uncertain, recommend HOLD\n"
            "5. Return ONLY valid JSON (no markdown, no extra text)\n\n"
            
            "The JSON must follow this exact schema:\n"
            "{\n"
            '  "recommendation": "BUY|SELL|HOLD",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "summary": "one concise sentence",\n'
            '  "reasoning": ["bullet 1", "bullet 2", "bullet 3"],\n'
            '  "decision_factors": [\n'
            '    {\n'
            '      "signal": "sentiment|technical|fundamental|forecast|risk|market",\n'
            '      "impact": "positive|negative|neutral",\n'
            '      "evidence": "short evidence string",\n'
            '      "action": "why this matters for the decision"\n'
            '    }\n'
            '  ],\n'
            '  "risk_notes": ["key risk 1", "key risk 2"],\n'
            '  "upside_catalysts": ["positive catalyst 1"],\n'
            '  "downside_catalysts": ["negative catalyst 1"]\n'
            "}\n\n"
        )

        # ===== DATA SECTION =====
        # Ticker & Query
        prompt += f"Ticker: {payload.get('ticker', 'UNKNOWN')}\n"
        prompt += f"User query: {payload.get('user_query') or 'None'}\n\n"

        # Stock Data
        stock_data = payload.get('stock_data') or {}
        if stock_data:
            prompt += "STOCK DATA:\n"
            prompt += f"- Current Price: ${stock_data.get('current_price', 'N/A')}\n"
            prompt += f"- Volume: {stock_data.get('volume', 'N/A')}\n"
            prompt += f"- Market Cap: {stock_data.get('market_cap', 'N/A')}\n\n"

        # Company Info
        company_info = payload.get('company_info') or {}
        if company_info:
            prompt += "COMPANY INFO:\n"
            prompt += f"- Sector: {company_info.get('sector', 'N/A')}\n"
            prompt += f"- P/E Ratio: {company_info.get('pe_ratio', 'N/A')}\n"
            prompt += f"- Dividend Yield: {company_info.get('dividend_yield', 'N/A')}\n\n"

        # Technical Indicators
        technical = payload.get('technical_indicators') or {}
        if technical:
            prompt += "TECHNICAL INDICATORS:\n"
            prompt += f"- RSI: {technical.get('RSI', 'N/A')}\n"
            prompt += f"- MACD: {technical.get('MACD', 'N/A')}\n"
            prompt += f"- SMA 50: {technical.get('SMA_50', 'N/A')}\n"
            prompt += f"- SMA 200: {technical.get('SMA_200', 'N/A')}\n\n"

        # Price Forecast
        forecast = payload.get('price_forecast') or {}
        if forecast:
            prompt += "PRICE FORECAST:\n"
            prompt += f"- Current Price: ${forecast.get('current_price', 'N/A')}\n"
            prompt += f"- 7-Day Forecast: ${forecast.get('forecast_7d', 'N/A')}\n"
            prompt += f"- 30-Day Forecast: ${forecast.get('forecast_30d', 'N/A')}\n\n"

        # Sentiment
        sentiment = payload.get('sentiment_score')
        if sentiment is not None:
            prompt += f"SENTIMENT SCORE: {sentiment:.3f}\n"
        sentiment_conf = payload.get('sentiment_confidence')
        if sentiment_conf is not None:
            prompt += f"SENTIMENT CONFIDENCE: {sentiment_conf:.2f}\n"
        
        news_summary = payload.get('news_summary')
        if news_summary:
            prompt += f"NEWS SUMMARY: {news_summary}\n"
        
        key_events = payload.get('key_events') or []
        if key_events:
            prompt += f"KEY EVENTS: {', '.join(key_events[:5])}\n\n"

        # Risk Metrics
        risk = payload.get('risk_metrics') or {}
        if risk:
            prompt += "RISK METRICS:\n"
            prompt += f"- Volatility: {risk.get('volatility', 'N/A')}\n"
            prompt += f"- Sharpe Ratio: {risk.get('Sharpe_ratio', 'N/A')}\n"
            prompt += f"- Max Drawdown: {risk.get('max_drawdown', 'N/A')}\n"
            prompt += f"- VaR (95%): {risk.get('var_95', 'N/A')}\n\n"

        # Fundamental Analysis
        fundamental = payload.get('fundamental_analysis') or {}
        if fundamental:
            prompt += f"FUNDAMENTAL ANALYSIS:\n"
            prompt += f"- Valuation: {fundamental.get('valuation', 'N/A')}\n"
            prompt += f"- Profitability: {fundamental.get('profitability', 'N/A')}\n\n"

        # Market Context
        market = payload.get('market_context') or {}
        if market:
            prompt += f"MARKET CONTEXT:\n"
            prompt += f"- Trend: {market.get('trend', 'N/A')}\n"
            prompt += f"- Sector Performance: {market.get('sector_performance', 'N/A')}\n\n"

        # Final instruction
        prompt += (
            "Based on ALL the evidence above, provide your recommendation.\n"
            "Be strict, transparent, and conservative when confidence is weak.\n"
            "Return ONLY valid JSON as specified."
        )

        return prompt

    def _parse_gemini_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Parse and validate Gemini's JSON response.
        
        Args:
            raw_text: Raw response from Gemini
            
        Returns:
            Parsed and validated dictionary
        """
        parsed = _safe_json_loads(raw_text)
        if not parsed:
            logger.warning("Failed to parse Gemini response as JSON")
            return {}

        # Normalize fields
        parsed["recommendation"] = _normalize_recommendation(parsed.get("recommendation"))
        parsed["confidence"] = _normalize_confidence(parsed.get("confidence"))
        parsed["reasoning"] = self._normalize_list(parsed.get("reasoning"))
        parsed["decision_factors"] = self._normalize_decision_factors(parsed.get("decision_factors"))
        parsed["risk_notes"] = self._normalize_list(parsed.get("risk_notes"))
        parsed["upside_catalysts"] = self._normalize_list(parsed.get("upside_catalysts"))
        parsed["downside_catalysts"] = self._normalize_list(parsed.get("downside_catalysts"))

        return parsed

    def _normalize_list(self, value: Any) -> List[str]:
        """Normalize a value to a list of strings."""
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _normalize_decision_factors(self, factors: Any) -> List[Dict[str, str]]:
        """Normalize decision factors to a list of dictionaries."""
        if not isinstance(factors, list):
            return []
        
        normalized = []
        for f in factors:
            if isinstance(f, dict):
                normalized.append({
                    "signal": str(f.get("signal", "unknown")),
                    "impact": str(f.get("impact", "neutral")),
                    "evidence": str(f.get("evidence", "")),
                    "action": str(f.get("action", ""))
                })
        return normalized

    def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a recommendation using Gemini or fallback to heuristic.
        
        Args:
            payload: Dictionary containing all agent outputs
            
        Returns:
            Recommendation dictionary with reasoning
        """
        # Check if Gemini is available
        if not self.is_available():
            logger.info("Gemini unavailable, using heuristic fallback")
            return _heuristic_synthesis(payload)

        try:
            # Build and send prompt
            prompt = self.build_prompt(payload)
            logger.debug(f"Prompt sent to Gemini (length: {len(prompt)} chars)")
            
            response = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_output_tokens,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                },
            )
            
            raw_text = getattr(response, "text", "") or ""
            logger.debug(f"Gemini response length: {len(raw_text)} chars")
            
            # Parse response
            parsed = self._parse_gemini_response(raw_text)
            
            # Validate and build result
            result = {
                "recommendation": parsed.get("recommendation", "HOLD"),
                "confidence": parsed.get("confidence", 0.5),
                "summary": str(parsed.get("summary", "Gemini synthesized the available evidence.")),
                "reasoning": parsed.get("reasoning", ["Gemini returned no detailed reasoning."]),
                "decision_factors": parsed.get("decision_factors", []),
                "risk_notes": parsed.get("risk_notes", []),
                "upside_catalysts": parsed.get("upside_catalysts", []),
                "downside_catalysts": parsed.get("downside_catalysts", []),
                "raw_response": raw_text,
                "source": "gemini",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Gemini recommendation: {result['recommendation']} (confidence: {result['confidence']:.2f})")
            return result
            
        except Exception as e:
            logger.warning(f"Gemini recommendation generation failed: {e}")
            return _heuristic_synthesis(payload)

# ============================================================================
# PUBLIC API
# ============================================================================

def generate_investment_recommendation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a transparent investment recommendation.
    
    This is the main entry point for generating recommendations.
    It handles both Gemini and heuristic generation.
    
    Args:
        payload: Dictionary containing all agent outputs:
            - ticker: Stock ticker symbol
            - user_query: Optional user query
            - stock_data: Stock data dictionary
            - company_info: Company information
            - technical_indicators: Technical indicators
            - price_forecast: Price forecast
            - sentiment_score: Sentiment score
            - risk_metrics: Risk metrics
            - fundamental_analysis: Fundamental analysis
            - market_context: Market context
            - news_summary: News summary
            - key_events: Key events list
            - entity_sentiments: Entity sentiment dictionary
            - topic_analysis: Topic analysis
            - risk_factors: Risk factors list
    
    Returns:
        Recommendation dictionary with:
            - recommendation: BUY/SELL/HOLD
            - confidence: 0.0-1.0
            - summary: One sentence summary
            - reasoning: List of reasoning bullets
            - decision_factors: List of factors
            - risk_notes: List of risk notes
            - upside_catalysts: List of catalysts
            - downside_catalysts: List of catalysts
            - source: "gemini" or "heuristic"
            - timestamp: ISO format timestamp
    
    Example:
        >>> result = generate_investment_recommendation({
        ...     "ticker": "AAPL",
        ...     "sentiment_score": 0.5,
        ...     "technical_indicators": {"RSI": 45}
        ... })
        >>> print(result["recommendation"])
        BUY
    """
    engine = GeminiRecommendationEngine()
    return engine.generate(payload)