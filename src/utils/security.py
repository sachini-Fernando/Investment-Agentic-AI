"""Security and compliance primitives for the investment dashboard."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, Optional


TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.=-]{0,14}$")
REQUIRED_SECRET_NAMES = ("SESSION_SECRET",)


class SecurityError(Exception):
    """Base error for rejected security-sensitive operations."""


class AuthenticationError(SecurityError):
    """Raised when credentials or a session are invalid."""


class AuthorizationError(SecurityError):
    """Raised when a user accesses another user's data."""


class RateLimitExceeded(SecurityError):
    """Raised when an external-provider request limit is exceeded."""


class TradingNotAvailable(SecurityError):
    """Raised because analysis does not execute trades."""


def validate_ticker(ticker: str) -> str:
    """Normalize and validate a provider ticker before any network request."""
    normalized = str(ticker or "").strip().upper()
    if not TICKER_PATTERN.fullmatch(normalized):
        raise ValueError("Ticker must be 1-15 characters and contain only letters, numbers, '.', '=' or '-'.")
    return normalized


def hash_password(password: str, iterations: int = 260_000) -> str:
    if len(password or "") < 12:
        raise ValueError("Password must contain at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iteration_text, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iteration_text)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (AttributeError, TypeError, ValueError):
        return False


@dataclass
class SessionManager:
    """Small in-process session registry for the Streamlit process."""

    ttl_seconds: int = 8 * 60 * 60
    _sessions: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {"user_id": user_id, "expires_at": time.time() + self.ttl_seconds}
        return token

    def user_for(self, token: str) -> str:
        session = self._sessions.get(token)
        if not session or session["expires_at"] <= time.time():
            self._sessions.pop(token, None)
            raise AuthenticationError("Your session has expired. Please sign in again.")
        return str(session["user_id"])

    def revoke(self, token: str) -> None:
        self._sessions.pop(token, None)


@dataclass
class SlidingWindowRateLimiter:
    """Thread-safe per-provider limiter for outbound API calls."""

    max_calls: int = 5
    window_seconds: float = 60.0
    _calls: Dict[str, Deque[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, provider: str) -> None:
        now = time.monotonic()
        with self._lock:
            calls = self._calls.setdefault(provider, deque())
            while calls and now - calls[0] >= self.window_seconds:
                calls.popleft()
            if len(calls) >= self.max_calls:
                retry_after = max(1, int(self.window_seconds - (now - calls[0])))
                raise RateLimitExceeded(f"{provider} rate limit reached; retry after {retry_after} seconds.")
            calls.append(now)


def load_secret(name: str, required: bool = False) -> Optional[str]:
    """Read a secret from the environment without logging its value."""
    value = os.getenv(name)
    if required and not value:
        raise SecurityError(f"Required secret {name} is not configured.")
    return value


def validate_secret_configuration() -> None:
    missing = [name for name in REQUIRED_SECRET_NAMES if not os.getenv(name)]
    if missing:
        raise SecurityError(f"Missing required secret configuration: {', '.join(missing)}")


def audit_event(
    action: str,
    user_id: str,
    outcome: str,
    details: Optional[Dict[str, Any]] = None,
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Append a redacted, structured audit event to a local JSONL log."""
    event = {
        "event_id": secrets.token_hex(12),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "user_id": user_id,
        "outcome": outcome,
        "details": details or {},
    }
    audit_path = path or Path(os.getenv("AUDIT_LOG_PATH", "data/audit.log"))
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def authorize_owner(resource: Dict[str, Any], user_id: str) -> None:
    owner_id = resource.get("user_id") or resource.get("owner_id")
    if owner_id != user_id:
        raise AuthorizationError("You are not authorized to access this record.")


def execute_trade(*_: Any, confirmation: bool = False, broker: Any = None, **__: Any) -> None:
    """Reject trading unless an explicit confirmation and broker adapter exist."""
    if not confirmation or broker is None:
        raise TradingNotAvailable(
            "No trade was placed. Explicit confirmation and a configured broker integration are required."
        )
    raise TradingNotAvailable("Broker trading is intentionally unavailable in this analysis-only application.")
