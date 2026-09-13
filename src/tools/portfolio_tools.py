"""Portfolio calculations and user-scoped portfolio persistence.

These calculations are educational planning aids, not personalised financial advice.
"""

import json
import math
import os
from pathlib import Path
from statistics import stdev
from typing import Any, Dict, List, Optional


_TARGET_ALLOCATIONS = {
    "Conservative": {"Stocks": 35, "Bonds": 45, "Cash": 20},
    "Balanced": {"Stocks": 60, "Bonds": 30, "Cash": 10},
    "Growth": {"Stocks": 75, "Bonds": 20, "Cash": 5},
    "Aggressive": {"Stocks": 90, "Bonds": 5, "Cash": 5},
}

_PORTFOLIO_FILE = Path(__file__).parents[2] / "data" / "portfolios.json"


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_holding(holding: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one holding and calculate its cost, value, return, and dividends."""
    shares = max(0.0, _number(holding.get("shares")))
    purchase_price = max(0.0, _number(holding.get("purchase_price")))
    current_price = max(0.0, _number(holding.get("current_price"), purchase_price))
    dividend_per_share = max(0.0, _number(holding.get("dividend_per_share")))
    total_dividends = max(0.0, _number(holding.get("total_dividends"), shares * dividend_per_share))
    cost_basis = shares * purchase_price
    current_value = shares * current_price
    total_return = current_value + total_dividends - cost_basis
    historical_returns = holding.get("historical_returns", [])
    if not isinstance(historical_returns, list):
        historical_returns = []
    historical_returns = [_number(value, float("nan")) for value in historical_returns]
    historical_returns = [value for value in historical_returns if math.isfinite(value)]
    return {
        "ticker": str(holding.get("ticker", "")).strip().upper(),
        "company": str(holding.get("company") or holding.get("ticker", "")).strip(),
        "sector": str(holding.get("sector") or "Other").strip(),
        "asset_type": str(holding.get("asset_type") or "Stocks").strip(),
        "shares": shares,
        "purchase_price": purchase_price,
        "current_price": current_price,
        "dividend_per_share": dividend_per_share,
        "total_dividends": total_dividends,
        "cost_basis": cost_basis,
        "current_value": current_value,
        "total_return": total_return,
        "return_percent": total_return / cost_basis if cost_basis else 0.0,
        "annual_volatility": max(0.0, _number(holding.get("annual_volatility"))),
        "historical_returns": historical_returns,
    }


def calculate_portfolio_volatility(holdings: List[Dict[str, Any]]) -> Optional[float]:
    """Calculate annualized portfolio volatility as a decimal.

    When all holdings provide equally sized ``historical_returns`` series, the
    portfolio return series is calculated first and its sample standard
    deviation is annualized using 252 trading days. Otherwise, the function
    combines holding-level ``annual_volatility`` values assuming zero
    correlation, which is a transparent fallback rather than a prediction.
    """
    normalized = [normalize_holding(item) for item in holdings if str(item.get("ticker", "")).strip()]
    total_value = sum(item["current_value"] for item in normalized)
    if not normalized or total_value <= 0:
        return None

    weights = [item["current_value"] / total_value for item in normalized]
    histories = [item["historical_returns"] for item in normalized]
    if histories and all(history and len(history) == len(histories[0]) for history in histories) and len(histories[0]) > 1:
        portfolio_returns = [
            sum(weight * history[index] for weight, history in zip(weights, histories))
            for index in range(len(histories[0]))
        ]
        return stdev(portfolio_returns) * math.sqrt(252)

    if any(item["annual_volatility"] > 0 for item in normalized):
        return math.sqrt(sum((weight * item["annual_volatility"]) ** 2 for weight, item in zip(weights, normalized)))
    return None


def calculate_portfolio_summary(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate portfolio totals, allocations, concentration, and income."""
    normalized = [normalize_holding(item) for item in holdings if str(item.get("ticker", "")).strip()]
    total_cost = sum(item["cost_basis"] for item in normalized)
    total_value = sum(item["current_value"] for item in normalized)
    total_dividends = sum(item["total_dividends"] for item in normalized)
    total_return = total_value + total_dividends - total_cost

    def allocations(key: str) -> Dict[str, float]:
        return {
            label: value / total_value if total_value else 0.0
            for label, value in _group_values(normalized, key).items()
        }

    company_allocations = allocations("ticker")
    largest_ticker, largest_weight = max(company_allocations.items(), key=lambda item: item[1], default=(None, 0.0))
    concentration_alerts = []
    if largest_weight > 0.25:
        concentration_alerts.append(f"{largest_ticker} represents {largest_weight:.0%} of the portfolio, above the 25% concentration guide.")
    sector_allocations = allocations("sector")
    for sector, weight in sector_allocations.items():
        if weight > 0.50:
            concentration_alerts.append(f"{sector} represents {weight:.0%} of the portfolio, above the 50% sector guide.")

    return {
        "holdings": normalized,
        "total_cost": total_cost,
        "total_value": total_value,
        "total_dividends": total_dividends,
        "total_return": total_return,
        "return_percent": total_return / total_cost if total_cost else 0.0,
        "company_allocations": company_allocations,
        "sector_allocations": sector_allocations,
        "asset_type_allocations": allocations("asset_type"),
        "largest_holding": largest_ticker,
        "largest_holding_weight": largest_weight,
        "concentration_status": "Review" if concentration_alerts else "Within guide",
        "concentration_alerts": concentration_alerts,
        "portfolio_volatility": calculate_portfolio_volatility(normalized),
    }


def _group_values(holdings: List[Dict[str, Any]], key: str) -> Dict[str, float]:
    grouped: Dict[str, float] = {}
    for holding in holdings:
        label = holding.get(key) or "Other"
        grouped[label] = grouped.get(label, 0.0) + holding["current_value"]
    return grouped


def suggest_rebalancing(summary: Dict[str, Any], risk_profile: str = "Balanced") -> List[Dict[str, Any]]:
    """Suggest transparent asset-type adjustments against the selected target mix."""
    targets = {key: value / 100 for key, value in _TARGET_ALLOCATIONS.get(risk_profile, _TARGET_ALLOCATIONS["Balanced"]).items()}
    current = summary.get("asset_type_allocations", {})
    suggestions = []
    for asset_type, target in targets.items():
        actual = current.get(asset_type, 0.0)
        difference = target - actual
        if abs(difference) >= 0.05:
            suggestions.append({
                "asset_type": asset_type,
                "current_weight": actual,
                "target_weight": target,
                "difference": difference,
                "action": "Increase" if difference > 0 else "Reduce",
            })
    return sorted(suggestions, key=lambda item: abs(item["difference"]), reverse=True)


def load_portfolio(user_id: str, path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load holdings for one authenticated user; never return another user's data."""
    portfolio_path = path or _PORTFOLIO_FILE
    if not portfolio_path.exists():
        return []
    try:
        records = json.loads(portfolio_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [item for item in records.get(user_id, []) if isinstance(item, dict)]


def save_portfolio(user_id: str, holdings: List[Dict[str, Any]], path: Optional[Path] = None) -> None:
    """Persist holdings under the authenticated user's account."""
    portfolio_path = path or _PORTFOLIO_FILE
    records: Dict[str, List[Dict[str, Any]]] = {}
    if portfolio_path.exists():
        try:
            records = json.loads(portfolio_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            records = {}
    records[user_id] = [normalize_holding(item) for item in holdings]
    portfolio_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = portfolio_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    os.replace(temporary_path, portfolio_path)


def build_portfolio_insights(profile: Dict[str, Any], ticker: str) -> Dict[str, Any]:
    """Translate a user's context into transparent diversification guidance."""
    profile = profile or {}
    risk_profile = profile.get("risk_profile", "Balanced")
    horizon_years = int(profile.get("horizon_years", 10) or 10)
    existing_weight = max(0.0, float(profile.get("existing_ticker_weight", 0) or 0))
    proposed_weight = max(0.0, float(profile.get("proposed_weight", 0) or 0))
    resulting_weight = existing_weight + proposed_weight
    alerts: List[str] = []

    if horizon_years < 3:
        alerts.append("A short investment horizon can make volatile investments less suitable for near-term goals.")
    if profile.get("liquidity_need") == "High":
        alerts.append("Keep an accessible cash reserve before adding long-term or volatile investments.")
    if resulting_weight > 0.10:
        alerts.append(f"{ticker} would be {resulting_weight:.0%} of your portfolio; review single-company concentration.")
    if resulting_weight > 0.20:
        alerts.append("This is above the app's 20% educational concentration alert level.")

    rebalance_action = "No action needed. Review your allocation periodically as markets move."
    if proposed_weight > 0 and resulting_weight <= 0.10:
        rebalance_action = "Fund this idea from an asset class that is above its target allocation."
    elif resulting_weight > 0.10:
        rebalance_action = "Consider reducing or pausing additions until the single-company weight is back within your guardrail."

    return {
        "goal": profile.get("goal", "Long-term growth"),
        "risk_profile": risk_profile,
        "horizon_years": horizon_years,
        "target_allocation": dict(_TARGET_ALLOCATIONS.get(risk_profile, _TARGET_ALLOCATIONS["Balanced"])),
        "existing_ticker_weight": existing_weight,
        "proposed_weight": proposed_weight,
        "resulting_ticker_weight": resulting_weight,
        "concentration_status": "Review" if resulting_weight > 0.10 else "Within guardrail",
        "rebalance_action": rebalance_action,
        "alerts": alerts,
    }