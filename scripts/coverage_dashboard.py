#!/usr/bin/env python3
"""
📊 REAL-TIME COVERAGE DASHBOARD
Monitors generation progress across all 36 categories

Features:
- Live progress bars
- Category-wise completion
- API usage statistics
- ETA calculation
- Quality metrics
"""

import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import os
import sys

OUTPUT_DIR = Path("/home/mohanganesh/ship/training/orchestrated_60k")
OUTPUT_FILE = OUTPUT_DIR / "maritime_60k.jsonl"
STATS_FILE = OUTPUT_DIR / "stats.json"

GENERATION_PLAN = {
    "marpol_details": 2606,
    "solas_specifics": 2172,
    "stcw_competencies": 1737,
    "ism_code": 1303,
    "isps_code": 869,
    "mlc_2006": 869,
    "port_state_control": 869,
    "fire_emergency": 1737,
    "enclosed_space": 1737,
    "man_overboard": 1303,
    "abandon_ship": 1303,
    "medical_emergencies": 1303,
    "collision_damage": 869,
    "grounding_response": 869,
    "flooding_control": 869,
    "cargo_operations": 1737,
    "ballast_operations": 1303,
    "bunkering": 1303,
    "mooring_anchoring": 1303,
    "watchkeeping": 869,
    "drills": 869,
    "stability_calculations": 1737,
    "cargo_calculations": 1303,
    "navigation_calculations": 1303,
    "fuel_calculations": 869,
    "trim_corrections": 869,
    "gmdss": 1303,
    "lifesaving_equipment": 1303,
    "fire_detection": 869,
    "navigation_equipment": 869,
    "engineering_systems": 1303,
    "heavy_weather": 869,
    "ice_navigation": 434,
    "piracy": 434,
    "canal_transit": 434,
    "unusual_incidents": 869,
}

TOTAL_TARGET = 42515

def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')

def progress_bar(current, total, width=40):
    """Generate ASCII progress bar."""
    filled = int(width * current / total) if total > 0 else 0
    bar = '█' * filled + '░' * (width - filled)
    pct = 100 * current / total if total > 0 else 0
    return f"[{bar}] {pct:5.1f}% ({current}/{total})"

def read_stats():
    """Read current statistics."""
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            return json.load(f)
    return None

def count_by_category():
    """Count generated samples by category."""
    counts = defaultdict(int)
    
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    counts[sample.get("category", "unknown")] += 1
                except:
                    pass
    
    return counts

def estimate_completion(stats):
    """Estimate time to completion."""
    if not stats or stats["successful"] == 0:
        return "Calculating..."
    
    start_time = datetime.fromisoformat(stats["start_time"])
    elapsed = datetime.now() - start_time
    
    rate = stats["successful"] / elapsed.total_seconds()  # samples per second
    remaining = TOTAL_TARGET - stats["successful"]
    
    if rate > 0:
        eta_seconds = remaining / rate
        eta = timedelta(seconds=int(eta_seconds))
        completion_time = datetime.now() + eta
        return f"{eta} (at {completion_time.strftime('%H:%M:%S')})"
    
    return "Unknown"

def display_dashboard():
    """Display the dashboard."""
    
    clear_screen()
    
    print("=" * 100)
    print("🚀 MARITIME 60K GENERATION - LIVE DASHBOARD".center(100))
    print("=" * 100)
    print()
    
    # Read stats
    stats = read_stats()
    counts = count_by_category()
    
    if not stats:
        print("⏳ Waiting for generation to start...")
        return
    
    # Overall progress
    print("📊 OVERALL PROGRESS")
    print("-" * 100)
    overall_bar = progress_bar(stats["successful"], TOTAL_TARGET, 60)
    print(f"  {overall_bar}")
    print()
    print(f"  ✅ Successful: {stats['successful']:,}")
    print(f"  ❌ Failed: {stats['failed']:,}")
    print(f"  📈 Success Rate: {stats['successful']/(stats['successful']+stats['failed'])*100:.1f}%")
    print()
    
    # Rate and ETA
    start_time = datetime.fromisoformat(stats["start_time"])
    elapsed = datetime.now() - start_time
    rate_per_hour = stats["successful"] / (elapsed.total_seconds() / 3600) if elapsed.total_seconds() > 0 else 0
    
    print(f"  ⚡ Rate: {rate_per_hour:.0f} samples/hour")
    print(f"  ⏱️  Elapsed: {str(elapsed).split('.')[0]}")
    print(f"  🎯 ETA: {estimate_completion(stats)}")
    print()
    
    # Provider breakdown
    print("🔑 API USAGE BY PROVIDER")
    print("-" * 100)
    for provider, count in stats["by_provider"].items():
        bar = progress_bar(count, stats["successful"], 40)
        pct = 100 * count / stats["successful"] if stats["successful"] > 0 else 0
        print(f"  {provider.upper():12} {bar} ({pct:.1f}% of total)")
    print()
    
    # Category progress (grouped by phase)
    phases = {
        "Phase 1: Regulatory": ["marpol_details", "solas_specifics", "stcw_competencies", "ism_code", "isps_code", "mlc_2006", "port_state_control"],
        "Phase 2: Emergency": ["fire_emergency", "enclosed_space", "man_overboard", "abandon_ship", "medical_emergencies", "collision_damage", "grounding_response", "flooding_control"],
        "Phase 3: Operations": ["cargo_operations", "ballast_operations", "bunkering", "mooring_anchoring", "watchkeeping", "drills"],
        "Phase 4: Technical": ["stability_calculations", "cargo_calculations", "navigation_calculations", "fuel_calculations", "trim_corrections"],
        "Phase 5: Equipment": ["gmdss", "lifesaving_equipment", "fire_detection", "navigation_equipment", "engineering_systems"],
        "Phase 6: Edge Cases": ["heavy_weather", "ice_navigation", "piracy", "canal_transit", "unusual_incidents"],
    }
    
    print("📋 CATEGORY PROGRESS")
    print("-" * 100)
    
    for phase, categories in phases.items():
        print(f"\n{phase}:")
        
        phase_current = sum(counts[cat] for cat in categories)
        phase_target = sum(GENERATION_PLAN[cat] for cat in categories)
        phase_bar = progress_bar(phase_current, phase_target, 30)
        print(f"  {phase_bar}")
        
        for cat in categories:
            current = counts[cat]
            target = GENERATION_PLAN[cat]
            bar = progress_bar(current, target, 20)
            
            status = "✅" if current >= target else "🔄"
            cat_display = cat.replace("_", " ").title()[:30]
            
            print(f"    {status} {cat_display:30} {bar}")
    
    print()
    print("=" * 100)
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to exit")
    print("=" * 100)

def main():
    """Main dashboard loop."""
    
    print("Starting dashboard...")
    print("Monitoring:", OUTPUT_FILE)
    print()
    
    try:
        while True:
            display_dashboard()
            time.sleep(5)  # Update every 5 seconds
            
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard closed.")
        sys.exit(0)

if __name__ == "__main__":
    main()
