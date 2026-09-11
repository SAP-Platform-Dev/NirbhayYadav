"""Simple interactive menu for the NSE equity research agent."""

import csv
import os
from typing import Optional


def _pause() -> None:
    input("\nPress Enter to return...")


def _symbol() -> Optional[str]:
    symbol = input("NSE symbol: ").strip().upper()
    if not symbol:
        print("[!] Symbol is required.")
        return None
    return symbol


def _market_cap() -> Optional[str]:
    print("\nMarket-cap universe")
    print("  1. Microcap")
    print("  2. Smallcap")
    print("  3. Midcap")
    print("  4. Largecap")
    choice = input("Choose: ").strip()
    return {"1": "MICROCAP", "2": "SMALLCAP", "3": "MIDCAP", "4": "LARGECAP"}.get(choice)


def _opportunity_scan() -> None:
    from src.opportunity_scanner import run_opportunity_scan

    segment = _market_cap()
    if not segment:
        return

    refresh = input("Refresh NSE universe? (y/N): ").strip().lower() == "y"

    print(f"\n[*] Scanning {segment} and building the top 50 quality watchlist...")
    print("[*] Growth matters, valuation is growth-aware, and governance still requires deep research.")
    print("[*] Stage 1 creates the watchlist only — it does not issue BUY/AVOID decisions.")
    run_opportunity_scan(segment=segment, top=50, refresh=refresh)
    _pause()


def _analyse_stock() -> None:
    from src.stock_analysis import analyze_stock

    symbol = _symbol()
    if not symbol:
        _pause()
        return
    analyze_stock(symbol)
    _pause()


def _corporate_risk() -> None:
    from src.corporate_risk import assess_corporate_risk, extract_announcements_from_rows
    from src.nse_corporate_filings import NSECorporateFilings

    symbol = _symbol()
    if not symbol:
        _pause()
        return

    print(f"\n[*] Fetching live NSE corporate risk data for {symbol}...")
    data = NSECorporateFilings().risk_inputs(symbol)
    shareholding = data.get("shareholding", {})
    announcements = extract_announcements_from_rows(data.get("announcements", []))
    announcements.extend(data.get("pit_risk_rows", []))

    result = assess_corporate_risk(
        promoter_holding_pct=data.get("promoter_holding_pct", shareholding.get("promoter_holding_pct")),
        promoter_pledge_pct=data.get("promoter_pledge_pct", shareholding.get("promoter_pledge_pct")),
        promoter_change_pct=data.get("promoter_change_pct", shareholding.get("promoter_change_pct")),
        announcements=announcements,
    )

    print("\n" + "=" * 60)
    print(f"CORPORATE RISK: {symbol}")
    print("=" * 60)
    print(f"Risk score   : {result.risk_score}")
    print(f"Governance   : {result.governance_grade}")
    print(f"Hard fail    : {'YES' if result.hard_fail else 'NO'}")
    if result.risk_flags:
        print("\nRisk flags:")
        for item in result.risk_flags:
            print(f"  - {item}")
    if result.positive_signals:
        print("\nPositive signals:")
        for item in result.positive_signals:
            print(f"  + {item}")
    if result.data_gaps:
        print("\nData gaps:")
        for item in result.data_gaps:
            print(f"  ? {item}")
    _pause()


def _deep_scan() -> None:
    from src.deep_scanner import run_deep_scan

    input_csv = "./outputs/opportunity_scan.csv"
    if not os.path.exists(input_csv):
        print("[!] No 50-stock watchlist found. Run 'Scan & Build Watchlist' first.")
        _pause()
        return

    print("\n--- DEEP RESEARCH FROM TOP 50 WATCHLIST ---")
    print("Enter symbols separated by commas, or press Enter for the first 5.")
    symbols = input("Symbols: ").strip().upper()

    if symbols:
        requested = [item.strip() for item in symbols.split(",") if item.strip()]
        with open(input_csv, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        selected = [row for row in rows if str(row.get("symbol", "")).upper() in requested]
        missing = [symbol for symbol in requested if symbol not in {str(row.get("symbol", "")).upper() for row in rows}]
        if missing:
            print(f"[!] Not found in top 50 watchlist: {', '.join(missing)}")
        if not selected:
            _pause()
            return

        temp_csv = "./outputs/deep_research_selection.csv"
        with open(temp_csv, "w", newline="", encoding="utf-8") as fh:
            fields = list(rows[0].keys()) if rows else []
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(selected)
        input_csv = temp_csv
        deep_limit = len(selected)
    else:
        deep_limit = 5

    live = input("Use live NSE corporate filings? (Y/n): ").strip().lower() != "n"
    run_deep_scan(input_csv=input_csv, top=deep_limit, deep_limit=deep_limit, live_filings=live)
    _pause()


def _scanner_menu() -> None:
    while True:
        print("\n--- STOCK OPPORTUNITY AGENT ---")
        print("  1. Scan & Build Top 50 Watchlist")
        print("  2. Deep Research from Top 50")
        print("  0. Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            _opportunity_scan()
        elif choice == "2":
            _deep_scan()
        elif choice == "0":
            return
        else:
            print("[!] Invalid option.")


def _view_latest_results() -> None:
    paths = [
        os.path.join("outputs", "small_microcap_deep_analysis.csv"),
        os.path.join("outputs", "opportunity_scan.csv"),
    ]
    path = next((candidate for candidate in paths if os.path.exists(candidate)), None)
    if not path:
        print("[!] No result file found in ./outputs yet.")
        _pause()
        return

    print(f"\n[*] Showing: {path}")
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("[!] Result file is empty.")
        _pause()
        return

    preferred = [
        "symbol", "company_name", "market_cap_category", "market_cap_rank", "opportunity_score",
        "growth_score", "pe", "verdict", "quality_score", "corporate_risk_score", "governance_grade",
    ]
    fields = [field for field in preferred if field in rows[0]] or list(rows[0].keys())[:8]
    print("\n" + " | ".join(f"{field[:18]:<18}" for field in fields))
    print("-" * min(160, len(fields) * 21))
    for row in rows[:50]:
        print(" | ".join(f"{str(row.get(field, ''))[:18]:<18}" for field in fields))
    _pause()


def show_menu() -> None:
    while True:
        print("\n" + "=" * 68)
        print("        NSE EQUITY OPPORTUNITY AGENT")
        print("=" * 68)
        print("\n  1. Stock Opportunity Scanner")
        print("  2. Full Stock Analysis")
        print("  3. Corporate Risk Check")
        print("  4. View Top 50 Watchlist")
        print("  0. Exit")
        print("=" * 68)

        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                _scanner_menu()
            elif choice == "2":
                _analyse_stock()
            elif choice == "3":
                _corporate_risk()
            elif choice == "4":
                _view_latest_results()
            elif choice == "0":
                print("\nGoodbye.")
                return
            else:
                print("[!] Invalid option. Choose 1-4 or 0.")
        except KeyboardInterrupt:
            print("\n[!] Operation cancelled. Returning to the main menu.")
        except Exception as exc:
            print(f"\n[!] Operation failed: {exc}")
            _pause()


if __name__ == "__main__":
    show_menu()
