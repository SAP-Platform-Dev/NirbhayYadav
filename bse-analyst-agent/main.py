"""CLI entrypoint for the NSE equity research agent.

The entrypoint intentionally contains no research logic. Research capabilities
live in independent modules under ``src/`` so they can be changed and tested
without changing the menu or CLI.
"""

import argparse
import os
import sys
import warnings

from dotenv import load_dotenv

warnings.filterwarnings("ignore", message=r".*automatic function calling \(AFC\).*")
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

from src.deep_scanner import run_deep_scan
from src.reporting import save_investment_summary
from src.stock_analysis import analyze_stock
from src.universe_scan import run_universe_scan


# Backward-compatible public names. Existing scripts importing functions from
# main.py continue to work while the real implementation stays modular.
def main(symbol, price=None, shares_cr=None, target_pe=25.0, mos=20.0):
    return analyze_stock(symbol, price, shares_cr, target_pe, mos)


def save_summary_to_notepad(
    symbol,
    forensics,
    ratios,
    quality,
    valuation,
    recommendation,
    memo,
    output_dir="./outputs",
):
    return save_investment_summary(
        symbol,
        forensics,
        ratios,
        quality,
        valuation,
        recommendation,
        memo,
        output_dir,
    )


if __name__ == "__main__":
    # No arguments = interactive menu. Existing CLI commands remain available
    # for automation/backward compatibility (e.g. --scan, --deep-scan, TCS).
    if len(sys.argv) == 1:
        from src.menu import show_menu
        show_menu()
        raise SystemExit(0)

    cli = argparse.ArgumentParser(
        description="Indian equity research agent and small/micro-cap scanner"
    )
    cli.add_argument("symbol", nargs="?", default="TCS", help="NSE symbol for deep analysis")
    cli.add_argument("--scan", action="store_true", help="Stage 1: discover NSE small/micro-cap candidates")
    cli.add_argument("--deep-scan", action="store_true", help="Stage 2: deeply analyze the Stage-1 CSV")
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

    if args.deep_scan:
        run_deep_scan(
            input_csv=args.input_csv,
            top=args.top,
            deep_limit=args.deep_limit,
            live_filings=not args.no_live_filings,
        )
    elif args.scan:
        run_universe_scan(refresh=args.refresh, top=args.top, limit=args.limit)
    else:
        main(args.symbol, args.price, args.shares_cr, args.target_pe, args.mos)
