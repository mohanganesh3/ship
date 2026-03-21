# MARITIME TRAINING DATA — COVERAGE GAP ANALYSIS

## Dataset Under Review: ~100 files, ~28,000 pages across 11 categories

> **Analysis Date**: 16 February 2026
> **Purpose**: Identify missing, underrepresented, and outdated content for a maritime AI chatbot training dataset
> **Analyst Perspective**: Maritime engineering domain expert + AI training data analyst

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Critical Topics MISSING Entirely](#2-critical-topics-missing-entirely)
3. [Topics UNDERREPRESENTED](#3-topics-underrepresented)
4. [OUTDATED Materials](#4-outdated-materials)
5. [Rank/Role-Specific Gaps](#5-rankrole-specific-gaps)
6. [Coverage Ratings (1-10)](#6-coverage-ratings-1-10)
7. [Priority Acquisition List](#7-priority-acquisition-list)
8. [Appendix: Complete Gap Matrix](#8-appendix-complete-gap-matrix)

---

## 1. EXECUTIVE SUMMARY

### Overall Dataset Health: 4.5/10

The current dataset has **strong theoretical foundations** (thermodynamics, marine diesels, naval architecture) but has **critical operational gaps** that would leave a ship crew chatbot unable to answer 40-50% of daily operational questions. The biggest blind spots are:

| Severity | Gap Area | Impact |
|----------|----------|--------|
| 🔴 CRITICAL | Cargo operations (tanker/bulk/container) | Officers ask about this DAILY |
| 🔴 CRITICAL | Auxiliary machinery systems (OWS, FWG, purifiers, sewage, incinerator) | Engineers ask about this EVERY WATCH |
| 🔴 CRITICAL | GMDSS / communication systems | Bridge officers need this constantly |
| 🔴 CRITICAL | ECDIS operations (not just the resolution) | Mandatory on all SOLAS vessels |
| 🟠 SEVERE | Deck operations (mooring, anchoring, cranes) | Deck officers' core job |
| 🟠 SEVERE | Bunkering operations & fuel management | Weekly/bi-weekly for every vessel |
| 🟠 SEVERE | Permit to Work / enclosed space / hot work | Safety-critical, PSC focus area |
| 🟠 SEVERE | Ship-type-specific operations | Different ships = different worlds |
| 🟡 MAJOR | Port State Control inspections | Every port call |
| 🟡 MAJOR | Class surveys & dry-docking | Career-defining events for engineers |
| 🟡 MAJOR | Environmental compliance (scrubbers, BWTS, ECA) | Tightening regulations |
| 🟡 MAJOR | Hydraulic & pneumatic systems | Every ship has them |
| 🟡 MAJOR | Refrigeration & HVAC | Standard auxiliary system |
| 🟡 MAJOR | Welding, coatings, and repair procedures | Maintenance reality |

### The Fundamental Problem

The dataset is **textbook-heavy and procedure-light**. It teaches theory well (how a diesel engine works) but doesn't teach operations well (how to start the ME from cold, how to switch from HFO to MDO before entering ECA, how to run a fuel oil purifier). 

A crew member doesn't ask "explain the Otto cycle" — they ask:
- *"What's the procedure to switch fuel before entering SECA?"*
- *"OWS is alarming at 14 ppm — what do I check?"*
- *"How do I prepare tanks for loading palm oil after carrying fuel oil?"*
- *"What documents does PSC want to see?"*

The dataset cannot answer most of these questions.

---

## 2. CRITICAL TOPICS MISSING ENTIRELY

### 2.1 🔴 CARGO OPERATIONS — The Biggest Gap

**Why it's critical**: Cargo is the REASON ships exist. Deck officers spend 60-70% of their working time on cargo operations. Engineers interact with cargo systems (pumps, heating, IG, COW) constantly on tankers.

#### MISSING: Oil Tanker Operations
- **ISGOTT** (International Safety Guide for Oil Tankers and Terminals, 6th ed 2020) — THE bible for tanker operations
- Crude Oil Washing (COW) procedures
- Inert Gas System (IGS) operations and troubleshooting
- Tank cleaning procedures and sequences
- Cargo calculation (ullage, innage, VEF, ROB, OBQ)
- Loading/discharge planning and rate calculations
- Vapour recovery systems
- Tank atmosphere testing and gas-freeing
- Static electricity precautions
- Ship-to-ship (STS) transfer operations
- Tanker Management and Self Assessment (TMSA) — OCIMF
- Condition Assessment Programme (CAP)

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **ISGOTT 6th Edition (OCIMF, 2020)** | 🔴 CRITICAL |
| **ICS/OCIMF Ship-to-Ship Transfer Guide (Petroleum)** | 🟠 HIGH |
| **OCIMF Mooring Equipment Guidelines (MEG4, 2018)** | 🟠 HIGH |
| Inert Gas Systems (IMO, 1990)** | 🟡 MEDIUM |
| Tanker Safety Guide (Chemicals) — ICS | 🟡 MEDIUM |

#### MISSING: Chemical Tanker Operations
- IBC Code (International Code for the Construction and Equipment of Ships Carrying Dangerous Chemicals in Bulk)
- Chemical handling procedures
- Compatibility charts
- Tank coating requirements per cargo
- P&A Manual (Procedures and Arrangements Manual)
- Cargo heating/cooling requirements

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **IBC Code (IMO, current edition)** | 🔴 CRITICAL |
| **Tanker Safety Guide — Chemicals (ICS, 5th ed)** | 🟠 HIGH |
| **Chemical Distribution Institute (CDI) inspection guides** | 🟡 MEDIUM |

#### MISSING: Bulk Carrier Operations
- BLU Code (Code of Practice for Safe Loading and Unloading of Bulk Carriers)
- Cargo liquefaction risks (IMSBC Code)
- Hold preparation and cleaning
- Draft survey procedures
- Hatch cover testing (ultrasonic, hose test)
- Cargo ventilation (three rules of ventilation)
- Grain loading (International Grain Code)
- Hold bilge system management
- Bulk carrier structural awareness (IACS recommendations)

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **IMSBC Code (IMO, 2023 amendment)** | 🔴 CRITICAL |
| **BLU Code & BLU Manual (IMO)** | 🟠 HIGH |
| **International Grain Code** | 🟡 MEDIUM |
| **Bulk Carrier Practice (Capt. Jack Isbester)** | 🟡 MEDIUM |

#### MISSING: Container Ship Operations
- Container stowage planning (bay plans)
- Lashing and securing (CSS Code)
- Dangerous Goods in containers (IMDG Code)
- Reefer container management
- Container weighing (VGM — SOLAS Chapter VI)
- Stack weight limits and stability
- Parametric rolling in container ships

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **IMDG Code (IMO, 2024 amendment)** | 🔴 CRITICAL |
| **CSS Code (IMO)** | 🟠 HIGH |
| **Container Ship Operations — Capt. Isbester** | 🟡 MEDIUM |

#### MISSING: LNG/LPG Carrier Operations
- IGC Code (International Code for the Construction and Equipment of Ships Carrying Liquefied Gases in Bulk)
- Cargo containment systems (membrane, Moss, SPB)
- Boil-off gas (BOG) management
- Reliquefaction systems
- Cool-down, loading, discharge procedures
- Gas detection systems
- Nitrogen systems
- Emergency shutdown (ESD) systems

> **Note**: There is 1 LNG operation guide in Category 11, but its scope/depth is unknown. If it's a single-vessel operating manual, it won't cover the theory and general procedures needed.

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **IGC Code (IMO, current edition)** | 🔴 CRITICAL |
| **Liquefied Gas Handling Principles on Ships and in Terminals (SIGTTO, 4th ed)** | 🔴 CRITICAL |
| **LNG Shipping Knowledge (SIGTTO)** | 🟠 HIGH |

---

### 2.2 🔴 AUXILIARY MACHINERY SYSTEMS

**Why it's critical**: Engineers spend MORE time on auxiliary systems than the main engine. The ME runs steadily; auxiliary systems break constantly.

#### MISSING: Oily Water Separator (OWS)
- Operating principles (gravity, coalescence, membrane)
- 15 ppm bilge alarm monitoring equipment
- MEPC.107(49) performance standards
- Oil content meter calibration
- MARPOL Annex I compliance recording
- Oil Record Book Part I entries
- Common faults and troubleshooting
- PSC deficiency: OWS is the #1 detention item globally

**Recommended**: *Marine Auxiliary Machinery (McGeorge, 7th ed)* covers this + multiple other gaps below.

#### MISSING: Fresh Water Generator (FWG) / Evaporator
- Vacuum evaporation principles
- Plate-type vs shell-and-tube
- Reverse Osmosis (RO) systems
- Chemical treatment of product water
- Jacket water temperature control for FWG
- Output testing (chloride content, conductivity)
- Common problems: scaling, priming, low output

#### MISSING: Sewage Treatment Plant (STP)
- Biological treatment (aerobic/anaerobic)
- Chemical treatment
- MARPOL Annex IV requirements
- MEPC.227(64) performance standards
- Effluent quality monitoring
- Comminuting and disinfecting

#### MISSING: Incinerator
- MEPC.244(66) performance standards
- Operation procedures
- Prohibited materials
- Temperature requirements
- Ash disposal
- MARPOL Annex VI compliance

#### MISSING: Fuel Oil Treatment / Purification System
- Centrifugal purifiers and clarifiers (Alfa Laval, Mitsubishi, Westfalia)
- Gravity disc selection
- Self-cleaning/self-desludging mechanisms
- Fuel oil system (settling tank → service tank → engine)
- Fuel testing (compatibility, stability, cat fines)
- Water content monitoring
- Fuel changeover procedures (HFO ↔ LSFO ↔ MGO)
- Cold flow properties (pour point, CFPP)
- ISO 8217 fuel specifications

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **Marine Auxiliary Machinery (McGeorge, 7th ed or later)** | 🔴 CRITICAL — fills 6+ gaps at once |
| **Reeds Vol 12: Motor Engineering Knowledge (Russell)** | 🔴 CRITICAL |
| **Alfa Laval Purifier Manual / Technical Documentation** | 🟠 HIGH |
| **Marine Fuel Oil Handling (CIMAC guidelines)** | 🟡 MEDIUM |

#### MISSING: Refrigeration & HVAC Systems
- Vapour compression cycle (R134a, R404A, R407C, R410A)
- Provision cooling plant
- Cargo refrigeration (reefer vessels)
- AC plant operations
- Compressor types and troubleshooting
- Refrigerant handling (ODS regulations, Kigali Amendment)
- Fan coil units, AHU maintenance
- Temperature control systems

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **Marine Refrigeration and Air Conditioning (Hundy, Trott, Welch)** | 🟠 HIGH |
| **Reeds Vol 9: Steam Engineering Knowledge** (covers ref/AC in marine context) | 🟡 MEDIUM |

#### MISSING: Air Compressor Systems
- Starting air system (30 bar)
- Control air system (7 bar)
- Working air / service air
- Air dryers and moisture separators
- Auto-start/stop controls
- Safety valves and relief devices
- Unloader mechanisms

#### MISSING: Steering Gear — Comprehensive
- The dataset has a Kawasaki steering gear manual (single product), but lacks:
  - Ram type vs rotary vane theory
  - SOLAS Chapter II-1 Reg 29 requirements
  - Steering gear testing procedures (pre-departure)
  - Emergency steering procedures
  - Autopilot interaction with steering gear
  - Hydraulic power unit maintenance
  - Trick wheel operations

#### MISSING: Hydraulic Systems (General)
- Hydraulic circuit design
- Pumps (gear, vane, piston)
- Valves (relief, directional, flow control)
- Accumulators
- Hydraulic fluid maintenance
- Troubleshooting (overheating, cavitation, leaks)
- Application: winches, cranes, hatch covers, steering gear, stabilizers

#### MISSING: Pneumatic Systems
- Instrument air systems
- Control valves (I/P converters)
- Pneumatic tools
- Air-operated valve actuators
- Compressed air safety

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **Marine Auxiliary Machinery (McGeorge, 7th ed)** | 🔴 CRITICAL (covers hydraulics, pneumatics, steering, compressors) |
| **Industrial Hydraulics Manual (Parker Hannifin)** | 🟡 MEDIUM |

---

### 2.3 🔴 COMMUNICATION SYSTEMS (GMDSS)

**Why it's critical**: GMDSS is a mandatory exam subject for all deck officers. There is ZERO coverage in the current dataset.

#### MISSING:
- GMDSS principles and sea areas (A1, A2, A3, A4)
- VHF DSC operations
- MF/HF DSC operations  
- INMARSAT C / Fleet Broadband
- EPIRB (Emergency Position Indicating Radio Beacon)
- SART (Search and Rescue Transponder)
- AIS-SART
- Navtex receiver operations
- Routine, urgency, distress, and safety communications
- Radio log keeping
- Battery maintenance for GMDSS equipment
- GMDSS survey requirements
- ITU Radio Regulations (relevant extracts)

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **GMDSS Manual (IMO, 2019 edition)** | 🔴 CRITICAL |
| **IAMSAR Manual Vol III (Mobile Facilities, IMO)** | 🔴 CRITICAL |
| **Reeds Vol 7: GMDSS (Waugh)** | 🟠 HIGH |
| **GMDSS Handbook (ITU/IMO)** | 🟡 MEDIUM |

---

### 2.4 🔴 ECDIS OPERATIONS

**Why it's critical**: ECDIS is now mandatory on ALL SOLAS vessels. Officers use it every watch. The dataset has only Resolution A.852 (1997 guidelines) — completely insufficient.

#### MISSING:
- ECDIS operational procedures
- Chart update management (permits, ENC updates)
- Route planning in ECDIS
- ECDIS alarms and watch settings
- Backup arrangements (independent ECDIS, paper charts)
- IHO S-52 presentation standards
- IHO S-57 / S-101 data standards  
- Chart datum and horizontal datum issues
- ECDIS anomalies and known problems
- Type-specific training (Furuno, JRC, Transas/Wärtsilä, Kongsberg)

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **ECDIS and Positioning (Weintrit, 2009 or later)** | 🟠 HIGH |
| **The Shiphandler's Guide (Hooyer, with ECDIS content)** | 🟡 MEDIUM |
| **IMO MSC.232(82) — Performance Standards for ECDIS** | 🟡 MEDIUM |
| Specific ECDIS equipment manuals (Furuno FMD-3x00, JRC JAN-9x02) | 🟠 HIGH |

---

### 2.5 🟠 DECK OPERATIONS

#### MISSING: Mooring Operations
- OCIMF Mooring Equipment Guidelines (MEG4)
- Mooring line types (HMPE, wire, synthetic)
- Mooring arrangements and patterns
- Mooring winch operations (auto-tension, rendering)
- Snap-back zones
- Ship-to-ship mooring
- Single point mooring (SPM/CBM)
- Mooring risk assessment

#### MISSING: Anchoring Operations
- Anchoring procedures
- Anchor watch procedures
- Anchor dragging detection
- Mediterranean mooring
- Emergency anchoring
- Anchor cable maintenance and testing
- Windlass operations

#### MISSING: Deck Crane Operations
- Crane types (knuckle boom, telescopic, pedestal)
- SWL calculations
- Load testing requirements
- Crane maintenance
- Operator certification
- Safety procedures

#### MISSING: Hatch Cover Operations
- Types (folding, rolling, lift-away, side-rolling)
- Weather-tightness testing
- Maintenance of seals and cleats
- Hydraulic system for hatch covers

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **OCIMF MEG4 (Mooring Equipment Guidelines, 4th ed, 2018)** | 🟠 HIGH |
| **The Mariner's Handbook (UKHO, NP100)** | 🟠 HIGH |
| **Nicholls's Seamanship & Nautical Knowledge** — already in dataset but need to verify coverage of mooring/anchoring sections | ✅ Verify |

---

### 2.6 🟠 OPERATIONAL PROCEDURES

#### MISSING: Bunkering Operations
- Pre-bunkering checklist
- Bunkering plan and communication
- Tank sounding procedures
- Fuel quality testing (on-board and lab)
- Bunker Delivery Note (BDN) verification
- Spill prevention and response
- Mass flow meter vs tank measurement
- MARPOL Annex VI fuel sulfur compliance
- Fuel changeover procedures

#### MISSING: Engine Room Watchkeeping
- Standing orders for engine room watch
- Watchkeeping routines (hourly rounds)
- Parameter logging and trend analysis
- Alarm response procedures
- Starting/stopping generators
- Paralleling generators
- Load sharing
- Blackout prevention and recovery
- Emergency procedures (flooding, fire, loss of steering)

#### MISSING: Permit to Work (PTW) Systems
- Enclosed space entry procedures (SOLAS Reg II-1/3-9)
- Hot work permits and procedures
- Working aloft / over the side
- Electrical isolation (lock-out/tag-out — LOTO)
- Cold work permits
- Risk assessment procedures
- Toolbox talks
- Near-miss reporting

#### MISSING: Bunkering & Fuel Management (Complete System)
- ISO 8217 fuel specifications
- Fuel testing and analysis
- Cat fines (catalytic fines) management
- Fuel treatment before engine
- Fuel accounting and ROB calculations
- Bunker survey procedures

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **ICS Safety Management Guidelines / Engine Room Procedures** | 🟠 HIGH |
| **OCIMF / ICS Ship-to-Ship Transfer Guide** | 🟡 MEDIUM |
| **Company SMS Manual template** (generic for training) | 🟡 MEDIUM |

---

### 2.7 🟠 ENVIRONMENTAL COMPLIANCE

**Why it's critical**: Environmental regulations are the FASTEST CHANGING area of maritime law. Non-compliance means detention, fines, even criminal prosecution.

#### MISSING / INSUFFICIENT:
- **MARPOL Annex VI — Air Pollution** (SOx, NOx, GHG regulations)
  - 2020 Global Sulphur Cap (0.50% → 0.10% in ECA)
  - IMO DCS (Data Collection System for fuel consumption)
  - CII (Carbon Intensity Indicator) — NEW since 2023
  - EEXI (Energy Efficiency Existing Ship Index) — NEW since 2023
  - EU ETS for shipping (2024+)
  - FuelEU Maritime regulation (2025+)
- **Exhaust Gas Cleaning Systems (Scrubbers)**
  - Open-loop, closed-loop, hybrid
  - Wash water monitoring and discharge criteria
  - Compliance monitoring
- **Ballast Water Management** — Convention is in dataset but:
  - Actual BWMS equipment operation is missing
  - UV, electrochlorination, filtration systems
  - D-1 vs D-2 standards
  - Commissioning testing
  - Ballast Water Record Book
- **SCR / EGR** for NOx Tier III compliance
- **Shore Power Connection (Cold Ironing)**
- **Carbon Capture (future readiness)**

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **MARPOL Annex VI — current consolidated text** | 🔴 CRITICAL |
| **IMO MEPC.353(78) — CII Guidelines** | 🟠 HIGH |
| **IMO MEPC.352(78) — EEXI Guidelines** | 🟠 HIGH |
| **EU ETS / FuelEU Maritime summary documents** | 🟠 HIGH |
| **Alfa Laval PureBallast / Optimarin manual** (or equivalent BWTS manual) | 🟡 MEDIUM |
| **Wärtsilä scrubber technical documentation** | 🟡 MEDIUM |

---

### 2.8 🟡 PORT STATE CONTROL & CLASS SURVEYS

#### MISSING: Port State Control (PSC)
- PSC inspection procedures (what they check)
- MOU guidelines (Paris MOU, Tokyo MOU, USCG)
- Common deficiency codes and categories
- Detention criteria
- ISM-related deficiencies
- How to prepare for PSC
- Appeals processes
- Concentrated Inspection Campaigns (CICs) — annual focus areas

#### MISSING: Classification Society Surveys
- Annual survey requirements
- Intermediate survey scope
- Special survey / Class renewal
- Dry-docking scope and requirements
- Continuous survey machinery (CSM)
- Enhanced Survey Programme (ESP) for tankers/bulk carriers
- Thickness measurement procedures
- Survey status tracking

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **Paris MOU Guidelines / PSC Manual** | 🟡 MEDIUM |
| **IACS Common Structural Rules** (relevant extracts) | 🟡 MEDIUM |
| **Dry Docking and Shipboard Maintenance (David House)** | 🟡 MEDIUM |

---

### 2.9 🟡 WELDING, COATINGS & REPAIR

#### MISSING:
- Shipboard welding procedures
- Welding processes (SMAW, GMAW, FCAW)
- Welding safety and certifications
- Hot work in hazardous areas
- Paint systems and coating specifications
- Surface preparation standards (Sa 2.5, SSPC)
- Ballast tank coating requirements (PSPC, MSC.215(82))
- Anti-fouling systems (AFS Convention)
- Cathodic protection (anodes, ICCP)
- Temporary repairs at sea vs yard repairs
- GRP repair procedures
- Stern tube and propeller shaft repair

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **AWS D3.6 Underwater Welding Code** (relevant sections) | 🟡 MEDIUM |
| **IMO Performance Standard for Protective Coatings (PSPC)** | 🟡 MEDIUM |
| **Marine Painting Manual (Hempel/Jotun guidelines)** | 🟡 MEDIUM |

---

### 2.10 🟡 WEATHER & VOYAGE PLANNING

#### MISSING:
- Weather routing principles
- Heavy weather procedures and preparations
- Tropical revolving storm (TRS) avoidance
- Ice navigation procedures (Polar Code)
- Passage planning requirements (STCW, SOLAS)
- UKC (Under Keel Clearance) calculations
- Squat, bank effect, shallow water effects
- Voyage data recorder (VDR) data management
- Piracy and armed robbery procedures (BMP5)

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **The Mariner's Handbook (NP100, UKHO)** | 🟠 HIGH |
| **BMP5 (Best Management Practices for Protection against Piracy)** | 🟡 MEDIUM |
| **Guide to Navigating in Ice (Transport Canada or IMO Polar Code)** | 🟡 MEDIUM |
| **Admiralty Guide to ECDIS Implementation, Policy and Procedures** | 🟡 MEDIUM |

---

### 2.11 🟡 LUBRICATING OIL SYSTEMS

#### MISSING:
- Main engine cylinder oil feed rates
- System oil management
- Lube oil testing and analysis (TBN, viscosity, insolubles, water content)
- Crosshead bearing lubrication
- Stern tube lubrication (oil-lubricated vs water-lubricated)
- Turbocharger lubrication
- Separator operation for lube oil
- Condition-based oil change strategies

---

### 2.12 🟡 SAR & EMERGENCY COORDINATION

#### MISSING:
- IAMSAR Manual Vol III (required aboard all ships)
- SAR coordination procedures
- On-scene commander (OSC) duties
- Search patterns (parallel, expanding square, sector)
- Person overboard (MOB) manoeuvres (Williamson turn, Anderson turn)
- MEDEVAC procedures
- Abandon ship procedures (beyond lifeboat manual)
- Damage control procedures
- Emergency towing
- Salvage — LOF, SCOPIC

**Recommended acquisitions:**
| Resource | Priority |
|----------|----------|
| **IAMSAR Manual Vol III (Mobile Facilities)** | 🔴 CRITICAL |
| **Shipboard Emergency Procedures (ICS)** | 🟠 HIGH |

---

## 3. TOPICS UNDERREPRESENTED

These topics EXIST in the dataset but lack the depth needed for a production-level maritime chatbot.

### 3.1 Electrical Systems — UNDERREPRESENTED

**What's there**: McGeorge (general), Payne (general), Reeds Vol 10 (instrumentation), Kraal (1965 — obsolete), PLCs (generic textbook)

**What's insufficient**:
- **High-voltage systems (3.3kV, 6.6kV, 11kV)** — increasingly common on modern ships (LNG carriers, cruise ships, large container ships, DP vessels). No dedicated coverage.
- **Power management systems** — automatic load shedding, blackout prevention, generator protection
- **Shore power connection** — regulations and procedures  
- **Variable frequency drives (VFDs)** — ubiquitous in modern ships for pumps, fans, compressors
- **Motor control centers** — practical troubleshooting
- **Insulation resistance testing** — megger testing procedures
- **Emergency generator testing** — weekly and annual requirements
- **Battery systems** — beyond the single flooded battery manual (modern ships use Li-ion for UPS, GMDSS, emergency lighting)
- **Hazardous area classification** — Zone 0, 1, 2 (IEC 60079) for tankers

**Recommended additions:**
| Resource | Priority |
|----------|----------|
| **Marine Electrical Equipment and Practice (McGeorge) — check if latest edition** | Verify |
| **High Voltage Installations in Ships (IACS UR-E)** | 🟠 HIGH |
| **IEC 60092 Series — Electrical Installations in Ships** | 🟡 MEDIUM |
| **ABB Marine Electrical Systems handbook** | 🟡 MEDIUM |

### 3.2 Navigation — UNDERREPRESENTED

**What's there**: Radar/ARPA (good), Bridge Procedures Guide (good), Heading sensor manual, Navipilot manual

**What's insufficient**:
- **Celestial navigation** — still required for Master's exam
- **Chartwork and position fixing** — traditional methods
- **Tides and tidal streams** — calculations
- **Magnetic compass** — deviation, adjustment (still tested)
- **Gyro compass** — principles, error corrections
- **AIS** — interpretation, SOLAS requirements
- **GPS/GNSS** — principles, errors, differential corrections
- **Pilotage** — master-pilot exchange, pilot card
- **Shiphandling** — berthing, unberthing, canal transits
- **Restricted visibility navigation** — practical procedures
- **Traffic Separation Schemes** — COLREG Rule 10

**Recommended additions:**
| Resource | Priority |
|----------|----------|
| **Nicholls's Concise Guide to Navigation (if not already the Seamanship book)** | 🟠 HIGH |
| **Reeds Vol 1: Mathematics for Marine Engineers** | 🟡 MEDIUM |
| **Reeds Vol 2: Applied Mechanics** | 🟡 MEDIUM |
| **Admiralty Manual of Navigation Vol 1** | 🟡 MEDIUM |
| **Shiphandling for the Mariner (MacElrevey & MacElrevey)** | 🟡 MEDIUM |

### 3.3 Safety — UNDERREPRESENTED

**What's there**: Olsen Firefighting (good), CO2 system manual, Water Mist, Fire Pump, Foam, Lifeboat manual

**What's insufficient**:
- **ISM Code implementation** — the CODE is there (×2), but no practical guidance on:
  - Safety Management System structure
  - Internal audits
  - Management review
  - Non-conformity management
  - Document control
  - Safety meetings
- **Risk assessment** — formal safety assessment methodology
- **Accident investigation** — procedures, root cause analysis (partially covered)
- **Enclosed space entry** — #1 killer on ships, no dedicated material
- **Liferaft servicing and deployment** — different from lifeboat
- **Pyrotechnics** — types, usage, expiry
- **SOPEP (Shipboard Oil Pollution Emergency Plan)** — response procedures
- **Contingency planning** — grounding, collision, flooding response
- **Crowd management and crisis leadership** — per STCW amendments

**Recommended additions:**
| Resource | Priority |
|----------|----------|
| **Code of Safe Working Practices for Merchant Seafarers (COSWP, MCA)** | 🔴 CRITICAL |
| **Guidelines for Entering Enclosed Spaces (IMO Res A.1050(27))** | 🟠 HIGH |
| **SOPEP Manual template / guidelines** | 🟡 MEDIUM |

### 3.4 Main Engine — UNDERREPRESENTED (Surprising)

**What's there**: Pounder's (theory, 2009), Lamb's (Q&A), specific engine manuals (Wartsila, MAN, HiMSEN)

**What's insufficient**:
- **Low-speed two-stroke engine electronic control** — ME-C / ME-GI / RT-flex modern control systems (beyond the basic manual)
- **Engine performance analysis** — power cards, draw cards, indicator diagrams  
  - MIP calculation
  - Fuel pump timing adjustment
  - Exhaust gas analysis
  - Scavenge air pressure analysis
- **Fuel injection systems** — common rail vs jerk pump, modern developments
- **Cylinder condition monitoring** — liner wear measurement, drain oil analysis
- **Dual-fuel engines** — increasingly common (LNG, methanol, ammonia — future fuels)
- **Slow steaming effects** — operational considerations
- **Engine room simulator scenarios** — practical procedures

**Recommended additions:**
| Resource | Priority |
|----------|----------|
| **MAN Energy Solutions — ME-C/-GI Engine Operation Manual** | 🟠 HIGH |
| **Reeds Vol 12: Motor Engineering Knowledge for Marine Engineers** | 🟠 HIGH |
| **Marine Engine Room Blue Book (Alfa Laval / Kockumation era, or modern equivalent)** | 🟡 MEDIUM |

### 3.5 Ship Stability — UNDERREPRESENTED

**What's there**: Barrass, Pemberton, Ridley stability books

**What's insufficient**:
- **Stability calculations for specific ship types** (tankers with free surface, container ships with high KG)
- **Damage stability** — probabilistic vs deterministic methods
- **Grain stability** — International Grain Code requirements
- **Dynamic stability** — parametric rolling, synchronous rolling
- **Stability software usage** — LoadMaster, CargoMax, NAPA
- **Intact stability criteria** — IMO 2008 IS Code (A.749(18) as amended)
- **Inclining experiment** — procedures and calculations

### 3.6 Maintenance Management — UNDERREPRESENTED

**What's there**: Root Cause Analysis handbook, Maintenance Engineering Handbook, Good Maintenance on Ships

**What's insufficient**:
- **Planned Maintenance System (PMS)** — software-based (AMOS, DNV ShipManager, Bass, TM Master)
- **Condition-based maintenance** — vibration analysis, oil analysis, thermography
- **Spare parts management** — requisition, critical spares identification
- **Dry dock specification** — how to prepare a repair specification
- **Fleet management KPIs** — OPEX, dry dock budget, technical performance
- **Purchasing and procurement for ships** — requisition procedures

---

## 4. OUTDATED MATERIALS

### Materials Requiring Replacement or Supplementation

| Current Material | Year | Problem | Replacement Needed |
|-----------------|------|---------|-------------------|
| **Kraal Marine Electrical Practice** | **1965** | 60 years old. Pre-semiconductor, pre-PLC, pre-VFD. Dangerous to rely on for electrical advice. | Replace with current edition McGeorge or equivalent |
| **MARPOL 2011 (DjVu)** | **2011** | Missing: 2020 Sulphur Cap, 2023 EEXI/CII, NOx Tier III areas, EEDI Phase 3. Critical gaps in air pollution rules. | **MARPOL Consolidated 2022+ edition** |
| **STCW 2011 (DjVu)** | **2011** | Missing: 2015 Manila Amendments implementation, ECDIS training requirements, ERM (Engine Room Management), polar water operations. | **STCW including 2015/2017 amendments** |
| **Corrosion Engineering (Fontana)** | **1985** | 40 years old. Missing: modern marine coatings, PSPC, IMO anti-fouling convention, cathodic protection advances. | **Corrosion and Materials in the Oil and Gas Industries** (modern) |
| **Pounder's Marine Diesel Engines** | **2009** | 17 years old. Missing: ME-GI dual fuel, Tier III compliance, electronic engines, methanol/ammonia engines, slow steaming optimization. | **Pounder's 10th ed (2021)** if available, or supplement with MAN/Wartsila technical papers |
| **Ballast Water Convention (DjVu)** | **2009** | Pre-entry into force (convention entered force 2017). Missing: D-2 implementation timeline, BWMS type approval standards, experience-building phase amendments. | **BWM Convention as amended 2022+** |
| **Machinery's Handbook** | **2016 (30th ed)** | **31st ed (2020)** available. Not critical — mostly mathematical/reference tables that don't change much. | Low priority update |
| **COLREG 2018** | 2018 | Reasonably current but verify amendments | Low priority |
| **SOLAS 2020** | 2020 | Missing 2022-2024 amendments (SOLAS III lifesaving, goal-based standards) | 🟠 Update when possible |
| **Sean Bennett Truck Engines** | 2015 | Not marine-specific. Limited value for maritime chatbot. | Consider removing or reducing weight in training |

### DjVu Format Concern

Three critical regulatory documents are in **DjVu format**: MARPOL, STCW, Ballast Water Convention. DjVu files:
- Have **poor OCR quality** compared to PDF
- Will produce **noisy, error-prone text** during extraction
- May have **missing pages, garbled text, or incorrect character recognition**
- **Recommendation**: Replace with clean PDF versions or manually verify OCR output quality

---

## 5. RANK/ROLE-SPECIFIC KNOWLEDGE GAPS

### 5.1 Engine Cadets (TME / Junior Engineer Trainee)

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Basic marine engineering theory | ✅ Good (Thermodynamics, Machinery's Handbook) | — |
| Engine room familiarization | ⚠️ Partial (engine manuals exist) | No structured familiarization guide |
| Workshop skills (fitting, turning, welding) | ❌ Missing | Workshop Practice Series or equivalent |
| Watchkeeping under supervision | ❌ Missing | Watchkeeping procedures guide |
| Safety orientation | ⚠️ Partial | COSWP needed |
| Oral exam preparation | ❌ Missing | Reeds series, Lamb's Q&A (partial) |

**Critical missing resource**: *Reeds Vol 8: General Engineering Knowledge for Marine Engineers* — the standard cadet textbook.

### 5.2 4th / 3rd Engineer (Operational Level)

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Main engine operation | ✅ Good | Performance analysis weak |
| Auxiliary machinery | ❌ CRITICAL GAP | McGeorge Marine Aux Machinery needed |
| Electrical systems (operational) | ⚠️ Partial | Practical troubleshooting weak |
| Fuel & lube oil management | ❌ Missing | — |
| Purifier operation | ❌ Missing | — |
| OWS / sewage / incinerator | ❌ Missing | — |
| Boiler operations | ✅ Good | — |
| Refrigeration plant | ❌ Missing | — |
| Watchkeeping procedures | ❌ Missing | — |
| PMS entries | ❌ Missing | — |

### 5.3 2nd Engineer / Chief Engineer (Management Level)

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Engine performance optimization | ⚠️ Partial | — |
| Maintenance planning | ⚠️ Partial (theory) | PMS software, practical planning missing |
| Chief Engineer's standing orders | ❌ Missing | — |
| Dry dock preparation | ❌ Missing | — |
| Budgeting and procurement | ❌ Missing | — |
| ISM compliance (engineering) | ⚠️ Code only | Implementation guidance missing |
| PSC preparation (engine room) | ❌ Missing | — |
| Class survey preparation | ❌ Missing | — |
| Incident investigation | ⚠️ Partial (RCA) | — |
| Environmental compliance | ❌ Missing | — |
| Bunkering oversight | ❌ Missing | — |
| Crew training and assessment | ❌ Missing | — |

### 5.4 Deck Cadets

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Seamanship basics | ⚠️ Partial (Nicholls's) | Need verification of depth |
| Navigation theory | ⚠️ Partial | Celestial nav, chartwork missing |
| COLREG | ✅ Good | — |
| Watchkeeping | ❌ Missing | — |
| Cargo basics | ❌ CRITICAL GAP | — |
| GMDSS basics | ❌ CRITICAL GAP | — |
| Mooring/anchoring | ❌ Missing | — |

### 5.5 2nd Officer / Chief Officer (Operational → Management)

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Passage planning | ❌ Missing | — |
| ECDIS operation | ❌ Missing (only resolution) | — |
| Cargo operations (type-specific) | ❌ CRITICAL GAP | — |
| Stability calculations | ✅ Good (theory) | Practical loading computer usage missing |
| Safety officer duties | ⚠️ Partial | — |
| Mooring/anchoring planning | ❌ Missing | — |
| SOPEP / contingency plans | ❌ Missing | — |
| Crew training and assessment | ❌ Missing | — |

### 5.6 Master / Captain

| Needed Knowledge | Coverage | Gap |
|-----------------|----------|-----|
| Shiphandling | ❌ Missing | — |
| Bridge Resource Management (BRM) | ❌ Missing | — |
| Maritime law & charterparties | ❌ Missing | — |
| P&I Club procedures | ❌ Missing | — |
| Collision/grounding response | ❌ Missing | — |
| Heavy weather decision-making | ❌ Missing | — |
| PSC interface | ❌ Missing | — |
| Company ISM compliance | ⚠️ Code only | — |
| Pilot-master exchange | ❌ Missing | — |
| Emergency command and control | ❌ Missing | — |
| Commercial awareness | ❌ Missing | — |
| Voyage planning oversight | ❌ Missing | — |

**Recommended for Captain/senior officer coverage:**
| Resource | Priority |
|----------|----------|
| **Shipmaster's Business Self-Examiner (Isbester)** | 🟠 HIGH |
| **The Shipmaster's Handbook on Ship's Business (Marico Marine)** | 🟠 HIGH |
| **Maritime Law (Christopher Hill, 6th ed)** or Lloyd's Maritime Law | 🟡 MEDIUM |

---

## 6. COVERAGE RATINGS (1-10)

### Rating Scale
- **9-10**: Comprehensive, production-ready, current
- **7-8**: Good foundation, minor gaps
- **5-6**: Partial coverage, significant gaps
- **3-4**: Basic/theoretical only, major practical gaps
- **1-2**: Token/negligible coverage
- **0**: Completely absent

### Ratings

| # | Critical Area | Rating | Justification |
|---|--------------|--------|---------------|
| 1 | **Main Engine Operations** | **6/10** | Strong theory (Pounder's) and specific manuals (MAN, Wartsila), but missing: performance analysis procedures, electronic engine control, dual-fuel operations, practical troubleshooting flowcharts. Pounder's is from 2009. |
| 2 | **Auxiliary Systems** | **2/10** | This is the WORST gap. No OWS, no FWG, no sewage plant, no incinerator, no purifiers, no refrigeration, no comprehensive auxiliary machinery textbook. Engineers deal with aux systems more than the ME. |
| 3 | **Electrical Systems** | **5/10** | Decent theoretical coverage across multiple books, but missing high-voltage systems, VFDs, practical troubleshooting, and the 1965 Kraal book is actively harmful (outdated). PLC book is generic, not marine-specific. |
| 4 | **Navigation** | **5/10** | Good radar/ARPA coverage and bridge procedures, but missing ECDIS operations, GMDSS, celestial navigation, chartwork, GPS/GNSS, AIS, shiphandling, passage planning procedures. |
| 5 | **Safety/Emergency Procedures** | **5/10** | Good firefighting coverage (Olsen 2023 is current and relevant). Lifeboat manual present. But missing: enclosed space entry, permit to work, COSWP, SOPEP, emergency response procedures, SAR, abandon ship procedures. |
| 6 | **Cargo Operations** | **1/10** | CRITICAL FAILURE. Virtually zero cargo operations content. No ISGOTT, no IBC Code, no IMSBC Code, no IMDG Code, no cargo calculation procedures, no tank cleaning, no inert gas. This is what officers DO. |
| 7 | **Environmental Compliance** | **3/10** | MARPOL is there but from 2011 — missing the 2020 Sulphur Cap, EEXI, CII, EU ETS. Ballast Water Convention present but pre-entry-into-force version. No scrubber content, no BWTS operation, no practical compliance procedures. |
| 8 | **Ship Management** | **2/10** | ISM Code present (×2) but no implementation guidance. No PMS procedures, no survey preparation, no PSC guidance, no crew management, no commercial operations, no voyage planning procedures, no SMS documentation. |
| 9 | **Medical Emergencies** | **7/10** | Good coverage with 3 dedicated medical resources (Ship Captain's Medical Guide, MFAG, WHO/ILO). This is one of the better-covered areas. Minor gap: telemedicine procedures, pandemic response (post-COVID protocols). |
| 10 | **Communication Systems** | **0/10** | ZERO GMDSS coverage. No VHF procedures, no DSC, no INMARSAT, no EPIRB/SART, no Navtex. This is a mandatory competency for all deck officers. Complete blind spot. |

### Summary Visualization

```
Main Engine Operations     ██████░░░░  6/10
Auxiliary Systems          ██░░░░░░░░  2/10   ← CRITICAL
Electrical Systems         █████░░░░░  5/10
Navigation                 █████░░░░░  5/10
Safety/Emergency           █████░░░░░  5/10
Cargo Operations           █░░░░░░░░░  1/10   ← CRITICAL
Environmental Compliance   ███░░░░░░░  3/10
Ship Management            ██░░░░░░░░  2/10   ← CRITICAL
Medical Emergencies        ███████░░░  7/10   ✓ Best coverage
Communication Systems      ░░░░░░░░░░  0/10   ← CRITICAL
                                              ──────────
                           WEIGHTED AVG: 3.6/10
```

---

## 7. PRIORITY ACQUISITION LIST

### TIER 1 — CRITICAL (Must have before any training)

These fill the largest gaps and provide the most value per document.

| # | Resource | Pages (est.) | Gaps Filled | Priority Score |
|---|----------|:------------:|-------------|:--------------:|
| 1 | **Marine Auxiliary Machinery (McGeorge, 7th+ ed)** | ~700 | OWS, FWG, purifiers, steering gear, compressors, hydraulics, pneumatics, refrigeration, bilge systems, fuel systems | **10/10** |
| 2 | **ISGOTT 6th Edition (OCIMF, 2020)** | ~500 | All tanker operations, cargo safety, tank cleaning, IG, loading/discharge | **10/10** |
| 3 | **GMDSS Manual (IMO, 2019)** | ~400 | ALL communication gaps | **10/10** |
| 4 | **IAMSAR Manual Vol III** | ~300 | SAR procedures, distress communication, search patterns, MOB | **9/10** |
| 5 | **IMSBC Code (IMO, current)** | ~500 | Bulk cargo operations, liquefaction, ventilation | **9/10** |
| 6 | **IMDG Code (IMO, current)** | ~1200 | Dangerous goods in containers, labeling, stowage, segregation | **9/10** |
| 7 | **Code of Safe Working Practices (COSWP, MCA)** | ~550 | PTW, enclosed space, hot work, PPE, working aloft, LOTO, risk assessment | **9/10** |
| 8 | **MARPOL Consolidated 2022+ Edition** | ~700 | Updates to all 6 annexes, 2020 sulphur cap, EEXI, CII | **9/10** |
| 9 | **Reeds Vol 12: Motor Engineering Knowledge** | ~400 | Auxiliary systems, engine room procedures, exam prep for engineers | **8/10** |
| 10 | **IGC Code (IMO)** | ~300 | LNG/LPG carrier operations | **8/10** |

**Estimated total: ~5,550 pages → Would raise overall coverage from 3.6/10 to approximately 6.5/10**

### TIER 2 — HIGH PRIORITY (Should have for comprehensive coverage)

| # | Resource | Pages (est.) | Gaps Filled |
|---|----------|:------------:|-------------|
| 11 | **Reeds Vol 7: GMDSS** | ~300 | GMDSS exam preparation, practical operations |
| 12 | **IBC Code (IMO)** | ~400 | Chemical tanker operations |
| 13 | **OCIMF MEG4 (Mooring Equipment Guidelines)** | ~300 | Mooring operations, snap-back zones, equipment |
| 14 | **The Mariner's Handbook (NP100, UKHO)** | ~400 | Weather, ice, tides, port entry, general guidance |
| 15 | **Shipmaster's Business Self-Examiner** | ~400 | Master's commercial/legal knowledge |
| 16 | **BLU Code & BLU Manual** | ~200 | Bulk carrier loading/unloading safety |
| 17 | **Liquefied Gas Handling Principles (SIGTTO)** | ~350 | LNG/LPG cargo handling theory + practice |
| 18 | **STCW Updated Edition (with 2015-2017 amendments)** | ~400 | Current training standards, ECDIS requirement |
| 19 | **Pounder's Marine Diesel Engines 10th ed (2021+)** | ~600 | Updated engine technology, dual fuel, Tier III |
| 20 | **CSS Code (IMO)** | ~200 | Container securing |

**Estimated total: ~3,550 pages → Would raise overall coverage to approximately 7.5/10**

### TIER 3 — MEDIUM PRIORITY (Nice to have for depth)

| # | Resource | Pages (est.) | Gaps Filled |
|---|----------|:------------:|-------------|
| 21 | Reeds Vol 8: General Engineering Knowledge | ~400 | Cadet-level comprehensive engineering |
| 22 | Marine Refrigeration and Air Conditioning | ~350 | Refrigeration systems detail |
| 23 | Shiphandling for the Mariner | ~300 | Berthing, unberthing, shiphandling |
| 24 | Nicholls's Concise Guide to Navigation | ~400 | Celestial navigation, chartwork |
| 25 | Dry Docking and Shipboard Maintenance | ~300 | Survey prep, dry dock procedures |
| 26 | ICS Engine Room Procedures Guide | ~200 | Watchkeeping SOPs |
| 27 | Admiralty Manual of Navigation Vol 1 | ~400 | Navigation theory depth |
| 28 | Parker Industrial Hydraulics Manual | ~250 | Hydraulic systems |
| 29 | Maritime Law (Christopher Hill) | ~500 | Legal knowledge for Masters |
| 30 | BMP5 (Anti-piracy Best Practices) | ~100 | Piracy/armed robbery procedures |

**Estimated total: ~3,200 pages → Would raise overall coverage to approximately 8.5/10**

---

## 8. APPENDIX: COMPLETE GAP MATRIX

### Topic-by-Topic Coverage Status (Alphabetical)

| Topic | Status | Sources in Dataset | Gap Severity |
|-------|--------|-------------------|--------------|
| Abandon ship procedures | ❌ Missing | — | 🟠 HIGH |
| Air compressors | ❌ Missing | — | 🟡 MEDIUM |
| Air conditioning / HVAC | ❌ Missing | — | 🟡 MEDIUM |
| AIS (Automatic Identification System) | ❌ Missing | — | 🟠 HIGH |
| Anchoring operations | ❌ Missing | Nicholls (partial?) | 🟠 HIGH |
| Anti-fouling systems | ❌ Missing | — | 🟡 MEDIUM |
| Auxiliary boiler operations | ✅ Present | Boiler Operations manual | ✅ OK |
| Ballast water management (convention) | ⚠️ Outdated | BWM Conv 2009 (DjVu) | 🟡 UPDATE |
| Ballast water treatment systems (equipment) | ❌ Missing | — | 🟠 HIGH |
| Blackout recovery | ❌ Missing | — | 🟠 HIGH |
| Bridge procedures | ✅ Present | ICS Bridge Procedures Guide 2016 | ✅ OK |
| Bulk carrier operations | ❌ Missing | — | 🔴 CRITICAL |
| Bunkering operations | ❌ Missing | — | 🟠 HIGH |
| Cargo calculations (tanker) | ❌ Missing | — | 🔴 CRITICAL |
| Cargo securing (containers) | ❌ Missing | — | 🔴 CRITICAL |
| Cathodic protection | ❌ Missing | Fontana 1985 (minimal, outdated) | 🟡 MEDIUM |
| Celestial navigation | ❌ Missing | — | 🟡 MEDIUM |
| Centrifugal pumps | ✅ Present | Gülich textbook | ✅ OK |
| Chemical tanker operations | ❌ Missing | — | 🔴 CRITICAL |
| CII / EEXI compliance | ❌ Missing | — | 🔴 CRITICAL |
| COLREG | ✅ Present | COLREG 2018 | ✅ OK |
| Condition monitoring | ⚠️ Basic | Condition monitoring guide | 🟡 MEDIUM |
| Container ship operations | ❌ Missing | — | 🔴 CRITICAL |
| Corrosion protection | ⚠️ Outdated | Fontana 1985 (DjVu) | 🟡 UPDATE |
| Crane operations (deck) | ❌ Missing | — | 🟡 MEDIUM |
| Damage control | ❌ Missing | — | 🟠 HIGH |
| Dangerous goods (IMDG) | ❌ Missing | — | 🔴 CRITICAL |
| Dry docking | ❌ Missing | — | 🟠 HIGH |
| Dual-fuel engines | ❌ Missing | MAN 31DF manual only | 🟠 HIGH |
| ECDIS operations | ❌ Missing | Only Res A.852 (1997) | 🔴 CRITICAL |
| Electrical – high voltage | ❌ Missing | — | 🟠 HIGH |
| Electrical – basic | ✅ Present | McGeorge, Payne | ✅ OK |
| Emergency generator | ❌ Missing (procedures) | — | 🟡 MEDIUM |
| Enclosed space entry | ❌ Missing | — | 🔴 CRITICAL |
| Engine performance analysis | ⚠️ Partial | Pounder's (2009) | 🟡 MEDIUM |
| EU ETS / FuelEU Maritime | ❌ Missing | — | 🟠 HIGH |
| Exhaust gas cleaning (scrubbers) | ❌ Missing | — | 🟠 HIGH |
| Fire detection systems | ⚠️ Partial | Olsen (general) | 🟡 MEDIUM |
| Firefighting | ✅ Good | Olsen 2023 + system manuals | ✅ OK |
| Fresh water generator | ❌ Missing | — | 🟠 HIGH |
| Fuel oil treatment / purifiers | ❌ Missing | — | 🔴 CRITICAL |
| GMDSS / communications | ❌ Missing | — | 🔴 CRITICAL |
| GPS / GNSS | ❌ Missing | — | 🟡 MEDIUM |
| Hatch covers | ❌ Missing | — | 🟡 MEDIUM |
| Heat exchangers | ✅ Present | Kakaç textbook | ✅ OK |
| Heavy weather operations | ❌ Missing | — | 🟠 HIGH |
| Hot work procedures | ❌ Missing | — | 🟠 HIGH |
| Hydraulic systems | ❌ Missing | — | 🟠 HIGH |
| Ice navigation / Polar Code | ❌ Missing | — | 🟡 MEDIUM |
| Incinerator | ❌ Missing | — | 🟠 HIGH |
| Inert gas system | ❌ Missing | — | 🔴 CRITICAL |
| ISM Code (text) | ✅ Present | ISM Code ×2 | ✅ OK |
| ISM implementation | ❌ Missing | — | 🟠 HIGH |
| ISPS Code | ✅ Present | ISPS Code | ✅ OK |
| Lifeboat | ✅ Present | Viking Norsafe manual | ✅ OK |
| Liferaft | ❌ Missing | — | 🟡 MEDIUM |
| LNG carrier operations | ⚠️ Partial | LNG operation guide (scope unknown) | 🟠 VERIFY |
| Lubricating oil systems | ❌ Missing | — | 🟠 HIGH |
| Main engine – slow speed | ✅ Present | Wartsila, MAN manuals; Pounder's | ✅ OK |
| Main engine – medium speed | ⚠️ Partial | HiMSEN, some Wartsila | 🟡 MEDIUM |
| Maritime law | ❌ Missing | — | 🟡 MEDIUM |
| Medical | ✅ Good | Ship Captain's Medical Guide, MFAG, WHO/ILO | ✅ OK |
| Mooring operations | ❌ Missing | — | 🟠 HIGH |
| Naval architecture theory | ✅ Good | Molland, Bruce, Reeds vols | ✅ OK |
| Oily water separator | ❌ Missing | — | 🔴 CRITICAL |
| Painting / coatings | ❌ Missing | — | 🟡 MEDIUM |
| Passage planning | ❌ Missing | — | 🟠 HIGH |
| Permit to work systems | ❌ Missing | — | 🔴 CRITICAL |
| Piracy / armed robbery | ❌ Missing | — | 🟡 MEDIUM |
| Planned Maintenance System | ❌ Missing | — | 🟠 HIGH |
| PLCs | ⚠️ Generic | Petruzella (not marine-specific) | 🟡 MEDIUM |
| Pneumatic systems | ❌ Missing | — | 🟡 MEDIUM |
| Port State Control | ❌ Missing | — | 🟠 HIGH |
| Propulsion theory | ✅ Present | Carlton Propellers | ✅ OK |
| Radar / ARPA | ✅ Good | Bole, Dineley, Wall 2013 | ✅ OK |
| Refrigeration systems | ❌ Missing | — | 🟠 HIGH |
| SAR procedures | ❌ Missing | — | 🟠 HIGH |
| Scrubber systems | ❌ Missing | — | 🟠 HIGH |
| Sewage treatment plant | ❌ Missing | — | 🟠 HIGH |
| Ship construction | ✅ Good | Bruce, Reeds Vol 5 | ✅ OK |
| Ship stability (theory) | ✅ Good | Barrass, Pemberton, Ridley | ✅ OK |
| Ship stability (loading computer) | ❌ Missing | — | 🟡 MEDIUM |
| Shiphandling | ❌ Missing | — | 🟡 MEDIUM |
| SOLAS | ✅ Present | SOLAS 2020 | ✅ OK |
| SOPEP | ❌ Missing | — | 🟡 MEDIUM |
| Steering gear (comprehensive) | ⚠️ Partial | Kawasaki manual only | 🟡 MEDIUM |
| Tank cleaning (tankers) | ❌ Missing | — | 🔴 CRITICAL |
| Tanker operations | ❌ Missing | — | 🔴 CRITICAL |
| Thermodynamics | ✅ Good | Moran textbook | ✅ OK |
| Turbochargers | ✅ Present | Turbocharger manual | ✅ OK |
| VDR data management | ❌ Missing | — | 🟡 MEDIUM |
| VFDs / motor drives | ❌ Missing | — | 🟡 MEDIUM |
| Voyage planning | ❌ Missing | — | 🟠 HIGH |
| Watch-keeping (engine room) | ❌ Missing | — | 🟠 HIGH |
| Weather routing | ❌ Missing | — | 🟡 MEDIUM |
| Welding procedures | ❌ Missing | — | 🟡 MEDIUM |
| Windlass / anchor gear | ❌ Missing | — | 🟡 MEDIUM |

### Statistics

| Status | Count | Percentage |
|--------|:-----:|:----------:|
| ✅ Present / Good | 22 | 25% |
| ⚠️ Partial / Outdated | 11 | 13% |
| ❌ Missing | 54 | 62% |

---

## CONCLUSION

### The Bottom Line

The dataset is built like a **marine engineering school library** — heavy on theory, textbooks, and reference books. What it's missing is the **operational layer**: the procedures, codes, and practical guides that crew members actually use on board.

### Top 5 Actions (in order):

1. **Acquire McGeorge Marine Auxiliary Machinery** — single book that fills the most gaps
2. **Acquire ISGOTT + IMSBC Code + IMDG Code** — fills the entire cargo operations void
3. **Acquire GMDSS Manual + IAMSAR Vol III** — fills communication & SAR gaps completely
4. **Acquire COSWP** — fills safety procedures and permit to work gaps
5. **Replace MARPOL 2011 with current consolidated edition** — brings environmental compliance up to date

### Estimated Impact

| Scenario | Coverage Rating | Page Count |
|----------|:--------------:|:----------:|
| Current dataset | **3.6/10** | ~28,000 |
| + Tier 1 (10 resources) | **6.5/10** | ~33,550 |
| + Tier 2 (10 resources) | **7.5/10** | ~37,100 |
| + Tier 3 (10 resources) | **8.5/10** | ~40,300 |
| Full coverage target | **9.0/10** | ~45,000 |

The current 28,000 pages are not wasted — they provide an excellent theoretical foundation. But without the operational layer (~12,000-17,000 additional pages), the chatbot will fail on the majority of questions that real crew members actually ask.

---

*End of Coverage Gap Analysis*
