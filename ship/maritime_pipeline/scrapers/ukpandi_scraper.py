#!/usr/bin/env python3
"""
ukpandi_scraper.py — UK P&I Club loss prevention publications scraper.

Source  : https://www.ukpandi.com/knowledge-development/
Licence : Free to access, for educational/research use

Publications include:
  - Loss Prevention Bulletins
  - Circulars
  - Guides
  - Safety Cards

Usage:
    cd maritime_pipeline
    python scrapers/ukpandi_scraper.py
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
        logging.FileHandler(LOGS_DIR / "ukpandi_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ukpandi")

BASE_URL      = "https://www.ukpandi.com"
SOURCE_NAME   = "ukpandi"
OUT_DIR       = SOURCES["ukpandi"]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

# Publication index pages to scrape
INDEX_PAGES = [
    "https://www.ukpandi.com/knowledge-development/loss-prevention/loss-prevention-publications/",
    "https://www.ukpandi.com/knowledge-development/loss-prevention/loss-prevention-bulletins/",
    "https://www.ukpandi.com/knowledge-development/loss-prevention/loss-prevention-circulars/",
    "https://www.ukpandi.com/news-and-resources/circulars/",
    "https://www.ukpandi.com/knowledge-development/loss-prevention/guides-and-booklets/",
]

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
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


def _collect_publication_urls() -> list[dict]:
    """Scrape UK P&I Club publication index pages to find PDF downloads."""
    items: list[dict] = []
    seen: set[str] = set()

    for index_url in INDEX_PAGES:
        log.info("Fetching index: %s", index_url)
        page = 1
        while True:
            url = index_url if page == 1 else f"{index_url}?page={page}"
            try:
                resp = _get(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                found_on_page = 0

                # Find all publication entries
                # Try common patterns: article cards, list items, link containers
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    # Look for PDF links directly
                    if href.endswith(".pdf") or "/wp-content/" in href:
                        abs_url = urljoin(BASE_URL, href)
                        if abs_url not in seen:
                            seen.add(abs_url)
                            title = a.get_text(strip=True) or href.split("/")[-1]
                            items.append({
                                "title": title,
                                "pdf_url": abs_url,
                                "detail_url": "",
                                "date": "",
                                "source": SOURCE_NAME,
                            })
                            found_on_page += 1
                    # Look for publication detail page links
                    elif "/knowledge-development/" in href or "/publications/" in href or "/circulars/" in href:
                        abs_url = urljoin(BASE_URL, href)
                        if abs_url not in seen and abs_url != index_url:
                            seen.add(abs_url)
                            items.append({
                                "title": a.get_text(strip=True),
                                "pdf_url": "",
                                "detail_url": abs_url,
                                "date": "",
                                "source": SOURCE_NAME,
                            })
                            found_on_page += 1

                log.info("  Page %d: +%d items (total %d)", page, found_on_page, len(items))

                # Check for next page
                next_btn = soup.select_one("a[rel='next'], .pagination-next, .next-page, li.next a")
                if not next_btn or found_on_page == 0:
                    break
                page += 1
            except Exception as exc:
                log.error("Index page %d failed: %s", page, exc)
                break

    log.info("Total UK P&I Club publications found: %d", len(items))
    return items


def _resolve_pdf_from_detail(detail_url: str) -> str:
    """Visit publication detail page to find PDF link."""
    try:
        resp = _get(detail_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower() or "/wp-content/" in href:
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

    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_",
                      pdf_url.split("/")[-1].split("?")[0] or "ukpandi.pdf")
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    year = re.search(r"(\d{4})", item.get("date", "") + pdf_url)
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


def run() -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = _collect_publication_urls()

    # Resolve PDF URLs from detail pages
    needs_resolve = [i for i in items if not i["pdf_url"] and i["detail_url"]]
    log.info("Resolving %d detail pages for PDF links …", len(needs_resolve))
    for item in tqdm(needs_resolve, desc="Resolving PDFs", unit="page"):
        item["pdf_url"] = _resolve_pdf_from_detail(item["detail_url"])

    ok = fail = skip = 0
    for item in tqdm(items, desc="Downloading UK P&I Club publications", unit="pdf"):
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
    ap = argparse.ArgumentParser(description="UK P&I Club publications scraper")
    ap.parse_args()
    run()
