"""
bsu_scraper.py — German Federal Bureau of Maritime Casualty Investigation (BSU) report downloader.

Source  : https://www.bsu-bund.de/EN/Publications/Unfallberichte/
Licence : German Federal Government Open Data
Reports available in English. ~200+ professional marine investigation reports.

Usage:
    cd maritime_pipeline
    python scrapers/bsu_scraper.py
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
    DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR, RAW_PDFS_DIR,
)
from db import (
    init_db, is_downloaded, mark_download_pending,
    mark_download_done, mark_download_failed, sha256_file,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bsu_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bsu")

BASE_URL     = "https://www.bsu-bund.de"
SOURCE_NAME  = "bsu"
OUT_DIR      = RAW_PDFS_DIR / SOURCE_NAME
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT   = DEFAULT_RATE_LIMIT_SECONDS

# BSU publishes a year-based table URL pattern
YEAR_TABLE_PATTERN = (
    "https://www.bsu-bund.de/EN/Publications/Unfallberichte/"
    "_functions/unfallberichte_table_{year}.html"
)
START_YEAR = 2000
END_YEAR   = 2026

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
    "Accept-Language": "en-GB,en;q=0.9,de;q=0.5",
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


def _collect_from_year_table(year: int) -> list[dict]:
    """Fetch the year table page and extract PDF links."""
    url = YEAR_TABLE_PATTERN.format(year=year)
    items: list[dict] = []
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find PDF links — BSU links are typically .pdf or /EN/.../report.pdf
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue
            pdf_url = urljoin(BASE_URL, href)
            title = a.get_text(strip=True) or f"BSU_{year}_report"
            # Try to get row context
            row = a.find_parent("tr")
            description = ""
            if row:
                cells = row.find_all("td")
                description = " | ".join(c.get_text(strip=True) for c in cells if c.get_text(strip=True))

            items.append({
                "title": title,
                "description": description,
                "pdf_url": pdf_url,
                "year": str(year),
                "date": "",
                "source": SOURCE_NAME,
            })
        log.info("Year %d: %d PDFs found", year, len(items))
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            log.debug("Year %d: 404 (no table)", year)
        else:
            log.warning("Year %d HTTP error: %s", year, exc)
    except Exception as exc:
        log.warning("Year %d: %s", year, exc)

    return items


def _collect_from_main_index() -> list[dict]:
    """Also scrape the main index page for links missed by year tables."""
    items: list[dict] = []
    seen: set[str] = set()
    index_url = "https://www.bsu-bund.de/EN/Publications/Unfallberichte/unfallberichte_node.html"
    try:
        resp = _get(index_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue
            pdf_url = urljoin(BASE_URL, href)
            if pdf_url not in seen:
                seen.add(pdf_url)
                items.append({
                    "title": a.get_text(strip=True),
                    "description": "",
                    "pdf_url": pdf_url,
                    "year": "",
                    "date": "",
                    "source": SOURCE_NAME,
                })
        log.info("Main index: %d additional PDFs", len(items))
    except Exception as exc:
        log.warning("Main index failed: %s", exc)
    return items


def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        return False
    if is_downloaded(pdf_url):
        return True

    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", pdf_url.split("/")[-1].split("?")[0])
    if not filename.endswith(".pdf"):
        filename += ".pdf"

    sub = OUT_DIR / (item.get("year") or "misc")
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


def run(start_year: int = START_YEAR, end_year: int = END_YEAR) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    seen_urls: set[str] = set()

    # Collect from year tables
    for year in range(start_year, end_year + 1):
        year_items = _collect_from_year_table(year)
        for item in year_items:
            if item["pdf_url"] not in seen_urls:
                seen_urls.add(item["pdf_url"])
                all_items.append(item)

    # Also try main index
    for item in _collect_from_main_index():
        if item["pdf_url"] not in seen_urls:
            seen_urls.add(item["pdf_url"])
            all_items.append(item)

    log.info("Total BSU reports to download: %d", len(all_items))

    ok = fail = skip = 0
    for item in tqdm(all_items, desc="Downloading BSU reports", unit="pdf"):
        if is_downloaded(item["pdf_url"]):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="BSU German maritime investigation scraper")
    ap.add_argument("--start-year", type=int, default=START_YEAR)
    ap.add_argument("--end-year", type=int, default=END_YEAR)
    args = ap.parse_args()
    run(start_year=args.start_year, end_year=args.end_year)
