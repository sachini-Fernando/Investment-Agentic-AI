"""Repeatable offline evaluator for prompt-security test suites."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .prompt_security import PromptSecurityGateway


def evaluate_cases(cases: Iterable[dict], gateway: PromptSecurityGateway | None = None) -> dict:
    gateway = gateway or PromptSecurityGateway()
    results = []
    for case in cases:
        prompt = case.get("prompt") or case.get("input") or case.get("text") or ""
        assessment = gateway.inspect_user_query(prompt)
        expected = case.get("expected_action", case.get("expected", "block"))
        actual = assessment["action"]
        results.append({"id": case.get("id", str(len(results) + 1)), "expected": expected, "actual": actual,
                        "passed": actual == expected, "categories": assessment["categories"]})
    passed = sum(item["passed"] for item in results)
    return {"total": len(results), "passed": passed, "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 3) if results else 1.0, "results": results}


def evaluate_directory(directory: str | Path) -> dict:
    suites = {}
    for path in sorted(Path(directory).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cases = payload if isinstance(payload, list) else payload.get("cases", [])
            suites[path.stem] = evaluate_cases(cases)
        except (OSError, json.JSONDecodeError) as exc:
            suites[path.stem] = {"error": str(exc)}
    return {"suites": suites}


__all__ = ["evaluate_cases", "evaluate_directory"]
