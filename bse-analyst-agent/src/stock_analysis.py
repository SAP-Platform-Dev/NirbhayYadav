"""Single-stock research use case.

This module owns the end-to-end analysis of one NSE symbol. It does not know
about the interactive menu or the command-line entrypoint.
"""

import os
import sys

from .agent import AnalysisOrchestrator
from .doc_parser import FinancialDocParser
from .financial_tools import (
    calculate_fundamental_ratios,
    calculate_pe_valuation,
    calculate_quality_score,
    determine_final_recommendation,
)
from .nse_downloader import NSEDownloader
from .reporting import save_investment_summary


def analyze_stock(symbol, price=None, shares_cr=None, target_pe=25.0, mos=20.0):
    """Run the complete single-stock research pipeline for one symbol."""
    symbol = symbol.upper().strip()
    print(
        f"\n==========================================\n"
        f" Starting V2 NSE Analysis Agent | {symbol}\n"
        f"==========================================\n"
    )

    pdf_path = NSEDownloader().download_report(symbol)
    if not pdf_path:
        print(f"[!] Could not download annual report for {symbol}. Exiting.")
        return None

    parser = FinancialDocParser(pdf_path)
    sections = parser.extract_critical_sections()
    orchestrator = AnalysisOrchestrator()

    print("\n[*] Running forensic governance audit...")
    forensics = orchestrator.audit_forensics(
        sections["auditor_report"], sections["notes"]
    )

    print("[*] Extracting five-year financial history...")
    history = orchestrator.extract_metrics_payload(sections["financial_statements"])
    ratios = calculate_fundamental_ratios(history)

    governance_clean = (
        forensics.audit_opinion_type.lower().startswith("unmodified")
        and forensics.contingent_liability_risk.lower().startswith("low")
        and forensics.related_party_risk.lower().startswith("low")
        and not forensics.forensic_red_flags
    )

    quality = calculate_quality_score(ratios, governance_clean=governance_clean)
    valuation = {
        "available": False,
        "reason": "Supply --price and --shares-cr to calculate transparent P/E fair value.",
    }
    if price is not None and shares_cr is not None:
        valuation = calculate_pe_valuation(
            price,
            shares_cr,
            history.years[-1].pat,
            ratios["PAT CAGR (%)"],
            target_pe,
            mos,
        )

    print("[*] Generating investment thesis...")
    memo = orchestrator.run_investment_committee(
        forensics, ratios, quality, valuation
    )
    recommendation = determine_final_recommendation(
        quality, ratios, governance_clean, valuation
    )
    memo.verdict = recommendation["verdict"]

    print("\n" + "=" * 60)
    print(f"FINAL VERDICT: {recommendation['verdict']}")
    print(f"QUALITY SCORE: {quality['score_100']}/100")
    print(f"AI THESIS CONVICTION: {memo.conviction_score}/10")
    if valuation.get("available"):
        print(
            f"FAIR VALUE: ₹{valuation['fair_value']} | "
            f"BUY BELOW: ₹{valuation['buy_below']}"
        )
    print("=" * 60)

    saved_file = save_investment_summary(
        symbol,
        forensics,
        ratios,
        quality,
        valuation,
        recommendation,
        memo,
    )
    print(f"[+] Summary saved: {saved_file}")

    # Preserve the existing Windows convenience behavior without making it
    # required for the research pipeline.
    if os.name == "nt":
        try:
            os.system(f'notepad "{saved_file}"')
        except Exception:
            pass

    return {
        "symbol": symbol,
        "forensics": forensics,
        "ratios": ratios,
        "quality": quality,
        "valuation": valuation,
        "recommendation": recommendation,
        "memo": memo,
        "report_path": saved_file,
    }
