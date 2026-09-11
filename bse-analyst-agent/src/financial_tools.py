from typing import Dict, Any, List
from pydantic import BaseModel, Field


class AnnualFinancials(BaseModel):
    fiscal_year: str = Field(description="Fiscal year label, e.g. FY2026")
    revenue: float = Field(description="Revenue from operations, INR Cr")
    ebit: float = Field(description="Operating profit / EBIT, INR Cr")
    pat: float = Field(description="Profit after tax, INR Cr")
    total_equity: float = Field(description="Total equity, INR Cr")
    total_debt: float = Field(description="Total debt, INR Cr")
    cash: float = Field(description="Cash and cash equivalents, INR Cr")
    cfo: float = Field(description="Cash flow from operations, INR Cr")
    interest_expense: float = Field(description="Interest expense, INR Cr")


class CompanyFinancialHistory(BaseModel):
    company_name: str
    years: List[AnnualFinancials]


def calculate_fundamental_ratios(history: CompanyFinancialHistory) -> Dict[str, Any]:
    years = history.years
    if not years:
        return {}

    latest = years[-1]
    prior = years[-2] if len(years) >= 2 else None

    avg_capital = latest.total_equity + latest.total_debt - latest.cash
    roce = (latest.ebit / avg_capital * 100) if avg_capital else 0.0
    roe = (latest.pat / latest.total_equity * 100) if latest.total_equity else 0.0
    revenue_yoy = ((latest.revenue / prior.revenue) - 1) * 100 if prior and prior.revenue else 0.0
    pat_yoy = ((latest.pat / prior.pat) - 1) * 100 if prior and prior.pat else 0.0

    n = len(years) - 1
    revenue_cagr = ((latest.revenue / years[0].revenue) ** (1 / n) - 1) * 100 if n and years[0].revenue else 0.0
    pat_cagr = ((latest.pat / years[0].pat) ** (1 / n) - 1) * 100 if n and years[0].pat else 0.0
    pat_margin = (latest.pat / latest.revenue * 100) if latest.revenue else 0.0
    debt_equity = (latest.total_debt / latest.total_equity) if latest.total_equity else 0.0
    net_debt = latest.total_debt - latest.cash
    interest_coverage = (latest.ebit / latest.interest_expense) if latest.interest_expense else 0.0
    cfo_pat = (latest.cfo / latest.pat) if latest.pat else 0.0
    cfo_pat_values = [(y.cfo / y.pat) for y in years if y.pat]
    avg_cfo_pat = sum(cfo_pat_values) / len(cfo_pat_values) if cfo_pat_values else 0.0
    positive_cfo_years = sum(1 for y in years if y.cfo > 0)

    hurdles = []
    if roce < 10:
        hurdles.append("ROCE below 10%")
    if roe < 10:
        hurdles.append("ROE below 10%")
    if debt_equity > 1:
        hurdles.append("Debt/Equity above 1")
    if avg_cfo_pat < 0.5:
        hurdles.append("Average CFO/PAT below 0.5")

    return {
        "ROCE": round(roce, 2),
        "ROE": round(roe, 2),
        "Revenue YoY %": round(revenue_yoy, 2),
        "PAT YoY %": round(pat_yoy, 2),
        "Revenue CAGR %": round(revenue_cagr, 2),
        "PAT CAGR %": round(pat_cagr, 2),
        "PAT Margin %": round(pat_margin, 2),
        "Debt to Equity": round(debt_equity, 2),
        "Net Debt": round(net_debt, 2),
        "Interest Coverage": round(interest_coverage, 2),
        "CFO / PAT Quality Ratio": round(cfo_pat, 2),
        "Average CFO / PAT": round(avg_cfo_pat, 2),
        "Positive CFO Years": positive_cfo_years,
        "Total Years": len(years),
        "Hurdles": hurdles,
    }


def calculate_quality_score(ratios: Dict[str, Any], governance_clean: bool = True) -> Dict[str, Any]:
    roce = ratios.get("ROCE", 0)
    roe = ratios.get("ROE", 0)
    revenue_cagr = ratios.get("Revenue CAGR %", 0)
    pat_cagr = ratios.get("PAT CAGR %", 0)
    debt_equity = ratios.get("Debt to Equity", 0)
    net_debt = ratios.get("Net Debt", 0)
    cfo_pat = ratios.get("CFO / PAT Quality Ratio", 0)
    avg_cfo_pat = ratios.get("Average CFO / PAT", 0)

    capital_efficiency = 20 if roce >= 20 else 15 if roce >= 15 else 8 if roce >= 10 else 0
    growth = 20 if revenue_cagr >= 15 and pat_cagr >= 15 else 15 if revenue_cagr >= 10 and pat_cagr >= 10 else 8 if revenue_cagr >= 5 else 0
    balance_sheet = 20 if net_debt <= 0 else 15 if debt_equity <= 0.5 else 10 if debt_equity <= 1 else 0
    cash_quality = 20 if cfo_pat >= 1 and avg_cfo_pat >= 0.8 else 15 if cfo_pat >= 0.7 and avg_cfo_pat >= 0.7 else 8 if avg_cfo_pat >= 0.5 else 0
    governance = 20 if governance_clean else 0

    score = capital_efficiency + growth + balance_sheet + cash_quality + governance
    rating = "INVESTIBLE" if score >= 80 else "WATCHLIST" if score >= 60 else "AVOID"

    return {
        "score_100": score,
        "rating": rating,
        "components": {
            "capital_efficiency": capital_efficiency,
            "growth": growth,
            "balance_sheet": balance_sheet,
            "cash_quality": cash_quality,
            "governance": governance,
        },
    }


def calculate_pe_valuation(
    current_price: float,
    market_cap_cr: float,
    shares_cr: float,
    pat_cr: float,
    pat_cagr_pct: float = 0.0,
    target_pe: float = 20.0,
    margin_of_safety_pct: float = 30.0,
) -> Dict[str, Any]:
    eps = pat_cr / shares_cr if shares_cr else 0.0
    current_pe = current_price / eps if eps else None
    fair_value = eps * target_pe if eps else None
    buy_below = fair_value * (1 - margin_of_safety_pct / 100) if fair_value is not None else None

    return {
        "available": fair_value is not None,
        "current_price": round(current_price, 2),
        "market_cap_cr": round(market_cap_cr, 2),
        "shares_cr": round(shares_cr, 2),
        "eps": round(eps, 2),
        "current_pe": round(current_pe, 2) if current_pe is not None else None,
        "target_pe": round(target_pe, 2),
        "fair_value": round(fair_value, 2) if fair_value is not None else None,
        "margin_of_safety_pct": round(margin_of_safety_pct, 2),
        "buy_below": round(buy_below, 2) if buy_below is not None else None,
        "upside_to_fair_value_pct": round((fair_value / current_price - 1) * 100, 2) if fair_value is not None and current_price else None,
        "pat_cagr_used_pct": round(pat_cagr_pct, 2),
    }


def determine_final_recommendation(
    quality: Dict[str, Any],
    ratios: Dict[str, Any],
    forensic_clean: bool,
    valuation: Dict[str, Any] | None = None,
    governance_grade: str | None = None,
) -> Dict[str, Any]:
    """Compatibility wrapper around the V8 deterministic decision engine."""
    from src.decision_engine import calculate_investment_decision

    if governance_grade is None:
        governance_grade = "A" if forensic_clean else "D"

    return calculate_investment_decision(
        quality=quality,
        ratios=ratios,
        valuation=valuation,
        governance_grade=governance_grade,
        forensic_clean=forensic_clean,
    )
