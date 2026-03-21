#!/usr/bin/env python3
"""
gcaptain_scraper.py - gCaptain maritime news scraper.

gCaptain (https://gcaptain.com) is one of the most popular maritime news 
sites covering:
- Vessel accidents and incidents
- Maritime regulations and compliance
- Shipping markets and industry news
- Coast Guard and port state control
- Offshore and energy sectors
- Naval architecture and technology

gCaptain has 50+ sitemap files with ~100K article URLs since 2007.
This scraper uses sitemap-based discovery for maximum coverage.
"""

import sys, re, time, logging, json
import xml.etree.ElementTree as ET
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
        logging.FileHandler(LOGS_DIR / "gcaptain_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("gcaptain")

BASE_URL    = "https://gcaptain.com"
SOURCE_NAME = "gcaptain"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "gcaptain_articles.jsonl"
RATE_LIMIT  = 0.7
MAX_ARTICLES = 8000  # gCaptain has ~100K articles; limit to 8000
SITEMAP_INDEX = "https://gcaptain.com/sitemap.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Skip non-article URLs  
SKIP_PATTERNS = [
    "wp-content/uploads",
    "cdn-cgi",
    "join-the-club",
    ".jpg", ".jpeg", ".png", ".gif", ".pdf",
]


def _get(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, verify=False)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except Exception as exc:
            log.warning("GET %s attempt %d: %s", url, attempt + 1, exc)
            time.sleep(RATE_LIMIT * 2)
    return None


def _collect_sitemap_urls():
    """Parse sitemap index and all child sitemaps to get article URLs."""
    try:
        r = requests.get(SITEMAP_INDEX, headers=HEADERS, timeout=60, verify=False)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        child_sitemaps = []
        for elem in root.iter():
            if "loc" in elem.tag and elem.text:
                url = elem.text.strip()
                if "sitemap" in url and ".xml" in url:
                    child_sitemaps.append(url)
        log.info("Found %d child sitemaps", len(child_sitemaps))
    except Exception as e:
        log.error("Sitemap index error: %s", e)
        return []

    all_urls = []
    for sitemap_url in child_sitemaps:
        try:
            r = requests.get(sitemap_url, headers=HEADERS, timeout=60, verify=False)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.text)
            count = 0
            for elem in root.iter():
                if "loc" in elem.tag and elem.text:
                    url = elem.text.strip()
                    # Skip non-article URLs
                    if any(pat in url for pat in SKIP_PATTERNS):
                        continue
                    # Must be root-level slug (no sub-paths)
                    path = urlparse(url).path.strip("/")
                    if path and "/" not in path and len(path) > 5:
                        all_urls.append(url)
                        count += 1
            log.info("Sitemap %s: %d article URLs", sitemap_url.split("/")[-1], count)
            time.sleep(0.5)
        except Exception as e:
            log.warning("Sitemap %s error: %s", sitemap_url, e)

    log.info("Total article URLs from sitemaps: %d", len(all_urls))
    return all_urls


def _scrape_article(url):
    """Extract text from a gCaptain article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # gCaptain content is in .entry-content
    content = (
        soup.find("div", class_="entry-content")
        or soup.find("div", class_=re.compile(r"post-content|article-content|article-body", re.I))
        or soup.find("article")
        or soup.find("main")
    )
    if not content:
        return None

    text = content.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
    text = "\n".join(lines)

    word_count = len(text.split())
    if word_count < 80:
        return None

    return {
        "url": url,
        "title": title,
        "content": text,
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

    # Get article URLs from sitemaps
    all_links = _collect_sitemap_urls()
    all_links = [u for u in all_links if u not in seen_urls]
    log.info("New articles to scrape: %d (will do up to %d)", len(all_links), MAX_ARTICLES)

    a_saved = a_failed = 0
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_links[:MAX_ARTICLES]:
            article = _scrape_article(url)
            if article:
                jf.write(json.dumps(article, ensure_ascii=False) + "\n")
                jf.flush()
                log.info("Saved: %s (%d words)", article["title"][:60], article["word_count"])
                a_saved += 1
                seen_urls.add(url)
            else:
                log.debug("Failed/short: %s", url)
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Saved=%d Failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
