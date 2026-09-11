"""Interactive menu for the NSE equity research agent.

The menu is intentionally a thin UI layer. Existing research modules remain
responsible for the actual discovery, risk, analysis and scoring work.
"""

import csv
import os
from typing import Optional


def _pause() -> None:
    input("\nPress Enter to return to the main menu...")


def _ask_int(prompt: str, default: int) -> int:
    value = input(f"{prompt} [{default}]: ").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        print("[!] Please enter a whole number. Using the default.")
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


def _scan_nse() -> None:
    from main import run_universe_scan

    top = _ask_int("How many candidates should be saved", 50)
    refresh = input("Refresh NSE data? (y/N): ").strip().lower() == "y"
    run_universe_scan(refresh=refresh, top=top)
    _pause()


def _corporate_risk() -> None:
    from src.corporate_risk import assess_corporate_risk
    from src.nse_corporate_filings import NSECorporateFilings

    symbol = input("NSE symbol: ").strip().upper()
    if not symbol:
        print("[!] Symbol is required.")
        _pause()
        return

    client = NSECorporateFilings()
    print(f"\n[*] Fetching live NSE corporate risk data for {symbol}...")
    data = client.risk_inputs(symbol)
    result = assess_corporate_risk(
        symbol,
        shareholding=data.get("shareholding", {}),
        announcements=data.get("announcements", []),
        pit=data.get("pit_risk_rows", data.get("pit", [])),
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


def _analyse_stock() -> None:
    from main import main as analyse

    symbol = input("NSE symbol: ").strip().upper()
    if not symbol:
        print("[!] Symbol is required.")
        _pause()
        return

    print("\nOptional valuation inputs. Leave blank if unavailable.")
    price = _ask_float("Current share price")
    shares_cr = _ask_float("Shares outstanding (crore)")
    target_pe = _ask_float("Target P/E", 25.0) or 25.0
    mos = _ask_float("Margin of safety %", 20.0) or 20.0
    analyse(symbol, price, shares_cr, target_pe, mos)
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
    fields = [field for field in preferred if field in rows[0]]
    if not fields:
        fields = list(rows[0].keys())[:8]

    print("\n" + " | ".join(f"{field[:18]:<18}" for field in fields))
    print("-" * min(140, len(fields) * 21))
    for row in rows[:20]:
        print(" | ".join(f"{str(row.get(field, ''))[:18]:<18}" for field in fields))
    _pause()


def show_menu() -> None:
    while True:
        print("\n" + "=" * 64)
        print("        NSE EQUITY RESEARCH & 10X OPPORTUNITY AGENT")
        print("=" * 64)
        print("\nDISCOVERY")
        print("  1. Scan NSE Universe")
        print("  2. Find Small / Micro Cap Candidates")
        print("\nRESEARCH")
        print("  3. Analyse a Stock")
        print("  4. Corporate Risk Check")
        print("\nSCANNER")
        print("  5. Run Full Small / Micro Cap Deep Scan")
        print("\nRESULTS")
        print("  6. View Latest Results")
        print("\nSYSTEM")
        print("  0. Exit")
        print("=" * 64)

        choice = input("Choose an option: ").strip()
        try:
            if choice in {"1", "2"}:
                _scan_nse()
            elif choice == "3":
                _analyse_stock()
            elif choice == "4":
                _corporate_risk()
            elif choice == "5":
                _deep_scan()
            elif choice == "6":
                _view_latest_results()
            elif choice == "0":
                print("\nGoodbye.")
                return
            else:
                print("[!] Invalid option. Choose a number from the menu.")
        except KeyboardInterrupt:
            print("\n[!] Operation cancelled. Returning to the menu.")
        except Exception as exc:
            print(f"\n[!] Operation failed: {exc}")
            _pause()


if __name__ == "__main__":
    show_menu()
