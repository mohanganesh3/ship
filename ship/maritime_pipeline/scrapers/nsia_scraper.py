"""
nsia_scraper.py — Norwegian Safety Investigation Authority (NSIA) maritime report downloader.

Source  : https://www.nsia.no/Maritime/Investigation-reports
Licence : Norwegian Government Open Data (NLOD) — free for reuse
Reports in English and Norwegian; English versions preferred.

Usage:
    cd maritime_pipeline
    python scrapers/nsia_scraper.py
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

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
        logging.FileHandler(LOGS_DIR / "nsia_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("nsia")

BASE_URL           = "https://www.nsia.no"
REPORTS_INDEX      = "https://www.nsia.no/Marine/Published-reports"
CURRENT_INDEX      = "https://www.nsia.no/Marine/Current-investigations"
RSS_MARITIME       = "https://www.nsia.no/rss?lcid=1033&type=3"  # English maritime RSS
PDF_PARAM          = "?pid=SHT-Report-ReportFile&attach=1"   # magic suffix for PDF download
SOURCE_NAME   = "nsia"
OUT_DIR       = SOURCES["nsia"]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
    "Accept-Language": "en-GB,en;q=0.9,nb;q=0.7",
})


def _get(url: str, stream: bool = False) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _collect_report_pages(max_pages: int = 999) -> list[dict]:
    """Collect NSIA maritime investigation reports.
    
    Strategy:
    1. Scrape /Marine/Published-reports listing (30+ report cards)
    2. Also try /Marine/Current-investigations for in-progress reports
    3. RSS feed as fallback for any recent ones missed
    
    PDF URL pattern: {report_url}?pid=SHT-Report-ReportFile&attach=1
    """
    items: list[dict] = []
    seen: set[str] = set()

    def _add_item(href: str, title: str = "", date: str = "") -> None:
        """Add a report item with its PDF URL derived from pattern."""
        if not href:
            return
        if not href.startswith("http"):
            href = BASE_URL + href
        if href in seen:
            return
        seen.add(href)
        # Generate PDF URL from the known pattern
        pdf_url = href.rstrip("/") + PDF_PARAM
        items.append({
            "title": title or href.split("/")[-1].replace("-", " ").title(),
            "detail_url": href,
            "pdf_url": pdf_url,
            "date": date,
            "lang": "en",
        })

    # Strategy 1: Published-reports listing page
    log.info("Fetching NSIA Published-reports listing …")
    try:
        resp = _get(REPORTS_INDEX)
        soup = BeautifulSoup(resp.text, "html.parser")
        seen_hrefs: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/Marine/Published-reports/" in href and href not in seen_hrefs:
                seen_hrefs.add(href)
                title = a.get_text(strip=True) or ""
                _add_item(href, title=title)
        log.info("Published-reports listing: found %d unique reports", len(items))
    except Exception as exc:
        log.error("Published-reports listing failed: %s", exc)

    # Strategy 2: Current-investigations listing (no report PDFs yet — these are ongoing)
    # We skip this to avoid 404 errors — current investigations have no downloadable report
    # log.info("Skipping Current-investigations (ongoing, no report PDFs yet)")
    log.info("Fetching NSIA Current-investigations listing …")
    prev_count = len(items)
    try:
        resp2 = _get(CURRENT_INDEX)
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        for a in soup2.find_all("a", href=True):
            href = a["href"]
            if "/Marine/Current-investigations/" in href:
                # Skip — these are ongoing and have no PDFs
                pass  # Do not add current investigations
        log.info("Current-investigations: skipped (no report PDFs for ongoing investigations)")
    except Exception as exc:
        log.error("Current-investigations failed: %s", exc)

    # Strategy 3: RSS feed for any recent reports missed
    log.info("Fetching NSIA maritime RSS feed …")
    prev_count = len(items)
    try:
        resp3 = _get(RSS_MARITIME)
        soup3 = BeautifulSoup(resp3.content, "xml")
        for entry in soup3.find_all("item"):
            link_tag = entry.find("link")
            title_tag = entry.find("title")
            date_tag = entry.find("pubDate")
            detail_url = link_tag.text.strip() if link_tag else ""
            if detail_url and "/Marine/" in detail_url:
                _add_item(
                    detail_url,
                    title=title_tag.text.strip() if title_tag else "",
                    date=date_tag.text.strip() if date_tag else "",
                )
        log.info("RSS feed: +%d additional items", len(items) - prev_count)
    except Exception as exc:
        log.error("RSS feed failed: %s", exc)

    log.info("Total NSIA maritime reports found: %d", len(items))
    return items


def _resolve_pdf_from_detail(detail_url: str) -> str:
    """NSIA PDF URL is derived directly from the report URL using the known pattern.
    The PDF download link is: {report_url}?pid=SHT-Report-ReportFile&attach=1
    We only fall back to HTML scraping if the direct download fails.
    """
    # Primary: use the known PDF param pattern
    pdf_url = detail_url.rstrip("/") + PDF_PARAM
    return pdf_url


def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        return False
    if is_downloaded(pdf_url):
        return True

    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_",
                      pdf_url.split("/")[-1].split("?")[0] or "nsia_report.pdf")
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    year = re.search(r"(\d{4})", item.get("date", ""))
    sub = OUT_DIR / (year.group(1) if year else "misc")
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
        log.info("✓ %s (%.1f KB)", out_path.name, n / 1024)
        return True
    except Exception as exc:
        log.error("✗ %s: %s", pdf_url, exc)
        mark_download_failed(pdf_url, str(exc))
        return False


def run(max_pages: int = 999) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = _collect_report_pages(max_pages=max_pages)

    # PDF URLs are already set from the ?pid= pattern — only resolve if missing
    needs_resolve = [i for i in items if not i["pdf_url"]]
    if needs_resolve:
        log.info("Resolving %d detail pages for PDF links …", len(needs_resolve))
        for item in tqdm(needs_resolve, desc="Resolving PDF URLs", unit="page"):
            item["pdf_url"] = _resolve_pdf_from_detail(item["detail_url"])

    ok = fail = skip = 0
    for item in tqdm(items, desc="Downloading NSIA reports", unit="pdf"):
        if not item["pdf_url"]:
            skip += 1
            continue
        if is_downloaded(item["pdf_url"]):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="NSIA maritime investigation report scraper")
    ap.add_argument("--max-pages", type=int, default=999)
    args = ap.parse_args()
    run(max_pages=args.max_pages)
