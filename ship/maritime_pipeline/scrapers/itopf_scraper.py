#!/usr/bin/env python3
"""
itopf_scraper.py - ITOPF (International Tanker Owners Pollution Federation) publications.

Source: https://www.itopf.org/   (NOTE: .org not .com)
Publications: Technical Information Papers (TIPs 01-19), data statistics

PDFs are on individual TIP detail pages under href="/fileadmin/...pdf" links.
"""

import sys, re, time, logging, urllib3
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "itopf_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("itopf")

BASE_URL    = "https://www.itopf.org"
SOURCE_NAME = "itopf"
OUT_DIR     = SOURCES.get("itopf", Path(__file__).parent.parent / "data" / "raw_pdfs" / "itopf")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = 2.0

INDEX_PAGES = [
    "https://www.itopf.org/knowledge-resources/documents-guides/technical-information-papers/",
    "https://www.itopf.org/knowledge-resources/documents-guides/compensation/",
    "https://www.itopf.org/knowledge-resources/documents-guides/contingency-response-planning/",
    "https://www.itopf.org/knowledge-resources/documents-guides/disposal/",
    "https://www.itopf.org/knowledge-resources/documents-guides/environmental-effects/",
    "https://www.itopf.org/knowledge-resources/documents-guides/fate-of-oil-spills/",
    "https://www.itopf.org/knowledge-resources/documents-guides/response-techniques/",
    "https://www.itopf.org/knowledge-resources/documents-guides/",
    "https://www.itopf.org/knowledge-resources/data-statistics/",
    "https://www.itopf.org/in-action/case-studies/",
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


def _collect_pdf_links(page_url):
    resp = _get(page_url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            full = urljoin(BASE_URL, href) if not href.startswith("http") else href
            pdfs.append(full)
    return list(dict.fromkeys(pdfs))


def _collect_detail_pages(index_url):
    resp = _get(index_url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    pages = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http"):
            href = urljoin(BASE_URL, href)
        parsed = urlparse(href)
        if (parsed.netloc == "www.itopf.org"
                and "/knowledge-resources/documents-guides/" in parsed.path
                and "?" not in href
                and "#" not in href
                and href != index_url):
            pages.append(href)
    return list(dict.fromkeys(pages))


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
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True, verify=False)
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
    all_pdfs = []
    visited_pages = set()

    for idx in INDEX_PAGES:
        log.info("Index: %s", idx)
        direct_pdfs = _collect_pdf_links(idx)
        for p in direct_pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
                log.info("  Direct PDF: %s", p)

        detail_pages = _collect_detail_pages(idx)
        log.info("  Found %d detail pages", len(detail_pages))
        for dp in detail_pages:
            if dp in visited_pages:
                continue
            visited_pages.add(dp)
            time.sleep(RATE_LIMIT)
            pdfs = _collect_pdf_links(dp)
            for p in pdfs:
                if p not in all_pdfs:
                    all_pdfs.append(p)
                    log.info("  PDF at %s", p)
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
