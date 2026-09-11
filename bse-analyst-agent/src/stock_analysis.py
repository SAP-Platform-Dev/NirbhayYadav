"""Single-stock research use case.

The public function remains stable for the CLI/menu while the replaceable
workflow lives in ``StockResearchEngine``.
"""

from .agent import AnalysisOrchestrator
from .doc_parser import FinancialDocParser
from .nse_downloader import NSEDownloader
from .stock_research_engine import StockResearchEngine


def analyze_stock(symbol, price=None, shares_cr=None, target_pe=25.0, mos=20.0):
    """Run the complete single-stock research pipeline for one symbol."""
    symbol = symbol.upper().strip()
    print(
        f"\n==========================================\n"
        f" Starting V2 NSE Analysis Agent | {symbol}\n"
        f"==========================================\n"
    )
    print("[*] Running independent stock research engine...")

    engine = StockResearchEngine(
        downloader=NSEDownloader(),
        parser_factory=FinancialDocParser,
        orchestrator_factory=AnalysisOrchestrator,
    )
    result = engine.analyze(symbol, price, shares_cr, target_pe, mos)

    if result is None:
        print(f"[!] Could not download annual report for {symbol}. Exiting.")
        return None

    recommendation = result["recommendation"]
    quality = result["quality"]
    valuation = result["valuation"]
    memo = result["memo"]
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
    print(f"[+] Summary saved: {result['report_path']}")
    return result
