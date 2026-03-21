#!/usr/bin/env python3
"""steamship_scraper.py - Steamship Mutual P&I Club publications scraper.

PDFs found at: /club-circulars and /loss-prevention/* subpages
PDF URL pattern: /sites/default/files/medialibrary/files/*.pdf
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
        logging.FileHandler(LOGS_DIR / "steamship_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("steamship")

BASE_URL    = "https://www.steamshipmutual.com"
SOURCE_NAME = "steamship"
OUT_DIR     = SOURCES["steamship"]
RATE_LIMIT  = DEFAULT_RATE_LIMIT_SECONDS

# Confirmed pages with PDFs (92 on club-circulars, ~25 on loss-prevention subs)
INDEX_PAGES = [
    "/club-circulars",
    "/loss-prevention/ship-technical-and-safety-management",
    "/loss-prevention/peme",
    "/loss-prevention/seafarers_mental_well-being_0820",
    "/loss-prevention/piracy",
    "/loss-prevention/riskalert",
    "/safety-bulletins",
    "/loss-prevention",
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


def _collect_pdfs(page_path, visited):
    """Collect PDF links from a Steamship page."""
    url = BASE_URL + page_path
    if url in visited:
        return []
    visited.add(url)

    log.info("Fetching: %s", url)
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(BASE_URL, href)
        if href.lower().endswith(".pdf"):
            pdfs.append(full)

    # Check for pagination
    next_a = soup.find("a", rel="next")
    if not next_a:
        # Steamship uses query params for pagination
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if text in ("next", "next page", ">"):
                next_href = a["href"]
                next_url = urljoin(BASE_URL, next_href)
                if next_url not in visited:
                    time.sleep(RATE_LIMIT)
                    visited.add(next_url)
                    r2 = _get(next_url)
                    if r2:
                        s2 = BeautifulSoup(r2.text, "html.parser")
                        for a2 in s2.find_all("a", href=True):
                            if a2["href"].lower().endswith(".pdf"):
                                pdfs.append(urljoin(BASE_URL, a2["href"]))
                break

    return list(dict.fromkeys(pdfs))


def _safe_filename(url):
    name = urlparse(url).path.split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "doc.pdf"


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
    all_pdfs = []

    for page_path in INDEX_PAGES:
        pdfs = _collect_pdfs(page_path, visited)
        log.info("%s -> %d PDFs", page_path, len(pdfs))
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
