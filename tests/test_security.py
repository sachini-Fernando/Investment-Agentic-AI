from pathlib import Path

import pytest

from src.utils.security import (
    AuthorizationError,
    RateLimitExceeded,
    SessionManager,
    SlidingWindowRateLimiter,
    TradingNotAvailable,
    audit_event,
    authorize_owner,
    execute_trade,
    hash_password,
    validate_ticker,
    verify_password,
)


def test_passwords_are_hashed_and_verifiable():
    encoded = hash_password("correct horse battery staple")

    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_ticker_validation_rejects_injection_like_values():
    assert validate_ticker("aapl") == "AAPL"
    with pytest.raises(ValueError):
        validate_ticker("AAPL;DROP TABLE")


def test_sessions_expire_or_revoke():
    sessions = SessionManager(ttl_seconds=60)
    token = sessions.create("user-1")

    assert sessions.user_for(token) == "user-1"
    sessions.revoke(token)
    with pytest.raises(Exception):
        sessions.user_for(token)


def test_rate_limiter_blocks_excess_calls():
    limiter = SlidingWindowRateLimiter(max_calls=1, window_seconds=60)
    limiter.check("newsapi")
    with pytest.raises(RateLimitExceeded):
        limiter.check("newsapi")


def test_authorization_requires_matching_owner():
    authorize_owner({"user_id": "user-1"}, "user-1")
    with pytest.raises(AuthorizationError):
        authorize_owner({"user_id": "user-1"}, "user-2")


def test_audit_event_writes_structured_record(tmp_path: Path):
    event = audit_event("login", "user-1", "success", {"method": "password"}, tmp_path / "audit.log")

    assert event["user_id"] == "user-1"
    assert '"action": "login"' in (tmp_path / "audit.log").read_text()


def test_trading_requires_confirmation_and_broker_but_remains_disabled():
    with pytest.raises(TradingNotAvailable):
        execute_trade("AAPL", quantity=1)
    with pytest.raises(TradingNotAvailable):
        execute_trade("AAPL", quantity=1, confirmation=True, broker=object())
