#!/usr/bin/env python3
"""emsa_scraper.py - European Maritime Safety Agency publications scraper.

EMSA PDF download URL pattern:
  /path/to/section/download/{file_id}/{item_id}/23.html
These links serve raw PDFs (content-type: application/pdf).
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
        logging.FileHandler(LOGS_DIR / "emsa_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("emsa")

BASE_URL    = "https://www.emsa.europa.eu"
SOURCE_NAME = "emsa"
OUT_DIR     = SOURCES["emsa"]
RATE_LIMIT  = DEFAULT_RATE_LIMIT_SECONDS

# Confirmed working index pages (serve EMSA /download/ links)
INDEX_PAGES = [
    "/accident-investigation-publications/annual-overview.html",
    "/accident-investigation-publications/emcip-documents.html",
    "/accident-investigation-publications/safety-analysis.html",
    "/accident-investigation-publications/infographics-accident-investigation.html",
    "/publications/highlights.html",
    "/publications/corporate-publications.html",
    "/publications/inventories.html",
]

DOWNLOAD_RE = re.compile(r"/download/\d+/\d+/\d+\.html$")


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


def _collect_download_links(page_path, visited):
    """Collect EMSA /download/ links from a page (one level deep)."""
    url = BASE_URL + page_path
    if url in visited:
        return []
    visited.add(url)

    log.info("Fetching: %s", url)
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    downloads = []
    sub_items = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE_URL, href)
        if DOWNLOAD_RE.search(href):
            downloads.append(full)
        elif (
            "emsa.europa.eu" in full
            and "/item/" in href
            and full not in visited
        ):
            sub_items.append(full)

    # Visit item pages for more download links
    for item_url in sub_items[:50]:
        if item_url in visited:
            continue
        visited.add(item_url)
        time.sleep(RATE_LIMIT)
        dr = _get(item_url)
        if not dr:
            continue
        dsoup = BeautifulSoup(dr.text, "html.parser")
        for a in dsoup.find_all("a", href=True):
            href2 = a["href"]
            if DOWNLOAD_RE.search(href2):
                downloads.append(urljoin(BASE_URL, href2))

    return list(dict.fromkeys(downloads))


def _safe_filename(url):
    # Extract a meaningful filename from EMSA download URL
    # Pattern: /download/{file_id}/{item_id}/23.html
    m = re.search(r"/download/(\d+)/(\d+)/", url)
    if m:
        return f"emsa_{m.group(2)}_{m.group(1)}.pdf"
    name = urlparse(url).path.split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "emsa_doc.pdf"


def _download_pdf(url):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url)
    dest = Path(OUT_DIR) / filename
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
    all_links = []

    for page_path in INDEX_PAGES:
        links = _collect_download_links(page_path, visited)
        log.info("%s -> %d download links", page_path, len(links))
        for l in links:
            if l not in all_links:
                all_links.append(l)
        time.sleep(RATE_LIMIT)

    log.info("Total unique download links: %d", len(all_links))
    dl = fa = sk = 0
    for url in all_links:
        s = _download_pdf(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded": dl += 1
        elif s == "failed":   fa += 1
        else:                 sk += 1

    log.info("Done. Downloaded=%d, Failed=%d, Skipped=%d", dl, fa, sk)


if __name__ == "__main__":
    run()
