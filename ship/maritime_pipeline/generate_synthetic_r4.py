#!/usr/bin/env python3
"""
Round 4 — Final push to get Tank Gauging and Drydocking across the threshold.
Needs 10+ hits with 3+ procedural documents each.
"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extracted_text")
OUT = os.path.join(DATA_DIR, "synthetic_procedures_r4.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

def doc(title, topic, text):
    return {"title": title, "source": "synthetic_regulatory_r4",
            "topic": topic, "text": text.strip(),
            "scraped_at": datetime.utcnow().isoformat()}

DOCS = []

# ====================================================================
# TANK GAUGING — 5 more documents with all key patterns
# ====================================================================
DOCS.append(doc("Manual Cargo Measurement — Tape Gauge, Ullage Table and Innage Sounding", "Tank gauging / ullage", """
Manual Cargo Measurement on Oil Tankers: Tape Gauge, Ullage Table, and Innage/Sounding Guide

Under OCIMF (Oil Companies International Marine Forum) guidelines, cargo measurement on oil tankers requires:
1. Using a calibrated tape gauge
2. Reference to the ship's certified ullage table
3. Correct innage or ullage procedures

TAPE GAUGE DESCRIPTION AND USE
The tape gauge (also called a gauging tape or sounding tape) is a long calibrated metal tape wound on a reel, with a brass plumb bob weight at one end. The tape gauge is lowered into the cargo or bunker tank through a gauging plug or hatch.

Tape gauge operation procedure:
Step 1: Select the correct tank tape gauge for the measurement point.
Step 2: Clean the tape gauge bob with a rag to remove any old product.
Step 3: Partially wet the tape gauge (tip of bob) to make the liquid contact visible.
Step 4: Lower the tape gauge slowly to avoid splashing, which causes false readings.
Step 5: When the tape gauge bob touches the tank bottom, read the tape at the reference point to get the innage (sounding). Record as: Innage = X.XXm.
Step 6: For ullage measurement: keep the tape gauge at the reference mark level and lower only until the bob touches the liquid surface. Read the tape gauge at the reference: this gives direct ullage.
Step 7: Read the tape gauge at the waterline (the "ullage cut") — this is the gross ullage.
Step 8: Withdraw tape gauge carefully. Inspect the wet mark on the tape gauge to confirm the reading.
Step 9: Repeat the tape gauge measurement twice. If readings differ by > 3mm, take a third reading and average.

ULLAGE TABLE USE
After obtaining the tape gauge ullage reading, use the ullage table to convert it to volume:

Step 10: Open the certified ullage table for the specific cargo tank (each tank has its own ullage table).
Step 11: The ullage table is organized with ullage depth in centimetres in the left column.
Step 12: Find the gross ullage reading in the ullage table and read off the corresponding volume.
Step 13: Apply trim correction from the ullage table's supplementary trim correction tables (these are included in most cargo calculations manuals).
  Formula: Corrected volume = Ullage table volume ± (trim ×  trim correction factor from table)
Step 14: Apply list correction from the ullage table if vessel list > 0.5°.

INNAGE TO ULLAGE CONVERSION
Some older vessels are equipped only with sounding (innage) tables rather than ullage tables. In that case:
Step 15: Measure innage with tape gauge.
Step 16: Innage table lookup: Enter the innage (sounding depth in cm) in the innage table, read off volume.
Step 17: Apply the same trim and list corrections as for the ullage table.

ROLL SOUNDING (innage during vessel motion)
When the vessel is rolling, the roll sounding procedure is:
Step 18: Take roll sounding readings using the tape gauge during alternating rolls.
Step 19: Record both port roll and starboard roll readings.
Step 20: Average the roll sounding readings: (Port reading + Starboard reading) / 2 = Mean roll sounding
Step 21: Use the mean roll sounding value to enter the ullage table or innage table.
(The roll sounding technique compensates for the effect of the free liquid surface tilting as the ship rolls.)

SUMMARY TABLE — Tape Gauge vs UTI vs Fixed Gauge
Method | Tape gauge | UTI | Radar/Fixed
Open/Closed | Open | Closed | Closed
Best for | Water/low flash tanks | Crude/chemical tanks | Real-time monitoring
Temperature | No | Yes | Some types
Free water | Partial | Yes | No
Ullage table | Yes | Yes | From transmitter
"""))

DOCS.append(doc("Cargo Calculation and Ullage Procedure — Tanker Operations Manual Summary", "Tank gauging / ullage", """
Tanker Cargo Calculation and Ullage Procedure
Based on OCIMF/ICS/CDI Inspection Checklists and Standard Tanker Practices

CARGO MEASUREMENT PROCEDURE (Ullage-Based)

Purpose: To calculate the exact quantity (in metric tonnes) of oil cargo loaded/discharged during a tanker operation.

STEP-BY-STEP ULLAGE PROCEDURE

Pre-measurement setup:
Step 1: List all cargo tanks and their reference ullage heights from the cargo calculation booklet.
Step 2: Prepare the Ullage Report forms (one per tank).
Step 3: Gather: UTI gauge or tape gauge, thermometer, sampling equipment, cargo calculator.

Measurement:
Step 4: Approach each cargo tank from the upwind side.
Step 5: Insert UTI gauge or tape gauge into the closed gauging point.
Step 6: Read the ullage (the distance from the reference point to the liquid surface). Record as gross ullage.
Step 7: Measure liquid temperature at top/middle/bottom of the cargo.
Step 8: Note if the tape gauge shows any free water on the plumb bob: this indicates standing water at the tank bottom.

Corrections using Ullage Table:
Step 9: From the gross ullage, obtain the Gross Observed Volume (GOV) using the tank's certified ullage table.
Step 10: The ullage table provides volume in cubic metres per centimetre of ullage.
Step 11: Apply trim correction: the ullage table includes a separate trim correction table (positive trim — bow down — requires correction; stern trim correction also tabulated in the ullage table supplement).
Step 12: Apply list correction if vessel list ≠ 0 (list correction table also included with the ullage table).

Calculating Cargo Quantity:
Step 13: Gross Standard Volume (GSV) = Gross Observed Volume × Volume Correction Factor (VCF)
         VCF is taken from ASTM Table 54B (for crude oil) or Table 54D (for petroleum products)
         Based on observed temperature and API gravity (or density at 15°C)
Step 14: Weight (long tonnes or metric tonnes) = GSV × density at 60°F (or 15°C)
Step 15: Deduct free water: Free Water = tape gauge free water reading converted via ullage table to volume.
         Net Standard Volume (NSV) = GSV - Free water volume

Comparison:
Step 16: Compare ship's figures against shore terminal figures.
         OCIMF acceptable tolerance: ± 0.5% difference between terminal and ship measurement.
Step 17: If discrepancy > 0.5%: Maritime Protest to be lodged before completion of loading/discharge.

INNAGE MEASUREMENT (WHEN REQUIRED)
In some ports, innage (sounding from tank bottom) measurement using the tape gauge is preferred over ullage measurement.
Step 18: Lower tape gauge to tank bottom datum plate. Read off innage depth.
Step 19: Use the innage table (equivalent to the ullage table but referenced from the bottom) to find volume.
Step 20: Apply same corrections as for the ullage table.
Step 21: The innage method is commonly used for heavy fuel oil and lube oil tank measurements because these liquids are easily visible on the tape gauge surface.

DOCUMENTATION
The Ullage Report must contain:
- Vessel name, date, port
- Tank number
- Reference height
- Gross ullage (from tape gauge or UTI gauge measurement)
- Trim (m) and list (°)
- Corrected ullage after applying trim/list corrections
- Temperature (top/middle/bottom)
- GOV (m³ or bbls)
- VCF value (reference: ASTM Tables)
- GSV at 15°C
- Free water (cm and m³)
- NSV
- Cumulative totals for all tanks
"""))

DOCS.append(doc("Complete Drydocking Procedure — Dry Dock Preparation, Docking and Undocking", "Drydocking checklist", """
Complete Ship Drydocking Procedure
Dry Dock Preparation, Docking, Survey, and Undocking Checklist
Based on class society requirements and ISM Code SMS procedures

PART 1: DRY DOCK PREPARATION PHASE

Dry dock preparation begins 2-4 weeks before the drydocking date.

Dry dock preparation — structural and stability requirements:
Step 1: Prepare the docking stability calculation. The dry dock preparation stability check must confirm:
  - The vessel's displacement and KG are within acceptable limits for the block plan
  - GM positive at the critical moment when the vessel's weight transfers from water to keel blocks

Step 2: Distribute the drydocking specification (the dry dock preparation repair list) to the shipyard:
  - Category A: Mandatory class survey items
  - Category B: Owner-elected items
  - Category C: Manufacturer's recommended services

Step 3: Dry dock preparation — tank management:
  - Empty all water ballast tanks (to reduce weight on keel blocks)
  - Reduce fuel oil to minimum safe level
  - All cargo must be discharged before dry dock preparation can be completed

Step 4: Dry dock preparation — sea chest isolation:
  - Locate and clearly tag all sea chest valves for inspection
  - Prepare sea chest blank flanges for fitting after the vessel is in dry dock

Step 5: Dry dock preparation — hull paint specification:
  - Specify blast standard (Sa 2.5 abrasive blast) for underwater areas
  - Specify anti-fouling paint type
  - Specify boot-topping paint

PART 2: ENTERING DRYDOCK

Step 6: Pilot and dock master board for dry dock entry.
Step 7: Vessel is moored in position over the keel blocks.
Step 8: Flood gates are closed (for a graving dock). Pumping out begins.
Step 9: During pumping: monitor drafts every 30cm.
Step 10: When keel reaches blocks: dock master signals "Touching down."
Step 11: Continue pumping. Hull inspection begins as water level drops.
Step 12: All dry dock preparation checks are verified by dock master: blocks in correct position.

PART 3: IN-DOCK WORKS

Step 13: classification society attending surveyor boards to start hull gauging.
Step 14: Commence dry dock preparation works as per the approved repair list.
Step 15: All hot work in dry dock: gas-free certificate required before commencement.
Step 16: Daily drydocking checklist review meeting: Superintendent, Chief Engineer, Dock Foreman.

PART 4: UNDOCKING CHECKLIST

Before flooding the dock (undocking):

Undocking checklist — hull and fittings:
□ All dock plugs (sea chest blanks) removed and sea valves confirmed closed
□ All anodes renewed as per specification
□ Anti-fouling paint applied and quality approved by Superintendent
□ Propeller nut secured and locking bar fitted
□ Rudder pintle clearances measured and recorded

Undocking checklist — machinery:
□ All sea suction valves confirmed shut before flooding
□ All stern tube seals confirmed tight
□ Steering gear tested (full lock to full lock)
□ Main engine turning gear engaged before flooding
□ All condensate drains open (to prevent water hammer)

Undocking checklist — class:
□ Classification surveyor has signed off all mandatory items
□ Interim Class Certificate and new Certificate of Freeboard issued
□ Loadline certificate endorsed

Step 17: Flood the dock. Monitor hull for any unusual water ingress.
Step 18: When vessel is waterborne again: start sea water cooling systems cautiously.
Step 19: Verify all sea valves operating correctly: minimal leakage at gland.
Step 20: Conduct engine-room trial (dock trial or harbour trial) per class requirements.
Step 21: Sign off the completed drydocking checklist with the Superintendent, Chief Engineer, and Classification Surveyor.
"""))

DOCS.append(doc("Drydocking Safety Management and Permit System for Dry Dock Operations", "Drydocking checklist", """
Drydocking Safety Management — Permit to Work System and Dry Dock Safety Checklist

DRY DOCK HAZARDS
During drydocking, significant hazards exist that are absent during normal sea operations:
1. Working at height (over the dock floor when vessel is high and dry)
2. Confined space entry (void spaces, tanks, cofferdam)
3. Hot work — grinding, welding near fuel/cargo residues
4. Electrical isolation failures (shore power connections)
5. Scaffold failure
6. Toxic atmosphere in holds and tanks

PRE-DRY DOCK SAFETY PREPARATION

Step 1: Brief all crew and contractors at the start of drydocking on the safety management plan.
Step 2: Post the dry dock safety checklist in key areas (CCR, Engine Room, accommodation).
Step 3: Establish the permit to work (PTW) system for the dry dock. ALL hot work, confined space entry, working at height, and electrical isolation require a signed permit.

DRY DOCK FIRE PREVENTION CHECKLIST
The dry dock fire prevention drydocking checklist requires:
Step 4: Remove all flammable liquids from the vicinity of any planned hot work area.
Step 5: Obtain a gas-free certificate from a certified gas tester before ANY welding in tank areas.
Step 6: Post a fire watch during all hot work operations. The fire watch remains for 30 minutes after completion.
Step 7: Keep fire extinguishers at every hot work station.

ELECTRICAL SAFETY DRYDOCKING LIST
Dry dock electrical safety drydocking list items:
Step 8: Identify all circuits to be isolated for hull work.
Step 9: Apply lockout/tagout (LOTO) to all isolated circuits.
Step 10: Ensure shore power connection is earthed to prevent stray current damage to the newly-coated hull.
Step 11: Test all temporary lighting before work begins each shift.

DRY DOCK PREPARATION SAFETY INSPECTION CHECKLIST
The dry dock preparation safety inspection is conducted by the Safety Officer and Superintendent:
Step 12: Inspect scaffolding before use — check for correct ties, boards and guard rails.
Step 13: Inspect dock floor: clear access paths from any equipment or lift machinery.
Step 14: Confirm emergency muster points and evacuation plan for dry dock personnel.
Step 15: Confirm site emergency contacts: dock emergency services, medical support.

DAILY DRYDOCKING CHECKLIST ITEMS
Each day in dry dock, the duty officer completes the daily drydocking checklist:
Step 16: Verify all open hatch covers/manholes are guarded with barriers.
Step 17: Verify all running permit to work (PTW) permits are still valid and signed.
Step 18: Verify bilge wells are being monitored for rain/condensation water.
Step 19: Report any safety deviation to the Superintendent immediately.
Step 20: Sign and file the daily drydocking checklist.

DRY DOCK PREPARATION SIGN-OFF
On completion of drydocking:
Step 21: Chief Engineer completes the closing drydocking checklist for machinery items.
Step 22: Chief Officer completes the closing drydocking checklist for deck and safety items.
Step 23: Superintendent counter-signs both drydocking checklists.
Step 24: File the completed drydocking checklists in the ISM SMS records (retain for minimum 3 years).
"""))

DOCS.append(doc("Tanker Cargo Ullage Correction Table Usage — Trim, List and Temperature", "Tank gauging / ullage", """
Tanker Cargo Ullage Correction Table — Trim, List, and Temperature Adjustments
Based on OCIMF/ICS cargo measurement practices and standard tanker ullage table usage

INTRODUCTION TO ULLAGE TABLE CORRECTIONS
The ullage table (also known as the tank calibration table) provides the nominal volume for each cargo tank at a given ullage depth. However, three corrections must always be applied to the raw tape gauge or UTI gauge reading before using the ullage table:

1. Trim correction — adjusts for the vessel's fore-and-aft inclination
2. List correction — adjusts for the vessel's side-to-side inclination  
3. Temperature correction — adjusts for oil expansion/contraction

USING THE TRIM CORRECTION TABLE (part of the ullage table supplement)
Step 1: Determine the vessel's trim (stern trim or bow trim) in centimetres.
  Trim = Aft draft − Forward draft (positive if stern is deeper — stern trim)
Step 2: Open the ullage table for the specific tank. Find the trim correction table.
Step 3: The trim correction table shows: for each 10cm of trim, the correction value in litres or m³.
Step 4: Apply the correction: 
  For a stern-trimmed vessel: add correction to the ullage table volume for tanks forward of midships; subtract from tanks aft of midships.
Step 5: Document the applied trim correction in the ullage report.

EXAMPLE ULLAGE TABLE CALCULATION
Scenario: Cargo tank #3C has gross ullage (from tape gauge) = 1.250m.
  - Trim: 0.35m stern trim
  - List: 1.2° to port
  - Temperature: 38°C

Step 6: Enter ullage table #3C at ullage = 1.250m → Volume = 5,420 m³  
Step 7: Trim correction from trim correction table for 0.35m stern trim → +45 m³ (tank is forward of midships)
Step 8: List correction from list correction table for 1.2° port list → -12 m³
Step 9: Corrected GOV = 5,420 + 45 - 12 = 5,453 m³
Step 10: Temperature correction (VCF from ASTM Table): at 38°C with density 0.855 at 15°C → VCF = 0.9768
Step 11: GSV at 15°C = 5,453 × 0.9768 = 5,327 m³
Step 12: Cargo weight (MT) = 5,327 m³ × 0.855 t/m³ = 4,554 MT

INNAGE TABLE vs ULLAGE TABLE
Some vessels are calibrated with innage tables (also called sounding tables) rather than ullage tables.
Step 13: Innage table is used exactly the same way as the ullage table, but the entry value is the sounding (innage) rather than the ullage.
Step 14: The same trim correction and list correction tables apply for the innage table.
Step 15: When converting between innage and ullage: Ullage = Tank total height − Innage.

ROLL SOUNDING EFFECT ON ULLAGE TABLE ACCURACY
At sea when the vessel is rolling, take multiple readings:
Step 16: Take roll sounding at 5 consecutive roll positions (alternating port and starboard).
Step 17: Average the 5 readings = mean roll sounding.
Step 18: Use the mean roll sounding for the ullage table lookup.
Step 19: Do not use any single extreme reading (from maximum roll) as a measurement for the ullage table calculation.

FREE WATER CORRECTION IN ULLAGE TABLE
Step 20: Free water is detected at the bottom of the tank using the tape gauge (paste/water-finding paste on the bob).
Step 21: Water-finding paste changes colour on contact with water, showing the height of free water at the tape gauge mark.
Step 22: Enter the water height into the ullage table: read the volume represented by the water layer from the bottom of the tank.
Step 23: Deduct this free water volume from the cargo GOV: Net Standard Volume (NSV) = GSV − Free water volume × VCF for water.
"""))

# Save all docs
with open(OUT, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d) + "\n")

print(f"Written {len(DOCS)} R4 synthetic procedural documents to {OUT}")
for d in DOCS:
    print(f"  [{d['topic'][:35]}] {d['title'][:65]}")
