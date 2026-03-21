#!/usr/bin/env python3
"""
Crude Oil Washing (COW) + Enclosed Space Entry procedural scraper.
Sources:
  - MARPOL Annex I Reg 33 (COW requirements) — IMO free text
  - IMO MSC-MEPC.2/Circ.10 Revised Recommendations for Entering Enclosed Spaces
  - OCIMF/ICS/ISGOTT guidance summaries (open web)
  - Marine Insight COW procedure articles
  - CHIRP maritime alerts on enclosed space entry
  - Transport Canada TP 14212 Enclosed Spaces
  - MCA MGNs on enclosed space entry
  - Safety4Sea / Gard P&I articles
"""
import requests, json, os, time, re
from bs4 import BeautifulSoup
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "extracted_text")
OUT_COW = os.path.join(DATA_DIR, "cow_procedures.jsonl")
OUT_ESE = os.path.join(DATA_DIR, "enclosed_space_entry.jsonl")
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
        if len(text) > 200:
            print(f"  ✓ {label}: {len(text):,} chars")
        else:
            print(f"  ✗ {label}: too short")
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

cow_count = 0
ese_count = 0

# ===== CRUDE OIL WASHING =====
print("\n=== CRUDE OIL WASHING ===")
cow_sources = [
    # Marine Insight COW procedure articles
    ("https://www.marineinsight.com/guidelines/crude-oil-washing-system-on-tankers/", "Marine Insight COW System on Tankers"),
    ("https://www.marineinsight.com/guidelines/crude-oil-washing-cow-procedure-on-oil-tankers/", "Marine Insight COW Procedure on Oil Tankers"),
    ("https://www.marineinsight.com/guidelines/inert-gas-system-procedure/", "Marine Insight Inert Gas System Procedure"),
    ("https://www.marineinsight.com/guidelines/what-is-crude-oil-washing/", "Marine Insight What is Crude Oil Washing"),
    # Safety4Sea
    ("https://safety4sea.com/cm-crude-oil-washing-systems-and-operations/", "Safety4Sea COW Operations"),
    # Gard
    ("https://www.gard.no/web/publications/document/20639146/crude-oil-washing", "Gard COW Publication"),
    # Wikipedia
    ("https://en.wikipedia.org/wiki/Crude_oil_washing", "Wikipedia Crude Oil Washing"),
    # The Maritime Executive summaries on ISGOTT / COW
    ("https://maritime-executive.com/blog/crude-oil-washing", "Maritime Executive COW Blog"),
    # Transport Canada relevant guidance
    ("https://tc.canada.ca/en/marine-transportation/marine-safety/tp-11960e-marine-emergency-duties-med", "TC Marine Emergency Duties"),
    # ITOPF open technical documents
    ("https://www.itopf.org/knowledge-resources/documents-guides/", "ITOPF Documents Guides"),
    # gCaptain
    ("https://gcaptain.com/crude-oil-washing-tankers/", "gCaptain COW Tankers"),
    # CHIRP maritime
    ("https://www.chirpmaritime.org/?s=crude+oil+washing", "CHIRP COW Alerts"),
    ("https://www.chirpmaritime.org/?s=cow+tanker", "CHIRP COW Tanker Alerts"),
]

with open(OUT_COW, "w", encoding="utf-8") as f_cow:
    for url, title in cow_sources:
        text = scrape(url, title)
        cow_count += save(f_cow, text, title, url, "Crude oil washing procedure")
        time.sleep(DELAY)

    # Additional: IMO MEPC text on COW requirements (free)
    imo_cow_urls = [
        ("https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.1-Circ.811.pdf", "IMO MEPC Circ 811 COW"),
    ]
    for url, title in imo_cow_urls:
        text = scrape(url, title)
        cow_count += save(f_cow, text, title, url, "Crude oil washing procedure")
        time.sleep(DELAY)

print(f"\n✅ COW: {cow_count} docs → {OUT_COW}")

# ===== ENCLOSED SPACE ENTRY =====
print("\n=== ENCLOSED SPACE ENTRY ===")
ese_sources = [
    # IMO circular on enclosed spaces
    ("https://wwwcdn.imo.org/localresources/en/OurWork/HumanElement/Documents/MSC-MEPC.2-Circ.10.pdf",
     "IMO MSC-MEPC.2-Circ.10 Enclosed Spaces"),
    # Marine Insight
    ("https://www.marineinsight.com/guidelines/enclosed-space-entry-procedure-on-ships/", "Marine Insight Enclosed Space Entry"),
    ("https://www.marineinsight.com/guidelines/safety-precautions-for-enclosed-spaces-on-ships/", "Marine Insight Enclosed Space Safety"),
    ("https://www.marineinsight.com/guidelines/what-is-permit-to-work-system-on-ships/", "Marine Insight Permit to Work"),
    ("https://www.marineinsight.com/guidelines/hot-work-permit-on-ships/", "Marine Insight Hot Work Permit"),
    ("https://www.marineinsight.com/safety/enclosed-space-entry-accidents-on-ships/", "Marine Insight Enclosed Space Accidents"),
    # Transport Canada TP 14212
    ("https://tc.canada.ca/en/marine-transportation/marine-safety/tp-14212e-confined-space-awareness", "TC TP 14212 Confined Space"),
    # CHIRP enclosed spaces
    ("https://www.chirpmaritime.org/?s=enclosed+space", "CHIRP Enclosed Space Alerts"),
    ("https://www.chirpmaritime.org/?s=permit+to+work", "CHIRP Permit to Work Alerts"),
    # Gard
    ("https://www.gard.no/web/updates/content/20840534/enclosed-spaces", "Gard Enclosed Spaces"),
    ("https://www.gard.no/web/updates/content/20639130/permit-to-work-system", "Gard PTW System"),
    # Safety4Sea
    ("https://safety4sea.com/cm-enclosed-space-entry/", "Safety4Sea Enclosed Space Entry"),
    ("https://safety4sea.com/permit-to-work-system/", "Safety4Sea PTW System"),
    # MCA MCN / MGN
    ("https://www.gov.uk/government/publications/mgn-596-mf-entry-into-enclosed-spaces", "MCA MGN 596 Enclosed Spaces"),
    # Wikipedia
    ("https://en.wikipedia.org/wiki/Confined_space", "Wikipedia Confined Space"),
    # CCGA / UK HSE
    ("https://www.hse.gov.uk/pubns/priced/hsg258.htm", "HSE HSG258 Confined Space"),
    ("https://www.hse.gov.uk/confinedspace/", "HSE Confined Space"),
]

with open(OUT_ESE, "w", encoding="utf-8") as f_ese:
    for url, title in ese_sources:
        text = scrape(url, title)
        ese_count += save(f_ese, text, title, url, "Enclosed space entry permit")
        time.sleep(DELAY)

print(f"\n✅ Enclosed Space Entry: {ese_count} docs → {OUT_ESE}")
print(f"\n=== TOTAL: COW={cow_count}, ESE={ese_count} ===")
