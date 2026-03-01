"""
maib_scraper.py — UK Marine Accident Investigation Branch report downloader.

Source  : https://www.gov.uk/maib-reports
Licence : Open Government Licence v3.0 (free for AI training)
Strategy: Paginate the HTML listing → collect PDF links → download each PDF.
          SQLite tracks state for full resume support.

Usage:
    cd maritime_pipeline
    python scrapers/maib_scraper.py [--max-pages N] [--out-dir PATH]
"""

import sys
import os
import re
import json
import time
import logging
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# ── path bootstrap (allow running from any cwd) ───────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import (
    init_db, is_downloaded, mark_download_pending,
    mark_download_done, mark_download_failed, sha256_file,
)

# ── logging ───────────────────────────────────────────────────────────────────
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "maib_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("maib")

# ── constants ─────────────────────────────────────────────────────────────────
BASE_URL      = "https://www.gov.uk"
LISTING_URL   = "https://www.gov.uk/maib-reports"
SOURCE_NAME   = "maib"
OUT_DIR       = SOURCES[SOURCE_NAME]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

# ── HTTP session ──────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
})


def _get(url: str, stream: bool = False) -> requests.Response:
    """GET with exponential backoff."""
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _scrape_listing_page(page_num: int) -> tuple[list[dict], bool]:
    """
    Returns (items, has_next_page).
    Each item: {title, url, date, ship_type, report_type, pdf_url}
    """
    url = f"{LISTING_URL}?page={page_num}" if page_num > 1 else LISTING_URL
    log.info("Fetching listing page %d: %s", page_num, url)
    resp = _get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    items: list[dict] = []
    # GOV.UK finder results live in <li class="gem-c-document-list__item">
    for li in soup.select("li.gem-c-document-list__item, li.document-row"):
        a_tag = li.find("a")
        if not a_tag:
            continue
        href = a_tag.get("href", "")
        title = a_tag.get_text(strip=True)
        detail_url = urljoin(BASE_URL, href)

        # Metadata fields from the listing (best-effort)
        meta_items = li.select(".gem-c-document-list__item-metadata span, .metadata span")
        date_str = ""
        ship_type = ""
        report_type = ""
        for m in meta_items:
            text = m.get_text(strip=True)
            if re.match(r"\d{1,2}\s+\w+\s+\d{4}", text):
                date_str = text
            elif "ship" in text.lower() or "vessel" in text.lower():
                ship_type = text
            else:
                report_type = text

        items.append({
            "title": title,
            "detail_url": detail_url,
            "date": date_str,
            "ship_type": ship_type,
            "report_type": report_type,
            "pdf_url": "",       # filled in later
        })

    # Check for a "next page" link
    next_link = soup.select_one('link[rel="next"], a[rel="next"], .gem-c-pagination__item--next a')
    has_next = next_link is not None and bool(items)

    return items, has_next


def _find_pdf_url(detail_url: str) -> str:
    """Visit the report detail page and extract the first PDF download link."""
    try:
        resp = _get(detail_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for a direct PDF attachment link
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf"):
                return urljoin(BASE_URL, href)
        # GOV.UK sometimes uses /media/ paths
        for a in soup.select("a[href*='/media/'], a[href*='assets.publishing']"):
            href = a["href"]
            if ".pdf" in href.lower():
                return href
    except Exception as exc:
        log.warning("Could not fetch detail page %s: %s", detail_url, exc)
    return ""


def _download_pdf(item: dict) -> bool:
    """Download a single PDF. Returns True on success."""
    pdf_url = item["pdf_url"]
    if not pdf_url:
        log.warning("No PDF URL for: %s", item["title"])
        return False

    if is_downloaded(pdf_url):
        log.debug("Already downloaded: %s", pdf_url)
        return True

    # Derive local filename
    filename = pdf_url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    # Sanitise
    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", filename)
    out_path = OUT_DIR / filename

    mark_download_pending(pdf_url, SOURCE_NAME)

    try:
        resp = _get(pdf_url, stream=True)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(65536):
                fh.write(chunk)

        file_hash = sha256_file(out_path)
        n_bytes = out_path.stat().st_size
        mark_download_done(pdf_url, out_path, file_hash, n_bytes)

        # Write metadata
        with open(METADATA_FILE, "a", encoding="utf-8") as mf:
            record = {**item, "local_path": str(out_path),
                      "downloaded_at": datetime.utcnow().isoformat()}
            mf.write(json.dumps(record) + "\n")

        log.info("Downloaded %s → %s (%.1f KB)", filename, out_path.name, n_bytes / 1024)
        return True

    except Exception as exc:
        log.error("Failed to download %s: %s", pdf_url, exc)
        mark_download_failed(pdf_url, str(exc))
        return False


def run(max_pages: int = 999) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Phase 1: collect all items across all listing pages ───────────────────
    all_items: list[dict] = []
    page = 1
    while page <= max_pages:
        try:
            items, has_next = _scrape_listing_page(page)
        except Exception as exc:
            log.error("Failed to fetch listing page %d: %s", page, exc)
            break
        all_items.extend(items)
        log.info("Page %d → %d items (total so far: %d)", page, len(items), len(all_items))
        if not has_next:
            break
        page += 1

    log.info("Total reports found: %d", len(all_items))

    # ── Phase 2: resolve PDF URLs ─────────────────────────────────────────────
    log.info("Resolving PDF links from detail pages …")
    for item in tqdm(all_items, desc="Resolving PDFs", unit="report"):
        if not item["pdf_url"]:
            item["pdf_url"] = _find_pdf_url(item["detail_url"])

    # ── Phase 3: download PDFs ────────────────────────────────────────────────
    ok = fail = skip = 0
    for item in tqdm(all_items, desc="Downloading PDFs", unit="pdf"):
        pdf_url = item.get("pdf_url", "")
        if not pdf_url:
            skip += 1
            continue
        if is_downloaded(pdf_url):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MAIB report scraper")
    ap.add_argument("--max-pages", type=int, default=999,
                    help="Maximum listing pages to fetch (default: all)")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Override output directory")
    args = ap.parse_args()
    if args.out_dir:
        OUT_DIR = args.out_dir
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_FILE = OUT_DIR / "metadata.jsonl"
    run(max_pages=args.max_pages)
