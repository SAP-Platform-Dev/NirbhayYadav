"""Stable contracts for the research application's replaceable modules.

These Protocols describe what the application expects from each major
capability. They deliberately contain no implementation imports, so a module
can be rewritten, optimized, or replaced without forcing changes throughout
the application.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class UniverseDiscovery(Protocol):
    def discover(self, limit: int | None = None, refresh: bool = False) -> list[Mapping[str, Any]]:
        ...


class AnnualReportDownloader(Protocol):
    def download_report(
        self,
        symbol: str,
        custom_filename: str | None = None,
        force_redownload: bool = False,
    ) -> str | None:
        ...


class DocumentExtractor(Protocol):
    def extract_critical_sections(self) -> Mapping[str, str]:
        ...


class CorporateRiskAssessor(Protocol):
    def assess(self, **inputs: Any) -> Any:
        ...


class FinancialAnalyzer(Protocol):
    def __call__(self, data: Any) -> Mapping[str, Any]:
        ...


class DeepScanner(Protocol):
    def __call__(self, **options: Any) -> Sequence[Mapping[str, Any]]:
        ...


class ReportWriter(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> str:
        ...


PUBLIC_MODULE_APIS = {
    "discovery": "src.universe_scan.run_universe_scan",
    "risk": "src.corporate_risk.CorporateRiskEngine.assess",
    "annual_report": "src.nse_downloader.NSEDownloader.download_report",
    "document_parser": "src.doc_parser.FinancialDocParser.extract_critical_sections",
    "financial_ratios": "src.financial_tools.calculate_fundamental_ratios",
    "quality_score": "src.financial_tools.calculate_quality_score",
    "valuation": "src.financial_tools.calculate_pe_valuation",
    "recommendation": "src.financial_tools.determine_final_recommendation",
    "deep_scan": "src.deep_scanner.run_deep_scan",
    "reporting": "src.reporting.save_investment_summary",
}
