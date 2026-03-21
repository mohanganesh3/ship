"""
dutch_safety_scraper.py — Dutch Safety Board (Onderzoeksraad) maritime report downloader.

Source  : https://www.onderzoeksraad.nl/en/page/3885/marine
Licence : CC BY 4.0 (free to reuse with attribution)
Reports available in English, Netherlands transport crash/marine investigations.

Usage:
    cd maritime_pipeline
    python scrapers/dutch_safety_scraper.py
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
        logging.FileHandler(LOGS_DIR / "dutch_safety_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("dutch_safety")

BASE_URL      = "https://onderzoeksraad.nl"
# Shipping/Marine thema page — static listing of maritime investigations
MARINE_INDEX  = "https://onderzoeksraad.nl/en/thema/shipping/"
# All investigations with pagination — filter for shipping type
INVEST_INDEX  = "https://onderzoeksraad.nl/en/home/investigations/"
INVEST_PARAMS = {"_sort": "date:DESC", "_type": "shipping"}
SOURCE_NAME   = "dutch_safety"
OUT_DIR       = SOURCES["dutch_safety"]

METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
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


def _collect_report_items(max_pages: int = 50) -> list[dict]:
    """Collect Dutch Safety Board maritime/shipping investigation reports.

    Strategy:
    1. Scrape /en/thema/shipping/ — the shipping investigations thematic page
    2. Paginate /en/home/investigations/ for all-investigations listing
    3. Each unique slug URL visited for PDF download link
    """
    items: list[dict] = []
    seen: set[str] = set()

    def _add_item(href: str, title: str = "", date: str = "") -> None:
        if not href:
            return
        if not href.startswith("http"):
            href = BASE_URL + href
        if href in seen:
            return
        # Skip navigation/category/non-report pages
        skip_pats = ['/thema/', '/home/', '/contact/', '/about', '/news/', '#', 'javascript:', 'mailto:']
        if any(p in href for p in skip_pats):
            return
        # Only accept slug-based deep URLs (at least 4 path segments)
        if href.count("/") < 4:
            return
        seen.add(href)
        items.append({
            "title": title or href.rstrip("/").split("/")[-1].replace("-", " ").title(),
            "detail_url": href,
            "pdf_url": "",
            "date": date,
            "source": SOURCE_NAME,
        })

    # Strategy 1: Shipping thema page
    log.info("Fetching Dutch Safety shipping thema page …")
    try:
        resp = _get(MARINE_INDEX)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("https://onderzoeksraad.nl/en/"):
                _add_item(href, title=a.get_text(strip=True))
            elif href.startswith("/en/"):
                _add_item(BASE_URL + href, title=a.get_text(strip=True))
        log.info("Shipping thema: found %d items", len(items))
    except Exception as exc:
        log.error("Shipping thema page failed: %s", exc)

    # Strategy 2: Paginate investigations index
    log.info("Paginating Dutch Safety investigations …")
    prev_count = len(items)
    for page in range(1, max_pages + 1):
        params = {"_sort": "date:DESC", "_page": str(page)}
        try:
            resp = _get(INVEST_INDEX, params=params)
            soup = BeautifulSoup(resp.text, "html.parser")
            found_on_page = 0

            # All anchor tags
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("https://onderzoeksraad.nl/en/"):
                    before = len(seen)
                    _add_item(href, title=a.get_text(strip=True))
                    found_on_page += len(seen) - before
                elif href.startswith("/en/"):
                    before = len(seen)
                    _add_item(BASE_URL + href, title=a.get_text(strip=True))
                    found_on_page += len(seen) - before

            # Article cards
            for article in soup.select("article, .search-result, .case-item, li.publication, .card"):
                a_tag = article.find("a", href=True)
                if a_tag:
                    href = a_tag["href"]
                    title_tag = article.find(["h2", "h3", "h4"])
                    title = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
                    date_tag = article.find("time") or article.select_one(".date, .publication-date")
                    date = date_tag.get("datetime", date_tag.get_text(strip=True)) if date_tag else ""
                    if href.startswith("http"):
                        _add_item(href, title=title, date=date)
                    elif href.startswith("/"):
                        _add_item(BASE_URL + href, title=title, date=date)

            log.info("Investigations page %d: +%d new (total %d)", page, found_on_page, len(items))
            if found_on_page == 0:
                break
        except Exception as exc:
            log.error("Investigations page %d failed: %s", page, exc)
            break

    log.info("Total Dutch Safety maritime items found: %d", len(items))
    return items


def _resolve_pdf(detail_url: str) -> str:
    """Visit report detail page to find the PDF download link."""
    try:
        resp = _get(detail_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower():
                return urljoin(BASE_URL, href)
    except Exception as exc:
        log.warning("Cannot resolve PDF at %s: %s", detail_url, exc)
    return ""


def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        return False
    if is_downloaded(pdf_url):
        return True

    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", pdf_url.split("/")[-1].split("?")[0])
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    # Year sub-directory
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


def run(max_pages: int = 50) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = _collect_report_items(max_pages=max_pages)

    # Resolve PDFs from detail pages
    needs_resolve = [i for i in items if not i["pdf_url"]]
    log.info("Resolving %d detail pages for PDF links …", len(needs_resolve))
    for item in tqdm(needs_resolve, desc="Resolving PDFs", unit="page"):
        item["pdf_url"] = _resolve_pdf(item["detail_url"])

    ok = fail = skip = 0
    for item in tqdm(items, desc="Downloading Dutch Safety Board reports", unit="pdf"):
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
    ap = argparse.ArgumentParser(description="Dutch Safety Board maritime report scraper")
    ap.add_argument("--max-pages", type=int, default=50)
    args = ap.parse_args()
    run(max_pages=args.max_pages)
