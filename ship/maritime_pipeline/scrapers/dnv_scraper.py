#!/usr/bin/env python3
"""
dnv_scraper.py - DNV maritime insights and publications article scraper.

Source: https://www.dnv.com/maritime/
Focus: Insights, technical topics, advisory articles — all publicly accessible.

DNV's maritime website has hundreds of in-depth articles on:
- CII, EEXI, SEEMP, MRV (emissions regulations)
- FuelEU Maritime, LNG, alternative fuels
- Ship energy efficiency
- Maritime cybersecurity
- SOLAS regulations
- Classification rules

Usage:
    cd maritime_pipeline
    python scrapers/dnv_scraper.py
"""

import sys, re, time, json, logging
import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

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
        logging.FileHandler(LOGS_DIR / "dnv_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("dnv")

BASE_URL    = "https://www.dnv.com"
SOURCE_NAME = "dnv"
OUT_PDF_DIR = SOURCES.get("dnv", Path(__file__).parent.parent / "data" / "raw_pdfs" / "dnv")
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "dnv_articles.jsonl"
OUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = 2.0
MAX_ARTICLES = 500

# DNV maritime insights - CONFIRMED working URLs (no /index.html suffix needed)
INDEX_PAGES = [
    "https://www.dnv.com/maritime/insights/",
    "https://www.dnv.com/maritime/insights/topics/",
    "https://www.dnv.com/maritime/publications/",
    # Confirmed topic pages from the topics directory
    "https://www.dnv.com/maritime/insights/topics/CII-carbon-intensity-indicator/",
    "https://www.dnv.com/maritime/insights/topics/fueleu-maritime/",
    "https://www.dnv.com/maritime/insights/topics/eexi/",
    "https://www.dnv.com/maritime/insights/topics/eu-emissions-trading-system/",
    "https://www.dnv.com/maritime/insights/topics/ship-energy-efficiency/",
    "https://www.dnv.com/maritime/insights/topics/maritime-cybersecurity/",
    "https://www.dnv.com/maritime/insights/topics/net-zero-framework/",
    "https://www.dnv.com/maritime/insights/topics/lng-as-marine-fuel/",
    "https://www.dnv.com/maritime/insights/topics/ihm-ship-recycling/",
    "https://www.dnv.com/maritime/insights/topics/managing-the-risk-of-blackouts/",
    "https://www.dnv.com/maritime/insights/topics/new-solas-regulation-for-lifting-appliances-overview/",
    "https://www.dnv.com/maritime/insights/topics/new-solas-regulation-for-anchor-handling-winches/",
    "https://www.dnv.com/maritime/insights/topics/shaft-alignment-and-propulsion-shaft-bearings/",
    "https://www.dnv.com/maritime/insights/topics/waps-wind-assisted-propulsion-systems/",
    "https://www.dnv.com/maritime/insights/topics/seemp-part-iii/",
    "https://www.dnv.com/maritime/insights/topics/dcs/",
    "https://www.dnv.com/maritime/insights/topics/mrv/",
    "https://www.dnv.com/maritime/insights/topics/imo-ip-code/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}


def _get(url):
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code == 404:
                log.warning("404: %s", url)
                return None
            r.raise_for_status()
            return r
        except Exception as exc:
            log.warning("GET %s attempt %d: %s", url, attempt + 1, exc)
            time.sleep(RATE_LIMIT)
    return None


def _extract_text_from_soup(soup):
    """Extract readable text from a DNV article page."""
    # Remove navigation, scripts, styles
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    # Try article content first
    article = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|article|main", re.I))
    if article:
        text = article.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # Clean up
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines)


def _collect_article_links(index_url, visited):
    if index_url in visited:
        return []
    visited.add(index_url)

    resp = _get(index_url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        full = urljoin(BASE_URL, href) if not href.startswith("http") else href
        parsed = urlparse(full)

        # Accept DNV maritime article/insight pages
        if (parsed.netloc == "www.dnv.com"
                and "/maritime/" in parsed.path
                and full not in visited
                and "?" not in full
                and "#" not in full
                and not full.endswith(".pdf")):
            # Skip navigation utility pages
            skip = ["/contacts/", "/customer-tools/", "/services-and-solutions/",
                    "/login", "/register", "/search", "/sitemap"]
            if not any(s in parsed.path for s in skip):
                articles.append(full)

    return list(dict.fromkeys(articles))


def _scrape_article(url, visited):
    if url in visited or is_downloaded(url):
        return None
    visited.add(url)

    resp = _get(url)
    if not resp:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-2]

    text = _extract_text_from_soup(soup)
    words = text.split()
    if len(words) < 100:
        return None

    record = {
        "url": url,
        "title": title,
        "text": text,
        "word_count": len(words),
        "source": SOURCE_NAME,
        "scraped_at": datetime.datetime.utcnow().isoformat(),
    }
    return record


def run():
    init_db()
    visited = set()
    article_links = []

    # First pass: collect article links from all index pages
    for idx in INDEX_PAGES:
        links = _collect_article_links(idx, visited)
        for l in links:
            if l not in article_links:
                article_links.append(l)
        time.sleep(RATE_LIMIT)

    log.info("Candidate article URLs collected: %d", len(article_links))

    # Second pass: scrape articles
    saved = 0
    for url in article_links:
        if saved >= MAX_ARTICLES:
            break

        record = _scrape_article(url, set())
        if record:
            with open(JSONL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            mark_download_pending(url, SOURCE_NAME)
            mark_download_done(url, JSONL_FILE, "article", len(record["text"].encode()))
            log.info("[%d] %s (%d words)", saved + 1, record["title"][:60], record["word_count"])
            saved += 1

        # Also look for PDFs on each page
        resp = _get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if a["href"].lower().endswith(".pdf"):
                    pdf_url = urljoin(BASE_URL, a["href"])
                    if not is_downloaded(pdf_url):
                        try:
                            fname = pdf_url.split("/")[-1]
                            dest = OUT_PDF_DIR / fname
                            mark_download_pending(pdf_url, SOURCE_NAME)
                            pr = requests.get(pdf_url, headers=HEADERS, timeout=60, stream=True)
                            pr.raise_for_status()
                            n = 0
                            with open(dest, "wb") as f:
                                for chunk in pr.iter_content(8192):
                                    f.write(chunk)
                                    n += len(chunk)
                            fh = sha256_file(dest)
                            mark_download_done(pdf_url, dest, fh, n)
                            log.info("  PDF: %s (%.1f KB)", fname, n / 1024)
                        except Exception as exc:
                            log.warning("  PDF FAIL %s: %s", pdf_url, exc)
                            mark_download_failed(pdf_url, str(exc))

        time.sleep(RATE_LIMIT)

    log.info("Done. Articles saved: %d", saved)


if __name__ == "__main__":
    run()
