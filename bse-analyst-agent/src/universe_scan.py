"""NSE universe and small/micro-cap discovery use case.

The scanner is independent of the interactive menu and CLI entrypoint.
"""

import csv
import os

from .nse_universe import NSEUniverse
from .smallcap_scanner import SmallMicrocapConfig, classify_market_cap


def run_universe_scan(refresh=False, top=50, limit=None, output_dir="./outputs"):
    """Discover liquid NSE small/micro-cap candidates.

    This is a discovery screen only; it does not make an investment
    recommendation.
    """
    cfg = SmallMicrocapConfig()
    universe = NSEUniverse()
    print("\n[*] Discovering NSE equity universe...")
    rows = universe.discover(limit=limit, refresh=refresh)
    candidates = []

    for row in rows:
        market_cap = row.get("market_cap_cr")
        price = row.get("price")
        traded_value = row.get("avg_daily_value_cr")
        if market_cap is None or price is None or traded_value is None:
            continue

        category = classify_market_cap(float(market_cap), cfg)
        if category not in ("MICROCAP", "SMALLCAP"):
            continue
        if float(price) < cfg.min_price or float(traded_value) < cfg.min_daily_traded_value_cr:
            continue
        candidates.append({**row, "market_cap_category": category})

    candidates.sort(
        key=lambda x: (
            0 if x["market_cap_category"] == "MICROCAP" else 1,
            -float(x["market_cap_cr"]),
            -float(x["avg_daily_value_cr"]),
        )
    )

    selected = candidates[:top]
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "small_microcap_universe.csv")
    fields = [
        "symbol",
        "company_name",
        "market_cap_category",
        "market_cap_cr",
        "price",
        "avg_daily_value_cr",
        "source",
    ]

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: row.get(k) for k in fields} for row in selected)

    print(f"[+] NSE rows collected: {len(rows)}")
    print(f"[+] Candidates passing market/liquidity filters: {len(candidates)}")
    print(f"[+] Saved top {len(selected)} candidates to: {path}")
    print("\nTOP CANDIDATES — Stage 1 only (NOT investment recommendations)")
    print("-" * 95)
    for i, row in enumerate(selected, 1):
        print(
            f"{i:>2}. {row['symbol']:<15} {row['market_cap_category']:<9} "
            f"MCap ₹{float(row['market_cap_cr']):>9.0f} Cr  "
            f"Price ₹{float(row['price']):>8.2f}  "
            f"Traded ₹{float(row['avg_daily_value_cr']):>7.2f} Cr"
        )
    return selected
