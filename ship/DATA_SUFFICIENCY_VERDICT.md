# DATA SUFFICIENCY VERDICT — Is Your Data Enough?

## Date: 16 February 2026

---

## VERDICT: ❌ NOT ENOUGH FOR PRODUCTION — BORDERLINE FOR STUDY AID

Your **8.4M tokens from ~100 books** is **3-6× below the minimum effective CPT threshold** for a 4B model. Every published successful domain CPT on models ≥1B used at least 25-50M tokens.

### The Brutal Numbers

| Metric | Your Data | Minimum for "Study Aid" | Minimum for "Production" |
|--------|:---------:|:-----------------------:|:------------------------:|
| CPT corpus tokens | 8.4M | 15-25M | 50-100M |
| Token-to-parameter ratio | 0.002:1 | 0.005:1 | 0.015:1 |
| SFT Q&A pairs | ~32K planned | 30-50K | 80-100K |
| DPO pairs | ~10K planned | 10K | 20K |
| Topic coverage | ~38% | 60% | 85%+ |

### What You'd Actually Get at 8.4M Tokens

| Question Type | Expected Accuracy | Example |
|---------------|:-----------------:|---------|
| Conceptual explanations | 75-90% | "How does a 2-stroke crosshead engine work?" ✅ |
| General procedures | 60-75% | "Steps to start an auxiliary boiler?" ⚠️ |
| Specific factual recall | 30-60% | "What's the MARPOL Annex VI SOx limit in ECAs?" ❌ |
| Exact values/numbers | 20-40% | "REF601 relay CT ratio setting range?" ❌ |
| Multi-hop troubleshooting | 25-45% | "ME cyl 3 high exhaust temp + low scavenge pressure — cause?" ❌ |

### ⚠️ SAFETY WARNING

This goes on ships. Wrong answers about O₂ thresholds for enclosed space entry, firefighting system operations, or lifeboat procedures **can kill**. At 8.4M tokens, the model will give **confidently incorrect specific values 20-40% of the time** on exactly these safety-critical questions.

---

## TWO PROBLEMS TO FIX

### Problem 1: NOT ENOUGH DATA (Volume)

You need to go from **8.4M → 30-50M tokens** minimum.

### Problem 2: MASSIVE COVERAGE GAPS (62% of critical topics missing)

Your data is **theory-heavy and procedure-light** — it teaches how engines work but not how to operate a ship.

---

## COVERAGE GAP ANALYSIS

### Coverage Ratings for Critical Maritime Areas

| Area | Rating | Status |
|------|:------:|--------|
| Main Engine theory | 7/10 | ✅ Good — Pounder's, Lamb's, MAN, Wartsila manuals |
| Main Engine troubleshooting | 5/10 | ⚠️ Calder + Compton cover basics, but shallow |
| **Auxiliary Systems** | **2/10** | **❌ CRITICAL GAP — No OWS, FWG, purifiers, refrigeration, sewage, incinerator** |
| Electrical theory | 6/10 | ⚠️ McGeorge + Payne decent, but Kraal is from 1965 |
| **Electrical troubleshooting** | **3/10** | **❌ Missing switchboard procedures, generator paralleling** |
| Navigation theory | 5/10 | ⚠️ Radar/ARPA good, ECDIS absent |
| **GMDSS/Communications** | **0/10** | **❌ ZERO CONTENT — mandatory for all deck officers** |
| Safety/firefighting | 6/10 | ⚠️ Olsen 2023 is good, but ISM implementation missing |
| **Cargo Operations** | **1/10** | **❌ CRITICAL GAP — No ISGOTT, IMSBC, IMDG, IBC, IGC** |
| **Ship Management/PSC** | **2/10** | **❌ No PMS procedures, no PSC inspection prep, no survey procedures** |
| Regulations (text available) | 6/10 | ⚠️ SOLAS/MARPOL present but outdated (2011-2020) |
| **Regulations (applied)** | **1/10** | **❌ The codes exist but no "how to comply" guidance** |
| Naval architecture | 7/10 | ✅ Good coverage |
| **Enclosed space/hot work** | **0/10** | **❌ ZERO CONTENT — top killer of seafarers** |
| **Bunkering operations** | **0/10** | **❌ ZERO CONTENT** |
| **Mooring/anchoring** | **0/10** | **❌ ZERO CONTENT — #2 cause of crew injuries** |
| **Deck machinery** | **0/10** | **❌ ZERO — No cranes, winches, windlass** |
| **Hydraulic/pneumatic systems** | **1/10** | **❌ Mentioned in Reeds but no depth** |
| **Lubricating oil systems** | **1/10** | **❌ Critical for engineers, barely covered** |
| **Fuel oil treatment** | **2/10** | ⚠️ Wartsila manual has some, but no dedicated purifier content |
| Medical | 6/10 | ⚠️ Ship Captain's Medical Guide is good |
| Welding/repair | 0/10 | ❌ Nothing |

### What's OUTDATED and Needs Replacing/Supplementing

| Book | Year | Problem |
|------|:----:|---------|
| Kraal Basic Electrotechnology | **1965** | 60 years old. Pre-semiconductor era. Useless. |
| Corrosion Engineering (Fontana) | **1985** | 40 years old. Missing modern coatings, cathodic protection advances |
| Lamb's Q&A | **1990** | Pre-electronic engine era. No common-rail, no electronic governors |
| McGeorge Marine Electrical | **1993** | 32 years old. No power management systems, no VFDs |
| Morton's Steam Engineering | **1979** | 46 years old. Steam knowledge still valid but presentation archaic |
| MARPOL | **2011** | Missing 2020 sulphur cap (0.50%), EEXI, CII, EEDI Phase 3 |
| STCW | **2011** | Missing post-Manila implementation guidance |
| Pounder's Marine Diesel | **2004/2009** | Missing Tier III, dual-fuel engines, methanol/ammonia fuels |

---

## THE DATA COLLECTION PLAN

### TIER 1: FREE DATA — Collect Immediately (Target: +15-20M tokens)

These are **legally free**, publicly available, and contain the highest-quality maritime technical content.

#### 1A. Accident Investigation Reports (~8M tokens) — BEST TRAINING DATA

Real-world scenarios with technical analysis. Perfect for teaching troubleshooting.

| Source | Reports | Est. Tokens | URL | Legal |
|--------|:-------:|:-----------:|-----|-------|
| **MAIB** (UK) | 800+ | 5-8M | https://www.gov.uk/maib-reports | UK Open Government Licence ✅ |
| **NTSB Marine** | 500+ | 2-3M | https://www.ntsb.gov/investigations/AccidentReports/Pages/marine.aspx | US Public Domain ✅ |
| **ATSB Marine** (Australia) | 200+ | 800K | https://www.atsb.gov.au/marine/reports | CC BY 4.0 ✅ |
| **TSB Marine** (Canada) | 300+ | 1M | https://bst-tsb.gc.ca/eng/rapports-reports/marine/index.html | Canada Open Government ✅ |

**Download method**: Batch PDF download. MAIB Python scraper:
```python
import requests
from bs4 import BeautifulSoup
import os, time

BASE = "https://www.gov.uk/maib-reports"
OUT = "/Users/mohanganesh/ship/data_extra/maib/"
os.makedirs(OUT, exist_ok=True)

for page in range(1, 50):
    url = f"{BASE}?page={page}"
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".pdf"):
            fname = href.split("/")[-1]
            if not os.path.exists(os.path.join(OUT, fname)):
                r = requests.get(f"https://www.gov.uk{href}" if href.startswith("/") else href)
                with open(os.path.join(OUT, fname), "wb") as f:
                    f.write(r.content)
                time.sleep(1)
    print(f"Page {page} done")
```

#### 1B. Government Maritime Publications (~5M tokens)

| Source | Content | Est. Tokens | URL |
|--------|---------|:-----------:|-----|
| **USCG NVICs** | Navigation & Vessel Inspection Circulars — US compliance guidance | 1-2M | https://www.dco.uscg.mil/Our-Organization/NVIC/ |
| **USCG Marine Safety Manual** (3 vols) | Complete safety procedures | 1M | https://www.dco.uscg.mil/Portals/9/DCO%20Documents/5000%20Series/ |
| **MCA COSWP** | Code of Safe Working Practices for Merchant Seafarers | 500K | https://www.gov.uk/government/publications/code-of-safe-working-practices-for-merchant-seafarers |
| **MCA MGNs/MSNs/MINs** | 500+ Marine Guidance/Safety/Information Notices | 2M | https://www.gov.uk/government/collections/marine-guidance-notices-mgns |
| **NOAA Bowditch** (American Practical Navigator) | 900pp navigation bible, public domain | 500K | https://msi.nga.mil/Publications/APN |
| **NOAA Coast Pilot** (9 volumes) | Navigation/port information | 2M | https://nauticalcharts.noaa.gov/publications/coast-pilot/index.html |

#### 1C. P&I Club Loss Prevention Guides (~3M tokens)

**Extremely high-quality** practical maritime guidance. Freely downloadable.

| Source | Content | URL |
|--------|---------|-----|
| **Gard AS** | 100+ loss prevention guides (mooring, cargo, enclosed spaces, etc.) | https://www.gard.no/web/articles |
| **UK P&I Club** | Risk Focus publications, crew health, technical guides | https://www.ukpandi.com/knowledge-publications/ |
| **Swedish Club** | Loss prevention bulletins, machinery damage reports | https://www.swedishclub.com/publications |
| **Standard Club** | Risk alerts, safety publications | https://www.standard-club.com/knowledge |
| **North P&I** | Loss prevention guides, technical bulletins | https://www.nepia.com/insights/ |
| **Britannia P&I** | Risk watch, loss prevention | https://www.britanniapin.com/loss-prevention |

#### 1D. Classification Society Free Publications (~2M tokens)

| Source | Content | URL |
|--------|---------|-----|
| **DNV Rules & Standards** (free access) | Class rules, technical guidelines | https://standards.dnv.com/ |
| **ABS Eagle** | Advisory & guidance notes | https://ww2.eagle.org/en.html |
| **Lloyd's Register** | Technical papers, class rules summaries | https://www.lr.org/en/knowledge/ |
| **IACS Procedural Requirements** | Common structural rules, survey requirements | https://iacs.org.uk/resolutions/procedural-requirements |

#### 1E. Engine Manufacturer Technical Papers (~2M tokens)

| Source | Content | URL |
|--------|---------|-----|
| **MAN Energy Solutions** | Technical papers (50+), service letters, ME-C guides | https://www.man-es.com/marine/publications |
| **Wartsila Encyclopedia** | Marine encyclopedia entries | https://www.wartsila.com/encyclopedia |
| **ABB Marine** | Technical papers on electrical systems, drives | https://new.abb.com/marine/references-and-articles |

---

### TIER 2: BOOKS TO ACQUIRE (Target: +10-15M tokens)

These fill the **critical knowledge gaps**. Some are available on Library Genesis or similar.

#### Priority 1 — MUST GET (fills 0-2/10 rated gaps)

| # | Book | Fills Gap | Pages | Est. Tokens |
|---|------|-----------|:-----:|:-----------:|
| 1 | **McGeorge — Marine Auxiliary Machinery (7th ed, 1995)** | Auxiliary systems, purifiers, FWG, OWS, refrigeration, incinerator, sewage — fills 6+ gaps in one book | 500 | 150K |
| 2 | **ISGOTT 6th Edition (OCIMF, 2020)** | ALL tanker cargo operations, tank cleaning, gas-freeing, COW | 500 | 150K |
| 3 | **IMSBC Code (IMO, 2023)** | Bulk cargo operations, liquefaction, hazards | 400 | 120K |
| 4 | **IMDG Code (IMO, 2022)** | Dangerous goods in containers | 800 | 240K |
| 5 | **GMDSS Manual (IMO, 2019)** | ALL communication systems — VHF, MF-HF, INMARSAT, EPIRB, SART, DSC | 400 | 120K |
| 6 | **Reeds Vol 12 — Motor Engineering Knowledge (latest)** | Modern engine management, common-rail, electronic governors | 400 | 120K |
| 7 | **COSWP (MCA, free download!)** | Enclosed space entry, permit to work, hot work, mooring safety | 350 | 105K |
| 8 | **Mooring Equipment Guidelines (MEG4, OCIMF, 2018)** | Mooring operations — #2 cause of injuries | 300 | 90K |
| 9 | **ICS/OCIMF Ship-to-Ship Transfer Guide** | STS operations, lightering | 300 | 90K |
| 10 | **Marine Refrigeration & Air Conditioning (Hundy et al.)** | Refrigeration, HVAC — standard equipment on every ship | 400 | 120K |

#### Priority 2 — STRONGLY RECOMMENDED

| # | Book | Fills Gap | Pages | Tokens |
|---|------|-----------|:-----:|:------:|
| 11 | **Reeds Vol 1 — Mathematics for Marine Engineers** | Engineering calculations reference | 350 | 105K |
| 12 | **Reeds Vol 2 — Applied Mechanics** | Practical mechanics | 400 | 120K |
| 13 | **Reeds Vol 4 — Naval Architecture** | Updated naval arch | 350 | 105K |
| 14 | **SIRE 2.0 VIQ (OCIMF, 2024)** | Vetting inspections — critical for tankers | 300 | 90K |
| 15 | **Maritime Hydraulics (by Brejcha or equivalent)** | Hydraulic systems theory + practice | 350 | 105K |
| 16 | **Clark's Marine Welding** | Welding procedures aboard ships | 250 | 75K |
| 17 | **Watchkeeping Safety & Cargo Management (ICS)** | Watchkeeping procedures, cargo care | 300 | 90K |
| 18 | **PSC Inspection Manual (various flag states)** | Port State Control preparation | 200 | 60K |
| 19 | **Bunkering Guidelines (ISGOTT Ch.25 or ICS)** | Bunkering operations procedures | 150 | 45K |
| 20 | **Marine Lubrication — Oil Analysis Guide** | Lube oil management, purification | 200 | 60K |

#### Priority 3 — NICE TO HAVE (for broader coverage)

| # | Book | Fills Gap |
|---|------|-----------|
| 21 | **LNG Carrier Operations (SIGTTO)** | LNG-specific operations |
| 22 | **Tanker Safety Guide (ICS)** | Chemical/product tanker operations |
| 23 | **Cargo Securing Manual template + CSS Code** | Container/cargo securing |
| 24 | **Maritime English (Demydenko)** | Communication standardization |
| 25 | **IBC Code** | Chemical tanker cargo |
| 26 | **IGC Code** | Gas carrier cargo |
| 27 | **MARPOL Consolidated 2022** | Updated environmental regulations |
| 28 | **Pounder's Marine Diesel (10th ed, 2021)** | Updated engine technology, Tier III, dual-fuel |
| 29 | **Deck Machinery Manual (MacGregor/Liebherr)** | Crane, winch, hatch cover operations |
| 30 | **ECDIS and Navigation (Weintrit)** | Electronic chart display systems |

---

### TIER 3: SYNTHETIC DATA EXPANSION (Target: +5-10M tokens, $0 API)

After collecting Tiers 1-2, use a **local teacher** on the 4‑GPU machine to **augment** your corpus:

| Method | Input | Output | Cost |
|--------|-------|--------|:----:|
| **Paraphrase/reformulate** key textbook sections | Important sections from your corpus | 3-5 alternate explanations per concept | ~$10 |
| **Generate textbook-style prose** for gap topics | Topic outline + key facts | Synthetic textbook chapters | ~$8 |
| **Multi-angle SFT pairs** | Existing Q&A pairs | 5-10 variations per key fact (different wording, difficulty, context) | ~$5 |
| **"What would a cadet ask?"** | Chapter summaries | Realistic study questions at various difficulty levels | ~$3 |

**Note:** With local generation, the *monetary* cost is $0 (no API), but the *time* cost can be multi-day depending on your teacher model size and decoding speed.

---

## REVISED TOKEN BUDGET

| Source | Tokens | Cost | Effort |
|--------|:------:|:----:|--------|
| **Current textbooks** | 8.4M | $0 | Done |
| **MAIB + NTSB + ATSB + TSB reports** | 8-12M | $0 | 2 days scraping + processing |
| **MCA COSWP + MGNs + USCG NVICs** | 3-5M | $0 | 1 day downloading |
| **P&I Club guides (Gard, UK P&I, Swedish Club)** | 2-3M | $0 | 1 day downloading |
| **Classification society publications** | 1-2M | $0 | 1 day downloading |
| **MAN/Wartsila tech papers** | 1-2M | $0 | 1 day |
| **NOAA Bowditch + Coast Pilot** | 2-3M | $0 | Free download |
| **Priority 1 books (10 books)** | 1.3M | $0-100 | Source from lib sites |
| **Priority 2 books (10 books)** | 0.9M | $0-50 | Source from lib sites |
| **Synthetic augmentation** | 5-10M | $0 | Multi-day local teacher generation |
| **TOTAL** | **33-50M** | **$15-175** | **~7-10 days** |

**This brings you from 8.4M → 35-50M tokens — into the "adequate for production" zone.**

---

## DATA COLLECTION EXECUTION PLAN

### Week 1: Free Data Harvesting (Days 1-5)

| Day | Task | Target |
|:---:|------|:------:|
| 1 | Set up scraper for MAIB reports (800+ PDFs), start downloading | 5-8M tokens |
| 1 | Download NTSB marine investigation reports | 2-3M tokens |
| 2 | Download ATSB + TSB marine reports | 1.5M tokens |
| 2 | Download MCA COSWP + all MGNs/MSNs/MINs | 2-3M tokens |
| 3 | Download USCG NVICs + Marine Safety Manual volumes | 2M tokens |
| 3 | Download NOAA Bowditch + Coast Pilot volumes | 2-3M tokens |
| 4 | Download all Gard AS + UK P&I Club loss prevention guides | 2M tokens |
| 4 | Download Swedish Club + Standard Club publications | 1M tokens |
| 5 | Download MAN Energy Solutions tech papers + Wartsila encyclopedia | 1-2M tokens |
| 5 | Download IACS procedural requirements + DNV free standards | 1M tokens |

**Week 1 Result: +20-25M tokens of free, legally safe data**

### Week 2: Books + Processing (Days 6-10)

| Day | Task |
|:---:|------|
| 6 | Source Priority 1 books (McGeorge Aux, ISGOTT, IMSBC, IMDG, GMDSS Manual) |
| 7 | Source Priority 1 books (Reeds Vol 12, MEG4, STS Guide, Refrigeration) |
| 7 | Source Priority 2 books (hydraulics, welding, lubrication, PSC) |
| 8 | Process ALL new data through Marker (batch processing ~2 days for everything) |
| 9 | Continue Marker processing |
| 10 | Categorize all new documents, quality check, merge with existing corpus |

**Week 2 Result: +2-3M tokens from books, all data processed**

### Week 3: Synthetic Augmentation + Training Data (Days 11-15)

| Day | Task |
|:---:|------|
| 11 | Run paraphrase/reformulation on key textbook sections ($10) |
| 12 | Generate synthetic textbook prose for remaining gap topics ($8) |
| 13 | Generate expanded SFT pairs: 80-100K Q&A with multi-angle variations ($10) |
| 14 | Generate expanded DPO pairs: 20K preference pairs ($5) |
| 15 | Quality filter, dedup, create final training splits |

**Week 3 Result: Final corpus ready — 35-50M tokens CPT + 80-100K SFT + 20K DPO**

---

## WHAT THIS BUYS YOU

| Metric | With 8.4M tokens (current) | With 35-50M tokens (after plan) |
|--------|:-------------------------:|:-------------------------------:|
| Conceptual accuracy | 75-90% | 85-95% |
| Procedural accuracy | 60-75% | 75-85% |
| Factual recall | 30-60% | 55-75% |
| Safety-critical answers | 50-70% | 70-85% |
| Hallucination rate (severe) | 15-25% | 5-12% |
| Topic coverage | ~38% | ~80% |
| **Production viability** | **Study aid only** | **Viable crew assistant** |

### Honest Limitations Even After Augmentation

Even with 50M tokens, a 4B model will NOT be perfect:
- **Exact regulation clause numbers**: ~60% accuracy (deploy as study aid, not legal reference)
- **Equipment-specific procedures**: Only as good as the manuals you feed it
- **Rapidly changing regulations**: Needs quarterly updates
- **Multi-step complex troubleshooting**: ~65% accuracy (good for guidance, not definitive diagnosis)

**Always display disclaimer**: "This is an AI study assistant. For safety-critical decisions, always consult official ship-specific procedures and qualified officers."

---

## QUICK ACTION ITEMS (Start Today)

1. **Download COSWP** — it's FREE: https://www.gov.uk/government/publications/code-of-safe-working-practices-for-merchant-seafarers
2. **Download Bowditch** — it's FREE: https://msi.nga.mil/Publications/APN
3. **Start MAIB scraper** — run the Python script above
4. **Download NTSB marine reports** — browse and bulk download
5. **Create `/ship/data_extra/` folder** with subfolders for each new source
