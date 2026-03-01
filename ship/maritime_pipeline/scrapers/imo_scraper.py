#!/usr/bin/env python3
"""
imo_scraper.py - IMO (International Maritime Organization) public documents scraper.

Source: https://www.imo.org/
Focus: 
  - IMO publications excerpts and overviews (public pages, not paid publications)
  - Circulars, resolutions summaries accessible via public news/press releases
  - Maritime safety committee (MSC) highlights
  - MEPC highlights
  - STCW documents

Most IMO full documents require purchase, but there are many public-facing
summary pages, press releases, and free-to-access resources.

Usage:
    cd maritime_pipeline
    python scrapers/imo_scraper.py
"""

import sys, re, time, json, logging
import datetime
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
        logging.FileHandler(LOGS_DIR / "imo_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("imo")

BASE_URL    = "https://www.imo.org"
SOURCE_NAME = "imo"
OUT_PDF_DIR = Path(__file__).parent.parent / "data" / "raw_pdfs" / "imo"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "imo_articles.jsonl"
OUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = DEFAULT_RATE_LIMIT_SECONDS

INDEX_PAGES = [
    # News and media - all public
    "https://www.imo.org/en/MediaCentre/Pages/Home.aspx",
    "https://www.imo.org/en/MediaCentre/PressBriefings/Pages/default.aspx",
    "https://www.imo.org/en/MediaCentre/MeetingSummaries/Pages/default.aspx",
    # Safety topics - public
    "https://www.imo.org/en/OurWork/Safety/Pages/default.aspx",
    "https://www.imo.org/en/OurWork/Environment/Pages/default.aspx",
    # Conventions and instruments
    "https://www.imo.org/en/OurWork/Safety/Pages/SOLAS.aspx",
    "https://www.imo.org/en/OurWork/Environment/Pages/MARPOL.aspx",
    "https://www.imo.org/en/OurWork/HumanElement/Pages/NewSTCW-SectionII.aspx",
    # Facilitation and security
    "https://www.imo.org/en/OurWork/Facilitation/Pages/default.aspx",
    "https://www.imo.org/en/OurWork/Security/Pages/maritimesecurity.aspx",
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


def _extract_text(soup):
    """Extract main content from IMO page."""
    for sel in [
        "div.imo-content", "div.content", "div.main-content",
        "article", "div#SuiteBarLeft", "div.ms-rtestate-field",
        "div.imo-text", "main",
    ]:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text.split()) > 100:
                return text

    candidate, max_words = None, 0
    for div in soup.find_all(["div", "article", "section"]):
        text = div.get_text(separator="\n", strip=True)
        w = len(text.split())
        if w > max_words and w > 150:
            max_words, candidate = w, div
    return candidate.get_text(separator="\n", strip=True) if candidate else ""


def _collect_links(index_url, visited):
    """Collect sub-page links and PDFs from IMO index."""
    if index_url in visited:
        return [], []
    visited.add(index_url)

    resp = _get(index_url)
    if not resp:
        return [], []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    articles = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href)
        parsed = urlparse(full)

        if href.lower().endswith(".pdf"):
            pdfs.append(full)
        elif (
            "imo.org" in parsed.netloc
            and full not in visited
            and "/en/" in parsed.path
            and parsed.path.endswith(".aspx")
        ):
            articles.append(full)

    return pdfs, list(dict.fromkeys(articles))


def _safe_filename(url):
    name = urlparse(url).path.split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    return name or "doc.pdf"


def _download_pdf(url):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url)
    dest = OUT_PDF_DIR / filename
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
        log.info("OK PDF %s (%.1f KB)", filename, n_bytes / 1024)
        return "downloaded"
    except Exception as exc:
        log.warning("FAIL %s: %s", url, exc)
        mark_download_failed(url, str(exc))
        return "failed"


def _scrape_article(url):
    if is_downloaded(url):
        return "skipped"

    resp = _get(url)
    if not resp:
        return "failed"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Check for PDFs on the page
    for a in soup.find_all("a", href=True):
        if a["href"].strip().lower().endswith(".pdf"):
            _download_pdf(urljoin(BASE_URL, a["href"].strip()))

    title_tag = soup.find("h1") or soup.find("h2") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]

    body = _extract_text(soup)
    if len(body.split()) < 80:
        mark_download_pending(url, SOURCE_NAME)
        mark_download_done(url, JSONL_FILE, "too_short", 0)
        return "skipped"

    record = {
        "url": url,
        "title": title,
        "text": body,
        "source": SOURCE_NAME,
        "scraped_at": datetime.datetime.utcnow().isoformat(),
    }
    with open(JSONL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    mark_download_pending(url, SOURCE_NAME)
    mark_download_done(url, JSONL_FILE, "article", len(body.encode()))
    log.info("Article: %s (%d words)", title[:60], len(body.split()))
    return "downloaded"


def run():
    init_db()
    visited = set()
    all_pdfs = []
    all_articles = []

    for idx in INDEX_PAGES:
        log.info("Scanning index: %s", idx)
        pdfs, arts = _collect_links(idx, visited)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        for a in arts:
            if a not in all_articles:
                all_articles.append(a)
        time.sleep(RATE_LIMIT)

    log.info("Found %d PDFs, %d article pages", len(all_pdfs), len(all_articles))

    dl = fa = sk = 0
    for url in all_pdfs:
        s = _download_pdf(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded": dl += 1
        elif s == "failed":   fa += 1
        else:                 sk += 1

    for url in all_articles[:300]:
        s = _scrape_article(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded": dl += 1
        elif s == "failed":   fa += 1
        else:                 sk += 1

    log.info("Done. Downloaded=%d, Failed=%d, Skipped=%d", dl, fa, sk)


if __name__ == "__main__":
    run()
