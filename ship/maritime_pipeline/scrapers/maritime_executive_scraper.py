#!/usr/bin/env python3
"""
maritime_executive_scraper.py - The Maritime Executive news scraper.

The Maritime Executive (https://maritime-executive.com) is a leading 
maritime industry publication covering:
- Vessel incidents and accidents
- Maritime safety and security
- Environmental regulations
- Maritime law and policy
- Port operations
- Offshore energy
- Naval and coast guard news
- Technology and innovation

Sitemap contains 6,684+ article URLs - uses sitemap-based discovery.
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
        logging.FileHandler(LOGS_DIR / "maritime_executive_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("maritime_executive")

BASE_URL    = "https://maritime-executive.com"
SOURCE_NAME = "maritime_executive"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "maritime_executive_articles.jsonl"
RATE_LIMIT  = 0.7
MAX_ARTICLES = 6000  # Sitemap has 6684 articles

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SITEMAP_URL = "https://maritime-executive.com/sitemap.xml"


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
    """Parse sitemap.xml and return all article URLs."""
    try:
        r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=60, verify=False)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        urls = []
        for elem in root.iter():
            if "loc" in elem.tag and elem.text:
                url = elem.text.strip()
                path = urlparse(url).path.strip("/")
                # Only article and blog URLs
                if path.startswith("article/") or path.startswith("blog/"):
                    urls.append(url)
        log.info("Sitemap: found %d article URLs", len(urls))
        return urls
    except Exception as e:
        log.error("Sitemap error: %s", e)
        return []


def _scrape_article(url):
    """Extract text from a Maritime Executive article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Maritime Executive article content
    content = (
        soup.find("div", class_=re.compile(r"article-body|entry-content|post-content|content-body", re.I))
        or soup.find("div", {"itemprop": "articleBody"})
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

    # Get all article URLs from sitemap
    all_links = _collect_sitemap_urls()
    # Filter out already seen
    all_links = [u for u in all_links if u not in seen_urls]
    log.info("New articles to scrape: %d", len(all_links))

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
