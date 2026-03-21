#!/usr/bin/env python3
"""
paris_mou_scraper.py - Paris MOU & Tokyo MOU port state control scraper.

Paris MOU: https://www.parismou.org/
Tokyo MOU: https://www.tokyo-mou.org/

These publish annual/quarterly reports, deficiency statistics, detained-ship
lists, and inspection reports — highly relevant maritime safety and compliance data.

Annual reports are PDFs with comprehensive data on ship inspections,
detentions, deficiencies per flag state, company, ship type, etc.
"""

import sys, re, time, logging, json
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
        logging.FileHandler(LOGS_DIR / "paris_mou_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("parismou")

SOURCE_NAME = "paris_mou"
OUT_DIR     = SOURCES.get("paris_mou", Path(__file__).parent.parent / "data" / "raw_pdfs" / "paris_mou")
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "paris_mou_articles.jsonl"
RATE_LIMIT  = 2.0
MAX_PDFS    = 500

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Paris MOU and Tokyo MOU index pages
PARIS_PAGES = [
    "https://parismou.org/publications",
    "https://parismou.org/publications?field_news_category_target_id=2",
    "https://parismou.org/publications?field_news_category_target_id=4",
    "https://parismou.org/publications?field_news_category_target_id=5",
    "https://parismou.org/publications?field_news_category_target_id=6",
    "https://parismou.org/publications?field_news_category_target_id=7",
    "https://parismou.org/publications?field_news_category_target_id=8",
    "https://parismou.org/publications?field_news_category_target_id=9",
    "https://parismou.org/publications?field_news_category_target_id=10",
    "https://parismou.org/PMoU-Procedures",
    "https://parismou.org/about-us/history",
]

TOKYO_PAGES = [
    "https://www.tokyo-mou.org/publications/annual_report.php",
    "https://www.tokyo-mou.org/publications/",
    "https://www.tokyo-mou.org/organization/press_release.php",
    "https://www.tokyo-mou.org/publications/performance_list.php",
    "https://www.tokyo-mou.org/doc/cic/",
]

ALL_INDEX_PAGES = PARIS_PAGES + TOKYO_PAGES


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


def _safe_filename(url, source_prefix=""):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name or name == "_":
        name = re.sub(r"[^\w]", "_", url[-40:])
    if source_prefix and not name.startswith(source_prefix):
        name = f"{source_prefix}_{name}"
    return name or "mou_doc.pdf"


def _is_pdf_url(url):
    low = url.lower()
    return low.endswith(".pdf") or ".pdf?" in low or "/pdf/" in low


def _collect_pdfs_from_page(url, visited, base_filter=None):
    """Collect PDF URLs from a page, optionally filtered by domain."""
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
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        full = urljoin(url, href) if not href.startswith("http") else href
        if _is_pdf_url(full):
            if base_filter is None or any(d in full for d in base_filter):
                if full not in pdfs:
                    pdfs.append(full)

    return pdfs


def _download_pdf(url, prefix=""):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url, prefix)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    dest = OUT_DIR / filename
    mark_download_pending(url, SOURCE_NAME)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120, stream=True,
                         allow_redirects=True, verify=False)
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
        log.info("OK %s (%.1f KB)", filename, n_bytes / 1024)
        return "downloaded"
    except Exception as exc:
        log.warning("FAIL %s: %s", url, exc)
        mark_download_failed(url, str(exc))
        return "failed"


def _scrape_article(url):
    """Extract text from a news/publication page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    content_area = (
        soup.find("main")
        or soup.find("article")
        or soup.find(class_=re.compile(r"content|article|body|main", re.I))
        or soup.body
    )
    text = content_area.get_text(separator="\n", strip=True) if content_area else ""
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
    text = "\n".join(lines)

    if len(text.split()) < 80:
        return None

    return {"url": url, "title": title, "text": text,
            "word_count": len(text.split()), "source": SOURCE_NAME}


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    visited = set()
    all_pdfs = []
    all_articles = []

    for page_url in ALL_INDEX_PAGES:
        if "parismou" in page_url:
            base = "https://parismou.org"
            domain_filter = ["parismou.org"]
        else:
            base = "https://www.tokyo-mou.org"
            domain_filter = ["tokyo-mou.org"]

        log.info("Fetching: %s", page_url)
        resp = _get(page_url)
        if not resp:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            full = urljoin(base, href) if not href.startswith("http") else href
            if not any(d in full for d in domain_filter):
                continue
            low = full.lower()
            if low.endswith(".pdf") or ".pdf?" in low:
                if full not in all_pdfs:
                    all_pdfs.append(full)
            elif re.search(r"/\d{4}/\d{2}/|/publications/|/news/|/PMoU-Proc", full):
                if full not in all_articles:
                    all_articles.append(full)

        time.sleep(RATE_LIMIT)

    log.info("Total unique PDFs found: %d, articles: %d", len(all_pdfs), len(all_articles))

    dl = fa = sk = 0
    for url in all_pdfs[:MAX_PDFS]:
        prefix = "paris" if "parismou" in url else "tokyo"
        s = _download_pdf(url, prefix)
        time.sleep(RATE_LIMIT)
        if s == "downloaded":
            dl += 1
        elif s == "failed":
            fa += 1
        else:
            sk += 1

    log.info("Done. Downloaded=%d Failed=%d Skipped=%d", dl, fa, sk)

    # Scrape article text from Paris/Tokyo MOU pages
    a_saved = a_failed = 0
    seen_urls = set()
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_articles:
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

    log.info("Articles saved=%d failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
