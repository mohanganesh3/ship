#!/usr/bin/env python3
"""
FINAL ORCHESTRATED GENERATOR - NO DUPLICATES, MAXIMUM SPEED
Uses category-based distribution to prevent overlap
"""

import json
import os
import sys
import time
import threading
import random
from datetime import datetime
from pathlib import Path
import hashlib

# Import scenarios
sys.path.append(os.path.dirname(__file__))
from real_maritime_scenarios import (
    REAL_MARITIME_SCENARIOS,
    MARITIME_CALCULATIONS,
    STANDARD_PROCEDURES
)

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = Path("/home/mohanganesh/ship/training/real_maritime_data")
OUTPUT_FILE = OUTPUT_DIR / "maritime_real_scenarios.jsonl"
PROGRESS_FILE = OUTPUT_DIR / "category_progress.json"
LOCK_FILE = OUTPUT_DIR / ".generation.lock"

# Target distribution (500K total)
CATEGORY_TARGETS = {
    "navigation_real_scenarios": 100000,
    "engineering_real_scenarios": 60000,
    "safety_real_scenarios": 60000,
    "cargo_real_scenarios": 40000,
    "regulations_real_scenarios": 20000,
    "stability_real_scenarios": 10000,
    "communications_real_scenarios": 10000,
    "navigation_calculations": 40000,
    "stability_calculations": 30000,
    "cargo_calculations": 20000,
    "engineering_calculations": 10000,
    "bridge_procedures": 30000,
    "engine_procedures": 25000,
    "safety_procedures": 25000,
    "cargo_procedures": 20000,
}

# API endpoints
CEREBRAS_ENDPOINT = "https://api.cerebras.ai/v1/chat/completions"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GOOGLE_ENDPOINT_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

# Rate limiting (seconds between requests)
GOOGLE_DELAY = 6.0  # 10 RPM = 1 req per 6 seconds (free tier limit: 15 RPM)
CEREBRAS_DELAY = 1.0  # 60 RPM = 1 req per second
GROQ_DELAY = 2.0  # 30 RPM = 1 req per 2 seconds (free tier limit)

# ============================================================================
# PROGRESS TRACKING
# ============================================================================

progress_lock = threading.Lock()
file_lock = threading.Lock()

def load_progress():
    """Load category progress"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {cat: 0 for cat in CATEGORY_TARGETS.keys()}

def save_progress(progress):
    """Save progress atomically"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

# ============================================================================
# PROMPT GENERATION
# ============================================================================

def get_prompt_for_category(category, seed=None):
    """Generate unique prompt for category"""
    
    if seed is not None:
        random.seed(seed)
    
    if category.endswith('_real_scenarios'):
        # Real scenario
        scenarios = REAL_MARITIME_SCENARIOS.get(category, [])
        if not scenarios:
            return None, None
        
        scenario_data = random.choice(scenarios)
        scenario = scenario_data["scenario"]
        context = scenario_data["context"]
        must_include = scenario_data["must_include"]
        safety_critical = scenario_data.get("safety_critical", False)
        basis = scenario_data.get("real_incident_basis", "industry standard practice")
        
        prompt = f"""You are a senior maritime officer with 20+ years experience.

REAL SCENARIO (Based on: {basis}):
Type: {category}
Title: {scenario}
Situation: {context}

REQUIREMENTS - Every answer MUST include:
{chr(10).join(f'- {item}' for item in must_include)}

{"⚠️ SAFETY CRITICAL: Emphasize safety procedures." if safety_critical else ""}

Generate a detailed question and comprehensive answer.

ANSWER MUST:
1. Reference specific regulations (SOLAS/MARPOL/STCW/COLREGS)
2. List step-by-step procedures
3. Emphasize safety considerations
4. Include required communications
5. Mention documentation
6. Be 300-500 words with technical accuracy

Format EXACTLY as:
QUESTION: [question]
ANSWER: [answer]"""
        
        return prompt, {"scenario": scenario, "basis": basis, "safety_critical": safety_critical}
    
    elif '_calculations' in category:
        # Calculation - MARITIME_CALCULATIONS is a dict with lists
        all_topics = []
        for cat_topics in MARITIME_CALCULATIONS.values():
            all_topics.extend(cat_topics)
        
        if not all_topics:
            return None, None
        
        topic = random.choice(all_topics)
        
        prompt = f"""You are a maritime academy instructor.

CALCULATION: {topic}
CATEGORY: {category}

Create a realistic maritime calculation problem with:
1. Clear problem statement with all values and units
2. Step-by-step solution showing ALL working
3. Formulas with explanations
4. Final answer verified

Requirements:
- Realistic maritime values
- Complete working (200-400 words)
- Units throughout

Format EXACTLY as:
QUESTION: [problem]
ANSWER: [solution]"""
        
        return prompt, {"topic": topic}
    
    elif '_procedures' in category:
        # Procedure - STANDARD_PROCEDURES is a dict with lists
        all_procedures = []
        for cat_procs in STANDARD_PROCEDURES.values():
            all_procedures.extend(cat_procs)
        
        if not all_procedures:
            return None, None
        
        procedure = random.choice(all_procedures)
        
        prompt = f"""You are writing ship SOPs.

PROCEDURE: {procedure}
CATEGORY: {category}

Create detailed SOP:
1. When to use (context)
2. Step-by-step instructions
3. Safety precautions
4. Required equipment/personnel
5. Regulatory basis
6. Common mistakes
7. Documentation

Requirements: 200-400 words, practical, safety-focused

Format EXACTLY as:
QUESTION: When and how to perform {procedure}?
ANSWER: [SOP]"""
        
        return prompt, {"procedure": procedure}
    
    return None, None

# ============================================================================
# API CALLER
# ============================================================================

def call_api(api_type, api_key, prompt):
    """Call appropriate API"""
    import requests
    
    try:
        if api_type == 'google':
            url = GOOGLE_ENDPOINT_TEMPLATE.format(api_key=api_key)
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}
            }
            response = requests.post(url, json=data, headers=headers, timeout=60)
            if response.status_code == 200:
                return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return None
        
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
                return response.json()["choices"][0]["message"]["content"].strip()
            return None
        
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
                return response.json()["choices"][0]["message"]["content"].strip()
            return None
    
    except Exception as e:
        print(f"API error ({api_type}): {e}")
        return None

# ============================================================================
# WORKER THREAD
# ============================================================================

def worker(worker_id, category, api_type, api_key, target, shared_progress):
    """Worker thread generating samples for assigned category"""
    
    print(f"🚀 Worker {worker_id} ({api_type}): {category} → target {target:,}")
    
    generated = 0
    errors = 0
    
    # Determine delay based on API type
    if api_type == 'google':
        delay = GOOGLE_DELAY
    elif api_type == 'cerebras':
        delay = CEREBRAS_DELAY
    else:  # groq
        delay = GROQ_DELAY
    
    while generated < target:
        # Check if we should stop (other workers completed this category)
        with progress_lock:
            current_progress = shared_progress.get(category, 0)
            category_target = CATEGORY_TARGETS.get(category, 0)
            if current_progress >= category_target:
                print(f"✓ Worker {worker_id}: Category {category} complete!")
                break
        
        # Generate unique seed for this sample
        seed = int(time.time() * 1000000) + worker_id + generated
        
        # Get prompt
        prompt, metadata = get_prompt_for_category(category, seed=seed)
        if prompt is None:
            time.sleep(1)
            continue
        
        # Call API
        text = call_api(api_type, api_key, prompt)
        
        if text and "QUESTION:" in text and "ANSWER:" in text:
            try:
                # Parse response
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
                    "account": f"worker_{worker_id}",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata
                }
                
                # Write to file (thread-safe)
                with file_lock:
                    with open(OUTPUT_FILE, 'a') as f:
                        f.write(json.dumps(sample) + '\n')
                
                # Update progress (thread-safe)
                with progress_lock:
                    shared_progress[category] = shared_progress.get(category, 0) + 1
                
                generated += 1
                
                if generated % 50 == 0:
                    print(f"  Worker {worker_id}: {generated}/{target} ({category})")
            
            except Exception as e:
                errors += 1
                print(f"  ❌ Worker {worker_id}: Parse error: {e}")
        else:
            errors += 1
        
        time.sleep(delay)
    
    print(f"🏁 Worker {worker_id} finished: {generated} samples, {errors} errors")

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("🚢 FINAL ORCHESTRATED MARITIME DATA GENERATOR")
    print("=" * 70)
    print()
    
    # Load accounts
    with open('accounts.json', 'r') as f:
        accounts_data = json.load(f)
    accounts = accounts_data['accounts']
    
    # Count APIs
    google_count = sum(1 for a in accounts if a.get('google_api_key'))
    cerebras_count = sum(1 for a in accounts if a.get('cerebras_api_key'))
    groq_count = sum(1 for a in accounts if a.get('groq_api_key'))
    
    print(f"✓ Accounts: {len(accounts)}")
    print(f"  Google: {google_count}, Cerebras: {cerebras_count}, Groq: {groq_count}")
    print()
    
    # Load progress
    progress = load_progress()
    total_done = sum(progress.values())
    total_target = sum(CATEGORY_TARGETS.values())
    
    print(f"📊 Progress: {total_done:,} / {total_target:,} ({total_done/total_target*100:.1f}%)")
    print()
    
    # Show top 5 categories by remaining work
    remaining = {cat: CATEGORY_TARGETS[cat] - progress.get(cat, 0) for cat in CATEGORY_TARGETS}
    top_categories = sorted(remaining.items(), key=lambda x: x[1], reverse=True)[:5]
    print("Top 5 categories by remaining work:")
    for cat, rem in top_categories:
        print(f"  {cat:40s}: {rem:,} remaining")
    print()
    
    # Assign workers to categories
    # Strategy: Assign to categories with most remaining work
    assignments = []
    worker_id = 0
    
    for account in accounts:
        # Try Google first (most reliable)
        if account.get('google_api_key'):
            # Find category with most remaining work
            cat = max(remaining.items(), key=lambda x: x[1])[0]
            target = remaining[cat] // max(1, google_count)  # Divide among Google accounts
            if target > 0:
                assignments.append((worker_id, cat, 'google', account['google_api_key'], target))
                remaining[cat] -= target
                worker_id += 1
        
        # Then Cerebras
        if account.get('cerebras_api_key'):
            cat = max(remaining.items(), key=lambda x: x[1])[0]
            target = min(5000, remaining[cat] // max(1, cerebras_count))  # Limited by tokens
            if target > 0:
                assignments.append((worker_id, cat, 'cerebras', account['cerebras_api_key'], target))
                remaining[cat] -= target
                worker_id += 1
        
        # Then Groq
        if account.get('groq_api_key'):
            cat = max(remaining.items(), key=lambda x: x[1])[0]
            target = min(10000, remaining[cat] // max(1, groq_count))  # Limited by credits
            if target > 0:
                assignments.append((worker_id, cat, 'groq', account['groq_api_key'], target))
                remaining[cat] -= target
                worker_id += 1
    
    print(f"🎯 Starting {len(assignments)} workers...")
    for wid, cat, api, _, target in assignments:
        print(f"  Worker {wid:2d} ({api:8s}): {cat:40s} → {target:,}")
    print()
    
    # Start workers
    threads = []
    shared_progress = dict(progress)
    
    for wid, cat, api, key, target in assignments:
        t = threading.Thread(target=worker, args=(wid, cat, api, key, target, shared_progress))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.3)
    
    print("✅ All workers started!")
    print()
    
    # Monitor
    try:
        last_total = total_done
        start_time = time.time()
        
        while any(t.is_alive() for t in threads):
            time.sleep(30)
            
            # Save progress
            with progress_lock:
                save_progress(shared_progress)
            
            # Show stats
            current_total = sum(shared_progress.values())
            elapsed = time.time() - start_time
            rate = (current_total - last_total) / (elapsed / 3600) if elapsed > 0 else 0
            
            print(f"⏱️  Total: {current_total:,}/{total_target:,} | Rate: {rate:.0f}/hr | {len([t for t in threads if t.is_alive()])} workers active")
            
            last_total = current_total
            start_time = time.time()
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted! Saving progress...")
        with progress_lock:
            save_progress(shared_progress)
        print("✓ Progress saved")
        return
    
    # Wait for completion
    for t in threads:
        t.join()
    
    # Final save
    with progress_lock:
        save_progress(shared_progress)
    
    final_total = sum(shared_progress.values())
    print()
    print("=" * 70)
    print(f"✅ COMPLETE: {final_total:,} / {total_target:,}")
    print("=" * 70)

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main()
