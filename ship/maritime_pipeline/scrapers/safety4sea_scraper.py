#!/usr/bin/env python3
"""
safety4sea_scraper.py - SAFETY4SEA maritime safety news scraper.

SAFETY4SEA is one of the most comprehensive maritime safety portals,
publishing extensive content on:
- Accidents and incidents
- Regulatory compliance
- PSC detentions and inspections  
- Environmental topics
- Crew safety and training
- Technical publications

Source: https://safety4sea.com/

NOTE: Uses tag-based pagination - verified working via debug.
Category URLs (/category/...) return 404.
Tag pages (/tag/SLUG/page/N/) work correctly.
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
        logging.FileHandler(LOGS_DIR / "safety4sea_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("safety4sea")

BASE_URL    = "https://safety4sea.com"
SOURCE_NAME = "safety4sea"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "safety4sea_articles.jsonl"
RATE_LIMIT  = 0.7
MAX_ARTICLES = 5000
MAX_PAGES_PER_TAG = 50  # ~10 articles per page, 50 pages = ~500 per tag

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Verified working tags (debug_s4s2.py + debug_s4s3.py confirmed these return 200)
TAGS = [
    "maritime-safety",
    "imo",
    "marpol",
    "fire",
    "collision",
    "grounding",
    "solas",
    "psc",
    "port-state-control",
    "seafarers",
    "pollution",
    "tanker",
    "bulk-carrier",
    "container-ship",
    "accidents",
    "incident",
    "navigation",
    "vessel",
    "emergency",
    "safety-management",
    "crew",
    "training",
    "decarbonization",
    "emissions",
    "ecdis",
    "bridge",
    "machinery",
    "cargo",
    "piracy",
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


def _collect_article_links_from_tag_page(url):
    """Extract article links from a safety4sea tag/listing page."""
    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        if not href.startswith("http"):
            href = urljoin(BASE_URL, href)
        if "safety4sea.com" not in href:
            continue
        # Skip event/external subdomains
        if "events.safety4sea.com" in href:
            continue

        path = urlparse(href).path.strip("/")
        # Articles are root-level slugs - no subdirectory separator
        # e.g. /grounding-incident-2024/ not /tag/grounding/
        if (path
                and "/" not in path  # root-level slug only
                and len(path) > 10
                and not path.startswith("page")
                and not path.startswith("wp-")
                and not path.startswith("feed")):
            if href not in links:
                links.append(href)

    return links


def _scrape_article(url):
    """Extract text from a safety4sea article page."""
    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["nav", "footer", "script", "style", "header", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("h2")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Safety4Sea content is in .entry-content or similar
    content = (
        soup.find("div", class_="entry-content")
        or soup.find("div", class_=re.compile(r"post-content|article-body|content-area", re.I))
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

    all_links = []
    all_links_set = set(seen_urls)

    for tag in TAGS:
        if len(all_links) >= MAX_ARTICLES:
            break

        for page_num in range(1, MAX_PAGES_PER_TAG + 1):
            if len(all_links) >= MAX_ARTICLES:
                break

            if page_num == 1:
                page_url = f"{BASE_URL}/tag/{tag}/"
            else:
                page_url = f"{BASE_URL}/tag/{tag}/page/{page_num}/"

            links = _collect_article_links_from_tag_page(page_url)
            if not links:
                log.info("Tag %s: no more articles at page %d", tag, page_num)
                break

            new = [l for l in links if l not in all_links_set]
            all_links.extend(new)
            all_links_set.update(new)
            log.info("Tag /%s/ page %d: +%d new links (total %d)",
                     tag, page_num, len(new), len(all_links))

            time.sleep(RATE_LIMIT)

    log.info("Total unique article links collected: %d", len(all_links))

    a_saved = a_failed = 0
    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for url in all_links[:MAX_ARTICLES]:
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
                log.debug("Failed/short: %s", url)
                a_failed += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Saved=%d Failed=%d", a_saved, a_failed)


if __name__ == "__main__":
    run()
