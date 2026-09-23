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


__all__ = ["RetrievalQualityChecker", "evaluate_cases", "evaluate_directory", "evaluate_retrieval_cases"]
