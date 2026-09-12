"""Independent deterministic financial analysis engine.

The engine groups the financial-analysis decisions behind a replaceable class
while keeping the existing functional APIs in ``financial_tools`` intact for
backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .financial_tools import (
    calculate_fundamental_ratios,
    calculate_pe_valuation,
    calculate_quality_score,
    determine_final_recommendation,
)


@dataclass(frozen=True)
class FinancialAnalysisResult:
    """Stable result object returned by the combined financial pipeline."""

    ratios: Mapping[str, Any]
    quality: Mapping[str, Any]
    valuation: Mapping[str, Any]
    recommendation: Mapping[str, Any]


class FinancialAnalysisEngine:
    """Run financial calculations without knowing about CLI, menu, or NSE IO."""

    def calculate_ratios(self, history: Any) -> dict[str, Any]:
        return calculate_fundamental_ratios(history)

    def calculate_quality(
        self,
        ratios: Mapping[str, Any],
        governance_clean: bool = True,
    ) -> dict[str, Any]:
        return calculate_quality_score(dict(ratios), governance_clean=governance_clean)

    def calculate_valuation(
        self,
        current_price: float,
        shares_outstanding_cr: float,
        latest_pat_cr: float,
        pat_cagr_pct: float | None,
        target_pe: float = 25.0,
        margin_of_safety_pct: float = 20.0,
    ) -> dict[str, Any]:
        return calculate_pe_valuation(
            current_price,
            shares_outstanding_cr,
            latest_pat_cr,
            pat_cagr_pct,
            target_pe,
            margin_of_safety_pct,
        )

    def determine_recommendation(
        self,
        quality: Mapping[str, Any],
        ratios: Mapping[str, Any],
        governance_clean: bool,
        valuation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return determine_final_recommendation(
            dict(quality),
            dict(ratios),
            governance_clean,
            dict(valuation) if valuation is not None else None,
        )

    def analyze(
        self,
        history: Any,
        governance_clean: bool = True,
        current_price: float | None = None,
        shares_outstanding_cr: float | None = None,
        target_pe: float = 25.0,
        margin_of_safety_pct: float = 20.0,
    ) -> FinancialAnalysisResult:
        """Calculate ratios, quality, valuation and the final deterministic decision."""
        ratios = self.calculate_ratios(history)
        quality = self.calculate_quality(ratios, governance_clean)

        valuation: dict[str, Any] = {
            "available": False,
            "reason": "Supply current price and shares outstanding to calculate transparent P/E fair value.",
        }
        if current_price is not None and shares_outstanding_cr is not None:
            valuation = self.calculate_valuation(
                current_price,
                shares_outstanding_cr,
                history.years[-1].pat,
                ratios.get("PAT CAGR (%)"),
                target_pe,
                margin_of_safety_pct,
            )

        recommendation = self.determine_recommendation(
            quality,
            ratios,
            governance_clean,
            valuation,
        )
        return FinancialAnalysisResult(ratios, quality, valuation, recommendation)
