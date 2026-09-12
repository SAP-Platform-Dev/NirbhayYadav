from typing import Any, Dict


GOVERNANCE_POINTS = {"A": 10, "B": 8, "C": 4, "D": 0}


def calculate_investment_decision(
    quality: Dict[str, Any],
    ratios: Dict[str, Any],
    valuation: Dict[str, Any] | None = None,
    governance_grade: str = "D",
    forensic_clean: bool = True,
) -> Dict[str, Any]:
    """Risk-adjusted deterministic investment decision.

    Keeps business quality, valuation and governance as separate dimensions.
    Forensic/governance failures remain hard blockers rather than being hidden
    inside a single composite score.
    """
    components = quality.get("components", {})
    fundamental_score = sum(
        int(points or 0) for name, points in components.items() if name != "governance"
    )
    governance_score = GOVERNANCE_POINTS.get(str(governance_grade).upper(), 0)

    valuation_score = 0
    valuation_state = "UNAVAILABLE"
    if valuation and valuation.get("available"):
        price = float(valuation.get("current_price") or 0)
        fair_value = float(valuation.get("fair_value") or 0)
        buy_below = float(valuation.get("buy_below") or 0)
        if buy_below > 0 and price <= buy_below:
            valuation_score = 10
            valuation_state = "MARGIN_OF_SAFETY"
        elif fair_value > 0 and price <= fair_value:
            valuation_score = 6
            valuation_state = "BELOW_FAIR_VALUE"
        else:
            valuation_state = "ABOVE_FAIR_VALUE"

    decision_score = fundamental_score + valuation_score + governance_score
    positive_cfo = str(ratios.get("Positive CFO Years", "0/0"))
    cfo_persistent_failure = positive_cfo.startswith("0/")

    if not forensic_clean:
        verdict = "AVOID"
        reason = "Forensic/governance clearance failed; capital preservation overrides the composite score."
    elif cfo_persistent_failure:
        verdict = "AVOID"
        reason = "Operating cash flow is persistently weak; earnings quality is not sufficiently supported by cash generation."
    elif fundamental_score < 40:
        verdict = "AVOID"
        reason = "Core fundamental quality is below the minimum investable threshold."
    elif valuation_score == 10 and fundamental_score >= 60 and governance_score >= 8:
        verdict = "BUY"
        reason = "Strong fundamentals, acceptable governance and a demonstrated margin of safety."
    elif decision_score >= 60:
        verdict = "WATCHLIST"
        if valuation_state == "ABOVE_FAIR_VALUE":
            reason = "Fundamentals are acceptable, but valuation does not provide sufficient margin of safety."
        elif valuation_state == "UNAVAILABLE":
            reason = "Fundamentals are acceptable, but valuation data is unavailable for a high-conviction entry."
        else:
            reason = "Fundamentals are acceptable, but the stock does not yet meet the high-conviction BUY threshold."
    else:
        verdict = "AVOID"
        reason = "Risk-adjusted investment score is below the minimum threshold."

    return {
        "verdict": verdict,
        "reason": reason,
        "decision_score": decision_score,
        "decision_components": {
            "fundamental_quality": fundamental_score,
            "valuation": valuation_score,
            "governance": governance_score,
        },
        "valuation_state": valuation_state,
    }
