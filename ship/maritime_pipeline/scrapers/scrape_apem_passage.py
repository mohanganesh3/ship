#!/usr/bin/env python3
"""
APEM / Passage Planning procedural content scraper.
Sources:
  - MCA MGN 315, MGN 379 (passage planning guidance) -- GOV.UK
  - MAIB Passage planning lessons from accident reports
  - UK MAIB safety bulletins (free)
  - SQE Marine / free open training text
  - OCIMF / International Chamber of Shipping guidelines (open summaries)
  - Marine Insight passage planning articles (open)
  - IMO resolution A.893(21) Guidelines for voyage planning (free)
"""
import requests, json, os, time, re
from bs4 import BeautifulSoup
from datetime import datetime

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "extracted_text", "apem_passage.jsonl")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
DELAY = 2

session = requests.Session()
session.headers.update(HEADERS)

def scrape_text(url, label=""):
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        text = " ".join(soup.get_text(" ", strip=True).split())
        return text
    except Exception as e:
        print(f"  ✗ {label}: {e}")
        return ""

def write(f, text, title, source, topic):
    if len(text) < 200:
        return 0
    doc = {"title": title, "source": source, "topic": topic,
           "text": text, "scraped_at": datetime.utcnow().isoformat()}
    f.write(json.dumps(doc) + "\n")
    return 1

count = 0
with open(OUT, "w", encoding="utf-8") as f:

    # ---- IMO Res A.893(21) voyage planning guidelines ----
    # Full text via IMO IMODOCS (public)
    urls_a893 = [
        ("https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/AssemblyDocuments/A.893(21).pdf",
         "IMO Resolution A.893(21) Voyage Planning Guidelines"),
    ]
    # Try wiki text on passage planning procedure
    wiki_pages = [
        ("https://en.wikipedia.org/wiki/Passage_planning", "Wikipedia Passage Planning"),
        ("https://en.wikipedia.org/wiki/APEM_(navigation)", "Wikipedia APEM Navigation"),
    ]
    for url, title in wiki_pages:
        print(f"  Fetching {title}...")
        text = scrape_text(url, title)
        count += write(f, text, title, url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- MCA MGN 315 (M) — Passage Planning ----
    mgn_urls = [
        ("https://www.gov.uk/government/publications/mgn-315-mf-passage-planning",
         "MCA MGN 315 Passage Planning"),
        ("https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/284710/mgn315.pdf",
         "MCA MGN 315 PDF"),
        ("https://www.gov.uk/government/publications/mgn-379-mf-keeping-a-safe-navigational-watch",
         "MCA MGN 379 Safe Navigational Watch"),
    ]
    for url, title in mgn_urls:
        print(f"  Fetching {title}...")
        text = scrape_text(url, title)
        count += write(f, text, title, url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- Transport Canada Passage Planning ----
    tc_urls = [
        ("https://tc.canada.ca/en/marine-transportation/marine-safety/tp-1313e-voyage-planning-guide",
         "Transport Canada Voyage Planning Guide"),
        ("https://tc.canada.ca/en/marine-transportation/marine-safety/marine-safety-notices",
         "Transport Canada Marine Safety Notices"),
    ]
    for url, title in tc_urls:
        print(f"  Fetching {title}...")
        text = scrape_text(url, title)
        count += write(f, text, title, url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- Marine Insight — APEM procedural articles ----
    marine_insight_urls = [
        "https://www.marineinsight.com/guidelines/passage-planning-procedure-on-ships/",
        "https://www.marineinsight.com/guidelines/what-is-passage-planning/",
        "https://www.marineinsight.com/guidelines/voyage-planning-on-ships/",
        "https://www.marineinsight.com/guidelines/bridge-watchkeeping-procedures/",
        "https://www.marineinsight.com/guidelines/assess-plan-execute-and-monitor-components-of-passage-planning/",
        "https://www.marineinsight.com/guidelines/10-key-points-of-passage-planning/",
        "https://www.marineinsight.com/guidelines/passage-plan-appraisal/",
        "https://www.marineinsight.com/safety/passage-planning-apem/",
    ]
    for url in marine_insight_urls:
        title = url.split("/")[-2].replace("-"," ").title()
        print(f"  Fetching Marine Insight: {title}...")
        text = scrape_text(url, title)
        count += write(f, text, title, url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- Maritime Manual / SQE free resources ----
    sqe_urls = [
        "https://en.marinemba.com/passage-planning/",
        "https://www.seamanship-international.com/passage-planning/",
        "https://www.theseamanshand.com/passage-planning/",
    ]
    for url in sqe_urls:
        title = url.split("/")[2] + " passage planning"
        print(f"  Fetching {title}...")
        text = scrape_text(url, title)
        count += write(f, text, title, url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- MAIB accident lessons on bad passage planning ----
    maib_urls = [
        "https://www.gov.uk/maib-reports?keywords=passage+planning",
        "https://assets.publishing.service.gov.uk/media/5a7feb9eed915d74e33f70a4/MAIBInvReport5-2017.pdf",
    ]
    for url in maib_urls[:1]:
        print(f"  Fetching MAIB passage planning reports index...")
        text = scrape_text(url, "MAIB passage planning reports")
        count += write(f, text, "MAIB passage planning deficiencies", url, "APEM passage planning")
        time.sleep(DELAY)

    # ---- CHIRP maritime alerts on passage planning ----
    chirp_urls = [
        "https://www.chirpmaritime.org/?s=passage+planning",
        "https://www.chirpmaritime.org/?s=apem",
    ]
    for url in chirp_urls:
        print(f"  Fetching CHIRP: {url}...")
        text = scrape_text(url, "CHIRP passage planning alerts")
        count += write(f, text, "CHIRP passage planning alert", url, "APEM passage planning")
        time.sleep(DELAY)

print(f"\n✅ APEM/Passage Planning: {count} documents written to {OUT}")
