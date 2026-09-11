"""Minimal interactive menu for the NSE equity research engine."""

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


def _show_cached_watchlist(segment: str) -> bool:
    path = "./outputs/opportunity_scan.csv"
    if not os.path.exists(path):
        return False

    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    selected = [row for row in rows if str(row.get("market_cap_category", "")).upper() == segment]
    if not selected:
        return False

    print(f"\n[+] Loaded saved {segment} quality/watchlist scan.")
    print("[+] No universe or quality rescan was performed.")
    print("[+] Use Refresh = y when you want new market/fundamental data.")
    print("\nTOP 50 WATCHLIST — SAVED SCAN")
    print("-" * 100)
    for index, row in enumerate(selected[:50], 1):
        growth = row.get("earnings_growth_pct")
        pe = row.get("pe")
        print(
            f"{index:>2}. {row.get('symbol', ''):<15} "
            f"Score {float(row.get('opportunity_score') or 0):>5.1f}  "
            f"Growth {growth if growth else 'N/A':>7}  "
            f"P/E {pe if pe else 'N/A':>7}"
        )
    return True


def _opportunity_scan() -> None:
    from src.opportunity_scanner import run_opportunity_scan

    segment = _market_cap()
    if not segment:
        print("[!] Invalid market-cap selection.")
        return

    refresh = input("Refresh universe + quality scan? (y/N): ").strip().lower() == "y"

    if not refresh and _show_cached_watchlist(segment):
        _pause()
        return

    print(f"\n[*] Running full {segment} universe + quality scan...")
    print("[*] Growth-aware valuation is used; governance is still validated during deep research.")
    run_opportunity_scan(segment=segment, top=50, refresh=refresh)
    _pause()


def _deep_stock() -> None:
    from src.stock_analysis import analyze_stock

    symbol = _symbol()
    if not symbol:
        _pause()
        return

    print("\n[*] Running COMPLETE STOCK ENGINE")
    print("    Annual report + financial scan + valuation + governance + corporate filings + decision")
    result = analyze_stock(symbol)
    if result is not None:
        print("\n[+] Complete stock decision generated.")
    _pause()


def show_menu() -> None:
    while True:
        print("\n" + "=" * 68)
        print("        NSE EQUITY OPPORTUNITY AGENT")
        print("=" * 68)
        print("\n  1. Opportunity Scanner — Build/Load Top 50")
        print("  2. Deep Stock Engine — Enter Any Symbol")
        print("  0. Exit")
        print("=" * 68)

        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                _opportunity_scan()
            elif choice == "2":
                _deep_stock()
            elif choice == "0":
                print("\nGoodbye.")
                return
            else:
                print("[!] Invalid option. Choose 1, 2 or 0.")
        except KeyboardInterrupt:
            print("\n[!] Operation cancelled. Returning to the main menu.")
        except Exception as exc:
            print(f"\n[!] Operation failed: {exc}")
            _pause()


if __name__ == "__main__":
    show_menu()
