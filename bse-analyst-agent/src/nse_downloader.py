"""Annual-report downloader with NSE primary source and public-web fallback."""

import os
import re
from typing import Optional
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup


class NSEDownloader:
    BASE_HOME = "https://www.nseindia.com"
    API_URL = "https://www.nseindia.com/api/annual-reports"
    SEARCH_URL = "https://html.duckduckgo.com/html/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    def __init__(self, download_dir: str = "./data/downloads"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._session_initialized = False

    @staticmethod
    def _clean_symbol(symbol: str) -> str:
        value = symbol.upper().strip()
        return value[:-3] if value.endswith(".NS") else value

    def _init_session(self) -> bool:
        try:
            resp = self.session.get(self.BASE_HOME, headers={**self.HEADERS, "Referer": "https://www.google.com/"}, timeout=15)
            resp.raise_for_status()
            self._session_initialized = True
            return True
        except requests.RequestException as exc:
            print(f"[!] NSE access unavailable ({exc}). Using annual-report fallback search.")
            return False

    @staticmethod
    def _is_pdf_candidate(url: str, title: str = "") -> bool:
        text = f"{url} {title}".lower()
        # Some BSE annual-report PDFs use opaque AttachHis UUID URLs, so the
        # URL itself may contain neither 'annual' nor 'report'. The search
        # result title is therefore equally important.
        return ".pdf" in text and (
            any(term in text for term in ("annual", "report", "ar_", "financial"))
            or "bseindia.com" in url.lower()
        )

    def _fallback_search(self, symbol: str) -> Optional[str]:
        clean_symbol = self._clean_symbol(symbol)
        queries = [
            f'"{clean_symbol}" "annual report" filetype:pdf',
            f'"{clean_symbol}" "annual report 2025-26" pdf',
            f'"{clean_symbol}" "annual report 2024-25" pdf',
            f'"KJMC Financial Services Limited" "annual report" pdf',
            f'"KJMC Financial Services Limited" "38th Annual Report" pdf',
            f'"530235" "annual report" pdf',
            f'site:bseindia.com "KJMC Financial Services" "Annual Report" pdf',
            f'site:bseindia.com "530235" "Annual Report" pdf',
        ]
        for query in queries:
            try:
                response = self.session.get(
                    self.SEARCH_URL,
                    params={"q": query},
                    headers={**self.HEADERS, "Referer": "https://duckduckgo.com/"},
                    timeout=20,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                candidates: list[tuple[int, str]] = []
                for anchor in soup.select("a.result__a"):
                    href = anchor.get("href") or ""
                    title = anchor.get_text(" ", strip=True)
                    match = re.search(r"uddg=([^&]+)", href)
                    url = unquote(match.group(1)) if match else href
                    if not url.startswith(("http://", "https://")) or not self._is_pdf_candidate(url, title):
                        continue
                    lower_url = url.lower()
                    lower_title = title.lower()
                    score = 0
                    if "bseindia.com" in lower_url:
                        score += 120
                    if "nsearchives.nseindia.com" in lower_url:
                        score += 110
                    if "kjmc" in lower_url or "kjmc" in lower_title:
                        score += 40
                    if "530235" in lower_url or "530235" in lower_title:
                        score += 35
                    if ".pdf" in lower_url:
                        score += 20
                    if "annual" in lower_title or "annual" in lower_url:
                        score += 25
                    if "report" in lower_title or "report" in lower_url:
                        score += 15
                    if "2025-26" in lower_title or "2025-26" in lower_url or "2026" in lower_title or "2026" in lower_url:
                        score += 15
                    if "2024-25" in lower_title or "2024-25" in lower_url or "2025" in lower_title or "2025" in lower_url:
                        score += 10
                    candidates.append((score, url))
                if candidates:
                    candidates.sort(reverse=True)
                    url = candidates[0][1]
                    print(f"[+] Fallback annual-report PDF found for {clean_symbol}: {url}")
                    return url
            except requests.RequestException as exc:
                print(f"[!] Fallback annual-report search failed for {clean_symbol}: {exc}")
        print(f"[!] Could not locate an annual-report PDF for '{clean_symbol}' via NSE or fallback search.")
        return None

    def get_latest_annual_report_url(self, symbol: str) -> Optional[str]:
        symbol = self._clean_symbol(symbol)
        if not self._session_initialized:
            self._init_session()
        params = {"index": "equities", "symbol": symbol}
        api_headers = {**self.HEADERS, "Referer": "https://www.nseindia.com/companies-listing/corporate-filings-annual-reports", "Accept": "application/json, text/plain, */*"}
        try:
            res = self.session.get(self.API_URL, params=params, headers=api_headers, timeout=15)
            if res.status_code in (401, 403):
                print(f"[!] NSE annual-report API returned HTTP {res.status_code} for {symbol}.")
                return self._fallback_search(symbol)
            res.raise_for_status()
            items = (res.json() or {}).get("data", [])
            if not items:
                print(f"[!] No annual reports returned by NSE for symbol '{symbol}'. Trying fallback search.")
                return self._fallback_search(symbol)
            latest = items[0]
            file_url = latest.get("fileName")
            if file_url:
                print(f"[+] Found NSE filing for {symbol} ({latest.get('companyName', '')}) - FY: {latest.get('finYear', 'N/A')}")
                return file_url
            return self._fallback_search(symbol)
        except (requests.RequestException, ValueError) as exc:
            print(f"[!] NSE annual-report lookup failed for {symbol}: {exc}")
            return self._fallback_search(symbol)

    def download_report(self, symbol: str, custom_filename: Optional[str] = None, force_redownload: bool = False) -> Optional[str]:
        clean_symbol = self._clean_symbol(symbol)
        target_filename = custom_filename or f"{clean_symbol}_latest_annual_report.pdf"
        target_path = os.path.join(self.download_dir, target_filename)
        if os.path.exists(target_path) and os.path.getsize(target_path) > 10 * 1024 and not force_redownload:
            print(f"[✓] File already exists: {target_path}")
            print("[*] Skipping download. Using cached report directly for analysis.")
            return target_path
        pdf_url = self.get_latest_annual_report_url(clean_symbol)
        if not pdf_url:
            return None
        print(f"[*] Downloading annual report from: {pdf_url}")
        temp_path = f"{target_path}.tmp"
        try:
            res = self.session.get(pdf_url, headers={**self.HEADERS, "Referer": "https://www.nseindia.com/"}, stream=True, timeout=90)
            res.raise_for_status()
            with open(temp_path, "wb") as fh:
                for chunk in res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        fh.write(chunk)
            if os.path.getsize(temp_path) <= 10 * 1024:
                raise IOError("Downloaded annual-report file is unexpectedly small")
            if os.path.exists(target_path):
                os.remove(target_path)
            os.replace(temp_path, target_path)
            print(f"[+] Successfully downloaded: {target_path}")
            return target_path
        except Exception as exc:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            print(f"[x] Annual-report download failed for {clean_symbol}: {exc}")
            return None
