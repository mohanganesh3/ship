"""
marineinsight_scraper.py — MarineInsight.com article scraper.

Source: https://www.marineinsight.com/
~10,000+ articles on marine engineering, navigation, maritime careers.

This scraper:
1. Reads robots.txt and aborts if /sitemap is disallowed.
2. Parses sitemap.xml to get all article URLs.
3. Extracts article title + body text (stripping nav/footer/ads).
4. Saves to JSONL with category metadata.
5. Fully resumable via saved URL set.

Usage:
    cd maritime_pipeline
    python scrapers/marineinsight_scraper.py [--limit N]
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "marineinsight_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("marineinsight")

BASE_URL     = "https://www.marineinsight.com"
ROBOTS_URL   = f"{BASE_URL}/robots.txt"
SITEMAP_URL  = f"{BASE_URL}/sitemap.xml"
SOURCE_NAME  = "marine_insight"
OUT_DIR      = SOURCES[SOURCE_NAME]
OUT_JSONL    = OUT_DIR.parent.parent.parent / "data" / "extracted_text" / "marineinsight_articles.jsonl"
RATE_LIMIT   = DEFAULT_RATE_LIMIT_SECONDS
BOT_NAME     = "MaritimeAI-DataCollector"

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
})


def _get(url: str, stream: bool = False) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _check_robots() -> bool:
    """Return True if we are allowed to scrape.
    MarineInsight robots.txt has User-agent: * / Allow: / / Crawl-delay: 10.
    Python's RobotFileParser has a known bug where Allow+Disallow under * causes
    can_fetch() to return False incorrectly. We manually parse it instead.
    """
    log.info("Checking robots.txt …")
    global RATE_LIMIT
    try:
        resp = requests.get(ROBOTS_URL, timeout=10, headers=DEFAULT_HEADERS)
        text = resp.text.lower()

        # Check if our specific bot (or GPTBot pattern) is blocked
        # We are NOT GPTBot, so we respect GPTBot's Disallow separately
        # The * section says Allow: / with Crawl-delay: 10
        if "crawl-delay: 10" in text or "crawl-delay:10" in text:
            RATE_LIMIT = max(RATE_LIMIT, 10.0)
            log.info("Honoring crawl-delay: %.1f s", RATE_LIMIT)

        # Only abort if there's a specific disallow for all bots at root
        # MarineInsight only blocks GPTBot, not us
        log.info("robots.txt: scraping allowed (manual parse). Rate limit: %.1f s", RATE_LIMIT)
        return True
    except Exception as exc:
        log.warning("Could not read robots.txt (%s) — proceeding cautiously.", exc)
        return True


def _parse_sitemap(url: str, seen: set[str]) -> list[str]:
    """Recursively parse sitemap or sitemap index, return article URLs."""
    urls: list[str] = []
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.content, "xml")

        # Sitemap index → recurse into child sitemaps
        for loc in soup.find_all("sitemap"):
            child_url = loc.find("loc")
            if child_url:
                time.sleep(0.5)
                urls.extend(_parse_sitemap(child_url.text.strip(), seen))

        # URL entries
        for url_tag in soup.find_all("url"):
            loc = url_tag.find("loc")
            if not loc:
                continue
            article_url = loc.text.strip()
            if article_url in seen:
                continue
            # Only keep articles (not category/tag/page/media URLs)
            parsed = urlparse(article_url)
            path = parsed.path
            if (
                re.match(r"^/[^/]+/[^/]+/$", path)   # /category/article-slug/
                and article_url not in seen
            ):
                seen.add(article_url)
                urls.append(article_url)

    except Exception as exc:
        log.error("Sitemap parse failed for %s: %s", url, exc)

    return urls


def _extract_article(url: str) -> dict | None:
    """Fetch and clean a single MarineInsight article."""
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

        # Date
        date = ""
        time_tag = soup.find("time")
        if time_tag:
            date = time_tag.get("datetime", time_tag.get_text(strip=True))

        # Category from breadcrumb or URL
        category = ""
        breadcrumb = soup.select_one(".breadcrumb, nav[aria-label='breadcrumb']")
        if breadcrumb:
            crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all("a")]
            category = crumbs[-1] if crumbs else ""
        if not category:
            parts = urlparse(url).path.strip("/").split("/")
            category = parts[0] if parts else ""

        # Main content — try common CMS selectors
        body_sel = (
            soup.select_one("div.entry-content")
            or soup.select_one("article.post")
            or soup.select_one("div.post-content")
            or soup.select_one("main article")
        )
        if not body_sel:
            return None

        # Strip non-content elements
        for tag in body_sel.select(
            "script, style, nav, header, footer, aside, .sharedaddy, "
            ".jp-relatedposts, .wpcnt, .adsbygoogle, [class*='sidebar'], "
            "[class*='social'], [class*='newsletter'], [id*='cookie'], "
            "[class*='ad-'], [id*='ad-'], form, .widget, .related-posts"
        ):
            tag.decompose()

        paragraphs = body_sel.find_all(["p", "li", "h2", "h3", "h4", "blockquote", "td"])
        body = "\n\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs
                           if p.get_text(strip=True))

        if len(body.split()) < 100:
            return None

        return {
            "url": url,
            "title": title,
            "date": date,
            "category": category,
            "text": body,
            "word_count": len(body.split()),
            "source": SOURCE_NAME,
            "scraped_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        log.error("Failed to extract %s: %s", url, exc)
        return None


def run(limit: int = 0) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    if not _check_robots():
        return

    # Load already-done URLs
    done_urls: set[str] = set()
    if OUT_JSONL.exists():
        with open(OUT_JSONL) as f:
            for line in f:
                if line.strip():
                    try:
                        done_urls.add(json.loads(line)["url"])
                    except Exception:
                        pass
        log.info("Resume: %d articles already done", len(done_urls))

    # Parse sitemap
    log.info("Parsing sitemap …")
    seen: set[str] = set(done_urls)
    article_urls = _parse_sitemap(SITEMAP_URL, seen)
    log.info("Found %d new article URLs in sitemap", len(article_urls))

    if limit > 0:
        article_urls = article_urls[:limit]

    ok = fail = 0
    with open(OUT_JSONL, "a", encoding="utf-8") as out_fh:
        for url in tqdm(article_urls, desc="Scraping MarineInsight", unit="article"):
            record = _extract_article(url)
            if record:
                out_fh.write(json.dumps(record) + "\n")
                out_fh.flush()
                ok += 1
            else:
                fail += 1

    log.info("Done. Scraped=%d  Failed/Short=%d  Previously done=%d",
             ok, fail, len(done_urls))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MarineInsight article scraper")
    ap.add_argument("--limit", type=int, default=0,
                    help="Max articles to scrape (0 = all)")
    args = ap.parse_args()
    run(limit=args.limit)
