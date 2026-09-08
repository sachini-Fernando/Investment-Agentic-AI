"""Simple on-device analysis history for the Streamlit dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "analysis_history.json"
MAX_HISTORY_ITEMS = 50


def _history_path(path: Optional[Path] = None) -> Path:
    return path or DEFAULT_HISTORY_PATH


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def load_local_history(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load saved summaries, returning an empty list if no history exists yet."""
    history_file = _history_path(path)
    if not history_file.exists():
        return []
    try:
        records = json.loads(history_file.read_text(encoding="utf-8"))
        return records if isinstance(records, list) else []
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"Could not read local analysis history: {exc}")
        return []


def save_analysis_summary(state: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    """Save a compact, beginner-readable record of a completed analysis."""
    history_file = _history_path(path)
    summary = state.get("llm_summary") or "Analysis completed. Open this entry to review the evidence and risks."
    record = {
        "ticker": str(state.get("ticker", "")).upper(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "recommendation": state.get("final_recommendation") or state.get("risk_adjusted_recommendation") or "HOLD",
        "confidence": _as_float(state.get("llm_confidence") or state.get("confidence_score")),
        "risk_level": state.get("risk_level") or "Not available",
        "summary": str(summary),
        "risk_factors": [str(item) for item in (state.get("risk_factors") or [])][:3],
        "question": state.get("user_query") or "General stock review",
    }
    if not record["ticker"]:
        raise ValueError("A ticker is required to save analysis history.")

    records = [item for item in load_local_history(history_file) if item.get("ticker") != record["ticker"]]
    records.insert(0, record)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = history_file.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(records[:MAX_HISTORY_ITEMS], indent=2), encoding="utf-8")
    temporary_file.replace(history_file)
    return record
