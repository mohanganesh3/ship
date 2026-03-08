#!/usr/bin/env python3
"""
bimco_scraper.py - BIMCO maritime publications and news scraper.

BIMCO (Baltic and International Maritime Council) publishes:
- Free news articles and commentary
- Shipping insights and publications
- Regulatory updates and circular letters
- Market analysis and shipping trends

Source: https://www.bimco.org/
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
        logging.FileHandler(LOGS_DIR / "bimco_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("bimco")

BASE_URL    = "https://www.bimco.org"
SOURCE_NAME = "bimco"
OUT_DIR     = SOURCES.get("bimco", Path(__file__).parent.parent / "data" / "raw_pdfs" / "bimco")
OUT_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "bimco_articles.jsonl"
RATE_LIMIT  = 2.0
MAX_ARTICLES = 800

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
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


def _safe_filename(url, prefix="bimco"):
    name = urlparse(url).path.rstrip("/").split("/")[-1]
    name = re.sub(r"[^\w\-.]", "_", name)
    if not name or len(name) < 4:
        name = re.sub(r"[^\w]", "_", url[-50:])
    return f"{prefix}_{name}"


def _collect_sitemap_urls():
    """Get all article URLs from BIMCO sitemap."""
    resp = _get("https://www.bimco.org/sitemap.xml")
    if not resp:
        log.error("Failed to fetch sitemap")
        return []

    soup = BeautifulSoup(resp.text, "xml")
    all_urls = [loc.get_text().strip() for loc in soup.find_all("loc")]
    log.info("Sitemap total URLs: %d", len(all_urls))

    article_urls = []
    for u in all_urls:
        path = urlparse(u).path
        if re.search(r"/news-insights/[^/]+/[^/]+", path):
            article_urls.append(u)
        elif re.search(r"/regulatory-affairs/[^/]+/insights/[^/]+", path):
            article_urls.append(u)
    log.info("Article URLs from sitemap: %d", len(article_urls))
    return article_urls


def _scrape_article(url):
    """Extract text from a BIMCO article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # BIMCO content: try specific selectors that work (found via debug)
    content = (
        soup.find("div", class_=re.compile(r"main-page-layout__body"))
        or soup.find("div", class_=re.compile(r"bimco-container"))
        or soup.find("article")
        or soup.find("main")
    )
    if not content:
        return None

    # Remove navigation and related content sections
    for tag in content.find_all(class_=re.compile(r"related|nav|menu|breadcrumb|social|header")):
        tag.decompose()

    text = content.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
    text = "\n".join(lines)

    word_count = len(text.split())
    if word_count < 80:
        return None

    return {
        "url": url,
        "title": title,
        "text": text,
        "word_count": word_count,
        "source": SOURCE_NAME,
    }


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load already saved URLs to resume
    seen_urls = set()
    if JSONL_FILE.exists():
        with open(JSONL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if "url" in d:
                        seen_urls.add(d["url"])
                except Exception:
                    pass
    log.info("Already saved: %d articles", len(seen_urls))

    # Collect URLs from sitemap
    article_urls = _collect_sitemap_urls()

    a_saved = a_failed = 0

    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in article_urls[:MAX_ARTICLES]:
            if url in seen_urls:
                continue

            article = _scrape_article(url)
            if article:
                jf.write(json.dumps(article, ensure_ascii=False) + "\n")
                jf.flush()
                log.info("Saved: %s (%d words)", article["title"][:60], article["word_count"])
                a_saved += 1
                seen_urls.add(url)
            else:
                log.warning("Failed: %s", url)
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Articles saved=%d failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
