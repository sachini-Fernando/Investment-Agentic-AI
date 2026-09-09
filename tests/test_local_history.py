import pytest

from src.pipeline import local_history
from src.pipeline.local_history import load_local_history, save_analysis_summary


def test_saved_analysis_is_available_after_reload(tmp_path):
    history_path = tmp_path / "history.json"
    save_analysis_summary(
        {"ticker": "aapl", "final_recommendation": "HOLD", "llm_confidence": 0.72},
        history_path,
    )

    history = load_local_history(history_path)

    assert len(history) == 1
    assert history[0]["ticker"] == "AAPL"
    assert history[0]["recommendation"] == "HOLD"


def test_latest_analysis_replaces_old_entry_for_same_ticker(tmp_path):
    history_path = tmp_path / "history.json"
    save_analysis_summary({"ticker": "MSFT", "final_recommendation": "BUY"}, history_path)
    save_analysis_summary({"ticker": "MSFT", "final_recommendation": "HOLD"}, history_path)

    history = load_local_history(history_path)

    assert len(history) == 1
    assert history[0]["recommendation"] == "HOLD"


def test_mongodb_only_save_does_not_write_local_file(monkeypatch, tmp_path):
    monkeypatch.setattr(local_history, "_mongodb_history_collection", lambda: None)
    history_path = tmp_path / "history.json"

    with pytest.raises(RuntimeError, match="MongoDB is required"):
        save_analysis_summary(
            {"ticker": "AAPL", "final_recommendation": "HOLD"},
            history_path,
            allow_local_fallback=False,
        )

    assert not history_path.exists()
