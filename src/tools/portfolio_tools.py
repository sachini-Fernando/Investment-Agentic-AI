"""Goal-based portfolio guardrails used by the investment workflow.

These calculations are educational planning aids, not personalised financial advice.
"""

from typing import Any, Dict, List


_TARGET_ALLOCATIONS = {
    "Conservative": {"Stocks": 35, "Bonds": 45, "Cash": 20},
    "Balanced": {"Stocks": 60, "Bonds": 30, "Cash": 10},
    "Growth": {"Stocks": 75, "Bonds": 20, "Cash": 5},
    "Aggressive": {"Stocks": 90, "Bonds": 5, "Cash": 5},
}


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
