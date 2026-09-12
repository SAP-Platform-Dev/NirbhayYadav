"""Market-cap opportunity scanner.

Stage 1 scans the selected market-cap universe, enriches the full candidate
universe with lightweight fundamentals, applies a growth-aware quality score,
and returns the top 50 as a research watchlist. It does not issue BUY/AVOID
decisions.

Large/mid/small classification follows the SEBI/AMFI rank convention using the
current discovered universe: large = ranks 1-100, mid = 101-250, small = 251+
by full market-cap value. Microcap is a project-defined subset of small caps
with market cap <= Rs 5,000 Cr.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from typing import Any

import requests

from .nse_universe import NSEUniverse


SEGMENTS = ("MICROCAP", "SMALLCAP", "MIDCAP", "LARGECAP")
MICROCAP_MAX_CR = 5000.0


def _raw(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("raw")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _pct(value: Any) -> float | None:
    number = _raw(value)
    if number is None:
        return None
    return number * 100 if abs(number) <= 2 else number


def _growth_points(value: float | None, maximum: float = 20.0) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(value / maximum, 1.0))


def classify_rank(rank: int, market_cap_cr: float | None) -> str | None:
    if rank <= 100:
        return "LARGECAP"
    if rank <= 250:
        return "MIDCAP"
    if market_cap_cr is not None and market_cap_cr <= MICROCAP_MAX_CR:
        return "MICROCAP"
    return "SMALLCAP"


def _cache_path(output_dir: str) -> str:
    return os.path.join(output_dir, "opportunity_quality_cache.json")


class OpportunityScanner:
    def __init__(self, universe: NSEUniverse | None = None, request_delay: float = 0.20):
        self.universe = universe or NSEUniverse()
        self.request_delay = request_delay
        self.session = requests.Session()
        self.session.headers.update(NSEUniverse.HEADERS)
        self.yahoo_crumb: str | None = None

    def _init_yahoo_auth(self) -> None:
        if self.yahoo_crumb:
            return
        self.session.get("https://fc.yahoo.com", headers={"Referer": "https://finance.yahoo.com/"}, timeout=15)
        response = self.session.get(
            "https://query1.finance.yahoo.com/v1/test/getcrumb",
            headers={"Referer": "https://finance.yahoo.com/"},
            timeout=15,
        )
        response.raise_for_status()
        self.yahoo_crumb = response.text.strip()
        if not self.yahoo_crumb or "Unauthorized" in self.yahoo_crumb:
            raise requests.RequestException("Yahoo Finance returned an invalid crumb")

    def _fetch_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Fetch a compact set of current fundamentals for one NSE symbol."""
        self._init_yahoo_auth()
        modules = ",".join(["price", "summaryDetail", "defaultKeyStatistics", "financialData"])
        response = self.session.get(
            f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}.NS",
            params={"modules": modules, "crumb": self.yahoo_crumb},
            headers={"Referer": "https://finance.yahoo.com/"},
            timeout=20,
        )
        response.raise_for_status()
        result = ((response.json().get("quoteSummary") or {}).get("result") or [])
        if not result:
            return {}
        data = result[0]
        merged: dict[str, Any] = {}
        for section_name in ("price", "summaryDetail", "defaultKeyStatistics", "financialData"):
            section = data.get(section_name) or {}
            if isinstance(section, dict):
                merged.update(section)
        return merged

    def _load_cache(self, output_dir: str) -> dict[str, dict[str, Any]]:
        path = _cache_path(output_dir)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_cache(self, output_dir: str, cache: dict[str, dict[str, Any]]) -> None:
        os.makedirs(output_dir, exist_ok=True)
        with open(_cache_path(output_dir), "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2)

    @staticmethod
    def _show_progress(current: int, total: int, width: int = 34) -> None:
        """Render a compact in-place progress bar for the quality-check loop."""
        if total <= 0:
            return
        ratio = current / total
        filled = int(width * ratio)
        bar = "#" * filled + "-" * (width - filled)
        percent = ratio * 100
        sys.stdout.write(f"\r[*] Quality checks: |{bar}| {percent:6.2f}% ({current}/{total})")
        sys.stdout.flush()
        if current >= total:
            sys.stdout.write("\n")

    def _score(self, row: dict[str, Any]) -> dict[str, Any]:
        revenue_growth = _pct(row.get("revenueGrowth"))
        earnings_growth = _pct(row.get("earningsGrowth"))
        roe = _pct(row.get("returnOnEquity"))
        margin = _pct(row.get("profitMargins"))
        debt_to_equity = _pct(row.get("debtToEquity"))
        pe = _raw(row.get("trailingPE"))
        peg = _raw(row.get("pegRatio"))
        operating_cashflow = _raw(row.get("operatingCashflow"))
        free_cashflow = _raw(row.get("freeCashflow"))

        growth_score = 15 * _growth_points(revenue_growth) + 15 * _growth_points(earnings_growth)
        quality_score = 15 * max(0.0, min((roe or 0.0) / 25.0, 1.0)) + 10 * max(0.0, min((margin or 0.0) / 20.0, 1.0))

        if debt_to_equity is None:
            balance_score = 0.0
        else:
            balance_score = 15 * max(0.0, min((100.0 - debt_to_equity) / 100.0, 1.0))

        cash_value = operating_cashflow if operating_cashflow is not None else free_cashflow
        cash_score = 10.0 if cash_value is not None and cash_value > 0 else 0.0

        # Valuation is growth-aware: a high P/E is not automatically penalised
        # when growth is strong. PEG < 1 is strongest; otherwise compare P/E
        # with a simple growth-adjusted ceiling.
        if peg is not None and peg > 0:
            valuation_score = 15 * max(0.0, min(1.0, 1.5 / peg))
        elif pe is not None and pe > 0:
            growth_anchor = max(revenue_growth or 0.0, earnings_growth or 0.0, 5.0)
            valuation_score = 15 * max(0.0, min(1.0, (growth_anchor * 2.0) / pe))
        else:
            valuation_score = 0.0

        liquidity = _raw(row.get("avg_daily_value_cr")) or 0.0
        liquidity_score = 5 * max(0.0, min(liquidity / 10.0, 1.0))

        total = round(growth_score + quality_score + balance_score + cash_score + valuation_score + liquidity_score, 2)
        data_fields = [revenue_growth, earnings_growth, roe, margin, debt_to_equity, pe]
        coverage = round(sum(value is not None for value in data_fields) / len(data_fields) * 100)

        return {
            "opportunity_score": total,
            "growth_score": round(growth_score, 2),
            "quality_score": round(quality_score, 2),
            "financial_health_score": round(balance_score, 2),
            "cash_flow_score": round(cash_score, 2),
            "valuation_score": round(valuation_score, 2),
            "revenue_growth_pct": revenue_growth,
            "earnings_growth_pct": earnings_growth,
            "roe_pct": roe,
            "profit_margin_pct": margin,
            "debt_to_equity_pct": debt_to_equity,
            "pe": pe,
            "peg": peg,
            "fundamental_data_coverage_pct": coverage,
        }

    def run(
        self,
        segment: str,
        top: int = 50,
        refresh: bool = False,
        universe_limit: int | None = None,
        quality_pool: int | None = None,
        output_dir: str = "./outputs",
    ) -> list[dict[str, Any]]:
        segment = segment.strip().upper()
        if segment not in SEGMENTS:
            raise ValueError(f"Unknown market-cap segment: {segment}")
        if top < 1:
            raise ValueError("top must be at least 1")

        print(f"\n[*] Scanning entire {segment} universe...")
        rows = self.universe.discover(limit=universe_limit, refresh=refresh)
        rows = [row for row in rows if row.get("market_cap_cr") is not None]
        rows.sort(key=lambda row: float(row["market_cap_cr"]), reverse=True)

        ranked: list[dict[str, Any]] = []
        for rank, row in enumerate(rows, 1):
            category = classify_rank(rank, float(row["market_cap_cr"]))
            if category == segment:
                ranked.append({**row, "market_cap_rank": rank, "market_cap_category": category})

        # Stage 1 is intentionally universe-wide: quality, growth, financial
        # health, cash flow and valuation determine the top 50. Liquidity is a
        # scoring input, not a gate that decides which companies get checked.
        pool = ranked
        cache = self._load_cache(output_dir)
        enriched = 0
        failed = 0

        print(f"[+] Quality checks queued for {len(pool)} {segment} candidates")
        self._show_progress(0, len(pool))

        for index, row in enumerate(pool, 1):
            symbol = str(row.get("symbol") or "").upper()
            if not symbol:
                self._show_progress(index, len(pool))
                continue
            if symbol in cache:
                fundamentals = cache[symbol]
            else:
                try:
                    fundamentals = self._fetch_fundamentals(symbol)
                    cache[symbol] = fundamentals
                    enriched += 1
                    if self.request_delay:
                        time.sleep(self.request_delay)
                except requests.RequestException as exc:
                    fundamentals = {}
                    failed += 1
                    print(f"\n[!] Fundamental data unavailable for {symbol}: {exc}")
            row.update({
                "fundamental_source": "Yahoo Finance" if fundamentals else "DATA GAP",
                **fundamentals,
            })
            row.update(self._score(row))
            if index % 10 == 0 or index == len(pool):
                self._show_progress(index, len(pool))

        self._save_cache(output_dir, cache)
        pool.sort(key=lambda row: (float(row.get("opportunity_score") or 0.0), float(row.get("avg_daily_value_cr") or 0.0)), reverse=True)
        selected = pool[:top]

        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "opportunity_scan.csv")
        fields = [
            "symbol", "company_name", "market_cap_category", "market_cap_rank", "market_cap_cr", "price",
            "avg_daily_value_cr", "opportunity_score", "growth_score", "quality_score",
            "financial_health_score", "cash_flow_score", "valuation_score", "revenue_growth_pct",
            "earnings_growth_pct", "roe_pct", "profit_margin_pct", "debt_to_equity_pct", "pe", "peg",
            "fundamental_data_coverage_pct", "fundamental_source",
        ]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(selected)

        print(f"[+] Universe rows: {len(rows)}")
        print(f"[+] {segment} candidates quality-checked: {len(ranked)}")
        print(f"[+] Newly enriched: {enriched} | failed: {failed}")
        print(f"[+] Saved top {len(selected)} watchlist candidates to: {path}")
        print("\nTOP 50 WATCHLIST — Stage 1 quality ranking only")
        print("Management/governance is not treated as clean merely because data is missing; deep research remains required.")
        print("-" * 110)
        for index, row in enumerate(selected, 1):
            growth = row.get("earnings_growth_pct")
            pe = row.get("pe")
            print(
                f"{index:>2}. {row['symbol']:<15} Score {float(row.get('opportunity_score') or 0):>5.1f}  "
                f"Growth {str(round(growth, 1)) + '%' if isinstance(growth, (int, float)) else 'N/A':>7}  "
                f"P/E {str(round(pe, 1)) if isinstance(pe, (int, float)) else 'N/A':>6}  "
                f"MCap ₹{float(row['market_cap_cr']):>9.0f} Cr"
            )
        return selected


def run_opportunity_scan(segment: str, top: int = 50, refresh: bool = False, universe_limit: int | None = None,
                         quality_pool: int | None = None, output_dir: str = "./outputs"):
    return OpportunityScanner().run(segment, top, refresh, universe_limit, quality_pool, output_dir)
