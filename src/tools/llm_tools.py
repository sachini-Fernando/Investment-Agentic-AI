"""
LLM synthesis utilities for recommendation generation with Google Gemini.
"""

from __future__ import annotations

import os
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