#!/usr/bin/env python3
"""
🚀 FAST MARITIME DATA GENERATOR - Optimized for Speed
Starts generation immediately, counts existing samples in parallel
"""

import json
import time
import requests
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from queue import Queue

# Configuration
OUTPUT_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/maritime_60k.jsonl")
STATS_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/stats.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Target: 42,567 total samples distributed across 36 categories
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

# Load Cerebras keys
with open("/home/mohanganesh/ship/accounts_MASTER.json") as f:
    accounts = json.load(f)["accounts"]
    cerebras_keys = [acc["cerebras_api_key"] for acc in accounts if acc.get("cerebras_api_key")]

print("=" * 80)
print("🚀 FAST JSON GENERATOR - STARTING IMMEDIATELY")
print("=" * 80)
print(f"🔑 Using {len(cerebras_keys)} Cerebras API keys")
print(f"🎯 Target: 42,567 total samples")
print()

# Count existing samples quickly (don't block startup)
existing_by_category = defaultdict(int)
existing_total = 0

def count_existing():
    global existing_by_category, existing_total
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    cat = sample.get("category", "unknown")
                    existing_by_category[cat] += 1
                    existing_total += 1
                except:
                    pass
        print(f"📊 Counted {existing_total} existing samples")
        
        # Adjust targets
        for cat, count in existing_by_category.items():
            if cat in CATEGORY_TARGETS:
                CATEGORY_TARGETS[cat] = max(0, CATEGORY_TARGETS[cat] - count)
        
        remaining = sum(CATEGORY_TARGETS.values())
        print(f"   Need to generate: {remaining} more")
        print()

# Start counting in background
count_thread = threading.Thread(target=count_existing, daemon=True)
count_thread.start()

# Stats
stats = {
    "successful": 0,
    "failed": 0,
    "by_category": defaultdict(int),
    "start_time": datetime.now().isoformat(),
}
stats_lock = threading.Lock()
write_lock = threading.Lock()

# Maritime prompts for JSON generation
MARITIME_PROMPT_TEMPLATE = """Generate a realistic maritime training question and answer for the category: {category}

Requirements:
- Question: 100-200 words describing a realistic scenario aboard a ship
- Answer: 250-500 words with step-by-step procedures, regulatory citations (MARPOL/SOLAS/STCW), and safety considerations
- Focus on: {focus}

Return ONLY valid JSON in this EXACT format (no markdown, no extra text):
{{"question": "your question here...", "answer": "your detailed answer here..."}}"""

CATEGORY_FOCUS = {
    "marpol_details": "MARPOL Annexes I-VI, pollution prevention, waste management, emissions control",
    "solas_specifics": "SOLAS chapters, fire safety, life-saving appliances, construction standards",
    "stcw_competencies": "STCW certification, watchkeeping standards, training requirements",
    "ism_code": "ISM Code compliance, safety management systems, documentation",
    "isps_code": "Ship security, access control, security drills and procedures",
    "mlc_2006": "Seafarer rights, working conditions, accommodation standards",
    "port_state_control": "PSC inspections, deficiencies, detention procedures",
    "fire_emergency": "Fire detection, firefighting, evacuation, containment procedures",
    "enclosed_space": "Permit-to-work, gas testing, rescue procedures for tanks/voids",
    "man_overboard": "MOB detection, recovery procedures, man overboard equipment",
    "abandon_ship": "Lifeboat launching, survival craft provisioning, abandon ship procedures",
    "medical_emergencies": "First aid, medical care, telemedicine, medevac procedures",
    "collision_damage": "Damage assessment, watertight integrity, collision response",
    "grounding_response": "Grounding procedures, re-floating, hull integrity checks",
    "flooding_control": "Damage control, dewatering, emergency pumping",
    "cargo_operations": "Loading/unloading, securing, stowage, dangerous goods",
    "ballast_operations": "Ballast exchange, water management, stability maintenance",
    "bunkering": "Fuel transfer procedures, spill prevention, quantity verification",
    "mooring_anchoring": "Mooring operations, anchor handling, port procedures",
    "watchkeeping": "Bridge/engine room watch duties, lookout, handover procedures",
    "drills": "Emergency drills, training exercises, drill documentation",
    "stability_calculations": "GM calculations, stability curves, loading conditions",
    "cargo_calculations": "Load distribution, weight calculations, trim and stress",
    "navigation_calculations": "Position fixing, course plotting, tidal calculations",
    "fuel_calculations": "Fuel consumption, range calculations, bunker planning",
    "trim_corrections": "Trim adjustments, ballast transfer, cargo redistribution",
    "gmdss": "Distress communication, radio procedures, GMDSS equipment",
    "lifesaving_equipment": "Lifeboat/raft maintenance, immersion suits, EPIRB",
    "fire_detection": "Fire detection systems, alarm testing, sensor maintenance",
    "navigation_equipment": "Radar, GPS, ECDIS, compass calibration",
    "engineering_systems": "Main engine, auxiliary systems, maintenance procedures",
    "heavy_weather": "Storm tactics, cargo securing, heavy weather routing",
    "ice_navigation": "Ice operations, ice damage prevention, polar procedures",
    "piracy": "Anti-piracy measures, citadel procedures, security alerting",
    "canal_transit": "Suez/Panama canal procedures, pilot requirements, restrictions",
    "unusual_incidents": "Rare emergencies, uncommon scenarios, complex situations",
}

def generate_sample(api_key, worker_id, category):
    """Generate one sample using Cerebras with JSON output."""
    prompt = MARITIME_PROMPT_TEMPLATE.format(
        category=category.replace('_', ' ').title(),
        focus=CATEGORY_FOCUS.get(category, "general maritime operations")
    )
    
    for attempt in range(3):
        try:
            response = requests.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3.1-8b",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.9,
                    "max_tokens": 1500,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                try:
                    content = response.json()["choices"][0]["message"]["content"]
                    
                    # Extract JSON (between first { and last })
                    start = content.find('{')
                    end = content.rfind('}')
                    if start != -1 and end != -1:
                        json_str = content[start:end+1]
                        qa_data = json.loads(json_str)
                        
                        if "question" in qa_data and "answer" in qa_data:
                            q = qa_data["question"].strip()
                            a = qa_data["answer"].strip()
                            
                            if len(q) > 50 and len(a) > 150:
                                return {
                                    "category": category,
                                    "question": q,
                                    "answer": a,
                                    "worker_id": worker_id,
                                    "generated_at": datetime.now().isoformat(),
                                }
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
            
            elif response.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            
        except Exception:
            if attempt < 2:
                time.sleep(2)
    
    return None

def worker(worker_id, api_key, task_queue):
    """Worker thread - generates samples from task queue."""
    while True:
        try:
            task = task_queue.get(timeout=2)
            if task is None:
                break
            
            category = task
            sample = generate_sample(api_key, worker_id, category)
            
            if sample:
                # Write to file
                with write_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                # Update stats
                with stats_lock:
                    stats["successful"] += 1
                    stats["by_category"][category] += 1
                    
                    # Progress update every 50 samples
                    if stats["successful"] % 50 == 0:
                        total = existing_total + stats["successful"]
                        pct = 100 * total / 42567
                        print(f"   ✅ {total:,}/42,567 samples ({pct:.1f}%) | +{stats['successful']} new")
                        
                        # Save stats
                        with open(STATS_FILE, 'w') as sf:
                            json.dump(dict(stats), sf, indent=2)
            else:
                with stats_lock:
                    stats["failed"] += 1
            
            time.sleep(1.2)  # Rate limit: ~50 RPM
            task_queue.task_done()
            
        except Exception:
            break

# Build task queue
print("📝 Building task queue...")
task_queue = Queue()

# Wait briefly for counting to finish (max 5 seconds)
count_thread.join(timeout=5)

# Fill queue with all categories proportionally
tasks_added = 0
for category, target_count in sorted(CATEGORY_TARGETS.items()):
    if target_count > 0:
        for _ in range(target_count):
            task_queue.put(category)
            tasks_added += 1

print(f"   {tasks_added:,} tasks queued across {len([c for c in CATEGORY_TARGETS.values() if c > 0])} categories")
print()

# Start workers
print(f"🚀 Starting {len(cerebras_keys)} workers...")
threads = []
for i, key in enumerate(cerebras_keys):
    t = threading.Thread(
        target=worker,
        args=(f"cerebras_{i+1}", key, task_queue),
        daemon=True
    )
    t.start()
    threads.append(t)
    time.sleep(0.1)  # Stagger startup

print(f"✅ All workers started!")
print("=" * 80)
print("GENERATING SAMPLES...")
print("=" * 80)
print()

# Monitor progress
try:
    task_queue.join()
    print("\n" + "=" * 80)
    print("✅ GENERATION COMPLETE!")
    print("=" * 80)
    print(f"   Successful: {stats['successful']:,}")
    print(f"   Failed: {stats['failed']:,}")
    print(f"   Total in file: {existing_total + stats['successful']:,}")
    print()
    
except KeyboardInterrupt:
    print("\n⚠️  Interrupted! Saving progress...")
    
finally:
    # Final stats
    stats["end_time"] = datetime.now().isoformat()
    with open(STATS_FILE, 'w') as sf:
        json.dump(dict(stats), sf, indent=2)
    
    print(f"📊 Stats saved to {STATS_FILE}")
    print("🎉 Done!")
