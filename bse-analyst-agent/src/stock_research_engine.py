"""Replaceable single-stock research orchestration engine."""

from __future__ import annotations

import os
from typing import Any, Callable

from .financial_engine import FinancialAnalysisEngine
from .reporting import save_investment_summary


class StockResearchEngine:
    """Orchestrate one-stock research through injectable collaborators.

    The engine owns workflow only. Downloader, parser, AI orchestrator,
    financial engine and report writer can all be replaced independently.
    """

    def __init__(
        self,
        downloader: Any,
        parser_factory: Callable[[str], Any],
        orchestrator_factory: Callable[[], Any],
        financial_engine: FinancialAnalysisEngine | None = None,
        report_writer: Callable[..., str] = save_investment_summary,
    ) -> None:
        self.downloader = downloader
        self.parser_factory = parser_factory
        self.orchestrator_factory = orchestrator_factory
        self.financial_engine = financial_engine or FinancialAnalysisEngine()
        self.report_writer = report_writer

    def analyze(
        self,
        symbol: str,
        price: float | None = None,
        shares_cr: float | None = None,
        target_pe: float = 25.0,
        mos: float = 20.0,
    ) -> dict[str, Any] | None:
        symbol = symbol.upper().strip()
        pdf_path = self.downloader.download_report(symbol)
        if not pdf_path:
            return None

        parser = self.parser_factory(pdf_path)
        sections = parser.extract_critical_sections()
        orchestrator = self.orchestrator_factory()

        forensics = orchestrator.audit_forensics(
            sections["auditor_report"], sections["notes"]
        )
        history = orchestrator.extract_metrics_payload(
            sections["financial_statements"]
        )

        governance_clean = (
            forensics.audit_opinion_type.lower().startswith("unmodified")
            and forensics.contingent_liability_risk.lower().startswith("low")
            and forensics.related_party_risk.lower().startswith("low")
            and not forensics.forensic_red_flags
        )

        analysis = self.financial_engine.analyze(
            history,
            governance_clean=governance_clean,
            current_price=price,
            shares_outstanding_cr=shares_cr,
            target_pe=target_pe,
            margin_of_safety_pct=mos,
        )

        memo = orchestrator.run_investment_committee(
            forensics,
            analysis.ratios,
            analysis.quality,
            analysis.valuation,
        )
        memo.verdict = analysis.recommendation["verdict"]

        saved_file = self.report_writer(
            symbol,
            forensics,
            analysis.ratios,
            analysis.quality,
            analysis.valuation,
            analysis.recommendation,
            memo,
        )

        if os.name == "nt":
            try:
                os.system(f'notepad "{saved_file}"')
            except Exception:
                pass

        return {
            "symbol": symbol,
            "forensics": forensics,
            "ratios": analysis.ratios,
            "quality": analysis.quality,
            "valuation": analysis.valuation,
            "recommendation": analysis.recommendation,
            "memo": memo,
            "report_path": saved_file,
        }
