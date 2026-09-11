"""Structured financial-data provider for deep-stock analysis.

Financial numbers should come from structured market data, not from an LLM
reading annual-report tables. The annual-report PDF remains a qualitative
source for governance, forensic and management commentary.

Primary regulatory probe: NSE financial-results filings.
Fallback: public Screener.in company tables for up to ten years of structured
history used by the deterministic financial engine.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from .financial_tools import AnnualFinancials, CompanyFinancialHistory


class FinancialDataError(RuntimeError):
    """Raised when structured financial data is unavailable or unreliable."""


class StructuredFinancialProvider:
    NSE_RESULTS_URL = "https://www.nseindia.com/api/corporates-financial-results"
    NSE_RESULTS_PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"
    SCREENER_URLS = (
        "https://www.screener.in/company/{symbol}/consolidated/",
        "https://www.screener.in/company/{symbol}/",
    )

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    @staticmethod
    def _symbol(symbol: str) -> str:
        return symbol.upper().strip().removesuffix(".NS").removesuffix(".BO")

    def _warm_nse(self) -> None:
        try:
            self.session.get(self.NSE_RESULTS_PAGE, timeout=self.timeout)
        except requests.RequestException:
            pass

    def _nse_annual_probe(self, symbol: str) -> bool:
        """Confirm that NSE exposes annual financial-result filings."""
        self._warm_nse()
        try:
            response = self.session.get(
                self.NSE_RESULTS_URL,
                params={"index": "equities", "period": "Annual", "symbol": symbol},
                headers={"Referer": self.NSE_RESULTS_PAGE},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("data", []) if isinstance(payload, dict) else payload
            return bool(rows)
        except (requests.RequestException, ValueError, TypeError):
            return False

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None:
            return None
        text = str(value).strip().replace("₹", "").replace(",", "")
        if text in {"", "-", "—", "NA", "N/A"}:
            return None
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()")
        text = re.sub(r"[^0-9.+-]", "", text)
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        return -number if negative else number

    @classmethod
    def _table(cls, soup: BeautifulSoup, section_id: str) -> dict[str, list[float | None]]:
        section = soup.find(id=section_id)
        if section is None:
            return {}
        table = section.find("table") if section.name != "table" else section
        if table is None:
            return {}

        result: dict[str, list[float | None]] = {}
        header_row = table.find("tr")
        if header_row:
            raw_headers = [cell.get_text(" ", strip=True) for cell in header_row.find_all(["th", "td"])]
            result["__periods__"] = raw_headers[1:] if len(raw_headers) > 1 else []

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True)
            if not label or label.lower() == "report date":
                continue
            values = [cls._number(cell.get_text(" ", strip=True)) for cell in cells[1:]]
            if values:
                result[label.lower()] = values
        return result

    @staticmethod
    def _row(table: dict[str, list[float | None]], *names: str) -> list[float | None] | None:
        normalized = {re.sub(r"[^a-z0-9]", "", name.lower()) for name in names}
        for key, values in table.items():
            if key == "__periods__":
                continue
            key_norm = re.sub(r"[^a-z0-9]", "", key)
            if key_norm in normalized:
                return values
        return None

    @staticmethod
    def _period_year(period: str) -> str | None:
        match = re.search(r"(?:Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb)[- ]?(\d{2,4})", period, re.I)
        if not match:
            return None
        year = int(match.group(1))
        if year < 100:
            year += 2000
        return f"FY{year}"

    @staticmethod
    def _sum_if_complete(*values: float | None) -> float | None:
        if any(value is None for value in values):
            return None
        return sum(float(value) for value in values if value is not None)

    @staticmethod
    def _reliable_records(records: list[AnnualFinancials]) -> list[AnnualFinancials]:
        filtered = [r for r in records if re.match(r"^FY20\d{2}$", r.fiscal_year)]
        return filtered[-10:]

    def _screener_history(self, symbol: str) -> CompanyFinancialHistory:
        last_error: Exception | None = None
        for template in self.SCREENER_URLS:
            try:
                return self._parse_screener(symbol, template.format(symbol=symbol))
            except (requests.RequestException, FinancialDataError) as exc:
                last_error = exc
        raise FinancialDataError(f"Could not read Screener financial tables for {symbol}: {last_error}")

    def _parse_screener(self, symbol: str, url: str) -> CompanyFinancialHistory:
        response = self.session.get(url, headers={"Referer": "https://www.screener.in/"}, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        pnl = self._table(soup, "profit-loss")
        balance = self._table(soup, "balance-sheet")
        cashflow = self._table(soup, "cash-flow")
        periods = pnl.get("__periods__", [])
        years = [self._period_year(period) for period in periods]

        sales = self._row(pnl, "sales", "revenue")
        operating_profit = self._row(pnl, "operating profit")
        interest = self._row(pnl, "interest", "finance cost", "finance costs")
        net_profit = self._row(pnl, "net profit", "profit after tax")
        equity_capital = self._row(balance, "equity share capital", "equity capital")
        reserves = self._row(balance, "reserves")
        borrowings = self._row(balance, "borrowings")
        investments = self._row(balance, "investments")
        cash_bank = self._row(balance, "cash & bank", "cash and bank", "cash & equivalents")
        cfo = self._row(cashflow, "cash from operating activity", "cash from operations")

        arrays = [sales, operating_profit, interest, net_profit, equity_capital, reserves, borrowings, investments, cash_bank, cfo]
        if not years or any(values is None for values in arrays):
            raise FinancialDataError(f"Incomplete Screener financial tables for {symbol}")

        count = min(len(years), *(len(values) for values in arrays if values is not None))
        records: list[AnnualFinancials] = []
        for idx in range(count):
            fiscal_year = years[idx]
            if not fiscal_year:
                continue
            revenue = sales[idx]
            pat = net_profit[idx]
            if revenue is None or pat is None:
                continue
            total_equity = self._sum_if_complete(equity_capital[idx], reserves[idx])
            cash = self._sum_if_complete(investments[idx], cash_bank[idx])
            records.append(AnnualFinancials(
                fiscal_year=fiscal_year,
                revenue=float(revenue),
                ebit=operating_profit[idx],
                pat=float(pat),
                total_debt=borrowings[idx],
                total_equity=total_equity,
                cash_equivalents=cash,
                cfo=cfo[idx],
                interest_expense=interest[idx],
            ))

        records = self._reliable_records(records)
        if not records:
            raise FinancialDataError(f"No valid annual financial years for {symbol}")

        nonzero_revenue = sum(1 for row in records if row.revenue > 0)
        nonzero_pat = sum(1 for row in records if row.pat != 0)
        available_cfo = sum(1 for row in records if row.cfo is not None)
        nonzero_cfo = sum(1 for row in records if row.cfo is not None and row.cfo != 0)
        if nonzero_revenue != len(records) or nonzero_pat != len(records):
            raise FinancialDataError(f"Financial data quality check failed for {symbol}")
        if available_cfo >= 2 and nonzero_cfo < 2:
            raise FinancialDataError(f"Financial data quality check failed for {symbol}")

        return CompanyFinancialHistory(
            years=records,
            source="Screener.in public structured tables",
            data_quality="MEDIUM",
            source_notes="Structured annual P&L, balance-sheet and cash-flow tables; no PDF financial-table extraction used.",
        )

    def get_history(self, symbol: str) -> CompanyFinancialHistory:
        clean_symbol = self._symbol(symbol)
        nse_available = self._nse_annual_probe(clean_symbol)
        history = self._screener_history(clean_symbol)
        if nse_available:
            history.source_notes += " NSE annual financial-result filings were also detected and can be used for future cross-checking."
        return history
