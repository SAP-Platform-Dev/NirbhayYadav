"""Deterministic corporate-risk engine for small/micro-cap research.

Corporate risk combines current exchange signals with historical annual-report
forensic evidence. Missing information is recorded as UNKNOWN rather than
silently treated as clean.
"""

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass
class CorporateRiskResult:
    hard_fail: bool = False
    risk_flags: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    data_gaps: list[str] = field(default_factory=list)
    risk_score: int = 0
    annual_report_score: int = 0
    reports_scanned: int = 0

    @property
    def governance_grade(self) -> str:
        if self.hard_fail or self.risk_score >= 60:
            return "D"
        if self.risk_score >= 45:
            return "C"
        if self.risk_score >= 25:
            return "B"
        return "A"


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip().lower()


def _keywords(text: str, terms: Iterable[str]) -> bool:
    text = text.lower()
    return any(term.lower() in text for term in terms)


def _announcement_risk(subject: str, details: str) -> tuple[int, list[str], bool]:
    text = f"{subject} {details}".lower()
    score = 0
    flags: list[str] = []
    hard_fail = False

    hard_patterns = {
        "adverse opinion": 60,
        "disclaimer of opinion": 60,
        "fraud": 50,
        "forensic audit": 45,
        "insolvency": 60,
        "delisting": 60,
        "auditor resignation": 40,
        "resignation of auditor": 40,
        "qualified opinion": 45,
        "default": 40,
    }
    medium_patterns = {
        "change in auditor": 15,
        "related party": 10,
        "preferential allotment": 15,
        "preferential": 10,
        "warrant": 10,
        "convertible": 10,
        "qip": 6,
        "fund raising": 4,
        "promoter sale": 12,
        "promoter pledge": 15,
        "pledge": 10,
        "resignation of director": 8,
        "regulatory order": 15,
        "sebi": 8,
        "stock exchange fine": 12,
    }

    for term, points in hard_patterns.items():
        if term in text:
            flags.append(f"Corporate filing: {term}")
            score += points
            hard_fail = True
    for term, points in medium_patterns.items():
        if term in text and not any(term in flag.lower() for flag in flags):
            flags.append(f"Corporate filing: {term}")
            score += points

    return min(score, 100), flags, hard_fail


def _annual_report_risk(audits: Iterable[Mapping[str, Any]]) -> tuple[int, list[str], list[str], bool, int]:
    """Score up to ten years of structured annual-report forensic audits.

    Recent reports carry more weight, but a severe historical event remains a
    hard fail because governance failures cannot be made safe merely by age.
    """
    rows = list(audits or [])[:10]
    if not rows:
        return 0, [], ["Annual-report forensic history unavailable"], False, 0

    score_total = 0.0
    weight_total = 0.0
    flags: list[str] = []
    positives: list[str] = []
    hard_fail = False

    for index, audit in enumerate(rows):
        weight = max(0.55, 1.0 - (index * 0.05))
        weight_total += weight
        year = str(audit.get("fiscal_year") or audit.get("year") or f"report-{index + 1}")
        report_score = 0.0

        opinion = _text(audit.get("audit_opinion_type"))
        if "adverse" in opinion or "disclaimer" in opinion:
            report_score += 60
            hard_fail = True
            flags.append(f"{year}: {audit.get('audit_opinion_type')}")
        elif "qualified" in opinion:
            report_score += 45
            hard_fail = True
            flags.append(f"{year}: Qualified audit opinion")
        elif "unmodified" in opinion or "clean" in opinion:
            positives.append(f"{year}: Clean/unmodified audit opinion")
        elif opinion:
            report_score += 15
            flags.append(f"{year}: Unclear audit opinion: {audit.get('audit_opinion_type')}")

        contingent = _text(audit.get("contingent_liability_risk"))
        if contingent in {"high", "very high", "critical"}:
            report_score += 20
            flags.append(f"{year}: High contingent-liability risk")
        elif contingent in {"medium", "moderate"}:
            report_score += 10
            flags.append(f"{year}: Moderate contingent-liability risk")

        related = _text(audit.get("related_party_risk"))
        if related in {"high", "very high", "critical"}:
            report_score += 20
            flags.append(f"{year}: High related-party risk")
        elif related in {"medium", "moderate"}:
            report_score += 10
            flags.append(f"{year}: Moderate related-party risk")

        red_flags = audit.get("forensic_red_flags") or []
        if isinstance(red_flags, str):
            red_flags = [red_flags]
        red_flags = [str(x).strip() for x in red_flags if str(x).strip()]
        if red_flags:
            report_score += min(25, 8 * len(red_flags))
            flags.append(f"{year}: {len(red_flags)} forensic red flag(s)")
            if any(_keywords(x, ["fraud", "misstatement", "diversion", "fabricat", "forgery"]) for x in red_flags):
                hard_fail = True

        score_total += min(report_score, 100) * weight

    score = round(score_total / weight_total) if weight_total else 0
    return min(score, 100), flags, positives, hard_fail, len(rows)


def assess_corporate_risk(
    *,
    promoter_holding_pct: Any = None,
    promoter_pledge_pct: Any = None,
    promoter_change_pct: Any = None,
    auditor_status: str | None = None,
    related_party_risk: str | None = None,
    announcements: Iterable[Mapping[str, Any]] | None = None,
    annual_report_audits: Iterable[Mapping[str, Any]] | None = None,
) -> CorporateRiskResult:
    """Evaluate current exchange signals plus historical annual-report evidence."""
    result = CorporateRiskResult()

    pledge = _num(promoter_pledge_pct)
    if pledge is None:
        result.data_gaps.append("Promoter pledge data unavailable")
    elif pledge > 20:
        result.risk_score += 35
        result.risk_flags.append(f"High promoter pledge: {pledge:.2f}%")
        result.hard_fail = True
    elif pledge > 5:
        result.risk_score += 20
        result.risk_flags.append(f"Promoter pledge above threshold: {pledge:.2f}%")
    else:
        result.positive_signals.append("Promoter pledge <= 5%")

    promoter = _num(promoter_holding_pct)
    if promoter is None:
        result.data_gaps.append("Promoter holding data unavailable")
    elif promoter < 25:
        result.risk_score += 10
        result.risk_flags.append(f"Low promoter holding: {promoter:.2f}%")
    else:
        result.positive_signals.append("Promoter holding >= 25%")

    change = _num(promoter_change_pct)
    if change is None:
        result.data_gaps.append("Promoter holding change unavailable")
    elif change < -5:
        result.risk_score += 20
        result.risk_flags.append(f"Sharp promoter holding decline: {change:.2f} pp")
    elif change > 2:
        result.positive_signals.append(f"Promoter holding increased {change:.2f} pp")

    auditor = _text(auditor_status)
    if not auditor:
        result.data_gaps.append("Auditor change/status unavailable")
    elif _keywords(auditor, ["resign", "qualified", "adverse", "disclaimer"]):
        result.risk_score += 30
        result.risk_flags.append(f"Auditor concern: {auditor_status}")
        result.hard_fail = True
    else:
        result.positive_signals.append("No mechanical auditor red flag")

    rtp = _text(related_party_risk)
    if not rtp:
        result.data_gaps.append("Related-party risk unavailable")
    elif rtp in {"high", "very high", "critical"}:
        result.risk_score += 30
        result.risk_flags.append(f"High related-party risk: {related_party_risk}")
        result.hard_fail = True
    elif rtp in {"medium", "moderate"}:
        result.risk_score += 15
        result.risk_flags.append(f"Moderate related-party risk: {related_party_risk}")
    else:
        result.positive_signals.append("Related-party risk not elevated")

    for announcement in announcements or []:
        points, flags, hard = _announcement_risk(
            _text(announcement.get("subject")),
            _text(announcement.get("details")),
        )
        result.risk_score += points
        result.risk_flags.extend(flags)
        result.hard_fail = result.hard_fail or hard

    annual_score, annual_flags, annual_positives, annual_hard_fail, report_count = _annual_report_risk(annual_report_audits)
    result.annual_report_score = annual_score
    result.reports_scanned = report_count
    result.risk_flags.extend(annual_flags)
    result.positive_signals.extend(annual_positives)
    result.hard_fail = result.hard_fail or annual_hard_fail

    # Current exchange evidence is slightly more important than older annual
    # reports, while historical reports prevent recent clean periods from
    # hiding a long-running governance problem.
    exchange_score = min(result.risk_score, 100)
    if report_count:
        result.risk_score = round((exchange_score * 0.55) + (annual_score * 0.45))
    else:
        result.risk_score = exchange_score

    result.risk_score = min(result.risk_score, 100)
    return result


def extract_announcements_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Normalize exchange announcement rows for the risk engine."""
    normalized = []
    for row in rows:
        normalized.append(
            {
                "subject": str(row.get("subject") or row.get("SUBJECT") or ""),
                "details": str(row.get("details") or row.get("DETAILS") or ""),
                "date": str(row.get("date") or row.get("BROADCAST_DATE") or ""),
            }
        )
    return normalized
