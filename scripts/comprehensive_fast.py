#!/usr/bin/env python3
"""
OPTIMIZED Comprehensive Maritime Data Generation - Parallel Processing
Uses all 3 APIs in parallel with multiple workers per API
Target: 500K samples in 24-48 hours
"""

import json
import os
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue

# API Configuration (SAME AS BEFORE)
GOOGLE_API_KEY = "GOOGLE_API_KEY_PLACEHOLDER"
CEREBRAS_API_KEY = "CEREBRAS_API_KEY_PLACEHOLDER"
GROQ_API_KEY = "GROQ_API_KEY_PLACEHOLDER"

OUTPUT_DIR = Path("/home/mohanganesh/ship/training/comprehensive_data_fast")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = OUTPUT_DIR / "generation_progress.json"
OUTPUT_FILE = OUTPUT_DIR / "maritime_qa_comprehensive.jsonl"
STATS_FILE = OUTPUT_DIR / "generation_stats.json"

TARGET_SAMPLES = 500000
BATCH_SIZE = 1000
MAX_WORKERS_PER_API = 5  # 5 workers per API = 15 total
RATE_LIMIT_DELAY = 0.1  # 100ms between requests per worker

# Simplified topic structure for faster generation
MARITIME_CATEGORIES = [
    "navigation", "engineering", "safety", "cargo_ops", "regulations",
    "stability", "communications", "seamanship", "emergency", "equipment"
]

QUESTION_TYPES = [
    "procedure", "troubleshooting", "calculation", "regulation", 
    "safety", "best_practice", "emergency", "maintenance"
]

write_lock = threading.Lock()
stats_lock = threading.Lock()

@dataclass
class Stats:
    successful: int = 0
    failed: int = 0
    google: int = 0
    cerebras: int = 0
    groq: int = 0
    start_time: str = ""
    
def load_stats() -> Stats:
    if STATS_FILE.exists():
        with open(STATS_FILE) as f:
            return Stats(**json.load(f))
    return Stats(start_time=datetime.now().isoformat())

def save_stats(stats: Stats):
    with stats_lock:
        with open(STATS_FILE, 'w') as f:
            json.dump(asdict(stats), f)

def generate_google(prompt: str, worker_id: int) -> Optional[str]:
    """Generate from Google Gemini."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 600, "temperature": 0.9}
        }
        response = requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout=45)
        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
    except:
        pass
    return None

def generate_cerebras(prompt: str, worker_id: int) -> Optional[str]:
    """Generate from Cerebras."""
    try:
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama3.1-8b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.9
        }
        response = requests.post(url, json=data, headers=headers, timeout=45)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return None

def generate_groq(prompt: str, worker_id: int) -> Optional[str]:
    """Generate from Groq."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 600,
            "temperature": 0.9
        }
        response = requests.post(url, json=data, headers=headers, timeout=45)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except:
        pass
    return None

def create_prompt(category: str, qtype: str, num: int) -> str:
    """Create generation prompt."""
    return f"""You are a maritime expert creating training data for ship officers.

Category: {category}
Type: {qtype}
Context: Real-world maritime operations, safety, regulations

Generate a detailed, practical maritime question and comprehensive answer.

REQUIREMENTS:
- Question: Specific, realistic scenario officers face
- Answer: 200-400 words, technically accurate
- Include: procedures, safety, regulations (SOLAS/MARPOL/STCW)
- Use proper maritime terminology
- For emergencies: emphasize safety
- For calculations: show steps

Format EXACTLY:
QUESTION: [detailed question]

ANSWER: [comprehensive answer]

Generate:"""

def parse_response(text: str) -> Optional[Tuple[str, str]]:
    """Parse Q&A from response."""
    try:
        if "QUESTION:" not in text or "ANSWER:" not in text:
            return None
        parts = text.split("ANSWER:")
        q = parts[0].replace("QUESTION:", "").strip()
        a = parts[1].strip()
        if len(q) < 20 or len(a) < 100:
            return None
        if any(p in a.lower() for p in ["i cannot", "i can't", "as an ai"]):
            return None
        return (q, a)
    except:
        return None

def worker_loop(api_func, api_name: str, worker_id: int, task_queue: Queue, stats: Stats):
    """Worker thread that processes tasks."""
    file_handle = open(OUTPUT_FILE, 'a')
    
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:  # Poison pill
                break
            
            category, qtype, num = task
            
            # Generate
            prompt = create_prompt(category, qtype, num)
            response = api_func(prompt, worker_id)
            
            if response:
                parsed = parse_response(response)
                if parsed:
                    q, a = parsed
                    sample = {
                        "id": f"{category}_{qtype}_{num}_{int(time.time())}_{worker_id}",
                        "category": category,
                        "question_type": qtype,
                        "question": q,
                        "answer": a,
                        "provider": api_name,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Write to file
                    with write_lock:
                        file_handle.write(json.dumps(sample) + '\n')
                        file_handle.flush()
                    
                    # Update stats
                    with stats_lock:
                        stats.successful += 1
                        if api_name == "google":
                            stats.google += 1
                        elif api_name == "cerebras":
                            stats.cerebras += 1
                        elif api_name == "groq":
                            stats.groq += 1
                    
                    if stats.successful % 100 == 0:
                        save_stats(stats)
                else:
                    with stats_lock:
                        stats.failed += 1
            else:
                with stats_lock:
                    stats.failed += 1
            
            task_queue.task_done()
            time.sleep(RATE_LIMIT_DELAY)
            
        except Exception as e:
            pass
    
    file_handle.close()

def main():
    print("🚀 OPTIMIZED Maritime Data Generation - Parallel Processing")
    print("=" * 70)
    print(f"Target: {TARGET_SAMPLES:,} samples")
    print(f"Workers: {MAX_WORKERS_PER_API} per API × 3 APIs = {MAX_WORKERS_PER_API * 3} total")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 70)
    
    stats = load_stats()
    task_queue = Queue()
    
    # Create workers
    workers = []
    
    # Google workers
    for i in range(MAX_WORKERS_PER_API):
        t = threading.Thread(target=worker_loop, args=(generate_google, "google", i, task_queue, stats))
        t.start()
        workers.append(t)
    
    # Cerebras workers
    for i in range(MAX_WORKERS_PER_API):
        t = threading.Thread(target=worker_loop, args=(generate_cerebras, "cerebras", i + 10, task_queue, stats))
        t.start()
        workers.append(t)
    
    # Groq workers
    for i in range(MAX_WORKERS_PER_API):
        t = threading.Thread(target=worker_loop, args=(generate_groq, "groq", i + 20, task_queue, stats))
        t.start()
        workers.append(t)
    
    print(f"✓ Started {len(workers)} workers")
    
    # Fill task queue
    print(f"📋 Generating {TARGET_SAMPLES:,} tasks...")
    start_time = time.time()
    
    for i in range(TARGET_SAMPLES):
        category = random.choice(MARITIME_CATEGORIES)
        qtype = random.choice(QUESTION_TYPES)
        task_queue.put((category, qtype, i))
        
        if i % 10000 == 0 and i > 0:
            print(f"   Queued {i:,} tasks...")
    
    print(f"✓ All tasks queued in {time.time() - start_time:.1f}s")
    print("\n🔄 Generation in progress...")
    print("   Monitor: python3 scripts/monitor_comprehensive.py")
    print()
    
    # Monitor progress
    last_count = 0
    while not task_queue.empty() or any(w.is_alive() for w in workers):
        time.sleep(10)
        current = stats.successful
        delta = current - last_count
        last_count = current
        
        elapsed = time.time() - start_time
        rate = stats.successful / elapsed if elapsed > 0 else 0
        remaining = TARGET_SAMPLES - stats.successful
        eta = remaining / rate / 3600 if rate > 0 else 0
        
        print(f"   Progress: {stats.successful:,}/{TARGET_SAMPLES:,} ({stats.successful/TARGET_SAMPLES*100:.1f}%) | "
              f"Rate: {rate:.1f}/s ({rate * 3600:.0f}/hr) | +{delta} | ETA: {eta:.1f}h")
        
        if stats.successful % 1000 == 0:
            save_stats(stats)
    
    # Stop workers
    for _ in workers:
        task_queue.put(None)
    
    for w in workers:
        w.join()
    
    save_stats(stats)
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print("🎉 GENERATION COMPLETE!")
    print(f"✓ Total: {stats.successful:,} successful, {stats.failed:,} failed")
    print(f"⏱️  Time: {elapsed/3600:.2f} hours")
    print(f"⚡ Rate: {stats.successful/elapsed:.2f}/s ({stats.successful/elapsed * 3600:.0f}/hr)")
    print(f"📊 Providers: Google={stats.google:,}, Cerebras={stats.cerebras:,}, Groq={stats.groq:,}")
    print("=" * 70)

if __name__ == "__main__":
    main()
