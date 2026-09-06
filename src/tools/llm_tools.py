"""
LLM synthesis utilities for recommendation generation with Google Gemini.
"""

from __future__ import annotations

import os
import json
import re
from typing import List
from typing import Optional
from dataclasses import dataclass
from typing import Any, Dict

from loguru import logger


try:
    import google.generativeai as genai

    GEMINI_AVAILABLE = True

except ImportError:
    genai = None  # type: ignore[assignment]
    GEMINI_AVAILABLE = False

    logger.warning(
        "google-generativeai is not available. "
        "Falling back to heuristic recommendations."
    )

def _safe_json_loads(text: str) -> Dict[str, Any]:
    """
    Safely parse JSON returned by Gemini.

    Handles responses wrapped in Markdown code fences.
    """

    if not text:
        return {}

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start:end + 1]

    try:
        return json.loads(cleaned)

    except Exception:
        return {}


def _normalize_recommendation(
    value: Optional[str]
) -> str:
    """
    Normalize Gemini recommendation to BUY, SELL, or HOLD.
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


def _heuristic_synthesis(
    payload: Dict[str, Any]
) -> Dict[str, Any]:

    sentiment = payload.get(
        "sentiment_score"
    )

    rsi = (
        (payload.get("technical_indicators") or {})
        .get("RSI")
    )

    sharpe = (
        (payload.get("risk_metrics") or {})
        .get("Sharpe_ratio")
    )

    forecast = (
        (payload.get("price_forecast") or {})
        .get("forecast_7d")
    )

    current = (
        (payload.get("price_forecast") or {})
        .get("current_price")
    )

    pe = (
        (payload.get("fundamental_analysis") or {})
        .get("pe_analysis", {})
        .get("valuation")
    )

    score = 0

    rationale: List[str] = []

    # Sentiment
    if sentiment is not None:

        if sentiment > 0.25:
            score += 1

            rationale.append(
                f"News sentiment is positive at "
                f"{sentiment:.2f}."
            )

        elif sentiment < -0.25:
            score -= 1

            rationale.append(
                f"News sentiment is negative at "
                f"{sentiment:.2f}."
            )

        else:
            rationale.append(
                f"News sentiment is neutral at "
                f"{sentiment:.2f}."
            )

    # RSI
    if rsi is not None:

        if rsi < 30:
            score += 1

            rationale.append(
                f"RSI at {rsi:.1f} suggests "
                "oversold conditions."
            )

        elif rsi > 70:
            score -= 1

            rationale.append(
                f"RSI at {rsi:.1f} suggests "
                "overbought conditions."
            )

        else:
            rationale.append(
                f"RSI at {rsi:.1f} is in a "
                "neutral zone."
            )

    # Sharpe ratio
    if sharpe is not None:

        if sharpe > 1.0:
            score += 1

            rationale.append(
                f"Sharpe ratio of {sharpe:.2f} "
                "indicates favorable "
                "risk-adjusted returns."
            )

        elif sharpe < 0.0:
            score -= 1

            rationale.append(
                f"Sharpe ratio of {sharpe:.2f} "
                "indicates weak "
                "risk-adjusted returns."
            )

    # Price forecast
    if forecast is not None and current:

        upside = (
            (forecast - current)
            / current
        ) * 100

        if upside > 5:
            score += 1

            rationale.append(
                f"7-day forecast implies "
                f"{upside:.1f}% upside."
            )

        elif upside < -5:
            score -= 1

            rationale.append(
                f"7-day forecast implies "
                f"{upside:.1f}% downside."
            )

    # Fundamental valuation
    if isinstance(pe, str):

        if pe == "Undervalued":
            score += 1

            rationale.append(
                "Fundamentals suggest the "
                "stock looks undervalued."
            )

        elif pe == "Overvalued":
            score -= 1

            rationale.append(
                "Fundamentals suggest the "
                "stock looks overvalued."
            )

    # Recommendation
    if score >= 2:
        recommendation = "BUY"

    elif score <= -2:
        recommendation = "SELL"

    else:
        recommendation = "HOLD"

    confidence = min(
        0.95,
        0.45 + (abs(score) * 0.15)
    )

    if not rationale:
        rationale.append(
            "Insufficient strong signals for "
            "a high-conviction decision."
        )

    decision_factors = [
        {
            "signal": "sentiment",
            "impact": (
                "positive"
                if sentiment is not None
                and sentiment > 0.25
                else "negative"
                if sentiment is not None
                and sentiment < -0.25
                else "neutral"
            ),
            "evidence": (
                f"{sentiment:.2f}"
                if sentiment is not None
                else "N/A"
            ),
        },
        {
            "signal": "technical",
            "impact": (
                "bullish"
                if rsi is not None
                and rsi < 30
                else "bearish"
                if rsi is not None
                and rsi > 70
                else "neutral"
            ),
            "evidence": (
                f"RSI={rsi:.1f}"
                if rsi is not None
                else "N/A"
            ),
        },
        {
            "signal": "risk",
            "impact": (
                "supportive"
                if sharpe is not None
                and sharpe > 1.0
                else "cautionary"
                if sharpe is not None
                and sharpe < 0.0
                else "neutral"
            ),
            "evidence": (
                f"Sharpe={sharpe:.2f}"
                if sharpe is not None
                else "N/A"
            ),
        },
    ]

    return {
        "recommendation": recommendation,
        "confidence": round(
            confidence,
            2
        ),
        "reasoning": rationale,
        "decision_factors": decision_factors,
        "summary": (
            "Heuristic synthesis used because "
            "Gemini was unavailable."
        ),
        "raw_response": None,
        "source": "heuristic",
    }

@dataclass
class GeminiRecommendationEngine:
    """
    Builds a transparent BUY / SELL / HOLD recommendation
    from all agent outputs using Google Gemini.
    """

    model_name: str = "gemini-1.5-flash"
    temperature: float = 0.2
    max_output_tokens: int = 1024

    def __post_init__(self) -> None:
        self.model_name = os.getenv(
            "GEMINI_MODEL",
            self.model_name
        )

    def _build_model(self):
        if not GEMINI_AVAILABLE:
            return None

        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            return None

        genai.configure(api_key=api_key)

        return genai.GenerativeModel(self.model_name)


    def build_prompt(self, payload: Dict[str, Any]) -> str:
    return (
        "You are an institutional equity analyst. "
        "Synthesize all available signals into a single investment "
        "recommendation.\n"

        "Use only the evidence provided below. Be explicit about "
        "why each signal supports or weakens the decision.\n"

        "Return ONLY valid JSON with this schema:\n"

        "{\n"
        '  "recommendation": "BUY|SELL|HOLD",\n'
        '  "confidence": 0.0,\n'
        '  "summary": "one concise sentence",\n'
        '  "reasoning": ["bullet 1", "bullet 2"],\n'

        '  "decision_factors": ['
        '{"signal": "sentiment|technical|fundamental|forecast|risk|market", '
        '"impact": "positive|negative|neutral", '
        '"evidence": "short evidence string", '
        '"action": "why it matters"}],\n'

        '  "risk_notes": ["key risk 1"],\n'
        '  "upside_catalysts": ["key catalyst 1"],\n'
        '  "downside_catalysts": ["key risk 1"]\n'

        "}\n\n"

        f"Ticker: {payload.get('ticker')}\n"

        f"User query: "
        f"{payload.get('user_query') or 'None'}\n"

        f"Stock snapshot: "
        f"{json.dumps(payload.get('stock_data') or {}, default=str)}\n"

        f"Company info: "
        f"{json.dumps(payload.get('company_info') or {}, default=str)}\n"

        f"Financial statements: "
        f"{json.dumps(payload.get('financial_statements') or {}, default=str)}\n"

        f"Technical indicators: "
        f"{json.dumps(payload.get('technical_indicators') or {}, default=str)}\n"

        f"Price forecast: "
        f"{json.dumps(payload.get('price_forecast') or {}, default=str)}\n"

        f"Fundamental analysis: "
        f"{json.dumps(payload.get('fundamental_analysis') or {}, default=str)}\n"

        f"Sentiment score: "
        f"{payload.get('sentiment_score')}\n"

        f"Sentiment confidence: "
        f"{payload.get('sentiment_confidence')}\n"

        f"News summary: "
        f"{payload.get('news_summary') or 'None'}\n"

        f"Key events: "
        f"{json.dumps(payload.get('key_events') or [], default=str)}\n"

        f"Entity sentiments: "
        f"{json.dumps(payload.get('entity_sentiments') or {}, default=str)}\n"

        f"Topic analysis: "
        f"{json.dumps(payload.get('topic_analysis') or {}, default=str)}\n"

        f"Risk metrics: "
        f"{json.dumps(payload.get('risk_metrics') or {}, default=str)}\n"

        f"Risk factors: "
        f"{json.dumps(payload.get('risk_factors') or [], default=str)}\n"

        f"Market context: "
        f"{json.dumps(payload.get('market_context') or {}, default=str)}\n"

        "Be strict, transparent, and conservative "
        "when confidence is weak."
    )

    def generate(
    self,
    payload: Dict[str, Any]
) -> Dict[str, Any]:

    model = self._build_model()

    if model is None:
    return _heuristic_synthesis(payload)

    prompt = self.build_prompt(payload)

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            },
        )

        raw_text = getattr(
            response,
            "text",
            ""
        ) or ""

        parsed = _safe_json_loads(raw_text)

        recommendation = _normalize_recommendation(
            parsed.get("recommendation")
        )

        confidence = parsed.get(
            "confidence",
            0.5
        )

        try:
            confidence = float(confidence)

        except Exception:
            confidence = 0.5

        confidence = max(
            0.0,
            min(1.0, confidence)
        )

        reasoning = parsed.get(
            "reasoning"
        ) or []

        if isinstance(reasoning, str):
            reasoning = [reasoning]

        reasoning = [
            str(item)
            for item in reasoning
            if str(item).strip()
        ]

        decision_factors = (
            parsed.get("decision_factors")
            or []
        )

        if not isinstance(
            decision_factors,
            list
        ):
            decision_factors = []

        return {
            "recommendation": recommendation,
            "confidence": round(
                confidence,
                2
            ),
            "summary": (
                str(
                    parsed.get("summary")
                    or ""
                ).strip()
                or "Gemini synthesized the available evidence."
            ),
            "reasoning": (
                reasoning
                or [
                    "Gemini returned no detailed reasoning; "
                    "using summary only."
                ]
            ),
            "decision_factors": decision_factors,
            "raw_response": raw_text,
            "source": "gemini",
        }

    except Exception as exc:
    logger.warning(
        f"Gemini recommendation generation failed: {exc}"
    )

    return _heuristic_synthesis(payload)






    