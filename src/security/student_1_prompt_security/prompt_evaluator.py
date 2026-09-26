"""Repeatable offline evaluator for prompt-security test suites.

Supports all 6 evaluation areas:
- Prompt Injection
- Jailbreak Attempts
- Prompt Leakage
- Instruction Override
- Prompt Manipulation
- Prompt Robustness
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

from .prompt_security import PromptSecurityGateway


# Expected file names for each area
EXPECTED_SUITES = {
    "prompt_injection_tests": "Prompt Injection",
    "jailbreak_tests": "Jailbreak Attempts",
    "prompt_leakage_tests": "Prompt Leakage",
    "instruction_override_tests": "Instruction Override",
    "prompt_manipulation_tests": "Prompt Manipulation",
    "prompt_robustness_tests": "Prompt Robustness",
}


def evaluate_cases(
    cases: Iterable[dict],
    gateway: PromptSecurityGateway | None = None,
) -> dict:
    """
    Evaluate a set of test cases.

    Args:
        cases: Iterable of test case dictionaries
        gateway: Optional PromptSecurityGateway instance

    Returns:
        Evaluation summary
    """
    gateway = gateway or PromptSecurityGateway()

    results = []
    area_stats: Dict[str, Dict[str, int]] = {}

    for case in cases:
        prompt = (
            case.get("prompt")
            or case.get("input")
            or case.get("text")
            or ""
        )
        assessment = gateway.inspect_user_query(prompt)
        expected = case.get("expected_action", case.get("expected", "block"))
        actual = assessment["action"]
        passed = actual == expected
        area = case.get("area", "unknown")

        # Track per-area stats
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
            "prompt_preview": prompt[:80],
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "severity": assessment["severity"],
            "categories": assessment["categories"],
            "areas_detected": assessment.get("areas", []),
        })

    passed = sum(item["passed"] for item in results)
    total = len(results)

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 1.0,
        "by_area": area_stats,
        "results": results,
    }


def evaluate_directory(directory: str | Path) -> dict:
    """
    Evaluate all test suites in a directory.

    Args:
        directory: Path to directory containing JSON test files

    Returns:
        Dictionary with per-suite results and overall summary
    """
    suites: Dict[str, Any] = {}
    all_results = []
    area_stats: Dict[str, Dict[str, int]] = {}

    for path in sorted(Path(directory).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cases = payload if isinstance(payload, list) else payload.get("cases", [])

            suite_name = path.stem
            suite_area = EXPECTED_SUITES.get(suite_name, suite_name)

            result = evaluate_cases(cases)
            result["area_label"] = suite_area
            suites[suite_name] = result

            all_results.extend(result["results"])

            # Aggregate area stats
            for area, stats in result["by_area"].items():
                if area not in area_stats:
                    area_stats[area] = {"total": 0, "passed": 0, "failed": 0}
                for key in ("total", "passed", "failed"):
                    area_stats[area][key] += stats.get(key, 0)

        except (OSError, json.JSONDecodeError) as exc:
            suites[path.stem] = {"error": str(exc)}

    # Overall summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])

    return {
        "overall": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 1.0,
        },
        "by_area": area_stats,
        "suites": suites,
    }


def print_evaluation_report(report: dict) -> None:
    """Print a formatted evaluation report to the console."""
    print("\n" + "=" * 70)
    print("PROMPT SECURITY EVALUATION REPORT")
    print("=" * 70)

    overall = report.get("overall", {})
    print(f"\nOverall: {overall.get('passed', 0)}/{overall.get('total', 0)} passed "
          f"({overall.get('pass_rate', 0) * 100:.1f}%)")

    print("\n" + "-" * 70)
    print("RESULTS BY EVALUATION AREA")
    print("-" * 70)

    for area, stats in sorted(report.get("by_area", {}).items()):
        total = stats.get("total", 0)
        passed = stats.get("passed", 0)
        rate = (passed / total * 100) if total else 0
        status = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
        print(f"{status} {area:30s} | {passed}/{total} passed ({rate:.0f}%)")

    print("\n" + "-" * 70)
    print("PER-SUITE RESULTS")
    print("-" * 70)

    for suite_name, suite_data in sorted(report.get("suites", {}).items()):
        if "error" in suite_data:
            print(f"❌ {suite_name}: ERROR - {suite_data['error']}")
            continue
        rate = suite_data.get("pass_rate", 0) * 100
        print(f"  {suite_name}: {suite_data.get('passed', 0)}/"
              f"{suite_data.get('total', 0)} ({rate:.0f}%)")

    print("=" * 70)


def save_report(report: dict, output_file: str | Path) -> None:
    """Save the evaluation report to a JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\nReport saved to: {output_path}")


__all__ = [
    "evaluate_cases",
    "evaluate_directory",
    "print_evaluation_report",
    "save_report",
]