"""Detection primitives for prompt-injection and jailbreak attempts.

This module intentionally uses deterministic, explainable checks.  It is a
guardrail, not a replacement for model-side instruction hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Iterable, List


@dataclass(frozen=True)
class AttackFinding:
    category: str
    severity: str
    pattern: str
    span: tuple[int, int]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["span"] = list(self.span)
        return data


class PromptAttackDetector:
    """Classify common prompt attacks without storing the original prompt."""

    _RULES = (
        ("instruction_override", "high", r"\b(ignore|disregard|override|forget|bypass)\b.{0,80}\b(previous|prior|system|developer|instructions?|rules?)\b"),
        ("jailbreak", "high", r"\b(do anything now|dan mode|jailbreak|developer mode|unrestricted mode)\b"),
        ("prompt_leakage", "high", r"\b(reveal|show|print|dump|repeat|extract)\b.{0,80}\b(system prompt|hidden prompt|developer message|instructions?|api[ _-]?key|secret)\b"),
        ("prompt_injection", "high", r"\b(system\s*:\s*|assistant\s*:\s*|<\s*/?(?:system|instructions?|prompt)\s*>)"),
        ("prompt_manipulation", "medium", r"\b(act as|roleplay as|pretend (?:you are|to be)|simulate)\b.{0,80}\b(system|administrator|developer|unfiltered)\b"),
        ("data_exfiltration", "high", r"\b(send|upload|exfiltrate|export)\b.{0,80}\b(secret|credential|token|password|api[ _-]?key|environment)\b"),
        ("encoding_evasion", "medium", r"\b(base64|rot13|unicode|hex)\b.{0,60}\b(decode|encode|instructions?|prompt)\b"),
    )

    def detect(self, text: object) -> List[AttackFinding]:
        candidate = str(text or "")
        findings = []
        for category, severity, expression in self._RULES:
            for match in re.finditer(expression, candidate, flags=re.IGNORECASE | re.DOTALL):
                findings.append(AttackFinding(category, severity, match.group(0)[:160], match.span()))
        return findings

    def assess(self, text: object) -> dict:
        findings = self.detect(text)
        severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3}
        severity = max((item.severity for item in findings), key=severity_order.get, default="none")
        return {
            "safe": not findings,
            "severity": severity,
            "categories": sorted({item.category for item in findings}),
            "findings": [item.to_dict() for item in findings],
        }


__all__ = ["AttackFinding", "PromptAttackDetector"]
