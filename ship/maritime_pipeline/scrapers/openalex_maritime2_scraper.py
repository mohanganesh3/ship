#!/usr/bin/env python3
"""
openalex_maritime2_scraper.py - Second wave of academic papers via OpenAlex API.

Extends openalex_maritime_scraper.py with additional specialized queries
covering different aspects of maritime: propulsion, naval architecture,
port operations, ocean engineering, ship design, etc.

Source: https://api.openalex.org/works

CRITICAL: Do NOT use `select=` param or `filter=has_abstract:true` --
those break cursor pagination and return count=0 from the API.
"""

import sys, time, json, logging
from pathlib import Path
from urllib.parse import urlencode

import requests

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
        logging.FileHandler(LOGS_DIR / "openalex2_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("openalex2")

OPENALEX_BASE = "https://api.openalex.org/works"
JSONL_FILE    = Path(__file__).parent.parent / "data" / "extracted_text" / "openalex_maritime2.jsonl"
RATE_LIMIT    = 1.5  # Increased slightly to reduce 429 rate limit conflicts
MAX_PER_QUERY = 500  # max papers per query

# Additional maritime-relevant queries NOT in the first scraper
QUERIES = [
    # Naval architecture and design
    "ship hull design resistance",
    "vessel stability metacentric height",
    "ship structural analysis finite element",
    "vessel seakeeping wave loads motions",
    "ship propeller cavitation efficiency",
    "marine diesel engine efficiency emissions",
    "naval architecture design optimization",
    # Port and logistics
    "port container terminal efficiency",
    "shipping logistics supply chain management",
    "vessel port state inspection deficiency",
    "container ship stowage planning",
    "port congestion vessel waiting time",
    "bulk carrier loading operations",
    "tanker cargo loading discharge",
    # Safety and accidents
    "ship grounding accident cause",
    "vessel flooding stability accident",
    "fire suppression ship fixed system",
    "explosion ship accident investigation",
    "rescue survival immersion suit",
    "maritime accident human error",
    "ship capsize accident cause analysis",
    # Environmental and regulatory
    "ballast water invasive species shipping",
    "ship air pollution nitrogen oxide sulfur",
    "LNG liquefied gas carrier safety",
    "offshore platform safety management",
    "submarine pipeline inspection maintenance",
    "wave energy converter marine renewable",
    # Navigation and communication
    "ship radar collision avoidance ARPA",
    "electronic chart display ECDIS navigation",
    "vessel traffic service VTS monitoring",
    "automatic identification system AIS vessel",
    "celestial navigation astronomy maritime",
    # Crew and operations
    "seafarer fatigue watch schedule",
    "crew training maritime simulator",
    "International Safety Management ISM Code",
    "maritime labour convention seafarer",
    "ship management safety culture",
    # Oceanography and metocean
    "ocean current wave prediction forecast",
    "tsunami wave coastal marine",
    "Arctic shipping ice navigation route",
    "tropical cyclone track shipping",
    "marine weather routing voyage optimization",
    # Specific ship types
    "cruise ship passenger safety evacuation",
    "ro-ro ferry vehicle deck fire ventilation",
    "fishing vessel safety stability fishing",
    "tug boat harbor assist operation",
    "dredging vessel marine construction",
    # Cargo and materials
    "dangerous goods IMDG code transport",
    "liquid bulk terminal cargo measurement",
    "grain cargo shift stability",
    "refrigerated cargo reefer container",
    # Emergency and response
    "marine oil spill response trajectory",
    "search rescue SOLAS lifesaving",
    "piracy maritime security counter",
    "ship salvage towage casualty",
]


def _reconstruct_abstract(inverted_index):
    """Reconstruct abstract text from OpenAlex inverted index format."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


def _fetch_page(query, cursor="*"):
    """Fetch one page of results from OpenAlex API."""
    params = {
        "search": query,
        "cursor": cursor,
        "per-page": 25,
        "mailto": "maritime-ai-research@example.com",
    }
    url = f"{OPENALEX_BASE}?{urlencode(params)}"
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=30, headers={"Accept": "application/json"})
            if r.status_code == 429:
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s...
                log.warning("Rate limited (429) attempt %d - waiting %ds", attempt + 1, wait_time)
                time.sleep(wait_time)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            log.warning("OpenAlex API error (attempt %d): %s", attempt + 1, exc)
            time.sleep(RATE_LIMIT * 4)
    return None


def _already_collected(url, seen_ids):
    """Check if paper ID already in this session."""
    return url in seen_ids


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load existing IDs to avoid duplicates
    seen_ids = set()
    if JSONL_FILE.exists():
        with open(JSONL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if "url" in d:
                        seen_ids.add(d["url"])
                except Exception:
                    pass
    log.info("Loaded %d existing paper IDs", len(seen_ids))

    total_saved = 0

    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for query in QUERIES:
            log.info("Query: %s (max %d)", query, MAX_PER_QUERY)
            cursor = "*"
            q_count = 0

            while q_count < MAX_PER_QUERY:
                data = _fetch_page(query, cursor)
                if not data:
                    break

                results = data.get("results", [])
                if not results:
                    break

                for work in results:
                    work_id = work.get("id", "")
                    if work_id in seen_ids:
                        continue
                    seen_ids.add(work_id)

                    # Extract abstract
                    abstract = _reconstruct_abstract(
                        work.get("abstract_inverted_index") or {}
                    )
                    if not abstract or len(abstract.split()) < 50:
                        continue

                    # Build record
                    title = work.get("display_name", "")
                    year = work.get("publication_year")
                    authors = [
                        a.get("author", {}).get("display_name", "")
                        for a in work.get("authorships", [])[:5]
                    ]
                    venue = ""
                    primary_location = work.get("primary_location") or {}
                    source = primary_location.get("source") or {}
                    venue = source.get("display_name", "")

                    text = f"{title}\n\n{abstract}"
                    if venue:
                        text = f"{title}\n{venue}\n\n{abstract}"

                    record = {
                        "url": work_id,
                        "title": title,
                        "text": text,
                        "abstract": abstract,
                        "year": year,
                        "authors": authors,
                        "venue": venue,
                        "word_count": len(abstract.split()),
                        "source": "openalex",
                        "query": query,
                    }
                    jf.write(json.dumps(record, ensure_ascii=False) + "\n")
                    jf.flush()
                    q_count += 1
                    total_saved += 1

                # Get next cursor
                meta = data.get("meta", {})
                next_cursor = meta.get("next_cursor")
                if not next_cursor or q_count >= MAX_PER_QUERY:
                    break
                cursor = next_cursor
                time.sleep(RATE_LIMIT)

            log.info("Query %r: collected %d papers (total: %d)", query, q_count, total_saved)
            time.sleep(RATE_LIMIT * 2)

    log.info("Done. Total papers saved: %d", total_saved)


if __name__ == "__main__":
    run()
