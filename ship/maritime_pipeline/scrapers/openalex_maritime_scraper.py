#!/usr/bin/env python3
"""
openalex_maritime_scraper.py - Fetch maritime research paper abstracts + full texts via OpenAlex API.

OpenAlex is fully free and open. It contains millions of academic papers.
We query for maritime/shipping/IMO/vessel safety papers and save abstracts + text.

Target: papers in maritime engineering, ship safety, marine pollution, navigation.
These will add scientifically rigorous content for the CPT corpus.

Usage:
    cd maritime_pipeline
    python scrapers/openalex_maritime_scraper.py
"""

import sys, re, time, json, logging
import datetime
from pathlib import Path
from urllib.parse import urlencode

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import (
    init_db, is_downloaded, mark_download_pending,
    mark_download_done, mark_download_failed,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "openalex_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("openalex")

SOURCE_NAME = "openalex"
JSONL_FILE  = Path(__file__).parent.parent / "data" / "extracted_text" / "openalex_maritime.jsonl"
JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)
RATE_LIMIT  = 1.0  # OpenAlex is fast and allows ~10 req/s with API key

API_BASE = "https://api.openalex.org/works"

# Maritime-focused search queries
QUERIES = [
    "maritime safety",
    "ship collision accident",
    "marine pollution prevention",
    "SOLAS convention",
    "MARPOL shipping",
    "seafarer training STCW",
    "vessel navigation safety",
    "maritime incident investigation",
    "ship fire explosion",
    "bulk carrier safety",
    "tanker safety oil spill",
    "container ship accident",
    "port state control",
    "maritime flag state",
    "loss of stability ship",
    "marine engineering machinery",
    "crew fatigue maritime",
    "piracy maritime security",
    "autonomous ship vessel",
    "maritime decarbonization shipping",
    "hull structural integrity",
    "ship grounding stranding",
    "man overboard maritime",
    "lifeboat davit maritime",
    "ballast water management",
    "shore-based maritime monitoring",
    "ecdis navigation electronic chart",
    "AIS vessel tracking",
    "VHF radio maritime",
    "GMDSS distress safety",
    "maritime rescue coordination",
    "oil tanker mooring",
    "dry dock inspection survey",
    "classification society rules",
    "international maritime law",
]

HEADERS = {
    "User-Agent": "maritimeAI-data-collection/1.0 (research; contact@example.com)",
    "Accept": "application/json",
}


def _fetch_page(query: str, cursor: str = "*", per_page: int = 100):
    """Fetch one page of OpenAlex results."""
    params = {
        "search": query,
        "per-page": per_page,
        "cursor": cursor,
        # Note: don't use 'select' - it breaks cursor pagination with filter
        # Note: don't use 'filter=has_abstract:true' - returns 0 with select
        # Just use search and filter client-side
    }
    url = API_BASE + "?" + urlencode(params)
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            log.warning("API request attempt %d failed: %s", attempt + 1, exc)
            time.sleep(RATE_LIMIT * 3)
    return None


def _reconstruct_abstract(inverted_index: dict) -> str:
    """OpenAlex stores abstracts as inverted index: {word: [positions]}."""
    if not inverted_index:
        return ""
    # Convert to list of (word, position) pairs
    word_pos = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_pos.append((pos, word))
    word_pos.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_pos)


def _process_query(query: str, max_results: int = 500):
    """Fetch up to max_results papers for a query."""
    log.info("Query: %s (max %d)", query, max_results)
    cursor = "*"
    collected = 0

    while collected < max_results:
        data = _fetch_page(query, cursor=cursor)
        if not data:
            break

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            work_id = work.get("id", "")
            if not work_id or is_downloaded(work_id):
                continue

            abstract_inv = work.get("abstract_inverted_index", {})
            abstract = _reconstruct_abstract(abstract_inv)
            if len(abstract.split()) < 50:
                continue

            title = work.get("title", "")
            year = work.get("publication_year", "")
            doi = work.get("doi", "")

            # Try to get open access URL for full text
            oa = work.get("open_access", {})
            oa_url = oa.get("oa_url", "")

            text = f"Title: {title}\n\nYear: {year}\n\nDOI: {doi}\n\nAbstract:\n{abstract}"

            record = {
                "url": work_id,
                "title": title,
                "text": text,
                "year": year,
                "doi": doi,
                "oa_url": oa_url,
                "query": query,
                "source": SOURCE_NAME,
                "scraped_at": datetime.datetime.utcnow().isoformat(),
            }

            with open(JSONL_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            mark_download_pending(work_id, SOURCE_NAME)
            mark_download_done(work_id, JSONL_FILE, "abstract", len(text.encode()))
            collected += 1

        # Get next cursor
        meta = data.get("meta", {})
        next_cursor = meta.get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor
        time.sleep(RATE_LIMIT)

    log.info("Query '%s': collected %d papers", query, collected)
    return collected


def run():
    init_db()
    total = 0

    for query in QUERIES:
        n = _process_query(query, max_results=500)
        total += n
        time.sleep(RATE_LIMIT * 2)

    log.info("Done. Total papers collected: %d", total)


if __name__ == "__main__":
    run()
