"""
REAL MARITIME USE CASES - Not Random Generation!

This defines ACTUAL scenarios that maritime officers face daily.
Every question must be defensible as a REAL situation.
Every answer must be SAFE and follow proper procedures.

This is a LIFE-SAFETY system, not a chatbot.
"""

# REAL WORLD MARITIME SCENARIOS
# Each scenario is based on actual incidents, regulations, and daily operations

REAL_MARITIME_SCENARIOS = {
    
    # NAVIGATION - Real Bridge Operations
    "navigation_real_scenarios": [
        {
            "scenario": "Collision avoidance in TSS",
            "context": "Your vessel is transiting through Dover Strait TSS at 14 knots. You observe a vessel on ARPA showing CPA 0.3nm, TCPA 8 minutes, crossing from port to starboard.",
            "must_include": ["COLREGS Rule 15", "sound signals", "VHF communication", "action to avoid collision", "documentation in deck log"],
            "safety_critical": True,
            "real_incident_basis": "Based on Dover Strait traffic patterns"
        },
        {
            "scenario": "GPS failure in pilotage waters",
            "context": "All GPS receivers fail while approaching pilot station in restricted visibility (0.5nm visibility). You have radar, compass, and paper charts.",
            "must_include": ["radar position fixing", "parallel indexing", "reducing speed", "sound signals", "calling pilot station"],
            "safety_critical": True,
            "real_incident_basis": "GPS jamming incidents in Middle East"
        },
        {
            "scenario": "Anchor dragging in storm",
            "context": "Vessel at anchor in designated anchorage. Wind increases to Force 9. Anchor watch reports GPS shows vessel has moved 200m from original position.",
            "must_include": ["checking anchor position", "engine readiness", "second anchor deployment", "VTS notification", "master notification"],
            "safety_critical": True,
            "real_incident_basis": "Common anchoring emergency"
        },
        {
            "scenario": "ECDIS primary and backup failure",
            "context": "Both ECDIS systems crash simultaneously during ocean passage. Paper chart portfolio is on board but not fully corrected for current voyage.",
            "must_include": ["switching to paper charts", "requesting ENC updates via email", "plotting position manually", "NAVAREA warnings", "company reporting"],
            "safety_critical": True,
            "real_incident_basis": "ECDIS software failures documented by IMO"
        }
    ],
    
    # ENGINEERING - Real Machinery Problems
    "engineering_real_scenarios": [
        {
            "scenario": "Main engine high cooling water temperature",
            "context": "Main engine cooling water temperature rises from 72°C to 88°C during sea passage. Cooling water pressure normal. Sea water temperature 28°C.",
            "must_include": ["checking strainers", "inspecting cooler", "checking thermostats", "reducing engine load", "checking expansion tank"],
            "safety_critical": True,
            "real_incident_basis": "Common cooling system issue"
        },
        {
            "scenario": "Blackout in port during cargo operations",
            "context": "Total electrical failure while loading containers in port. Cranes stopped mid-operation. Emergency generator starts but cannot take full load.",
            "must_include": ["emergency generator priorities", "stopping cargo operations", "shore power", "informing terminal", "investigating cause"],
            "safety_critical": True,
            "real_incident_basis": "Blackout incidents in container terminals"
        },
        {
            "scenario": "Fuel contamination discovered",
            "context": "After bunkering 200MT IFO380 in Singapore, fuel analysis shows high water content (0.8%) and sediment. Main engine is running on this fuel.",
            "must_include": ["purifier operation", "settling time", "fuel sampling", "engine monitoring", "bunker claim documentation"],
            "safety_critical": True,
            "real_incident_basis": "Bunker contamination cases"
        },
        {
            "scenario": "Steering gear hydraulic leak",
            "context": "Steering gear alarm sounds. Inspection shows hydraulic oil leaking from starboard ram seal. Oil level dropped 15%. Vessel is 20nm from pilot station.",
            "must_include": ["switching to emergency steering", "reducing speed", "notifying pilot", "manual steering drill", "port authority notification"],
            "safety_critical": True,
            "real_incident_basis": "Steering gear failures causing incidents"
        }
    ],
    
    # SAFETY - Real Emergency Situations  
    "safety_real_scenarios": [
        {
            "scenario": "Man overboard in North Atlantic",
            "context": "Crew member falls overboard during heavy weather (Force 8, 4m seas) at 2300 LT. Vessel speed 12 knots. Location: 48°N, 020°W.",
            "must_include": ["immediate actions", "Williamson turn", "GMDSS distress", "lifebuoy with light", "searchlight", "rescue boat preparation"],
            "safety_critical": True,
            "real_incident_basis": "Actual MOB incidents in North Atlantic"
        },
        {
            "scenario": "Enclosed space entry - tank inspection",
            "context": "Need to inspect ballast tank #3 for corrosion. Tank was last opened 6 months ago. Tank has been in use (ballasted and deballasted).",
            "must_include": ["ventilation time", "gas testing (O2, H2S, LEL)", "permit to work", "rescue equipment", "communication", "attendant on deck"],
            "safety_critical": True,
            "real_incident_basis": "Enclosed space fatalities - INTERCARGO reports"
        },
        {
            "scenario": "Engine room fire in fuel purifier",
            "context": "Fire alarm from engine room. CCTV shows flames from fuel purifier area. Unmanned engine room. Vessel at sea.",
            "must_include": ["emergency stop", "fire boundaries", "fixed fire suppression", "mustering crew", "emergency steering", "GMDSS preparation"],
            "safety_critical": True,
            "real_incident_basis": "Engine room fires - AGCS loss statistics"
        },
        {
            "scenario": "Crew member chest pain",
            "context": "45-year-old engineer complains of severe chest pain radiating to left arm. Sweating, pale. Vessel is 800nm from nearest port. No doctor on board.",
            "must_include": ["MEDICO call", "first aid", "aspirin if not allergic", "monitoring vital signs", "medevac considerations", "diversion decision"],
            "safety_critical": True,
            "real_incident_basis": "Medical emergencies requiring medevac"
        }
    ],
    
    # CARGO - Real Cargo Operations
    "cargo_real_scenarios": [
        {
            "scenario": "Reefer container temperature alarm",
            "context": "Container TCLU1234567 (pharmaceuticals at -20°C) shows temperature risen to -15°C. Container is on deck, bay 42, tier 82.",
            "must_include": ["checking power connection", "checking setpoint", "checking refrigerant", "cargo interests notification", "temperature records"],
            "safety_critical": False,
            "real_incident_basis": "Reefer cargo claims"
        },
        {
            "scenario": "Dangerous goods container damage",
            "context": "During heavy weather, container with UN 1203 (gasoline) Class 3 shows structural damage to corner post. Container is in hold, no leakage visible.",
            "must_include": ["inspection", "segregation check", "ventilation", "fire watch", "IMDG Code reference", "port authority notification"],
            "safety_critical": True,
            "real_incident_basis": "DG container incidents"
        },
        {
            "scenario": "Bulk cargo liquefaction risk",
            "context": "Loading iron ore concentrate. Moisture content certificate shows 8.5%. TML is 9.0%. Shipper requests to load cargo.",
            "must_include": ["IMSBC Code", "can test", "Master's decision", "written protest", "P&I club notification"],
            "safety_critical": True,
            "real_incident_basis": "Bulk carrier losses due to cargo shift"
        }
    ],
    
    # REGULATIONS - Real Compliance Scenarios
    "regulations_real_scenarios": [
        {
            "scenario": "MARPOL Annex I - oil spill during bunkering",
            "context": "During bunkering operations, overflow from bunker tank causes 0.5m³ oil spill into harbor water. Port authority witnesses the spill.",
            "must_include": ["immediate containment", "SOPEP activation", "port authority notification", "oil record book", "internal investigation", "reporting requirements"],
            "safety_critical": True,
            "real_incident_basis": "Bunker spill penalties and detentions"
        },
        {
            "scenario": "PSC inspection - deficiencies found",
            "context": "Paris MOU PSC inspection finds: 1) Expired lifeboat batteries 2) Missing SOPEP drill records 3) Fire door held open with wooden wedge.",
            "must_include": ["immediate rectification", "detention risk", "company notification", "corrective actions", "follow-up inspection"],
            "safety_critical": True,
            "real_incident_basis": "PSC detention statistics"
        },
        {
            "scenario": "STCW rest hours non-compliance",
            "context": "During PSC inspection, Second Officer's records show only 8 hours rest in 24-hour period on 3 occasions in past 14 days due to cargo operations.",
            "must_include": ["STCW rest hour requirements", "exemptions", "master's responsibility", "deficiency", "manning review"],
            "safety_critical": False,
            "real_incident_basis": "Common PSC deficiency"
        },
        {
            "scenario": "ISM internal audit finding",
            "context": "Internal audit finds bridge team not following company SMS procedure for voyage planning. 3 voyages completed without proper documented appraisal.",
            "must_include": ["non-conformity report", "root cause analysis", "corrective action", "crew training", "DPA notification"],
            "safety_critical": False,
            "real_incident_basis": "ISM audit findings"
        }
    ],
    
    # STABILITY - Real Stability Issues
    "stability_real_scenarios": [
        {
            "scenario": "Loading computer failure before departure",
            "context": "Loading computer crashes after loading completed. Container ship ready to sail in 2 hours. Paper stability booklet available. 1,800 TEU on board.",
            "must_include": ["manual GM calculation", "stress calculation", "max KG check", "stability criteria", "departure checklist"],
            "safety_critical": True,
            "real_incident_basis": "Loading computer dependencies"
        },
        {
            "scenario": "Free surface effect - slack tanks",
            "context": "Chief Officer reports GM is 1.2m but vessel feels 'tender' (slow rolling). Fuel tanks are at 40% capacity. No ballast in double bottom.",
            "must_include": ["free surface correction", "tank filling", "ballasting", "stability book FSM tables", "master notification"],
            "safety_critical": True,
            "real_incident_basis": "Stability accidents due to free surface"
        },
        {
            "scenario": "Heavy weather damage - water on deck",
            "context": "After heavy weather, vessel has water on deck (hatch covers area). Estimated 200 tons of water. Rolling period has increased.",
            "must_include": ["draining water", "freeing ports", "GM recalculation", "weather routing", "structural inspection"],
            "safety_critical": True,
            "real_incident_basis": "Heavy weather incidents"
        }
    ],
    
    # COMMUNICATIONS - Real Communication Scenarios
    "communications_real_scenarios": [
        {
            "scenario": "Receiving MAYDAY relay",
            "context": "Your vessel receives MAYDAY RELAY from coast station. Vessel in distress is 45nm from your position. You are closest vessel. Master is on bridge.",
            "must_include": ["acknowledging message", "informing master", "SAR coordination", "course alteration", "crew preparation", "GMDSS log"],
            "safety_critical": True,
            "real_incident_basis": "SAR obligations under SOLAS"
        },
        {
            "scenario": "GMDSS equipment failure",
            "context": "MF/HF radio transceiver fails during ocean passage. VHF and INMARSAT C working. Nearest coast 300nm. Next port 5 days away.",
            "must_include": ["spare parts", "alternative communications", "flag state notification", "repair arrangements", "sailing permit"],
            "safety_critical": True,
            "real_incident_basis": "GMDSS equipment failures"
        }
    ]
}

# CALCULATION SCENARIOS - Must have step-by-step working
MARITIME_CALCULATIONS = {
    "navigation_calculations": [
        "Great circle vs rhumb line distance comparison",
        "ETA calculation with current and wind",
        "Fuel consumption for voyage planning",
        "Tidal height calculation for port entry",
        "True motion vs relative motion ARPA",
        "Parallel indexing calculations",
        "Anchor chain scope calculation"
    ],
    "stability_calculations": [
        "GM calculation from roll period",
        "Free surface moment calculation",
        "Maximum KG for departure condition",
        "Deadweight and displacement from drafts",
        "Trim calculation after cargo operation",
        "Shear force and bending moment limits",
        "Grain heeling moment calculation"
    ],
    "engineering_calculations": [
        "Fuel consumption per day calculation",
        "Boiler steam generation vs fuel consumption",
        "Refrigeration capacity calculation",
        "Pump capacity and head calculation",
        "Electrical load calculation and generator sizing",
        "Air compressor capacity for ship's requirements",
        "Propeller slip calculation"
    ],
    "cargo_calculations": [
        "Reefer container electrical load",
        "Ballast water calculation for GM",
        "Cargo stowage factor calculation",
        "Dunnage requirements for steel cargo",
        "Tank capacity ullage tables",
        "Cargo hold ventilation requirements",
        "Lashing force calculation for containers"
    ]
}

# REGULATORY SCENARIOS - Must reference actual regulations
REGULATORY_REFERENCES = {
    "SOLAS": [
        "Chapter III - Lifesaving appliances and arrangements",
        "Chapter II-2 - Fire protection, detection and extinction",
        "Chapter V - Safety of navigation",
        "Chapter VI - Carriage of cargoes",
        "Chapter XI-2 - Ship security"
    ],
    "MARPOL": [
        "Annex I - Oil pollution prevention",
        "Annex II - Chemical tankers",
        "Annex IV - Sewage",
        "Annex V - Garbage",
        "Annex VI - Air pollution and SEEMP"
    ],
    "STCW": [
        "Table A-II/1 - OOW Certificate requirements",
        "Table A-III/1 - Engineering OOW requirements",
        "Rest hours requirements Section A-VIII/1",
        "Watchkeeping principles Section A-VIII/2"
    ],
    "IMDG_CODE": [
        "Class 3 - Flammable liquids segregation",
        "Class 5.1 - Oxidizing substances separation",
        "Class 7 - Radioactive materials special requirements",
        "Class 9 - Miscellaneous dangerous goods"
    ],
    "ISM_CODE": [
        "Section 6 - Resources and personnel",
        "Section 7 - Development of plans for shipboard operations",
        "Section 9 - Reports and analysis of non-conformities",
        "Section 10 - Maintenance of ship and equipment"
    ],
    "ISPS_CODE": [
        "Part A - Mandatory requirements",
        "Security Level 1, 2, 3 procedures",
        "SSP - Ship Security Plan components",
        "Security drills and exercises"
    ]
}

# PROCEDURE SCENARIOS - Must follow published procedures
STANDARD_PROCEDURES = {
    "bridge_procedures": [
        "Bridge team management during pilotage",
        "Taking over navigation watch - handover checklist",
        "Master standing orders compliance",
        "Navigation audit preparation",
        "ECDIS backup and route copy"
    ],
    "engine_procedures": [
        "Main engine start sequence from dead ship",
        "Changing over from HFO to MDO",
        "Boiler light-up procedure",
        "Emergency generator start and load test",
        "Fuel oil purifier operation"
    ],
    "safety_procedures": [
        "Fire drill conduct and evaluation",
        "Lifeboat davit operation and safety",
        "Permit to work for hot work",
        "Lockout/tagout procedure",
        "Emergency steering drill"
    ],
    "cargo_procedures": [
        "Pre-loading tank inspection",
        "Inerting cargo holds before loading",
        "Cargo securing inspection before departure",
        "Temperature monitoring for reefer cargo",
        "Dangerous goods emergency response"
    ]
}
