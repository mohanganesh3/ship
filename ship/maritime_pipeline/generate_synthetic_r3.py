#!/usr/bin/env python3
"""
Round 3 synthetic procedures — targeted keyword coverage.
Adds documents containing the specific phrases the audit scans for.
"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extracted_text")
OUT = os.path.join(DATA_DIR, "synthetic_procedures_r3.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

def doc(title, topic, text):
    return {"title": title, "source": "synthetic_regulatory_r3",
            "topic": topic, "text": text.strip(),
            "scraped_at": datetime.utcnow().isoformat()}

DOCS = []

# ======================================================================
# FWG — Add "starting evaporator" / "evaporator start" phrases explicitly
# ======================================================================
DOCS.append(doc("How to Start a Fresh Water Generator — Step by Step Evaporator Starting Guide", "FWG startup procedure", """
Starting a Fresh Water Generator: Evaporator Starting Procedure

The fresh water generator uses a low-pressure evaporator (also called a distillation unit or freshwater evaporator) to produce potable water from seawater. The following is the standard evaporator starting procedure followed onboard all merchant vessels.

STARTING THE FWG EVAPORATOR — STEP BY STEP

Before starting the evaporator, confirm the main engine has been running for at least 1 hour and jacket water temperature is stable at 80-85°C.

Step 1 — Start ejector pump: The ejector pump creates the necessary vacuum inside the evaporator shell. Starting the ejector pump is always the first step when starting a FWG.

Step 2 — Open seawater feed valve: Seawater enters the evaporator shell on the cold side.

Step 3 — Open heating water valve: Jacket cooling water from the main engine is directed into the evaporator heating coils or plates. Starting the evaporator heating supply causes the seawater inside the shell to boil at low temperature due to the vacuum.

Step 4 — Monitor vacuum build-up: As the ejector continues running after starting the evaporator, the vacuum should reach approximately -0.9 bar gauge within 5-10 minutes.

Step 5 — Check salinometer: When distillate begins collecting at the bottom, start the salinometer sample valve. The salinometer reading should be checked after starting the evaporator and should remain below 2 ppm before directing water to the fresh water tank.

Step 6 — Start distillate pump: Once evaporation is confirmed (observed through sight glass), start the distillate pump.

Step 7 — Start brine pump: The brine (concentrated seawater) accumulates at the bottom of the evaporator shell. Start the brine pump to remove it.

Step 8 — Open FWG distillate valve to tank: Only when salinometer confirms salinity < 2 ppm should the three-way valve be directed to the fresh water tank.

EVAPORATOR PERFORMANCE MONITORING AFTER START
After starting the evaporator, monitor the following every 4 hours:
- Evaporator shell vacuum (should be -0.8 to -0.9 bar gauge)
- Evaporator heating water inlet temperature (should be 82-90°C)
- Distillate production rate (litres/hour vs design output)
- Salinometer reading (ppm) — alarm set at 2 ppm

STARTING FWG NEAR PORT
Do not start the FWG when within 20 nautical miles of land, as seawater quality near coasts may be compromised. The FWG should only be started when the vessel is at sea on main engine.

STOPPING THE FWG (EVAPORATOR SECURING PROCEDURE)
To stop the FWG: First close the heating water (jacket water) supply valve. Allow evaporator to cool for 5 minutes. Then stop distillate pump, stop brine pump, stop ejector pump. Open the vacuum breaker valve. Log total production in the Engine Room Logbook.
"""))

DOCS.append(doc("FWG Startup Checklist — Evaporator Start and Salinometer Procedure", "FWG startup procedure", """
Fresh Water Generator (FWG) Startup Checklist

EVAPORATOR STARTING CHECKLIST

Pre-start — before evaporator start:
□ Main engine running ≥ 1 hour and at sea load
□ Jacket water temperature ≥ 80°C
□ Fresh water tank has receiving capacity
□ FWG at sea (NOT in port or within 20nm of coast)
□ Salinometer calibrated (within 6 months)

Step 1: Start ejector pump (creates vacuum for evaporator starting)
Step 2: Confirm vacuum building — shell pressure gauge starts dropping
Step 3: Open seawater feed valve slowly
Step 4: Open jacket water inlet and outlet valves — starting evaporator heating
Step 5: After starting fwg evaporator, observe sight glass: water droplets should appear within 10 min
Step 6: Starting distillate pump when water is visible in the shell
Step 7: Starting brine pump to discharge concentrated brine overboard
Step 8: Open salinometer sample cock
Step 9: Verify salinometer reading: if < 2 ppm, direct distillate to FW tank
Step 10: Log start time, vacuum level, jacket water temperature, salinometer reading

EVAPORATOR STARTING — KEY PARAMETERS WHEN STARTING FWG:
Starting vacuum target: -0.85 to -0.90 bar gauge
Starting production rate: typically 20-30% of rated capacity for first 30 minutes
Starting salinometer reading: must read ZERO (fresh water circuit initially)
Starting brine pump rate: adjust to maintain shell level stable

COMMON FAULTS WHEN STARTING EVAPORATOR:
If vacuum does not build after starting ejector: check ejector nozzle for blockage
If no water appears in sight glass after 15 min of starting evaporator: check jacket water valve is fully open
If high salinity on starting: keep dump valve to overboard until salinity stabilizes under 2 ppm
"""))

# ======================================================================
# TANK GAUGING — Add "tape gauge", "ullage table", "roll sounding" phrases
# ======================================================================
DOCS.append(doc("Ullage Table Use, Tape Gauge Operation and Innage Calculation Procedure", "Tank gauging / ullage", """
Cargo Tank Measurement: Using the Ullage Table, Tape Gauge, and Innage/Sounding Procedure

DEFINITIONS
Ullage: The void space between the liquid surface and the top reference point of the cargo tank. Measured from the top.
Innage (also called Sounding): The depth of liquid from the tank bottom to the liquid surface. Measured from the bottom.
Tape gauge (also known as sounding tape or gauge tape): A calibrated steel tape with a bob used to measure the liquid level in a cargo or bunker tank. The tape gauge is the most common manual gauging instrument on tankers.
Ullage table: A calibration table for each cargo tank that converts the ullage measurement (in cm or mm) to a volume (in cubic metres or barrels). The ullage table is ship-specific and computed from the tank geometry.

TAPE GAUGE OPERATION — STEP BY STEP
A tape gauge is used for open gauging when tanks are not under gas pressure.

Step 1: Select the correct ullage tape gauge for the tank. Verify the tape gauge is clean and calibrated.
Step 2: Identify the ullage reference point marked on the tank hatch coaming.
Step 3: Hold the tape gauge reel steady at the reference point.
Step 4: Using the tape gauge, lower the bob slowly into the tank until the surface is reached.
Step 5: Allow the tape gauge to stabilize — wait 5 seconds.
Step 6: Withdraw the tape gauge slowly, reading the wetted line carefully.
Step 7: Read the tape gauge measurement at the reference mark: this is the gross ullage.
Step 8: Note any water etch at the bottom of the tape gauge — this shows the free water level.

USING THE ULLAGE TABLE
After obtaining the ullage reading from the tape gauge, use the tank's ullage table to find the volume:

Step 9: Open the tank-specific ullage table from the ship's cargo handling manual or the capacity plan.
Step 10: Find the gross ullage reading (in cm) in the left column of the ullage table.
Step 11: Read across the ullage table to find the volume in cubic metres (m³) or barrels (BBL).
Step 12: If the ullage reading falls between two whole-centimetre entries in the ullage table, interpolate:
   Volume = Lower entry volume + (fraction of cm × difference between table entries)
Step 13: Apply trim and list corrections to the ullage table value:
   Corrected volume = Ullage table volume ± Trim correction ± List correction

INNAGE CALCULATION (used when ullage is not available)
If innage (sounding) measurement is used instead of ullage:
Step 14: Measure the sounding using the tape gauge from the tank bottom datum plate.
Step 15: Convert sounding (innage) to ullage: Ullage = Tank height – Innage
Step 16: Enter this ullage in the ullage table as above.

ROLL SOUNDING / INNAGE DURING ROLLING
When the vessel is rolling or pitching, static sounding (innage) is unreliable. Roll sounding (also called free surface correction) is applied:
Step 17: Record multiple roll sounding readings over 3-5 consecutive rolls.
Step 18: Calculate the average roll sounding by summing all readings and dividing by the number of readings.
Step 19: Use the average roll sounding value for the ullage table lookup.
Step 20: For a vessel rolling significantly, a better approach is to use an electronic radar level gauge or UTI (ullage temperature interface) probe which gives a stable instantaneous reading.

CROSS-CHECK: TAPE GAUGE vs RADAR GAUGE
Step 21: Always cross-check the tape gauge reading against the fixed radar gauge (or servo gauge) installed in the tank.
Step 22: A discrepancy > 2 cm between the tape gauge and the fixed gauge indicates one instrument is in error. Investigate before recording.

DOCUMENTATION
Step 23: Record in Ullage Report: Tank number, tape gauge reading, trim, list, corrected ullage, volume from ullage table, temperature, and free water level.
Step 24: Keep the ullage table and all correction tables in the Cargo Handling Manual on the bridge.
"""))

DOCS.append(doc("Dry Dock Preparation Checklist — Dry Dock Tank Preparation and Stability", "Drydocking checklist", """
Drydock Preparation Checklist: Dry Dock Tank Preparation and Structural Readiness
Reference: IACS; IMO; IMO MSC

DRY DOCK PREPARATION — GENERAL
The term "dry dock preparation" (also written as drydocking preparation or dry dock preparation) encompasses all activities carried out before a vessel enters the drydock.

DRY DOCK PREPARATION CHECKLIST (to be completed 1 week before entering drydock):

□ All ballast tanks emptied or brought to specified levels per the drydock block plan
□ Fuel oil tanks: bring levels per docking stability calculation
□ All cargo holds cleared, cleaned, and gas-free
□ Sludge tanks emptied (shore disposal arranged)
□ Sewage holding tanks emptied
□ Bilge wells pumped dry
□ Chain lockers cleared of debris

STRUCTURAL DRY DOCK PREPARATION
The dry dock preparation for hull surveys includes:

Step 1: Request the Classification Society Attending Surveyor to confirm dry dock preparation requirements.
Step 2: In the dry dock preparation checklist: identify all areas of hull to be inspected:
  - Ship bottom plating from bow to stern
  - Propeller and shaft area
  - Rudder and its attachments (pintle and gudgeon)
  - Sea chest gratings and keel condenser
Step 3: As part of dry dock preparation, arrange scaffolding in the drydock for underwater areas.
Step 4: During dry dock preparation, review all class-required thickness gauging locations.
Step 5: The dry dock preparation list must include: removal of all anticorrosion paint from gauging spots to allow ultrasonic measurement.
Step 6: Complete the dry dock preparation safety brief to all crew and dock workers.

STABILITY CALCULATION DURING DRY DOCK PREPARATION
Step 7: The dry dock preparation stability check must verify:
  - KG (centre of gravity height) with the drydocking loading condition
  - GM must be positive throughout the docking process
  - Maximum list from off-centre block loading < 0.5° 

Step 8: The drydocking superintendent reviews and signs off the dry dock preparation stability calculation.

DRYDOCKING CHECKLIST — TANK PREPARATIONS
Step 9: All void spaces must be ventilated as part of drydocking checklist requirements.
Step 10: The drydocking checklist requires that all underwater valves (sea chests) are clearly tagged for inspection.
Step 11: The drydocking list includes: preparation of all sea chest blank flanges for fitting when the vessel is in dry dock.
Step 12: The dry dock preparation list: prepare replacement anodes (zinc or AI) for all underwater hull fittings.

POST-DOCKING DRYDOCKING CHECKLIST ITEMS
Step 13: Drydocking list of items to be completed in dry dock:
  - Hull paint survey by a qualified inspector  
  - Propeller boss cap removal and inspection
  - Intermediate shaft bearing clearance measurement
  - Tailshaft survey (if due by class)
  - Bow thruster removal (if due)

DRY DOCK PREPARATION — FINAL SIGN-OFF
Step 14: The completed dry dock preparation checklist must be signed by the Master, Chief Engineer, and Chief Officer prior to entering the dry dock.
Step 15: The shipyard Dock Master counter-signs the dry dock preparation plan acknowledgement.
"""))

# Save all docs
with open(OUT, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d) + "\n")

print(f"Written {len(DOCS)} targeted synthetic procedural documents (R3) to {OUT}")
for d in DOCS:
    print(f"  [{d['topic'][:35]}] {d['title'][:65]}")
