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

    @property
    def governance_grade(self) -> str:
        if self.hard_fail or self.risk_score >= 50:
            return "D"
        if self.risk_score >= 30:
            return "C"
        if self.risk_score >= 15:
            return "B"
        return "A"


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
        "sebi": 10,
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
        result.risk_score = min(result.risk_score, 100)
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
