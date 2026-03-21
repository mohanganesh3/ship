"""
gard_scraper.py — Gard P&I Club maritime insights article scraper.

Source  : https://www.gard.no/en/insights/
~1,450+ articles on maritime safety, loss prevention, casualty handling.
No explicit robots.txt restriction on /en/insights/.

Usage:
    cd maritime_pipeline
    python scrapers/gard_scraper.py [--max-pages N]
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

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
        logging.FileHandler(LOGS_DIR / "gard_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("gard")

BASE_URL      = "https://www.gard.no"
INSIGHTS_URL  = "https://www.gard.no/en/insights/"
SITEMAP_URLS  = [
    "https://gard.no/sitemaps/insights.xml",
    "https://gard.no/sitemaps/company-news.xml",
    "https://gard.no/sitemaps/circulars.xml",
]
SOURCE_NAME  = "gard"
OUT_DIR      = SOURCES[SOURCE_NAME]
OUT_JSONL    = OUT_DIR.parent.parent.parent / "data" / "extracted_text" / "gard_articles.jsonl"
RATE_LIMIT   = DEFAULT_RATE_LIMIT_SECONDS

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
})


def _get(url: str, params: dict = None) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT,
                               allow_redirects=True, params=params)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _collect_article_urls(max_pages: int = 999) -> list[str]:
    """Collect all Gard article URLs from their XML sitemaps."""
    urls: list[str] = []
    seen: set[str] = set()

    for sitemap_url in SITEMAP_URLS:
        log.info("Fetching sitemap: %s", sitemap_url)
        try:
            resp = _get(sitemap_url)
            soup = BeautifulSoup(resp.content, "xml")
            locs = soup.find_all("loc")
            for loc in locs:
                url = loc.text.strip()
                if url and url not in seen:
                    # Ensure URL uses www.gard.no domain
                    url = url.replace("https://gard.no/", "https://www.gard.no/")
                    seen.add(url)
                    urls.append(url)
            log.info("Sitemap %s: +%d URLs (total %d)", sitemap_url, len(locs), len(urls))
        except Exception as exc:
            log.error("Failed to fetch sitemap %s: %s", sitemap_url, exc)

    log.info("Total article URLs collected: %d", len(urls))
    return urls


def _extract_article(url: str) -> dict | None:
    """Fetch and parse a single Gard insight article."""
    try:
        resp = _get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

        # Date
        date = ""
        date_tag = soup.select_one("time[datetime], .article-date, .publication-date, .date")
        if date_tag:
            date = date_tag.get("datetime", "") or date_tag.get_text(strip=True)

        # Category / tags
        category = ""
        cat_tag = soup.select_one(".category, .tag, .article-type, nav.breadcrumb li:last-child")
        if cat_tag:
            category = cat_tag.get_text(strip=True)

        # Body text — strip boilerplate
        body_sel = (
            soup.select_one("article .article-body")
            or soup.select_one("div.rich-text")
            or soup.select_one(".article-content")
            or soup.select_one("main article")
            # Gard uses Chakra UI with dynamic class names — pick div with most paragraph content
            or next(
                (div for div in soup.find_all("div", class_=True)
                 if sum(len(p.get_text().split()) for p in div.find_all("p", recursive=False)) > 50),
                None
            )
            or soup.select_one("main")
        )
        if not body_sel:
            return None

        for tag in body_sel(["script", "style", "nav", "header", "footer",
                              "aside", "form", ".related-articles", ".share-buttons"]):
            tag.decompose()

        paragraphs = body_sel.find_all(["p", "li", "h2", "h3", "h4", "blockquote"])
        body = "\n\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs)

        if len(body.split()) < 50:
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


def run(max_pages: int = 999) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

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
        log.info("Resuming: %d articles already scraped", len(done_urls))

    article_urls = _collect_article_urls(max_pages=max_pages)
    to_scrape = [u for u in article_urls if u not in done_urls]
    log.info("Articles to scrape: %d (skipping %d)", len(to_scrape), len(done_urls))

    ok = fail = 0
    with open(OUT_JSONL, "a", encoding="utf-8") as out_fh:
        for url in tqdm(to_scrape, desc="Scraping Gard articles", unit="article"):
            record = _extract_article(url)
            if record:
                out_fh.write(json.dumps(record) + "\n")
                out_fh.flush()
                ok += 1
            else:
                fail += 1

    log.info("Done. Scraped=%d  Failed/Skipped=%d", ok, fail)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gard P&I Club insights scraper")
    ap.add_argument("--max-pages", type=int, default=999,
                    help="Max listing pages to traverse")
    args = ap.parse_args()
    run(max_pages=args.max_pages)
