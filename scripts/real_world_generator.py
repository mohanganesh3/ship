#!/usr/bin/env python3
"""
Real-World Maritime Data Generator
Based on actual operational frequency and PSC detention data
"""

import json
import os
import time
import random
from pathlib import Path
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# NEW API KEYS (provided by user)
GOOGLE_API_KEY = "GOOGLE_API_KEY_PLACEHOLDER"
CEREBRAS_API_KEY = "CEREBRAS_API_KEY_PLACEHOLDER"
GROQ_API_KEY = "GROQ_API_KEY_PLACEHOLDER"

# Output configuration
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/real_world_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "maritime_real_world.jsonl"
STATS_FILE = OUTPUT_DIR / "generation_stats.json"
PROGRESS_FILE = OUTPUT_DIR / "progress.json"

# Real-world topic distribution
TOPICS = {
    # DAILY OPERATIONS (60%)
    "watchkeeping_navigation": {
        "weight": 16,
        "prompt": "Generate a practical question about navigation watch procedures, equipment checks, or routine operations that a deck officer encounters every watch. Focus on ECDIS alarms, position logging, traffic monitoring, VHF communications, weather logging, or course/speed adjustments."
    },
    "watchkeeping_engine": {
        "weight": 16,
        "prompt": "Generate a practical question about engine room watch procedures, machinery rounds, or alarm responses that an engineer encounters every watch. Focus on parameter logging, fuel operations, purifier operations, bilge management, OWS operations, or equipment troubleshooting."
    },
    "cargo_monitoring": {
        "weight": 8,
        "prompt": "Generate a practical question about cargo monitoring during a voyage - tank pressures, hold temperatures, reefer container monitoring, or ventilation adjustments. Focus on routine checks and parameter logging."
    },
    "deck_operations": {
        "weight": 8,
        "prompt": "Generate a practical question about deck operations - mooring rounds, pilot ladder rigging, anchor watch, safety rounds, or weather deck checks. Focus on daily routine operations by deck crew."
    },
    "documentation": {
        "weight": 6,
        "prompt": "Generate a practical question about ship documentation - logbook entries, oil record book, garbage record book, STCW rest hours recording, or PMS entries. Focus on what officers need to document daily."
    },
    "equipment_checks": {
        "weight": 6,
        "prompt": "Generate a practical question about routine equipment checks - fire detection systems, LSA inspection, GMDSS tests, steering gear tests, or emergency equipment verification."
    },
    
    # WEEKLY OPERATIONS (25%)
    "planned_maintenance": {
        "weight": 10,
        "prompt": "Generate a practical question about planned maintenance execution, spare parts management, tool calibration, preservation work, or system testing. Focus on PMS tasks that happen weekly."
    },
    "drills_training": {
        "weight": 6,
        "prompt": "Generate a practical question about ship drills and training - fire drills, abandon ship drills, MOB drills, or emergency steering drills. Focus on procedure execution and crew coordination."
    },
    "cargo_operations": {
        "weight": 4,
        "prompt": "Generate a practical question about cargo loading/discharge operations, tank cleaning, or hold preparation. Focus on operational procedures and safety."
    },
    "port_operations": {
        "weight": 3,
        "prompt": "Generate a practical question about port operations - berthing procedures, bunkering operations, crew changes, or shore inspections. Focus on practical execution."
    },
    "administrative": {
        "weight": 2,
        "prompt": "Generate a practical question about administrative tasks - safety meetings, crew briefings, company reports, or certificate verification."
    },
    
    # PSC DETENTION CAUSES (15%)
    "firefighting_equipment": {
        "weight": 3,
        "prompt": "Generate a practical question about firefighting equipment deficiencies that cause PSC detentions - expired fire extinguishers, fire pumps that won't start, fire doors that don't close properly, or SCBA cylinder testing."
    },
    "navigation_lights_signals": {
        "weight": 2,
        "prompt": "Generate a practical question about navigation lights, shapes, or sound signals - lights not working, whistle failures, wrong day shapes, or insufficient light range."
    },
    "ism_code": {
        "weight": 2,
        "prompt": "Generate a practical question about ISM Code compliance issues - safety meetings not recorded, drills not conducted, SMS not followed, or non-conformities not closed."
    },
    "fire_doors": {
        "weight": 2,
        "prompt": "Generate a practical question about fire door and opening deficiencies - doors wedged open, self-closing mechanisms broken, penetrations not sealed, or dampers that don't close."
    },
    "lifesaving_equipment": {
        "weight": 3,
        "prompt": "Generate a practical question about lifesaving equipment deficiencies - rescue boats that won't lower, lifeboat engines that won't start, expired equipment, or failed tests."
    },
    "aux_machinery": {
        "weight": 2,
        "prompt": "Generate a practical question about auxiliary machinery issues - emergency generator failures, auto-start problems, fuel system issues, or load capacity problems."
    },
    "main_machinery": {
        "weight": 1,
        "prompt": "Generate a practical question about main engine problems - cannot maintain sea speed, excessive smoke, high temperatures, or lubrication oil issues."
    },
    
    # MONTHLY (10%)
    "major_maintenance": {
        "weight": 4,
        "prompt": "Generate a practical question about major maintenance, overhauls, or dry dock planning - major component overhauls, extensive repairs, or dry dock preparation."
    },
    "audits_inspections": {
        "weight": 3,
        "prompt": "Generate a practical question about PSC inspection preparation, vetting inspections, or internal audits - checklist preparation, document verification, or deficiency handling."
    },
    "planning_admin": {
        "weight": 3,
        "prompt": "Generate a practical question about voyage planning, budget management, or performance reporting - passage planning, cost control, or operational reporting."
    },
    
    # RARE/EMERGENCY (5%)
    "emergency_response": {
        "weight": 3,
        "prompt": "Generate a practical question about emergency response - collision, fire, flooding, man overboard, or medical emergencies. Focus on immediate actions and decision-making."
    },
    "special_operations": {
        "weight": 2,
        "prompt": "Generate a practical question about special operations - celestial navigation backup, damage control, salvage operations, SAR coordination, or piracy response."
    },
}

# API endpoints
GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def generate_with_google(prompt, category):
    """Generate Q&A with Google Gemini"""
    try:
        response = requests.post(
            f"{GOOGLE_URL}?key={GOOGLE_API_KEY}",
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.9,
                    "maxOutputTokens": 2048,
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return parse_qa(text, category, "google")
        else:
            # Log rate limit or other errors
            if response.status_code == 429:
                time.sleep(2)  # Rate limit backoff
        return None
    except Exception as e:
        # Don't print errors, just fail silently
        return None

def generate_with_cerebras(prompt, category):
    """Generate Q&A with Cerebras"""
    try:
        response = requests.post(
            CEREBRAS_URL,
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}"},
            json={
                "model": "llama3.1-8b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 2048,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0]["message"]["content"]
                return parse_qa(text, category, "cerebras")
        elif response.status_code == 429:
            time.sleep(2)
        return None
    except Exception as e:
        return None

def generate_with_groq(prompt, category):
    """Generate Q&A with Groq"""
    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 2048,
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                text = data["choices"][0]["message"]["content"]
                return parse_qa(text, category, "groq")
        elif response.status_code == 429:
            time.sleep(2)
        return None
    except Exception as e:
        return None

def parse_qa(text, category, provider):
    """Parse Q&A from generated text"""
    try:
        # Try multiple parsing strategies
        question = ""
        answer = ""
        
        # Strategy 1: Look for Q: and A: patterns
        lines = text.strip().split('\n')
        in_answer = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('Q:') or line.startswith('Question:'):
                question = line.split(':', 1)[1].strip()
                in_answer = False
            elif line.startswith('A:') or line.startswith('Answer:'):
                answer = line.split(':', 1)[1].strip()
                in_answer = True
            elif in_answer and line:
                answer += " " + line
        
        # Strategy 2: If no Q/A found, split on first paragraph break
        if not question or not answer:
            parts = text.strip().split('\n\n', 1)
            if len(parts) == 2:
                question = parts[0].strip()
                answer = parts[1].strip()
        
        # Strategy 3: Look for markdown-style format
        if not question or not answer:
            if '**Question:**' in text and '**Answer:**' in text:
                parts = text.split('**Question:**', 1)[1].split('**Answer:**')
                if len(parts) == 2:
                    question = parts[0].strip()
                    answer = parts[1].strip()
        
        # Strategy 4: Just use the whole text as one Q&A if nothing else worked
        if not question or not answer:
            # Split roughly in half
            sentences = text.strip().split('. ')
            if len(sentences) >= 2:
                mid = len(sentences) // 3
                question = '. '.join(sentences[:mid]) + '.'
                answer = '. '.join(sentences[mid:])
        
        # Clean up
        question = question.replace('**', '').replace('##', '').strip()
        answer = answer.replace('**', '').replace('##', '').strip()
        
        if question and answer and len(question) > 20 and len(answer) > 50:
            return {
                "question": question,
                "answer": answer,
                "category": category,
                "provider": provider,
                "timestamp": datetime.now().isoformat()
            }
        return None
    except Exception as e:
        return None

def generate_sample(category, topic_data):
    """Generate one sample using round-robin API selection"""
    providers = [generate_with_google, generate_with_cerebras, generate_with_groq]
    provider_func = random.choice(providers)
    
    full_prompt = f"""{topic_data['prompt']}

Format your response as:
Q: [Your practical, specific question]
A: [Detailed answer with procedures, steps, and safety considerations]

Make it realistic and based on actual shipboard operations."""
    
    return provider_func(full_prompt, category)

def main():
    print("🚢 REAL-WORLD MARITIME DATA GENERATOR")
    print("=" * 60)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Target: 500,000 samples")
    print("=" * 60)
    
    # Calculate total weight
    total_weight = sum(t["weight"] for t in TOPICS.values())
    
    # Start generation
    generated = 0
    successful = 0
    failed = 0
    by_category = {cat: 0 for cat in TOPICS.keys()}
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        while generated < 500000:
            # Select category based on weights
            rand = random.randint(1, total_weight)
            cumsum = 0
            selected_category = None
            
            for category, data in TOPICS.items():
                cumsum += data["weight"]
                if rand <= cumsum:
                    selected_category = category
                    break
            
            # Generate sample
            future = executor.submit(generate_sample, selected_category, TOPICS[selected_category])
            result = future.result(timeout=60)
            
            if result:
                # Write to file
                with open(OUTPUT_FILE, 'a') as f:
                    f.write(json.dumps(result) + '\n')
                successful += 1
                by_category[selected_category] += 1
            else:
                failed += 1
            
            generated += 1
            
            # Progress update every 100 samples
            if generated % 100 == 0:
                elapsed = time.time() - start_time
                rate = generated / elapsed
                eta_seconds = (500000 - generated) / rate if rate > 0 else 0
                eta_hours = eta_seconds / 3600
                
                print(f"\r[{generated:,}/500,000] Success: {successful:,} | Failed: {failed} | Rate: {rate:.1f}/sec | ETA: {eta_hours:.1f}h", end='', flush=True)
                
                # Save stats
                stats = {
                    "generated": generated,
                    "successful": successful,
                    "failed": failed,
                    "by_category": by_category,
                    "rate_per_sec": rate,
                    "eta_hours": eta_hours
                }
                with open(STATS_FILE, 'w') as f:
                    json.dump(stats, f, indent=2)
    
    print(f"\n\n✅ Generation complete!")
    print(f"Total generated: {generated:,}")
    print(f"Successful: {successful:,}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    main()
