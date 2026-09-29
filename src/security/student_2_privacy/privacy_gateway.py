"""Reusable privacy boundary for chat requests, responses, and stored data.

 The Streamlit application invokes this module before an analysis and after
 the generated response. Other callers can use the same interface. The
result is plain JSON-compatible data so it can be returned by an API or shown
by a frontend without importing security implementation details.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .privacy_controls import (
    contains_sensitive_key,
    contains_sensitive_value,
    redact_sensitive_value,
    sanitize_audit_mapping,
)


_PRIVATE_REQUEST_PATTERNS = (
    re.compile(r"(?i)\bshow\b.*\b(another|other|someone else|user)\b.*\b(conversation|chat|history|message)s?\b"),
    re.compile(r"(?i)\b(give|show|tell|reveal|provide|find)\b.*\b(user'?s?|another user'?s?)\b.*\b(password|api[ _-]?key|secret|token|credential)s?\b"),
    re.compile(r"(?i)\b(access|read|dump|export)\b.*\b(another|other|someone else|user)\b.*\b(data|account|history|records?)\b"),
    re.compile(r"(?i)\b(show|give|tell|reveal|provide|find|get|what is)\b.*\b(the )?(user'?s?|system'?s?|stored|environment|internal)\b.*\b(password|api[ _-]?key|secret|token|credential)s?\b"),
    re.compile(r"(?i)\b(give|show|tell|reveal|provide|find|get|what is)\b.*\b(password|api[ _-]?key|secret|token|credential)s?\b"),
    re.compile(r"(?i)\bshow\b.*\b(user\s+[a-z0-9_-]+|another user|other user)\b.*\b(previous|past|private)\b.*\b(analysis|conversation|chat|history|record)s?\b"),
)


def _private_request_reason(user_input: Any) -> str | None:
    text = str(user_input or "")
    if contains_sensitive_value(text):
        return "Credential-like material was supplied in the user input."
    if any(pattern.search(text) for pattern in _PRIVATE_REQUEST_PATTERNS):
        return "The request targets another user's private data or credentials."
    return None


def _history_findings(history: Any, user_id: str | None) -> list[str]:
    if history is None:
        return []
    if not isinstance(history, Sequence) or isinstance(history, (str, bytes, bytearray)):
        return ["Conversation history must be a sequence of records."]

    findings = []
    for record in history:
        if not isinstance(record, Mapping):
            findings.append("Conversation history contains a non-record value.")
            continue
        record_user_id = record.get("user_id")
        if user_id and record_user_id not in (user_id, None):
            findings.append("Conversation history contains a record owned by another user.")
    return findings


def _result(
    *,
    allowed: bool,
    status: str,
    reason: str,
    findings: list[str],
    safe_input: str,
    safe_output: str,
    safe_audit_details: dict[str, str],
) -> dict[str, Any]:
    return {
        "allowed": allowed,
        "status": status,
        "reason": reason,
        "findings": findings,
        "safe_input": safe_input,
        "safe_output": safe_output,
        "safe_audit_details": safe_audit_details,
    }


def inspect_privacy(
    *,
    user_input: Any = "",
    user_id: str | None = None,
    history: Any = None,
    generated_response: Any = "",
    audit_details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect a chat exchange and return a JSON-compatible privacy decision.

    ``BLOCKED`` means the caller should not run the analysis or display the
    original content. ``REDACTED`` means the exchange can continue only with
    the returned sanitized values. This function does not authenticate a user;
    it can only validate the identity supplied by its caller.
    """
    safe_input = redact_sensitive_value(user_input)
    safe_output = redact_sensitive_value(generated_response)
    safe_audit_details = sanitize_audit_mapping(audit_details)
    findings: list[str] = []

    request_reason = _private_request_reason(user_input)
    if request_reason:
        findings.append(request_reason)

    findings.extend(_history_findings(history, user_id))

    if contains_sensitive_key(audit_details):
        findings.append("Audit details contain a sensitive field name and were redacted.")
    if contains_sensitive_value(generated_response):
        findings.append("The generated response contains credential-like material and was redacted.")

    blocking_findings = [item for item in findings if "redacted" not in item.lower()]
    if blocking_findings:
        return _result(
            allowed=False,
            status="BLOCKED",
            reason=blocking_findings[0],
            findings=findings,
            safe_input="",
            safe_output=safe_output,
            safe_audit_details=safe_audit_details,
        )

    if findings or safe_input != str(user_input or "") or safe_output != str(generated_response or ""):
        return _result(
            allowed=True,
            status="REDACTED",
            reason="Sensitive values were removed before downstream use.",
            findings=findings,
            safe_input=safe_input,
            safe_output=safe_output,
            safe_audit_details=safe_audit_details,
        )

    return _result(
        allowed=True,
        status="PASS",
        reason="No obvious sensitive information or unauthorized private-data request was detected.",
        findings=[],
        safe_input=safe_input,
        safe_output=safe_output,
        safe_audit_details=safe_audit_details,
    )


__all__ = ["inspect_privacy"]