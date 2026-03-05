#!/usr/bin/env python3
"""
classnk_scraper.py - ClassNK (Nippon Kaiji Kyokai) publication scraper.

ClassNK is one of the world's largest and most prestigious maritime
classification societies, publishing safety guidelines, technical notices,
and maritime engineering research.

Sources:
- https://www.classnk.or.jp/hp/en/
- Technical guidelines and publications
- Survey/inspection related documents

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
        logging.FileHandler(LOGS_DIR / "classnk_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("classnk")

BASE_URL    = "https://www.classnk.or.jp"
SOURCE_NAME = "classnk"
OUT_DIR     = Path(__file__).parent.parent / "data" / "raw_pdfs" / "classnk"
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "classnk_articles.jsonl"
RATE_LIMIT  = 2.5
MAX_PDFS    = 500
MAX_ARTICLES = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ClassNK public content pages
INDEX_PAGES = [
    "https://www.classnk.or.jp/hp/en/publications_outlines.html",
    "https://www.classnk.or.jp/hp/en/tech_info.html",
    "https://www.classnk.or.jp/hp/en/activities/tech/notice/index.html",
    "https://www.classnk.or.jp/hp/en/activities/tech/paper/",
    "https://www.classnk.or.jp/hp/en/rules_reg/rules/nkrules_list.html",
    "https://www.classnk.or.jp/hp/en/activities/tech/seminar.html",
    "https://www.classnk.or.jp/hp/en/activities/environment.html",
    "https://www.classnk.or.jp/hp/en/activities/tech/service/index.html",
    "https://www.classnk.or.jp/hp/en/sustainability/",
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


def _safe_filename(url, prefix="classnk"):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name or len(name) < 4:
        name = re.sub(r"[^\w]", "_", url[-50:])
    return f"{prefix}_{name}"


def _collect_from_page(url, visited):
    """Collect PDF and article links from page."""
    if url in visited:
        return [], []
    visited.add(url)

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

        # Only classnk.or.jp + public PDF repositories
        if "classnk" not in full and "nk-file" not in full:
            continue

        low = full.lower()
        if low.endswith(".pdf") or ".pdf?" in low:
            if full not in pdfs:
                pdfs.append(full)
        elif "/en/" in full and "/hp/" in full:
            if full not in articles and full != url:
                # Only pages with content
                path = urlparse(full).path
                if len(path.split("/")) >= 4:
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
    title = title_tag.get_text(strip=True) if title_tag else urlparse(url).path.split("/")[-1]

    content = (
        soup.find("main")
        or soup.find(id="contents")
        or soup.find(class_=re.compile(r"contents|content|main|body", re.I))
        or soup.body
    )
    if not content:
        return None

    text = content.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 25]
    text = "\n".join(lines)

    word_count = len(text.split())
    if word_count < 80:
        return None

    return {"url": url, "title": title, "text": text,
            "word_count": word_count, "source": SOURCE_NAME}


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    visited_pages = set()
    all_pdfs = []
    all_articles = []

    # First pass: collect from known pages
    for page_url in INDEX_PAGES:
        log.info("Indexing: %s", page_url)
        pdfs, articles = _collect_from_page(page_url, visited_pages)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        for a in articles:
            if a not in all_articles:
                all_articles.append(a)
        time.sleep(RATE_LIMIT)

    log.info("Pass 1: Found %d PDFs, %d articles", len(all_pdfs), len(all_articles))

    # Second pass: follow article links one level deeper
    article_pass1 = all_articles[:]
    for art_url in article_pass1[:50]:
        pdfs, sub_articles = _collect_from_page(art_url, visited_pages)
        for p in pdfs:
            if p not in all_pdfs:
                all_pdfs.append(p)
        for a in sub_articles:
            if a not in all_articles:
                all_articles.append(a)
        time.sleep(RATE_LIMIT)

    log.info("Pass 2: Found %d PDFs, %d articles total", len(all_pdfs), len(all_articles))

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
    seen_art_urls = set()
    a_saved = a_failed = 0
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_articles[:MAX_ARTICLES]:
            if url in seen_art_urls:
                continue
            seen_art_urls.add(url)
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
