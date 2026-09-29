"""Prompt-security boundary for the investment recommendation model.

User questions and market/news text are data, never instructions. The
boundary detects attacks, removes sensitive values, labels untrusted content,
and validates model output before it reaches the application.

Coverage:
- Prompt Injection
- Jailbreak Attempts
- Prompt Leakage
- Instruction Override
- Prompt Manipulation
- Prompt Robustness
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from .attack_detector import PromptAttackDetector


REFUSAL_MESSAGE = (
    "I can help with investment research, but I cannot follow requests to override "
    "instructions, reveal hidden prompts, or expose secrets. Please ask a market or portfolio question."
)

ROBUSTNESS_MESSAGE = (
    "I couldn't process that request. Please provide a clear stock ticker and question."
)


_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|AIza|ghp|xox[baprs])[-_A-Za-z0-9]{16,}\b"),
    re.compile(r"(?i)\b(api[_ -]?key|access[_ -]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),  # Base64-like tokens
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
    """Central security boundary for all prompt-based interactions."""

    detector: PromptAttackDetector = None  # type: ignore[assignment]
    max_user_chars: int = 1200
    max_context_chars: int = 4000
    block_threshold: str = "high"  # block at this severity or above

    def __post_init__(self) -> None:
        if self.detector is None:
            self.detector = PromptAttackDetector()

    # ============================================
    # USER QUERY INSPECTION
    # ============================================
    def inspect_user_query(self, query: object) -> Dict[str, Any]:
        """
        Inspect a user query and determine the appropriate action.

        Returns:
            Assessment dictionary with action, severity, categories, etc.
        """
        # Check for empty or whitespace-only input (robustness)
        raw_text = str(query or "").strip()

        if not raw_text:
            return {
                "safe": True,
                "severity": "low",
                "categories": ["empty_input"],
                "areas": ["prompt_robustness"],
                "findings": [],
                "findings_by_area": {},
                "source": "user_query",
                "action": "block",
                "sanitized_text": "",
                "user_message": ROBUSTNESS_MESSAGE,
            }

        # Check length (DoS robustness)
        if len(raw_text) > self.detector.max_input_length:
            return {
                "safe": False,
                "severity": "medium",
                "categories": ["oversized_input"],
                "areas": ["prompt_robustness"],
                "findings": [],
                "findings_by_area": {"prompt_robustness": ["oversized_input"]},
                "source": "user_query",
                "action": "block",
                "sanitized_text": raw_text[:self.max_user_chars],
                "user_message": ROBUSTNESS_MESSAGE,
            }

        # Run attack detection
        assessment = self.detector.assess(query)

        # Determine action based on severity
        severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        current_severity = severity_order.get(assessment["severity"], 0)
        threshold = severity_order.get(self.block_threshold, 3)

        action = "block" if current_severity >= threshold else "allow"

        return {
            **assessment,
            "source": "user_query",
            "action": action,
            "sanitized_text": _compact(query, self.max_user_chars),
            "user_message": REFUSAL_MESSAGE if action == "block" else None,
        }

    # ============================================
    # UNTRUSTED CONTEXT SANITIZATION
    # ============================================
    def sanitize_untrusted_context(
        self, value: object, source: str = "retrieved_context"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitize untrusted content (news, search results, RAG context).

        Returns:
            Tuple of (sanitized_text, assessment)
        """
        assessment = self.detector.assess(value)
        text = _compact(value, self.max_context_chars)

        # Remove high-severity content entirely
        if assessment["severity"] in ("high", "critical"):
            text = "[Untrusted content removed by prompt-security policy.]"
            action = "removed"
        elif assessment["severity"] == "medium":
            # Sanitize but preserve
            text = redact_sensitive_text(text)
            action = "sanitized"
        else:
            action = "preserved"

        assessment.update({
            "source": source,
            "action": action,
            "sanitized_text": text,
        })
        return text, assessment

    # ============================================
    # PREPARE FULL PROMPT CONTEXT
    # ============================================
    def prepare(
        self, query: object, context: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        Prepare a secure prompt context for the model.

        Args:
            query: User query
            context: Dictionary of untrusted context (news, search results)

        Returns:
            Prepared dictionary with safe_query, context, events, blocked flag
        """
        query_assessment = self.inspect_user_query(query)
        protected_context: Dict[str, str] = {}
        context_events: List[Dict[str, Any]] = []

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
            "user_message": query_assessment.get("user_message"),
            "severity": query_assessment["severity"],
            "areas": query_assessment.get("areas", []),
        }

    # ============================================
    # OUTPUT VALIDATION
    # ============================================
    def validate_model_output(self, output: object) -> Tuple[str, Dict[str, Any]]:
        """
        Prevent leaked instructions/credentials from being displayed or persisted.

        Returns:
            Tuple of (cleaned_output, assessment)
        """
        cleaned = redact_sensitive_text(output)
        assessment = self.detector.assess(cleaned)

        # Block if output contains leakage or exfiltration
        leak_categories = {"prompt_leakage", "data_exfiltration"}
        blocked = (
            assessment["severity"] in ("high", "critical")
            and any(cat in leak_categories for cat in assessment["categories"])
        )

        return (
            REFUSAL_MESSAGE if blocked else cleaned,
            {**assessment, "action": "blocked" if blocked else "allowed"},
        )

    # ============================================
    # BATCH EVALUATION HELPER
    # ============================================
    def evaluate_cases(self, cases: Iterable[dict]) -> Dict[str, Any]:
        """
        Evaluate a batch of test cases.

        Args:
            cases: Iterable of test case dictionaries

        Returns:
            Evaluation summary dictionary
        """
        results = []
        area_stats: Dict[str, Dict[str, int]] = {}

        for case in cases:
            prompt = (
                case.get("prompt")
                or case.get("input")
                or case.get("text")
                or ""
            )
            assessment = self.inspect_user_query(prompt)
            expected = case.get("expected_action", case.get("expected", "block"))
            actual = assessment["action"]
            passed = actual == expected
            area = case.get("area", "unknown")

            # Update area stats
            if area not in area_stats:
                area_stats[area] = {"total": 0, "passed": 0, "failed": 0}
            area_stats[area]["total"] += 1
            if passed:
                area_stats[area]["passed"] += 1
            else:
                area_stats[area]["failed"] += 1

            results.append({
                "id": case.get("id", str(len(results) + 1)),
                "area": area,
                "expected": expected,
                "actual": actual,
                "passed": passed,
                "severity": assessment["severity"],
                "categories": assessment["categories"],
                "areas_detected": assessment.get("areas", []),
            })

        passed = sum(1 for item in results if item["passed"])
        total = len(results)

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 1.0,
            "by_area": area_stats,
            "results": results,
        }


__all__ = ["PromptSecurityGateway", "REFUSAL_MESSAGE", "ROBUSTNESS_MESSAGE", "redact_sensitive_text"]