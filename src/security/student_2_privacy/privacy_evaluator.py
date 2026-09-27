"""
Offline evaluator for the Student 2 privacy test-case catalogue.

IMPORTANT:
This module validates the quality and structure of the test
catalogue only.

It does NOT determine whether the application is secure.

A catalogue case is considered valid when:
- required fields are present
- the ID is valid
- the ID is unique
- the catalogue contains T01-T15
- obvious credential-like values are not placed in the input
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .privacy_controls import contains_sensitive_value


# =====================================================================
# REQUIRED FIELDS
# =====================================================================

REQUIRED_FIELDS = (
    "id",
    "area",
    "objective",
    "input",
    "expected",
    "evidence",
)


# =====================================================================
# EXPECTED TEST IDS
# =====================================================================

EXPECTED_TEST_IDS = {
    f"T{i:02d}"
    for i in range(1, 16)
}


# =====================================================================
# CASE EVALUATION
# =====================================================================

def evaluate_cases(
    cases: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate the structure and safety of the privacy test catalogue.

    This function does not test application security.
    """

    cases = list(cases)

    results: list[dict[str, Any]] = []

    seen_ids: set[str] = set()

    for index, case in enumerate(
        cases,
        start=1,
    ):

        case_id = str(
            case.get(
                "id",
                index,
            )
        )

        missing_fields = [
            field
            for field in REQUIRED_FIELDS
            if not case.get(field)
        ]

        duplicate_id = (
            case_id in seen_ids
        )

        seen_ids.add(case_id)

        unexpected_id = (
            case_id not in EXPECTED_TEST_IDS
        )

        contains_sensitive_input = (
            contains_sensitive_value(
                case.get("input")
            )
        )

        valid = (
            not missing_fields
            and not duplicate_id
            and not unexpected_id
            and not contains_sensitive_input
        )

        results.append(
            {
                "id": case_id,
                "valid": valid,
                "missing_fields": missing_fields,
                "duplicate_id": duplicate_id,
                "unexpected_id": unexpected_id,
                "contains_sensitive_input": (
                    contains_sensitive_input
                ),
            }
        )

    valid_count = sum(
        item["valid"]
        for item in results
    )

    invalid_count = (
        len(results) - valid_count
    )

    actual_ids = {
        str(case.get("id"))
        for case in cases
    }

    missing_expected_ids = sorted(
        EXPECTED_TEST_IDS - actual_ids
    )

    unexpected_ids = sorted(
        actual_ids - EXPECTED_TEST_IDS
    )

    return {
        "total": len(results),
        "passed": valid_count,
        "failed": invalid_count,
        "pass_rate": (
            round(
                valid_count / len(results),
                3,
            )
            if results
            else 1.0
        ),
        "expected_test_count": len(
            EXPECTED_TEST_IDS
        ),
        "missing_expected_ids": (
            missing_expected_ids
        ),
        "unexpected_ids": unexpected_ids,
        "results": results,
    }


# =====================================================================
# FILE EVALUATION
# =====================================================================

def evaluate_case_file(
    path: str | Path,
) -> dict[str, Any]:
    """
    Load a JSON test-case catalogue and validate it.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            "Privacy test-case file not found: "
            f"{file_path}"
        )

    payload = json.loads(
        file_path.read_text(
            encoding="utf-8"
        )
    )

    if isinstance(payload, list):
        cases = payload

    elif isinstance(payload, dict):
        cases = payload.get(
            "cases",
            [],
        )

    else:
        cases = []

    return evaluate_cases(cases)


__all__ = [
    "REQUIRED_FIELDS",
    "EXPECTED_TEST_IDS",
    "evaluate_cases",
    "evaluate_case_file",
]