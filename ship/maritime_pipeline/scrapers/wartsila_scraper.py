"""
wartsila_scraper.py — Wärtsilä Encyclopedia of Marine Technology scraper.

Source     : https://www.wartsila.com/encyclopedia
robots.txt : Allow /encyclopedia, crawl-delay: 1
~4000+ technical entries, freely readable.

Strategy: Collect all entry URLs from the A-Z index pages, then fetch each entry
          and save title + full text to JSONL.

Usage:
    cd maritime_pipeline
    python scrapers/wartsila_scraper.py
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import init_db, is_downloaded, mark_download_pending, mark_download_done, mark_download_failed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "wartsila_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("wartsila")

BASE_URL     = "https://www.wartsila.com"
ENC_INDEX    = "https://www.wartsila.com/encyclopedia"
SOURCE_NAME  = "wartsila"
# Wartsila is text-only, store in a JSONL under the source dir
OUT_DIR      = SOURCES[SOURCE_NAME]
OUT_JSONL    = OUT_DIR.parent.parent.parent / "data" / "extracted_text" / "wartsila_encyclopedia.jsonl"
RATE_LIMIT   = max(DEFAULT_RATE_LIMIT_SECONDS, 1.0)   # honour crawl-delay: 1

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Referer": "https://www.wartsila.com/encyclopedia",
})


def _get(url: str) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _collect_entry_urls() -> list[str]:
    """
    The Wärtsilä encyclopedia A-Z index links to either:
      (a) Letter pages: /encyclopedia/a, /encyclopedia/b, …
      (b) Or lists all entries on one page.
    We handle both patterns.
    """
    urls: list[str] = []
    seen: set[str] = set()

    # Fetch the main index
    log.info("Fetching encyclopedia index …")
    resp = _get(ENC_INDEX)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Pattern 1: find letter-index links (new Wartsila URL: /encyclopedia/letter/X)
    letter_links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Match /encyclopedia/letter/a through /encyclopedia/letter/z
        if re.match(r"^/?encyclopedia/letter/[a-z0-9]$", href, re.IGNORECASE):
            # Handle both absolute and relative hrefs
            full = (BASE_URL + "/" + href.lstrip("/")) if href.startswith("/") else href
            if "/encyclopedia/letter/" not in full:
                full = BASE_URL + "/encyclopedia/letter/" + href[-1]
            if full not in seen:
                seen.add(full)
                letter_links.append(full)

    # Also add full-URL letter links (https://www.wartsila.com/encyclopedia/letter/a)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/encyclopedia/letter/[a-z0-9]$", href, re.IGNORECASE):
            full = href if href.startswith("http") else BASE_URL + href
            if full not in seen:
                seen.add(full)
                letter_links.append(full)

    if letter_links:
        log.info("Found %d letter-index pages", len(letter_links))
        for lurl in tqdm(letter_links, desc="Collecting entry URLs", unit="letter"):
            try:
                lresp = _get(lurl)
                lsoup = BeautifulSoup(lresp.text, "html.parser")
                for a in lsoup.find_all("a", href=True):
                    href = a["href"]
                    # New pattern: /encyclopedia/term/slug OR full URL
                    is_term = (
                        re.search(r"/encyclopedia/term/[^/]+", href)
                        or re.match(r"^/encyclopedia/[^/]+$", href)
                    )
                    if not is_term:
                        continue
                    # Skip letter index pages themselves
                    if re.search(r"/encyclopedia/letter/", href):
                        continue
                    full = href if href.startswith("http") else BASE_URL + href
                    if full not in seen and full != ENC_INDEX:
                        seen.add(full)
                        urls.append(full)
            except Exception as exc:
                log.warning("Failed letter page %s: %s", lurl, exc)
    
    if not letter_links or not urls:
        # Fallback: mine index page for /term/ links directly
        log.info("No letter pages / no entries found, mining index page directly …")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if re.search(r"/encyclopedia/term/", href) or re.match(r"^/encyclopedia/[^/]+$", href):
                full = href if href.startswith("http") else BASE_URL + href
                if full not in seen and full != ENC_INDEX:
                    seen.add(full)
                    urls.append(full)

    log.info("Total encyclopedia entry URLs collected: %d", len(urls))
    return urls


def _extract_entry_text(soup: BeautifulSoup) -> tuple[str, str]:
    """Return (title, body_text) from a Wärtsilä encyclopedia entry page."""
    # Title
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Main content — try several CSS selector patterns
    content_div = (
        soup.select_one("div.encyclopedia-content")
        or soup.select_one("div.entry-content")
        or soup.select_one("article")
        or soup.select_one("main")
        or soup.select_one(".content-section")
    )

    if content_div:
        # Remove script/style/nav
        for tag in content_div(["script", "style", "nav", "header", "footer",
                                 "aside", "form", "button"]):
            tag.decompose()
        paragraphs = content_div.find_all(["p", "li", "h2", "h3", "h4", "td"])
        body = "\n\n".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
    else:
        # Fallback: all paragraph text
        body = "\n\n".join(p.get_text(strip=True) for p in soup.find_all("p"))

    return title, body.strip()


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def run(limit: int = 0) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    entry_urls = _collect_entry_urls()
    if limit > 0:
        entry_urls = entry_urls[:limit]

    already_done = 0
    if OUT_JSONL.exists():
        with open(OUT_JSONL) as f:
            done_urls = {json.loads(l)["url"] for l in f if l.strip()}
        already_done = len(done_urls)
        entry_urls = [u for u in entry_urls if u not in done_urls]
        log.info("Resuming: %d already done, %d remaining", already_done, len(entry_urls))

    ok = fail = 0
    with open(OUT_JSONL, "a", encoding="utf-8") as out_fh:
        for url in tqdm(entry_urls, desc="Scraping encyclopedia", unit="entry"):
            slug = _slug_from_url(url)
            try:
                resp = _get(url)
                soup = BeautifulSoup(resp.text, "html.parser")
                title, body = _extract_entry_text(soup)

                if len(body.split()) < 20:
                    log.debug("Skipping shallow entry: %s", url)
                    continue

                record = {
                    "url": url,
                    "slug": slug,
                    "title": title,
                    "text": body,
                    "word_count": len(body.split()),
                    "source": SOURCE_NAME,
                    "scraped_at": datetime.utcnow().isoformat(),
                }
                out_fh.write(json.dumps(record) + "\n")
                out_fh.flush()
                ok += 1
            except Exception as exc:
                log.error("Failed %s: %s", url, exc)
                fail += 1

    log.info("Done. Scraped=%d  Errors=%d  Previously done=%d", ok, fail, already_done)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Wärtsilä Encyclopedia scraper")
    ap.add_argument("--limit", type=int, default=0,
                    help="Max entries to fetch (0 = all)")
    args = ap.parse_args()
    run(limit=args.limit)
