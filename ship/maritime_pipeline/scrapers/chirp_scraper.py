#!/usr/bin/env python3
"""
chirp_scraper.py - CHIRP Maritime Safety Digest scraper.

CHIRP (Confidential Human Factors Incident Reporting Programme) publishes
maritime and aviation safety digests. The maritime digest is fully public.

Source: https://www.chirpmaritime.org/
Reports: Deck/bridge/navigation/cargo incidents, "maritime reporter" issues

Each "Maritime Reporter" issue is a PDF with anonymised safety incident reports.
Hundreds of issues available, very rich narrative content ideal for CPT.
"""

import sys, re, time, logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
        logging.FileHandler(LOGS_DIR / "chirp_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("chirp")

BASE_URL    = "https://www.chirpmaritime.org"
SOURCE_NAME = "chirp"
OUT_DIR     = SOURCES.get("chirp", Path(__file__).parent.parent / "data" / "raw_pdfs" / "chirp")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = 2.0

# CHIRP maritime reporter index pages
INDEX_PAGES = [
    "https://www.chirpmaritime.org/maritime-reporter/",
    "https://www.chirpmaritime.org/reports/",
    "https://www.chirpmaritime.org/safety-information/",
    "https://www.chirpmaritime.org/reports/summary-reports/",
    "https://www.chirpmaritime.org/reports/feedback-articles/",
    "https://www.chirpmaritime.org/reports/safety-flashes/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}


def _get(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, verify=False)
            r.raise_for_status()
            return r
        except Exception as exc:
            log.warning("GET %s attempt %d: %s", url, attempt + 1, exc)
            time.sleep(RATE_LIMIT * 2)
    return None


def _collect_from_page(page_url, visited):
    """Collect PDF links from a given page, and recursively follow pagination."""
    if page_url in visited:
        return []
    visited.add(page_url)

    log.info("Fetching: %s", page_url)
    resp = _get(page_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href) if not href.startswith("http") else href
        if href.lower().endswith(".pdf") or "?post_type=attachment" in href.lower():
            pdfs.append(full)
        elif full.startswith(BASE_URL) and re.search(r"/page/\d+", full):
            # Pagination — recurse
            pdfs.extend(_collect_from_page(full, visited))

    return list(dict.fromkeys(pdfs))


def _safe_filename(url):
    name = urlparse(url).path.split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "chirp_doc.pdf"


def _download_pdf(url):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    dest = OUT_DIR / filename
    mark_download_pending(url, SOURCE_NAME)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True, allow_redirects=True, verify=False)
        r.raise_for_status()
        n_bytes = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                n_bytes += len(chunk)
        if n_bytes < 1024:
            dest.unlink(missing_ok=True)
            mark_download_failed(url, "too small")
            return "failed"
        # Verify it looks like a PDF
        with open(dest, "rb") as f:
            header = f.read(4)
        if not header.startswith(b"%PDF"):
            dest.unlink(missing_ok=True)
            mark_download_failed(url, "not a PDF")
            return "failed"
        fhash = sha256_file(dest)
        mark_download_done(url, dest, fhash, n_bytes)
        log.info("OK %s (%.1f KB)", filename, n_bytes / 1024)
        return "downloaded"
    except Exception as exc:
        log.warning("FAIL %s: %s", url, exc)
        mark_download_failed(url, str(exc))
        return "failed"


def run():
    init_db()
    visited = set()
    all_pdfs = []

    for idx in INDEX_PAGES:
        pdfs = _collect_from_page(idx, visited)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        time.sleep(RATE_LIMIT)

    log.info("Total unique PDFs found: %d", len(all_pdfs))
    dl = fa = sk = 0
    for url in all_pdfs:
        s = _download_pdf(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded":  dl += 1
        elif s == "failed":    fa += 1
        else:                  sk += 1

    log.info("Done. Downloaded=%d, Failed=%d, Skipped=%d", dl, fa, sk)


if __name__ == "__main__":
    run()
