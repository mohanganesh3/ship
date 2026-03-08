#!/usr/bin/env python3
"""
Bunkering Checklist + Drydocking Checklist + Master Override procedural scraper.
Sources:
  - OCIMF/ICS Bunker Fuel Checklist guidance (open summaries)
  - Marine Insight bunkering procedure articles
  - CHIRP bunkering alerts
  - Gard bunkering publications
  - MARPOL BDN / flowmeter requirements (open)
  - Drydock: IACS unified requirements (open summaries)
  - BIMCO drydocking guidance
  - Master override: ISM Code clause 8 (IMO free text)
"""
import requests, json, os, time, re
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "extracted_text")
OUT_BUNKER = os.path.join(DATA_DIR, "bunkering_checklist.jsonl")
OUT_DRYCK  = os.path.join(DATA_DIR, "drydocking_checklist.jsonl")
OUT_MO     = os.path.join(DATA_DIR, "master_override.jsonl")
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

# ===== BUNKERING CHECKLIST =====
print("\n=== BUNKERING CHECKLIST ===")
bunk_sources = [
    ("https://www.marineinsight.com/guidelines/bunkering-checklist-on-ships/", "Marine Insight Bunkering Checklist"),
    ("https://www.marineinsight.com/guidelines/bunkering-procedure-on-ships/", "Marine Insight Bunkering Procedure"),
    ("https://www.marineinsight.com/guidelines/pre-bunkering-checklist/", "Marine Insight Pre-Bunkering Checklist"),
    ("https://www.marineinsight.com/guidelines/bunker-fuel-sampling/", "Marine Insight Bunker Fuel Sampling"),
    ("https://www.marineinsight.com/guidelines/bunkering-safety/", "Marine Insight Bunkering Safety"),
    ("https://www.marineinsight.com/guidelines/marpol-bdn/", "Marine Insight MARPOL BDN"),
    ("https://www.marineinsight.com/guidelines/how-to-read-bunker-delivery-note/", "Marine Insight Read BDN"),
    ("https://www.marineinsight.com/guidelines/bunkering-spill-prevention/", "Marine Insight Bunker Spill Prevention"),
    ("https://safety4sea.com/cm-best-bunkering-practices/", "Safety4Sea Best Bunkering Practices"),
    ("https://safety4sea.com/bunkering-checklist/", "Safety4Sea Bunkering Checklist"),
    ("https://www.gard.no/web/updates/content/20639063/bunkering-precautions", "Gard Bunkering Precautions"),
    ("https://www.gard.no/web/updates/content/20639063/bunker-fuel-quality", "Gard Bunker Quality"),
    ("https://gcaptain.com/?s=bunkering+checklist", "gCaptain Bunkering Checklist"),
    ("https://gcaptain.com/?s=bunkering+procedure", "gCaptain Bunkering Procedure"),
    ("https://www.chirpmaritime.org/?s=bunkering", "CHIRP Bunkering Alerts"),
    ("https://en.wikipedia.org/wiki/Bunkering", "Wikipedia Bunkering"),
    # IMO MARPOL flowmeter / BDN requirements
    ("https://www.imo.org/en/OurWork/Environment/Pages/Bunkering.aspx", "IMO Bunkering Page"),
    # International Bunker Industry Association (IBIA)
    ("https://ibia.net/resources/bunkering-guides/", "IBIA Bunkering Guides"),
    ("https://ibia.net/bunkering/procedures/", "IBIA Bunkering Procedures"),
    # VPS fuel testing
    ("https://www.vps-qsl.com/bunkering-best-practices/", "VPS Bunkering Best Practices"),
    # BIMCO
    ("https://www.bimco.org/education-and-training/seaguide/fuel-oil/bunkering", "BIMCO Bunkering Guide"),
]

bunk_count = 0
with open(OUT_BUNKER, "w", encoding="utf-8") as f:
    for url, title in bunk_sources:
        text = scrape(url, title)
        bunk_count += save(f, text, title, url, "Bunkering checklist")
        time.sleep(DELAY)

print(f"\n✅ Bunkering: {bunk_count} docs → {OUT_BUNKER}")

# ===== DRYDOCKING CHECKLIST =====
print("\n=== DRYDOCKING CHECKLIST ===")
dry_sources = [
    ("https://www.marineinsight.com/guidelines/dry-docking-procedure-of-ships/", "Marine Insight Drydocking Procedure"),
    ("https://www.marineinsight.com/guidelines/pre-drydock-checklist/", "Marine Insight Pre-Drydock Checklist"),
    ("https://www.marineinsight.com/guidelines/ship-drydocking-procedure/", "Marine Insight Ship Drydocking"),
    ("https://www.marineinsight.com/guidelines/entering-drydock/", "Marine Insight Entering Drydock"),
    ("https://www.marineinsight.com/guidelines/drydock-planning/", "Marine Insight Drydock Planning"),
    ("https://www.marineinsight.com/guidelines/special-survey/", "Marine Insight Special Survey"),
    ("https://www.marineinsight.com/guidelines/dry-dock-report/", "Marine Insight Drydock Report"),
    ("https://safety4sea.com/cm-dry-docking/", "Safety4Sea Dry Docking"),
    ("https://gcaptain.com/?s=drydocking", "gCaptain Drydocking Articles"),
    ("https://www.chirpmaritime.org/?s=drydock", "CHIRP Drydock Alerts"),
    ("https://en.wikipedia.org/wiki/Drydock", "Wikipedia Drydock"),
    ("https://www.gard.no/web/updates/content/20639120/dry-docking", "Gard Dry Docking"),
    # Class society guidance pages
    ("https://www.dnv.com/services/drydocking-and-special-surveys/", "DNV Drydocking Services"),
    ("https://www.lr.org/en/marine/surveys-and-inspections/drydocking/", "Lloyd's Register Drydocking"),
    # BIMCO
    ("https://www.bimco.org/education-and-training/seaguide/maintenance/dry-docking", "BIMCO Drydocking"),
    # Ship Inspection Report Programme (SIRE) on drydock items
    ("https://www.ocimf.org/programmes/sire/", "OCIMF SIRE Drydocking"),
]

dry_count = 0
with open(OUT_DRYCK, "w", encoding="utf-8") as f:
    for url, title in dry_sources:
        text = scrape(url, title)
        dry_count += save(f, text, title, url, "Drydocking checklist")
        time.sleep(DELAY)

print(f"\n✅ Drydocking: {dry_count} docs → {OUT_DRYCK}")

# ===== MASTER'S OVERRIDE =====
print("\n=== MASTER OVERRIDE ===")
mo_sources = [
    ("https://www.marineinsight.com/guidelines/master-override-on-ships/", "Marine Insight Master Override"),
    ("https://www.marineinsight.com/guidelines/masters-responsibilities-on-ships/", "Marine Insight Master Responsibilities"),
    ("https://www.marineinsight.com/guidelines/ism-code-requirements/", "Marine Insight ISM Code"),
    ("https://safety4sea.com/cm-master-override/", "Safety4Sea Master Override"),
    ("https://safety4sea.com/masters-authority-ships/", "Safety4Sea Master Authority"),
    ("https://www.gard.no/web/updates/content/20639138/masters-authority", "Gard Master Authority"),
    ("https://www.chirpmaritime.org/?s=master+override", "CHIRP Master Override Alerts"),
    ("https://www.chirpmaritime.org/?s=just+culture", "CHIRP Just Culture"),
    # ISM Code text (IMO free)
    ("https://www.imo.org/en/OurWork/HumanElement/Pages/ISMCode.aspx", "IMO ISM Code Page"),
    ("https://en.wikipedia.org/wiki/International_Safety_Management_Code", "Wikipedia ISM Code"),
    # STCW Master authority reference
    ("https://www.imo.org/en/OurWork/HumanElement/Pages/STCW-Convention.aspx", "IMO STCW Convention"),
    # CHIRP report on pressure on master
    ("https://www.chirpmaritime.org/?s=pressure+master", "CHIRP Pressure on Master"),
    ("https://gcaptain.com/?s=master+override", "gCaptain Master Override"),
    ("https://gcaptain.com/?s=master+authority", "gCaptain Master Authority"),
    # MAIB reports where master authority was relevant
    ("https://www.gov.uk/maib-reports?keywords=master+override", "MAIB Master Override Reports"),
]

mo_count = 0
with open(OUT_MO, "w", encoding="utf-8") as f:
    for url, title in mo_sources:
        text = scrape(url, title)
        mo_count += save(f, text, title, url, "Master override")
        time.sleep(DELAY)

print(f"\n✅ Master Override: {mo_count} docs → {OUT_MO}")
print(f"\n=== TOTAL: Bunkering={bunk_count}, Drydocking={dry_count}, MasterOverride={mo_count} ===")
