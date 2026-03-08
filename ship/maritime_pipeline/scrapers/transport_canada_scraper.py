#!/usr/bin/env python3
"""
transport_canada_scraper.py - Transport Canada Marine Safety Notices.

Source: https://tc.canada.ca/en/marine-transportation/marine-safety
Content: Notices to Shipping, Ship Safety Bulletins, Marine Safety Notices

Very detailed technical bulletins and safety notices similar to MCA/MAIB.
Hundreds of PDFs and HTML notices.
"""

import sys, re, time, logging
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

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
        logging.FileHandler(LOGS_DIR / "transport_canada_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("transport_canada")

BASE_URL    = "https://tc.canada.ca"
SOURCE_NAME = "transport_canada"
OUT_DIR     = SOURCES.get("transport_canada", Path(__file__).parent.parent / "data" / "raw_pdfs" / "transport_canada")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = 2.5

# Ship safety bulletins and notices index pages
INDEX_PAGES = [
    "https://tc.canada.ca/en/marine-transportation/marine-safety/ship-safety-bulletins",
    "https://tc.canada.ca/en/marine-transportation/marine-safety/notice-shipping",
    "https://tc.canada.ca/en/marine-transportation/marine-safety",
    "https://tc.canada.ca/en/marine-transportation/marine-safety/marine-safety-notices",
    "https://tc.canada.ca/en/marine-transportation/marine-safety/programs-policies/vessel-construction-registration/vessel-design",
    "https://tc.canada.ca/en/marine-transportation/marine-safety/programs-policies/vessel-safety-equipment",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-CA,en;q=0.9",
}


def _get(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as exc:
            log.warning("GET %s attempt %d: %s", url, attempt + 1, exc)
            time.sleep(RATE_LIMIT * 2)
    return None


def _collect_pdfs_from_page(page_url, visited):
    if page_url in visited:
        return []
    visited.add(page_url)

    log.info("Fetching: %s", page_url)
    resp = _get(page_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    detail_pages = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href) if not href.startswith("http") else href
        parsed = urlparse(full)

        if href.lower().endswith(".pdf"):
            pdfs.append(full)
        elif "tc.canada.ca" in parsed.netloc and full not in visited:
            # Look for ship safety bulletin detail pages
            if any(kw in full.lower() for kw in ["bulletin", "notice", "safety", "marine"]):
                detail_pages.append(full)

    # Visit likely detail pages for embedded PDFs
    for dp in list(dict.fromkeys(detail_pages))[:200]:
        if dp in visited:
            continue
        visited.add(dp)
        time.sleep(RATE_LIMIT * 0.5)
        dr = _get(dp)
        if not dr:
            continue
        dsoup = BeautifulSoup(dr.text, "html.parser")
        for a in dsoup.find_all("a", href=True):
            href2 = a["href"].strip()
            if href2.lower().endswith(".pdf"):
                pdfs.append(urljoin(BASE_URL, href2))

    return list(dict.fromkeys(pdfs))


def _safe_filename(url):
    name = urlparse(url).path.split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "doc.pdf"


def _download_pdf(url):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url)
    dest = OUT_DIR / filename
    mark_download_pending(url, SOURCE_NAME)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
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
        pdfs = _collect_pdfs_from_page(idx, visited)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        time.sleep(RATE_LIMIT)

    log.info("Total unique PDFs: %d", len(all_pdfs))
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
