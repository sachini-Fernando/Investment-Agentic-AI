"""
Reusable privacy-control helpers for Student 2 security assessment.

These helpers are lightweight detection and sanitization utilities.

They help with:
- credential-like value detection
- sensitive-key detection
- log-value redaction
- audit-detail sanitization

They are NOT a complete PII detector and do not replace:
- authentication
- authorization
- encryption
- secure secret management
- retention controls
"""

from __future__ import annotations

import re
from typing import Any, Mapping


# =====================================================================
# SENSITIVE VALUE PATTERNS
# =====================================================================

_SENSITIVE_PATTERNS = (
    re.compile(
        r"(?i)\b("
        r"api[_ -]?key|"
        r"access[_ -]?token|"
        r"auth[_ -]?token|"
        r"password|"
        r"passwd|"
        r"secret"
        r")\s*[:=]\s*[^\s,;]+"
    ),
    re.compile(
        r"\b(?:sk|AIza|ghp|xox[baprs])[-_A-Za-z0-9]{16,}\b"
    ),
    re.compile(
        r"\b(?:\d[ -]?){13,19}\b"
    ),
)


# =====================================================================
# SENSITIVE KEYS
# =====================================================================

_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pass",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "token",
}


# =====================================================================
# REDACTION
# =====================================================================

def redact_sensitive_value(value: Any) -> str:
    """
    Replace supported credential-like values with [REDACTED].
    """

    text = str(
        value if value is not None else ""
    )

    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(
            "[REDACTED]",
            text,
        )

    return text


# =====================================================================
# VALUE DETECTION
# =====================================================================

def contains_sensitive_value(value: Any) -> bool:
    """
    Return True when the supplied value contains a supported
    credential-like pattern.
    """

    original = str(
        value if value is not None else ""
    )

    redacted = redact_sensitive_value(
        original
    )

    return redacted != original


# =====================================================================
# KEY DETECTION
# =====================================================================

def contains_sensitive_key(
    details: Mapping[str, Any] | None,
) -> bool:
    """
    Return True when a mapping contains an explicitly sensitive key.
    """

    if not details:
        return False

    normalized_keys = {
        str(key).strip().lower()
        for key in details.keys()
    }

    return bool(
        normalized_keys.intersection(
            _SENSITIVE_KEYS
        )
    )


# =====================================================================
# BASIC AUDIT SANITIZATION
# =====================================================================

def sanitize_audit_details(
    details: Mapping[str, Any] | None,
) -> dict[str, str]:
    """
    Sanitize audit-log values using value-based detection.
    """

    if not details:
        return {}

    return {
        str(key): redact_sensitive_value(value)
        for key, value in details.items()
    }


# =====================================================================
# STRONG AUDIT SANITIZATION
# =====================================================================

def sanitize_audit_mapping(
    details: Mapping[str, Any] | None,
) -> dict[str, str]:
    """
    Stronger audit-log sanitization.

    Explicitly sensitive keys are always redacted, even if their
    values do not match a known regular-expression pattern.
    """

    if not details:
        return {}

    sanitized: dict[str, str] = {}

    for key, value in details.items():

        key_text = str(key)
        normalized_key = (
            key_text.strip().lower()
        )

        if normalized_key in _SENSITIVE_KEYS:
            sanitized[key_text] = "[REDACTED]"
        else:
            sanitized[key_text] = (
                redact_sensitive_value(value)
            )

    return sanitized


__all__ = [
    "contains_sensitive_value",
    "contains_sensitive_key",
    "redact_sensitive_value",
    "sanitize_audit_details",
    "sanitize_audit_mapping",
]