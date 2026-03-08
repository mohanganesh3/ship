#!/usr/bin/env python3
"""nepia_scraper.py - North of England P&I Club publications scraper."""

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
        logging.FileHandler(LOGS_DIR / "nepia_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("nepia")

BASE_URL    = "https://www.nepia.com"
SOURCE_NAME = "nepia"
OUT_DIR     = SOURCES["nepia"]
RATE_LIMIT  = DEFAULT_RATE_LIMIT_SECONDS

INDEX_PAGES = [
    "https://www.nepia.com/media/publications/",
    "https://www.nepia.com/media/publications/loss-prevention-bulletins/",
    "https://www.nepia.com/media/publications/sea-venture/",
    "https://www.nepia.com/media/publications/carefully-to-carry/",
    "https://www.nepia.com/publications/advice-to-members/",
    "https://www.nepia.com/media/publications/members-circular/",
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

def _collect_pdf_links(index_url, visited):
    if index_url in visited:
        return []
    visited.add(index_url)
    log.info("Fetching index: %s", index_url)
    resp = _get(index_url)
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    details = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href)
        parsed = urlparse(full)
        if "nepia.com" not in parsed.netloc:
            continue
        if href.lower().endswith(".pdf"):
            pdfs.append(full)
        elif parsed.path.count("/") >= 3 and full != index_url:
            details.append(full)
    next_a = soup.find("a", rel="next")
    if not next_a:
        next_a = soup.find("a", string=re.compile(r"next", re.I))
    if next_a and next_a.get("href"):
        time.sleep(RATE_LIMIT)
        pdfs.extend(_collect_pdf_links(urljoin(BASE_URL, next_a["href"]), visited))
    for detail in list(dict.fromkeys(details)):
        if detail in visited:
            continue
        visited.add(detail)
        time.sleep(RATE_LIMIT)
        dr = _get(detail)
        if not dr:
            continue
        dsoup = BeautifulSoup(dr.text, "html.parser")
        for a in dsoup.find_all("a", href=True):
            h2 = a["href"].strip()
            if h2.lower().endswith(".pdf"):
                pdfs.append(urljoin(BASE_URL, h2))
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
        ctype = r.headers.get("content-type", "")
        if "html" in ctype and not url.lower().endswith(".pdf"):
            mark_download_failed(url, "html response")
            return "failed"
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
        pdfs = _collect_pdf_links(idx, visited)
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
