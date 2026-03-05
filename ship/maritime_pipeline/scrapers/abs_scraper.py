#!/usr/bin/env python3
"""
abs_scraper.py - American Bureau of Shipping (ABS) publications scraper.

ABS publishes free maritime safety and technical guidance including:
- Advisory notes and technical papers
- Safety management guides  
- Environmental and regulatory publications
- Ship type specific guidance

Source: https://ww2.eagle.org/en/publication.html
        https://www.eagle.org/
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
        logging.FileHandler(LOGS_DIR / "abs_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("abs")

BASE_URL    = "https://ww2.eagle.org"
SOURCE_NAME = "abs"
OUT_DIR     = SOURCES.get("abs", Path(__file__).parent.parent / "data" / "raw_pdfs" / "abs")
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "abs_articles.jsonl"
RATE_LIMIT  = 2.0
MAX_PDFS    = 300

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

INDEX_PAGES = [
    # ABS publications and advisory notes
    "https://ww2.eagle.org/en/rules-and-resources/regulatory-news.html",
    "https://ww2.eagle.org/en/rules-and-resources/rules-and-guides-v2.html",
    "https://ww2.eagle.org/en/rules-and-resources/rules-and-guides-v2/Notice-of-Rule-Changes.html",
    "https://ww2.eagle.org/en/rules-and-resources/flag-port-state-information.html",
    "https://ww2.eagle.org/en/rules-and-resources/flag-port-state-information/psc-quarterly-report.html",
    "https://ww2.eagle.org/en/rules-and-resources/flag-port-state-information/resources.html",
    "https://ww2.eagle.org/en/rules-and-resources/flag-port-state-information/detentions.html",
    "https://ww2.eagle.org/en/rules-and-resources/abs-engineering-reviews.html",
    "https://ww2.eagle.org/en/Products-and-Services/classification-services.html",
    "https://ww2.eagle.org/en/rules-and-resources/abs-app.html",
]


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


def _safe_filename(url, prefix="abs"):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name or len(name) < 4:
        name = re.sub(r"[^\w]", "_", url[-50:])
    return f"{prefix}_{name}" if not name.startswith(prefix) else name


def _collect_from_page(url, visited, base_domains):
    """Collect PDF and article links from page."""
    if url in visited:
        return [], []
    visited.add(url)

    log.info("Fetching: %s", url)
    resp = _get(url)
    if not resp:
        return [], []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    articles = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(url, href) if not href.startswith("http") else href

        # Check domain
        domain_ok = any(d in full for d in base_domains)
        if not domain_ok:
            continue

        low = full.lower()
        if low.endswith(".pdf") or ".pdf?" in low or "/pdf/" in low:
            if full not in pdfs:
                pdfs.append(full)
        elif re.search(r"/(guidance|advisory|technical|news|publication|resource|safenet|bulletin|report|circular)/", full):
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
            hdr = f.read(4)
        if not hdr.startswith(b"%PDF"):
            dest.unlink(missing_ok=True)
            mark_download_failed(url, "not PDF")
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
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    content = (
        soup.find("main")
        or soup.find(class_=re.compile(r"content|article|body|main|entry", re.I))
        or soup.body
    )
    text = content.get_text(separator="\n", strip=True) if content else ""
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
    base_domains = ["eagle.org"]

    for page_url in INDEX_PAGES:
        pdfs, articles = _collect_from_page(page_url, visited, base_domains)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        for a in articles:
            if a not in all_articles:
                all_articles.append(a)
        time.sleep(RATE_LIMIT)

    log.info("Found %d PDFs, %d articles", len(all_pdfs), len(all_articles))

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
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_articles[:300]:
            article = _scrape_article(url)
            if article:
                jf.write(json.dumps(article, ensure_ascii=False) + "\n")
                jf.flush()
                log.info("Article: %s (%d words)", article["title"][:60], article["word_count"])
                a_saved += 1
            else:
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Articles=%d Failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
