#!/usr/bin/env python3
"""
Comprehensive Maritime Data Generation System
==============================================
Generate 500K+ high-quality Q&A pairs covering ALL maritime topics
Using: Google Gemini, Cerebras, and Groq APIs

Strategy:
1. Comprehensive topic coverage (100+ maritime categories)
2. Multi-provider rotation for maximum throughput
3. Quality validation and filtering
4. Progress tracking and resumability
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

# API Configuration
GOOGLE_API_KEY = "GOOGLE_API_KEY_PLACEHOLDER"
CEREBRAS_API_KEY = "CEREBRAS_API_KEY_PLACEHOLDER"
GROQ_API_KEY = "GROQ_API_KEY_PLACEHOLDER"

# Output paths
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/comprehensive_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROGRESS_FILE = OUTPUT_DIR / "generation_progress.json"
OUTPUT_FILE = OUTPUT_DIR / "maritime_qa_comprehensive.jsonl"
STATS_FILE = OUTPUT_DIR / "generation_stats.json"

# Generation targets
TARGET_SAMPLES = 500000
BATCH_SIZE = 100
MAX_WORKERS = 10

@dataclass
class GenerationStats:
    total_generated: int = 0
    successful: int = 0
    failed: int = 0
    google_count: int = 0
    cerebras_count: int = 0
    groq_count: int = 0
    by_category: Dict[str, int] = None
    start_time: str = ""
    last_update: str = ""
    
    def __post_init__(self):
        if self.by_category is None:
            self.by_category = {}

# Comprehensive Maritime Topic Categories
MARITIME_TOPICS = {
    # Navigation & Bridge Operations (8 categories)
    "celestial_navigation": {
        "weight": 10,
        "description": "Star sights, sun lines, planet observations, time zones, position fixing",
        "subcategories": ["star_identification", "sextant_usage", "sight_reduction", "time_calculations"]
    },
    "electronic_navigation": {
        "weight": 15,
        "description": "GPS, ECDIS, radar, AIS, chart corrections, voyage planning",
        "subcategories": ["ecdis_operations", "radar_interpretation", "ais_monitoring", "chart_updates"]
    },
    "collision_avoidance": {
        "weight": 20,
        "description": "COLREGS, rules of the road, traffic separation, special circumstances",
        "subcategories": ["rule_interpretations", "crossing_situations", "narrow_channels", "restricted_visibility"]
    },
    "ship_handling": {
        "weight": 15,
        "description": "Maneuvering, berthing, anchoring, pilot operations, towing",
        "subcategories": ["berthing_procedures", "anchoring_techniques", "pilot_transfer", "towing_operations"]
    },
    "meteorology": {
        "weight": 8,
        "description": "Weather routing, tropical cyclones, ice navigation, weather interpretation",
        "subcategories": ["weather_forecasting", "cyclone_avoidance", "ice_navigation", "heavy_weather"]
    },
    "passage_planning": {
        "weight": 10,
        "description": "Route selection, tide calculations, distance estimation, ETA calculations",
        "subcategories": ["route_optimization", "tidal_calculations", "fuel_planning", "port_selection"]
    },
    "watchkeeping": {
        "weight": 12,
        "description": "Bridge procedures, lookout duties, handover procedures, night orders",
        "subcategories": ["watch_procedures", "lookout_duties", "bridge_resource_management", "handover"]
    },
    "pilotage": {
        "weight": 8,
        "description": "Pilot embarkation, pilot ladder, master-pilot exchange, local regulations",
        "subcategories": ["pilot_boarding", "mpe_procedures", "pilot_ladder_safety", "compulsory_pilotage"]
    },
    
    # Engineering & Machinery (12 categories)
    "main_engine": {
        "weight": 18,
        "description": "Diesel engines, maintenance, troubleshooting, performance monitoring",
        "subcategories": ["engine_operation", "fuel_injection", "turbochargers", "cooling_systems"]
    },
    "auxiliary_engines": {
        "weight": 10,
        "description": "Generator sets, emergency generators, harbor generators",
        "subcategories": ["generator_operation", "load_sharing", "emergency_power", "maintenance"]
    },
    "boilers": {
        "weight": 8,
        "description": "Steam generation, water treatment, combustion control, safety",
        "subcategories": ["boiler_operation", "water_treatment", "combustion_efficiency", "safety_valves"]
    },
    "pumps_systems": {
        "weight": 12,
        "description": "Pumping systems, ballast, bilge, cargo, fire fighting",
        "subcategories": ["pump_types", "ballast_operations", "bilge_systems", "fire_pumps"]
    },
    "electrical_systems": {
        "weight": 15,
        "description": "Power distribution, switchboards, motors, generators, automation",
        "subcategories": ["power_distribution", "switchboard_operations", "motor_control", "emergency_power"]
    },
    "refrigeration_hvac": {
        "weight": 8,
        "description": "Refrigerated cargo, provisions, HVAC, air conditioning",
        "subcategories": ["refrigeration_cycles", "cargo_cooling", "ac_systems", "troubleshooting"]
    },
    "propulsion_steering": {
        "weight": 12,
        "description": "Propellers, shafting, stern tubes, steering gear, thrusters",
        "subcategories": ["propeller_maintenance", "shaft_alignment", "steering_gear", "bow_thrusters"]
    },
    "fuel_systems": {
        "weight": 10,
        "description": "Fuel handling, purification, storage, bunkering, quality",
        "subcategories": ["fuel_purification", "bunkering_procedures", "fuel_testing", "contamination"]
    },
    "lub_oil_systems": {
        "weight": 10,
        "description": "Lubrication, oil analysis, purification, storage",
        "subcategories": ["oil_analysis", "purification_systems", "lub_oil_handling", "contamination_control"]
    },
    "hydraulic_systems": {
        "weight": 8,
        "description": "Hydraulic pumps, valves, steering, deck machinery",
        "subcategories": ["hydraulic_principles", "maintenance", "troubleshooting", "safety"]
    },
    "automation_control": {
        "weight": 12,
        "description": "PLC systems, UMS, monitoring, alarms, control loops",
        "subcategories": ["plc_programming", "ums_operations", "alarm_management", "control_systems"]
    },
    "maintenance_planning": {
        "weight": 10,
        "description": "PMS, condition monitoring, dry docking, surveys",
        "subcategories": ["planned_maintenance", "condition_monitoring", "dry_dock_planning", "class_surveys"]
    },
    
    # Safety & Emergency (10 categories)
    "fire_safety": {
        "weight": 18,
        "description": "Fire prevention, detection, fighting, drills, equipment",
        "subcategories": ["fire_prevention", "fire_detection", "firefighting_equipment", "fire_drills"]
    },
    "lifesaving_equipment": {
        "weight": 15,
        "description": "Lifeboats, life rafts, immersion suits, EPIRB, SART",
        "subcategories": ["lifeboat_operations", "life_raft_maintenance", "distress_signals", "abandon_ship"]
    },
    "enclosed_spaces": {
        "weight": 20,
        "description": "Entry procedures, gas testing, rescue, permits to work",
        "subcategories": ["gas_testing", "entry_permits", "rescue_procedures", "ventilation"]
    },
    "man_overboard": {
        "weight": 12,
        "description": "MOB procedures, recovery, prevention, equipment",
        "subcategories": ["mob_response", "recovery_methods", "prevention_measures", "mob_equipment"]
    },
    "medical_emergencies": {
        "weight": 12,
        "description": "First aid, MEDICO calls, medical evacuation, pharmacy",
        "subcategories": ["first_aid", "medical_advice", "medevac_procedures", "ship_pharmacy"]
    },
    "search_rescue": {
        "weight": 10,
        "description": "SAR coordination, IAMSAR, GMDSS, distress procedures",
        "subcategories": ["sar_coordination", "distress_signals", "rescue_operations", "gmdss_procedures"]
    },
    "ppe_safety_equipment": {
        "weight": 10,
        "description": "Personal protective equipment, safety gear, standards",
        "subcategories": ["ppe_selection", "safety_equipment", "maintenance", "standards"]
    },
    "emergency_drills": {
        "weight": 12,
        "description": "Fire drills, abandon ship, MOB, emergency steering",
        "subcategories": ["drill_requirements", "drill_conduct", "evaluation", "record_keeping"]
    },
    "risk_assessment": {
        "weight": 10,
        "description": "Job safety analysis, risk matrices, permit to work",
        "subcategories": ["jsa_procedures", "risk_evaluation", "permit_systems", "safety_meetings"]
    },
    "emergency_procedures": {
        "weight": 15,
        "description": "Flooding, grounding, collision, abandonment, pollution",
        "subcategories": ["flooding_control", "grounding_response", "collision_procedures", "damage_control"]
    },
    
    # Cargo Operations (8 categories)
    "cargo_handling": {
        "weight": 15,
        "description": "Loading plans, stability, securing, ventilation",
        "subcategories": ["load_planning", "cargo_securing", "ventilation", "damage_prevention"]
    },
    "container_operations": {
        "weight": 12,
        "description": "Container securing, stowage, dangerous goods, reefers",
        "subcategories": ["lashing_systems", "stowage_planning", "dg_containers", "reefer_monitoring"]
    },
    "bulk_cargo": {
        "weight": 10,
        "description": "Grain, ore, coal, loading, discharge, stability",
        "subcategories": ["bulk_loading", "cargo_care", "hold_preparation", "discharge_operations"]
    },
    "liquid_cargo": {
        "weight": 12,
        "description": "Oil tankers, chemical tankers, gas carriers, operations",
        "subcategories": ["tank_cleaning", "cargo_transfer", "gas_freeing", "inerting"]
    },
    "dangerous_goods": {
        "weight": 18,
        "description": "IMDG Code, segregation, documentation, emergencies",
        "subcategories": ["dg_classification", "segregation_requirements", "dg_documentation", "dg_emergencies"]
    },
    "refrigerated_cargo": {
        "weight": 8,
        "description": "Reefer containers, temperature monitoring, ventilation",
        "subcategories": ["temperature_control", "monitoring_systems", "cargo_care", "troubleshooting"]
    },
    "ro_ro_operations": {
        "weight": 8,
        "description": "Vehicle carriers, ramps, securing, stability",
        "subcategories": ["vehicle_stowage", "ramp_operations", "securing_procedures", "stability_considerations"]
    },
    "cargo_documentation": {
        "weight": 10,
        "description": "Bills of lading, cargo manifests, customs, certificates",
        "subcategories": ["bl_types", "manifest_preparation", "customs_documentation", "cargo_certificates"]
    },
    
    # Regulations & Compliance (10 categories)
    "marpol": {
        "weight": 20,
        "description": "Pollution prevention, annexes I-VI, oil records, garbage",
        "subcategories": ["oil_pollution", "garbage_management", "sewage_regulations", "air_emissions"]
    },
    "solas": {
        "weight": 18,
        "description": "Safety of life at sea, chapters, amendments, certificates",
        "subcategories": ["construction_standards", "lifesaving_requirements", "fire_safety_requirements", "radio_requirements"]
    },
    "stcw": {
        "weight": 15,
        "description": "Training, certification, watchkeeping, rest hours",
        "subcategories": ["certification_requirements", "competency_standards", "rest_hours", "training_requirements"]
    },
    "ism_code": {
        "weight": 15,
        "description": "Safety management, SMS, audits, non-conformities",
        "subcategories": ["sms_requirements", "internal_audits", "doc_smc", "non_conformity_management"]
    },
    "isps_code": {
        "weight": 12,
        "description": "Ship security, SSO, SSP, security levels, drills",
        "subcategories": ["security_levels", "security_assessments", "ssp_requirements", "security_drills"]
    },
    "mlc": {
        "weight": 10,
        "description": "Maritime labour convention, crew welfare, working conditions",
        "subcategories": ["accommodation_standards", "working_hours", "repatriation", "crew_welfare"]
    },
    "port_state_control": {
        "weight": 15,
        "description": "Inspections, deficiencies, detention, preparation",
        "subcategories": ["psc_preparation", "inspection_procedures", "deficiency_management", "detention_prevention"]
    },
    "flag_state_requirements": {
        "weight": 10,
        "description": "Flag administration, registration, surveys, certificates",
        "subcategories": ["registration_requirements", "flag_surveys", "statutory_certificates", "flag_compliance"]
    },
    "environmental_compliance": {
        "weight": 12,
        "description": "Emissions, ballast water, antifouling, recycling",
        "subcategories": ["emission_regulations", "bwm_convention", "antifouling_regulations", "ship_recycling"]
    },
    "piracy_security": {
        "weight": 10,
        "description": "BMP, citadel, security measures, high-risk areas",
        "subcategories": ["bmp_procedures", "citadel_operations", "security_equipment", "hra_transits"]
    },
    
    # Stability & Ship Construction (6 categories)
    "stability_calculations": {
        "weight": 18,
        "description": "GM, GZ curves, free surface, loading conditions",
        "subcategories": ["metacentric_height", "gz_curves", "free_surface_effect", "loading_conditions"]
    },
    "damage_stability": {
        "weight": 12,
        "description": "Flooding, watertight integrity, subdivision, calculations",
        "subcategories": ["damage_calculations", "watertight_doors", "subdivision_requirements", "flooding_scenarios"]
    },
    "ship_construction": {
        "weight": 10,
        "description": "Hull structure, bulkheads, tanks, materials, strength",
        "subcategories": ["hull_structure", "bulkhead_types", "material_properties", "structural_strength"]
    },
    "ballast_operations": {
        "weight": 12,
        "description": "Ballasting, deballasting, stress, stability, BWM",
        "subcategories": ["ballast_planning", "stress_monitoring", "bwm_operations", "ballast_exchange"]
    },
    "ship_terminology": {
        "weight": 8,
        "description": "Parts of ship, measurements, nautical terms",
        "subcategories": ["hull_parts", "deck_terminology", "measurements", "nautical_vocabulary"]
    },
    "tonnage_measurements": {
        "weight": 8,
        "description": "GRT, NRT, deadweight, displacement, calculations",
        "subcategories": ["tonnage_types", "measurement_rules", "calculations", "certificates"]
    },
    
    # Communications & Administration (6 categories)
    "gmdss": {
        "weight": 15,
        "description": "Distress alerting, radio equipment, procedures, DSC",
        "subcategories": ["distress_procedures", "radio_equipment", "dsc_operations", "radio_watches"]
    },
    "maritime_radio": {
        "weight": 10,
        "description": "VHF, MF/HF, INMARSAT, NAVTEX, procedures",
        "subcategories": ["vhf_procedures", "inmarsat_systems", "navtex_operations", "radio_regulations"]
    },
    "record_keeping": {
        "weight": 10,
        "description": "Logbooks, oil records, garbage, crew lists, reports",
        "subcategories": ["official_logbook", "oil_record_book", "garbage_record_book", "deck_logbook"]
    },
    "crew_management": {
        "weight": 10,
        "description": "Manning, watchkeeping, rest hours, crew changes",
        "subcategories": ["manning_requirements", "watchkeeping_arrangements", "rest_hour_compliance", "crew_changes"]
    },
    "company_procedures": {
        "weight": 8,
        "description": "Company policies, reporting, communication, SMS",
        "subcategories": ["reporting_requirements", "company_policies", "sms_procedures", "communication_protocols"]
    },
    "vessel_documentation": {
        "weight": 10,
        "description": "Certificates, surveys, class, statutory requirements",
        "subcategories": ["statutory_certificates", "class_documents", "survey_requirements", "certificate_validity"]
    },
    
    # Specialized Operations (8 categories)
    "heavy_weather": {
        "weight": 12,
        "description": "Storm tactics, damage prevention, preparations",
        "subcategories": ["heavy_weather_tactics", "securing_vessel", "cargo_securing", "damage_prevention"]
    },
    "anchoring_mooring": {
        "weight": 10,
        "description": "Anchor types, mooring arrangements, operations",
        "subcategories": ["anchoring_procedures", "mooring_operations", "anchor_equipment", "mooring_lines"]
    },
    "towing_salvage": {
        "weight": 8,
        "description": "Towing operations, salvage, emergency towing",
        "subcategories": ["towing_procedures", "towing_equipment", "emergency_towing", "salvage_operations"]
    },
    "ice_navigation": {
        "weight": 8,
        "description": "Ice operations, polar code, ice strengthening",
        "subcategories": ["ice_operations", "polar_code_requirements", "ice_strengthening", "icebreaker_assistance"]
    },
    "offshore_operations": {
        "weight": 8,
        "description": "DP operations, supply vessels, offshore transfers",
        "subcategories": ["dp_systems", "offshore_supply", "personnel_transfer", "cargo_operations"]
    },
    "canal_transit": {
        "weight": 8,
        "description": "Suez, Panama, special procedures, requirements",
        "subcategories": ["suez_transit", "panama_transit", "canal_preparations", "canal_procedures"]
    },
    "bunker_operations": {
        "weight": 10,
        "description": "Bunkering procedures, calculations, quality, safety",
        "subcategories": ["bunker_procedures", "quantity_calculations", "fuel_sampling", "bunker_safety"]
    },
    "ship_to_ship_transfer": {
        "weight": 8,
        "description": "STS operations, safety, procedures, equipment",
        "subcategories": ["sts_procedures", "sts_safety", "sts_equipment", "lightering_operations"]
    },
    
    # Professional Development (4 categories)
    "seamanship": {
        "weight": 12,
        "description": "Knots, ropes, rigging, deck operations, traditions",
        "subcategories": ["knots_splices", "rope_work", "deck_operations", "maritime_traditions"]
    },
    "navigation_calculations": {
        "weight": 15,
        "description": "Position fixing, course calculations, distance, speed",
        "subcategories": ["position_calculations", "course_conversions", "distance_speed", "tidal_calculations"]
    },
    "leadership_management": {
        "weight": 10,
        "description": "Bridge resource management, crew management, decision making",
        "subcategories": ["brm_principles", "team_management", "decision_making", "communication_skills"]
    },
    "maritime_law": {
        "weight": 10,
        "description": "Admiralty law, collisions, salvage, general average",
        "subcategories": ["collision_liability", "salvage_law", "general_average", "maritime_liens"]
    },
}

def calculate_category_distribution(total_samples: int) -> Dict[str, int]:
    """Calculate how many samples per category based on weights."""
    total_weight = sum(cat["weight"] for cat in MARITIME_TOPICS.values())
    distribution = {}
    
    for category, info in MARITIME_TOPICS.items():
        samples = int((info["weight"] / total_weight) * total_samples)
        distribution[category] = max(samples, 100)  # Minimum 100 per category
    
    return distribution

def load_progress() -> Dict:
    """Load generation progress."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {"completed_categories": {}, "total_generated": 0}

def save_progress(progress: Dict):
    """Save generation progress."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_stats() -> GenerationStats:
    """Load generation statistics."""
    if STATS_FILE.exists():
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            return GenerationStats(**data)
    return GenerationStats(
        start_time=datetime.now().isoformat(),
        by_category={}
    )

def save_stats(stats: GenerationStats):
    """Save generation statistics."""
    stats.last_update = datetime.now().isoformat()
    with open(STATS_FILE, 'w') as f:
        json.dump(asdict(stats), f, indent=2)

class APIProvider:
    """Base class for API providers."""
    
    def __init__(self, name: str, api_key: str, endpoint: str, model: str):
        self.name = name
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.request_count = 0
        self.error_count = 0
        self.lock = threading.Lock()
    
    def generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        """Generate response from API."""
        raise NotImplementedError

class GoogleGeminiProvider(APIProvider):
    """Google Gemini API provider."""
    
    def __init__(self):
        super().__init__(
            "google",
            GOOGLE_API_KEY,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            "gemini-2.5-flash"
        )
    
    def generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        try:
            with self.lock:
                self.request_count += 1
            
            url = f"{self.endpoint}?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.9,
                }
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            
            return None
            
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"Google API error: {e}")
            return None

class CerebrasProvider(APIProvider):
    """Cerebras API provider."""
    
    def __init__(self):
        super().__init__(
            "cerebras",
            CEREBRAS_API_KEY,
            "https://api.cerebras.ai/v1/chat/completions",
            "llama3.1-8b"
        )
    
    def generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        try:
            with self.lock:
                self.request_count += 1
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.9,
            }
            
            response = requests.post(self.endpoint, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0]["message"]["content"]
                return text.strip()
            
            return None
            
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"Cerebras API error: {e}")
            return None

class GroqProvider(APIProvider):
    """Groq API provider."""
    
    def __init__(self):
        super().__init__(
            "groq",
            GROQ_API_KEY,
            "https://api.groq.com/openai/v1/chat/completions",
            "llama-3.1-8b-instant"
        )
    
    def generate(self, prompt: str, max_tokens: int = 800) -> Optional[str]:
        try:
            with self.lock:
                self.request_count += 1
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.9,
            }
            
            response = requests.post(self.endpoint, json=data, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0]["message"]["content"]
                return text.strip()
            
            return None
            
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"Groq API error: {e}")
            return None

def create_generation_prompt(category: str, subcategory: str, description: str, sample_num: int) -> Tuple[str, str]:
    """Create a prompt for generating Q&A pairs."""
    
    question_types = [
        "practical_scenario", "troubleshooting", "procedure", 
        "regulation", "calculation", "safety_critical", 
        "best_practice", "emergency", "maintenance"
    ]
    
    question_type = random.choice(question_types)
    
    base_prompt = f"""You are an expert maritime professional creating training data for a life-safety AI system for ship officers.

Category: {category}
Subcategory: {subcategory}
Description: {description}
Question Type: {question_type}

Generate a realistic, detailed question and comprehensive answer about {subcategory} in the maritime industry.

CRITICAL REQUIREMENTS:
1. The question MUST be practical and real-world (something an officer would actually face)
2. The answer MUST be technically accurate, detailed, and complete
3. Include specific procedures, safety considerations, and regulatory requirements
4. Use proper maritime terminology
5. Reference relevant conventions (SOLAS, MARPOL, STCW, etc.) where applicable
6. For calculations, show step-by-step working
7. For emergencies, emphasize safety protocols
8. For procedures, list all steps in order

Format your response EXACTLY as:
QUESTION: [Your detailed question here]

ANSWER: [Your comprehensive answer here, 200-400 words]

Generate NOW:"""

    return base_prompt, question_type

def parse_qa_response(response: str) -> Optional[Dict[str, str]]:
    """Parse the Q&A from API response."""
    try:
        if "QUESTION:" not in response or "ANSWER:" not in response:
            return None
        
        parts = response.split("ANSWER:")
        question_part = parts[0].replace("QUESTION:", "").strip()
        answer_part = parts[1].strip()
        
        # Basic quality checks
        if len(question_part) < 20 or len(answer_part) < 100:
            return None
        
        # Check for refusals
        refusal_phrases = ["i cannot", "i can't", "as an ai", "i'm not able"]
        if any(phrase in answer_part.lower() for phrase in refusal_phrases):
            return None
        
        return {
            "question": question_part,
            "answer": answer_part
        }
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def generate_sample(
    category: str,
    subcategory: str,
    description: str,
    sample_num: int,
    providers: List[APIProvider],
    stats: GenerationStats
) -> Optional[Dict]:
    """Generate a single Q&A sample."""
    
    # Rotate through providers
    provider = providers[sample_num % len(providers)]
    
    prompt, question_type = create_generation_prompt(category, subcategory, description, sample_num)
    
    response = provider.generate(prompt, max_tokens=800)
    if not response:
        stats.failed += 1
        return None
    
    qa_data = parse_qa_response(response)
    if not qa_data:
        stats.failed += 1
        return None
    
    # Create sample
    sample = {
        "id": f"{category}_{subcategory}_{sample_num}_{int(time.time())}",
        "category": category,
        "subcategory": subcategory,
        "question_type": question_type,
        "question": qa_data["question"],
        "answer": qa_data["answer"],
        "provider": provider.name,
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "description": description,
            "sample_number": sample_num
        }
    }
    
    # Update stats
    stats.successful += 1
    if provider.name == "google":
        stats.google_count += 1
    elif provider.name == "cerebras":
        stats.cerebras_count += 1
    elif provider.name == "groq":
        stats.groq_count += 1
    
    if category not in stats.by_category:
        stats.by_category[category] = 0
    stats.by_category[category] += 1
    
    return sample

def main():
    """Main generation loop."""
    print("🚢 Comprehensive Maritime Data Generation System")
    print("=" * 60)
    print(f"Target: {TARGET_SAMPLES:,} samples")
    print(f"Categories: {len(MARITIME_TOPICS)}")
    print(f"Output: {OUTPUT_FILE}")
    print("=" * 60)
    
    # Initialize providers
    providers = [
        GoogleGeminiProvider(),
        CerebrasProvider(),
        GroqProvider()
    ]
    
    print("\n✅ API Providers initialized:")
    for p in providers:
        print(f"  - {p.name}: {p.model}")
    
    # Calculate distribution
    distribution = calculate_category_distribution(TARGET_SAMPLES)
    print(f"\n📊 Sample distribution across {len(distribution)} categories")
    
    # Load progress
    progress = load_progress()
    stats = load_stats()
    
    print(f"\n📈 Current progress: {stats.successful:,} successful, {stats.failed:,} failed")
    
    # Start generation
    start_time = time.time()
    samples_written = 0
    
    with open(OUTPUT_FILE, 'a') as f:
        for category, target_count in distribution.items():
            completed = progress["completed_categories"].get(category, 0)
            
            if completed >= target_count:
                print(f"✓ {category}: Already complete ({completed}/{target_count})")
                continue
            
            print(f"\n🔄 Generating {category} ({completed}/{target_count})...")
            info = MARITIME_TOPICS[category]
            
            subcategories = info["subcategories"]
            samples_per_sub = target_count // len(subcategories)
            
            for subcategory in subcategories:
                for i in range(samples_per_sub):
                    if completed >= target_count:
                        break
                    
                    sample = generate_sample(
                        category, subcategory, info["description"],
                        i, providers, stats
                    )
                    
                    if sample:
                        f.write(json.dumps(sample) + '\n')
                        f.flush()
                        samples_written += 1
                        completed += 1
                        
                        if samples_written % 10 == 0:
                            # Update progress
                            progress["completed_categories"][category] = completed
                            progress["total_generated"] = stats.successful
                            save_progress(progress)
                            save_stats(stats)
                            
                            elapsed = time.time() - start_time
                            rate = samples_written / elapsed if elapsed > 0 else 0
                            eta_seconds = (TARGET_SAMPLES - stats.successful) / rate if rate > 0 else 0
                            eta_hours = eta_seconds / 3600
                            
                            print(f"  ✓ {samples_written} samples | Rate: {rate:.2f}/s | ETA: {eta_hours:.1f}h")
                    
                    # Rate limiting
                    time.sleep(0.5)
            
            # Save after each category
            progress["completed_categories"][category] = completed
            save_progress(progress)
            save_stats(stats)
            
            print(f"✅ {category}: Complete ({completed}/{target_count})")
    
    # Final stats
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("🎉 GENERATION COMPLETE!")
    print(f"✓ Total generated: {stats.successful:,}")
    print(f"✗ Failed: {stats.failed:,}")
    print(f"⏱️  Time: {elapsed/3600:.2f} hours")
    print(f"📊 Rate: {stats.successful/elapsed:.2f} samples/sec")
    print(f"\nProvider usage:")
    print(f"  Google: {stats.google_count:,}")
    print(f"  Cerebras: {stats.cerebras_count:,}")
    print(f"  Groq: {stats.groq_count:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
