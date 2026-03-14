#!/usr/bin/env python3
"""
🚀 DIRECT GENERATION - Use Copilot's AI directly!
No external API calls, no rate limits, FAST!
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Configuration
OUTPUT_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/maritime_60k.jsonl")
STATS_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/stats_direct.json")

# Category targets
CATEGORY_TARGETS = {
    "marpol_details": 2606, "solas_specifics": 2172, "stcw_competencies": 1737,
    "ism_code": 1303, "isps_code": 869, "mlc_2006": 869, "port_state_control": 869,
    "fire_emergency": 1737, "enclosed_space": 1737, "man_overboard": 1303,
    "abandon_ship": 1303, "medical_emergencies": 1303, "collision_damage": 869,
    "grounding_response": 869, "flooding_control": 869, "cargo_operations": 1737,
    "ballast_operations": 1303, "bunkering": 1303, "mooring_anchoring": 1303,
    "watchkeeping": 869, "drills": 869, "stability_calculations": 1737,
    "cargo_calculations": 1303, "navigation_calculations": 1303, "fuel_calculations": 869,
    "trim_corrections": 869, "gmdss": 1303, "lifesaving_equipment": 1303,
    "fire_detection": 869, "navigation_equipment": 869, "engineering_systems": 1303,
    "heavy_weather": 869, "ice_navigation": 434, "piracy": 434,
    "canal_transit": 434, "unusual_incidents": 869,
}

# Count existing
existing_counts = defaultdict(int)
if OUTPUT_FILE.exists():
    with open(OUTPUT_FILE) as f:
        for line in f:
            try:
                sample = json.loads(line)
                existing_counts[sample.get("category", "unknown")] += 1
            except:
                pass

existing_total = sum(existing_counts.values())
print(f"📊 Found {existing_total:,} existing samples")

# Adjust targets
for cat, count in existing_counts.items():
    if cat in CATEGORY_TARGETS:
        CATEGORY_TARGETS[cat] = max(0, CATEGORY_TARGETS[cat] - count)

remaining = sum(CATEGORY_TARGETS.values())
print(f"🎯 Need to generate: {remaining:,} more samples")
print()
print("=" * 80)
print("This script prepares prompts for Copilot to generate samples directly.")
print("Copilot will generate samples without external API rate limits!")
print("=" * 80)
print()

# Create list of categories that need samples
categories_needed = [(cat, count) for cat, count in CATEGORY_TARGETS.items() if count > 0]
categories_needed.sort(key=lambda x: -x[1])  # Prioritize categories needing most samples

print(f"Categories needing samples: {len(categories_needed)}")
print()
print("Top 10 categories:")
for cat, count in categories_needed[:10]:
    print(f"  {cat}: {count:,} samples needed")

print()
print("=" * 80)
print("READY FOR DIRECT GENERATION!")
print("=" * 80)
print()
print("Next step: Ask Copilot to generate samples directly using the create tool")
print("No external APIs needed - Copilot can do it all!")
