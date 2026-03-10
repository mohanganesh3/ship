#!/usr/bin/env python3
"""
DEPTH AUDIT — checks not just presence but quality:
- Are documents procedural (step-by-step) or just theoretical mentions?
- How long are documents in each category?
- What sub-topics are missing entirely?
"""
import json, os, glob, re
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "extracted_text")

# Critical procedural sub-topics that MUST have dedicated content
DEEP_TOPICS = {
    # OWS procedures
    "OWS startup procedure":            ["start.*ows","starting.*oily water","ows.*start","bilge pump.*start","activate.*ows"],
    "OWS 15ppm alarm response":         ["15 ppm.*alarm","15ppm alarm","ows alarm","oil content monitor","ocm alarm","overboard discharge"],
    "OWS maintenance":                  ["ows.*clean","clean.*ows","ows.*filter","replace.*membrane","ows.*service"],
    # FWG
    "FWG startup procedure":            ["start.*fwg","starting.*evaporator","fwg.*start","evaporator.*start"],
    "FWG brine salinity control":       ["salinity","brine","salinometer","fresh water.*salinity","tds.*fresh"],
    # GMDSS
    "GMDSS DSC distress call":          ["dsc.*distress","digital selective calling.*distress","mayday.*dsc","dsc call procedure"],
    "EPIRB activation":                 ["epirb.*activ","activat.*epirb","epirb.*procedure","free float","hydrostatic release"],
    "NAVTEX reception":                 ["navtex.*receiv","receive.*navtex","navtex message","navtex station"],
    # ECDIS
    "ECDIS route planning steps":       ["ecdis.*plan","route.*ecdis","ecdis.*waypoint","waypoint.*ecdis","passage plan.*ecdis"],
    "ECDIS chart update":               ["chart update.*ecdis","ecdis.*chart update","ntm.*ecdis","update.*enc"],
    "ECDIS alarm management":           ["ecdis.*alarm","ecdis.*warning","ecdis.*guard zone"],
    # Cargo Tankers
    "Crude oil washing procedure":      ["cow.*procedure","crude oil wash.*procedure","crude oil washing.*step"],
    "Inert gas system operation":       ["inert gas.*operat","ig system.*start","igo2.*percent","oxygen content.*cargo"],
    "Tank gauging / ullage":            ["ullage.*procedure","tape gauge","ullage table","innage","roll.*sounding"],
    # Bulk cargo
    "Bulk cargo loading plan":          ["loading plan.*bulk","cargo plan.*bulk","stability.*bulk","trimming.*plan"],
    "Grain code compliance":            ["grain code","grain stability","grain loading","grain.*sf.*bg"],
    # Bunkering
    "Bunkering checklist":              ["bunkering.*checklist","bunker.*checklist","pre-bunkering","bunker operation.*check"],
    "MARPOL fuel sulphur compliance":   ["sulphur cap","0.5.*sulphur","eca.*sulphur","sulphur.*compliance","lsfo","vlsfo"],
    # PSC
    "PSC deficiency list":              ["deficiency.*code","psc.*deficiency","mou.*deficiency","detained"],
    "PSC expanded inspection":          ["expanded inspection","concentrated inspection","cic.*psc"],
    # PTW
    "Hot work permit procedure":        ["hot work.*permit","permit.*hot work","hotwork"],
    "Enclosed space entry permit":      ["enclosed space.*permit","confined space.*permit","enclosed space entry.*procedure"],
    # Stability
    "Inclining experiment procedure":   ["inclining experiment","inclining test","imomscs"],
    "Free surface effect":              ["free surface.*effect","free surface correction","fsc","loss of gm"],
    "Damage stability SOLAS":           ["damage stability.*solas","damage control","floodable length","permissible length"],
    # Fire
    "CO2 fire system release":          ["co2.*release","release.*co2","fixed co2","total flooding"],
    "Fire investigation response":      ["fire.*response","fire.*action","fire muster","firefighting station","boundary cool"],
    # LSA
    "Lifeboat release / launch":        ["lifeboat.*launch","launch.*lifeboat","lifeboat.*lowering","on load release","off load release"],
    "SART operation":                   ["sart.*operat","search.*rescue.*transponder","radar transponder"],
    # Engine room
    "Main engine fuel changeover":      ["fuel changeover","fuel oil changeover","hfo.*mdo","switch.*hfo","eca.*fuel switch"],
    "Main engine starting procedure":   ["main engine.*start","starting.*main engine","starting air","engine start procedure"],
    "Engine room fire procedure":       ["engine room fire","ero.*fire","manned.*fire","fire in engine"],
    # Voyage
    "APEM passage planning":            ["apem","assess.*plan.*execute.*monitor","passage planning.*stages"],
    "Notice to mariners":               ["notice to mariners","ntm","chart correction","weekly notice","admiralty ntm"],
    # MLC
    "MLC rest hours record":            ["rest hours.*mlc","hours of rest","mlc.*record","minimum rest"],
    "Crew complaint procedure":         ["crew.*complaint","grievance.*procedure","mlc.*complaint","onboard complaint"],
    # Drydock
    "Drydocking checklist":             ["drydock.*check","drydocking.*list","dry dock.*preparation"],
    # SMS/ISM
    "Near miss reporting":              ["near miss","near-miss","unsafe act","unsafe condition","hazardous occurrence"],
    "Master override":                  ["master.*override","captain.*override","master's discretion"],
}

def has_procedural(text):
    """Check if text has step-by-step procedural language."""
    markers = ["step 1","step 2","step one","step two","1.","2.","3.",
               "first,","then,","next,","ensure that","make sure","check that",
               "verify","open valve","close valve","start the","stop the",
               "procedure:","steps:","how to "]
    text_l = text.lower()
    count = sum(1 for m in markers if m in text_l)
    return count >= 3

results = {}
total_proc = 0
total_docs_scanned = 0

all_texts = []

# Collect all texts
jsonl_files = glob.glob(os.path.join(DATA, "*.jsonl"))
for jf in jsonl_files:
    with open(jf, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
                text = " ".join(str(v) for v in d.values() if isinstance(v, str))
                all_texts.append(text)
            except:
                pass

txt_files = glob.glob(os.path.join(DATA, "*", "*.txt"))
for tf in txt_files:
    try:
        with open(tf, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        all_texts.append(text)
    except:
        pass

print(f"Scanning {len(all_texts):,} documents for depth...\n")

for topic, patterns in DEEP_TOPICS.items():
    hit_docs = 0
    proc_docs = 0
    for text in all_texts:
        text_l = text.lower()
        found = any(re.search(p, text_l) for p in patterns)
        if found:
            hit_docs += 1
            if has_procedural(text):
                proc_docs += 1
    results[topic] = (hit_docs, proc_docs)

print(f"{'DEEP TOPIC':<45} {'HITS':>5} {'PROC':>5}  STATUS")
print("-"*70)

missing = []
weak = []
good = []

for topic, (hits, proc) in sorted(results.items(), key=lambda x: x[1][0]):
    if hits == 0:
        status = "❌ MISSING"
        missing.append(topic)
    elif hits < 10 or proc < 3:
        status = f"⚠️  WEAK"
        weak.append(topic)
    else:
        status = f"✅ OK"
        good.append(topic)
    print(f"{topic:<45} {hits:>5} {proc:>5}  {status}")

print(f"\n{'='*70}")
print(f"✅ Good:    {len(good)}")
print(f"⚠️  Weak:    {len(weak)}")
print(f"❌ Missing: {len(missing)}")

print(f"\n=== PRIORITY GAPS (Missing or Weak) ===")
for t in missing:
    print(f"  ❌ {t}")
for t in weak:
    print(f"  ⚠️  {t}")
