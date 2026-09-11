"""Complete single-stock research engine entry point."""

from datetime import datetime

from .agent import AnalysisOrchestrator
from .corporate_risk import assess_corporate_risk, extract_announcements_from_rows
from .doc_parser import FinancialDocParser
from .nse_corporate_filings import NSECorporateFilings
from .nse_downloader import NSEDownloader
from .stock_research_engine import StockResearchEngine


def _attach_corporate_risk(result, symbol: str):
    """Run live/cached corporate governance checks and make them part of the decision."""
    filings = NSECorporateFilings()
    data = filings.cached_risk_inputs(symbol)
    shareholding = data.get("shareholding", {})
    announcements = extract_announcements_from_rows(data.get("announcements", []))
    announcements.extend(data.get("pit_risk_rows", []))

    risk = assess_corporate_risk(
        promoter_holding_pct=data.get("promoter_holding_pct", shareholding.get("promoter_holding_pct")),
        promoter_pledge_pct=data.get("promoter_pledge_pct", shareholding.get("promoter_pledge_pct")),
        promoter_change_pct=data.get("promoter_change_pct", shareholding.get("promoter_change_pct")),
        announcements=announcements,
    )

    result["corporate_risk"] = risk
    result["corporate_filings"] = data

    # Governance red flags are a hard blocker. A high financial score must not
    # be allowed to hide serious management/corporate-risk issues.
    if risk.hard_fail:
        result["recommendation"]["verdict"] = "AVOID"
        result["recommendation"]["reason"] = (
            "Corporate governance/corporate-risk hard fail overrides financial quality: "
            + "; ".join(risk.risk_flags)
        )

    return result


def _append_governance_report(result, symbol: str) -> None:
    """Append live governance findings to the generated investment report."""
    report_path = result.get("report_path")
    risk = result.get("corporate_risk")
    if not report_path or risk is None:
        return

    with open(report_path, "a", encoding="utf-8") as fh:
        fh.write("\n" + "=" * 70 + "\n")
        fh.write("LIVE CORPORATE GOVERNANCE / RISK CHECK\n")
        fh.write("=" * 70 + "\n")
        fh.write(f"Checked: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n")
        fh.write(f"Risk score     : {risk.risk_score}/100\n")
        fh.write(f"Governance     : {risk.governance_grade}\n")
        fh.write(f"Hard fail      : {'YES' if risk.hard_fail else 'NO'}\n\n")
        fh.write("Risk flags:\n")
        for item in risk.risk_flags or ["None detected."]:
            fh.write(f"  ! {item}\n")
        fh.write("\nPositive signals:\n")
        for item in risk.positive_signals or ["None recorded."]:
            fh.write(f"  + {item}\n")
        fh.write("\nData gaps:\n")
        for item in risk.data_gaps or ["None recorded."]:
            fh.write(f"  ? {item}\n")
        fh.write("\nFINAL DECISION\n")
        fh.write(f"  {result['recommendation']['verdict']}: {result['recommendation']['reason']}\n")


def analyze_stock(symbol, price=None, shares_cr=None, target_pe=25.0, mos=20.0):
    """Run the complete stock engine: financials, valuation, governance and decision."""
    symbol = symbol.upper().strip()
    print(
        f"\n==========================================\n"
        f" COMPLETE NSE STOCK ENGINE | {symbol}\n"
        f"==========================================\n"
    )
    print("[*] 1/4 Annual report + forensic accounting")
    print("[*] 2/4 Five-year financial scan + quality ratios")
    print("[*] 3/4 Valuation + live/cached corporate governance")
    print("[*] 4/4 Deterministic investment decision + reasons")

    engine = StockResearchEngine(
        downloader=NSEDownloader(),
        parser_factory=FinancialDocParser,
        orchestrator_factory=AnalysisOrchestrator,
    )
    result = engine.analyze(symbol, price, shares_cr, target_pe, mos)

    if result is None:
        print(f"[!] Could not download annual report for {symbol}. Exiting.")
        return None

    result = _attach_corporate_risk(result, symbol)
    _append_governance_report(result, symbol)

    recommendation = result["recommendation"]
    quality = result["quality"]
    valuation = result["valuation"]
    memo = result["memo"]
    risk = result["corporate_risk"]

    print("\n" + "=" * 68)
    print(f"FINAL VERDICT: {recommendation['verdict']}")
    print(f"QUALITY SCORE: {quality['score_100']}/100")
    print(f"GOVERNANCE: {risk.governance_grade} | RISK SCORE: {risk.risk_score}/100")
    print(f"AI THESIS CONVICTION: {memo.conviction_score}/10")
    if valuation.get("available"):
        print(f"FAIR VALUE: ₹{valuation['fair_value']} | BUY BELOW: ₹{valuation['buy_below']}")
    print(f"\nWHY: {recommendation['reason']}")

    if memo.executive_summary:
        print("\nINVESTMENT THESIS")
        print(memo.executive_summary.strip())
    if memo.financial_strengths:
        print("\nWHY BUY / STRENGTHS")
        for item in memo.financial_strengths:
            print(f"  + {item}")
    if memo.critical_risks:
        print("\nWHY AVOID / RISKS")
        for item in memo.critical_risks:
            print(f"  - {item}")
    if risk.risk_flags:
        print("\nCORPORATE / MANAGEMENT RED FLAGS")
        for item in risk.risk_flags:
            print(f"  ! {item}")

    print("=" * 68)
    print(f"[+] Complete report saved: {result['report_path']}")
    return result
