"""Stable contracts for the research application's replaceable modules.

These Protocols describe what the application expects from each major
capability. They deliberately contain no implementation imports, so a module
can be rewritten, optimized, or replaced without forcing changes throughout
the application.

The concrete modules remain responsible for their own implementation:
    universe_scan.py      -> discovery
    nse_downloader.py     -> annual-report download
    doc_parser.py         -> document extraction
    corporate_risk.py     -> governance/risk assessment
    financial_tools.py    -> deterministic financial analysis
    deep_scanner.py       -> multi-stage deep scan
    reporting.py          -> report persistence
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class UniverseDiscovery(Protocol):
    """Contract for discovering exchange/universe candidates."""

    def discover(
        self, limit: int | None = None, refresh: bool = False
    ) -> list[Mapping[str, Any]]:
        ...


class AnnualReportDownloader(Protocol):
    """Contract for retrieving the latest annual report for a symbol."""

    def download_report(
        self,
        symbol: str,
        custom_filename: str | None = None,
        force_redownload: bool = False,
    ) -> str | None:
        ...


class DocumentExtractor(Protocol):
    """Contract for extracting research-relevant document sections."""

    def extract_critical_sections(self) -> Mapping[str, str]:
        ...


class CorporateRiskAssessor(Protocol):
    """Contract for deterministic corporate/governance screening."""

    def __call__(self, **inputs: Any) -> Any:
        ...


class FinancialAnalyzer(Protocol):
    """Contract for deterministic financial calculations."""

    def __call__(self, data: Any) -> Mapping[str, Any]:
        ...


class DeepScanner(Protocol):
    """Contract for the expensive end-to-end candidate analysis."""

    def __call__(self, **options: Any) -> Sequence[Mapping[str, Any]]:
        ...


class ReportWriter(Protocol):
    """Contract for persisting an investment/research report."""

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        ...


# Stable public names used in architecture documentation. These are not
# runtime imports: the concrete implementations can change independently.
PUBLIC_MODULE_APIS = {
    "discovery": "src.universe_scan.run_universe_scan",
    "risk": "src.corporate_risk.assess_corporate_risk",
    "annual_report": "src.nse_downloader.NSEDownloader.download_report",
    "document_parser": "src.doc_parser.FinancialDocParser.extract_critical_sections",
    "financial_ratios": "src.financial_tools.calculate_fundamental_ratios",
    "quality_score": "src.financial_tools.calculate_quality_score",
    "valuation": "src.financial_tools.calculate_pe_valuation",
    "recommendation": "src.financial_tools.determine_final_recommendation",
    "deep_scan": "src.deep_scanner.run_deep_scan",
    "reporting": "src.reporting.save_investment_summary",
}
