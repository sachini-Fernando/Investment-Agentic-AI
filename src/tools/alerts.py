"""Deterministic alert rules for market and portfolio analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


DEFAULT_ALERT_RULES: Dict[str, Any] = {
    "price_target": {"enabled": False, "target": None, "direction": "above"},
    "rsi": {"enabled": True, "overbought": 70.0, "oversold": 30.0},
    "large_move": {"enabled": True, "threshold_percent": 5.0},
    "negative_news": {"enabled": True, "threshold": -0.5, "lookback_days": 3},
    "earnings": {"enabled": True, "lookahead_days": 7, "lookback_days": 3},
    "portfolio_allocation": {"enabled": True, "limit": 0.10},
}


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _alert(
    alert_type: str,
    message: str,
    value: Any,
    threshold: Any,
    source: str,
    now: Optional[datetime] = None,
    severity: str = "warning",
) -> Dict[str, Any]:
    return {
        "type": alert_type,
        "severity": severity,
        "message": message,
        "value": value,
        "threshold": threshold,
        "source": source,
        "triggered_at": (now or datetime.now(timezone.utc)).isoformat(),
    }


def _recent_negative_news(
    articles: List[Dict[str, Any]], now: datetime, lookback_days: int
) -> Optional[Dict[str, Any]]:
    negative_words = {
        "loss", "miss", "downgrade", "lawsuit", "fraud", "layoff", "decline",
        "weak", "warning", "recall", "investigation", "cuts", "risk",
    }
    cutoff = now - timedelta(days=max(0, lookback_days))
    for article in articles:
        published = _parse_datetime(
            article.get("published_at") or article.get("date")
        )
        if published and published < cutoff:
            continue
        sentiment = article.get("sentiment")
        label = str((sentiment or {}).get("label", "")).upper()
        text = " ".join(
            str(article.get(field) or "")
            for field in ("title", "content", "summary")
        ).lower()
        if label == "NEGATIVE" or any(word in text for word in negative_words):
            return article
    return None


def _earnings_event(
    company_info: Dict[str, Any],
    articles: List[Dict[str, Any]],
    now: datetime,
    lookahead_days: int,
    lookback_days: int,
) -> Optional[str]:
    date_keys = (
        "earnings_date", "next_earnings_date", "earningsDate",
        "earnings_timestamp", "earningsTimestamp",
    )
    for key in date_keys:
        earnings_date = _parse_datetime(company_info.get(key))
        if earnings_date and now - timedelta(days=lookback_days) <= earnings_date <= now + timedelta(days=lookahead_days):
            return earnings_date.date().isoformat()

    cutoff = now - timedelta(days=max(0, lookback_days))
    for article in articles:
        published = _parse_datetime(article.get("published_at") or article.get("date"))
        text = " ".join(str(article.get(field) or "") for field in ("title", "content", "summary")).lower()
        if (not published or published >= cutoff) and "earning" in text:
            return str(article.get("title") or "Recent earnings announcement")
    return None


def evaluate_alerts(
    state: Dict[str, Any],
    rules: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Evaluate configured alerts against one completed analysis state."""
    active_rules = {**DEFAULT_ALERT_RULES, **(rules or {})}
    current_time = now or datetime.now(timezone.utc)
    ticker = str(state.get("ticker") or "the selected ticker").upper()
    stock_data = state.get("stock_data") or {}
    history = state.get("historical_prices") or []
    technical = state.get("technical_indicators") or {}
    articles = state.get("news_articles") or []
    alerts: List[Dict[str, Any]] = []

    price_rule = active_rules.get("price_target") or {}
    price = _number(stock_data.get("current_price"))
    if price is None and history:
        price = _number(history[-1].get("close"))
    target = _number(price_rule.get("target"))
    direction = price_rule.get("direction", "above")
    if price_rule.get("enabled") and price is not None and target is not None:
        reached = price >= target if direction == "above" else price <= target
        if reached:
            alerts.append(_alert(
                "price_target",
                f"{ticker} reached the ${target:.2f} target ({direction}).",
                price,
                target,
                "stock_data",
                current_time,
            ))

    rsi_rule = active_rules.get("rsi") or {}
    rsi = _number(technical.get("RSI"))
    if rsi_rule.get("enabled") and rsi is not None:
        overbought = _number(rsi_rule.get("overbought"))
        oversold = _number(rsi_rule.get("oversold"))
        if overbought is not None and rsi >= overbought:
            alerts.append(_alert("rsi_overbought", f"{ticker} RSI is overbought at {rsi:.1f}.", rsi, overbought, "technical_indicators"))
        elif oversold is not None and rsi <= oversold:
            alerts.append(_alert("rsi_oversold", f"{ticker} RSI is oversold at {rsi:.1f}.", rsi, oversold, "technical_indicators"))

    movement_rule = active_rules.get("large_move") or {}
    previous = _number(stock_data.get("previous_close"))
    if previous is None and len(history) >= 2:
        previous = _number(history[-2].get("close"))
    if price is not None and previous and movement_rule.get("enabled"):
        movement = ((price - previous) / previous) * 100
        threshold = _number(movement_rule.get("threshold_percent"))
        if threshold is not None and abs(movement) >= threshold:
            alerts.append(_alert("large_price_move", f"{ticker} moved {movement:+.2f}% since the previous observation.", movement, threshold, "stock_data", current_time))

    news_rule = active_rules.get("negative_news") or {}
    negative_threshold = _number(news_rule.get("threshold"))
    negative_article = _recent_negative_news(articles, current_time, int(news_rule.get("lookback_days", 3)))
    sentiment = _number(state.get("sentiment_score"))
    if news_rule.get("enabled") and negative_article:
        alerts.append(_alert("negative_news", f"New negative news was detected for {ticker}: {negative_article.get('title') or 'see recent news'}.", sentiment, negative_threshold, "news_articles"))

    earnings_rule = active_rules.get("earnings") or {}
    earnings_event = _earnings_event(state.get("company_info") or {}, articles, current_time, int(earnings_rule.get("lookahead_days", 7)), int(earnings_rule.get("lookback_days", 3)))
    if earnings_rule.get("enabled") and earnings_event:
        alerts.append(_alert("earnings_announcement", f"An earnings announcement is due or was recently reported for {ticker}: {earnings_event}.", earnings_event, earnings_rule.get("lookahead_days", 7), "company_info/news_articles", current_time))

    allocation_rule = active_rules.get("portfolio_allocation") or {}
    profile = state.get("investor_profile") or {}
    insights = state.get("portfolio_insights") or {}
    allocation = _number(insights.get("resulting_ticker_weight"))
    if allocation is None:
        allocation = (_number(profile.get("existing_ticker_weight")) or 0.0) + (_number(profile.get("proposed_weight")) or 0.0)
    limit = _number(allocation_rule.get("limit"))
    if allocation_rule.get("enabled") and limit is not None and allocation > limit:
        alerts.append(_alert("portfolio_allocation", f"{ticker} allocation is {allocation:.1%}, above the {limit:.1%} limit.", allocation, limit, "portfolio_insights", current_time))

    return alerts
