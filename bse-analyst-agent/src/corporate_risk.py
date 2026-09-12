"""Deterministic corporate-risk engine for small/micro-cap research.
The engine is intentionally independent of the CLI/menu and exchange clients.
It accepts normalized inputs and returns a structured result, so the data
source and the UI can be replaced independently.
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
        if self.hard_fail or self.risk_score >= 50:
            return "D"
        if self.risk_score >= 30:
            return "C"
        if self.risk_score >= 15:
            return "B"
        return "A"
def _annual_report_risk(
    audits: Iterable[Mapping[str, Any]],
) -> tuple[int, list[str], list[str], bool, int]:
    """Aggregate historical annual-report forensic audit results."""
    reports = list(audits or [])[:10]
    if not reports:
        return 0, [], [], False, 0
    flags: list[str] = []
    positives: list[str] = []
    hard_fail = False
    weighted_score = 0.0
    total_weight = 0.0
    for index, audit in enumerate(reports):
        weight = max(0.5, 1.0 - (index * 0.08))
        total_weight += weight
        year = str(
            audit.get("fiscal_year")
            or audit.get("year")
            or f"Report {index + 1}"
        )
        opinion = str(
            audit.get("audit_opinion_type")
            or audit.get("audit_opinion")
        )
        contingent = str(
            audit.get("contingent_liability_risk") or ""
        ).strip().lower()
        related = str(
            audit.get("related_party_risk") or ""
        ).strip().lower()
        # Gemini may return a classification followed by an explanation,
        # e.g. "Low, because..." or "Medium - ...".
        # Extract only the classification for deterministic scoring.
        for level in ("very high", "critical", "high", "moderate", "medium", "low"):
            if contingent.startswith(level):
                contingent = level
                break
        for level in ("very high", "critical", "high", "moderate", "medium", "low"):
            if related.startswith(level):
                related = level
                break
        red_flags = audit.get("forensic_red_flags") or []
        if isinstance(red_flags, str):
            red_flags = [red_flags]
        red_text = " ".join(str(x) for x in red_flags).lower()
        score = 0
        # Audit opinion
        if "adverse" in opinion:
            score += 60
            flags.append(
                f"{year}: adverse audit opinion"
            )
            hard_fail = True
        elif "disclaimer" in opinion:
            score += 60
            flags.append(
                f"{year}: disclaimer of opinion"
            )
            hard_fail = True
        elif "qualified" in opinion:
            score += 45
            flags.append(
                f"{year}: qualified audit opinion"
            )
        elif (
            "unmodified" in opinion
            or "unqualified" in opinion
            or opinion == "clean"
        ):
            positives.append(
                f"{year}: clean audit opinion"
            )
        # Contingent liabilities
        if contingent in {
            "high",
            "very high",
            "critical",
        }:
            score += 25
            flags.append(
                f"{year}: high contingent-liability risk"
            )
        elif contingent in {
            "medium",
            "moderate",
        }:
            score += 12
            flags.append(
                f"{year}: moderate contingent-liability risk"
            )
        # Related parties
        if related in {
            "high",
            "very high",
            "critical",
        }:
            score += 20
            flags.append(
                f"{year}: high related-party risk"
            )
        elif related in {
            "medium",
            "moderate",
        }:
            score += 10
            flags.append(
                f"{year}: moderate related-party risk"
            )
        # Forensic red flags
        # Every explicitly identified forensic red flag contributes risk.
        # Severe keywords receive an additional penalty below.
        red_flag_count = len(red_flags)
        if red_flag_count:
            score += min(30, red_flag_count * 10)
            flags.append(
                f"{year}: {red_flag_count} forensic red flag(s)"
            )
        severe_terms = (
            "fraud",
            "forensic",
            "diversion",
            "misstatement",
            "money laundering",
            "insolvency",
        )
        # Detect severe terms only when they appear to describe an
        # actual adverse finding. Avoid false positives such as
        # "no evidence of fraud" or "fraud risk not identified".
        negative_contexts = (
            "no evidence of",
            "no indication of",
            "no instance of",
            "not identified",
            "not observed",
            "not found",
            "without evidence of",
            "did not identify",
            "did not observe",
            "absence of",
        )
        severe_hits = []
        for term in severe_terms:
            if term not in red_text:
                continue
            is_negative = any(
                f"{context} {term}" in red_text
                for context in negative_contexts
            )
            if not is_negative:
                severe_hits.append(term)
        if severe_hits:
            score += min(
                40,
                15 * len(severe_hits),
            )
            flags.append(
                f"{year}: forensic red flags - "
                + ", ".join(severe_hits)
            )
            hard_fail = True
        weighted_score += min(score, 100) * weight
    annual_score = (
        round(weighted_score / total_weight)
        if total_weight
        else 0
    )
    return (
        min(annual_score, 100),
        flags,
        positives,
        hard_fail,
        len(reports),
    )
class CorporateRiskEngine:
    """Standalone rule engine for mechanical governance/corporate screening."""
    HARD_PATTERNS = {
        "auditor resignation": 35,
        "resignation of auditor": 35,
        "qualified opinion": 40,
        "adverse opinion": 50,
        "disclaimer of opinion": 50,
        "fraud": 50,
        "forensic audit": 40,
        "default": 35,
        "insolvency": 50,
        "delisting": 50,
    }
    MEDIUM_PATTERNS = {
        "change in auditor": 20,
        "related party": 15,
        "preferential": 15,
        "preferential allotment": 20,
        "warrant": 15,
        "convertible": 15,
        "qip": 8,
        "fund raising": 5,
        "promoter sale": 15,
        "promoter pledge": 20,
        "pledge": 15,
        "resignation of director": 10,
        "regulatory order": 20,
        "stock exchange fine": 15,
    }
    @staticmethod
    def _num(value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    @staticmethod
    def _text(value: Any) -> str:
        return "" if value is None else str(value).strip().lower()
    def assess_shareholding(
        self,
        result: CorporateRiskResult,
        *,
        promoter_holding_pct: Any = None,
        promoter_pledge_pct: Any = None,
        promoter_change_pct: Any = None,
    ) -> None:
        pledge = self._num(promoter_pledge_pct)
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
        promoter = self._num(promoter_holding_pct)
        if promoter is None:
            result.data_gaps.append("Promoter holding data unavailable")
        elif promoter < 25:
            result.risk_score += 10
            result.risk_flags.append(f"Low promoter holding: {promoter:.2f}%")
        else:
            result.positive_signals.append("Promoter holding >= 25%")
        change = self._num(promoter_change_pct)
        if change is None:
            result.data_gaps.append("Promoter holding change unavailable")
        elif change < -5:
            result.risk_score += 20
            result.risk_flags.append(f"Sharp promoter holding decline: {change:.2f} pp")
        elif change > 2:
            result.positive_signals.append(f"Promoter holding increased {change:.2f} pp")
    def assess_auditor(
        self, result: CorporateRiskResult, auditor_status: str | None = None
    ) -> None:
        auditor = self._text(auditor_status)
        if not auditor:
            result.data_gaps.append("Auditor change/status unavailable")
        elif any(term in auditor for term in ("resign", "qualified", "adverse", "disclaimer")):
            result.risk_score += 30
            result.risk_flags.append(f"Auditor concern: {auditor_status}")
            result.hard_fail = True
        else:
            result.positive_signals.append("No mechanical auditor red flag")
    def assess_related_party(
        self, result: CorporateRiskResult, related_party_risk: str | None = None
    ) -> None:
        risk = self._text(related_party_risk)
        if not risk:
            result.data_gaps.append("Related-party risk unavailable")
        elif risk in {"high", "very high", "critical"}:
            result.risk_score += 30
            result.risk_flags.append(f"High related-party risk: {related_party_risk}")
            result.hard_fail = True
        elif risk in {"medium", "moderate"}:
            result.risk_score += 15
            result.risk_flags.append(f"Moderate related-party risk: {related_party_risk}")
        else:
            result.positive_signals.append("Related-party risk not elevated")
    def assess_announcements(
        self,
        result: CorporateRiskResult,
        announcements: Iterable[Mapping[str, Any]] | None = None,
    ) -> None:
        for announcement in announcements or []:
            subject = self._text(announcement.get("subject"))
            details = self._text(announcement.get("details"))
            text = f"{subject} {details}"
            matched: set[str] = set()
            for term, points in self.HARD_PATTERNS.items():
                if term in text:
                    result.risk_flags.append(f"Corporate filing: {term}")
                    result.risk_score += points
                    matched.add(term)
                    if points >= 40:
                        result.hard_fail = True
            for term, points in self.MEDIUM_PATTERNS.items():
                if term in text and not any(term in existing.lower() for existing in result.risk_flags if existing.startswith("Corporate filing:")):
                    result.risk_flags.append(f"Corporate filing: {term}")
                    result.risk_score += points
        result.risk_score = min(result.risk_score, 100)
    def assess(self, **inputs: Any) -> CorporateRiskResult:
        """Run all deterministic corporate-risk checks on normalized inputs."""
        result = CorporateRiskResult()
        self.assess_shareholding(
            result,
            promoter_holding_pct=inputs.get("promoter_holding_pct"),
            promoter_pledge_pct=inputs.get("promoter_pledge_pct"),
            promoter_change_pct=inputs.get("promoter_change_pct"),
        )
        self.assess_auditor(result, inputs.get("auditor_status"))
        self.assess_related_party(result, inputs.get("related_party_risk"))
        self.assess_announcements(result, inputs.get("announcements"))
        annual_score, annual_flags, annual_positives, annual_hard_fail, report_count = (
            _annual_report_risk(
                inputs.get("annual_report_audits") or []
            )
        )
        result.annual_report_score = annual_score
        result.reports_scanned = report_count
        result.risk_flags.extend(annual_flags)
        result.positive_signals.extend(annual_positives)
        result.hard_fail = (
            result.hard_fail or annual_hard_fail
        )
        exchange_score = min(
            result.risk_score,
            100,
        )
        if report_count:
            result.risk_score = round(
                (exchange_score * 0.55)
                + (annual_score * 0.45)
            )
        else:
            result.risk_score = exchange_score
        result.risk_score = min(
            result.risk_score,
            100,
        )
        return result
def assess_corporate_risk(**inputs: Any) -> CorporateRiskResult:
    """Backward-compatible functional API backed by :class:`CorporateRiskEngine`."""
    return CorporateRiskEngine().assess(**inputs)
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
