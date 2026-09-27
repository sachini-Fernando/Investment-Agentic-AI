"""Detection primitives for prompt-injection and jailbreak attempts.

This module intentionally uses deterministic, explainable checks. It is a
guardrail, not a replacement for model-side instruction hierarchy.

Coverage:
- Prompt Injection
- Jailbreak Attempts
- Prompt Leakage
- Instruction Override
- Prompt Manipulation
- Prompt Robustness
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
import unicodedata
from typing import List, Optional


@dataclass(frozen=True)
class AttackFinding:
    category: str
    severity: str
    pattern: str
    span: tuple[int, int]
    area: str = "unknown"  # Maps to one of the 6 evaluation areas

    def to_dict(self) -> dict:
        data = asdict(self)
        data["span"] = list(self.span)
        return data


class PromptAttackDetector:
    """Classify common prompt attacks without storing the original prompt.

    Each rule maps to one of the six evaluation areas:
    - prompt_injection
    - jailbreak
    - prompt_leakage
    - instruction_override
    - prompt_manipulation
    - prompt_robustness
    """

    _RULES = (
        # ============================================
        # AREA 1: PROMPT INJECTION
        # ============================================
        (
            "prompt_injection",
            "high",
            r"\b(system\s*:\s*|assistant\s*:\s*|<\s*/?(?:system|instructions?|prompt)\s*>)",
            "prompt_injection",
        ),
        (
            "prompt_injection",
            "high",
            r"###\s*(?:override|system|instruction|new\s+rule)",
            "prompt_injection",
        ),
        (
            "prompt_injection",
            "high",
            r"\b(?:translate|summarize|complete|echo|repeat)\b.{0,80}\b(ignore|override|bypass|disregard)\b",
            "prompt_injection",
        ),
        (
            "prompt_injection",
            "medium",
            r"---+\s*(?:new|system|override)\s+(?:instruction|rule|prompt)",
            "prompt_injection",
        ),
        (
            "prompt_injection",
            "medium",
            r"(?:^|\n)\s*(?:NEW|SYSTEM|OVERRIDE)\s+(?:INSTRUCTION|RULE|COMMAND)\s*:",
            "prompt_injection",
        ),

        # ============================================
        # AREA 2: JAILBREAK ATTEMPTS
        # ============================================
        (
            "jailbreak",
            "high",
            r"\b(do anything now|dan mode|jailbreak|developer mode|unrestricted mode|god mode)\b",
            "jailbreak",
        ),
        (
            "jailbreak",
            "high",
            r"\b(stan|aim)\s+(?:mode|persona)\b",
            "jailbreak",
        ),
        (
            "jailbreak",
            "high",
            r"\b(no\s+(?:restrictions?|limits?|rules?|guidelines?|ethics?|filters?))\b",
            "jailbreak",
        ),
        (
            "jailbreak",
            "high",
            r"\b(bypass|disable|remove|turn\s+off)\b.{0,50}\b(safety|filter|restriction|guardrail|guideline|ethics)\b",
            "jailbreak",
        ),
        (
            "jailbreak",
            "medium",
            r"\b(for\s+educational\s+purposes?|for\s+research\s+purposes?|hypothetically|in\s+theory)\b.{0,80}\b(ignore|bypass|unrestricted|no\s+rules)\b",
            "jailbreak",
        ),
        (
            "jailbreak",
            "medium",
            r"\bpretend\s+(?:you\s+are|to\s+be)\b.{0,50}\b(unfiltered|uncensored|unrestricted|without\s+(?:rules|limits|ethics))\b",
            "jailbreak",
        ),

        # ============================================
        # AREA 3: PROMPT LEAKAGE
        # ============================================
        (
            "prompt_leakage",
            "critical",
            r"\b(reveal|show|print|dump|repeat|extract|output|display|give)\b.{0,80}\b(system prompt|hidden prompt|developer message|initial instructions?|api[ _-]?key|secret|credential|password|environment\s+variable)\b",
            "prompt_leakage",
        ),
        (
            "prompt_leakage",
            "high",
            r"\bwhat\s+(?:are|were)\s+your\s+(?:initial|original|system|developer|hidden)\s+(?:instructions?|prompt|rules?|messages?)\b",
            "prompt_leakage",
        ),
        (
            "prompt_leakage",
            "high",
            r"\brepeat\s+(?:the\s+)?(?:words?|text|instructions?)\s+(?:above|before)\b",
            "prompt_leakage",
        ),
        (
            "prompt_leakage",
            "high",
            r"\b(summarize|describe)\s+your\s+(?:system|initial|original|developer)\s+(?:instructions?|prompt|rules?)\b",
            "prompt_leakage",
        ),
        (
            "prompt_leakage",
            "critical",
            r"\b(?:sk|AIza|ghp|xox[baprs])[-_A-Za-z0-9]{10,}",
            "prompt_leakage",
        ),
        (
            "prompt_leakage",
            "critical",
            r"(?i)\b(api[_ -]?key|access[_ -]?token|password|secret|credential)\s*[:=]\s*\S+",
            "prompt_leakage",
        ),

        # ============================================
        # AREA 4: INSTRUCTION OVERRIDE
        # ============================================
        (
            "instruction_override",
            "high",
            r"\b(ignore|disregard|override|forget|bypass|skip|drop)\b.{0,80}\b(previous|prior|system|developer|instructions?|rules?|directives?|guidelines?|task)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "high",
            r"\b(your|the)\s+new\s+(?:primary\s+)?(?:objective|goal|task|instruction|rule|directive)\s+(?:is|:)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "high",
            r"\btreat\s+this\s+(?:message|text|input)\s+as\s+(?:a\s+)?new\s+(?:system\s+)?(?:prompt|instruction|rule)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "high",
            r"\bfrom\s+now\s+on\b.{0,50}\b(?:respond|output|say|recommend|always)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "medium",
            r"\bdo\s+not\s+(?:use|call|run|execute)\b.{0,50}\b(?:agent|tool|function|step|analysis)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "medium",
            r"\bskip\s+(?:the\s+)?\w+\s+(?:step|stage|phase|agent|check)\b",
            "instruction_override",
        ),
        (
            "instruction_override",
            "high",
            r"\bact\s+as\s+(?:the\s+)?(?:system\s+)?(?:administrator|admin|developer|root|superuser)\b",
            "instruction_override",
        ),

        # ============================================
        # AREA 5: PROMPT MANIPULATION
        # ============================================
        (
            "prompt_manipulation",
            "high",
            r"\b(base64|rot13|unicode|hex|binary|morse)\b.{0,60}\b(decode|encode|execute|run|instructions?|prompt|payload)\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"^[A-Za-z0-9+/]{20,}={0,2}$",  # Base64-like string
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\b(if\s+you\s+(?:were|had)\s+(?:to\s+)?(?:ignore|bypass)|hypothetically|in\s+a\s+hypothetical)\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\bcomplete\s+(?:this|the)\s+sentence\b.{0,80}\b(ignore|bypass|recommend|output)\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\b(?:act|roleplay|role-play|pretend)\s+(?:as|to\s+be)\b.{0,60}\b(?:system|administrator|developer|unfiltered|hacker|attacker)\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\brepeat\s+after\s+me\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\becho\s+(?:this|the\s+following)\b",
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "high",
            r"[\u200b\u200c\u200d\u2060\ufeff]",  # Zero-width characters
            "prompt_manipulation",
        ),
        (
            "prompt_manipulation",
            "medium",
            r"\b(?:1gn0r3|pr3v10u5|1n57ruc710n5|0u7pu7)\b",  # Leetspeak
            "prompt_manipulation",
        ),

        # ============================================
        # AREA 6: PROMPT ROBUSTNESS
        # ============================================
        (
            "prompt_robustness",
            "high",
            r"(?:'\s*(?:or|and)\s*'?\d|\b(?:drop|delete|truncate)\s+table\b|--\s*$|;\s*(?:drop|delete|insert|update)\b)",
            "prompt_robustness",  # SQL injection
        ),
        (
            "prompt_robustness",
            "high",
            r"<\s*script\b[^>]*>|javascript\s*:|on(?:error|load|click)\s*=",
            "prompt_robustness",  # XSS
        ),
        (
            "prompt_robustness",
            "medium",
            r"\{\{.*?\}\}|\$\{.*?\}|<%.*?%>",  # Template injection
            "prompt_robustness",
        ),
    )

    # Additional heuristics
    MAX_INPUT_LENGTH = 10000

    def __init__(self, max_input_length: int = MAX_INPUT_LENGTH):
        self.max_input_length = max_input_length

    def detect(self, text: object) -> List[AttackFinding]:
        """Detect all attack patterns in the given text."""
        candidate = str(text or "")
        findings: List[AttackFinding] = []

        # Length check (DoS robustness)
        if len(candidate) > self.max_input_length:
            findings.append(AttackFinding(
                category="oversized_input",
                severity="medium",
                pattern=f"Input length: {len(candidate)}",
                span=(0, len(candidate)),
                area="prompt_robustness",
            ))

        # Normalize unicode for better detection
        normalized = self._normalize(candidate)

        # Run all regex rules
        for category, severity, expression, area in self._RULES:
            try:
                for match in re.finditer(
                    expression,
                    normalized,
                    flags=re.IGNORECASE | re.DOTALL | re.MULTILINE,
                ):
                    findings.append(AttackFinding(
                        category=category,
                        severity=severity,
                        pattern=match.group(0)[:160],
                        span=match.span(),
                        area=area,
                    ))
            except re.error:
                continue

        # Deduplicate overlapping findings
        return self._deduplicate(findings)

    def _normalize(self, text: str) -> str:
        """Normalize unicode and detect zero-width characters."""
        # NFKC normalization
        normalized = unicodedata.normalize("NFKC", text)
        return normalized

    def _deduplicate(self, findings: List[AttackFinding]) -> List[AttackFinding]:
        """Remove duplicate findings based on span overlap and category."""
        seen = set()
        unique = []
        for finding in findings:
            key = (finding.category, finding.span)
            if key not in seen:
                seen.add(key)
                unique.append(finding)
        return unique

    def assess(self, text: object) -> dict:
        """Assess text and return a structured assessment."""
        findings = self.detect(text)

        severity_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        severity = max(
            (item.severity for item in findings),
            key=lambda s: severity_order.get(s, 0),
            default="none",
        )

        # Group findings by area
        by_area = {}
        for finding in findings:
            by_area.setdefault(finding.area, []).append(finding.category)

        return {
            "safe": not findings,
            "severity": severity,
            "categories": sorted({item.category for item in findings}),
            "areas": sorted({item.area for item in findings}),
            "findings_by_area": by_area,
            "findings": [item.to_dict() for item in findings],
            "input_length": len(str(text or "")),
        }


__all__ = ["AttackFinding", "PromptAttackDetector"]