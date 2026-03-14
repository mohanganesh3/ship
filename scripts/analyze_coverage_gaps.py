#!/usr/bin/env python3
"""
Coverage Gap Analyzer
Analyzes existing 17,485 curated samples to identify coverage gaps
Maps to 72 maritime categories and calculates what's needed
"""

import json
from pathlib import Path
from collections import Counter, defaultdict

# 72 Maritime Categories
CATEGORIES = {
    "navigation": ["celestial_navigation", "electronic_navigation", "collision_avoidance",
                   "ship_handling", "meteorology", "passage_planning", "watchkeeping", "pilotage"],
    "engineering": ["main_engine", "auxiliary_engines", "boilers", "pumps_systems",
                    "electrical_systems", "refrigeration_hvac", "propulsion_steering",
                    "fuel_systems", "lubrication", "hydraulic_systems", "automation_control",
                    "maintenance_planning"],
    "safety": ["fire_safety", "lifesaving_equipment", "enclosed_spaces", "man_overboard",
               "medical_emergencies", "search_rescue", "ppe_safety", "emergency_drills",
               "risk_assessment", "emergency_procedures"],
    "cargo": ["cargo_handling", "container_ops", "bulk_cargo", "liquid_cargo",
              "dangerous_goods", "refrigerated_cargo", "roro_ops", "cargo_documentation"],
    "regulations": ["marpol", "solas", "stcw", "ism_code", "isps_code", "mlc",
                    "port_state_control", "flag_state", "environmental_compliance", "piracy_security"],
    "stability": ["stability_calcs", "damage_stability", "ship_construction",
                  "ballast_ops", "ship_terminology", "tonnage_measurements"],
    "communications": ["gmdss", "maritime_radio", "record_keeping", "crew_management",
                       "company_procedures", "vessel_documentation"],
    "specialized": ["heavy_weather", "anchoring_mooring", "towing_salvage", "ice_navigation",
                    "offshore_ops", "canal_transit", "bunker_ops", "ship_to_ship"],
    "professional": ["seamanship", "navigation_calcs", "leadership_management", "maritime_law"]
}

# Target samples per category (OPTIMAL scenario)
TARGETS = {
    "safety": 1500,      # Critical
    "regulations": 1500, # Critical
    "stability": 1500,   # Critical
    "navigation": 500,   # High priority
    "cargo": 500,        # High priority
    "engineering": 500,  # High priority
    "communications": 200,  # Medium
    "specialized": 200,     # Medium
    "professional": 100     # Low
}

def analyze_curated_dataset():
    """Analyze existing 17,485 curated samples"""
    curated_file = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl")
    
    if not curated_file.exists():
        print(f"❌ Curated file not found: {curated_file}")
        return
    
    print("=" * 80)
    print("ANALYZING EXISTING 17,485 CURATED SAMPLES")
    print("=" * 80)
    
    samples = []
    with open(curated_file) as f:
        for line in f:
            try:
                samples.append(json.loads(line))
            except:
                pass
    
    print(f"\n✅ Loaded {len(samples)} samples")
    
    # Analyze content for category hints
    category_keywords = {
        "navigation": ["navigation", "radar", "gps", "chart", "position", "course", "bearing", "compass"],
        "engineering": ["engine", "machinery", "boiler", "pump", "generator", "motor", "turbine", "propulsion"],
        "safety": ["safety", "fire", "lifeboat", "emergency", "drill", "rescue", "enclosed space", "ppe"],
        "cargo": ["cargo", "container", "loading", "stowage", "lashing", "dangerous goods", "imdg"],
        "regulations": ["marpol", "solas", "stcw", "ism", "isps", "regulation", "compliance", "convention"],
        "stability": ["stability", "gm", "metacentric", "list", "trim", "ballast", "freeboard"],
        "communications": ["radio", "gmdss", "vhf", "inmarsat", "distress", "communication"],
        "specialized": ["weather", "anchor", "mooring", "towing", "ice", "canal", "bunker"],
        "professional": ["seamanship", "leadership", "management", "law", "knot", "rope"]
    }
    
    # Categorize samples based on keywords
    categorized = defaultdict(list)
    uncategorized = []
    
    for idx, sample in enumerate(samples):
        text = (sample.get('question', '') + ' ' + sample.get('answer', '') + ' ' + 
                sample.get('chunk_text', '') + ' ' + str(sample.get('metadata', {}))).lower()
        
        matched = False
        for cat, keywords in category_keywords.items():
            if any(kw in text for kw in keywords):
                categorized[cat].append(idx)
                matched = True
                break
        
        if not matched:
            uncategorized.append(idx)
    
    # Report findings
    print("\n" + "=" * 80)
    print("CATEGORY DISTRIBUTION (Estimated via keyword matching)")
    print("=" * 80)
    
    total_categorized = sum(len(v) for v in categorized.values())
    
    gaps = []
    for main_cat in CATEGORIES.keys():
        count = len(categorized.get(main_cat, []))
        target = TARGETS[main_cat] * len(CATEGORIES[main_cat])
        gap = max(0, target - count)
        pct = (count / len(samples) * 100) if len(samples) > 0 else 0
        
        print(f"\n{main_cat.upper():15} - {count:5} samples ({pct:5.1f}%)")
        print(f"  Target: {target:5} | Gap: {gap:5} samples")
        
        if gap > 0:
            gaps.append((main_cat, gap, target))
    
    print(f"\nUncategorized: {len(uncategorized)} samples ({len(uncategorized)/len(samples)*100:.1f}%)")
    
    # Priority gaps
    print("\n" + "=" * 80)
    print("TOP 10 PRIORITY GAPS (What to generate first)")
    print("=" * 80)
    
    gaps.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (cat, gap, target) in enumerate(gaps[:10], 1):
        print(f"{rank:2}. {cat:15} - Need {gap:5} more samples (target: {target})")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    total_gap = sum(g[1] for g in gaps)
    print(f"\n✅ Current samples: {len(samples):,}")
    print(f"🎯 Optimal target: 56,200")
    print(f"📊 Estimated gap: ~{total_gap:,} strategic samples needed")
    
    print("\n⚠️  CRITICAL GAPS (likely under-represented):")
    critical_cats = ['safety', 'regulations', 'stability']
    for cat in critical_cats:
        count = len(categorized.get(cat, []))
        target = TARGETS[cat] * len(CATEGORIES[cat])
        print(f"  - {cat:15}: {count:5} / {target:5} samples")
    
    print("\n🎯 RECOMMENDED GENERATION PRIORITY:")
    print("  1. Safety & Emergency procedures (especially enclosed spaces)")
    print("  2. Regulations (MARPOL, SOLAS details)")
    print("  3. Stability calculations")
    print("  4. Engineering troubleshooting")
    print("  5. Cargo operations")
    
    # Export gap analysis
    output = {
        "total_samples": len(samples),
        "categorized": {k: len(v) for k, v in categorized.items()},
        "gaps": {cat: gap for cat, gap, _ in gaps},
        "targets": {cat: target for cat, _, target in gaps},
        "uncategorized": len(uncategorized),
        "priority_generation": [cat for cat, _, _ in gaps[:10]]
    }
    
    output_file = Path("/home/mohanganesh/ship/training/coverage_gap_analysis.json")
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Detailed analysis saved to: {output_file}")

if __name__ == "__main__":
    analyze_curated_dataset()
