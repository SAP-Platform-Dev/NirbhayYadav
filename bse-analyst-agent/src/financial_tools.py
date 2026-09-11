from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class AnnualFinancials(BaseModel):
    fiscal_year: str = Field(description="Fiscal year label, e.g. FY2026")
    revenue: float = Field(description="Revenue from operations, INR Cr")
    ebit: Optional[float] = Field(default=None, description="Operating profit / EBIT, INR Cr")
    pat: float = Field(description="Profit after tax attributable to shareholders, INR Cr")
    total_debt: Optional[float] = Field(default=None, description="Total debt including lease liabilities, INR Cr")
    total_equity: Optional[float] = Field(default=None, description="Shareholders' equity / net worth, INR Cr")
    cash_equivalents: Optional[float] = Field(default=None, description="Cash, cash equivalents and current investments, INR Cr")
    cfo: Optional[float] = Field(default=None, description="Cash flow from operating activities, INR Cr")
    interest_expense: Optional[float] = Field(default=None, description="Finance costs / interest expense, INR Cr")
    capex: Optional[float] = Field(default=None, description="Capital expenditure / purchase of PPE and intangibles, INR Cr; positive amount")


class CompanyFinancialHistory(BaseModel):
    years: List[AnnualFinancials] = Field(min_length=1, max_length=10, description="Oldest fiscal year first, latest fiscal year last")
    source: str = Field(default="Unknown", description="Structured financial-data source")
    data_quality: str = Field(default="UNKNOWN", description="HIGH, MEDIUM, LOW, or UNKNOWN")
    source_notes: str = Field(default="", description="Financial-data provenance and validation notes")


CompanyFinancialInputs = AnnualFinancials


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _safe_growth(new: float | None, old: float | None) -> float | None:
    ratio = _safe_div(None if new is None or old is None else new - old, old)
    return ratio * 100.0 if ratio is not None else None


def _safe_cagr(series: list[float | None], periods: int) -> float | None:
    if len(series) < periods:
        return None
    start = series[-periods]
    end = series[-1]
    if start is None or end is None or start <= 0 or end <= 0:
        return None
    return ((end / start) ** (1 / (periods - 1)) - 1) * 100


def _trend(values: list[float | None]) -> str:
    clean = [value for value in values if value is not None]
    if len(clean) < 2:
        return "UNAVAILABLE"
    deltas = [new - old for old, new in zip(clean, clean[1:]) if new != old]
    if not deltas:
        return "STABLE"
    if all(delta > 0 for delta in deltas):
        return "UP"
    if all(delta < 0 for delta in deltas):
        return "DOWN"
    return "MIXED"


def calculate_fundamental_ratios(data: CompanyFinancialHistory) -> Dict[str, Any]:
    years = data.years
    latest = years[-1]
    prior = years[-2] if len(years) > 1 else None

    capital_employed = None
    if latest.total_equity is not None and latest.total_debt is not None and latest.cash_equivalents is not None:
        capital_employed = latest.total_equity + latest.total_debt - latest.cash_equivalents
    roce = _safe_div(latest.ebit, capital_employed)
    roce = roce * 100 if roce is not None and capital_employed and capital_employed > 0 else None
    roe = _safe_div(latest.pat, latest.total_equity)
    roe = roe * 100 if roe is not None else None
    net_debt = None if latest.total_debt is None or latest.cash_equivalents is None else latest.total_debt - latest.cash_equivalents
    de_ratio = _safe_div(latest.total_debt, latest.total_equity)
    interest_coverage = _safe_div(latest.ebit, latest.interest_expense)
    cfo_to_pat = _safe_div(latest.cfo, latest.pat)
    rev_growth_yoy = _safe_growth(latest.revenue, prior.revenue) if prior else None
    pat_growth_yoy = _safe_growth(latest.pat, prior.pat) if prior else None

    revenue_series = [year.revenue for year in years]
    ebit_series = [year.ebit for year in years]
    pat_series = [year.pat for year in years]
    cfo_series = [year.cfo for year in years]
    revenue_cagr_3y = _safe_cagr(revenue_series, 3)
    revenue_cagr_5y = _safe_cagr(revenue_series, 5)
    revenue_cagr_10y = _safe_cagr(revenue_series, 10)
    pat_cagr_3y = _safe_cagr(pat_series, 3)
    pat_cagr_5y = _safe_cagr(pat_series, 5)
    pat_cagr_10y = _safe_cagr(pat_series, 10)
    revenue_cagr = revenue_cagr_5y if revenue_cagr_5y is not None else revenue_cagr_3y
    pat_cagr = pat_cagr_5y if pat_cagr_5y is not None else pat_cagr_3y

    margins = [ratio * 100 for ratio in (_safe_div(y.pat, y.revenue) for y in years) if ratio is not None]
    latest_margin = margins[-1] if margins else None
    avg_margin = sum(margins) / len(margins) if margins else None
    margin_stability = max(margins) - min(margins) if margins else None
    positive_cfo_years = sum(1 for y in years if y.cfo is not None and y.cfo > 0)
    available_cfo_years = sum(1 for y in years if y.cfo is not None)
    conversion = [ratio for ratio in (_safe_div(y.cfo, y.pat) for y in years) if ratio is not None]
    avg_cash_conversion = sum(conversion) / len(conversion) if conversion else None
    roce_series = []
    roe_series = []
    for year in years:
        year_capital = None
        if year.total_equity is not None and year.total_debt is not None and year.cash_equivalents is not None:
            year_capital = year.total_equity + year.total_debt - year.cash_equivalents
        year_roce = _safe_div(year.ebit, year_capital)
        roce_series.append(year_roce * 100 if year_roce is not None and year_capital and year_capital > 0 else None)
        year_roe = _safe_div(year.pat, year.total_equity)
        roe_series.append(year_roe * 100 if year_roe is not None else None)

    hurdles = {
        "roce_above_15": roce is not None and roce >= 15.0,
        "clean_debt": (de_ratio is not None and de_ratio <= 1.0) or (net_debt is not None and net_debt <= 0),
        "cash_conversion_sound": cfo_to_pat is not None and cfo_to_pat >= 0.70,
        "healthy_coverage": interest_coverage is not None and interest_coverage >= 3.5,
        "cfo_positive_history": available_cfo_years > 0 and positive_cfo_years >= max(1, available_cfo_years - 1),
    }

    return {
        "years_analyzed": len(years),
        "history_years_available": len(years),
        "latest_fiscal_year": latest.fiscal_year,
        "financial_data_source": data.source,
        "financial_data_quality": data.data_quality,
        "financial_data_notes": data.source_notes,
        "ROCE (%)": _round(roce),
        "ROE (%)": _round(roe),
        "Revenue YoY Growth (%)": _round(rev_growth_yoy),
        "PAT YoY Growth (%)": _round(pat_growth_yoy),
        "Revenue CAGR (%)": _round(revenue_cagr),
        "PAT CAGR (%)": _round(pat_cagr),
        "Revenue CAGR 3Y (%)": _round(revenue_cagr_3y),
        "Revenue CAGR 5Y (%)": _round(revenue_cagr_5y),
        "Revenue CAGR 10Y (%)": _round(revenue_cagr_10y),
        "PAT CAGR 3Y (%)": _round(pat_cagr_3y),
        "PAT CAGR 5Y (%)": _round(pat_cagr_5y),
        "PAT CAGR 10Y (%)": _round(pat_cagr_10y),
        "Latest PAT Margin (%)": _round(latest_margin),
        "Average PAT Margin (%)": _round(avg_margin),
        "PAT Margin Range (pp)": _round(margin_stability),
        "Debt to Equity": _round(de_ratio),
        "Net Debt (Cr)": _round(net_debt),
        "Interest Coverage Ratio": _round(interest_coverage),
        "CFO / PAT Quality Ratio": _round(cfo_to_pat),
        "Average CFO / PAT (5Y)": _round(avg_cash_conversion),
        "Positive CFO Years": f"{positive_cfo_years}/{available_cfo_years}",
        "trends": {
            "revenue": _trend(revenue_series),
            "ebit": _trend(ebit_series),
            "pat": _trend(pat_series),
            "cfo": _trend(cfo_series),
            "pat_margin": _trend(margins),
            "roe": _trend(roe_series),
            "roce": _trend(roce_series),
        },
        "hurdles_passed": hurdles,
    }


def calculate_quality_score(ratios: Dict[str, Any], governance_clean: bool = True) -> Dict[str, Any]:
    roce = ratios.get("ROCE (%)")
    revenue_cagr = ratios.get("Revenue CAGR (%)")
    pat_cagr = ratios.get("PAT CAGR (%)")
    net_debt = ratios.get("Net Debt (Cr)")
    debt_to_equity = ratios.get("Debt to Equity")
    cfo_to_pat = ratios.get("CFO / PAT Quality Ratio")
    avg_cfo_to_pat = ratios.get("Average CFO / PAT (5Y)")
    components = {
        "capital_efficiency": 20 if roce is not None and roce >= 20 else 15 if roce is not None and roce >= 15 else 8 if roce is not None and roce >= 10 else 0,
        "growth": 20 if revenue_cagr is not None and pat_cagr is not None and revenue_cagr >= 15 and pat_cagr >= 15 else 15 if revenue_cagr is not None and pat_cagr is not None and revenue_cagr >= 10 and pat_cagr >= 10 else 8 if revenue_cagr is not None and revenue_cagr >= 5 else 0,
        "balance_sheet": 20 if net_debt is not None and net_debt <= 0 else 15 if debt_to_equity is not None and debt_to_equity <= 0.5 else 10 if debt_to_equity is not None and debt_to_equity <= 1 else 0,
        "cash_quality": 20 if cfo_to_pat is not None and avg_cfo_to_pat is not None and cfo_to_pat >= 1 and avg_cfo_to_pat >= 0.8 else 15 if cfo_to_pat is not None and avg_cfo_to_pat is not None and cfo_to_pat >= 0.7 and avg_cfo_to_pat >= 0.7 else 8 if avg_cfo_to_pat is not None and avg_cfo_to_pat >= 0.5 else 0,
        "governance": 20 if governance_clean else 0,
    }
    score = sum(components.values())
    rating = "INVESTIBLE" if score >= 80 else "WATCHLIST" if score >= 60 else "AVOID"
    return {"score_100": score, "rating": rating, "components": components}


def calculate_pe_valuation(current_price: float, shares_outstanding_cr: float, latest_pat_cr: float, pat_cagr_pct: float | None, target_pe: float = 25.0, margin_of_safety_pct: float = 20.0) -> Dict[str, Any]:
    if current_price <= 0 or shares_outstanding_cr <= 0 or latest_pat_cr <= 0:
        return {"available": False, "reason": "Valid price, shares outstanding and PAT are required."}
    if pat_cagr_pct is None:
        return {"available": False, "reason": "PAT CAGR is unavailable because the required financial history is incomplete."}
    eps = latest_pat_cr / shares_outstanding_cr
    fair_value = eps * target_pe
    buy_below = fair_value * (1 - margin_of_safety_pct / 100)
    market_cap_cr = current_price * shares_outstanding_cr
    implied_pe = current_price / eps if eps else 0.0
    return {
        "available": True,
        "current_price": round(current_price, 2),
        "market_cap_cr": round(market_cap_cr, 2),
        "eps": round(eps, 2),
        "current_pe": round(implied_pe, 2),
        "target_pe": round(target_pe, 2),
        "fair_value": round(fair_value, 2),
        "margin_of_safety_pct": round(margin_of_safety_pct, 2),
        "buy_below": round(buy_below, 2),
        "upside_to_fair_value_pct": round((fair_value / current_price - 1) * 100, 2),
        "pat_cagr_used_pct": round(pat_cagr_pct, 2),
    }


def determine_final_recommendation(quality: Dict[str, Any], ratios: Dict[str, Any], forensic_clean: bool, valuation: Dict[str, Any] | None = None, governance_grade: str | None = None) -> Dict[str, Any]:
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
