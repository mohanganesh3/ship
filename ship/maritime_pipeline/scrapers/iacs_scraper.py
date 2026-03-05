#!/usr/bin/env python3
"""
iacs_scraper.py - IACS (International Association of Classification Societies) publications.

Source: https://iacs.org.uk/
Publications: Unified Requirements, Recommendations, Procedural Requirements
These are publicly accessible technical standards for ship classification.

Usage:
    cd maritime_pipeline
    python scrapers/iacs_scraper.py
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
        logging.FileHandler(LOGS_DIR / "iacs_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("iacs")

BASE_URL    = "https://iacs.org.uk"
SOURCE_NAME = "iacs"
OUT_DIR     = Path(__file__).parent.parent / "data" / "raw_pdfs" / "iacs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = DEFAULT_RATE_LIMIT_SECONDS

# IACS publication index pages
INDEX_PAGES = [
    "https://iacs.org.uk/what-we-do/requirements/",
    "https://iacs.org.uk/what-we-do/recommendations/",
    "https://iacs.org.uk/what-we-do/resolutions/",
    "https://iacs.org.uk/publications/",
    "https://iacs.org.uk/what-we-do/publications/",
    "https://iacs.org.uk/what-we-do/procedural-requirements/",
]


def _get(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as exc:
            log.warning("GET %s attempt %d: %s", url, attempt + 1, exc)
            time.sleep(RATE_LIMIT)
    return None


def _collect_pdfs(index_url, visited, depth=0):
    if index_url in visited or depth > 3:
        return []
    visited.add(index_url)

    log.info("Fetching: %s", index_url)
    resp = _get(index_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    sub_pages = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href)
        parsed = urlparse(full)

        if href.lower().endswith(".pdf"):
            pdfs.append(full)
        elif "iacs.org.uk" in parsed.netloc and full != index_url and full not in visited:
            sub_pages.append(full)

    # Visit sub-pages for PDFs
    for sub in list(dict.fromkeys(sub_pages))[:50]:
        time.sleep(RATE_LIMIT)
        pdfs.extend(_collect_pdfs(sub, visited, depth + 1))

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
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=60, stream=True)
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
        pdfs = _collect_pdfs(idx, visited)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        time.sleep(RATE_LIMIT)

    log.info("Total unique PDFs: %d", len(all_pdfs))
    dl = fa = sk = 0
    for url in all_pdfs:
        s = _download_pdf(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded": dl += 1
        elif s == "failed":   fa += 1
        else:                 sk += 1

    log.info("Done. Downloaded=%d, Failed=%d, Skipped=%d", dl, fa, sk)


if __name__ == "__main__":
    run()
