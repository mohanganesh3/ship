#!/usr/bin/env python3
"""
Optimized Maritime Data Generator
- Batched file writes (100 samples per flush)
- Minimal lock contention
- Thread-local buffers
- High-performance architecture
"""

import json
import time
import threading
import random
import requests
import argparse
from queue import Queue
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

# Import data from original script
import sys
sys.path.insert(0, '/home/mohanganesh/ship/scripts')
from multi_account_real_generator import (
    REAL_MARITIME_SCENARIOS,
    MARITIME_CALCULATIONS, 
    STANDARD_PROCEDURES,
    create_real_scenario_prompt,
    create_calculation_prompt,
    create_procedure_prompt
)

OUTPUT_FILE = "/home/mohanganesh/ship/training/real_maritime_data/maritime_real_scenarios.jsonl"
BUFFER_SIZE = 100  # Write every 100 samples

@dataclass
class APIAccount:
    provider: str
    api_key: str
    account_id: str

# Global atomic counter (thread-safe without locks for reads)
class AtomicCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, delta=1):
        with self._lock:
            self._value += delta
            return self._value
    
    @property
    def value(self):
        return self._value

# Global counters
successful_counter = AtomicCounter()
failed_counter = AtomicCounter()

# Single file write lock (only used during batch flush)
file_lock = threading.Lock()

def load_accounts(config_file: str) -> List[APIAccount]:
    """Load API accounts from JSON config."""
    with open(config_file) as f:
        config = json.load(f)
    
    accounts = []
    for acc in config["accounts"]:
        account_name = acc.get("name", f"account_{len(accounts)}")
        
        # Skip Google (quota exhausted)
        # Google account - SKIP
        # if acc.get("google_api_key"):
        #     accounts.append(APIAccount(
        #         provider="google",
        #         api_key=acc["google_api_key"],
        #         account_id=f"{account_name}_google"
        #     ))
        
        # Cerebras account  
        if acc.get("cerebras_api_key"):
            accounts.append(APIAccount(
                provider="cerebras",
                api_key=acc["cerebras_api_key"],
                account_id=f"{account_name}_cerebras"
            ))
        
        # Groq account
        if acc.get("groq_api_key"):
            accounts.append(APIAccount(
                provider="groq",
                api_key=acc["groq_api_key"],
                account_id=f"{account_name}_groq"
            ))
    
    return accounts

def generate_api_call(provider: str, api_key: str, prompt: str) -> Optional[str]:
    """Make API call to generate text."""
    try:
        if provider == "cerebras":
            response = requests.post(
                'https://api.cerebras.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'llama3.1-8b',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000,
                    'temperature': 0.7
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
                
        elif provider == "groq":
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'llama-3.1-8b-instant',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000,
                    'temperature': 0.7
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
    
    except Exception as e:
        # Silent failure for speed
        pass
    
    return None

def parse_response(text: str) -> Optional[Dict[str, str]]:
    """Parse response from API (simplified for speed)."""
    try:
        if "QUESTION:" not in text or "ANSWER:" not in text:
            return None
        
        # Extract question
        q_start = text.find("QUESTION:") + 9
        a_start = text.find("ANSWER:")
        if a_start == -1:
            return None
        
        question = text[q_start:a_start].strip()
        answer = text[a_start + 7:].strip()
        
        # Quick extraction before additional sections
        for section in ["REGULATORY REFERENCES:", "SAFETY CONSIDERATIONS:"]:
            if section in answer:
                answer = answer.split(section)[0].strip()
        
        # Quality checks
        if len(question) < 30 or len(answer) < 150:
            return None
        
        # Check for refusals
        answer_lower = answer.lower()
        if any(p in answer_lower for p in ["i cannot", "i can't", "as an ai"]):
            return None
        
        return {"question": question, "answer": answer}
        
    except:
        return None

def worker_loop(account: APIAccount, task_queue: Queue):
    """Optimized worker with local buffer."""
    
    local_buffer = []
    
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:
                break
            
            task_type, task_data, task_id = task
            
            # Create prompt
            if task_type == "real_scenario":
                scenario_type, scenario_data = task_data
                prompt = create_real_scenario_prompt(scenario_data, scenario_type)
            elif task_type == "calculation":
                category, calc_topic = task_data
                prompt = create_calculation_prompt(calc_topic, category)
            elif task_type == "procedure":
                category, procedure = task_data
                prompt = create_procedure_prompt(procedure, category)
            else:
                task_queue.task_done()
                continue
            
            # Generate
            response = generate_api_call(account.provider, account.api_key, prompt)
            
            if response:
                parsed = parse_response(response)
                if parsed:
                    sample = {
                        "id": f"{task_type}_{task_id}_{int(time.time()*1000)}",
                        "type": task_type,
                        "scenario_category": task_data[0],
                        "question": parsed["question"],
                        "answer": parsed["answer"],
                        "provider": account.provider,
                        "account": account.account_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Add to local buffer
                    local_buffer.append(sample)
                    
                    # Flush buffer when full
                    if len(local_buffer) >= BUFFER_SIZE:
                        with file_lock:
                            with open(OUTPUT_FILE, 'a') as f:
                                for s in local_buffer:
                                    f.write(json.dumps(s) + '\n')
                        successful_counter.increment(len(local_buffer))
                        local_buffer = []
                else:
                    failed_counter.increment()
            else:
                failed_counter.increment()
            
            task_queue.task_done()
            
            # Minimal delay (0.1s for better throughput)
            time.sleep(0.1)
            
        except Exception as e:
            # Silently continue for maximum performance
            pass
    
    # Flush remaining buffer on exit
    if local_buffer:
        with file_lock:
            with open(OUTPUT_FILE, 'a') as f:
                for s in local_buffer:
                    f.write(json.dumps(s) + '\n')
        successful_counter.increment(len(local_buffer))

def main():
    parser = argparse.ArgumentParser(description="Optimized maritime data generator")
    parser.add_argument("--config", default="accounts.json", help="Accounts config")
    parser.add_argument("--target", type=int, required=True, help="Target samples")
    args = parser.parse_args()
    
    print("🚀 OPTIMIZED MARITIME DATA GENERATOR")
    print("=" * 70)
    
    # Load accounts
    accounts = load_accounts(args.config)
    print(f"✓ Loaded {len(accounts)} API accounts")
    
    provider_counts = defaultdict(int)
    for acc in accounts:
        provider_counts[acc.provider] += 1
    
    for provider, count in provider_counts.items():
        print(f"  - {provider}: {count} accounts")
    
    print(f"\n🎯 Target: {args.target:,} samples")
    print(f"📁 Output: {OUTPUT_FILE}")
    print(f"⚡ Optimizations: Batched writes, minimal locks, 0.1s delay")
    print("=" * 70)
    
    # Initialize
    task_queue = Queue()
    
    # Start workers
    workers = []
    for account in accounts:
        t = threading.Thread(target=worker_loop, args=(account, task_queue), daemon=True)
        t.start()
        workers.append(t)
    
    print(f"\n✓ Started {len(workers)} workers")
    
    # Generate tasks
    print(f"\n📋 Generating {args.target:,} tasks...")
    
    task_id = 0
    
    # Real scenarios (60%)
    real_count = int(args.target * 0.60)
    for scenario_type, scenarios in REAL_MARITIME_SCENARIOS.items():
        scenarios_needed = real_count // len(REAL_MARITIME_SCENARIOS)
        for i in range(scenarios_needed):
            scenario_data = random.choice(scenarios)
            task_queue.put(("real_scenario", (scenario_type, scenario_data), task_id))
            task_id += 1
    
    # Calculations (20%)
    calc_count = int(args.target * 0.20)
    all_calcs = [(cat, calc) for cat, calcs in MARITIME_CALCULATIONS.items() for calc in calcs]
    for i in range(calc_count):
        category, calc = random.choice(all_calcs)
        task_queue.put(("calculation", (category, calc), task_id))
        task_id += 1
    
    # Procedures (20%)
    proc_count = int(args.target * 0.20)
    all_procs = [(cat, proc) for cat, procs in STANDARD_PROCEDURES.items() for proc in procs]
    for i in range(proc_count):
        category, proc = random.choice(all_procs)
        task_queue.put(("procedure", (category, proc), task_id))
        task_id += 1
    
    print(f"✓ Queued {task_id:,} tasks")
    
    # Monitor
    print("\n🔄 Generation in progress...\n")
    start_time = time.time()
    last_count = 0
    last_time = start_time
    
    while not task_queue.empty() or any(w.is_alive() for w in workers):
        time.sleep(5)
        
        current = successful_counter.value
        now = time.time()
        
        # Calculate rates
        delta = current - last_count
        time_delta = now - last_time
        instant_rate = delta / time_delta if time_delta > 0 else 0
        
        elapsed = now - start_time
        avg_rate = current / elapsed if elapsed > 0 else 0
        
        remaining = args.target - current
        eta_hours = remaining / (avg_rate * 3600) if avg_rate > 0 else 0
        
        pct = (current / args.target * 100) if args.target > 0 else 0
        
        print(f"   {current:,}/{args.target:,} ({pct:.1f}%) | "
              f"Rate: {instant_rate:.1f}/s ({int(avg_rate*3600):,}/hr) | "
              f"Queue: {task_queue.qsize():,} | ETA: {eta_hours:.1f}h")
        
        last_count = current
        last_time = now
    
    # Stop workers
    for _ in workers:
        task_queue.put(None)
    for t in workers:
        t.join()
    
    # Final stats
    total_time = time.time() - start_time
    final_count = successful_counter.value
    final_rate = final_count / total_time if total_time > 0 else 0
    
    print("\n" + "=" * 70)
    print("✅ GENERATION COMPLETE")
    print(f"   Total: {final_count:,} samples")
    print(f"   Failed: {failed_counter.value:,}")
    print(f"   Time: {total_time/60:.1f} minutes")
    print(f"   Rate: {final_rate:.2f} samples/sec = {int(final_rate*86400):,} samples/day")
    print("=" * 70)

if __name__ == "__main__":
    main()
