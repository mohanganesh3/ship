#!/usr/bin/env python3
"""
FWG (Fresh Water Generator) + Tank Gauging/Ullage procedural scraper.
Sources:
  - Marine Insight FWG articles (open)
  - Alfa Laval / Wartsila open tech notes
  - YouTube transcripts (via yt-dlp if available)
  - Safety4Sea FWG articles
  - CHIRP FWG alerts
  - IMO/WHO marine potable water guidance
  - Tank gauging: OCIMF guidelines (open summaries)
  - Marine Insight ullage/gauging articles
  - gCaptain technical articles
"""
import requests, json, os, time, re, subprocess, shutil
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "extracted_text")
OUT_FWG = os.path.join(DATA_DIR, "fwg_procedures.jsonl")
OUT_GAUGE = os.path.join(DATA_DIR, "tank_gauging.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
DELAY = 2.0

session = requests.Session()
session.headers.update(HEADERS)

def scrape(url, label=""):
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","nav","footer","header","aside"]):
            t.decompose()
        text = " ".join(soup.get_text(" ", strip=True).split())
        ok = "✓" if len(text) > 200 else "✗"
        print(f"  {ok} {label}: {len(text):,} chars")
        return text
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        return ""

def save(fh, text, title, url, topic):
    if len(text) < 200:
        return 0
    fh.write(json.dumps({"title": title, "source": url, "topic": topic,
                          "text": text, "scraped_at": datetime.utcnow().isoformat()}) + "\n")
    return 1

# ===== FRESH WATER GENERATOR =====
print("\n=== FRESH WATER GENERATOR (FWG) ===")
fwg_sources = [
    ("https://www.marineinsight.com/guidelines/fresh-water-generator-on-ships/", "Marine Insight FWG on Ships"),
    ("https://www.marineinsight.com/guidelines/how-does-a-freshwater-generator-work-on-ships/", "Marine Insight FWG How it Works"),
    ("https://www.marineinsight.com/guidelines/fresh-water-generator-maintenance/", "Marine Insight FWG Maintenance"),
    ("https://www.marineinsight.com/guidelines/evaporator-on-ships/", "Marine Insight Ship Evaporator"),
    ("https://www.marineinsight.com/guidelines/fresh-water-generator-starting-procedure/", "Marine Insight FWG Starting Procedure"),
    ("https://www.marineinsight.com/guidelines/fresh-water-generator-salinometer/", "Marine Insight FWG Salinometer"),
    ("https://www.marineinsight.com/guidelines/fresh-water-generator-problems/", "Marine Insight FWG Problems"),
    ("https://www.marineinsight.com/guidelines/potable-water-on-ships/", "Marine Insight Potable Water"),
    ("https://en.wikipedia.org/wiki/Flash_evaporator", "Wikipedia Flash Evaporator"),
    ("https://en.wikipedia.org/wiki/Multi-effect_distillation", "Wikipedia Multi-Effect Distillation"),
    ("https://safety4sea.com/cm-fresh-water-generator/", "Safety4Sea FWG"),
    ("https://www.cfd-online.com/Forums/marine/", "CFD Online Marine Engineering Forum"),
    ("https://www.marineengineering.org.uk/", "Marine Engineering UK"),
    ("https://www.dieselduck.info/machine/01%20prime%20movers/freshwater%20generator.htm", "DieselDuck FWG"),
    # WHO shipboard water guide
    ("https://www.who.int/water_sanitation_health/hygiene/emergencies/shipboard_water.pdf", "WHO Shipboard Water Safety"),
    # CHIRP alerts on FWG/potable water
    ("https://www.chirpmaritime.org/?s=fresh+water+generator", "CHIRP FWG Alerts"),
    ("https://www.chirpmaritime.org/?s=potable+water", "CHIRP Potable Water Alerts"),
    # gCaptain
    ("https://gcaptain.com/?s=fresh+water+generator", "gCaptain FWG Articles"),
    # Alfa Laval open resources
    ("https://www.alfalaval.com/globalassets/documents/industries/marine-and-offshore/freshwater-generators-brochure.pdf",
     "Alfa Laval FWG Brochure"),
    # WARTSILA encyclopedia
    ("https://www.wartsila.com/encyclopedia/term/freshwater-generator-(fwg)", "Wartsila Encyclopedia FWG"),
]

fwg_count = 0
with open(OUT_FWG, "w", encoding="utf-8") as f:
    for url, title in fwg_sources:
        text = scrape(url, title)
        fwg_count += save(f, text, title, url, "FWG startup procedure")
        time.sleep(DELAY)

print(f"\n✅ FWG: {fwg_count} docs → {OUT_FWG}")

# ===== TANK GAUGING / ULLAGE =====
print("\n=== TANK GAUGING / ULLAGE ===")
gauge_sources = [
    ("https://www.marineinsight.com/guidelines/tank-gauging-on-ships/", "Marine Insight Tank Gauging"),
    ("https://www.marineinsight.com/guidelines/crude-oil-tanker-cargo-operations/", "Marine Insight Tanker Cargo Ops"),
    ("https://www.marineinsight.com/guidelines/ullage-and-innage-of-cargo-tanks-on-a-tanker/", "Marine Insight Ullage and Innage"),
    ("https://www.marineinsight.com/guidelines/oil-tanker-port-operations/", "Marine Insight Tanker Port Operations"),
    ("https://www.marineinsight.com/guidelines/venting-cargo-tanks-on-tankers/", "Marine Insight Tank Venting"),
    ("https://www.marineinsight.com/guidelines/cargo-calculations-on-tanker-ships/", "Marine Insight Cargo Calculations"),
    ("https://en.wikipedia.org/wiki/Tank_gauging", "Wikipedia Tank Gauging"),
    ("https://en.wikipedia.org/wiki/Ullage", "Wikipedia Ullage"),
    ("https://safety4sea.com/cm-cargo-measurement-tankers/", "Safety4Sea Cargo Measurement"),
    ("https://gcaptain.com/?s=tank+gauging", "gCaptain Tank Gauging Articles"),
    ("https://gcaptain.com/?s=ullage", "gCaptain Ullage Articles"),
    # Emerson CTG / Enraf (open resources)
    ("https://www.emerson.com/en-us/expertise/marine-vessel-measuring-and-monitoring", "Emerson Marine Tank Measurement"),
    # CHIRP
    ("https://www.chirpmaritime.org/?s=ullage", "CHIRP Ullage Alerts"),
    ("https://www.chirpmaritime.org/?s=tank+gauging", "CHIRP Tank Gauging Alerts"),
    # IMO MEPC text on cargo measurement (open)
    ("https://www.imo.org/en/OurWork/Environment/Pages/TankCleaning.aspx", "IMO Tank Cleaning Page"),
    # Wartsila
    ("https://www.wartsila.com/encyclopedia/term/ullage", "Wartsila Encyclopedia Ullage"),
    ("https://www.wartsila.com/encyclopedia/term/cargo-tank", "Wartsila Encyclopedia Cargo Tank"),
]

gauge_count = 0
with open(OUT_GAUGE, "w", encoding="utf-8") as f:
    for url, title in gauge_sources:
        text = scrape(url, title)
        gauge_count += save(f, text, title, url, "Tank gauging / ullage")
        time.sleep(DELAY)

print(f"\n✅ Tank Gauging: {gauge_count} docs → {OUT_GAUGE}")
print(f"\n=== TOTAL: FWG={fwg_count}, Tank Gauging={gauge_count} ===")
