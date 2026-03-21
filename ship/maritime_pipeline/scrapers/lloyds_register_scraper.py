#!/usr/bin/env python3
"""
lloyds_register_scraper.py - Lloyd's Register maritime publications scraper.

Lloyd's Register publishes free maritime safety guidance, class notes,
rules, and technical publications. Rich content for maritime AI training.

Sources:
- https://www.lr.org/en/knowledge/publications/
- https://www.lr.org/en/news/
- https://www.lr.org/en/sustainability/
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
        logging.FileHandler(LOGS_DIR / "lloyds_register_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("lr")

BASE_URL    = "https://www.lr.org"
SOURCE_NAME = "lloyds_register"
OUT_DIR     = SOURCES.get("lloyds_register", Path(__file__).parent.parent / "data" / "raw_pdfs" / "lloyds_register")
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "lloyds_register_articles.jsonl"
RATE_LIMIT  = 2.5
MAX_ARTICLES = 600
MAX_PDFS    = 400

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# High-value pages for maritime content
INDEX_PAGES = [
    # Knowledge hub with filter categories
    "https://www.lr.org/en/knowledge/",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=12960&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=9687&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=12965&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=12962&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=12961&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=1&sortBy=1&primaryFilter=12966&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=2&sortBy=1&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=3&sortBy=1&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=4&sortBy=1&setBack=false",
    "https://www.lr.org/en/knowledge/?currentPage=5&sortBy=1&setBack=false",
    # Press room and news
    "https://www.lr.org/en/knowledge/press-room/",
    # Expertise pages with maritime content
    "https://www.lr.org/en/expertise/segments/bulk-carrier/",
    "https://www.lr.org/en/expertise/segments/containership/",
    "https://www.lr.org/en/expertise/segments/tanker/",
    "https://www.lr.org/en/expertise/segments/gas/",
    "https://www.lr.org/en/expertise/segments/passenger-ships/",
    # Research reports
    "https://www.lr.org/en/knowledge/research/fuel-for-thought/",
    "https://www.lr.org/en/knowledge/marine-structural-software/",
]

import json


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


def _safe_filename(url):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name:
        name = re.sub(r"[^\w]", "_", url[-40:])
    return name or "lr_doc"


def _collect_links(page_url, visited):
    """Collect PDF and article links from a page."""
    if page_url in visited:
        return [], []
    visited.add(page_url)

    log.info("Fetching index: %s", page_url)
    resp = _get(page_url)
    if not resp:
        return [], []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    articles = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(BASE_URL, href) if not href.startswith("http") else href
        if not full.startswith("https://www.lr.org"):
            continue
        if href.lower().endswith(".pdf") or ".pdf?" in href.lower():
            if full not in pdfs:
                pdfs.append(full)
        elif re.search(r"/(knowledge|press-room|research|expertise|insight|blog|news|segment)/", full):
            if full not in articles:
                articles.append(full)

    return pdfs, articles


def _download_pdf(url):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    dest = OUT_DIR / filename
    mark_download_pending(url, SOURCE_NAME)
    try:
        r = requests.get(url, headers=HEADERS, timeout=90, stream=True, allow_redirects=True, verify=False)
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
        with open(dest, "rb") as f:
            header = f.read(4)
        if not header.startswith(b"%PDF"):
            dest.unlink(missing_ok=True)
            mark_download_failed(url, "not a PDF")
            return "failed"
        fhash = sha256_file(dest)
        mark_download_done(url, dest, fhash, n_bytes)
        log.info("OK PDF %s (%.1f KB)", filename, n_bytes / 1024)
        return "downloaded"
    except Exception as exc:
        log.warning("FAIL PDF %s: %s", url, exc)
        mark_download_failed(url, str(exc))
        return "failed"


def _scrape_article(url):
    """Extract text content from an article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove nav/footer/scripts
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    # Try to find main content
    title = ""
    title_tag = soup.find("h1") or soup.find("h2")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Get main content area
    content_area = (
        soup.find("main")
        or soup.find("article")
        or soup.find(class_=re.compile(r"content|article|body|main", re.I))
        or soup.find("div", {"id": re.compile(r"content|main|article", re.I)})
    )
    if content_area:
        text = content_area.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
    text = "\n".join(lines)

    word_count = len(text.split())
    if word_count < 100:
        return None

    return {"url": url, "title": title, "text": text, "word_count": word_count, "source": "lloyds_register"}


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Collect all links from index pages
    visited = set()
    all_pdfs = []
    all_articles = []

    for idx in INDEX_PAGES:
        pdfs, articles = _collect_links(idx, visited)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        for a in articles:
            if a not in all_articles:
                all_articles.append(a)
        time.sleep(RATE_LIMIT)

    log.info("Found %d PDFs, %d article links", len(all_pdfs), len(all_articles))

    # Download PDFs
    dl = fa = sk = 0
    for url in all_pdfs[:MAX_PDFS]:
        s = _download_pdf(url)
        time.sleep(RATE_LIMIT)
        if s == "downloaded":
            dl += 1
        elif s == "failed":
            fa += 1
        else:
            sk += 1

    log.info("PDFs: Downloaded=%d Failed=%d Skipped=%d", dl, fa, sk)

    # Scrape articles
    a_saved = a_failed = 0
    seen_urls = set()

    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_articles[:MAX_ARTICLES]:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            article = _scrape_article(url)
            if article:
                jf.write(json.dumps(article, ensure_ascii=False) + "\n")
                jf.flush()
                log.info("Article: %s (%d words)", article["title"][:60], article["word_count"])
                a_saved += 1
            else:
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Articles saved=%d failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
