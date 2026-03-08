#!/usr/bin/env python3
"""
hellenic_scraper.py - Hellenic Shipping News (HSN) scraper.

Hellenic Shipping News Worldwide is one of the most comprehensive
maritime news sources, covering:
- Ship accidents and incidents
- Regulatory changes
- Environmental news
- Port and shipping market news
- Technical and safety topics

Source: https://www.hellenicshippingnews.com/
Sections: Safety, Environmental, Regulations, Offshore, etc.
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
        logging.FileHandler(LOGS_DIR / "hellenic_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("hellenic")

BASE_URL    = "https://www.hellenicshippingnews.com"
SOURCE_NAME = "hellenic"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "hellenic_articles.jsonl"
RATE_LIMIT  = 0.7
MAX_ARTICLES = 2000  # HSN has thousands of articles
MAX_PAGES_PER_SECTION = 20  # Up to 20 pages per category section

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# HSN category pages to scrape (maritime-relevant sections)
# Use /category/ URL pattern (verified from site)
SECTIONS = [
    "/category/shipping-news/international-shipping-news/",
    "/category/shipping-news/piracy-and-security-news/",
    "/category/shipping-news/shipping-emission-possible/",
    "/category/shipping-news/marine-insurance-pi-club-news/",
    "/category/shipping-news/port-news/",
    "/category/shipping-news/shipbuilding-news/",
    "/category/shipping-news/shipping-law-news/",
    "/category/shipping-news/interviews/",
    "/category/shipping-news/",
    "/tag/safety/",
    "/tag/accident/",
    "/tag/maritime-safety/",
    "/tag/imo/",
    "/tag/marpol/",
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


def _collect_article_links_from_listing(url):
    """Extract article links from a HSN listing/category page."""
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href) if not href.startswith("http") else href
        if "hellenicshippingnews.com" not in full:
            continue
        # Helllenic articles are at root level with slug: /article-title-slug/
        # Not with date patterns. Filter out category/tag/page URLs.
        path = urlparse(full).path.strip("/")
        if (path and "/" not in path and  # only slug at root level
                not path.startswith("category") and
                not path.startswith("tag") and
                not path.startswith("page") and
                not path.startswith("rss") and
                not path.startswith("event") and
                len(path) > 10 and  # not too short
                full not in links):
            links.append(full)

    return links


def _scrape_article(url):
    """Extract text from a HSN article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()

    # Title
    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # HSN content is in the article section or .entry-content
    content = (
        soup.find("div", class_="entry-content")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"post-content|article-content|content-area", re.I))
        or soup.find("main")
    )
    if not content:
        return None

    text = content.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 25]
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

    # Load already saved URLs
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

    # Collect article links from all sections
    all_article_links = []
    for section in SECTIONS:
        for page_num in range(1, MAX_PAGES_PER_SECTION + 1):
            # HSN uses /page/N/ for pagination
            if page_num == 1:
                page_url = BASE_URL + section
            else:
                page_url = BASE_URL + section + f"page/{page_num}/"

            log.info("Fetching listing: %s", page_url)
            links = _collect_article_links_from_listing(page_url)
            if not links:
                log.info("No more articles in %s at page %d", section, page_num)
                break

            new_links = [l for l in links if l not in all_article_links]
            all_article_links.extend(new_links)
            log.info("Section %s page %d: +%d links (total %d)",
                     section, page_num, len(new_links), len(all_article_links))

            time.sleep(RATE_LIMIT)

            if len(all_article_links) >= MAX_ARTICLES:
                break

        if len(all_article_links) >= MAX_ARTICLES:
            break

    log.info("Total articles found: %d", len(all_article_links))

    # Scrape each article
    a_saved = a_failed = 0
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_article_links[:MAX_ARTICLES]:
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
                log.debug("Failed: %s", url)
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Saved=%d Failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
