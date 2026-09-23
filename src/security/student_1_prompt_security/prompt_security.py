"""Prompt-security boundary for the investment recommendation model.

User questions and market/news text are data, never instructions.  The
boundary detects attacks, removes sensitive values, labels untrusted content,
and validates model output before it reaches the application.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

from .attack_detector import PromptAttackDetector

REFUSAL_MESSAGE = (
    "I can help with investment research, but I cannot follow requests to override "
    "instructions, reveal hidden prompts, or expose secrets. Please ask a market or portfolio question."
)

_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|AIza|ghp|xox[baprs])[-_A-Za-z0-9]{16,}\b"),
    re.compile(r"(?i)\b(api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"),
)


def redact_sensitive_text(value: object) -> str:
    """Redact credential-like values before they are put into a model prompt/log."""
    text = str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _compact(value: object, limit: int) -> str:
    return re.sub(r"\s+", " ", redact_sensitive_text(value)).strip()[:limit]


@dataclass
class PromptSecurityGateway:
    detector: PromptAttackDetector = None  # type: ignore[assignment]
    max_user_chars: int = 1200
    max_context_chars: int = 4000

    def __post_init__(self) -> None:
        if self.detector is None:
            self.detector = PromptAttackDetector()

    def inspect_user_query(self, query: object) -> Dict[str, Any]:
        assessment = self.detector.assess(query)
        assessment["source"] = "user_query"
        assessment["action"] = "block" if assessment["severity"] == "high" else "allow"
        assessment["sanitized_text"] = _compact(query, self.max_user_chars)
        return assessment

    def sanitize_untrusted_context(self, value: object, source: str = "retrieved_context") -> Tuple[str, Dict[str, Any]]:
        assessment = self.detector.assess(value)
        text = _compact(value, self.max_context_chars)
        # Do not send adversarial retrieved instructions to the model at all.
        if assessment["severity"] == "high":
            text = "[Untrusted content removed by prompt-security policy.]"
            action = "removed"
        else:
            action = "preserved"
        assessment.update({"source": source, "action": action, "sanitized_text": text})
        return text, assessment

    def prepare(self, query: object, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        query_assessment = self.inspect_user_query(query)
        protected_context, context_events = {}, []
        for name, value in (context or {}).items():
            if isinstance(value, (dict, list, tuple)):
                value = json.dumps(value, default=str, ensure_ascii=False)
            clean, assessment = self.sanitize_untrusted_context(value, name)
            protected_context[name] = clean
            context_events.append(assessment)
        blocked = query_assessment["action"] == "block"
        return {
            "blocked": blocked,
            "safe_query": "" if blocked else query_assessment["sanitized_text"],
            "context": protected_context,
            "events": [query_assessment, *context_events],
            "user_message": REFUSAL_MESSAGE if blocked else None,
        }

    def validate_model_output(self, output: object) -> Tuple[str, Dict[str, Any]]:
        """Prevent leaked instructions/credentials from being displayed or persisted."""
        cleaned = redact_sensitive_text(output)
        assessment = self.detector.assess(cleaned)
        blocked = assessment["severity"] == "high" and any(
            kind in {"prompt_leakage", "data_exfiltration"} for kind in assessment["categories"]
        )
        return (REFUSAL_MESSAGE if blocked else cleaned, {**assessment, "action": "blocked" if blocked else "allowed"})


__all__ = ["PromptSecurityGateway", "REFUSAL_MESSAGE", "redact_sensitive_text"]
