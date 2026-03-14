#!/usr/bin/env python3
"""
🚀 MULTI-PROVIDER GENERATOR - Uses Cerebras + Groq (50 workers!)
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

# Target: 42,567 total samples
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

# Load keys
with open("/home/mohanganesh/ship/accounts_MASTER.json") as f:
    accounts = json.load(f)["accounts"]
    cerebras_keys = [(acc["cerebras_api_key"], "cerebras") for acc in accounts if acc.get("cerebras_api_key")]
    groq_keys = [(acc["groq_api_key"], "groq") for acc in accounts if acc.get("groq_api_key")]

all_keys = cerebras_keys + groq_keys

print("=" * 80)
print("🚀 MULTI-PROVIDER GENERATOR - 50 WORKERS!")
print("=" * 80)
print(f"🔑 Cerebras keys: {len(cerebras_keys)}")
print(f"🔑 Groq keys: {len(groq_keys)}")
print(f"🔑 TOTAL WORKERS: {len(all_keys)}")
print()

# Count existing
existing_by_category = defaultdict(int)
if OUTPUT_FILE.exists():
    with open(OUTPUT_FILE) as f:
        for line in f:
            try:
                sample = json.loads(line)
                existing_by_category[sample.get("category", "unknown")] += 1
            except:
                pass

existing_total = sum(existing_by_category.values())
print(f"📊 Existing samples: {existing_total:,}")

# Adjust targets
for cat, count in existing_by_category.items():
    if cat in CATEGORY_TARGETS:
        CATEGORY_TARGETS[cat] = max(0, CATEGORY_TARGETS[cat] - count)

remaining = sum(CATEGORY_TARGETS.values())
print(f"🎯 Need to generate: {remaining:,} more samples")
print()

# Stats
stats = {
    "successful": 0,
    "failed": 0,
    "by_category": defaultdict(int),
    "by_provider": defaultdict(int),
    "start_time": datetime.now().isoformat(),
}
stats_lock = threading.Lock()
write_lock = threading.Lock()

# Prompts
MARITIME_PROMPT_TEMPLATE = """Generate a realistic maritime training question and answer for: {category}

Requirements:
- Question: 100-200 words, realistic ship scenario
- Answer: 250-500 words, step-by-step procedures, regulatory citations (MARPOL/SOLAS/STCW), safety considerations
- Focus: {focus}

Return ONLY valid JSON (no markdown):
{{"question": "your question...", "answer": "your answer..."}}"""

CATEGORY_FOCUS = {
    "marpol_details": "MARPOL Annexes I-VI, pollution prevention, waste management",
    "solas_specifics": "SOLAS fire safety, life-saving appliances, construction",
    "stcw_competencies": "STCW certification, watchkeeping standards, training",
    "ism_code": "ISM Code compliance, safety management systems",
    "isps_code": "Ship security, access control, security drills",
    "mlc_2006": "Seafarer rights, working conditions, accommodation",
    "port_state_control": "PSC inspections, deficiencies, detention",
    "fire_emergency": "Fire detection, firefighting, evacuation",
    "enclosed_space": "Permit-to-work, gas testing, tank rescue",
    "man_overboard": "MOB detection, recovery procedures",
    "abandon_ship": "Lifeboat launching, survival craft",
    "medical_emergencies": "First aid, medical care, medevac",
    "collision_damage": "Damage assessment, watertight integrity",
    "grounding_response": "Grounding procedures, re-floating",
    "flooding_control": "Damage control, dewatering, emergency pumping",
    "cargo_operations": "Loading/unloading, securing, dangerous goods",
    "ballast_operations": "Ballast exchange, water management",
    "bunkering": "Fuel transfer, spill prevention",
    "mooring_anchoring": "Mooring operations, anchor handling",
    "watchkeeping": "Bridge/engine watch duties, handover",
    "drills": "Emergency drills, training exercises",
    "stability_calculations": "GM calculations, stability curves",
    "cargo_calculations": "Load distribution, weight, trim",
    "navigation_calculations": "Position fixing, course plotting",
    "fuel_calculations": "Fuel consumption, range calculations",
    "trim_corrections": "Trim adjustments, ballast transfer",
    "gmdss": "Distress communication, radio procedures",
    "lifesaving_equipment": "Lifeboat/raft maintenance, EPIRB",
    "fire_detection": "Fire detection systems, alarm testing",
    "navigation_equipment": "Radar, GPS, ECDIS, compass",
    "engineering_systems": "Main engine, auxiliary systems",
    "heavy_weather": "Storm tactics, cargo securing",
    "ice_navigation": "Ice operations, polar procedures",
    "piracy": "Anti-piracy measures, citadel procedures",
    "canal_transit": "Suez/Panama canal procedures",
    "unusual_incidents": "Rare emergencies, complex situations",
}

def generate_sample(api_key, provider, worker_id, category):
    """Generate one sample."""
    prompt = MARITIME_PROMPT_TEMPLATE.format(
        category=category.replace('_', ' ').title(),
        focus=CATEGORY_FOCUS.get(category, "general maritime operations")
    )
    
    for attempt in range(3):
        try:
            if provider == "cerebras":
                response = requests.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama3.1-8b",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.9,
                        "max_tokens": 1500,
                    },
                    timeout=30
                )
            else:  # groq
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.9,
                        "max_tokens": 1500,
                    },
                    timeout=30
                )
            
            if response.status_code == 200:
                try:
                    content = response.json()["choices"][0]["message"]["content"]
                    
                    # Extract JSON
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

def worker(worker_id, api_key, provider, task_queue):
    """Worker thread."""
    while True:
        try:
            task = task_queue.get(timeout=2)
            if task is None:
                break
            
            category = task
            sample = generate_sample(api_key, provider, worker_id, category)
            
            if sample:
                with write_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                with stats_lock:
                    stats["successful"] += 1
                    stats["by_category"][category] += 1
                    stats["by_provider"][provider] += 1
                    
                    if stats["successful"] % 100 == 0:
                        total = existing_total + stats["successful"]
                        pct = 100 * total / 42567
                        print(f"   ✅ {total:,}/42,567 ({pct:.1f}%) | +{stats['successful']} new | C:{stats['by_provider']['cerebras']} G:{stats['by_provider']['groq']}")
                        
                        with open(STATS_FILE, 'w') as sf:
                            json.dump(dict(stats), sf, indent=2)
            else:
                with stats_lock:
                    stats["failed"] += 1
            
            time.sleep(1.2 if provider == "cerebras" else 2.0)  # Rate limiting
            task_queue.task_done()
            
        except Exception:
            break

# Build task queue
task_queue = Queue()
for category, target_count in sorted(CATEGORY_TARGETS.items()):
    if target_count > 0:
        for _ in range(target_count):
            task_queue.put(category)

print(f"📝 Queued {task_queue.qsize():,} tasks")
print()

# Start workers
print(f"🚀 Starting {len(all_keys)} workers...")
threads = []
for i, (key, provider) in enumerate(all_keys, 1):
    worker_name = f"{provider}_{i}"
    t = threading.Thread(
        target=worker,
        args=(worker_name, key, provider, task_queue),
        daemon=True
    )
    t.start()
    threads.append(t)
    time.sleep(0.05)

print(f"✅ All workers started!")
print("=" * 80)
print("GENERATING WITH 50 PARALLEL WORKERS...")
print("=" * 80)
print()

# Monitor
try:
    task_queue.join()
    print("\n" + "=" * 80)
    print("✅ GENERATION COMPLETE!")
    print("=" * 80)
    print(f"   Successful: {stats['successful']:,}")
    print(f"   Cerebras: {stats['by_provider']['cerebras']:,}")
    print(f"   Groq: {stats['by_provider']['groq']:,}")
    print(f"   Failed: {stats['failed']:,}")
    print(f"   Total: {existing_total + stats['successful']:,}")
    
except KeyboardInterrupt:
    print("\n⚠️  Interrupted!")
    
finally:
    stats["end_time"] = datetime.now().isoformat()
    with open(STATS_FILE, 'w') as sf:
        json.dump(dict(stats), sf, indent=2)
    print(f"📊 Stats saved!")
