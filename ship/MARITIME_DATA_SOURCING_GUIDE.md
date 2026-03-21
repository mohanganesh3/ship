# Maritime Technical Text Data — Comprehensive Sourcing Guide

**Purpose:** Identify 20-30M+ additional tokens of high-quality maritime text for AI training  
**Current corpus:** ~8.4M tokens from ~100 textbooks  
**Target:** Double to triple corpus (16-25M+ tokens)  
**Date:** February 16, 2026  

---

## EXECUTIVE SUMMARY

| Priority Tier | Source Category | Estimated Tokens | Effort |
|---|---|---|---|
| **TIER 1 — Harvest First** | Accident Investigation Reports (MAIB, NTSB, ATSB, TSB, BMA) | 8-12M | Low-Medium |
| **TIER 1 — Harvest First** | USCG NVICs + Marine Safety Info + Navigation Manuals | 3-5M | Low |
| **TIER 1 — Harvest First** | UK MCA Notices (MGNs, MINs, MSNs) | 2-3M | Low |
| **TIER 2 — High Value** | P&I Club Loss Prevention Guides | 4-6M | Low-Medium |
| **TIER 2 — High Value** | Classification Society Free Publications (DNV, LR, ABS) | 3-5M | Medium |
| **TIER 2 — High Value** | IMO Publicly Available Circulars & Model Courses | 2-4M | Medium |
| **TIER 2 — High Value** | MAN/Wärtsilä/ABB Technical Papers | 2-3M | Medium |
| **TIER 3 — Supplementary** | MarineInsight / Bright Hub Articles | 3-5M | Medium (scraping) |
| **TIER 3 — Supplementary** | Wikipedia Maritime Articles | 2-3M | Low |
| **TIER 3 — Supplementary** | Open Educational Resources (MIT OCW, theses) | 1-2M | Medium |
| **TIER 3 — Supplementary** | YouTube Transcript Mining | 1-2M | Medium |
| **TIER 3 — Supplementary** | NOAA Publications | 1-2M | Low |
| **TIER 3 — Supplementary** | IACS, ICS, OCIMF, CHIRP Free Pubs | 1-2M | Medium |
| | **TOTAL ESTIMATED** | **33-54M** | |

**Realistic achievable with moderate effort: 20-30M tokens**

---

## 1. ACCIDENT INVESTIGATION REPORTS ⭐⭐⭐ (HIGHEST PRIORITY)

Accident reports are **gold-standard** training data: they describe real maritime operations in technical detail, cover equipment failures, human factors, navigation, stability, fire safety, engineering systems — essentially every domain your chatbot needs. They're written in clear technical English, are factually grounded, and are 100% public domain government publications.

---

### 1.1 MAIB — UK Marine Accident Investigation Branch

| Field | Detail |
|---|---|
| **URL** | https://www.gov.uk/maib-reports |
| **Content** | Full investigation reports for all serious maritime accidents in UK waters and involving UK-flagged vessels |
| **Volume** | ~800+ full reports (2000-2025), each 20-80 pages. **Estimated 5-8M tokens total** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Extremely detailed, covers machinery failure, navigation errors, stability, fire, structural failure |
| **Legal Status** | **Open Government Licence v3.0** — explicitly permits reproduction, adaptation, and use for any purpose including commercial. Perfect for AI training |
| **Download** | Direct PDF download from GOV.UK. Each report has a dedicated page with PDF link |
| **Scraping Method** | Paginated listing at `https://www.gov.uk/maib-reports?page=N`. Each page links to individual report pages containing PDF download links. Python + requests + BeautifulSoup, then PDF-to-text via `pdfplumber` or `PyMuPDF` |
| **Sample Topics** | Engine room fires, groundings, collisions, man overboard, cargo shift, flooding, propulsion failures, electrical failures |

**Scraping approach:**
```python
# Conceptual scraper for MAIB reports
import requests
from bs4 import BeautifulSoup

base_url = "https://www.gov.uk/maib-reports"
# Paginate through all pages
for page in range(1, 50):
    resp = requests.get(f"{base_url}?page={page}")
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Find all report links, download PDFs
    for link in soup.select('a[href*="/maib-reports/"]'):
        report_url = "https://www.gov.uk" + link['href']
        # Navigate to report page, find PDF download link
        # Download PDF, extract text with pdfplumber
```

**Why this is #1 priority:** Highest volume of freely available, legally clear, high-quality maritime technical text. Each report covers multiple maritime domains (navigation, engineering, safety management, regulations) in a single document.

---

### 1.2 NTSB — US National Transportation Safety Board (Marine Division)

| Field | Detail |
|---|---|
| **URL** | https://www.ntsb.gov/investigations/AccidentReports/Pages/marine.aspx |
| **Search** | https://data.ntsb.gov/carol-main-public/basic-search (filter: Mode = Marine) |
| **Content** | Major marine accident investigation reports, safety studies, safety recommendations |
| **Volume** | ~200+ major reports + thousands of brief factual reports. **Estimated 2-3M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — US government quality, extremely detailed engineering analysis |
| **Legal Status** | **Public domain** — US government works are not subject to copyright (17 U.S.C. § 105). Fully usable for any purpose |
| **Download** | Direct PDF downloads from NTSB CAROL database |
| **Method** | CAROL search interface allows filtering and downloading. Some bulk download may require scripting |

**Notable reports for training data quality:**
- El Faro sinking (2015) — 300+ pages, covers stability, weather routing, TOTE management
- Deepwater Horizon
- Conception dive boat fire — fire safety, vessel construction
- Various towing vessel accidents — inland waterway operations

---

### 1.3 ATSB — Australian Transport Safety Bureau (Marine)

| Field | Detail |
|---|---|
| **URL** | https://www.atsb.gov.au/marine/investigations |
| **Content** | Maritime accident/incident investigations in Australian waters |
| **Volume** | ~300+ reports. **Estimated 1-2M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Excellent detail, strong engineering analysis |
| **Legal Status** | **Creative Commons BY 3.0 AU** — explicitly permits reuse with attribution. Ideal for AI training |
| **Download** | Direct PDF download from investigation pages |
| **Method** | Browse investigation listing, download PDFs. Straightforward scraping |

---

### 1.4 TSB — Transportation Safety Board of Canada (Marine)

| Field | Detail |
|---|---|
| **URL** | https://www.tsb.gc.ca/eng/rapports-reports/marine/index.html |
| **Content** | Marine accident investigation reports in Canadian waters |
| **Volume** | ~500+ reports (1990-2025). **Estimated 1.5-2.5M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Bilingual (EN/FR), very detailed |
| **Legal Status** | **Government of Canada open data** — permitted for reproduction and derivative works |
| **Download** | Structured archive by year, direct PDF links |
| **Method** | Navigate year-by-year listing, download PDFs |

---

### 1.5 Bahamas Maritime Authority (BMA) Investigation Reports

| Field | Detail |
|---|---|
| **URL** | https://www.bahamasmaritime.com/maritime-casualty-investigations/ |
| **Content** | Casualty investigation reports for Bahamas-flagged vessels (one of the world's largest registries) |
| **Volume** | ~100+ reports. **Estimated 0.5-1M tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Good quality, often covering large commercial vessels |
| **Legal Status** | Published for public information, generally permissive |
| **Download** | PDF downloads from the website |

---

### 1.6 EMSA — European Maritime Safety Agency (EMCIP)

| Field | Detail |
|---|---|
| **URL** | https://emcip.jrc.ec.europa.eu/ |
| **Content** | Annual overview of marine casualties, safety analysis reports. Links to member state investigation body reports |
| **Volume** | Annual overviews + curated data. **Estimated 0.5-1M tokens** from EMSA's own publications |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Pan-European data, good statistical analysis |
| **Legal Status** | EU public data, generally reusable under EU open data policy |
| **Download** | Reports available as PDF from EMSA website |

**Note:** EMSA also links to national investigation bodies: Denmark (DMAIB), Netherlands (Dutch Safety Board), Germany (BSU), Sweden, Norway, etc. Each of these publishes their own reports in English — collectively another 1-2M tokens.

---

### 1.7 Other National Investigation Bodies

| Country | Body | URL | Est. Tokens | Notes |
|---|---|---|---|---|
| Denmark | DMAIB | https://dmaib.dk/reports | 300K-500K | All reports in English |
| Netherlands | Dutch Safety Board | https://www.onderzoeksraad.nl/en/shipping | 200K-400K | Major reports in English |
| Germany | BSU | https://www.bsu-bund.de/EN/ | 300K-500K | English translations available |
| Norway | AIBN/Havarikommisjonen | https://havarikommisjonen.no/Marine/Investigations | 300K-500K | English reports |
| Singapore | TSIB | https://www.mot.gov.sg/what-we-do/transport-safety-investigation-bureau | 200K-300K | English reports |
| Japan | JTSB | https://www.mlit.go.jp/jtsb/english.html | 500K-1M | English digests of major cases |
| Panama | PMA | http://www.segumar.com/ | 200K-400K | English reports for large registry |

**Combined additional tokens from "other" investigation bodies: ~2-4M**

---

## 2. US COAST GUARD PUBLICATIONS ⭐⭐⭐

### 2.1 Navigation and Vessel Inspection Circulars (NVICs)

| Field | Detail |
|---|---|
| **URL** | https://www.dco.uscg.mil/Our-Organization/NVIC/ |
| **Content** | Detailed policy/guidance on vessel design, inspection, safety equipment, stability, fire protection, machinery, electrical systems |
| **Volume** | ~500+ active NVICs, each 5-50 pages. **Estimated 1-2M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Authoritative US government technical guidance |
| **Legal Status** | **Public domain** (US government work) |
| **Download** | PDF downloads from USCG Homeport or DCO website |

**Key NVICs for maritime training data:**
- NVIC 1-97: Stability & dynamical stability
- NVIC 5-86: Inspection of fire detection/extinguishing equipment
- NVIC 9-02: Guidelines for marine engineering examinations
- NVIC 2-98: Marine safety information

### 2.2 Marine Safety Information Bulletins (MSIBs)

| Field | Detail |
|---|---|
| **URL** | https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/Marine-Safety-Alert/ |
| **Content** | Marine Safety Alerts covering specific hazards, equipment failures, lessons learned |
| **Volume** | ~300+ bulletins. **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Concise, focused safety information |
| **Legal Status** | **Public domain** |
| **Download** | Direct PDF downloads |

### 2.3 USCG Commandant Instructions & Manuals

| Field | Detail |
|---|---|
| **URL** | https://www.dco.uscg.mil/Directives-Manuals/ |
| **Content** | Operational manuals, inspection manuals, navigation rules, marine safety manuals |
| **Volume** | **Estimated 2-3M tokens** from key manuals |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | **Public domain** |

**Key manuals:**
- Marine Safety Manual (Vol I: Administration, Vol II: Material Inspection, Vol III: Marine Industry Personnel)
- Navigation Rules (Inland & International)
- Marine Environmental Protection manuals
- Port Security manuals

### 2.4 USCG Marine Casualty & Pollution Database

| Field | Detail |
|---|---|
| **URL** | https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/ |
| **Content** | Tabular data on marine casualties, but includes narrative descriptions |
| **Volume** | ~500K tokens from narratives |
| **Quality** | ⭐⭐⭐ (3/5) — Brief narratives, limited detail |
| **Legal Status** | **Public domain** |

### 2.5 US Army Corps of Engineers — Navigation Publications

| Field | Detail |
|---|---|
| **URL** | https://www.publications.usace.army.mil/ |
| **Content** | Inland waterway navigation manuals, lock and dam operations, waterway engineering |
| **Volume** | ~500K-1M tokens |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | **Public domain** |

### 2.6 USCG Exam Question Banks (Freely Available)

| Field | Detail |
|---|---|
| **URL** | https://www.dco.uscg.mil/nmc/deck_engineer_exam_questions/ and various mirrors |
| **Content** | Thousands of multiple-choice questions for USCG licensing exams (Deck, Engine, and other endorsements) |
| **Volume** | ~500K-1M tokens |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Excellent for Q&A-style training data |
| **Legal Status** | **Public domain** |
| **Download** | Available through NMC website; also mirrored on maritime training sites |

**This is EXCELLENT training data** — it's already in question-answer format, covering navigation, engineering, safety, rules of the road, stability, cargo handling, etc.

---

## 3. UK MCA PUBLICATIONS ⭐⭐⭐

### 3.1 Marine Guidance Notes (MGNs)

| Field | Detail |
|---|---|
| **URL** | https://www.gov.uk/government/collections/marine-guidance-notices-mgns |
| **Content** | Guidance on marine safety, vessel construction, equipment requirements, crew training |
| **Volume** | ~600+ MGNs, each 2-20 pages. **Estimated 1-1.5M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Clear, authoritative technical guidance |
| **Legal Status** | **Open Government Licence v3.0** — fully reusable |
| **Download** | PDF downloads from GOV.UK |

### 3.2 Marine Information Notes (MINs)

| Field | Detail |
|---|---|
| **URL** | https://www.gov.uk/government/collections/marine-information-notes-mins |
| **Content** | Shorter notices on operational matters, new regulations, port state control procedures |
| **Volume** | ~500+ MINs. **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | **Open Government Licence v3.0** |
| **Download** | PDF from GOV.UK |

### 3.3 Merchant Shipping Notices (MSNs)

| Field | Detail |
|---|---|
| **URL** | https://www.gov.uk/government/collections/merchant-shipping-notices-msns |
| **Content** | Mandatory requirements under UK merchant shipping legislation |
| **Volume** | ~200+ MSNs. **Estimated 500K-800K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | **Open Government Licence v3.0** |
| **Download** | PDF from GOV.UK |

### 3.4 MCA Code of Safe Working Practices for Merchant Seafarers (COSWP)

| Field | Detail |
|---|---|
| **URL** | https://www.gov.uk/government/publications/code-of-safe-working-practices-for-merchant-seafarers |
| **Content** | Comprehensive code covering all aspects of safe working on ships — PPE, enclosed spaces, work at height, mooring, anchoring, cargo, electrical safety, etc. |
| **Volume** | ~400 pages. **Estimated 150K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — THE reference for ship safety procedures |
| **Legal Status** | **Open Government Licence v3.0** |
| **Download** | Free PDF download |

---

## 4. AUSTRALIAN AMSA PUBLICATIONS ⭐⭐

| Field | Detail |
|---|---|
| **URL** | https://www.amsa.gov.au/about/regulations-and-standards/marine-orders |
| **Content** | Marine Orders, Marine Notices, guidelines on vessel safety, crewing, navigation, environmental protection |
| **Volume** | **Estimated 500K-1M tokens** across all publications |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | **Creative Commons BY 3.0 AU** in most cases |
| **Download** | PDF downloads from AMSA website |

**Key resources:**
- Marine Orders (47+ orders covering construction, equipment, crewing, cargo)
- Marine Notices
- National Plan for Maritime Environmental Emergencies documents
- AMSA PSC guidelines

---

## 5. SINGAPORE MPA CIRCULARS ⭐⭐

| Field | Detail |
|---|---|
| **URL** | https://www.mpa.gov.sg/regulations-and-port-services/port-marine-circulars |
| **Content** | Shipping Circulars, Port Marine Circulars covering safety, pollution prevention, port operations |
| **Volume** | ~500+ circulars. **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Singapore is a major maritime hub, circulars are highly relevant |
| **Legal Status** | Published for public information, generally permissive for non-commercial educational use |
| **Download** | PDF downloads from MPA website |

---

## 6. FLAG STATE GUIDELINES ⭐⭐

### 6.1 Marshall Islands (IRI)

| Field | Detail |
|---|---|
| **URL** | https://www.register-iri.com/maritime/maritime-regulations-guidelines/ |
| **Content** | Marine Safety Advisories, Marine Guidance, Technical Advisories |
| **Volume** | ~200+ documents. **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Published for flag state vessel compliance, generally usable |
| **Download** | PDF downloads |

### 6.2 Liberia (LISCR)

| Field | Detail |
|---|---|
| **URL** | https://www.liscr.com/liscr-marine-advisories |
| **Content** | Marine Advisories, Marine Operations Notes, Marine Guidance |
| **Volume** | ~300+ advisories. **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Download** | PDF downloads, some require registration |

### 6.3 Panama (PMA)

| Field | Detail |
|---|---|
| **URL** | https://panamamaritimeauthority.com/ (via Segumar for merchant marine circulars) |
| **Content** | Merchant Marine Circulars, advisory notices |
| **Volume** | ~200K-400K tokens |
| **Quality** | ⭐⭐⭐ (3/5) — Many in Spanish, English versions for key circulars |
| **Download** | PDF downloads |

---

## 7. IMO PUBLICLY AVAILABLE PUBLICATIONS ⭐⭐⭐

### 7.1 IMO Circulars (MSC, MEPC, FAL)

| Field | Detail |
|---|---|
| **URL** | https://www.imo.org/en/OurWork/Circulars/Pages/default.aspx |
| **Also** | https://docs.imo.org/ (IMODOCS system — requires free registration) |
| **Content** | Committee circulars covering safety (MSC), environment (MEPC), facilitation (FAL). Many are freely available while the full conventions are behind paywalls |
| **Volume** | Several thousand circulars. Accessible subset: **Estimated 1-2M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — The primary source of international maritime regulations |
| **Legal Status** | **Complex** — IMO asserts copyright on its publications, BUT circulars distributed to member states are generally considered public documents. Many are republished by flag states. For AI training, use circulars redistributed by government agencies (USCG, MCA, etc.) rather than directly from IMO |
| **Download** | IMODOCS system (free registration); some directly linked from IMO website |

**Key freely available IMO resources:**
- SOLAS Convention summaries
- MARPOL overviews
- STCW Convention summaries
- Polar Code overview
- IGF Code overview
- ISM Code overview
- ISPS Code overview
- Ballast Water Management Convention overview

### 7.2 IMO GISIS Database

| Field | Detail |
|---|---|
| **URL** | https://gisis.imo.org/ |
| **Content** | Global Integrated Shipping Information System — contains ship particulars, casualty data, company details, port state control deficiencies |
| **Volume** | Text data is primarily structured/tabular. Limited narrative text for AI training |
| **Quality** | ⭐⭐⭐ (3/5) for language model training (better for structured data) |
| **Legal Status** | Requires registration, some modules are public |
| **Usefulness** | Limited for LLM training — better for RAG knowledge base |

### 7.3 IMO Model Courses

| Field | Detail |
|---|---|
| **Content** | Comprehensive training syllabi for STCW competencies — engine room, navigation, safety, etc. |
| **Legal Status** | ⚠️ **Copyrighted by IMO, sold commercially** — NOT freely available |
| **Alternative** | Many maritime training academies publish their own STCW-compliant curricula based on model courses. Look for these instead (see Section 12) |

---

## 8. CLASSIFICATION SOCIETY FREE PUBLICATIONS ⭐⭐⭐

### 8.1 DNV (Det Norske Veritas)

| Field | Detail |
|---|---|
| **URL** | https://www.dnv.com/rules-standards/ (rules) |
| **Also** | https://www.dnv.com/publications/ (papers & reports) |
| **Content** | Class rules, recommended practices (RPs), class guidelines (CGs), technical reports, position papers, technology outlooks |
| **Volume** | Rules alone: thousands of pages. Free publications subset: **Estimated 2-3M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — World-class technical documentation |
| **Legal Status** | DNV rules are freely available for viewing/download. Technical papers are published for industry use. Fair use for AI training is defensible for educational purposes; check terms of use |
| **Download** | Rules: free PDF download after registration at rules.dnv.com. Papers: PDF from DNV website |

**Key free DNV resources:**
- Rules for Classification of Ships (Parts 1-7)
- Recommended Practices (RP-C201 buckling, RP-C203 fatigue, etc.)
- Class Guidelines (CG-0127 finite element analysis, others)
- Maritime Forecast to 2050 report
- Energy Transition Outlook
- Technical papers on alternative fuels, digitalization, autonomy

### 8.2 Lloyd's Register (LR)

| Field | Detail |
|---|---|
| **URL** | https://www.lr.org/en/knowledge/free-publications/ |
| **Also** | https://www.lr.org/en/knowledge/technical-papers/ |
| **Content** | Technical papers, guidance notes, ShipRight procedures, rules |
| **Volume** | **Estimated 500K-1M tokens** from free publications |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | Published for industry guidance; registration may be required |
| **Download** | PDF downloads, some require free registration |

**Key free LR resources:**
- Guidance Notes on various topics (structural, machinery, materials)
- Rules extracts
- Technical papers on alternative fuels, digital twins, autonomous vessels
- Historical Classed Ship Register entries

### 8.3 ABS (American Bureau of Shipping)

| Field | Detail |
|---|---|
| **URL** | https://ww2.eagle.org/en/rules-and-guides.html |
| **Content** | Rules, guides, guidance notes, advisories |
| **Volume** | **Estimated 1-2M tokens** freely available |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | ABS rules and guides are freely downloadable for reference |
| **Download** | PDF downloads from Eagle.org, registration may be required |

**Key free ABS resources:**
- Rules for Building and Classing Marine Vessels
- Guidance Notes on Ship Vibration
- Guidance Notes on Fatigue Assessment
- Guide for Crew Habitability
- Guide for Building and Classing Offshore Installations

### 8.4 Bureau Veritas (BV)

| Field | Detail |
|---|---|
| **URL** | https://marine-offshore.bureauveritas.com/rules-guidelines |
| **Content** | Rules, guidance notes, technical notes |
| **Volume** | **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Rules published for industry reference |
| **Download** | PDF downloads from BV Marine website |

### 8.5 ClassNK (Nippon Kaiji Kyokai)

| Field | Detail |
|---|---|
| **URL** | https://www.classnk.or.jp/hp/en/activities/statutory/ism/ and related pages |
| **Content** | Technical guidelines, PrimeShip guides, environmental guidelines |
| **Volume** | **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Published for industry guidance |
| **Download** | PDF downloads |

### 8.6 IACS — International Association of Classification Societies

| Field | Detail |
|---|---|
| **URL** | https://iacs.org.uk/resolutions/ |
| **Content** | Unified Requirements (URs), Unified Interpretations (UIs), Procedural Requirements (PRs), Recommendations |
| **Volume** | ~200+ documents. **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — These are the harmonized standards all class societies follow |
| **Legal Status** | Published for free public access |
| **Download** | Direct PDF downloads from IACS website |

---

## 9. INDUSTRY BODY FREE PUBLICATIONS ⭐⭐⭐

### 9.1 P&I Club Loss Prevention Publications

P&I Clubs produce outstanding technical guidance — arguably the best free maritime safety publications available.

#### 9.1.1 UK P&I Club

| Field | Detail |
|---|---|
| **URL** | https://www.ukpandi.com/knowledge-hub/ |
| **Content** | Loss Prevention Bulletins, Carefully to Carry guides, pocket safety guides, legal circulars |
| **Volume** | **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Practical, real-world focused |
| **Legal Status** | Published freely for maritime safety improvement. Generally permissive for educational use |
| **Download** | PDF downloads, some require free registration |

**Key publications:**
- "Carefully to Carry" cargo guides
- Loss Prevention Bulletins on specific topics
- Pocket safety guides (enclosed spaces, mooring, lifeboat safety)

#### 9.1.2 Gard P&I

| Field | Detail |
|---|---|
| **URL** | https://www.gard.no/web/publications |
| **Content** | Loss Prevention Circulars, Guidance publications, Claims statistics |
| **Volume** | **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Extremely thorough |
| **Download** | Free PDF downloads |

**Key publications:**
- "Gard Guidance to Masters"
- "Gard Guidance on Maritime Claims and Insurance"
- Loss prevention circulars covering cargo, navigation, machinery, human element

#### 9.1.3 The Swedish Club

| Field | Detail |
|---|---|
| **URL** | https://www.swedishclub.com/publications |
| **Content** | Loss prevention publications, machinery damage analyses, navigation claims, cargo claims |
| **Volume** | **Estimated 300K-600K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Their machinery damage studies are exceptional |
| **Download** | Free PDF downloads |

**Key publications:**
- "Main Engine Damage" study series — incredibly detailed analysis of engine failures
- "Navigational Claims" studies
- "Cargo Claims" studies — container damage, bulk cargo, tanker operations

#### 9.1.4 Standard Club

| Field | Detail |
|---|---|
| **URL** | https://www.standard-club.com/knowledge-centre/ |
| **Content** | Safety bulletins, loss prevention guides, master's guides |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Download** | Free PDF/online |

#### 9.1.5 North P&I Club

| Field | Detail |
|---|---|
| **URL** | https://www.nepia.com/publications/ |
| **Content** | Loss prevention briefings, crew health guides, cargo guides |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Download** | Free PDFs |

#### 9.1.6 West P&I Club / NorthStandard (merged)

| Field | Detail |
|---|---|
| **URL** | https://www.northstandard.com/insights |
| **Content** | Loss prevention bulletins, safety guides |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |

**Combined P&I Club tokens: ~2-4M**

### 9.2 OCIMF — Oil Companies International Marine Forum

| Field | Detail |
|---|---|
| **URL** | https://www.ocimf.org/publications |
| **Content** | Information papers, safety briefings. Note: Major publications (ISGOTT, MEG, TMSA) are sold commercially |
| **Volume** | Free subset: **Estimated 100K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) for content available |
| **Legal Status** | ⚠️ Major publications are copyrighted and sold. Only free briefings/papers are usable |
| **Download** | PDF downloads for free publications |

### 9.3 ICS — International Chamber of Shipping

| Field | Detail |
|---|---|
| **URL** | https://www.ics-shipping.org/resources/ |
| **Content** | Position papers, fact sheets, guidance on regulations. Major guides (Bridge Procedures Guide, ISGINTT) are sold commercially |
| **Volume** | Free subset: **Estimated 100K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Free resources generally permissive; commercial publications copyrighted |

### 9.4 INTERTANKO / INTERCARGO

| Field | Detail |
|---|---|
| **URLs** | https://www.intertanko.com/publications / https://www.intercargo.org/publications |
| **Content** | Safety bulletins, best practice guides for tanker and bulk carrier operations |
| **Volume** | **Estimated 100K-300K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Some publications freely available, others member-only |

### 9.5 CHIRP Maritime — Confidential Hazardous Incident Reporting Programme

| Field | Detail |
|---|---|
| **URL** | https://www.chirpmaritime.org/reports/ |
| **Content** | Anonymized reports of maritime safety incidents with expert analysis and recommendations |
| **Volume** | 100+ MARITIME FEEDBACK publications. **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Unique content: real-world incidents from crew perspectives with expert analysis |
| **Legal Status** | Published for safety awareness, generally permissive for educational use |
| **Download** | PDF downloads of quarterly MARITIME FEEDBACK publications |

---

## 10. ENGINE MANUFACTURER TECHNICAL DOCUMENTATION ⭐⭐⭐

### 10.1 MAN Energy Solutions

| Field | Detail |
|---|---|
| **URL** | https://www.man-es.com/marine/products/planning-tools-and-downloads/technical-papers |
| **Content** | Technical papers on two-stroke and four-stroke engines, propulsion, LNG, methanol, ammonia fuel, turbochargers, exhaust aftertreatment |
| **Volume** | ~100+ technical papers, each 20-80 pages. **Estimated 1-2M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Definitive marine diesel engine documentation |
| **Legal Status** | Published for customer/industry education. Generally permissive for non-commercial educational use |
| **Download** | Free PDF downloads from MAN website |

**Key publications (all free PDFs):**
- "Basic Principles of Ship Propulsion" — 96 pages, excellent foundational text
- "Propulsion Trends in Container Vessels" — detailed load analysis
- "Tier III two-stroke technology" — SCR, EGR systems
- "MAN B&W Two-Stroke Marine Engines" — engine selection guide
- "MAN B&W Vibration Characteristics" — hull vibration analysis
- "ME-C/ME-B engines — TII/TIII Compliance"
- "LPG as Fuel" / "Methanol as Fuel" / "Ammonia as Fuel" — alternative fuel series
- "Exhaust Gas Emission Control Today and Tomorrow"
- "Soot Deposits and Fires in Exhaust Gas Boilers" — common engineering problem

**This is some of the best marine engineering training data available anywhere.**

### 10.2 Wärtsilä

| Field | Detail |
|---|---|
| **URL** | https://www.wartsila.com/marine/insights |
| **Also** | Wärtsilä Encyclopedia of Marine and Energy Technology: https://www.wartsila.com/encyclopedia |
| **Content** | Technical articles, white papers, product documentation, the excellent Encyclopedia of Marine and Energy Technology |
| **Volume** | **Estimated 1-2M tokens** (especially the Encyclopedia) |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | Published for industry education. Encyclopedia is freely browsable online |
| **Download** | White papers: PDF download (some require registration). Encyclopedia: web scraping needed |

**The Wärtsilä Encyclopedia is a TREASURE:**
- Comprehensive technical articles on every marine engineering topic
- Covers engines, propulsion, electrical systems, automation, environmental systems
- Written in clear, educational English
- Organized alphabetically — easy to scrape systematically

**Scraping the Encyclopedia:**
```python
# Key sections of Wärtsilä Encyclopedia to extract
sections = [
    "engine-technology", "propulsion", "electrical-systems",
    "automation", "environmental-solutions", "gas-systems",
    "fuel-systems", "ship-design", "offshore"
]
# Each section contains multiple detailed articles
# Total estimated: 500K-1M tokens from Encyclopedia alone
```

### 10.3 Caterpillar Marine

| Field | Detail |
|---|---|
| **URL** | https://www.cat.com/en_US/by-industry/marine/technical-resources.html |
| **Content** | Marine application guides, technical papers on medium-speed marine engines |
| **Volume** | **Estimated 100K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Published for customers, generally permissive |

### 10.4 ABB Marine & Ports

| Field | Detail |
|---|---|
| **URL** | https://new.abb.com/marine/references-and-articles |
| **Content** | Technical papers on electric propulsion, power systems, Azipod drives, automation, shore connection |
| **Volume** | **Estimated 200K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Published for industry education |
| **Download** | PDF downloads, some require registration |

### 10.5 Alfa Laval Marine

| Field | Detail |
|---|---|
| **URL** | https://www.alfalaval.com/industries/marine-transportation/ |
| **Content** | Technical guides on fuel treatment, freshwater generation, boiler systems, ballast water treatment, exhaust gas cleaning |
| **Volume** | **Estimated 100K-300K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Download** | PDF downloads, registration often required |

---

## 11. OPEN EDUCATIONAL RESOURCES ⭐⭐

### 11.1 MIT OpenCourseWare — Naval Architecture & Marine Engineering

| Field | Detail |
|---|---|
| **URL** | https://ocw.mit.edu/search/?q=naval+architecture |
| **Key Courses** | 2.700 Principles of Naval Architecture, 2.019 Design of Ocean Systems, 13.024 Numerical Marine Hydrodynamics |
| **Content** | Lecture notes, problem sets, reading assignments |
| **Volume** | **Estimated 200K-500K tokens** across naval architecture courses |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — MIT academic quality, but quite theoretical |
| **Legal Status** | **Creative Commons BY-NC-SA 4.0** — suitable for non-commercial AI training |
| **Download** | Direct downloads of PDF/HTML lecture notes |

**Key courses:**
- 2.700/2.701: Principles of Naval Architecture
- 2.019: Design of Ocean Systems
- 2.011: Introduction to Ocean Science and Engineering
- 13.024: Numerical Marine Hydrodynamics
- 2.612: Marine Power and Propulsion

### 11.2 Open Textbooks

| Resource | URL | Content | Tokens |
|---|---|---|---|
| **OpenStax** | openstax.org | Physics, Engineering Mechanics (foundation for marine engineering) | 500K+ |
| **LibreTexts Engineering** | eng.libretexts.org | Fluid mechanics, thermodynamics, materials science | 500K-1M |
| **SNAME Transactions** (older issues) | sname.org/publications | Ship design, hydrodynamics (older issues may be public domain) | 200K-500K |

### 11.3 Maritime University Thesis Repositories

| University | Repository URL | Content | Est. Tokens |
|---|---|---|---|
| **World Maritime University (WMU)** | https://commons.wmu.se/ | Dissertations on shipping, maritime law, port management, safety | 2-3M |
| **SUNY Maritime** | Via ProQuest/institutional repo | Maritime engineering theses | 200K-500K |
| **Cal Maritime** | Library institutional repository | Maritime technology theses | 100K-300K |
| **Chalmers University** (Shipping & Marine Tech) | https://research.chalmers.se/ | Ship design, marine engineering research | 300K-500K |
| **Newcastle University** (Marine Sciences) | https://theses.ncl.ac.uk/ | Naval architecture, marine engineering | 300K-500K |
| **University of Strathclyde** (Naval Architecture) | https://strathprints.strath.ac.uk/ | Ship design, marine engineering | 300K-500K |

**WMU Commons is the highest value source** — hundreds of full master's dissertations on maritime topics, all freely downloadable as PDFs.

### 11.4 Project Gutenberg — Historical Maritime Texts

| Field | Detail |
|---|---|
| **URL** | https://www.gutenberg.org/ (search: "seamanship", "navigation", "naval architecture", "marine engineering") |
| **Content** | Public domain maritime textbooks from pre-1927 era |
| **Volume** | **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐ (3/5) — Historical value, some concepts outdated but fundamentals still relevant |
| **Legal Status** | **Public domain** — fully usable |
| **Download** | Direct text/HTML downloads |

**Key texts available:**
- "The Elements of Navigation" (various editions)
- "Marine Steam Engine" textbooks
- "Seamanship" manuals
- "Naval Architecture" early textbooks
- Bowditch "American Practical Navigator" (early editions)

---

## 12. NOAA PUBLICATIONS ⭐⭐⭐

### 12.1 American Practical Navigator (Bowditch)

| Field | Detail |
|---|---|
| **URL** | https://msi.nga.mil/Publications/APN |
| **Content** | THE definitive navigation reference — 900+ pages covering celestial navigation, electronic navigation, tides, currents, weather, voyage planning |
| **Volume** | ~900 pages. **Estimated 350K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — The single most important navigation reference in English |
| **Legal Status** | **Public domain** — US government publication |
| **Download** | Free PDF from NGA (National Geospatial-Intelligence Agency) |

### 12.2 Sight Reduction Tables for Marine Navigation (Pub. 229)

| Field | Detail |
|---|---|
| **URL** | https://msi.nga.mil/Publications/SR229 |
| **Content** | Celestial navigation tables |
| **Volume** | Mostly tabular, limited text |
| **Quality** | ⭐⭐⭐ (3/5) for LLM training |
| **Legal Status** | **Public domain** |

### 12.3 Radar Navigation and Maneuvering Board Manual (Pub. 1310)

| Field | Detail |
|---|---|
| **URL** | https://msi.nga.mil/Publications/Radar |
| **Content** | Comprehensive radar navigation manual — operation, interpretation, maneuvering boards, collision avoidance |
| **Volume** | **Estimated 100K-150K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) |
| **Legal Status** | **Public domain** |

### 12.4 International Code of Signals (Pub. 102)

| Field | Detail |
|---|---|
| **URL** | https://msi.nga.mil/Publications/ICS |
| **Content** | Signal flags, distress signals, radiotelephone procedures |
| **Volume** | **Estimated 50K-80K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | **Public domain** |

### 12.5 NOAA Chart Manuals & Coast Pilot

| Field | Detail |
|---|---|
| **URL** | https://nauticalcharts.noaa.gov/publications/coast-pilot/index.html |
| **Content** | US Coast Pilot — 9 volumes covering navigation details of US waters, port information |
| **Volume** | 9 volumes, thousands of pages. **Estimated 2-3M tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Excellent for navigation content |
| **Legal Status** | **Public domain** |
| **Download** | Free PDF downloads from NOAA |

### 12.6 NWS Marine Weather Services

| Field | Detail |
|---|---|
| **URL** | https://www.weather.gov/marine/ |
| **Content** | Marine weather guides, storm identification, sea state descriptions |
| **Volume** | **Estimated 100K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | **Public domain** |

---

## 13. ONLINE MARITIME KNOWLEDGE BASES ⭐⭐

### 13.1 MarineInsight

| Field | Detail |
|---|---|
| **URL** | https://www.marineinsight.com/ |
| **Content** | 2000+ articles covering marine engineering, naval architecture, navigation, shipping, maritime law, safety |
| **Volume** | **Estimated 3-5M tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Good educational content, written for maritime professionals and students |
| **Legal Status** | ⚠️ **Copyrighted** — Articles are copyrighted by Marine Insight. Use would require scraping and would be under fair use dispute. Consider reaching out to the publisher for permission or using as reference only |
| **Download** | Web scraping required. robots.txt may restrict automated access |

**Content areas:**
- Marine Engineering (engine systems, aux machinery, electrical, boilers)
- Naval Architecture (stability, ship construction, design)
- Navigation (ECDIS, ARPA, GMDSS, celestial)
- Safety (SOLAS, fire safety, life-saving appliances)
- Environment (MARPOL, ballast water, emissions)

### 13.2 Bright Hub Engineering — Maritime Section

| Field | Detail |
|---|---|
| **URL** | https://www.brighthubengineering.com/marine-engines-machinery/ and related sections |
| **Content** | Marine engineering articles, tutorials, explanations |
| **Volume** | **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐ (3/5) — Good introductory level, some articles lack depth |
| **Legal Status** | ⚠️ **Copyrighted** |
| **Download** | Web scraping needed |

### 13.3 Wikipedia Maritime Articles

| Field | Detail |
|---|---|
| **URL** | Various Wikipedia categories |
| **Content** | Comprehensive articles on ship types, marine engineering systems, navigation instruments, maritime regulations, famous ships |
| **Volume** | **Estimated 2-3M tokens** from maritime-related categories |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Variable, but generally good for foundational knowledge |
| **Legal Status** | **Creative Commons BY-SA 3.0** — freely usable with attribution |
| **Download** | Use Wikipedia API or Wikimedia dumps |

**Key Wikipedia categories to extract:**
```
Category:Marine engineering
Category:Naval architecture
Category:Marine propulsion
Category:Ship construction
Category:Nautical terms
Category:Maritime safety
Category:Ship types
Category:Shipbuilding
Category:Marine boilers
Category:Marine diesel engines
Category:Ship stability
Category:Navigation
Category:Celestial navigation
Category:Maritime law
Category:International Maritime Organization
Category:Classification societies
Category:Marine pollution
Category:Maritime accidents and incidents
Category:Ship machinery
```

**Extraction method:**
```python
import wikipediaapi

wiki = wikipediaapi.Wikipedia('en')
categories = [
    "Marine_engineering", "Naval_architecture", "Marine_propulsion",
    "Ship_construction", "Nautical_terms", "Maritime_safety",
    # ... all categories listed above
]

for cat_name in categories:
    cat = wiki.page(f"Category:{cat_name}")
    for page_title in cat.categorymembers:
        page = wiki.page(page_title)
        if page.exists():
            text = page.text  # Full article text
            # Clean, deduplicate, save
```

### 13.4 Wärtsilä Encyclopedia of Marine Technology (repeated from Section 10.2)

Deserves special mention as an online knowledge base — possibly the best single freely-accessible online reference for marine engineering.

---

## 14. YOUTUBE TRANSCRIPT MINING ⭐⭐

### 14.1 Chief MAKOi (Marine Engineering Channel)

| Field | Detail |
|---|---|
| **URL** | https://www.youtube.com/@ChiefMAKOi |
| **Content** | Marine engine operation, maintenance, troubleshooting, engine room operations |
| **Volume** | ~200+ videos, 10-30 min each. **Estimated 500K-1M tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Real chief engineer explaining real operations |
| **Legal Status** | ⚠️ YouTube ToS technically prohibits automated transcript downloading, but transcripts can be accessed via YouTube's API or `yt-dlp --write-subs`. Fair use is arguable for educational AI training. Consider reaching out for permission |
| **Download** | `yt-dlp --write-auto-sub --sub-lang en --skip-download URL` |

### 14.2 Casual Navigation

| Field | Detail |
|---|---|
| **URL** | https://www.youtube.com/@CasualNavigation |
| **Content** | Navigation, ship operations, maritime incidents explained, maritime law |
| **Volume** | ~200+ videos. **Estimated 400K-800K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Former navigation officer, excellent explanations |
| **Download** | Same method as above |

### 14.3 Marine Insight Videos

| Field | Detail |
|---|---|
| **URL** | https://www.youtube.com/@MarineInsightVideos |
| **Content** | Marine engineering, safety procedures, ship operations |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |

### 14.4 Other Maritime YouTube Channels

| Channel | Content Focus | Est. Tokens |
|---|---|---|
| **What is Going on With Shipping** | Shipping industry analysis | 200K-400K |
| **Marine Online** | Marine engineering tutorials | 100K-200K |
| **Mariner's World** | Maritime operations | 100K-200K |
| **Harry's Marine Engineering** | Engine room operations | 100K-200K |
| **Seaways Magazine** (Nautical Institute) | Safety at sea | 100K-200K |

**Transcript extraction method:**
```bash
# Using yt-dlp to extract auto-generated subtitles
pip install yt-dlp

# Single video
yt-dlp --write-auto-sub --sub-lang en --skip-download --sub-format vtt \
  "https://www.youtube.com/watch?v=VIDEO_ID"

# Entire channel (all videos)
yt-dlp --write-auto-sub --sub-lang en --skip-download --sub-format vtt \
  "https://www.youtube.com/@ChiefMAKOi/videos"

# Post-processing: VTT to clean text
# Remove timestamps, duplicated lines, format tags
```

**Combined YouTube tokens: ~1.5-3M**

**Quality consideration:** Auto-generated transcripts contain errors (especially technical terms like "purifier" → "purifier/provider"). You'll need a post-processing step to fix common maritime term transcription errors:
```python
# Common transcript corrections needed
corrections = {
    "see triple gas": "C-triple-gas",  # CO2 
    "em cee are": "MCR",
    "be em ee pee": "BMEP",
    "so less": "SOLAS",
    "my poll": "MARPOL",
    "scavenge air": "scavenge air",  # often correct
    "turbo charger": "turbocharger",
    # Build domain-specific correction dictionary
}
```

---

## 15. NAUTICAL INSTITUTE PUBLICATIONS ⭐⭐

| Field | Detail |
|---|---|
| **URL** | https://www.nautinst.org/resources.html |
| **Content** | Safety briefings, MARS (Mariners' Alerting and Reporting Scheme) reports, Seaways magazine articles |
| **Volume** | MARS reports alone: **Estimated 300K-500K tokens** |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — MARS reports are real incident reports from mariners worldwide |
| **Legal Status** | MARS reports appear freely accessible online. Full publications (books) are copyrighted |
| **Download** | MARS reports available on website |

**MARS reports** are particularly valuable — short incident reports covering navigation near-misses, engineering failures, safety incidents, with lessons learned. Thousands available.

---

## 16. TECHNICAL STANDARDS (FREE VERSIONS/SUMMARIES) ⭐

### 16.1 ISO Maritime Standards

| Field | Detail |
|---|---|
| **Content** | ISO 8217 (marine fuels), ISO 15544 (offshore platforms), ISO 19847/19848 (ship data), etc. |
| **Legal Status** | ⚠️ **Full standards are copyrighted and sold by ISO.** Only abstracts/previews are free |
| **Usable content** | Standard summaries, abstracts, and scope descriptions — minimal volume |
| **Alternative** | Class society rules often implement ISO standards and describe requirements in detail — use those instead |

### 16.2 ASTM/API Standards for Marine Equipment

| Field | Detail |
|---|---|
| **Legal Status** | ⚠️ **Copyrighted and sold** |
| **Alternative** | Equipment manufacturer documentation describes compliance with these standards |

### 16.3 NFPA Maritime Fire Protection

| Field | Detail |
|---|---|
| **URL** | https://www.nfpa.org/codes-and-standards (NFPA 301, 302, 303, 306, 312) |
| **Legal Status** | NFPA standards can be viewed online for free (read-only) but are copyrighted |
| **Volume** | Limited for extraction |
| **Alternative** | USCG fire safety NVICs and MCA fire safety MGNs cover the same ground and are public domain/OGL |

---

## 17. ADDITIONAL HIGH-VALUE SOURCES

### 17.1 ITF (International Transport Workers' Federation) Publications

| Field | Detail |
|---|---|
| **URL** | https://www.itfseafarers.org/en/know-your-rights |
| **Content** | Seafarer rights, MLC compliance guides, safety guides |
| **Volume** | **Estimated 100K-200K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) — Worker-focused, practical |
| **Legal Status** | Published for seafarer education |

### 17.2 InterManager Safety Campaign Materials

| Field | Detail |
|---|---|
| **URL** | https://www.intermanager.org/ |
| **Content** | Safety campaign materials, best practices for ship management |
| **Volume** | **Estimated 50K-100K tokens** |
| **Quality** | ⭐⭐⭐ (3/5) |

### 17.3 BIMCO (Baltic and International Maritime Council)

| Field | Detail |
|---|---|
| **URL** | https://www.bimco.org/insights-and-information |
| **Content** | Shipping market analysis, regulatory guides, cyber security guides |
| **Volume** | Free subset: **Estimated 100K-300K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | Some publications are freely available; others require membership |

### 17.4 RINA (Royal Institution of Naval Architects) — Free Resources

| Field | Detail |
|---|---|
| **URL** | https://www.rina.org.uk/ |
| **Content** | Conference papers, technical articles (some freely available) |
| **Volume** | **Estimated 200K-500K tokens** from free resources |
| **Quality** | ⭐⭐⭐⭐⭐ (5/5) — Top-tier naval architecture content |
| **Legal Status** | Check individual papers; conference proceedings often copyrighted |

### 17.5 Maritime New Zealand (MNZ)

| Field | Detail |
|---|---|
| **URL** | https://www.maritimenz.govt.nz/public/publications/ |
| **Content** | Maritime rules, guidelines, safety bulletins, investigation reports |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |
| **Legal Status** | New Zealand Government open license |

### 17.6 Transport Malta — Merchant Shipping Directorate

| Field | Detail |
|---|---|
| **URL** | https://www.transport.gov.mt/maritime/merchant-shipping-directorate-524 |
| **Content** | Merchant Shipping Notices, circulars for Malta-flagged vessels (large registry) |
| **Volume** | **Estimated 200K-400K tokens** |
| **Quality** | ⭐⭐⭐⭐ (4/5) |

---

## 18. SYSTEMATIC DATA HARVESTING PLAN

### Phase 1: Quick Wins (Week 1-2) — Target: 10-15M tokens

| # | Source | Method | Est. Tokens | Priority |
|---|---|---|---|---|
| 1 | MAIB Reports | Scrape GOV.UK, download PDFs, extract text | 5-8M | 🔴 HIGHEST |
| 2 | Bowditch (APN) | Download PDF, extract text | 350-500K | 🔴 HIGH |
| 3 | USCG NVICs & Marine Safety Manual | Download from DCO website | 2-3M | 🔴 HIGH |
| 4 | UK MCA MGNs/MSNs/MINs | Download from GOV.UK | 2-3M | 🔴 HIGH |
| 5 | NOAA Coast Pilot (9 volumes) | Download from NOAA | 2-3M | 🟡 HIGH |
| 6 | MCA COSWP | Download single PDF | 150-200K | 🟡 HIGH |
| 7 | USCG Exam Questions | Download from NMC | 500K-1M | 🟡 HIGH |

### Phase 2: Medium Effort (Week 2-4) — Target: 8-12M tokens

| # | Source | Method | Est. Tokens | Priority |
|---|---|---|---|---|
| 8 | NTSB Marine Reports | CAROL database search + download | 2-3M | 🔴 HIGH |
| 9 | P&I Club Publications (all clubs) | Download PDFs from each club | 2-4M | 🔴 HIGH |
| 10 | MAN Technical Papers | Download from MAN website | 1-2M | 🟡 HIGH |
| 11 | Wikipedia Maritime Articles | Wikipedia API extraction | 2-3M | 🟡 MEDIUM |
| 12 | TSB Canada Marine Reports | Download by year | 1.5-2.5M | 🟡 MEDIUM |
| 13 | ATSB Marine Reports | Download from ATSB | 1-2M | 🟡 MEDIUM |
| 14 | DNV Free Rules & Papers | Download from DNV | 1-2M | 🟡 MEDIUM |

### Phase 3: Deep Harvesting (Week 4-6) — Target: 5-10M tokens

| # | Source | Method | Est. Tokens | Priority |
|---|---|---|---|---|
| 15 | Wärtsilä Encyclopedia | Web scraping | 500K-1M | 🟡 MEDIUM |
| 16 | WMU Thesis Repository | Download dissertations | 2-3M | 🟡 MEDIUM |
| 17 | ABS/BV/ClassNK Rules | Download PDFs | 1-2M | 🟡 MEDIUM |
| 18 | IACS Unified Requirements | Download from IACS | 500K-1M | 🟡 MEDIUM |
| 19 | YouTube Transcripts | yt-dlp transcript extraction | 1-2M | 🟢 LOWER |
| 20 | Flag State Circulars (RMI, Liberia) | Download PDFs | 500K-1M | 🟢 LOWER |
| 21 | Other Investigation Bodies (DK, NL, NO, DE, SG) | Scrape individual sites | 2-4M | 🟢 LOWER |
| 22 | Project Gutenberg Maritime | Search and download | 500K-1M | 🟢 LOWER |
| 23 | MarineInsight Articles | Web scraping (check legality) | 3-5M | ⚠️ LEGAL RISK |
| 24 | CHIRP Maritime Feedback | Download PDFs | 200-400K | 🟢 LOWER |
| 25 | Nautical Institute MARS | Scrape MARS reports | 300-500K | 🟢 LOWER |

---

## 19. TEXT EXTRACTION PIPELINE

### PDF to Text (Primary Pipeline)

Most maritime publications are PDFs. Quality text extraction is critical.

```python
# Recommended pipeline for maritime PDF extraction

import pdfplumber
import re

def extract_maritime_pdf(pdf_path):
    """Extract and clean text from maritime technical PDF."""
    full_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                # Clean common PDF artifacts
                text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines
                text = re.sub(r'  +', ' ', text)  # Multiple spaces
                text = re.sub(r'-\n', '', text)  # Hyphenated line breaks
                text = re.sub(r'(?<=[a-z])\n(?=[a-z])', ' ', text)  # Rejoin lines
                full_text.append(text)
    
    return '\n\n'.join(full_text)

# Alternative for scanned PDFs (OCR needed):
# Use pytesseract + pdf2image
# pip install pytesseract pdf2image
```

### Web Scraping Template

```python
import requests
from bs4 import BeautifulSoup
import time
import os

def scrape_maritime_site(base_url, output_dir, css_selector='article'):
    """Generic scraper for maritime knowledge sites."""
    os.makedirs(output_dir, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Maritime-Research-Bot/1.0 (Educational AI Training)'
    })
    
    resp = session.get(base_url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    articles = soup.select(css_selector)
    for i, article in enumerate(articles):
        text = article.get_text(separator='\n', strip=True)
        with open(f"{output_dir}/article_{i:04d}.txt", 'w') as f:
            f.write(text)
        time.sleep(1)  # Respectful rate limiting
```

### Token Counting

```python
import tiktoken

def count_tokens(text, model="cl100k_base"):
    """Count tokens for estimating corpus size."""
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))

# Rule of thumb: 1 page ≈ 300-400 tokens
# 1 standard technical document page ≈ 350 tokens
```

---

## 20. LEGAL FRAMEWORK SUMMARY

| Source Type | Legal Status | Confidence for AI Training |
|---|---|---|
| **US Government publications** (USCG, NTSB, NOAA, NGA) | Public domain (17 USC §105) | ✅ **100% safe** |
| **UK Government publications** (MAIB, MCA) | Open Government Licence v3.0 | ✅ **100% safe** |
| **Australian Government** (ATSB, AMSA) | CC BY 3.0 AU | ✅ **100% safe** |
| **Canadian Government** (TSB) | Open Government Licence | ✅ **100% safe** |
| **Wikipedia** | CC BY-SA 3.0 | ✅ **Safe with attribution** |
| **MIT OCW** | CC BY-NC-SA 4.0 | ✅ **Safe for non-commercial** |
| **Classification Society rules** (freely published) | Varies — generally published for reference | 🟡 **Fair use defensible** |
| **P&I Club publications** (freely distributed) | Published for maritime safety | 🟡 **Educational fair use** |
| **Manufacturer tech papers** (freely downloadable) | Published for customer/industry education | 🟡 **Educational fair use** |
| **IMO documents** | Copyrighted by IMO | 🟠 **Use government re-publications** |
| **YouTube transcripts** | YouTube ToS restrictions | 🟠 **Gray area — seek permission** |
| **MarineInsight / Bright Hub** | Copyrighted articles | 🔴 **Requires permission** |
| **ISO/API/NFPA standards** | Copyrighted, sold commercially | 🔴 **Do not use** |

---

## 21. FINAL TOKEN ESTIMATES — CONSERVATIVE vs OPTIMISTIC

### Conservative (High-confidence, legally clear sources only)

| Source | Tokens |
|---|---|
| MAIB Reports | 5M |
| NTSB Marine Reports | 2M |
| ATSB + TSB + Other Investigation Bodies | 3M |
| USCG Publications (NVICs, Manuals, MSIBs, Exam Qs) | 3M |
| UK MCA (MGNs, MSNs, MINs, COSWP) | 2M |
| NOAA/NGA (Bowditch, Coast Pilot, Radar Manual) | 3M |
| Wikipedia Maritime Articles | 2M |
| AMSA + Singapore MPA + Flag States | 1M |
| **Subtotal — Legally Safe** | **21M** |

### Optimistic (Including fair-use sources)

| Source | Tokens |
|---|---|
| Conservative base | 21M |
| P&I Club Publications (all clubs) | 3M |
| Classification Society Free Pubs (DNV, ABS, LR, BV) | 3M |
| IACS Unified Requirements | 500K |
| MAN + Wärtsilä + ABB Technical Papers | 3M |
| WMU + Other Maritime Theses | 2M |
| MIT OCW Naval Architecture | 300K |
| YouTube Transcripts (with permission) | 1.5M |
| Nautical Institute MARS + CHIRP | 500K |
| Project Gutenberg Maritime | 500K |
| ICS/OCIMF/INTERTANKO Free Pubs | 300K |
| **Subtotal — Including Fair Use** | **35.6M** |

---

## 22. RECOMMENDED DOWNLOAD ORDER

**Start here — maximum impact, minimum effort, zero legal risk:**

1. **Bowditch (APN)** — Single PDF, 500K tokens, public domain, 30 minutes to process
2. **MCA COSWP** — Single PDF, 200K tokens, OGL, 15 minutes
3. **NOAA Coast Pilot Vol 1-9** — 9 PDFs, 2-3M tokens, public domain, 1 hour
4. **MAIB Reports** — Write scraper (2 hours), download all reports (~800 PDFs), extract text (5-8M tokens)
5. **USCG NVICs** — Download key circulars (1-2 hours), 1-2M tokens
6. **UK MCA MGNs** — Download from GOV.UK (1-2 hours), 1-1.5M tokens
7. **NTSB Major Marine Reports** — Search CAROL, download PDFs (2-3 hours), 2-3M tokens
8. **TSB Canada + ATSB Australia** — 2-3 hours each, 1.5-2.5M tokens each
9. **Wikipedia Maritime Categories** — Write extraction script (1 hour), run (30 min), 2-3M tokens
10. **MAN Technical Papers** — Download from website (1-2 hours), 1-2M tokens

**Following this order, you can reach 15-20M additional tokens in the first week.**

---

## APPENDIX A: MAIB REPORT SCRAPER (COMPLETE)

```python
#!/usr/bin/env python3
"""
MAIB Report Scraper — Downloads all MAIB marine accident investigation reports
from GOV.UK and extracts text content.

Legal: Open Government Licence v3.0 — free to use for any purpose
"""

import requests
from bs4 import BeautifulSoup
import pdfplumber
import os
import time
import json
from pathlib import Path

OUTPUT_DIR = "data/maib_reports"
TEXT_DIR = "data/maib_reports/text"
PDF_DIR = "data/maib_reports/pdf"
BASE_URL = "https://www.gov.uk/maib-reports"

def setup_dirs():
    os.makedirs(TEXT_DIR, exist_ok=True)
    os.makedirs(PDF_DIR, exist_ok=True)

def get_report_links():
    """Scrape all MAIB report page links from GOV.UK."""
    links = []
    page = 1
    while True:
        url = f"{BASE_URL}?page={page}"
        print(f"Fetching page {page}: {url}")
        resp = requests.get(url, headers={'User-Agent': 'Maritime-Research/1.0'})
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, 'html.parser')
        report_links = soup.select('a.gem-c-document-list__item-title')
        if not report_links:
            # Try alternative selectors
            report_links = soup.select('li.gem-c-document-list__item a')
        if not report_links:
            break
        for link in report_links:
            href = link.get('href', '')
            if '/maib-reports/' in href:
                full_url = f"https://www.gov.uk{href}" if href.startswith('/') else href
                links.append({'url': full_url, 'title': link.get_text(strip=True)})
        page += 1
        time.sleep(1)
    
    print(f"Found {len(links)} report links")
    return links

def download_report_pdf(report_url):
    """Visit report page and find/download the PDF attachment."""
    resp = requests.get(report_url, headers={'User-Agent': 'Maritime-Research/1.0'})
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Find PDF attachment links
    pdf_links = []
    for a in soup.find_all('a', href=True):
        if a['href'].endswith('.pdf'):
            pdf_url = a['href']
            if pdf_url.startswith('/'):
                pdf_url = f"https://www.gov.uk{pdf_url}"
            elif not pdf_url.startswith('http'):
                pdf_url = f"https://assets.publishing.service.gov.uk{pdf_url}"
            pdf_links.append(pdf_url)
    
    return pdf_links

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber."""
    try:
        full_text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
        return '\n\n'.join(full_text)
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}")
        return ""

def main():
    setup_dirs()
    
    # Step 1: Get all report links
    print("=== Step 1: Getting report links ===")
    reports = get_report_links()
    
    with open(f"{OUTPUT_DIR}/report_index.json", 'w') as f:
        json.dump(reports, f, indent=2)
    
    # Step 2: Download PDFs and extract text
    print("=== Step 2: Downloading and extracting ===")
    total_chars = 0
    
    for i, report in enumerate(reports):
        slug = report['url'].rstrip('/').split('/')[-1]
        text_path = f"{TEXT_DIR}/{slug}.txt"
        
        if os.path.exists(text_path):
            print(f"[{i+1}/{len(reports)}] Already processed: {slug}")
            continue
        
        print(f"[{i+1}/{len(reports)}] Processing: {slug}")
        
        try:
            pdf_urls = download_report_pdf(report['url'])
            
            combined_text = f"# MAIB Report: {report['title']}\n\n"
            combined_text += f"Source: {report['url']}\n\n---\n\n"
            
            for pdf_url in pdf_urls:
                pdf_filename = pdf_url.split('/')[-1]
                pdf_path = f"{PDF_DIR}/{pdf_filename}"
                
                # Download PDF
                if not os.path.exists(pdf_path):
                    pdf_resp = requests.get(pdf_url)
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_resp.content)
                
                # Extract text
                text = extract_text_from_pdf(pdf_path)
                combined_text += text + "\n\n"
            
            # Save extracted text
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            
            total_chars += len(combined_text)
            print(f"  Extracted {len(combined_text):,} chars")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(2)  # Rate limiting
    
    print(f"\n=== Complete ===")
    print(f"Total characters extracted: {total_chars:,}")
    print(f"Estimated tokens: ~{total_chars // 4:,}")

if __name__ == "__main__":
    main()
```

---

## APPENDIX B: WIKIPEDIA MARITIME EXTRACTOR (COMPLETE)

```python
#!/usr/bin/env python3
"""
Extract all maritime-related Wikipedia articles for AI training.
License: CC BY-SA 3.0 — usable with attribution.
"""

import wikipediaapi
import json
import os
import time
from collections import deque

OUTPUT_DIR = "data/wikipedia_maritime"
os.makedirs(OUTPUT_DIR, exist_ok=True)

wiki = wikipediaapi.Wikipedia(
    user_agent='Maritime-AI-Research/1.0 (educational project)',
    language='en'
)

# Root categories to traverse
ROOT_CATEGORIES = [
    "Marine_engineering",
    "Naval_architecture", 
    "Marine_propulsion",
    "Shipbuilding",
    "Nautical_terms",
    "Maritime_safety",
    "Navigation",
    "Celestial_navigation",
    "Ship_types",
    "Maritime_law",
    "International_Maritime_Organization",
    "Marine_pollution",
    "Ship_construction",
    "Marine_diesel_engines",
    "Marine_boilers",
    "Steering_gear",
    "Anchoring",
    "Mooring_(watercraft)",
    "Deck_machinery",
    "Maritime_incidents",
    "SOLAS",
    "Classification_societies",
    "Merchant_navy",
    "Cargo_ships",
    "Tankers",
    "Bulk_carriers",
    "Container_ships",
    "Liquefied_natural_gas_carriers",
    "Tugboats",
    "Offshore_platforms",
]

def get_category_members(cat_title, max_depth=2):
    """Recursively get all article titles from a category tree."""
    visited_cats = set()
    articles = {}
    queue = deque([(cat_title, 0)])
    
    while queue:
        cat, depth = queue.popleft()
        if cat in visited_cats or depth > max_depth:
            continue
        visited_cats.add(cat)
        
        cat_page = wiki.page(f"Category:{cat}")
        if not cat_page.exists():
            continue
            
        for title, member in cat_page.categorymembers.items():
            if member.ns == 0:  # Article namespace
                articles[title] = member
            elif member.ns == 14 and depth < max_depth:  # Category namespace
                subcat = title.replace("Category:", "")
                queue.append((subcat, depth + 1))
        
        time.sleep(0.5)
    
    return articles

def extract_article(page):
    """Extract clean text from a Wikipedia page."""
    if not page.exists():
        return None
    return {
        'title': page.title,
        'summary': page.summary,
        'text': page.text,
        'url': page.fullurl,
        'categories': [c for c in page.categories.keys()],
        'char_count': len(page.text)
    }

def main():
    all_articles = {}
    
    # Step 1: Collect all article titles from all categories
    print("=== Collecting article titles from categories ===")
    for cat in ROOT_CATEGORIES:
        print(f"Processing category: {cat}")
        articles = get_category_members(cat, max_depth=2)
        print(f"  Found {len(articles)} articles")
        all_articles.update(articles)
    
    print(f"\nTotal unique articles: {len(all_articles)}")
    
    # Step 2: Extract text from each article
    print("\n=== Extracting article text ===")
    total_chars = 0
    
    for i, (title, page) in enumerate(all_articles.items()):
        output_file = f"{OUTPUT_DIR}/{title.replace('/', '_').replace(' ', '_')[:100]}.json"
        
        if os.path.exists(output_file):
            continue
        
        article_data = extract_article(page)
        if article_data and article_data['char_count'] > 500:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, indent=2, ensure_ascii=False)
            total_chars += article_data['char_count']
            
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(all_articles)}] Total chars: {total_chars:,}")
        
        time.sleep(0.5)
    
    print(f"\n=== Complete ===")
    print(f"Total characters: {total_chars:,}")
    print(f"Estimated tokens: ~{total_chars // 4:,}")

if __name__ == "__main__":
    main()
```

---

## APPENDIX C: UNIVERSAL PDF BATCH DOWNLOADER

```python
#!/usr/bin/env python3
"""
Universal batch PDF downloader and text extractor for maritime data sources.
Handles USCG, MCA GOV.UK, AMSA, and similar government publication sites.
"""

import requests
from bs4 import BeautifulSoup
import pdfplumber
import os
import time
import re
from urllib.parse import urljoin

class MaritimePDFHarvester:
    def __init__(self, output_dir, rate_limit=2.0):
        self.output_dir = output_dir
        self.pdf_dir = os.path.join(output_dir, "pdfs")
        self.text_dir = os.path.join(output_dir, "text")
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Maritime-Research-Bot/1.0 (Educational AI Training)'
        })
        os.makedirs(self.pdf_dir, exist_ok=True)
        os.makedirs(self.text_dir, exist_ok=True)
    
    def find_pdfs_on_page(self, url):
        """Find all PDF links on a page."""
        resp = self.session.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        pdfs = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                full_url = urljoin(url, href)
                title = a.get_text(strip=True) or href.split('/')[-1]
                pdfs.append({'url': full_url, 'title': title})
        return pdfs
    
    def download_pdf(self, url, filename=None):
        """Download a PDF file."""
        if not filename:
            filename = url.split('/')[-1].split('?')[0]
        filepath = os.path.join(self.pdf_dir, filename)
        
        if os.path.exists(filepath):
            return filepath
        
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            return filepath
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    def extract_text(self, pdf_path):
        """Extract clean text from PDF."""
        try:
            texts = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # Clean up
                        text = re.sub(r'-\n', '', text)
                        text = re.sub(r'(?<=[a-z,;])\n(?=[a-z])', ' ', text)
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        texts.append(text)
            return '\n\n'.join(texts)
        except Exception as e:
            print(f"Extraction error for {pdf_path}: {e}")
            return ""
    
    def harvest_page(self, url, label=""):
        """Download all PDFs from a page and extract text."""
        print(f"Harvesting: {label or url}")
        pdfs = self.find_pdfs_on_page(url)
        print(f"  Found {len(pdfs)} PDFs")
        
        total_chars = 0
        for i, pdf_info in enumerate(pdfs):
            safe_name = re.sub(r'[^\w\-.]', '_', pdf_info['title'])[:80] + '.pdf'
            pdf_path = self.download_pdf(pdf_info['url'], safe_name)
            
            if pdf_path:
                text = self.extract_text(pdf_path)
                if len(text) > 100:
                    text_path = os.path.join(
                        self.text_dir, 
                        safe_name.replace('.pdf', '.txt')
                    )
                    with open(text_path, 'w', encoding='utf-8') as f:
                        f.write(f"Source: {pdf_info['url']}\n")
                        f.write(f"Title: {pdf_info['title']}\n\n")
                        f.write(text)
                    total_chars += len(text)
                    print(f"  [{i+1}/{len(pdfs)}] {safe_name}: {len(text):,} chars")
            
            time.sleep(self.rate_limit)
        
        print(f"  Total: {total_chars:,} chars (~{total_chars//4:,} tokens)")
        return total_chars


# Usage examples:

# USCG NVICs
# harvester = MaritimePDFHarvester("data/uscg_nvics")
# harvester.harvest_page("https://www.dco.uscg.mil/Our-Organization/NVIC/", "USCG NVICs")

# UK MCA MGNs
# harvester = MaritimePDFHarvester("data/mca_mgns")
# harvester.harvest_page(
#     "https://www.gov.uk/government/collections/marine-guidance-notices-mgns",
#     "MCA Marine Guidance Notes"
# )

# IACS Unified Requirements
# harvester = MaritimePDFHarvester("data/iacs")
# harvester.harvest_page("https://iacs.org.uk/resolutions/", "IACS Requirements")
```

---

*Document generated for Ship AI Chatbot data sourcing — February 2026*
*Target: 20-30M additional maritime tokens for domain-specific LLM training*
