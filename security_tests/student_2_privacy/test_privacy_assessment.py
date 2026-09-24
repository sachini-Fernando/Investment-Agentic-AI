"""Safe Student 2 privacy observations using temporary synthetic data only."""

import json
from pathlib import Path

from src.pipeline.local_history import load_local_history, load_persistent_history, save_analysis_summary
from src.utils import security


CANARY = "PRIVACY-CANARY-2026-ALPHA"


def _record(ticker, user_id, query=CANARY):
    return {"ticker": ticker, "user_id": user_id, "user_query": query, "direct_answer": "synthetic answer"}


def test_t01_password_file_stores_hash_not_plaintext(tmp_path, monkeypatch):
    users_file = tmp_path / "users.json"
    monkeypatch.setattr(security, "USERS_FILE", users_file)
    security.ensure_default_user("privacy_user_a", "Disposable-Password-Only")
    raw = users_file.read_text(encoding="utf-8")
    assert "Disposable-Password-Only" not in raw
    assert "pbkdf2_sha256$" in raw


def test_t02_default_credentials_are_accepted_in_current_implementation(tmp_path, monkeypatch):
    monkeypatch.setattr(security, "USERS_FILE", tmp_path / "users.json")
    security.ensure_default_user()
    assert security.authenticate_user("demo", "invest123") is True


def test_t03_unknown_user_and_wrong_password_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(security, "USERS_FILE", tmp_path / "users.json")
    security.ensure_default_user("privacy_user_a", "Disposable-Password-Only")
    assert security.authenticate_user("unknown_user", "bad-password") is False
    assert security.authenticate_user("privacy_user_a", "bad-password") is False


def test_t04_history_loader_returns_records_without_authentication(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    records = load_persistent_history(path=path, user_id=None)
    assert records and records[0]["user_id"] == "privacy_user_a"


def test_t05_user_scoped_history_excludes_other_user(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    save_analysis_summary(_record("MSFT", "privacy_user_b"), path)
    records = load_persistent_history(path=path, user_id="privacy_user_b")
    assert all(item.get("user_id") in (None, "privacy_user_b") for item in records)
    assert not any(item.get("user_id") == "privacy_user_a" for item in records)


def test_t06_anonymous_history_is_returned_to_authenticated_user(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", None), path)
    records = load_persistent_history(path=path, user_id="privacy_user_b")
    assert any(item.get("user_id") is None for item in records)


def test_t07_local_history_contains_canary_query(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    assert CANARY in path.read_text(encoding="utf-8")


def test_t08_history_record_contains_query_and_answer_fields(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    record = load_local_history(path)[0]
    assert {"question", "direct_answer"}.issubset(record)


def test_t09_audit_log_writes_detail_values(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.log"
    monkeypatch.setattr(security, "AUDIT_LOG_PATH", audit_path)
    security.log_audit_event("privacy_user_a", "test", {"note": CANARY})
    assert CANARY in audit_path.read_text(encoding="utf-8")


def test_t10_failed_login_audit_can_contain_submitted_username(tmp_path, monkeypatch):
    audit_path = tmp_path / "audit.log"
    monkeypatch.setattr(security, "AUDIT_LOG_PATH", audit_path)
    submitted_username = "synthetic_user_identifier"
    security.log_audit_event(submitted_username, "login", {"source": "test"}, "failure")
    entry = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["user_id"] == submitted_username


def test_t11_logout_does_not_delete_persisted_history(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    assert load_local_history(path)
    assert path.exists()


def test_t12_history_filter_is_based_on_caller_supplied_user_id(tmp_path):
    path = tmp_path / "history.json"
    save_analysis_summary(_record("AAPL", "privacy_user_a"), path)
    assert load_persistent_history(path=path, user_id="privacy_user_a")[0]["user_id"] == "privacy_user_a"


def test_t13_save_agent_state_source_contains_user_query_and_user_id():
    source = Path("src/pipeline/storage.py").read_text(encoding="utf-8")
    assert '"user_id": state.get("user_id")' in source
    assert '"user_query": state.get("user_query")' in source


def test_t14_secret_resolution_reads_local_env_fallback(tmp_path, monkeypatch):
    secrets_file = tmp_path / ".env"
    secrets_file.write_text("FAKE_TEST_KEY=synthetic-secret\n", encoding="utf-8")
    monkeypatch.setattr(security, "SECRETS_FILE", secrets_file)
    monkeypatch.delenv("FAKE_TEST_KEY", raising=False)
    assert security.get_secret("FAKE_TEST_KEY") == "synthetic-secret"


def test_t15_no_local_delete_or_export_helper_is_exposed():
    assert not hasattr(security, "delete_user_data")
    assert not hasattr(security, "export_user_data")