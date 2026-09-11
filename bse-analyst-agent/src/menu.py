"""Interactive menu for the NSE equity research agent.

The menu is deliberately a thin UI layer. It imports independent use-case
modules but those modules never import this menu or the CLI entrypoint.
"""

import csv
import os
from typing import Optional


def _pause() -> None:
    input("\nPress Enter to return...")


def _ask_int(prompt: str, default: int) -> int:
    value = input(f"{prompt} [{default}]: ").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        print("[!] Invalid whole number. Using the default.")
        return default


def _ask_float(prompt: str, default: Optional[float] = None) -> Optional[float]:
    suffix = f" [{default}]" if default is not None else " [optional]"
    value = input(f"{prompt}{suffix}: ").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        print("[!] Invalid number. Leaving it blank.")
        return default


def _symbol() -> Optional[str]:
    symbol = input("NSE symbol: ").strip().upper()
    if not symbol:
        print("[!] Symbol is required.")
        return None
    return symbol


def _scan_nse(refresh: bool = False) -> None:
    from src.universe_scan import run_universe_scan

    top = _ask_int("How many candidates should be saved", 50)
    run_universe_scan(refresh=refresh, top=top)
    _pause()


def _analyse_stock() -> None:
    from src.stock_analysis import analyze_stock

    symbol = _symbol()
    if not symbol:
        _pause()
        return

    print("\nOptional valuation inputs. Leave blank if unavailable.")
    price = _ask_float("Current share price")
    shares_cr = _ask_float("Shares outstanding (crore)")
    target_pe = _ask_float("Target P/E", 25.0) or 25.0
    mos = _ask_float("Margin of safety %", 20.0) or 20.0
    analyze_stock(symbol, price, shares_cr, target_pe, mos)
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

    top = _ask_int("Stage-1 candidates to shortlist", 10)
    deep_limit = _ask_int("Maximum candidates for deep analysis", 5)
    live = input("Use live NSE corporate filings? (Y/n): ").strip().lower() != "n"
    run_deep_scan(top=top, deep_limit=deep_limit, live_filings=live)
    _pause()


def _view_latest_results() -> None:
    path = os.path.join("outputs", "deep_scan_results.csv")
    if not os.path.exists(path):
        path = os.path.join("outputs", "small_microcap_universe.csv")
    if not os.path.exists(path):
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
        "symbol", "company_name", "market_cap_category", "verdict",
        "quality_score", "corporate_risk_score", "governance_grade",
    ]
    fields = [field for field in preferred if field in rows[0]] or list(rows[0].keys())[:8]

    print("\n" + " | ".join(f"{field[:18]:<18}" for field in fields))
    print("-" * min(140, len(fields) * 21))
    for row in rows[:20]:
        print(" | ".join(f"{str(row.get(field, ''))[:18]:<18}" for field in fields))
    _pause()


def _discovery_menu() -> None:
    while True:
        print("\n--- DISCOVERY ---")
        print("  1. Scan NSE Universe")
        print("  2. Find Small / Micro Cap Candidates")
        print("  0. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            _scan_nse(refresh=False)
        elif choice == "2":
            _scan_nse(refresh=False)
        elif choice == "0":
            return
        else:
            print("[!] Invalid option.")


def _research_menu() -> None:
    while True:
        print("\n--- STOCK RESEARCH ---")
        print("  1. Full Stock Analysis")
        print("  2. Corporate Risk Check")
        print("  0. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            _analyse_stock()
        elif choice == "2":
            _corporate_risk()
        elif choice == "0":
            return
        else:
            print("[!] Invalid option.")


def _scanner_menu() -> None:
    while True:
        print("\n--- OPPORTUNITY SCANNER ---")
        print("  1. Quick Small / Micro Cap Scan")
        print("  2. Deep Scan Candidates")
        print("  0. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            _scan_nse(refresh=False)
        elif choice == "2":
            _deep_scan()
        elif choice == "0":
            return
        else:
            print("[!] Invalid option.")


def _reports_menu() -> None:
    while True:
        print("\n--- REPORTS ---")
        print("  1. View Latest Results")
        print("  2. Open Outputs Folder")
        print("  0. Back")
        choice = input("Choose: ").strip()
        if choice == "1":
            _view_latest_results()
        elif choice == "2":
            print(f"Outputs directory: {os.path.abspath('outputs')}")
            _pause()
        elif choice == "0":
            return
        else:
            print("[!] Invalid option.")


def show_menu() -> None:
    while True:
        print("\n" + "=" * 68)
        print("        NSE EQUITY RESEARCH & 10X OPPORTUNITY AGENT")
        print("=" * 68)
        print("\n  1. Discovery")
        print("  2. Stock Research")
        print("  3. Opportunity Scanner")
        print("  4. Reports")
        print("  0. Exit")
        print("=" * 68)

        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                _discovery_menu()
            elif choice == "2":
                _research_menu()
            elif choice == "3":
                _scanner_menu()
            elif choice == "4":
                _reports_menu()
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
