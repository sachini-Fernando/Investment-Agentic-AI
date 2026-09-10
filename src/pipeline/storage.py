"""
MongoDB persistence for market data, analysis results, and news artifacts.
"""

from __future__ import annotations

import os
from uuid import uuid4
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from pymongo import MongoClient
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


def _to_native(value: Any) -> Any:
    try:
        if hasattr(value, "item"):
            return value.item()
    except Exception:
        pass
    if isinstance(value, dict):
        return {key: _to_native(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_native(item) for item in value]
    return value


def create_analysis_id(ticker: str) -> str:
    """Creates a unique identifier for one immutable investment analysis run."""
    return f"{ticker.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"


@dataclass
class MongoPipelineStore:
    """
    Stores market snapshots, news, and analysis outputs in MongoDB.
    """

    mongodb_uri: Optional[str] = None
    database_name: Optional[str] = None

    def __post_init__(self) -> None:
        self.mongodb_uri = self.mongodb_uri or os.getenv("MONGODB_URI")
        self.database_name = self.database_name or os.getenv("MONGODB_DB_NAME") or os.getenv("MONGODB_DATABASE", "investment_agent")
        self._client = None
        self._db = None

    @property
    def available(self) -> bool:
        return bool(PYMONGO_AVAILABLE and self.mongodb_uri)

    @property
    def db(self):
        if not self.available:
            return None
        if self._db is None:
            self._client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self._client.server_info()
            self._db = self._client[self.database_name]
            for collection_name in (
                "analysis_runs",
                "investment_inputs",
                "fundamental_analyses",
                "risk_assessments",
                "recommendations",
            ):
                self._db[collection_name].create_index([('ticker', 1), ('recorded_at', -1)])
        return self._db

    def save_market_bundle(self, bundle: Dict[str, Any]) -> None:
        database = self.db
        if not self.available or database is None:
            logger.info("MongoDB is unavailable. Skipping persistence.")
            return

        ticker = bundle.get("ticker")
        if not ticker:
            return

        payload = _to_native(dict(bundle))
        payload["updated_at"] = datetime.now(timezone.utc)

        snapshot_filter = {"analysis_id": payload.get("analysis_id")} if payload.get("analysis_id") else {"ticker": ticker}
        database.market_snapshots.update_one(
            snapshot_filter,
            {"$set": payload, "$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
            upsert=True,
        )

        for article in payload.get("news_articles", []) or []:
            database.news_articles.update_one(
                {"article_id": article.get("article_id")},
                {"$set": {**article, "ticker": ticker, "updated_at": datetime.now(timezone.utc)}},
                upsert=True,
            )

    def save_analysis_result(self, ticker: str, analysis: Dict[str, Any]) -> None:
        database = self.db
        if not self.available or database is None:
            return

        payload = _to_native(dict(analysis))
        analysis_id = payload.get("analysis_id") or create_analysis_id(ticker)
        recorded_at = datetime.now(timezone.utc)
        common = {
            "analysis_id": analysis_id,
            "ticker": ticker,
            "recorded_at": recorded_at,
        }

        # Keep the complete run and store queryable slices for history and reporting.
        database.analysis_runs.insert_one({**payload, **common})
        database.investment_inputs.insert_one({
            **common,
            **(payload.get("analysis_input") or {}),
            "stock_data": payload.get("stock_data") or {},
            "company_info": payload.get("company_info") or {},
            "financial_statements": payload.get("financial_statements") or {},
            "historical_prices": payload.get("historical_prices") or [],
            "sources_used": payload.get("sources_used") or [],
            "quality_report": payload.get("quality_report") or {},
        })
        database.fundamental_analyses.insert_one({
            **common,
            "fundamental_analysis": payload.get("fundamental_analysis") or {},
        })
        database.risk_assessments.insert_one({
            **common,
            "risk_metrics": payload.get("risk_metrics") or {},
            "risk_factors": payload.get("risk_factors") or [],
        })
        database.recommendations.insert_one({
            **common,
            "technical_indicators": payload.get("technical_indicators") or {},
            "price_forecast": payload.get("price_forecast") or {},
            "recommendation": payload.get("recommendation"),
            "confidence": payload.get("confidence"),
            "validation_status": payload.get("validation_status"),
            "risk_level": payload.get("risk_level"),
            "reasoning": payload.get("reasoning") or [],
            "position_sizing": payload.get("position_sizing"),
            "stop_loss": payload.get("stop_loss"),
            "take_profit": payload.get("take_profit"),
        })

    def save_agent_state(self, state: Dict[str, Any]) -> None:
        """Persists the final LangGraph state as an auditable analysis run."""
        ticker = state.get("ticker")
        if not ticker:
            return

        analysis = {
            "analysis_id": state.get("analysis_id") or create_analysis_id(ticker),
            "ticker": ticker,
            "analysis_input": {
                "user_query": state.get("user_query"),
            },
            "stock_data": state.get("stock_data"),
            "historical_prices": state.get("historical_prices"),
            "company_info": state.get("company_info"),
            "financial_statements": state.get("financial_statements"),
            "news_articles": state.get("news_articles"),
            "search_results": state.get("search_results"),
            "sentiment": {
                "score": state.get("sentiment_score"),
                "confidence": state.get("sentiment_confidence"),
                "breakdown": state.get("sentiment_breakdown"),
                "summary": state.get("news_summary"),
                "key_events": state.get("key_events"),
                "entity_sentiments": state.get("entity_sentiments"),
                "topic_analysis": state.get("topic_analysis"),
            },
            "technical_indicators": state.get("technical_indicators"),
            "price_forecast": state.get("price_forecast"),
            "fundamental_analysis": state.get("fundamental_analysis"),
            "risk_metrics": state.get("risk_metrics"),
            "risk_factors": state.get("risk_factors"),
            "risk_level": state.get("risk_level"),
            "validation_status": state.get("validation_status"),
            "recommendation": state.get("final_recommendation"),
            "confidence": state.get("llm_confidence") or state.get("confidence_score"),
            "reasoning": state.get("llm_reasoning") or state.get("reasoning_chain"),
            "decision_factors": state.get("llm_decision_factors"),
            "summary": state.get("llm_summary"),
            "direct_answer": state.get("direct_answer"),
            "beginner_explanation": state.get("beginner_explanation"),
            "position_sizing": state.get("position_sizing"),
            "stop_loss": state.get("stop_loss"),
            "take_profit": state.get("take_profit"),
            "agent_execution_order": state.get("agent_execution_order"),
            "agent_timestamps": state.get("timestamps"),
            "errors": state.get("errors"),
            "model_info": {
                "llm_model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            },
        }
        self.save_analysis_result(ticker, analysis)

    def save_quality_report(self, ticker: str, quality_report: Dict[str, Any], analysis_id: Optional[str] = None) -> None:
        database = self.db
        if not self.available or database is None:
            return

        payload = _to_native(dict(quality_report))
        payload.update({
            "ticker": ticker,
            "analysis_id": analysis_id,
            "recorded_at": datetime.now(timezone.utc),
        })
        database.quality_reports.insert_one(payload)
