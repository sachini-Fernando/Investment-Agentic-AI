"""
Student 2 - Privacy and Data Leakage Assessment.

Purpose:
    Assess privacy, authentication, authorization, persistence,
    logging, secret handling, and data-retention behaviour.

Safety:
    All automated tests use synthetic data only.

Important:
    Some tests intentionally reproduce insecure behaviour.
    Therefore, a pytest failure may represent a security finding,
    not a defect in the assessment code.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline.local_history import (
    load_local_history,
    load_persistent_history,
    save_analysis_summary,
)
from src.security.student_2_privacy import (
    evaluate_case_file,
)
from src.utils import security


# =====================================================================
# TEST CONSTANTS
# =====================================================================

CANARY = "PRIVACY-CANARY-2026-ALPHA"

SYNTHETIC_PASSWORD = (
    "Disposable-Password-Only"
)

SYNTHETIC_USERNAME = (
    "synthetic_user_identifier"
)

FAKE_PASSWORD = (
    "SYNTHETIC-FAKE-PASSWORD-2026"
)

FAKE_API_KEY = (
    "SYNTHETIC-API-KEY-2026-ONLY"
)

CASE_FILE = (
    Path(__file__).with_name(
        "privacy_test_cases.json"
    )
)

# Project root:
# Investment-Agentic-AI/
PROJECT_ROOT = (
    Path(__file__).resolve().parents[2]
)


# =====================================================================
# HELPERS
# =====================================================================

def _record(
    ticker: str,
    user_id: str | None,
    query: str = CANARY,
) -> dict:
    """
    Create a completely synthetic history record.
    """

    return {
        "ticker": ticker,
        "user_id": user_id,
        "user_query": query,
        "direct_answer": "synthetic answer",
    }


def _load_json_lines(
    path: Path,
) -> list[dict]:
    """
    Load JSON objects from a line-based audit log.
    """

    if not path.exists():
        return []

    entries: list[dict] = []

    for line in path.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        entries.append(
            json.loads(line)
        )

    return entries


def _print_finding(
    test_id: str,
    title: str,
    evidence: str,
) -> None:
    """
    Print a consistent vulnerability-finding format.
    """

    print("\n" + "=" * 70)
    print(f"{test_id} - FINDING DETECTED")
    print("=" * 70)
    print(f"Title    : {title}")
    print(f"Evidence : {evidence}")
    print(
        "Status   : Requires vulnerability analysis"
    )
    print("=" * 70)


# =====================================================================
# T00 - TEST CATALOGUE
# =====================================================================

def test_case_catalog_contains_fifteen_complete_cases():
    """
    Validate the Student 2 test catalogue.

    This is NOT an application security test.
    """

    result = evaluate_case_file(
        CASE_FILE
    )

    print("\n" + "=" * 70)
    print(
        "PRIVACY TEST CATALOGUE VALIDATION"
    )
    print("=" * 70)

    print(
        f"Total cases        : {result['total']}"
    )

    print(
        f"Valid cases        : {result['passed']}"
    )

    print(
        f"Invalid cases      : {result['failed']}"
    )

    print(
        f"Pass rate          : {result['pass_rate']}"
    )

    print(
        f"Missing test IDs   : "
        f"{result['missing_expected_ids']}"
    )

    print(
        f"Unexpected test IDs: "
        f"{result['unexpected_ids']}"
    )

    assert result["total"] == 15
    assert result["failed"] == 0
    assert not result["missing_expected_ids"]
    assert not result["unexpected_ids"]


# =====================================================================
# T01 - CREDENTIAL STORAGE
# =====================================================================

def test_t01_password_file_stores_hash_not_plaintext(
    tmp_path,
    monkeypatch,
):
    """
    Verify that a synthetic password is not stored in plaintext.
    """

    users_file = (
        tmp_path / "users.json"
    )

    monkeypatch.setattr(
        security,
        "USERS_FILE",
        users_file,
    )

    security.ensure_default_user(
        "privacy_user_a",
        SYNTHETIC_PASSWORD,
    )

    raw = users_file.read_text(
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("T01 - Credential Storage")
    print("=" * 70)
    print(raw)

    assert (
        SYNTHETIC_PASSWORD not in raw
    )

    assert (
        "pbkdf2_sha256$" in raw
    )

    print(
        "\nT01 RESULT: SECURITY CONTROL VERIFIED"
    )


# =====================================================================
# T02 - DEFAULT CREDENTIALS
# =====================================================================

def test_t02_default_credentials_are_not_accepted(
    tmp_path,
    monkeypatch,
):
    """
    Check whether default demo credentials are rejected.

    If authentication succeeds, the application behaviour is
    intentionally reported as a security finding.
    """

    users_file = (
        tmp_path / "users.json"
    )

    monkeypatch.setattr(
        security,
        "USERS_FILE",
        users_file,
    )

    security.ensure_default_user()

    result = security.authenticate_user(
        "demo",
        "invest123",
    )

    print("\n" + "=" * 70)
    print("T02 - Default Credential Test")
    print("=" * 70)

    print(
        f"Authentication result: {result}"
    )

    if result is True:

        _print_finding(
            "T02",
            "Default credentials are accepted",
            "Synthetic demo credentials authenticated successfully.",
        )

        pytest.fail(
            "SECURITY FINDING: default demo credentials "
            "are accepted by the current implementation."
        )

    print(
        "\nT02 RESULT: DEFAULT CREDENTIALS REJECTED"
    )


# =====================================================================
# T03 - USER ENUMERATION
# =====================================================================

def test_t03_unknown_user_and_wrong_password_are_rejected(
    tmp_path,
    monkeypatch,
):
    """
    Verify that invalid authentication attempts are rejected.

    Full enumeration resistance may additionally require
    comparing UI/API responses and timing.
    """

    users_file = (
        tmp_path / "users.json"
    )

    monkeypatch.setattr(
        security,
        "USERS_FILE",
        users_file,
    )

    security.ensure_default_user(
        "privacy_user_a",
        SYNTHETIC_PASSWORD,
    )

    unknown_result = (
        security.authenticate_user(
            "unknown_user",
            "bad-password",
        )
    )

    known_user_wrong_password = (
        security.authenticate_user(
            "privacy_user_a",
            "bad-password",
        )
    )

    print("\n" + "=" * 70)
    print("T03 - User Enumeration")
    print("=" * 70)

    print(
        f"Unknown user result       : "
        f"{unknown_result}"
    )

    print(
        f"Known user wrong password : "
        f"{known_user_wrong_password}"
    )

    assert unknown_result is False
    assert (
        known_user_wrong_password is False
    )

    print(
        "\nT03 RESULT: INVALID ATTEMPTS REJECTED"
    )

    print(
        "NOTE: UI/API response comparison "
        "is required for a complete enumeration assessment."
    )


# =====================================================================
# T04 - UNAUTHENTICATED HISTORY ACCESS
# =====================================================================

def test_t04_unauthenticated_history_does_not_return_private_records(
    tmp_path,
):
    """
    Check whether private history is returned when user_id=None.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
        ),
        path,
    )

    records = load_persistent_history(
        path=path,
        user_id=None,
    )

    print("\n" + "=" * 70)
    print(
        "T04 - Unauthenticated History Access"
    )
    print("=" * 70)

    print(records)

    private_records = [
        item
        for item in records
        if item.get("user_id") is not None
    ]

    if private_records:

        _print_finding(
            "T04",
            "Private history returned without user identity",
            f"Returned records: {private_records}",
        )

        pytest.fail(
            "SECURITY FINDING: private user history "
            "is returned when user_id=None."
        )

    print(
        "\nT04 RESULT: NO PRIVATE RECORDS RETURNED"
    )


# =====================================================================
# T05 - CROSS-USER ISOLATION
# =====================================================================

def test_t05_user_scoped_history_excludes_other_user(
    tmp_path,
):
    """
    Positive security control.

    User B must not receive User A's private records.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
            "USER-A-CANARY",
        ),
        path,
    )

    save_analysis_summary(
        _record(
            "MSFT",
            "privacy_user_b",
            "USER-B-CANARY",
        ),
        path,
    )

    records = load_persistent_history(
        path=path,
        user_id="privacy_user_b",
    )

    print("\n" + "=" * 70)
    print("T05 - Cross-User Isolation")
    print("=" * 70)

    print(records)

    assert not any(
        item.get("user_id")
        == "privacy_user_a"
        for item in records
    )

    assert any(
        item.get("user_id")
        == "privacy_user_b"
        for item in records
    )

    print(
        "\nT05 RESULT: CROSS-USER ISOLATION VERIFIED"
    )


# =====================================================================
# T06 - ANONYMOUS RECORDS
# =====================================================================

def test_t06_anonymous_records_are_not_treated_as_private_user_history(
    tmp_path,
):
    """
    Check whether anonymous records are automatically included
    in an authenticated user's private history.

    If returned, report as a privacy-boundary finding requiring
    confirmation of intended application behaviour.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            None,
            "ANONYMOUS-CANARY",
        ),
        path,
    )

    records = load_persistent_history(
        path=path,
        user_id="privacy_user_b",
    )

    print("\n" + "=" * 70)
    print(
        "T06 - Anonymous Record Isolation"
    )
    print("=" * 70)

    print(records)

    anonymous_records = [
        item
        for item in records
        if item.get("user_id") is None
    ]

    if anonymous_records:

        _print_finding(
            "T06",
            "Anonymous records returned in user-scoped history",
            f"Returned records: {anonymous_records}",
        )

        pytest.fail(
            "PRIVACY FINDING: anonymous records are returned "
            "inside User B's history. Confirm whether this is "
            "intentional application behaviour."
        )

    print(
        "\nT06 RESULT: ANONYMOUS RECORDS ISOLATED"
    )


# =====================================================================
# T07 - LOCAL PLAINTEXT PERSISTENCE
# =====================================================================

def test_t07_private_query_is_not_unnecessarily_stored_as_plaintext(
    tmp_path,
):
    """
    Check whether a synthetic private query is directly visible
    in local persistence.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
        ),
        path,
    )

    raw = path.read_text(
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("T07 - Local Persistence")
    print("=" * 70)

    print(raw)

    if CANARY in raw:

        _print_finding(
            "T07",
            "Private query content stored as plaintext",
            f"Canary found directly in {path.name}",
        )

        pytest.fail(
            "PRIVACY FINDING: synthetic private query "
            "is stored directly as plaintext in local persistence."
        )

    print(
        "\nT07 RESULT: CANARY NOT FOUND IN PLAINTEXT"
    )


# =====================================================================
# T08 - HISTORY MINIMIZATION
# =====================================================================

def test_t08_history_record_field_inventory(
    tmp_path,
):
    """
    Inventory persisted fields.

    This test captures the data inventory. It does not automatically
    classify every persisted field as a privacy vulnerability.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
        ),
        path,
    )

    records = load_local_history(
        path
    )

    assert records

    record = records[0]

    fields = sorted(
        record.keys()
    )

    print("\n" + "=" * 70)
    print("T08 - History Field Inventory")
    print("=" * 70)

    print("Persisted fields:")

    for field in fields:
        print(
            f"  - {field}"
        )

    print(
        "\nComplete synthetic record:"
    )

    print(record)

    assert "question" in record
    assert "direct_answer" in record

    print(
        "\nT08 RESULT: DATA INVENTORY CAPTURED"
    )

    print(
        "NOTE: Field necessity should be evaluated "
        "against the application's actual history requirements."
    )


# =====================================================================
# T09 - AUDIT LOG PRIVACY
# =====================================================================

def test_t09_audit_log_does_not_store_credential_like_values(
    tmp_path,
    monkeypatch,
):
    """
    Check whether credential-like audit details are protected.
    """

    audit_path = (
        tmp_path / "audit.log"
    )

    monkeypatch.setattr(
        security,
        "AUDIT_LOG_PATH",
        audit_path,
    )

    security.log_audit_event(
        "privacy_user_a",
        "test",
        {
            "api_key": FAKE_API_KEY,
        },
    )

    raw = audit_path.read_text(
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("T09 - Audit Log Privacy")
    print("=" * 70)

    print(raw)

    if FAKE_API_KEY in raw:

        _print_finding(
            "T09",
            "Credential-like value stored in audit log",
            "Synthetic API-key canary was found in the audit log.",
        )

        pytest.fail(
            "PRIVACY FINDING: credential-like value "
            "is stored in plaintext in the audit log."
        )

    print(
        "\nT09 RESULT: CREDENTIAL-LIKE VALUE NOT FOUND"
    )


# =====================================================================
# T10 - FAILED LOGIN PASSWORD LOGGING
# =====================================================================

def test_t10_failed_login_log_does_not_store_password(
    tmp_path,
    monkeypatch,
):
    """
    Verify that a failed-login event does not store the submitted
    password.
    """

    audit_path = (
        tmp_path / "audit.log"
    )

    monkeypatch.setattr(
        security,
        "AUDIT_LOG_PATH",
        audit_path,
    )

    security.log_audit_event(
        SYNTHETIC_USERNAME,
        "login",
        {
            "source": "security-test",
            "password": FAKE_PASSWORD,
        },
        "failure",
    )

    raw = audit_path.read_text(
        encoding="utf-8"
    )

    print("\n" + "=" * 70)
    print("T10 - Failed Login Privacy")
    print("=" * 70)

    print(raw)

    entries = _load_json_lines(
        audit_path
    )

    assert entries

    print(
        "\nParsed audit entry:"
    )

    print(
        json.dumps(
            entries[0],
            indent=2,
        )
    )

    if FAKE_PASSWORD in raw:

        _print_finding(
            "T10",
            "Failed-login password stored in plaintext audit log",
            "Synthetic password canary was found in the audit log.",
        )

        pytest.fail(
            "SECURITY FINDING: submitted password "
            "is stored in the audit log."
        )

    assert (
        entries[0]["user_id"]
        == SYNTHETIC_USERNAME
    )

    print(
        "\nT10 RESULT: PASSWORD NOT STORED IN LOG"
    )


# =====================================================================
# T11 - SESSION / RETENTION
# =====================================================================

def test_t11_persisted_history_survives_simulated_session_boundary(
    tmp_path,
):
    """
    Document persistence behaviour across a simulated session
    boundary.

    This does not test a real logout API.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
        ),
        path,
    )

    before_session_end = (
        load_local_history(path)
    )

    # Simulated session boundary.
    after_session_end = (
        load_local_history(path)
    )

    print("\n" + "=" * 70)
    print(
        "T11 - Logout / Retention Boundary"
    )
    print("=" * 70)

    print(
        "Before session boundary:"
    )

    print(before_session_end)

    print(
        "\nAfter session boundary:"
    )

    print(after_session_end)

    assert before_session_end
    assert after_session_end

    print(
        "\nT11 RESULT: PERSISTENCE BEHAVIOUR DOCUMENTED"
    )

    print(
        "NOTE: A real logout/session-invalidation test "
        "requires the application's actual session API."
    )


# =====================================================================
# T12 - AUTHORIZATION BOUNDARY
# =====================================================================

def test_t12_history_filter_accepts_caller_supplied_user_id(
    tmp_path,
):
    """
    Document whether the persistence helper accepts a supplied
    user_id.

    This does NOT prove privilege escalation.
    """

    path = (
        tmp_path / "history.json"
    )

    save_analysis_summary(
        _record(
            "AAPL",
            "privacy_user_a",
        ),
        path,
    )

    records = load_persistent_history(
        path=path,
        user_id="privacy_user_a",
    )

    print("\n" + "=" * 70)
    print("T12 - Authorization Boundary")
    print("=" * 70)

    print(records)

    assert records

    assert any(
        item.get("user_id")
        == "privacy_user_a"
        for item in records
    )

    print(
        "\nT12 RESULT: CALLER-SUPPLIED USER ID ACCEPTED"
    )

    print(
        "NOTE: An authenticated User B -> User A "
        "test is required to prove privilege escalation."
    )


# =====================================================================
# T13 - FULL STATE LEAKAGE
# =====================================================================

def test_t13_save_agent_state_contains_user_query_and_user_id():
    """
    Inspect storage.py for user-related state persistence.

    This is source-level privacy analysis.
    """

    storage_file = (
        PROJECT_ROOT
        / "src"
        / "pipeline"
        / "storage.py"
    )

    assert storage_file.exists(), (
        "Expected storage file was not found: "
        f"{storage_file}"
    )

    source = storage_file.read_text(
        encoding="utf-8"
    )

    user_id_present = (
        '"user_id": state.get("user_id")'
        in source
    )

    user_query_present = (
        '"user_query": state.get("user_query")'
        in source
    )

    print("\n" + "=" * 70)
    print(
        "T13 - Full-State Persistence Inspection"
    )
    print("=" * 70)

    print(
        f"Storage file: {storage_file}"
    )

    print(
        f"user_id persisted    : "
        f"{user_id_present}"
    )

    print(
        f"user_query persisted : "
        f"{user_query_present}"
    )

    assert user_id_present
    assert user_query_present

    print(
        "\nT13 RESULT: USER-RELATED STATE PERSISTENCE CONFIRMED"
    )

    print(
        "NOTE: Persistence alone does not prove unauthorized "
        "access or excessive collection."
    )


# =====================================================================
# T14 - SECRET PROTECTION
# =====================================================================

def test_t14_secret_resolution_uses_disposable_local_env(
    tmp_path,
    monkeypatch,
):
    """
    Verify that a disposable fake secret can be resolved locally.

    The actual secret value is never printed.
    """

    secrets_file = (
        tmp_path / ".env"
    )

    fake_secret = (
        "SYNTHETIC-SECRET-ONLY-FOR-TEST"
    )

    secrets_file.write_text(
        f"FAKE_TEST_KEY={fake_secret}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        security,
        "SECRETS_FILE",
        secrets_file,
    )

    monkeypatch.delenv(
        "FAKE_TEST_KEY",
        raising=False,
    )

    result = security.get_secret(
        "FAKE_TEST_KEY"
    )

    print("\n" + "=" * 70)
    print("T14 - Secret Protection")
    print("=" * 70)

    print(
        "Secret resolved:",
        result is not None,
    )

    # Never print result.
    print(
        "Secret value printed: NO"
    )

    assert result == fake_secret

    print(
        "\nT14 RESULT: LOCAL SECRET RESOLUTION VERIFIED"
    )

    print(
        "NOTE: Repository tracking requires a separate Git check."
    )


# =====================================================================
# T15 - DATA ACCESS / EXPORT / DELETION
# =====================================================================

def test_t15_known_local_delete_export_helpers_are_absent():
    """
    Check whether explicit local delete/export helpers exist.

    This checks only the security module. It does not prove that
    equivalent UI/API functionality is absent elsewhere.
    """

    delete_available = hasattr(
        security,
        "delete_user_data",
    )

    export_available = hasattr(
        security,
        "export_user_data",
    )

    print("\n" + "=" * 70)
    print(
        "T15 - Data Access / Export / Deletion"
    )
    print("=" * 70)

    print(
        f"delete_user_data : "
        f"{delete_available}"
    )

    print(
        f"export_user_data : "
        f"{export_available}"
    )

    assert not delete_available
    assert not export_available

    print(
        "\nT15 RESULT: KNOWN LOCAL HELPERS NOT FOUND"
    )

    print(
        "NOTE: Project-wide UI/API/service/documentation "
        "search is required for a complete assessment."
    )