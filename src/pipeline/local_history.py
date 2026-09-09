"""Simple on-device analysis history for the Streamlit dashboard."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

try:
    from pymongo import MongoClient
except ImportError:  # pragma: no cover - dependency is optional for local-only use
    MongoClient = None


DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "analysis_history.json"
MAX_HISTORY_ITEMS = 50
DEFAULT_MONGODB_HISTORY_COLLECTION = "analysis_history"


def _history_path(path: Optional[Path] = None) -> Path:
    return path or DEFAULT_HISTORY_PATH


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def create_analysis_id(ticker: str) -> str:
    """Create a unique ID used for both history records and graph threads."""
    return f"{ticker.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"


def _mongodb_history_collection():
    """Return the configured history collection, or None when MongoDB is unavailable."""
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri or MongoClient is None:
        return None

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        database_name = os.getenv("MONGODB_DB_NAME") or os.getenv("MONGODB_DATABASE", "investment_agent_db")
        collection_name = os.getenv("MONGODB_HISTORY_COLLECTION", DEFAULT_MONGODB_HISTORY_COLLECTION)
        collection = client[database_name][collection_name]
        collection.create_index([("saved_at", -1)])
        collection.create_index([("ticker", 1), ("saved_at", -1)])
        return collection
    except Exception as exc:
        logger.warning(f"MongoDB history is unavailable; using local history: {exc}")
        return None


def load_persistent_history(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load MongoDB history when configured, otherwise load the local fallback."""
    collection = _mongodb_history_collection()
    if collection is not None:
        try:
            records = list(collection.find({}, {"_id": 0}).sort("saved_at", -1).limit(MAX_HISTORY_ITEMS))
            if records:
                return records
        except Exception as exc:
            logger.warning(f"Could not read MongoDB analysis history: {exc}")
    return load_local_history(path)


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
    analysis_id = state.get("analysis_id") or create_analysis_id(str(state.get("ticker", "")))
    record = {
        "analysis_id": analysis_id,
        "thread_id": state.get("thread_id") or analysis_id,
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

    collection = _mongodb_history_collection()
    if collection is not None:
        try:
            collection.replace_one(
                {"analysis_id": record["analysis_id"]},
                record,
                upsert=True,
            )
            return record
        except Exception as exc:
            logger.warning(f"Could not save MongoDB analysis history; using local history: {exc}")

    records = [item for item in load_local_history(history_file) if item.get("ticker") != record["ticker"]]
    records.insert(0, record)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = history_file.with_suffix(".tmp")
    temporary_file.write_text(json.dumps(records[:MAX_HISTORY_ITEMS], indent=2), encoding="utf-8")
    temporary_file.replace(history_file)
    return record
