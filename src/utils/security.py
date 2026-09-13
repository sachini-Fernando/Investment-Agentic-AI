from __future__ import annotations

import json
import os
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
USERS_FILE = DATA_DIR / "users.json"
AUDIT_LOG_PATH = DATA_DIR / "audit.log"
SECRETS_FILE = PROJECT_ROOT / ".env"

_RATE_LIMIT_WINDOWS: Dict[str, Deque[float]] = defaultdict(deque)


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt_bytes = salt or os.urandom(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 260000)
    return f"pbkdf2_sha256$260000${salt_bytes.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations_int = int(iterations)
    except ValueError:
        return False

    salt_bytes = bytes.fromhex(salt_hex)
    expected = pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, iterations_int)
    return expected.hex() == digest_hex


def _load_users() -> Dict[str, str]:
    _ensure_data_dir()
    if not USERS_FILE.exists():
        return {}
    try:
        payload = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_users(users: Dict[str, str]) -> None:
    _ensure_data_dir()
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def ensure_default_user(username: str = "demo", password: str = "invest123") -> str:
    """Creates a default demo account if none exist so the app remains usable."""
    users = _load_users()
    if username not in users:
        users[username] = _hash_password(password)
        _save_users(users)
    return username


def authenticate_user(username: str, password: str) -> bool:
    user_name = (username or "").strip()
    if not user_name or not password:
        return False

    users = _load_users()
    if not users:
        ensure_default_user()
        users = _load_users()

    stored_hash = users.get(user_name)
    if not stored_hash:
        return False
    return _verify_password(password, stored_hash)


def validate_ticker_symbol(symbol: str) -> str:
    """Normalize a ticker into a safe, recognizable symbol string."""
    if symbol is None:
        raise ValueError("Ticker symbol is required.")

    candidate = str(symbol).strip().upper()
    if not candidate:
        raise ValueError("Ticker symbol is required.")

    if re.fullmatch(r"[A-Z][A-Z0-9.-]{0,10}", candidate) is None:
        raise ValueError("Ticker symbol must contain letters, numbers, dots, or dashes only.")

    if any(char in candidate for char in ("$", "@", "#", "!", "?", " ")):
        raise ValueError("Ticker symbol contains unsupported characters.")

    return candidate


def check_rate_limit(user_id: str, limit: int = 20, window_seconds: int = 60) -> bool:
    """Returns True when the user is still within the allowed request budget."""
    if not user_id:
        return False
    now = time.time()
    bucket = _RATE_LIMIT_WINDOWS[user_id]
    bucket.append(now)
    while bucket and bucket[0] < now - window_seconds:
        bucket.popleft()

    if len(bucket) > limit:
        return False
    return True


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Resolve a secret from environment first, then from a local .env file."""
    value = os.getenv(key)
    if value is not None:
        return value

    if not SECRETS_FILE.exists():
        return default

    try:
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, raw_value = stripped.split("=", 1)
            if name.strip() == key:
                return raw_value.strip().strip('"').strip("'")
    except OSError:
        pass
    return default


def log_audit_event(user_id: str, action: str, details: Optional[Dict[str, Any]] = None, outcome: str = "success") -> Dict[str, Any]:
    """Append a JSON record to the audit log for user actions."""
    _ensure_data_dir()
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id or "anonymous",
        "action": action,
        "details": details or {},
        "outcome": outcome,
    }
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, default=str) + "\n")
    return event


__all__ = [
    "authenticate_user",
    "check_rate_limit",
    "ensure_default_user",
    "get_secret",
    "log_audit_event",
    "validate_ticker_symbol",
]
