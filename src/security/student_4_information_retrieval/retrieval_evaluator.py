"""Offline assessment utilities for information retrieval quality and reliability."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


class RetrievalQualityChecker:
    """Checks whether retrieval output is relevant to the user query."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return " ".join(re.findall(r"[a-zA-Z0-9]+", str(value or "").lower()))

    def _keyword_matches(self, query: str, results: Iterable[dict], expected_keywords: list[str]) -> tuple[set[str], float]:
        combined_text = " ".join(
            f"{item.get('title', '')} {item.get('snippet', '')} {item.get('summary', '')} {item.get('content', '')}"
            for item in results
        )
        combined_text = self._normalize_text(combined_text)
        normalized_expected = [self._normalize_text(keyword) for keyword in expected_keywords if keyword]
        matches = {keyword for keyword in normalized_expected if keyword and keyword in combined_text}
        score = len(matches) / len(normalized_expected) if normalized_expected else 1.0
        return matches, score

    def evaluate_case(self, case: dict) -> dict:
        case_id = case.get("id", "unknown")
        query = str(case.get("query") or case.get("input") or "")
        results = case.get("results") or []
        expected_keywords = case.get("expected_keywords") or case.get("expected_terms") or []
        threshold = float(case.get("threshold", self.threshold))

        matches, relevance_score = self._keyword_matches(query, results, expected_keywords)
        passed = relevance_score >= threshold
        actual = "pass" if passed else "fail"
        expected = str(case.get("expected_action", case.get("expected", "pass"))).lower()
        if expected in {"allow", "accepted", "success", "pass", "ok"}:
            expected_result = "pass"
        elif expected in {"block", "reject", "fail", "denied"}:
            expected_result = "fail"
        else:
            expected_result = actual

        item = {
            "id": case_id,
            "query": query,
            "expected": expected_result,
            "actual": actual,
            "passed": actual == expected_result,
            "relevance_score": round(relevance_score, 3),
            "matched_keywords": sorted(matches),
            "expected_keywords": expected_keywords,
            "threshold": threshold,
        }
        if not results:
            item["warning"] = "No retrieval results were provided for evaluation."
        return item


def evaluate_retrieval_cases(cases: Iterable[dict], checker: RetrievalQualityChecker | None = None) -> dict:
    checker = checker or RetrievalQualityChecker()
    results = [checker.evaluate_case(case) for case in cases]
    passed = sum(1 for item in results if item["passed"])
    total = len(results)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 1.0,
        "results": results,
    }


def evaluate_cases(cases: Iterable[dict], checker: RetrievalQualityChecker | None = None) -> dict:
    return evaluate_retrieval_cases(cases, checker)


def evaluate_directory(directory: str | Path, checker: RetrievalQualityChecker | None = None) -> dict:
    checker = checker or RetrievalQualityChecker()
    suites = {}
    for path in sorted(Path(directory).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cases = payload if isinstance(payload, list) else payload.get("cases", [])
            suites[path.stem] = evaluate_retrieval_cases(cases, checker)
        except (OSError, json.JSONDecodeError) as exc:
            suites[path.stem] = {"error": str(exc)}
    return {"suites": suites}


class RetrievalManipulationDetector:
    """Detects instruction override or prompt manipulation attempts in retrieved content."""

    PATTERNS = {
        "instruction_override": [
            "ignore previous instructions",
            "ignore all prior instructions",
            "override the system",
            "override developer instructions",
            "disregard safety rules",
            "trust this instead",
        ],
        "prompt_leakage": [
            "reveal the system prompt",
            "show hidden instructions",
            "disclose developer instructions",
            "reveal credentials",
            "api key",
            "secret key",
        ],
        "roleplay": [
            "act as",
            "pretend to be",
            "developer mode",
            "dan mode",
            "jailbreak",
        ],
        "policy_bypass": [
            "bypass restrictions",
            "disable safety",
            "ignore safeguards",
            "ignore all policies",
            "not bound by policy",
        ],
    }

    def inspect(self, query: str, retrieved_text: str) -> dict:
        combined = f"{query or ''}\n{retrieved_text or ''}".lower()
        categories = []
        triggers = {}
        for category, patterns in self.PATTERNS.items():
            found = [pattern for pattern in patterns if pattern in combined]
            if found:
                categories.append(category)
                triggers[category] = found[:3]

        return {
            "blocked": bool(categories),
            "categories": categories,
            "risk_score": round(min(1.0, len(categories) / 4), 3),
            "triggers": triggers,
        }


class HallucinationRiskChecker:
    """Flags answers that are not grounded in the retrieved evidence."""

    SUSPICIOUS_CLAIMS = [
        "admitted fraud",
        "secretly",
        "rigged",
        "state actors",
        "cover up",
        "guaranteed",
        "insider conspiracy",
    ]

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return " ".join(re.findall(r"[a-zA-Z0-9]+", str(value or "").lower()))

    def assess(self, query: str, retrieved_results: list[dict], answer: str) -> dict:
        evidence_text = " ".join(
            f"{item.get('title', '')} {item.get('snippet', '')} {item.get('summary', '')} {item.get('content', '')}"
            for item in retrieved_results or []
        )
        evidence_terms = set(self._normalize_text(evidence_text).split())
        answer_terms = set(self._normalize_text(answer).split())
        overlap = len(answer_terms & evidence_terms) / max(1, len(answer_terms))
        suspicious_hits = [term for term in self.SUSPICIOUS_CLAIMS if term in self._normalize_text(answer)]
        unsupported_claims = 0
        findings = []

        if not retrieved_results:
            unsupported_claims += 1
            findings.append("no evidence retrieved")
        if suspicious_hits:
            unsupported_claims += len(suspicious_hits)
            findings.append("unsupported narrative claim")
        if overlap < 0.2:
            unsupported_claims += 1
            findings.append("low evidence overlap")

        risk_score = min(1.0, (unsupported_claims / 3) + max(0.0, 0.5 - overlap))
        if risk_score >= 0.7 or unsupported_claims >= 2:
            risk_level = "high"
        elif risk_score >= 0.4 or unsupported_claims:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "unsupported_claims": unsupported_claims,
            "evidence_coverage": round(overlap, 3),
            "findings": findings,
        }


__all__ = [
    "RetrievalQualityChecker",
    "RetrievalManipulationDetector",
    "HallucinationRiskChecker",
    "evaluate_cases",
    "evaluate_directory",
    "evaluate_retrieval_cases",
]
