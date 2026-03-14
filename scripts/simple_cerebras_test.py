#!/usr/bin/env python3
"""
🚀 SIMPLE CEREBRAS-ONLY GENERATOR
Uses 25 Cerebras keys to generate maritime samples
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
# Append mode to continue from existing samples
STATS_FILE = Path("/home/mohanganesh/ship/training/orchestrated_60k/stats.json")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

# Sample target - CONTINUE GENERATION
EXISTING_SAMPLES = 9393  # Already generated
TOTAL_TARGET = 42515 - EXISTING_SAMPLES  # Generate remaining 33,122
CATEGORIES = [
    "marpol_details", "solas_specifics", "stcw_competencies", "ism_code",
    "isps_code", "mlc_2006", "port_state_control", "fire_emergency",
    "enclosed_space", "man_overboard", "abandon_ship", "medical_emergencies",
    "collision_damage", "grounding_response", "flooding_control", "cargo_operations",
    "ballast_operations", "bunkering", "mooring_anchoring", "watchkeeping",
    "drills", "stability_calculations", "cargo_calculations", "navigation_calculations",
    "fuel_calculations", "trim_corrections", "gmdss", "lifesaving_equipment",
    "fire_detection", "navigation_equipment", "engineering_systems", "heavy_weather",
    "ice_navigation", "piracy", "canal_transit", "unusual_incidents"
]

# Round-robin category assignment
def get_category(task_num):
    return CATEGORIES[task_num % len(CATEGORIES)]

# Load Cerebras keys
with open("/home/mohanganesh/ship/accounts_MASTER.json") as f:
    accounts = json.load(f)["accounts"]
    cerebras_keys = [acc["cerebras_api_key"] for acc in accounts if acc.get("cerebras_api_key")]

print(f"🚀 Starting generation with {len(cerebras_keys)} Cerebras keys")
print(f"   Target: {TOTAL_TARGET} samples")
print(f"   Output: {OUTPUT_FILE}")

# Stats
stats = {
    "successful": 0,
    "failed": 0,
    "start_time": datetime.now().isoformat(),
}
stats_lock = threading.Lock()
write_lock = threading.Lock()

def generate_sample(api_key, worker_id, category):
    """Generate one sample using Cerebras."""
    url = "https://api.cerebras.ai/v1/chat/completions"
    
    category_name = category.replace("_", " ").title()
    prompt = f"""Generate a detailed maritime question and answer about {category_name}.

Format your response EXACTLY as:
QUESTION: [your detailed question here - 100-200 words]

ANSWER: [your detailed answer here - 250-400 words with step-by-step procedures, safety considerations, and regulatory citations]"""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3.1-8b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.9,
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            text = result["choices"][0]["message"]["content"].strip()
            
            # Parse Q&A - more lenient parsing
            if "QUESTION:" in text.upper() and "ANSWER:" in text.upper():
                # Split on ANSWER: (case insensitive)
                text_upper = text.upper()
                answer_pos = text_upper.find("ANSWER:")
                question_part = text[:answer_pos]
                answer_part = text[answer_pos:]
                
                # Extract question
                q_markers = ["QUESTION:", "Question:", "QUESTION", "**QUESTION:**"]
                question = question_part
                for marker in q_markers:
                    if marker in question_part:
                        question = question_part.split(marker, 1)[1].strip()
                        break
                
                # Extract answer
                a_markers = ["ANSWER:", "Answer:", "ANSWER", "**ANSWER:**"]
                answer = answer_part
                for marker in a_markers:
                    if marker in answer_part:
                        answer = answer_part.split(marker, 1)[1].strip()
                        break
                
                # Clean up markdown formatting
                question = question.replace("**", "").replace("****", "").strip()
                answer = answer.replace("**", "").strip()
                
                if len(question) > 30 and len(answer) > 100:
                    return {
                        "category": category,
                        "question": question,
                        "answer": answer,
                        "worker_id": worker_id,
                        "generated_at": datetime.now().isoformat(),
                    }
        
        return None
        
    except Exception as e:
        print(f"   Worker {worker_id} error: {e}")
        return None

def worker(worker_id, api_key, task_queue):
    """Worker thread."""
    while True:
        try:
            task_num = task_queue.get(timeout=1)
            if task_num is None:
                break
            
            category = get_category(task_num)
            sample = generate_sample(api_key, worker_id, category)
            
            if sample:
                with write_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                with stats_lock:
                    stats["successful"] += 1
                    if stats["successful"] % 100 == 0:
                        print(f"   ✅ {stats['successful']}/{TOTAL_TARGET} samples ({100*stats['successful']/TOTAL_TARGET:.1f}%)")
            else:
                with stats_lock:
                    stats["failed"] += 1
            
            time.sleep(1.5)  # Rate limit: ~40 RPM
            task_queue.task_done()
            
        except:
            break

# Create task queue
task_queue = Queue()
for i in range(TOTAL_TARGET):
    task_queue.put(i)

# Start workers
threads = []
for i, key in enumerate(cerebras_keys):
    t = threading.Thread(target=worker, args=(f"cerebras_{i+1}", key, task_queue), daemon=True)
    t.start()
    threads.append(t)

print(f"\n✅ {len(threads)} workers started!\n")

# Wait for completion
task_queue.join()

# Stop workers
for _ in threads:
    task_queue.put(None)

for t in threads:
    t.join(timeout=2)

# Final stats
print(f"\n{'='*80}")
print(f"COMPLETE!")
print(f"{'='*80}")
print(f"✅ Successful: {stats['successful']}")
print(f"❌ Failed: {stats['failed']}")
print(f"💾 Output: {OUTPUT_FILE}")

with open(STATS_FILE, 'w') as f:
    json.dump(stats, f, indent=2)
