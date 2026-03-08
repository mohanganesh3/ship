#!/usr/bin/env python3
"""
skuld_scraper.py - Skuld P&I Club and Swedish Club loss prevention scraper.

Skuld: https://www.skuld.com/topics/technical/
Swedish Club: https://www.swedishclub.com/loss-prevention/publications/

These publish maritime safety and loss prevention guidance - accident reports,
safety bulletins, marine circulars, and technical advice documents.
Excellent content for maritime AI training.
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
        logging.FileHandler(LOGS_DIR / "skuld_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("skuld")

SOURCE_NAME = "skuld"
OUT_DIR     = SOURCES.get("skuld", Path(__file__).parent.parent / "data" / "raw_pdfs" / "skuld")
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "skuld_articles.jsonl"
RATE_LIMIT  = 2.0
MAX_ARTICLES = 500
MAX_PDFS    = 300

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Skuld and Swedish Club pages
INDEX_PAGES = [
    # Skuld
    ("https://www.skuld.com/topics/technical/", "skuld.com"),
    ("https://www.skuld.com/topics/cargo/", "skuld.com"),
    ("https://www.skuld.com/topics/marine-risk/", "skuld.com"),
    ("https://www.skuld.com/topics/pollution/", "skuld.com"),
    ("https://www.skuld.com/topics/claims/", "skuld.com"),
    ("https://www.skuld.com/topics/legal/", "skuld.com"),
    ("https://www.skuld.com/topics/safety/", "skuld.com"),
    ("https://www.skuld.com/updates/", "skuld.com"),
    ("https://www.skuld.com/updates/news/", "skuld.com"),
    ("https://www.skuld.com/updates/alerts/", "skuld.com"),
    ("https://www.skuld.com/updates/circulars/", "skuld.com"),
    ("https://www.skuld.com/updates/loss-prevention-publications/", "skuld.com"),
    # Swedish Club
    ("https://www.swedishclub.com/loss-prevention/publications/", "swedishclub.com"),
    ("https://www.swedishclub.com/loss-prevention/", "swedishclub.com"),
    ("https://www.swedishclub.com/loss-prevention/safety-news/", "swedishclub.com"),
    ("https://www.swedishclub.com/loss-prevention/risk-alerts/", "swedishclub.com"),
    ("https://www.swedishclub.com/news/", "swedishclub.com"),
    ("https://www.swedishclub.com/knowledge/", "swedishclub.com"),
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


def _safe_filename(url, prefix=""):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name or len(name) < 3:
        name = re.sub(r"[^\w]", "_", url[-50:])
    if prefix:
        name = f"{prefix}_{name}"
    return name or "skuld_doc.pdf"


def _collect_from_page(page_url, domain_filter, visited):
    """Collect all PDF and article links from a page."""
    if page_url in visited:
        return [], []
    visited.add(page_url)

    log.info("Fetching: %s", page_url)
    resp = _get(page_url)
    if not resp:
        return [], []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []
    articles = []

    base_url = f"https://www.{domain_filter}"

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(base_url, href) if not href.startswith("http") else href
        if domain_filter not in full:
            continue
        low = full.lower()
        if low.endswith(".pdf") or ".pdf?" in low:
            if full not in pdfs:
                pdfs.append(full)
        elif len(full) > len(base_url) + 5:
            if full not in articles:
                articles.append(full)

    return pdfs, articles


def _download_pdf(url, prefix=""):
    if is_downloaded(url):
        return "skipped"
    filename = _safe_filename(url, prefix)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    dest = OUT_DIR / filename
    mark_download_pending(url, SOURCE_NAME)
    try:
        r = requests.get(url, headers=HEADERS, timeout=90, stream=True,
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
        or soup.find("article")
        or soup.find(class_=re.compile(r"content|article|body|entry", re.I))
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

    for page_url, domain in INDEX_PAGES:
        pdfs, articles = _collect_from_page(page_url, domain, visited)
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
        prefix = "skuld" if "skuld.com" in url else "swclub"
        s = _download_pdf(url, prefix)
        time.sleep(RATE_LIMIT)
        if s == "downloaded":
            dl += 1
        elif s == "failed":
            fa += 1
        else:
            sk += 1

    log.info("PDFs: Downloaded=%d Failed=%d Skipped=%d", dl, fa, sk)

    # Scrape article text
    a_saved = a_failed = 0
    seen_urls = set()
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_articles[:MAX_ARTICLES]:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Skip pagination, language toggle, etc.
            if re.search(r"[?&](page|lang|category)=", url):
                continue
            if url.endswith("/") and url.count("/") < 5:
                continue

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
