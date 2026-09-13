import json
from pathlib import Path

from src.utils.security import (
    check_rate_limit,
    get_secret,
    log_audit_event,
    validate_ticker_symbol,
)


def test_validate_ticker_symbol_accepts_common_symbols():
    assert validate_ticker_symbol("AAPL") == "AAPL"
    assert validate_ticker_symbol("BRK.B") == "BRK.B"
    assert validate_ticker_symbol("  msft  ") == "MSFT"


def test_validate_ticker_symbol_rejects_invalid_values():
    try:
        validate_ticker_symbol("BAD$TICKER")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_rate_limit_and_audit_helpers(tmp_path, monkeypatch):
    monkeypatch.setattr("src.utils.security.PROJECT_ROOT", tmp_path)
    monkeypatch.setattr("src.utils.security.AUDIT_LOG_PATH", tmp_path / "audit.log")
    monkeypatch.setattr("src.utils.security.USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr("src.utils.security.SECRETS_FILE", tmp_path / ".env")

    assert check_rate_limit("user-a", limit=2, window_seconds=60) is True
    assert check_rate_limit("user-a", limit=2, window_seconds=60) is True
    assert check_rate_limit("user-a", limit=2, window_seconds=60) is False

    log_audit_event("user-a", "analysis_run", {"ticker": "AAPL"}, "success")
    assert (tmp_path / "audit.log").exists()
    entries = [json.loads(line) for line in (tmp_path / "audit.log").read_text(encoding="utf-8").splitlines() if line.strip()]
    assert entries[0]["user_id"] == "user-a"

    monkeypatch.setenv("APP_SECRET", "demo-secret")
    assert get_secret("APP_SECRET") == "demo-secret"
