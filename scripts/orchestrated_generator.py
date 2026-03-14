#!/usr/bin/env python3
"""
ORCHESTRATED MARITIME DATA GENERATOR
Distributes 500K samples across categories and accounts intelligently
"""

import json
import os
import sys
import time
import threading
import queue
import random
from datetime import datetime
from pathlib import Path

# Import our scenario definitions
sys.path.append(os.path.dirname(__file__))
from real_maritime_scenarios import (
    REAL_MARITIME_SCENARIOS,
    MARITIME_CALCULATIONS,
    STANDARD_PROCEDURES
)

# ============================================================================
# ORCHESTRATION PLAN: 500K Samples Distributed by Category
# ============================================================================

GENERATION_PLAN = {
    # Format: "category": (target_samples, priority_weight)
    
    # REAL SCENARIOS (300,000 total - 60%)
    "navigation_real_scenarios": (100000, 1.0),      # Highest priority
    "engineering_real_scenarios": (60000, 0.9),
    "safety_real_scenarios": (60000, 1.0),           # Safety critical
    "cargo_real_scenarios": (40000, 0.8),
    "regulations_real_scenarios": (20000, 0.7),
    "stability_real_scenarios": (10000, 0.7),
    "communications_real_scenarios": (10000, 0.6),
    
    # CALCULATIONS (100,000 total - 20%)
    "navigation_calculations": (40000, 0.8),
    "stability_calculations": (30000, 0.7),
    "cargo_calculations": (20000, 0.6),
    "engineering_calculations": (10000, 0.6),
    
    # PROCEDURES (100,000 total - 20%)
    "bridge_procedures": (30000, 0.7),
    "engine_procedures": (25000, 0.7),
    "safety_procedures": (25000, 0.8),
    "cargo_procedures": (20000, 0.6),
}

TOTAL_TARGET = sum(count for count, _ in GENERATION_PLAN.values())
print(f"Total target samples in plan: {TOTAL_TARGET}")

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = Path("/home/mohanganesh/ship/training/real_maritime_data")
OUTPUT_FILE = OUTPUT_DIR / "maritime_real_scenarios.jsonl"
PROGRESS_FILE = OUTPUT_DIR / "orchestration_progress.json"
STATS_FILE = OUTPUT_DIR / "orchestration_stats.json"

# API Configuration
CEREBRAS_ENDPOINT = "https://api.cerebras.ai/v1/chat/completions"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GOOGLE_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

# Rate limiting (per account per day for Google)
GOOGLE_DAILY_LIMIT = 1500
GOOGLE_RATE_DELAY = 0.6  # ~60 seconds / 1500 = 0.04, but be conservative

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_progress():
    """Load generation progress to resume"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {category: 0 for category in GENERATION_PLAN.keys()}

def save_progress(progress):
    """Save current progress"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_accounts(config_file="accounts.json"):
    """Load API accounts from config"""
    with open(config_file, 'r') as f:
        data = json.load(f)
    return data['accounts']

def assign_accounts_to_categories(accounts, progress):
    """
    Intelligently assign accounts to categories based on:
    - Remaining work in each category
    - Account API provider (Google preferred for sustained work)
    - Load balancing
    """
    assignments = {}
    
    # Calculate remaining work per category
    remaining = {}
    for category, (target, _) in GENERATION_PLAN.items():
        done = progress.get(category, 0)
        remaining[category] = max(0, target - done)
    
    # Sort categories by remaining work (descending)
    sorted_categories = sorted(remaining.items(), key=lambda x: x[1], reverse=True)
    
    # Assign accounts round-robin to categories with work remaining
    active_categories = [cat for cat, rem in sorted_categories if rem > 0]
    
    if not active_categories:
        print("✅ All categories complete!")
        return {}
    
    # Distribute accounts
    for idx, account in enumerate(accounts):
        # Assign to category (round-robin)
        category = active_categories[idx % len(active_categories)]
        
        if category not in assignments:
            assignments[category] = []
        
        # Determine which API to use from this account
        if account.get('google_api_key'):
            api_type = 'google'
            api_key = account['google_api_key']
        elif account.get('cerebras_api_key'):
            api_type = 'cerebras'
            api_key = account['cerebras_api_key']
        elif account.get('groq_api_key'):
            api_type = 'groq'
            api_key = account['groq_api_key']
        else:
            continue  # Skip accounts with no valid keys
        
        assignments[category].append({
            'account_name': account['name'],
            'api_type': api_type,
            'api_key': api_key
        })
    
    return assignments

def create_prompt_for_category(category, scenario_data=None):
    """Create appropriate prompt based on category type"""
    
    if category.endswith('_real_scenarios'):
        # Real scenario
        if scenario_data is None:
            # Pick random scenario from this category
            scenarios = REAL_MARITIME_SCENARIOS.get(category, [])
            if not scenarios:
                return None
            scenario_data = random.choice(scenarios)
        
        scenario = scenario_data["scenario"]
        context = scenario_data["context"]
        must_include = scenario_data["must_include"]
        safety_critical = scenario_data.get("safety_critical", False)
        basis = scenario_data.get("real_incident_basis", "industry standard practice")
        
        prompt = f"""You are a senior maritime officer with 20+ years experience creating life-safety training scenarios.

REAL SCENARIO (Based on: {basis}):
Scenario Type: {category}
Scenario Title: {scenario}
Situation: {context}

CRITICAL REQUIREMENTS - Every answer MUST include:
{chr(10).join(f'- {item}' for item in must_include)}

{"⚠️ SAFETY CRITICAL: This scenario involves life-safety. Answer must emphasize safety procedures." if safety_critical else ""}

Generate a detailed question and comprehensive answer for this REAL maritime situation.

ANSWER MUST:
1. Reference specific regulations (SOLAS/MARPOL/STCW where applicable)
2. List step-by-step procedures in correct order
3. Emphasize safety considerations
4. Include communications/notifications required
5. Mention documentation/record-keeping
6. Be 300-500 words with technical accuracy

Format EXACTLY as:
QUESTION: [Specific question about this scenario]

ANSWER: [Comprehensive step-by-step answer]

Generate now:"""
        
        return prompt, scenario_data
    
    elif '_calculations' in category:
        # Calculation problem
        calc_topics = MARITIME_CALCULATIONS
        topic = random.choice(calc_topics)
        
        prompt = f"""You are a maritime academy instructor creating calculation problems for officers.

CALCULATION TOPIC: {topic}
CATEGORY: {category}

Create a realistic maritime calculation problem with:
1. Clear problem statement with all given values and units
2. Step-by-step solution showing ALL working
3. Formulas used with explanations
4. Final answer clearly stated and verified

Requirements:
- Use realistic maritime values (ship speeds, distances, weights, etc.)
- Show complete working (200-400 words)
- Include units throughout
- Verify answer makes sense

Format EXACTLY as:
QUESTION: [Calculation problem with all given values]

ANSWER: [Step-by-step solution with formulas and working]

Generate now:"""
        
        return prompt, {"calculation_topic": topic}
    
    elif '_procedures' in category:
        # Standard procedure
        procedures = STANDARD_PROCEDURES
        procedure = random.choice(procedures)
        
        prompt = f"""You are writing ship's standard operating procedures (SOPs).

PROCEDURE CATEGORY: {category}
PROCEDURE: {procedure}

Create a detailed SOP covering:
1. When to use this procedure (context)
2. Step-by-step instructions (numbered, clear)
3. Safety precautions and warnings
4. Required equipment and personnel
5. Regulatory basis (which regulation requires this)
6. Common mistakes to avoid
7. Documentation required

Requirements:
- 200-400 words
- Practical and actionable
- Safety focused

Format EXACTLY as:
QUESTION: When and how to perform [procedure name]?

ANSWER: [Complete SOP with all sections above]

Generate now:"""
        
        return prompt, {"procedure": procedure}
    
    return None, None

# ============================================================================
# GENERATION WORKER
# ============================================================================

def worker_thread(worker_id, category, account_info, target_samples, progress_lock, shared_progress, output_lock):
    """
    Worker thread for one account generating samples for one category
    """
    import requests
    
    account_name = account_info['account_name']
    api_type = account_info['api_type']
    api_key = account_info['api_key']
    
    print(f"🚀 Worker {worker_id} ({account_name}/{api_type}): Starting on {category}, target={target_samples}")
    
    generated = 0
    errors = 0
    
    while generated < target_samples:
        try:
            # Create prompt
            prompt_data = create_prompt_for_category(category)
            if prompt_data[0] is None:
                print(f"⚠️ Worker {worker_id}: No more prompts for {category}")
                break
            
            prompt, metadata = prompt_data
            
            # Generate
            if api_type == 'google':
                url = GOOGLE_ENDPOINT_TEMPLATE.format(api_key=api_key)
                headers = {"Content-Type": "application/json"}
                data = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 1000,
                        "temperature": 0.7
                    }
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    errors += 1
                    print(f"❌ Worker {worker_id}: Google API error {response.status_code}")
                    time.sleep(5)
                    continue
                
                time.sleep(GOOGLE_RATE_DELAY)
            
            elif api_type == 'cerebras':
                url = CEREBRAS_ENDPOINT
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                data = {
                    "model": "llama3.1-8b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=60)
                if response.status_code == 200:
                    text = response.json()["choices"][0]["message"]["content"].strip()
                else:
                    errors += 1
                    print(f"❌ Worker {worker_id}: Cerebras API error {response.status_code}")
                    time.sleep(5)
                    continue
                
                time.sleep(0.3)
            
            elif api_type == 'groq':
                url = GROQ_ENDPOINT
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                data = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=60)
                if response.status_code == 200:
                    text = response.json()["choices"][0]["message"]["content"].strip()
                else:
                    errors += 1
                    print(f"❌ Worker {worker_id}: Groq API error {response.status_code}")
                    time.sleep(5)
                    continue
                
                time.sleep(0.2)
            
            # Parse response
            if "QUESTION:" in text and "ANSWER:" in text:
                parts = text.split("ANSWER:", 1)
                question = parts[0].replace("QUESTION:", "").strip()
                answer = parts[1].strip()
                
                # Create sample
                sample = {
                    "id": f"{category}_{worker_id}_{generated}_{int(time.time())}",
                    "type": "real_scenario" if "_real_scenarios" in category else ("calculation" if "_calculations" in category else "procedure"),
                    "category": category,
                    "question": question,
                    "answer": answer,
                    "provider": api_type,
                    "account": account_name,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata
                }
                
                # Write to file (thread-safe)
                with output_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                # Update progress (thread-safe)
                with progress_lock:
                    shared_progress[category] = shared_progress.get(category, 0) + 1
                
                generated += 1
                
                if generated % 100 == 0:
                    print(f"✅ Worker {worker_id} ({category}): {generated}/{target_samples}")
            
            else:
                errors += 1
                print(f"⚠️ Worker {worker_id}: Parse error")
        
        except Exception as e:
            errors += 1
            print(f"❌ Worker {worker_id}: Error: {e}")
            time.sleep(5)
    
    print(f"🏁 Worker {worker_id} ({account_name}/{api_type}) completed: {generated} samples, {errors} errors")

# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def main():
    """Main orchestration logic"""
    
    print("=" * 70)
    print("🚢 ORCHESTRATED MARITIME DATA GENERATOR")
    print("=" * 70)
    print()
    
    # Load configuration
    accounts = load_accounts()
    print(f"✓ Loaded {len(accounts)} API accounts")
    
    # Load progress
    progress = load_progress()
    total_done = sum(progress.values())
    print(f"✓ Current progress: {total_done:,} / {TOTAL_TARGET:,} samples")
    print()
    
    # Show progress by category
    print("📊 Progress by category:")
    for category, (target, _) in sorted(GENERATION_PLAN.items()):
        done = progress.get(category, 0)
        pct = (done / target * 100) if target > 0 else 0
        print(f"   {category:40s}: {done:6,} / {target:6,} ({pct:5.1f}%)")
    print()
    
    # Assign accounts to categories
    assignments = assign_accounts_to_categories(accounts, progress)
    
    if not assignments:
        print("✅ All generation complete!")
        return
    
    print("🎯 Account assignments:")
    for category, account_list in assignments.items():
        target, _ = GENERATION_PLAN[category]
        done = progress.get(category, 0)
        remaining = target - done
        per_account = remaining // len(account_list)
        print(f"   {category}: {len(account_list)} accounts, {per_account:,} samples each")
    print()
    
    # Start workers
    print("🚀 Starting generation workers...")
    threads = []
    progress_lock = threading.Lock()
    output_lock = threading.Lock()
    shared_progress = dict(progress)  # Shared progress dict
    
    worker_id = 0
    for category, account_list in assignments.items():
        target, _ = GENERATION_PLAN[category]
        done = progress.get(category, 0)
        remaining = target - done
        
        if remaining <= 0:
            continue
        
        per_account = remaining // len(account_list)
        
        for account_info in account_list:
            worker_id += 1
            t = threading.Thread(
                target=worker_thread,
                args=(worker_id, category, account_info, per_account, progress_lock, shared_progress, output_lock)
            )
            t.start()
            threads.append(t)
            time.sleep(0.5)  # Stagger starts
    
    print(f"✓ Started {len(threads)} workers")
    print()
    
    # Monitor progress
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(30)
            
            # Save progress
            with progress_lock:
                save_progress(shared_progress)
            
            # Show stats
            total_now = sum(shared_progress.values())
            print(f"⏱️  Progress: {total_now:,} / {TOTAL_TARGET:,} ({total_now/TOTAL_TARGET*100:.1f}%)")
    
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted! Saving progress...")
        with progress_lock:
            save_progress(shared_progress)
        print("✓ Progress saved. You can resume later.")
        return
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Final save
    with progress_lock:
        save_progress(shared_progress)
    
    final_total = sum(shared_progress.values())
    print()
    print("=" * 70)
    print(f"✅ GENERATION COMPLETE: {final_total:,} / {TOTAL_TARGET:,} samples")
    print("=" * 70)

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main()
