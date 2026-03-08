#!/usr/bin/env python3
"""
openalex_maritime3_scraper.py - Third wave of academic papers via OpenAlex API.

More specialized maritime queries covering cruise industry, offshore operations,
dredging, naval vessels, underwater technology, port infrastructure, etc.

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
        logging.FileHandler(LOGS_DIR / "openalex3_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("openalex3")

OPENALEX_BASE = "https://api.openalex.org/works"
JSONL_FILE    = Path(__file__).parent.parent / "data" / "extracted_text" / "openalex_maritime3.jsonl"
RATE_LIMIT    = 2.0  # Increased to avoid 429 conflicts with OA2 running in parallel
MAX_PER_QUERY = 500

# Third wave of queries - different focus areas
QUERIES = [
    # Ship technology and innovation
    "autonomous vessel unmanned ship technology",
    "fuel cell hydrogen ship propulsion",
    "battery electric ferry hybrid vessel",
    "wind sail kite propulsion vessel",
    "air lubrication system drag reduction hull",
    "hull fouling biofouling antifouling coating",
    "ship noise underwater acoustic emission",
    "ship vibration machinery condition monitoring",
    "predictive maintenance ship machinery remote",
    "digital twin ship operations simulation",
    # Port infrastructure
    "port automation container crane handling",
    "berth allocation ship scheduling optimization",
    "fairway channel depth dredging",
    "port security maritime cybersecurity threat",
    "shore power cold ironing vessel emission",
    "port waste management ship garbage",
    "breakwater harbor design wave protection",
    # Ocean and environment
    "microplastic pollution ocean shipping",
    "underwater noise whale shipping conservation",
    "coral reef shipping damage assessment",
    "green shipping decarbonization pathway",
    "carbon capture ship direct air",
    "methanol ammonia marine fuel ship",
    "biofuel ship alternative fuel sustainability",
    # Offshore energy
    "offshore wind turbine installation vessel",
    "cable laying vessel subsea operations",
    "offshore platform mooring system design",
    "FPSO floating production storage offloading",
    "jack-up rig drilling platform stability",
    "dynamic positioning vessel control system",
    "underwater ROV inspection pipeline",
    # Safety culture and human factors
    "bridge team resource management maritime",
    "maritime education training competence",
    "fatigue management seafarer sleep",
    "near miss reporting maritime safety culture",
    "maritime accident root cause analysis",
    "ISM code implementation safety management ship",
    # Regulation and compliance
    "STCW competency standard seafarer training",
    "port state control deficiency detention flag",
    "carbon intensity indicator CII ship rating",
    "energy efficiency design index EEDI ship",
    "nitrogen oxide sulfur scrubber ship emission",
    "ballast water treatment IMO regulation",
    "ship recycling Hong Kong convention",
    # Oceanographic and routing
    "ocean weather routing voyage optimization",
    "sea state wave height ship response",
    "ice class ship Arctic polar operations",
    "tsunami propagation coastal inundation harbor",
    "typhoon tropical cyclone vessel avoidance",
    "current drift search rescue maritime",
    "oil spill fate weathering marine environment",
    # Naval and defense
    "naval ship stability damage control",
    "coast guard patrol vessel operations",
    "military sea transport amphibious operations",
    "submarine pressure hull design",
    "mine countermeasure vessel naval",
]


def _reconstruct_abstract(inverted_index):
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(w for _, w in word_positions)


def _fetch_page(query, cursor="*"):
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
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            log.warning("API error attempt %d: %s", attempt + 1, exc)
            time.sleep(RATE_LIMIT * 4)
    return None


def run():
    init_db()
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

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

                    abstract = _reconstruct_abstract(
                        work.get("abstract_inverted_index") or {}
                    )
                    if not abstract or len(abstract.split()) < 50:
                        continue

                    title = work.get("display_name", "")
                    year = work.get("publication_year")
                    authors = [
                        a.get("author", {}).get("display_name", "")
                        for a in work.get("authorships", [])[:5]
                    ]
                    primary_location = work.get("primary_location") or {}
                    source = primary_location.get("source") or {}
                    venue = source.get("display_name", "")

                    text = f"{title}\n{venue}\n\n{abstract}" if venue else f"{title}\n\n{abstract}"

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
