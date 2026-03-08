#!/usr/bin/env python3
"""
wikipedia_maritime2_scraper.py - Expanded Wikipedia maritime article scraper.

Covers maritime topics NOT in the original wikipedia_scraper including:
- Ship types (LNG carriers, bulk carriers, tankers, etc.)
- Historical maritime topics
- Navigation equipment and systems
- Maritime law and conventions
- Ports, waterways, and maritime geography
- Marine biology and oceanography
- Shipping companies and history

Output: JSONL with article text for training.
"""

import sys, time, json, logging
from pathlib import Path

import wikipediaapi

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LOGS_DIR, DEFAULT_RATE_LIMIT_SECONDS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "wikipedia2_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("wiki2")

JSONL_FILE = Path(__file__).parent.parent / "data" / "extracted_text" / "wikipedia_maritime2.jsonl"
RATE_LIMIT = 1.0

# Extensive list of maritime Wikipedia topics
MARITIME_TOPICS = [
    # Ship types and vessel classification
    "LNG carrier", "VLCC", "Suezmax", "Aframax", "Panamax",
    "Container ship", "Bulk carrier", "Tanker", "Chemical tanker",
    "Product tanker", "Crude oil tanker", "Very large crude carrier",
    "Roll-on/roll-off", "Passenger ship", "Cruise ship", "Ferry",
    "Ro-ro ship", "LASH vessel", "OBO ship", "Heavy-lift vessel",
    "Cable layer", "Pipe-laying vessel", "Crane vessel",
    "Dredger", "Harbor tug", "Offshore supply vessel",
    "Anchor handling tug supply vessel", "Platform supply vessel",
    "Drillship", "Semi-submersible", "Jack-up rig",
    "FPSO", "Flotel", "Accommodation vessel", "Construction vessel",
    "Ice breaker", "Research vessel", "Survey vessel",
    "Training ship", "Hospital ship",

    # Navigation and systems
    "Automatic Identification System", "ECDIS",
    "Radar (maritime)", "ARPA (maritime)", "AIS Class B",
    "Very-high-frequency omnidirectional range", "Loran",
    "GPS navigation", "Inertial navigation system",
    "Electronic chart", "Paper chart (navigation)", "Nautical chart",
    "Sextant", "Compass", "Gyrocompass", "Magnetic compass",
    "GMDSS", "EPIRB", "SART", "DSC (maritime)",
    "VHF radio", "MF/HF radio", "Satellite communication",
    "Inmarsat", "Iridium satellite constellation",

    # Safety equipment and procedures
    "Life raft", "Lifeboat", "SOLAS", "Life jacket",
    "Immersion suit", "Fire extinguisher (maritime)",
    "Officer of the watch", "Navigation watch",
    "Bridge resource management", "Crew resource management",
    "Pilot (maritime)", "Helmsman",
    "Emergency position-indicating radiobeacon",
    "Search and rescue transponder",
    "International safety management code",
    "Safety management system",

    # Maritime law and regulation
    "MARPOL", "UNCLOS", "STCW Convention",
    "Maritime Labour Convention", "ISM Code",
    "Load line", "Plimsoll line", "Gross tonnage",
    "Net register tonnage", "Deadweight tonnage",
    "Flag state", "Port state control",
    "Classification society", "Marine surveyorship",
    "P&I Club", "Marine insurance", "Hull insurance",
    "Cargo insurance", "Salvage (maritime law)",
    "General average", "Maritime lien", "Bill of lading",
    "Charter party", "Demurrage", "Laytime",

    # Ports and waterways
    "Port of Singapore", "Port of Rotterdam",
    "Port of Shanghai", "Port of Los Angeles",
    "Port of Long Beach", "Port of Hamburg",
    "Suez Canal", "Panama Canal", "Kiel Canal",
    "Strait of Malacca", "English Channel",
    "Dover Strait", "Cape of Good Hope", "Cape Horn",
    "Drake Passage", "Strait of Gibraltar",
    "Bosphorus", "Strait of Hormuz",
    "Northwest Passage", "Northeast Passage",
    "Port State Control", "Deep water port",
    "Container terminal", "Roll-on/roll-off terminal",
    "Dry dock", "Floating dry dock",

    # Propulsion and engineering
    "Marine diesel engine", "Two-stroke diesel engine",
    "Four-stroke diesel engine", "Gas turbine (maritime)",
    "Steam turbine (maritime)", "Nuclear marine propulsion",
    "Ship propeller", "Fixed pitch propeller",
    "Controllable pitch propeller", "Azimuth thruster",
    "Voith Schneider propeller", "Bow thruster",
    "Stern thruster", "Waterjet", "Paddlewheel",
    "Ship resistance", "Froude number",
    "Bulbous bow", "Stern shape",
    "Double bottom", "Ballast tank", "Cargo hold",
    "Cargo tank", "Cofferdam", "Void space",

    # Cargo operations
    "Cargo handling", "Loading", "Discharging",
    "Stevedore", "Cargo plan", "Stability calculation",
    "Lashing (cargo)", "Container", "TEU",
    "Break bulk cargo", "Ro-ro cargo", "Liquid bulk",
    "Dry bulk", "Heavy lift cargo", "Dangerous goods",
    "IMDG Code", "Hazmat",

    # Marine environment
    "Marine pollution", "Oil spill",
    "Ballast water", "Antifouling paint",
    "Marine debris", "Underwater noise pollution",
    "IMO 2020", "Sulfur cap",
    "Carbon intensity indicator",
    "Energy efficiency design index",
    "Ship recycling", "Hong Kong Convention",
    "Beaching (ship recycling)",

    # Maritime history and famous events
    "RMS Titanic", "MV Doña Paz", "MV Estonia",
    "MV Herald of Free Enterprise",
    "SS Edmund Fitzgerald", "MV Prestige",
    "Exxon Valdez oil spill",
    "Costa Concordia disaster",
    "Marine accident investigation",
    "Blackwall Hitch", "Splice (rope)",
    "Knot (unit)", "Nautical mile",

    # Oceanography
    "Ocean current", "Gulf Stream", "Kuroshio Current",
    "Thermohaline circulation", "Tsunami",
    "Storm surge", "Tides", "Swell (ocean)",
    "Beaufort scale", "Sea state",
    "Wave power", "Rogue wave",
]


def _get_wiki():
    return wikipediaapi.Wikipedia(
        user_agent="MaritimeAIResearcher/1.0 (maritimeai@example.com)",
        language="en",
    )


def _fetch_article(wiki, title):
    try:
        page = wiki.page(title)
        if not page.exists():
            log.warning("Page not found: %s", title)
            return None
        text = page.text
        word_count = len(text.split())
        if word_count < 100:
            log.info("Skip short: %s (%d words)", title, word_count)
            return None
        return {
            "url": page.fullurl,
            "title": page.title,
            "text": text,
            "word_count": word_count,
            "source": "wikipedia",
        }
    except Exception as exc:
        log.warning("Error fetching %s: %s", title, exc)
        return None


def run():
    JSONL_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load seen URLs to skip duplicates
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

    # Also load URLs from the original wiki file
    orig_wiki = JSONL_FILE.parent / "wikipedia_maritime.jsonl"
    if orig_wiki.exists():
        with open(orig_wiki, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if "url" in d:
                        seen_urls.add(d["url"])
                except Exception:
                    pass

    log.info("Loaded %d seen URLs", len(seen_urls))
    wiki = _get_wiki()

    saved = failed = skipped = 0

    with open(JSONL_FILE, "a", encoding="utf-8") as jf:
        for topic in MARITIME_TOPICS:
            article = _fetch_article(wiki, topic)
            if article is None:
                failed += 1
                time.sleep(RATE_LIMIT)
                continue

            if article["url"] in seen_urls:
                skipped += 1
                time.sleep(RATE_LIMIT * 0.3)
                continue

            seen_urls.add(article["url"])
            jf.write(json.dumps(article, ensure_ascii=False) + "\n")
            jf.flush()
            log.info("Saved: %s (%d words)", article["title"], article["word_count"])
            saved += 1
            time.sleep(RATE_LIMIT)

    log.info("Done. Saved=%d Failed=%d Skipped=%d", saved, failed, skipped)


if __name__ == "__main__":
    run()
