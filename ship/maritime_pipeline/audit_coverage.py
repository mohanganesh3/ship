#!/usr/bin/env python3
"""
FULL COVERAGE AUDIT
Scans all collected data to see which topics we have and which are missing.
"""
import json, os, glob, re
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "extracted_text")

# ── TOPIC KEYWORDS ──────────────────────────────────────────────────────────
TOPICS = {
    # MUST-HAVE for production
    "OWS / Oily Water Separator":     ["oily water separator","ows","15 ppm","bilge water","bilge pump"],
    "FWG / Fresh Water Generator":    ["fresh water generator","fwg","evaporator","distillation","potable water plant"],
    "GMDSS":                          ["gmdss","global maritime distress","epirb","sart","dsc","inmarsat","navtex","mf/hf","vhf radio","dsb","mrcc"],
    "ECDIS":                          ["ecdis","electronic chart","enc ","route planning","passage planning","chart update","noaa chart"],
    "Cargo Ops – Tankers":            ["isgott","tanker cargo","crude oil washing","cow","inert gas","ig system","ullage","product tanker","inerting"],
    "Cargo Ops – Bulk Carriers":      ["imsbc","bulk cargo","cargo hold cleaning","trimming","angle of repose","grain code","solid bulk"],
    "Cargo Ops – Containers":         ["imdg","dangerous goods","container securing","reefer container","css code","cargo securing manual"],
    "Cargo Ops – Gas Carriers":       ["igc code","lng carrier","lpg carrier","reliquefaction","boil-off","cargo compressor"],
    "Cargo Ops – Chemical Tankers":   ["ibc code","chemical tanker","tank cleaning","stripping","vapor emission","noxious liquid"],
    "Bunkering":                      ["bunkering","bunker fuel","fuel oil transfer","bdn","bunker delivery note","stem","marpol annex vi","sulphur cap"],
    "PSC Inspection":                 ["port state control","psc inspection","paris mou","tokyo mou","deficiency","detention","niwa","inspection checklist"],
    "Cargo Securing / Lashing":       ["cargo securing","lashing","css code","securing manual","container lashing","lashing rod","twist lock","turnbuckle"],
    "Anchor / Mooring":               ["anchorage","anchor watch","mooring","mooring line","bollard pull","fendering","berthing","windlass"],
    "Permit to Work":                 ["permit to work","ptw","hot work permit","enclosed space entry","lock out tag out","loto","gas testing"],
    "SMS / ISM Code":                 ["ism code","safety management system","sms","designated person ashore","dpa","doc","smc"],
    "STCW":                           ["stcw","standards of training","certificate of competency","coc","watchkeeping","rest hours","fatigue"],
    "MARPOL":                         ["marpol","garbage management","sewage","garbage record book","oil record book","orb"],
    "SOLAS":                          ["solas","life-saving","fire protection","damage stability","loadline","grain stability"],
    "Navigation / COLREGS":           ["colregs","collision regulations","rule 5","rule 16","traffic separation","watch","bridge team","radar plotting"],
    "Stability":                      ["intact stability","damage stability","metacentric height","gm ","righting lever","gz curve","inclining experiment"],
    "Fire Fighting":                  ["fixed fire fighting","co2 system","foam system","fire damper","fire patrol","fire fighting equipment","fire detection"],
    "LSA – Lifeboats":                ["lifeboat","rescue boat","immersion suit","pyrotechnic","epirb","life raft","muster station","abandon ship"],
    "Engine Room Ops":                ["main engine","reversing","manoeuvring","fuel changeover","engine room log","slow steaming","ero watch"],
    "Auxiliary Machinery":            ["auxiliary engine","alternator","generator","purifier","separator","heat exchanger","compressor","pumps"],
    "Sewage Treatment":               ["sewage treatment","sewage holding tank","marpol annex iv","stp","sewage discharge"],
    "Incinerator":                    ["incinerator","shipboard incineration","garbage incineration","sludge incineration"],
    "Voyage Planning":                ["voyage plan","apem","ecdis passage","chart correction","notice to mariners","ntm","pilot card"],
    "Weather / Routing":              ["weather routing","heavy weather","storm avoidance","significant wave height","cyclone","hurricane"],
    "MLC / Crew Welfare":             ["maritime labour convention","mlc","crew welfare","seafarer rights","wages","repatriation","grievance"],
    "Salvage / Towage":               ["salvage","towage","towing","lof","lloyd's open form","wreck removal"],
    "Accident Investigation":         ["accident investigation","marine accident","casualty investigation","formal safety assessment","fsa"],
    "Dry Dock / Surveys":             ["dry dock","drydocking","class survey","annual survey","special survey","hull inspection","underwater survey"],
    "Cargo Calculations":             ["ullage table","trim correction","wedge formula","free surface","virtual gm","deadweight survey","density correction"],
}

# ── SCAN ALL DATA ────────────────────────────────────────────────────────────
hits = defaultdict(int)
total_docs = 0
total_chars = 0

def scan_text(text):
    """Returns set of topic keys found in this text."""
    text_l = text.lower()
    found = set()
    for topic, keywords in TOPICS.items():
        for kw in keywords:
            if kw in text_l:
                found.add(topic)
                break
    return found

# Scan JSONL files
jsonl_files = glob.glob(os.path.join(DATA, "*.jsonl"))
for jf in jsonl_files:
    with open(jf, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line)
                text = " ".join(str(v) for v in d.values() if isinstance(v, str))
                found = scan_text(text)
                for t in found:
                    hits[t] += 1
                total_docs += 1
                total_chars += len(text)
            except:
                pass

# Scan text files in subdirectories
txt_files = glob.glob(os.path.join(DATA, "*", "*.txt"))
for tf in txt_files:
    try:
        with open(tf, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        found = scan_text(text)
        for t in found:
            hits[t] += 1
        total_docs += 1
        total_chars += len(text)
    except:
        pass

# ── REPORT ───────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"MARITIME COVERAGE AUDIT  |  {total_docs:,} documents scanned")
print(f"{'='*65}")
print(f"{'TOPIC':<40} {'DOCS':>6}  {'STATUS'}")
print(f"{'-'*65}")

GOOD = 30
WEAK = 5
covered = []
weak = []
missing = []

for topic in sorted(TOPICS.keys()):
    count = hits[topic]
    if count >= GOOD:
        status = "✅  COVERED"
        covered.append(topic)
    elif count >= WEAK:
        status = f"⚠️  WEAK ({count} docs)"
        weak.append(topic)
    else:
        status = f"❌  MISSING ({count} docs)"
        missing.append(topic)
    print(f"{topic:<40} {count:>6}  {status}")

print(f"\n{'='*65}")
print(f"✅  Covered:  {len(covered)}")
print(f"⚠️   Weak:     {len(weak)}")
print(f"❌  Missing:  {len(missing)}")
print(f"\nEst. total chars: {total_chars/1e6:.1f}M")
print(f"\n--- MISSING DOMAINS (priority targets) ---")
for t in missing:
    print(f"  ❌ {t}")
print(f"\n--- WEAK DOMAINS ---")
for t in weak:
    print(f"  ⚠️  {t}")
