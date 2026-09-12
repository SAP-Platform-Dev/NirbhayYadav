import argparse
import csv
import os
import sys
import warnings
from datetime import datetime
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message=r".*automatic function calling \(AFC\).*")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from src.nse_downloader import NSEDownloader
from src.doc_parser import FinancialDocParser
from src.financial_tools import calculate_fundamental_ratios, calculate_quality_score, calculate_pe_valuation, determine_final_recommendation
from src.agent import AnalysisOrchestrator
from src.nse_universe import NSEUniverse
from src.smallcap_scanner import SmallMicrocapConfig, classify_market_cap
from src.deep_scanner import run_deep_scan
from src.corporate_risk import assess_corporate_risk, extract_announcements_from_rows
from src.nse_corporate_filings import NSECorporateFilings


def run_corporate_risk_only(symbol: str, report_years: int = 10, live_filings: bool = True):
    """Corporate-risk-only test path.

    This deliberately does NOT run financial ratios, valuation, quality score,
    investment memo, or final investment recommendation. It downloads up to
    ten annual reports and uses only their audit/notes evidence for governance
    risk, alongside current NSE corporate/PIT/shareholding signals.
    """
    symbol = symbol.upper().strip()
    print(f"{'=' * 72} CORPORATE RISK ONLY | {symbol}{'=' * 72}")
    print(f"[*] Annual-report history requested: {report_years} years")

    filing_data = {"announcements": [], "pit_risk_rows": [], "shareholding": {}}
    if live_filings:
        print("[*] Collecting current NSE corporate/PIT/shareholding signals...")
        filing_data = NSECorporateFilings().cached_risk_inputs(symbol, days=180, refresh=True)

    shareholding = filing_data.get("shareholding", {})
    promoter_holding = filing_data.get("promoter_holding_pct")
    promoter_pledge = filing_data.get("promoter_pledge_pct")
    promoter_change = filing_data.get("promoter_change_pct")

    audits = []
    downloader = NSEDownloader()
    reports = downloader.download_reports(symbol, years=report_years)
    print(f"[+] Annual reports downloaded/available: {len(reports)}")

    ai = AnalysisOrchestrator()
    for item in reports:
        fy = item.get("fiscal_year", "Unknown")
        try:
            parser = FinancialDocParser(item["path"])
            sections = parser.extract_critical_sections()
            print(f"[*] Forensic governance audit: {fy}")
            forensic = ai.audit_forensics(sections.get("auditor_report", ""), sections.get("notes", ""))
            audits.append({
                "fiscal_year": fy,
                "audit_opinion_type": forensic.audit_opinion_type,
                "contingent_liability_risk": forensic.contingent_liability_risk,
                "related_party_risk": forensic.related_party_risk,
                "forensic_red_flags": forensic.forensic_red_flags,
            })
        except Exception as exc:
            print(f"[!] Could not audit {fy}: {type(exc).__name__}: {exc}")

    if not reports:
        report_gap = "No annual reports available from NSE"
    elif len(audits) < min(report_years, len(reports)):
        report_gap = f"Only {len(audits)}/{len(reports)} available reports were successfully audited"
    else:
        report_gap = None

    announcements = extract_announcements_from_rows(
        [*filing_data.get("announcements", []), *filing_data.get("pit_risk_rows", [])]
    )
    corporate = assess_corporate_risk(
        promoter_holding_pct=promoter_holding,
        promoter_pledge_pct=promoter_pledge,
        promoter_change_pct=promoter_change,
        announcements=announcements,
        annual_report_audits=audits,
    )
    if report_gap:
        corporate.data_gaps.append(report_gap)

    print("" + "=" * 72)
    print("CORPORATE GOVERNANCE RISK")
    print("=" * 72)

    print("OVERALL VERDICT")
    print(f"  Governance Grade   : {corporate.governance_grade}")
    print(f"  Numerical Risk     : {corporate.risk_score}/100")
    print(f"  Annual Report Risk : {corporate.annual_report_score}/100")
    print(
        f"  Critical Override  : "
        f"{'YES' if corporate.hard_fail else 'NO'}"
    )

    print("WHY?")

    if corporate.hard_fail:
        critical_flags = []

        for flag in corporate.risk_flags:
            text_lower = str(flag).lower()

            if any(
                term in text_lower
                for term in (
                    "fraud",
                    "forensic",
                    "adverse audit",
                    "disclaimer",
                    "insolvency",
                    "diversion",
                    "misstatement",
                    "money laundering",
                )
            ):
                critical_flags.append(flag)

        if critical_flags:
            for flag in critical_flags:
                print(f"  [CRITICAL] {flag}")
        else:
            print("  [CRITICAL] Critical governance trigger detected.")
    else:
        print("  No critical governance override detected.")

    print("KEY CONCERNS")

    concerns_found = False

    # Show the actual forensic findings from annual reports.
    for audit in audits:
        fiscal_year = str(audit.get("fiscal_year", "Unknown"))

        red_flags = audit.get("forensic_red_flags") or []

        if isinstance(red_flags, str):
            red_flags = [red_flags]

        if not red_flags:
            continue

        concerns_found = True

        print(f"  [!] {fiscal_year}")

        for red_flag in red_flags:
            print(f"      • {str(red_flag).strip()}")

    # Show other governance concerns.
    for flag in corporate.risk_flags:
        text_lower = str(flag).lower()

        # Annual-report forensic counts are already represented above.
        if "forensic red flag" in text_lower:
            continue

        print(f"  [!] {flag}")
        concerns_found = True

    if not concerns_found:
        print("  None identified.")

    print("POSITIVE SIGNALS")

    if corporate.positive_signals:
        for signal in corporate.positive_signals:
            print(f"  [+] {signal}")
    else:
        print("  None identified.")

    print("DATA LIMITATIONS")

    if corporate.data_gaps:
        for gap in corporate.data_gaps:
            print(f"  [?] {gap}")
    else:
        print("  None identified.")

    print("10-YEAR HISTORY")
    print(
        "  FY       Audit      Related Party    "
        "Contingent Risk    Flags"
    )
    print("  " + "-" * 65)

    for audit in audits:
        fiscal_year = str(audit.get("fiscal_year", "Unknown"))

        short_year = fiscal_year
        if fiscal_year.startswith("FY"):
            short_year = fiscal_year[2:]

        audit_opinion = str(
            audit.get("audit_opinion_type") or "Unknown"
        ).strip()

        audit_lower = audit_opinion.lower()

        if (
            "unmodified" in audit_lower
            or "unqualified" in audit_lower
            or audit_lower == "clean"
        ):
            audit_display = "Clean"
        elif "qualified" in audit_lower:
            audit_display = "Qualified"
        elif "adverse" in audit_lower:
            audit_display = "Adverse"
        elif "disclaimer" in audit_lower:
            audit_display = "Disclaimer"
        else:
            audit_display = audit_opinion[:12]

        def _risk_label(value):
            value_text = str(value or "Unknown").strip().lower()

            for level in (
                "very high",
                "critical",
                "high",
                "moderate",
                "medium",
                "low",
            ):
                if value_text.startswith(level):
                    return level.title()

            return "Unknown"

        related_display = _risk_label(
            audit.get("related_party_risk")
        )

        contingent_display = _risk_label(
            audit.get("contingent_liability_risk")
        )

        red_flags = audit.get("forensic_red_flags") or []

        if isinstance(red_flags, str):
            red_flags = [red_flags]

        red_flag_count = len(red_flags)

        critical_year = any(
            any(
                term in str(red_flag).lower()
                for term in (
                    "fraud",
                    "forensic",
                    "diversion",
                    "misstatement",
                    "money laundering",
                    "insolvency",
                )
            )
            for red_flag in red_flags
        )

        flag_display = str(red_flag_count)

        if critical_year:
            flag_display += " [CRITICAL]"

        print(
            f"  {short_year:<8}"
            f"{audit_display:<11}"
            f"{related_display:<17}"
            f"{contingent_display:<19}"
            f"{flag_display}"
        )

    print("INVESTOR INTERPRETATION")

    if corporate.hard_fail:
        print("  Critical forensic/governance trigger detected.")
        print(
            "  Manual review of the underlying annual-report "
            "evidence is required."
        )
        print(
            "  Numerical risk score alone does not determine the "
            "Governance Grade."
        )
        print(
            "  The Governance Grade is currently driven by the "
            "Critical Override."
        )
    elif corporate.risk_score >= 50:
        print(
            "  Governance risk is elevated based on the numerical "
            "risk score."
        )
    elif corporate.risk_score >= 30:
        print(
            "  Some governance concerns are present and should be "
            "monitored."
        )
    else:
        print(
            "  No major governance risk detected from the available "
            "signals."
        )

    print("=" * 72)



def save_summary_to_notepad(symbol, forensics, ratios, quality, valuation, recommendation, memo, output_dir="./outputs"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(output_dir, f"{symbol.upper()}_Investment_Summary_{timestamp}.txt")
    divider, sub = "=" * 70, "-" * 70
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{divider}FIVE-YEAR EQUITY RESEARCH INVESTMENT MEMO")
        f.write(f"Company: {symbol.upper()} | Date: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}{divider}")
        f.write(f"[FINAL VERDICT]: {recommendation['verdict']}")
        f.write(f"[DETERMINISTIC QUALITY SCORE]: {quality['score_100']} / 100")
        f.write(f"[AI THESIS CONVICTION]: {memo.conviction_score} / 10")
        f.write(f"[GOVERNANCE]: {'PASSED' if memo.governance_clearance else 'FAILED / REVIEW'}")
        f.write(f"[DECISION LOGIC]: {recommendation['reason']}")
        f.write(f"{sub}EXECUTIVE THESIS{sub}{memo.executive_summary.strip()}")
        f.write(f"{sub}FIVE-YEAR FUNDAMENTALS{sub}")
        for metric, value in ratios.items():
            if metric != "hurdles_passed": f.write(f"  • {metric:<30}: {value}")
        f.write("Hurdles:")
        for check, passed in ratios.get("hurdles_passed", {}).items(): f.write(f"  • {check.replace('_', ' ').title():<30}: {'PASS [✓]' if passed else 'FAIL [X]'}")
        f.write(f"{sub}QUALITY SCORE{sub}")
        for component, points in quality["components"].items(): f.write(f"  • {component.replace('_', ' ').title():<30}: {points:>2} / 20")
        f.write(f"  TOTAL: {quality['score_100']} / 100")
        f.write(f"{sub}VALUATION{sub}")
        if valuation.get("available"):
            for key, value in valuation.items():
                if key != "available": f.write(f"  • {key.replace('_', ' ').title():<30}: {value}")
        else: f.write(f"  • {valuation.get('reason', 'Not calculated.')}")
        f.write(f"{sub}FORENSIC & GOVERNANCE{sub}")
        f.write(f"  • Audit Opinion             : {forensics.audit_opinion_type}")
        f.write(f"  • Contingent Liability Risk : {forensics.contingent_liability_risk}")
        f.write(f"  • Related Party Risk        : {forensics.related_party_risk}")
        f.write("  Key Audit Matters:")
        for item in forensics.key_audit_matters or ["None specified."]: f.write(f"    - {item}")
        f.write("  Forensic Red Flags:")
        for item in forensics.forensic_red_flags or ["None detected."]: f.write(f"    ! {item}")
        f.write(f"{sub}FINANCIAL STRENGTHS{sub}")
        for item in memo.financial_strengths: f.write(f"  [+] {item}")
        f.write(f"{sub}CRITICAL RISKS{sub}")
        for item in memo.critical_risks: f.write(f"  [-] {item}")
        f.write(f"{divider}End of Report")
    return filepath


def run_universe_scan(refresh=False, top=50, limit=None, output_dir="./outputs"):
    """Stage 1: exchange-level discovery only; not an investment recommendation."""
    cfg = SmallMicrocapConfig(); universe = NSEUniverse()
    print("[*] Discovering NSE equity universe...")
    rows = universe.discover(limit=limit, refresh=refresh); candidates = []
    for row in rows:
        market_cap, price, traded_value = row.get("market_cap_cr"), row.get("price"), row.get("avg_daily_value_cr")
        if market_cap is None or price is None or traded_value is None: continue
        category = classify_market_cap(float(market_cap), cfg)
        if category not in ("MICROCAP", "SMALLCAP"): continue
        if float(price) < cfg.min_price or float(traded_value) < cfg.min_daily_traded_value_cr: continue
        candidates.append({**row, "market_cap_category": category})
    candidates.sort(key=lambda x: (0 if x["market_cap_category"] == "MICROCAP" else 1, -float(x["market_cap_cr"]), -float(x["avg_daily_value_cr"])))
    selected = candidates[:top]; os.makedirs(output_dir, exist_ok=True); path = os.path.join(output_dir, "small_microcap_universe.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fields = ["symbol", "company_name", "market_cap_category", "market_cap_cr", "price", "avg_daily_value_cr", "source"]
        writer = csv.DictWriter(fh, fieldnames=fields); writer.writeheader(); writer.writerows({k: row.get(k) for k in fields} for row in selected)
    print(f"[+] NSE rows collected: {len(rows)}"); print(f"[+] Candidates passing market/liquidity filters: {len(candidates)}"); print(f"[+] Saved top {len(selected)} candidates to: {path}")
    print("TOP CANDIDATES — Stage 1 only (NOT investment recommendations)"); print("-" * 95)
    for i, row in enumerate(selected, 1): print(f"{i:>2}. {row['symbol']:<15} {row['market_cap_category']:<9} MCap ₹{float(row['market_cap_cr']):>9.0f} Cr  Price ₹{float(row['price']):>8.2f}  Traded ₹{float(row['avg_daily_value_cr']):>7.2f} Cr")
    return selected


def main(symbol, price=None, shares_cr=None, target_pe=25.0, mos=20.0):
    symbol = symbol.upper().strip(); print(f"========================================== Starting V2 NSE Analysis Agent | {symbol}==========================================")
    pdf_path = NSEDownloader().download_report(symbol)
    if not pdf_path: print(f"[!] Could not download annual report for {symbol}. Exiting."); sys.exit(1)
    parser = FinancialDocParser(pdf_path); sections = parser.extract_critical_sections(); orchestrator = AnalysisOrchestrator()
    print("[*] Running forensic governance audit..."); forensics = orchestrator.audit_forensics(sections["auditor_report"], sections["notes"])
    print("[*] Extracting five-year financial history..."); history = orchestrator.extract_metrics_payload(sections["financial_statements"]); ratios = calculate_fundamental_ratios(history)
    governance_clean = (forensics.audit_opinion_type.lower().startswith("unmodified") and forensics.contingent_liability_risk.lower().startswith("low") and forensics.related_party_risk.lower().startswith("low") and not forensics.forensic_red_flags)
    quality = calculate_quality_score(ratios, governance_clean=governance_clean); valuation = {"available": False, "reason": "Supply --price and --shares-cr to calculate transparent P/E fair value."}
    if price is not None and shares_cr is not None: valuation = calculate_pe_valuation(price, shares_cr, history.years[-1].pat, ratios["PAT CAGR (%)"], target_pe, mos)
    print("[*] Generating investment thesis..."); memo = orchestrator.run_investment_committee(forensics, ratios, quality, valuation); recommendation = determine_final_recommendation(quality, ratios, governance_clean, valuation); memo.verdict = recommendation["verdict"]
    print("" + "=" * 60); print(f"FINAL VERDICT: {recommendation['verdict']}"); print(f"QUALITY SCORE: {quality['score_100']}/100"); print(f"AI THESIS CONVICTION: {memo.conviction_score}/10")
    if valuation.get("available"): print(f"FAIR VALUE: ₹{valuation['fair_value']} | BUY BELOW: ₹{valuation['buy_below']}")
    print("=" * 60); saved_file = save_summary_to_notepad(symbol, forensics, ratios, quality, valuation, recommendation, memo); print(f"[+] Summary saved: {saved_file}")
    try: os.system(f'notepad "{saved_file}"')
    except Exception: pass


if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="Indian equity research agent and small/micro-cap scanner"
    )

    cli.add_argument(
        "symbol",
        nargs="?",
        default=None,
        help="NSE symbol for deep analysis"
    )
    cli.add_argument("--scan", action="store_true", help="Stage 1: discover NSE small/micro-cap candidates")
    cli.add_argument("--deep-scan", action="store_true", help="Stage 2: deeply analyze the Stage-1 CSV")
    cli.add_argument("--corporate-risk", action="store_true", help="Corporate-risk-only test using up to ten annual reports")
    cli.add_argument("--corporate-years", type=int, default=10, help="Annual reports used by --corporate-risk (default: 10)")
    cli.add_argument("--refresh", action="store_true", help="Refresh the NSE universe cache")
    cli.add_argument("--top", type=int, default=50, help="Stage-1 candidates or Stage-2 shortlist size")
    cli.add_argument("--deep-limit", type=int, default=20, help="Maximum Stage-1 candidates sent to deep analysis")
    cli.add_argument("--no-live-filings", action="store_true", help="Disable live NSE corporate/PIT filing checks")
    cli.add_argument("--limit", type=int, help="Limit universe symbols for testing")
    cli.add_argument("--input-csv", default="./outputs/small_microcap_universe.csv", help="Stage-1 CSV for Stage 2")
    cli.add_argument("--price", type=float, help="Current share price for single-stock valuation")
    cli.add_argument("--shares-cr", type=float, help="Shares outstanding in crore for single-stock valuation")
    cli.add_argument("--target-pe", type=float, default=25.0, help="Target P/E multiple")
    cli.add_argument("--mos", type=float, default=20.0, help="Margin of safety percentage")

    args = cli.parse_args()

    # Interactive menu when no command-line arguments are supplied.
    if len(sys.argv) == 1:
        print("" + "=" * 60)
        print("        NSE EQUITY RESEARCH AGENT")
        print("=" * 60)
        print()
        print("1. Analyze a stock")
        print("2. Corporate governance risk")
        print("3. Small / micro-cap universe scan")
        print("4. Deep scan universe")
        print("5. Exit")
        print()

        choice = input("Select an option [1-5]: ").strip()

        if choice == "1":
            symbol = input("Enter NSE symbol: ").strip()

            if not symbol:
                print("[!] Symbol is required.")
                sys.exit(1)

            main(
                symbol,
                args.price,
                args.shares_cr,
                args.target_pe,
                args.mos,
            )

        elif choice == "2":
            symbol = input("Enter NSE symbol: ").strip()

            if not symbol:
                print("[!] Symbol is required.")
                sys.exit(1)

            years_input = input("Number of annual reports [10]: ").strip()

            try:
                years = int(years_input) if years_input else 10
            except ValueError:
                print("[!] Invalid number of years.")
                sys.exit(1)

            years = max(1, min(years, 10))

            run_corporate_risk_only(
                symbol,
                report_years=years,
                live_filings=True,
            )

        elif choice == "3":
            run_universe_scan(
                refresh=False,
                top=50,
                limit=None,
            )

        elif choice == "4":
            run_deep_scan(
                input_csv="./outputs/small_microcap_universe.csv",
                top=50,
                deep_limit=20,
                live_filings=True,
            )

        elif choice == "5":
            print("Exiting.")
            sys.exit(0)

        else:
            print("[!] Invalid option.")
            sys.exit(1)

        sys.exit(0)

    # Command-line modes.
    if args.corporate_risk:
        if not args.symbol:
            cli.error("--corporate-risk requires a symbol")

        run_corporate_risk_only(
            args.symbol,
            report_years=max(1, min(args.corporate_years, 10)),
            live_filings=not args.no_live_filings,
        )

    elif args.deep_scan:
        run_deep_scan(
            input_csv=args.input_csv,
            top=args.top,
            deep_limit=args.deep_limit,
            live_filings=not args.no_live_filings,
        )

    elif args.scan:
        run_universe_scan(
            refresh=args.refresh,
            top=args.top,
            limit=args.limit,
        )

    elif args.symbol:
        main(
            args.symbol,
            args.price,
            args.shares_cr,
            args.target_pe,
            args.mos,
        )

    else:
        cli.print_help()

