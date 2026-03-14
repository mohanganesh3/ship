#!/usr/bin/env python3
"""
🚀 IMPROVED MARITIME DATA GENERATOR - JSON FORMAT
Uses structured JSON output for 99%+ success rate
Generates 42,515 samples with proper category distribution
"""

import json
import time
import requests
import threading
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from queue import Queue
import random

# Configuration
OUTPUT_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/maritime_60k.jsonl")
STATS_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/stats.json")
PROGRESS_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/progress.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Category distribution (balanced across 36 categories)
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

TOTAL_TARGET = sum(CATEGORY_TARGETS.values())

# Load existing samples to track progress
existing_counts = defaultdict(int)
if OUTPUT_FILE.exists():
    with open(OUTPUT_FILE) as f:
        for line in f:
            try:
                sample = json.loads(line)
                existing_counts[sample.get("category", "unknown")] += 1
            except:
                pass

print(f"📊 Found {sum(existing_counts.values())} existing samples")
for cat, count in existing_counts.items():
    if cat in CATEGORY_TARGETS:
        CATEGORY_TARGETS[cat] = max(0, CATEGORY_TARGETS[cat] - count)

remaining_total = sum(CATEGORY_TARGETS.values())
print(f"🎯 Need to generate: {remaining_total} more samples")

# Load Cerebras keys
with open("/home/mohanganesh/ship/accounts_MASTER.json") as f:
    accounts = json.load(f)["accounts"]
    cerebras_keys = [acc["cerebras_api_key"] for acc in accounts if acc.get("cerebras_api_key")]

print(f"🔑 Using {len(cerebras_keys)} Cerebras API keys")
print(f"⚡ Target: {remaining_total} samples across {len([c for c in CATEGORY_TARGETS.values() if c > 0])} categories")
print()

# Stats
stats = {
    "successful": sum(existing_counts.values()),
    "failed": 0,
    "by_category": dict(existing_counts),
    "start_time": datetime.now().isoformat(),
}
stats_lock = threading.Lock()
write_lock = threading.Lock()

# Category-specific prompts
CATEGORY_PROMPTS = {
    "marpol_details": "MARPOL (International Convention for the Prevention of Pollution from Ships) - focus on Annexes I-VI, discharge criteria, record keeping",
    "solas_specifics": "SOLAS (Safety of Life at Sea) - focus on chapters, certificates, surveys, equipment requirements",
    "enclosed_space": "Enclosed space entry procedures - CRITICAL SAFETY: gas testing, permits, ventilation, rescue procedures",
    "fire_emergency": "Fire emergency procedures - fire classes, extinguishing systems, boundary cooling, muster procedures",
    "stability_calculations": "Ship stability calculations - GM, GZ curves, loading conditions, free surface effect",
    "gmdss": "GMDSS (Global Maritime Distress and Safety System) - radio equipment, distress procedures, certificates",
}

def get_category_description(category):
    """Get description for category."""
    if category in CATEGORY_PROMPTS:
        return CATEGORY_PROMPTS[category]
    return category.replace("_", " ").title()

def generate_sample(api_key, worker_id, category):
    """Generate one sample using Cerebras with JSON output."""
    url = "https://api.cerebras.ai/v1/chat/completions"
    
    category_desc = get_category_description(category)
    
    # Use JSON format for reliable parsing
    prompt = f"""Generate a detailed maritime training question and answer about: {category_desc}

Return ONLY valid JSON in this exact format:
{{
  "question": "A detailed maritime scenario question (100-200 words)",
  "answer": "A comprehensive step-by-step answer with procedures, regulations, and safety considerations (250-500 words)"
}}

Requirements:
- Question must be a realistic operational scenario
- Answer must include specific regulatory citations (MARPOL/SOLAS/STCW where applicable)
- Include step-by-step procedures
- Include safety considerations
- Use proper maritime terminology

Generate the JSON now:"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3.1-8b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.9,
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=data, headers=headers, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"].strip()
                
                # Try to extract JSON
                # Look for { } brackets
                start = text.find('{')
                end = text.rfind('}')
                
                if start != -1 and end != -1:
                    json_text = text[start:end+1]
                    
                    try:
                        qa_data = json.loads(json_text)
                        
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
                    except json.JSONDecodeError:
                        pass
            
            elif response.status_code == 429:
                # Rate limit - wait and retry
                time.sleep(5 * (attempt + 1))
                continue
            
        except Exception as e:
            if attempt == 2:
                pass  # Silent fail on last attempt
            else:
                time.sleep(2)
    
    return None

def worker(worker_id, api_key, task_queue):
    """Worker thread."""
    while True:
        try:
            task = task_queue.get(timeout=2)
            if task is None:
                break
            
            category = task
            sample = generate_sample(api_key, worker_id, category)
            
            if sample:
                with write_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                with stats_lock:
                    stats["successful"] += 1
                    stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
                    
                    if stats["successful"] % 100 == 0:
                        total = sum(CATEGORY_TARGETS.values()) + sum(existing_counts.values())
                        pct = 100 * stats["successful"] / total
                        print(f"   ✅ {stats['successful']}/{total} samples ({pct:.1f}%)")
                        
                        # Save progress
                        with open(STATS_FILE, 'w') as sf:
                            json.dump(stats, sf, indent=2)
            else:
                with stats_lock:
                    stats["failed"] += 1
            
            time.sleep(1.2)  # Rate limit
            task_queue.task_done()
            
        except:
            break

# Create task queue with proper category distribution
task_queue = Queue()

print("📝 Building task queue with category distribution...")
for category, target_count in CATEGORY_TARGETS.items():
    if target_count > 0:
        for _ in range(target_count):
            task_queue.put(category)

print(f"   {task_queue.qsize()} tasks queued")
print()

# Start workers
threads = []
for i, key in enumerate(cerebras_keys):
    t = threading.Thread(
        target=worker,
        args=(f"cerebras_{i+1}", key, task_queue),
        daemon=True
    )
    t.start()
    threads.append(t)

print(f"✅ {len(threads)} workers started!")
print("=" * 80)
print("GENERATING... (Press Ctrl+C to stop - progress auto-saved)")
print("=" * 80)
print()

# Monitor
try:
    task_queue.join()
except KeyboardInterrupt:
    print("\n⚠️  Interrupted! Saving progress...")

# Stop workers
for _ in threads:
    task_queue.put(None)

for t in threads:
    t.join(timeout=3)

# Final stats
print()
print("=" * 80)
print("GENERATION COMPLETE!")
print("=" * 80)
print(f"✅ Total generated: {stats['successful']}")
print(f"❌ Failed: {stats['failed']}")
print(f"📈 Success rate: {100*stats['successful']/(stats['successful']+stats['failed']):.1f}%")
print()
print("By category (top 10):")
sorted_cats = sorted(stats["by_category"].items(), key=lambda x: x[1], reverse=True)
for cat, count in sorted_cats[:10]:
    target = CATEGORY_TARGETS.get(cat, 0) + existing_counts.get(cat, 0)
    print(f"  {cat:30} {count:5} / {target}")
print()
print(f"💾 Output: {OUTPUT_FILE}")

with open(STATS_FILE, 'w') as f:
    json.dump(stats, f, indent=2)
