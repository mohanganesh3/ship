"""
ntsb_scraper.py — US National Transportation Safety Board marine report downloader.

Source  : https://www.ntsb.gov/investigations/AccidentReports/Pages/marine.aspx
Licence : US Government public domain
Note    : The NTSB marine page partially uses JavaScript for filtering. This scraper
          uses requests+BS4 against the static HTML; if that yields <50 results it
          prints a Playwright fallback hint.

Usage:
    cd maritime_pipeline
    python scrapers/ntsb_scraper.py
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import (
    init_db, is_downloaded, mark_download_pending,
    mark_download_done, mark_download_failed, sha256_file,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "ntsb_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ntsb")

BASE_URL      = "https://www.ntsb.gov"
MARINE_PAGE   = "https://www.ntsb.gov/investigations/AccidentReports/Pages/marine.aspx"
ACCIDENT_FEED = "https://www.ntsb.gov/investigations/AccidentReports/Lists/AccidentReportList/AllItems.aspx?View=%7BF8E24E5A-7BE1-48DA-B77E-5B900F1F6DAF%7D&FilterField1=Mode&FilterValue1=Marine"
# Direct PDF URL pattern confirmed working:
# https://www.ntsb.gov/investigations/AccidentReports/Reports/MAR2401.pdf
REPORTS_BASE  = "https://www.ntsb.gov/investigations/AccidentReports/Reports"

SOURCE_NAME   = "ntsb"
OUT_DIR       = SOURCES[SOURCE_NAME]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})


def _get(url: str, stream: bool = False, params: dict = None) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True, params=params)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _pdf_filename_from_url(url: str) -> str:
    name = url.split("/")[-1].split("?")[0]
    if not name.endswith(".pdf"):
        name += ".pdf"
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", name)


def _generate_candidate_urls() -> list[dict]:
    """
    Generate candidate NTSB marine report PDF URLs by brute-force.
    NTSB marine reports follow pattern: MAR[YY][NN].pdf or MAB[YY][NN].pdf
    Years 1990-2025, report numbers 01-30.
    Confirmed working: MAR2401.pdf, MAR2301.pdf
    """
    import datetime as dt
    current_year = dt.date.today().year
    items = []
    for prefix in ["MAR", "MAB"]:
        for year in range(90, 100):  # 1990-1999
            for num in range(1, 25):
                fn = f"{prefix}{year:02d}{num:02d}.pdf"
                items.append({
                    "title": fn.replace(".pdf", ""),
                    "report_number": fn.replace(".pdf", ""),
                    "date": f"19{year:02d}",
                    "location": "",
                    "pdf_url": f"{REPORTS_BASE}/{fn}",
                })
        for year in range(0, (current_year - 2000) + 2):  # 2000-current
            for num in range(1, 30):
                fn = f"{prefix}{year:02d}{num:02d}.pdf"
                items.append({
                    "title": fn.replace(".pdf", ""),
                    "report_number": fn.replace(".pdf", ""),
                    "date": f"20{year:02d}",
                    "location": "",
                    "pdf_url": f"{REPORTS_BASE}/{fn}",
                })
    return items


def _check_url_exists(url: str) -> bool:
    """HEAD request to check if PDF exists without downloading."""
    try:
        resp = SESSION.head(url, timeout=15, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


def _scrape_static_html() -> list[dict]:
    """Parse the NTSB marine accident reports page (static HTML portion)."""
    log.info("Fetching NTSB marine reports page …")
    items: list[dict] = []
    seen: set[str] = set()

    try:
        resp = _get(MARINE_PAGE)
        soup = BeautifulSoup(resp.text, "html.parser")

        content = soup.select_one("#ctl00_PlaceHolderMain_RichHtmlField1_ctl00, main, #content, .ms-rtestate-field")
        search_area = content if content else soup

        for a in search_area.find_all("a", href=True):
            href = a["href"]
            abs_href = urljoin(BASE_URL, href)
            if ".pdf" in href.lower() and abs_href not in seen:
                seen.add(abs_href)
                title = a.get_text(strip=True) or _pdf_filename_from_url(href)
                items.append({"title": title, "pdf_url": abs_href,
                               "report_number": "", "date": "", "location": ""})
    except Exception as exc:
        log.error("Static HTML scrape failed: %s", exc)

    log.info("Static HTML → %d PDF links", len(items))
    return items


def _scrape_paged_list() -> list[dict]:
    """NTSB SharePoint-style paginated list."""
    items: list[dict] = []
    seen: set[str] = set()
    page = 0
    page_size = 100

    base = "https://www.ntsb.gov/_layouts/15/listdata.svc/AccidentReportList"
    params = {
        "$filter": "Mode eq 'Marine'",
        "$orderby": "Accident_Date desc",
        "$top": str(page_size),
        "$skip": "0",
        "$format": "json",
    }

    while True:
        params["$skip"] = str(page * page_size)
        try:
            resp = SESSION.get(base, params=params, timeout=REQUEST_TIMEOUT,
                               headers={**SESSION.headers, "Accept": "application/json"})
            if resp.status_code != 200:
                break
            data = resp.json()
            rows = data.get("value", data.get("d", {}).get("results", []))
            if not rows:
                break
            for row in rows:
                pdf_path = row.get("PDF_Link") or row.get("pdf_link") or ""
                if not pdf_path:
                    continue
                pdf_url = urljoin(BASE_URL, pdf_path.strip())
                if pdf_url in seen:
                    continue
                seen.add(pdf_url)
                items.append({
                    "title": row.get("Title", ""),
                    "report_number": row.get("Report_Number", ""),
                    "date": row.get("Accident_Date", ""),
                    "location": row.get("Location", ""),
                    "pdf_url": pdf_url,
                })
            if len(rows) < page_size:
                break
            page += 1
            time.sleep(RATE_LIMIT)
        except Exception as exc:
            log.warning("Paged list fetch failed at page %d: %s", page, exc)
            break

    log.info("Paged list → %d PDF links", len(items))
    return items



def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        return False
    if is_downloaded(pdf_url):
        return True

    filename = _pdf_filename_from_url(pdf_url)
    # Organise by year if parseable
    year = ""
    if item.get("date"):
        m = re.search(r"(\d{4})", item["date"])
        year = m.group(1) if m else ""
    sub = OUT_DIR / (year or "unknown")
    sub.mkdir(parents=True, exist_ok=True)
    out_path = sub / filename

    mark_download_pending(pdf_url, SOURCE_NAME)
    try:
        resp = _get(pdf_url, stream=True)
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(65536):
                fh.write(chunk)
        h = sha256_file(out_path)
        n = out_path.stat().st_size
        mark_download_done(pdf_url, out_path, h, n)
        with open(METADATA_FILE, "a") as mf:
            mf.write(json.dumps({**item, "local_path": str(out_path),
                                  "downloaded_at": datetime.utcnow().isoformat()}) + "\n")
        log.info("✓ %s (%.1f KB)", filename, n / 1024)
        return True
    except Exception as exc:
        log.error("✗ %s: %s", pdf_url, exc)
        mark_download_failed(pdf_url, str(exc))
        return False


def run() -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Try paged list first (may fail on JS-heavy site)
    items = _scrape_paged_list()

    if len(items) < 10:
        log.warning("Paged list returned only %d items — trying static HTML …", len(items))
        static = _scrape_static_html()
        existing_urls = {i["pdf_url"] for i in items}
        for s in static:
            if s["pdf_url"] not in existing_urls:
                items.append(s)

    if len(items) < 10:
        log.info("Falling back to brute-force PDF URL generation …")
        candidates = _generate_candidate_urls()
        existing_urls = {i["pdf_url"] for i in items}
        log.info("Checking %d candidate URLs (HEAD requests) …", len(candidates))
        found = 0
        for c in tqdm(candidates, desc="Probing NTSB report URLs", unit="url"):
            if c["pdf_url"] in existing_urls:
                continue
            time.sleep(0.3)
            if _check_url_exists(c["pdf_url"]):
                items.append(c)
                existing_urls.add(c["pdf_url"])
                found += 1
        log.info("Brute-force found %d additional reports (total: %d)", found, len(items))

    log.info("Total NTSB marine reports to process: %d", len(items))

    ok = fail = skip = 0
    for item in tqdm(items, desc="Downloading NTSB reports", unit="pdf"):
        if is_downloaded(item["pdf_url"]):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="NTSB marine investigation report scraper")
    ap.parse_args()
    run()
