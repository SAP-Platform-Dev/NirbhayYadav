"""
src/nse_downloader.py
Automated downloader for Indian Annual Reports via NSE India API.
Includes local file caching and multi-year report support.
"""

import os
import requests
from typing import Optional


class NSEDownloader:
    BASE_HOME = "https://www.nseindia.com"
    API_URL = "https://www.nseindia.com/api/annual-reports"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, download_dir: str = "./data/downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._session_initialized = False

    def _init_session(self):
        """Visits NSE homepage to initialize required cookies and session state."""
        try:
            resp = self.session.get(self.BASE_HOME, timeout=15)
            resp.raise_for_status()
            self._session_initialized = True
        except Exception as e:
            print(f"[!] Warning: Could not initialize NSE session cookies: {e}")

    def get_annual_report_records(self, symbol: str) -> list[dict]:
        """Return available NSE annual-report records, newest first."""
        if not self._session_initialized:
            self._init_session()

        params = {"index": "equities", "symbol": symbol.upper().strip()}
        api_headers = {
            "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-annual-reports",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            res = self.session.get(self.API_URL, params=params, headers=api_headers, timeout=30)
            if res.status_code in (401, 403):
                self._init_session()
                res = self.session.get(self.API_URL, params=params, headers=api_headers, timeout=30)
            res.raise_for_status()
            data = res.json()
            items = data.get("data", []) if isinstance(data, dict) else []
            return [item for item in items if isinstance(item, dict) and item.get("fileName")]
        except Exception as e:
            print(f"[x] Error querying NSE annual reports: {e}")
            return []

    def get_latest_annual_report_url(self, symbol: str) -> Optional[str]:
        """Fetch the latest annual-report download URL."""
        records = self.get_annual_report_records(symbol)
        if not records:
            print(f"[!] No annual reports found on NSE for symbol '{symbol}'.")
            return None
        latest = records[0]
        print(f"[+] Found filing for {symbol} ({latest.get('companyName', '')}) - FY: {latest.get('finYear', 'N/A')}")
        return latest.get("fileName")

    @staticmethod
    def _safe_year(record: dict, index: int) -> str:
        value = str(record.get("finYear") or record.get("financialYear") or record.get("year") or "").strip()
        return value.replace("/", "-").replace(" ", "_") or f"report_{index + 1}"

    def download_reports(self, symbol: str, years: int = 10, force_redownload: bool = False) -> list[dict]:
        """Download up to ``years`` annual reports and return local paths plus metadata."""
        records = self.get_annual_report_records(symbol)
        if not records:
            return []

        selected = records[:max(1, years)]
        results: list[dict] = []
        for index, record in enumerate(selected):
            fy = self._safe_year(record, index)
            target_filename = f"{symbol.upper().strip()}_{fy}_annual_report.pdf"
            target_path = os.path.join(self.download_dir, target_filename)

            if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024 and not force_redownload:
                print(f"[✓] Cached annual report: {target_filename}")
            else:
                pdf_url = record.get("fileName")
                print(f"[*] Downloading {symbol.upper()} {record.get('finYear', fy)} annual report...")
                try:
                    temp_path = f"{target_path}.tmp"
                    res = self.session.get(pdf_url, stream=True, timeout=120)
                    res.raise_for_status()
                    with open(temp_path, "wb") as f:
                        for chunk in res.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.exists(target_path):
                        os.remove(target_path)
                    os.rename(temp_path, target_path)
                except Exception as exc:
                    print(f"[!] Failed to download {symbol.upper()} {record.get('finYear', fy)}: {exc}")
                    continue

            results.append({
                "fiscal_year": str(record.get("finYear") or record.get("financialYear") or fy),
                "path": target_path,
                "url": record.get("fileName"),
            })
        return results

    def download_report(self, symbol: str, custom_filename: Optional[str] = None, force_redownload: bool = False) -> Optional[str]:
        """Download/cache the latest annual report for the existing deep-analysis path."""
        target_filename = custom_filename or f"{symbol.upper()}_latest_annual_report.pdf"
        target_path = os.path.join(self.download_dir, target_filename)

        if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024 and not force_redownload:
            print(f"[✓] File already exists: {target_path}")
            print("[*] Skipping download. Using cached report directly for analysis.")
            return target_path

        pdf_url = self.get_latest_annual_report_url(symbol)
        if not pdf_url:
            return None

        print(f"[*] Downloading PDF from: {pdf_url}")
        temp_path = f"{target_path}.tmp"
        res = self.session.get(pdf_url, stream=True, timeout=90)
        res.raise_for_status()
        with open(temp_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)
        print(f"[+] Successfully downloaded: {target_path}")
        return target_path
