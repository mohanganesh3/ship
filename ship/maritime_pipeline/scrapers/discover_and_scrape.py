#!/usr/bin/env python3
"""
Discovers and scrapes current Marine Insight URLs from their sitemaps.
Also scrapes other reliable sources for our 8 weak topics.
"""
import requests, json, os, time, re
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extracted_text")
os.makedirs(DATA_DIR, exist_ok=True)

session = requests.Session()
session.headers.update(HEADERS)

TOPIC_KEYWORDS = {
    "FWG startup procedure": ["fresh.water","freshwater","fwg","evaporator","salinometer"],
    "Bunkering checklist": ["bunker"],
    "APEM passage planning": ["passage.plan","apem"],
    "Drydocking checklist": ["drydock","dry.dock"],
    "Enclosed space entry permit": ["enclosed","confined.space","permit.to.work"],
    "Crude oil washing procedure": ["crude.oil.wash","crude.oil.washing"],
    "Tank gauging / ullage": ["ullage","tank.gaug","innage"],
    "Master override": ["master.over","master.*override"],
}

print("Scanning Marine Insight sitemaps...")
all_topic_urls = {topic: [] for topic in TOPIC_KEYWORDS}
for i in range(1, 9):
    try:
        r = session.get(f"http://www.marineinsight.com/post-sitemap{i}.xml", timeout=20)
        found_urls = re.findall(r'https://www\.marineinsight\.com[^\s<"]+', r.text)
        for u in found_urls:
            for topic, keywords in TOPIC_KEYWORDS.items():
                pat = re.compile("|".join(keywords), re.I)
                if pat.search(u):
                    all_topic_urls[topic].append(u)
                    break
        print(f"  Sitemap {i}: {len(found_urls)} URLs scanned")
    except Exception as e:
        print(f"  Sitemap {i}: error — {e}")

print("\nDiscovered URLs per topic:")
for topic, urls in all_topic_urls.items():
    print(f"  {topic}: {len(urls)} URLs")
    for u in urls[:5]:
        print(f"    {u}")

def scrape(url, label=""):
    try:
        r = session.get(url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for t in soup(["script","style","nav","footer","header","aside"]):
            t.decompose()
        text = " ".join(soup.get_text(" ", strip=True).split())
        if len(text) > 200:
            return text
        return ""
    except Exception as e:
        return ""

def append_to_jsonl(filepath, text, title, url, topic):
    if len(text) < 200:
        return 0
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "title": title, "source": url, "topic": topic,
            "text": text, "scraped_at": datetime.utcnow().isoformat()
        }) + "\n")
    return 1

# Map topics to output files
OUTFILES = {
    "FWG startup procedure": os.path.join(DATA_DIR, "fwg_procedures.jsonl"),
    "Bunkering checklist": os.path.join(DATA_DIR, "bunkering_checklist.jsonl"),
    "APEM passage planning": os.path.join(DATA_DIR, "apem_passage.jsonl"),
    "Drydocking checklist": os.path.join(DATA_DIR, "drydocking_checklist.jsonl"),
    "Enclosed space entry permit": os.path.join(DATA_DIR, "enclosed_space_entry.jsonl"),
    "Crude oil washing procedure": os.path.join(DATA_DIR, "cow_procedures.jsonl"),
    "Tank gauging / ullage": os.path.join(DATA_DIR, "tank_gauging.jsonl"),
    "Master override": os.path.join(DATA_DIR, "master_override.jsonl"),
}

total = 0
print("\n\nScraping discovered Marine Insight URLs...")
for topic, urls in all_topic_urls.items():
    outfile = OUTFILES[topic]
    count = 0
    for url in urls[:15]:  # cap at 15 per topic
        text = scrape(url, url)
        if text:
            title = url.split("/")[-2].replace("-", " ").title()
            n = append_to_jsonl(outfile, text, title, url, topic)
            count += n
            if n:
                print(f"  ✓ [{topic[:30]}] {title[:50]}: {len(text):,} chars")
        time.sleep(1.5)
    print(f"  → {topic}: {count} docs added")
    total += count

print(f"\n✅ Marine Insight discovery: {total} total docs added")

# ===== ADDITIONAL RELIABLE SOURCES =====
print("\n\nAdding supplementary sources (Wikipedia, BBC, IMO, USCG NVIC)...")

supplement = [
    # Wikipedia pages that definitely exist
    ("https://en.wikipedia.org/wiki/Bunkering", "Wikipedia Bunkering", "Bunkering checklist"),
    ("https://en.wikipedia.org/wiki/Drydock", "Wikipedia Drydock", "Drydocking checklist"),
    ("https://en.wikipedia.org/wiki/Passage_planning", "Wikipedia Passage Planning", "APEM passage planning"),
    ("https://en.wikipedia.org/wiki/Crude_oil_washing", "Wikipedia Crude Oil Washing", "Crude oil washing procedure"),
    ("https://en.wikipedia.org/wiki/Confined_space", "Wikipedia Confined Space", "Enclosed space entry permit"),
    ("https://en.wikipedia.org/wiki/Flash_evaporator", "Wikipedia Flash Evaporator", "FWG startup procedure"),
    ("https://en.wikipedia.org/wiki/Multi-effect_distillation", "Wikipedia Multi-Effect Distillation", "FWG startup procedure"),
    ("https://en.wikipedia.org/wiki/Ullage", "Wikipedia Ullage", "Tank gauging / ullage"),
    ("https://en.wikipedia.org/wiki/Maritime_Safety_Act_1994", "Wikipedia Maritime Safety Act", "Master override"),
    # USCG NVIC indices for procedural content
    ("https://www.dco.uscg.mil/Our-Organization/Deputy-for-Operations-Prevention-DC-3/Inspections-Compliance-DC-5/National-Center-for-Expertise/Chemical-Tanker-Center/", "USCG Chemical Tanker Center", "Crude oil washing procedure"),
    # Wikipedia for passage planning
    ("https://en.wikipedia.org/wiki/Bridge_resource_management", "Wikipedia BRM", "APEM passage planning"),
    ("https://en.wikipedia.org/wiki/Watchkeeping", "Wikipedia Watchkeeping", "APEM passage planning"),
    ("https://en.wikipedia.org/wiki/International_Safety_Management_Code", "Wikipedia ISM Code", "Master override"),
    ("https://en.wikipedia.org/wiki/STCW_Convention", "Wikipedia STCW Convention", "APEM passage planning"),
    # USCG Boating Safety  
    ("https://www.navcen.uscg.gov/pdf/navRules/navrules.pdf", "USCG Navigation Rules", "APEM passage planning"),
    # MCA guidance open
    ("https://www.gov.uk/government/publications/mgn-315-mf-passage-planning", "MCA MGN 315 Passage Planning", "APEM passage planning"),
    # gCaptain (working)
    ("https://gcaptain.com/bunkering-guide/", "gCaptain Bunkering Guide", "Bunkering checklist"),
    ("https://gcaptain.com/what-is-bunkering/", "gCaptain What is Bunkering", "Bunkering checklist"),
    ("https://gcaptain.com/drydocking-101/", "gCaptain Drydocking 101", "Drydocking checklist"),
    # The Maritime Executive
    ("https://maritime-executive.com/editorials/passage-planning", "Maritime Executive Passage Planning", "APEM passage planning"),
    ("https://maritime-executive.com/editorials/enclosed-space-deaths", "Maritime Executive Enclosed Space", "Enclosed space entry permit"),
    # IMO open pages
    ("https://www.imo.org/en/OurWork/HumanElement/Pages/ISMCode.aspx", "IMO ISM Code", "Master override"),
    ("https://www.imo.org/en/OurWork/HumanElement/Pages/STCW-Convention.aspx", "IMO STCW", "APEM passage planning"),
    # Wayback / Maritimeprofessional
    ("https://www.maritimeprofessional.com/blogs/post/bunkering-checklist-20553", "Maritime Professional Bunkering Checklist", "Bunkering checklist"),
    ("https://www.maritimeprofessional.com/blogs/post/enclosed-space-entry-procedures-14012", "Maritime Professional Enclosed Space", "Enclosed space entry permit"),
    ("https://www.maritimeprofessional.com/blogs/post/crude-oil-washing-on-tankers-14011", "Maritime Professional COW", "Crude oil washing procedure"),
    # The Nautical Institute
    ("https://www.nautinst.org/uploads/assets/uploaded/cff38fa2-5d3d-471a-83b40c78ef0daa16.pdf", "Nautical Institute Passage Planning", "APEM passage planning"),
]

supp_total = 0
for url, title, topic in supplement:
    text = scrape(url, title)
    if text:
        outfile = OUTFILES[topic]
        n = append_to_jsonl(outfile, text, title, url, topic)
        if n:
            print(f"  ✓ {title[:60]}: {len(text):,} chars")
            supp_total += n
    time.sleep(1.5)

print(f"\n✅ Supplementary: {supp_total} docs added")
print(f"\n🎯 GRAND TOTAL NEW DOCS: {total + supp_total}")
print("\nNext: Run audit_depth.py to verify improvements")
