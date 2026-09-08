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
