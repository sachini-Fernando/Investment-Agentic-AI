"""
LLM synthesis utilities for recommendation generation with Google Gemini.
"""

from __future__ import annotations

import os
import json
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