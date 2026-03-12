#!/usr/bin/env python3
"""
Additional synthetic procedure documents — Round 2.
Targeting specifically the 6 remaining weak topics with multiple documents each.
"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extracted_text")
OUT = os.path.join(DATA_DIR, "synthetic_procedures_r2.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

def doc(title, topic, text):
    return {"title": title, "source": "synthetic_regulatory_r2",
            "topic": topic, "text": text.strip(),
            "scraped_at": datetime.utcnow().isoformat()}

DOCS = []

# ======================================================================
# CRUDE OIL WASHING — Additional procedures
# ======================================================================
DOCS.append(doc("COW (Crude Oil Washing) Pre-Operation Checklist and IG Monitoring", "Crude oil washing procedure", """
Crude Oil Washing Pre-Operation Safety Checklist
Reference: MARPOL Annex I Reg 33; ISGOTT 5th Edition; UK MAIB Safety Bulletins

PRE-COW SAFETY VERIFICATION
Before commencing crude oil washing (COW) procedure on any cargo tank:

Step 1: Verify inert gas (IG) system functionality. Start the IG fan and confirm IG supply pressure.
Step 2: Measure oxygen (O₂) content in all tanks to be crude washed. O₂ must be ≤ 8% by volume.
Step 3: Open the IG supply valve to the COW tanks. Ensure slight positive pressure (25–100 mm WG).
Step 4: Check all portable gas detectors for calibration (within 6-month calibration date).
Step 5: Inspect all fixed tank washing machines (TWM) for correct installation and freedom of rotation.
Step 6: Ensure COW washing line manifold valves are closed initially.
Step 7: Verify slop tank has sufficient capacity to receive wash residues.
Step 8: Check crude oil wash pressure at machine nozzle: typically 8–12 bar per maker's specification.
Step 9: Confirm COW operations manual is available on bridge and in cargo control room (CCR).
Step 10: Notify Chief Officer and OOW that COW will commence.
Step 11: Record in cargo log: start time, tanks to be washed, O₂ reading at start.

DURING COW OPERATION — CONTINUOUS MONITORING
Step 12: Monitor O₂ content every 30 minutes during crude oil washing. Stop COW if O₂ rises above 8%.
Step 13: Monitor inert gas pressure continuously: must remain positive throughout.
Step 14: Observe the cargo pump suction. Loss of suction indicates tank is approaching empty — reduce TWM flow accordingly.
Step 15: Verify TWM rotation by checking the rotation monitors on tank top.
Step 16: Monitor weather deck: no crew should remain on deck unnecessarily during COW.
Step 17: Record all COW activity in the Oil Record Book (ORB) Part I, under Code E (Tank Cleaning).

POST-COW PROCEDURE
Step 18: Close all COW machine supply valves.
Step 19: Drain the COW wash lines and manifold to slop tank.
Step 20: Take final UTI readings in washed tanks to confirm effective residue removal.
Step 21: Complete ORB Part I entries: tank numbers, COW duration, quantity of crude oil used for washing, final residue level.
Step 22: Record shutdown time. Sign and have the Master countersign the ORB entries.
Step 23: Notify terminal representative that COW is complete.
"""))

DOCS.append(doc("Crude Oil Washing Troubleshooting Guide", "Crude oil washing procedure", """
Crude Oil Washing (COW) — Common Problems and Corrective Actions
Based on ISGOTT, OCIMF Guidelines, and Class Survey Records

PROBLEM 1: High O₂ Content in Tank During COW
Symptoms: O₂ reading > 8% despite IG system operating
Cause and action:
Step 1: Immediately stop crude oil washing. Close COW supply valve.
Step 2: Check IG system for faults: verify IG blower running, check O₂ meter in IG main line.
Step 3: Verify that all tank openings (ullage hatches, gauging ports) are closed.
Step 4: Purge the tank with IG until O₂ drops below 8%.
Step 5: Do not restart COW until O₂ < 8% confirmed.

PROBLEM 2: Loss of COW Pump Suction
Symptoms: Pump flow drops, discharge pressure fluctuates
Cause and action:
Step 6: Reduce TWM supply flow rate.
Step 7: Check cargo control room for tank level. Tank may be running low.
Step 8: Switch COW operation to a tandem-stripping mode — use cargo pump for stripping while continuing COW from another source.
Step 9: Ensure stripping line is open. Verify stripping pump is operational.

PROBLEM 3: TWM Not Rotating
Symptoms: No rotation visible on rotation monitor; sound changes
Cause and action:
Step 10: Check TWM supply pressure. Minimum pressure needed for rotation: consult TWM maker data.
Step 11: Try cycling the supply valve (close then reopen) to clear any blockage.
Step 12: If still not rotating: shut off tank supply. Do not force rotation manually.
Step 13: Record TWM malfunction in the maintenance log.
Step 14: Continue COW with remaining operational TWMs.

PROBLEM 4: COW Line Leak
Symptoms: Oil noticed on tank top or at manifold during COW operation
Cause and action:
Step 15: Stop COW immediately. Close COW supply valve.
Step 16: Alert deck department. Assign crew with portable boom to contain any deck spill.
Step 17: Depressurize the COW washing line.
Step 18: Locate leak source: check all flange connections, valve packing, and hose coupling points.
Step 19: Repair the leak with the tank NOT under COW pressure.
Step 20: Test the repaired connection at low pressure before resuming COW.
"""))

# ======================================================================
# FWG — Additional procedures
# ======================================================================
DOCS.append(doc("Fresh Water Generator — Maintenance Procedure and Fault Diagnosis", "FWG startup procedure", """
Fresh Water Generator (FWG) Maintenance and Fault Diagnosis Procedure
Applicable to: Plate-type evaporators and shell-and-tube type FWGs

PLANNED MAINTENANCE PROCEDURE (PMS-triggered, typically every 1000 operating hours)

Step 1: Stop the FWG following the normal shutdown procedure.
Step 2: Isolate all jacket water valves (inlet and outlet). Apply lockout tags.
Step 3: Drain the evaporator shell of residual water using the drain cock at the bottom.
Step 4: Open the evaporator access cover (requires unbolting of the shell).
Step 5: Inspect the heating plates or tubes for:
  - Scale/fouling (whitish or brownish deposit on heating surfaces)
  - Corrosion or erosion
  - Tube/plate cracking or deformation
Step 6: Measure evaporator plate/tube fouling thickness. If > 2 mm scale deposit, proceed with chemical cleaning.

CHEMICAL CLEANING PROCEDURE (Descaling)
Step 7: Prepare citric acid cleaning solution: typically 5-10% w/v citric acid in fresh water.
Step 8: Ensure all valves to the potable water system are closed. Fresh water tank must not be connected during cleaning.
Step 9: Fill the evaporator shell with the citric acid solution via the drain connection (closed loop).
Step 10: Circulate the acid solution using the distillate pump for 4-6 hours.
Step 11: Monitor the pH of the circulating solution every hour. Start pH ≈ 2.5–3.5; solution is exhausted when pH rises above 5.
Step 12: Drain the acid solution completely.
Step 13: Flush the evaporator with clean fresh water at least 3 times until neutral pH (pH 7).
Step 14: Inspect all plates/tubes for cleanliness.
Step 15: Replace gaskets if any sign of deterioration.
Step 16: Reassemble the evaporator access cover. Verify all bolts are tightened to maker's torque specification.
Step 17: Record in PMS: date, type of cleaning, quantity of acid used, post-cleaning salinity test result.

FAULT: FWG NOT PRODUCING SUFFICIENT DISTILLATE
Step 18: Check shell vacuum. If vacuum < 0.8 bar gauge, check ejector pump, nozzle wear, and air leaks.
Step 19: Check jacket water inlet temperature. Must be ≥ 82°C for effective evaporation at sea.
Step 20: Check seawater feed flow. Insufficient seawater feed = insufficient cooling = poor vacuum.
Step 21: Check for scaling on heating surfaces. Even mild scaling reduces heat transfer significantly.
Step 22: Verify brine pump is operating correctly — if brine level rises, heat transfer is impaired.

FAULT: SALINITY ALARM (>2PPM) DURING NORMAL OPERATION
Step 23: Open dump valve immediately to direct any distillate overboard (not to freshwater tank).
Step 24: Check for carry-over: observe sight glass for high water level in vapour space.
Step 25: Reduce evaporation rate by throttling jacket water inlet.
Step 26: Check demister pad condition. Fouled demisters cause water carry-over.
Step 27: If salinometer itself may be faulty: verify with a separate conductivity meter or test kit.
"""))

DOCS.append(doc("Fresh Water Generator — Operational Log and Performance Monitoring", "FWG startup procedure", """
Fresh Water Generator Operational Performance Monitoring
Reference: SMS and ISM Code Planned Maintenance System (PMS) Requirements

FWG OPERATING LOG — PARAMETERS TO RECORD (every 4 hours during operation)
The following parameters must be recorded in the Engine Room Log or FWG Run Log:
  1. Date and time
  2. FWG in operation: Yes/No
  3. Shell vacuum / absolute pressure (mbar or bar abs)
  4. Jacket water inlet temperature (°C)
  5. Jacket water outlet temperature (°C)
  6. Seawater inlet temperature (°C)
  7. Seawater outlet temperature (°C)
  8. Brine level indicator reading
  9. Distillate production rate (litres/hour or tonnes/day)
  10. Salinometer reading (ppm)
  11. Freshwater tank level (percent full or metres)
  12. Running hours since last maintenance

PERFORMANCE BENCHMARKS
Step 1: Compare actual distillate production to design capacity (typically stated on FWG nameplate in tonnes/day at a reference jacket water temperature).
Step 2: Performance ratio = (Actual production / Design capacity) × 100%. Alert maintenance if ratio < 80%.
Step 3: Monitor heat transfer coefficient trend. As scaling increases, jacket water outlet temperature increases (less heat transferred to the evaporating water).
Step 4: Plot vacuum vs. production rate over running hours. Progressive vacuum degradation indicates ejector nozzle wear.

FRESH WATER TANK MANAGEMENT
Step 5: Test fresh water from the FWG daily using a portable test kit:
  - Total Dissolved Solids (TDS) — should be < 2 ppm
  - pH — should be 6.5–8.5
  - Chlorine residual (if disinfection system fitted) — should be 0.2–0.5 ppm free chlorine
Step 6: Maintain freshwater tank chlorination per WHO shipboard water quality requirements.
Step 7: Log FW tank test results in the potable water log.
Step 8: If TDS or biological contamination found: drain and disinfect the tank before returning to service.

SHUTTING DOWN FWG FOR PORT ENTRY
Step 9: FWG must NOT operate within 20 nautical miles of coastline (WHO shipboard water guideline). Shut down FWG before this point.
Step 10: Switch fresh water supply to port water or stored tank. Verify port water quality before use.
Step 11: Record shutdown time in log.
"""))

# ======================================================================
# APEM PASSAGE PLANNING — additional docs
# ======================================================================
DOCS.append(doc("Passage Planning — Chart Work Procedure and Clearing Bearings", "APEM passage planning", """
Passage Planning — Practical Chart Work and Clearing Bearings
Based on IMO Res A.893(21); NP5 Admiralty Manual of Navigation; MCA Navigation Guidance

CHART PRE-USE CHECKLIST
Step 1: Obtain the latest corrected charts for the planned voyage, cross-referenced with the relevant NtMs (Notices to Mariners) and Admiralty Chart 5011.
Step 2: Verify the chart publication date and last NtM correction number against the vessel's chart correction log.
Step 3: For ECDIS: confirm ENC (Electronic Navigational Chart) cell versions match the latest issued edition. Check the AVCS update is current.
Step 4: Identify the largest-scale chart available for all port approaches, anchorages, and coastal transits. These must be used when in those areas.

LAYING OFF THE TRACK
Step 5: Lay off the track (intended route) using a sharp pencil and parallel ruler. Do not use ink.
Step 6: Mark waypoints at all significant turning points. Number them sequentially (WP001, WP002, etc.).
Step 7: Calculate true course for each leg:
  Course = Bearing from WP to next WP (measured from True North on chart using protractor or parallel ruler)
Step 8: Apply variation to obtain Magnetic course:
  Magnetic course = True course ± Variation (East variation: subtracts; West variation: adds)
  (Mnemonic: "Error East compass least, Error West compass best")
Step 9: Note deviation from deviation card for the applicable heading to obtain Compass course.
Step 10: Calculate the distance of each leg using the longitude scale (1' = 1 nautical mile only on the latitude scale).

WHEEL OVER POSITIONS
Step 11: Calculate the advance and transfer for each turn based on the vessel's maneuvering data (wheel-over point trials or shipbuilder's data).
Advance = distance ship travels ahead from when the helm is applied until she is on the new course
Transfer = lateral distance ship moves from the original track
Step 12: Mark the wheel-over position (WOP) on the chart: this is the position the ship must be at when the helm ORDER is given for each course alteration.

CLEARING BEARINGS AND CLEARING DISTANCES
Step 13: For each hazard (rocks, shoals, headlands) along the route, draw a clearing line:
  - A clearing bearing: a compass bearing from which the hazard is just not visible
  - The track is safe as long as a specific landmark remains greater than (or less than) a specific bearing
Step 14: Example: "Keep X lighthouse bearing NOT LESS THAN 270°T to clear the reef on the west side."
Step 15: Mark clearing bearings prominently on the chart in red.
Step 16: Draw no-go areas (areas of water below the ship's safety depth contour) shaded in red or green cross-hatching.

TIDAL WINDOW PLANNING
Step 17: For a tidal approach, calculate the tidal window:
  Available water depth = Chart datum depth + Tidal height at time of transit
  Required water depth = Ship's maximum draft + UKC (Under Keel Clearance — minimum 10% of draft or per port requirements)
Step 18: Calculate ETAs for the approach to ensure arrival within the tidal window.
Step 19: Include a contingency plan if ETA changes (e.g., anchor in a safe anchorage and wait for the next tidal window).

VOYAGE PLAN — WRITTEN SUMMARY SHEET
Step 20: Produce a voyage plan summary sheet including:
  - All waypoints with lat/long, planned course and distance
  - ETAs at each waypoint (based on planned speed)
  - Tidal information for constricted ports/approaches
  - Weather forecast considerations
  - Risk areas (traffic separation, restricted waters) highlighted
  - Emergency plans: diversion ports, anchor positions, pilot embarkation points
Step 21: Submit the voyage plan to the Master for approval before departure.
Step 22: Keep a copy on the bridge. Distribute relevant sections to the Engine Room (expected maneuver times).
"""))

DOCS.append(doc("Passage Planning — ECDIS Route Validation and Cross-Checking Procedure", "APEM passage planning", """
ECDIS Route Validation and Anti-Grounding Procedure
Reference: MSC.1/Circ.1503 ECDIS Guidelines; Admiralty ECDIS Best Practice Guide; MCA MGN 379

ECDIS ROUTE CREATION PROCEDURE
Step 1: Create a new route in ECDIS. Name it with voyage reference number and date.
Step 2: Enter all waypoints using coordinates from the paper chart plan OR by clicking on the ECDIS display (use the largest scale ENCs available for each area).
Step 3: Set the safety contour in ECDIS to the vessel's maximum permitted safety depth:
  Safety contour = Ship's maximum draft + Minimum safe UKC
  Example: 9.5m draftt + 1.5m UKC = 11m safety contour
Step 4: Set the safety depth display: ECDIS shows areas shoaler than this in a distinct colour (typically blue vs white/grey).

ROUTE VALIDATION CHECKS
Step 5: Run the ECDIS automatic route check. The system will flag:
  □ Anti-grounding check: any waypoint or track segment that crosses the safety contour
  □ Traffic separation scheme violations
  □ Restricted zone crossings (military zones, marine reserves)
  □ Special areas (ECA, MARPOL special areas)
  □ No-go areas (areas shallower than safety contour)
Step 6: For each flag/alarm raised: investigate and either re-route or justify the flag in the voyage plan.
Step 7: If the track crosses the safety contour: re-route the passage or confirm that the area was surveyed to a reliable standard and the actual depth is safe (check source accuracy indicator S-57 category).

CROSS-CHECKING ECDIS WITH PAPER CHARTS
Step 8: Even if the vessel is ECDIS-primary, the responsible officer must:
  - Cross-reference the ECDIS planned track against the equivalent paper chart
  - Verify that critical waypoints and hazards match between ECDIS and paper chart
  - Check for any chart discrepancy (e.g., different datum between ECDIS and paper) and apply datum shift if needed
Step 9: Check ENC quality indicators: some ENCs are sourced from old surveys. Where ENC source data is older than 1980 or survey reliability is low, treat with extra caution and add extra UKC.

ECDIS LOOK-AHEAD AND ALARM SETTINGS
Step 10: Set the ECDIS look-ahead alarm: typically 6-12 minutes ahead of the vessel's current position. This alerts watch officers before the vessel approaches a hazard.
Step 11: Set the cross-track alarm: acceptable deviation from planned track (typically 0.1–0.3 nm in open water; 0.05 nm in coastal waters).
Step 12: Enable the guard ring/zone alarm: additional buffer zone around the vessel.
Step 13: Test all ECDIS alarms and confirm they sound in the helmsman's position and at the OOW's position.

MONITOR PHASE — CONTINUOUS ECDIS MONITORING AT SEA
Step 14: Position fix and comparison: at each position fix interval, compare the ECDIS GPS-derived position with an independent fix:
  - Radar range and bearing to a charted object (≤ 6nm range)
  - Visual bearing (transit) if landmarks available
  - Celestial fix (where practical)
Step 15: If ECDIS position and independent fix differ by > 0.1 nm: stop trusting ECDIS automatically. Investigate (check GPS signal quality, datum, other satellites).
Step 16: Record all position fixes in the deck logbook: time, method, position, and any discrepancy.
Step 17: Pan the ECDIS display ahead of the vessel to continuously look for hazards on the next 30-60 minutes of track.
Step 18: Never zoom into the ECDIS to the point where the scale becomes unreliable (ECDIS warns when using overscale display — treat this seriously: depth soundings may not display at very large scale).
"""))

# ======================================================================
# DRYDOCKING — Additional procedures
# ======================================================================
DOCS.append(doc("Drydocking — Complete Pre-Docking Survey Preparation Checklist", "Drydocking checklist", """
Pre-Drydocking Survey Preparation Checklist
Reference: IACS Requirements; DNV/LR/BV Classification Society Survey Requirements; ISM Code

DOCUMENTS TO PREPARE (typically 4-8 weeks before docking)
Step 1: Assemble the Classification Survey Status Report:
  - List all outstanding conditions of class
  - Identify all surveys due (special survey 5-year, intermediate 2.5-year, annual)
  - List all Class memoranda and recommendations
Step 2: Prepare the Drydock Specification (Repair List):
  Category A — Class mandatory items (must be done for class certificate validity)
  Category B — Owner-elected items (additional repairs desired)
  Category C — Maker recommendations (manufacturer service bulletins)
  Category D — Port State requirements (Flag State or PSC outstanding items)
Step 3: Compile Hull Survey records:
  - Last thickness measurement gauging records (EM gauging history)
  - Any known areas of wastage or pitting identified on last special survey
  - Hull painting records: last blast and paint date, paint type
Step 4: Prepare propeller records:
  - Propeller cavitation damage record (photographs)
  - Blade pitch measurements
  - Propeller boss clearance measurements
  - Stern tube oil analysis history

HULL STRUCTURAL ITEMS (to be included in repair list)
Step 5: List all areas of reported hull wastage (from previous voyage ultrasonic gauging):
  - Deck plates (especially under cargo hatch covers)
  - Ballast tank frames and brackets
  - Shell plating areas of known corrosion
Step 6: Identify areas requiring re-coating:
  - Internal ballast tank: specify blast standard (Sa 2.5 for full blast) and paint spec
  - Bottom: specify full blast + anti-fouling paint type (TBT-free, silicone-based, etc.)
  - Boot-topping area: specify treatment
Step 7: List all sea chest maintenance items:
  - Anodes to be replaced (zinc or aluminium anodes)
  - Sea suction strainers to be cleaned and inspected
  - Echo sounder transducer inspection
  - Speed log transducer inspection

PROPULSION AND STEERING MACHINERY
Step 8: Stern tube survey items:
  - Aft seal and forward seal to be opened and inspected
  - Check running clearances of shaft within stern tube (max acceptable wear per class)
  - Propeller shaft withdrawal if due (every 5 years for special survey)
  - Check propeller boss for cracks (dye penetrant test)
Step 9: Rudder survey items:
  - Rudder stock clearance measurement (top and bottom)
  - Visual inspection of pintle and gudgeon
  - Check rudder coupling bolts torqued to specification
  - Test steering gear hydraulic system for leaks: extend to maximum lock both ways
Step 10: Main engine items (if due):
  - Crankshaft deflection readings (pre-dock and post-dock)
  - Piston overhaul if in PMS
  - Turbocharger overhaul

SAFETY SYSTEM SURVEYS
Step 11: Fire detection and suppression:
  - Test all fire detectors (smoke, heat, optical) — complete list by zone
  - Test CO2 (or gas) total flooding system: verify release mechanism without actual release
  - Overhaul all fire hydrants and hoses
  - Inspect fire pump pressure
Step 12: LSA items due for class survey:
  - Lifeboat release mechanism annual service
  - Liferaft hydrostatic release unit (HRU) replacement if expired
  - EPIRB battery and hydrostatic release service
  - Pyrotechnic inventory replacement if expired

DOCKING PLAN
Step 13: Provide shipyard with:
  - Keel block plan showing acceptable keel block positions (from stability booklet)
  - Maximum weight distribution for dock blocks
  - Sea chest locations for dock plug requirements
  - Prohibited areas where blocks cannot be placed
Step 14: Prepare undocking stability calculation. Verify KG within limits for undocking with anticipated fuel and ballast condition.
Step 15: Submit all items to Classification Surveyor's representative for pre-approval before arrival at drydock.
Step 16: Record in engine room log: date sent and confirmation receipt from class surveyor.
"""))

# ======================================================================
# TANK GAUGING — Additional procedures
# ======================================================================
DOCS.append(doc("Bunker Tank Gauging and Fuel Oil Density Measurement", "Tank gauging / ullage", """
Bunker Tank Gauging and Fuel Oil Quantity Calculation
Reference: MARPOL Annex VI; IMO MEPC.182(59); OCIMF Recommendations

PURPOSE
Accurate bunker tank gauging is required to:
1. Accurately determine fuel quantity on board (FOOB) for port state inspections and for voyage planning
2. Verify delivered bunker quantities against the BDN (Bunker Delivery Note)
3. Comply with MARPOL/IMO fuel consumption reporting (IMO DCS, EU MRV)

BUNKER MEASUREMENT PROCEDURE
Step 1: Check all tank sounding points are accessible and clear of cargo/stores.
Step 2: Use a calibrated steel measuring tape (sounding tape) marked in centimetres, with a plumb bob weight.
Step 3: Check that the measuring tape has a distinct "wet/dry" line visible when withdrawn from the tank. Pre-wet tape slightly to enable easier reading.
Step 4: Lower the tape through the sounding pipe until the bob touches the tank bottom (or the datum plate if there is oil residue at the bottom).
Step 5: Wait 5-10 seconds for the reading to stabilize (fuel is viscous — takes time to show clearly).
Step 6: Withdraw the tape. Read the level at the wet/dry interface to the nearest mm.
Step 7: Record the GROSS SOUNDING on the Sounding Report (example: 2.345 m).

CORRECTION FOR TRIM AND LIST
Step 8: If the vessel has trim (head or stern), apply the trim correction from the tank's individual sounding/capacity table:
  Corrected sounding = Gross sounding ± Trim correction (from table)
  (Tables show correction for each metre of trim, bow up and bow down)
Step 9: If the vessel has list (L° or starboard), apply list correction similarly from sounding tables.

CALCULATING VOLUME
Step 10: Using the corrected sounding, enter the tank's ullage/sounding capacity table to find the volume in cubic metres (m³) or litres.
Step 11: These tables are ship-specific (each tank is calibrated individually). Use the Trim and Stability Booklet table for the specific tank.

CALCULATING WEIGHT (METRIC TONNES)
Step 12: Obtain the fuel oil density at 15°C from the BDN (for last delivered bunker) or from log. Typical HFO density: 0.990–0.995 kg/litre; VLSFO: 0.870–0.900 kg/litre.
Step 13: Apply the temperature correction to the volume:
  Corrected volume = Observed volume × Volume Correction Factor (VCF)
  (VCF from ASTM tables: based on observed temperature and density at 15°C)
Step 14: Calculate weight (metric tonnes):
  Weight (MT) = Corrected volume (litres) × Density at 15°C (kg/litre) / 1000
  OR  
  Weight (MT) = Corrected volume (m³) × Density at 15°C (tonne/m³)

FUEL OIL RECORD BOOK REPORTING
Step 15: Record all soundings in the Ship's Fuel Oil Record Book (FORB) as required by international convention.
Step 16: Enter total fuel oil on board (FOOB) calculation in the voyage report for IMO DCS fuel consumption reporting.
Step 17: Compare ship's calculated figures against BDN quantity. Acceptable discrepancy per OCIMF: ± 0.5% of BDN quantity.
Step 18: If discrepancy > 0.5%: protest the BDN by noting the discrepancy in writing to the supplier before signing.

BALLAST WATER GAUGING
Step 19: Ballast tanks are gauged by the same method. Use fresh water correction if the water is fresh (density 1.000) vs salt water (density 1.025).
Step 20: Calculate ballast weight using the relevant ballast tank sounding tables.
Step 21: Enter ballast quantity in the Ballast Water Record Book (BWRB) as required by Ballast Water Management Convention (BWM Convention D-2 regulation).
"""))

DOCS.append(doc("Ullage Measurement Using UTI (Ullage Temperature Interface) Probe", "Tank gauging / ullage", """
UTI (Ullage Temperature Interface) Gauging Procedure — Oil Tankers
Based on OCIMF/ICS International Safety Guide for Oil Tankers and Terminals (ISGOTT)

EQUIPMENT DESCRIPTION
The UTI (Ullage Temperature Interface) measuring device is a portable closed-gauge instrument used for:
  1. Measuring cargo ullage (distance from reference point to liquid surface)
  2. Measuring liquid temperature at multiple levels (top/middle/bottom)
  3. Detecting water/oil interface level (free water level at tank bottom)

PRE-USE EQUIPMENT CHECKS
Step 1: Verify the UTI tape measure is calibrated (certification label showing last calibration date within 12 months).
Step 2: Check that the temperature sensors and interface detector are functional by testing in a known reference liquid before use.
Step 3: Ensure the UTI reel is fully wound and the tape is not kinked or damaged.

GAUGING PROCEDURE
Step 4: Identify the ullage reference point on the tank (marked point from which all ullage measurements are taken).
Step 5: Open the closed gauge port — this is a small weighted valve fitting on the tank top that allows the probe to enter without releasing vapour.
Step 6: Insert the UTI probe through the gauging slot. Allow the probe to hang free.
Step 7: Lower slowly — 1–2 m per minute maximum — watching the tape markings carefully.
Step 8: When the interface detector contacts the liquid surface, the audio/visual indicator (beeper/lamp) activates.
Step 9: Read the tape at the reference point to obtain the ULLAGE (distance from reference to surface).
Step 10: Record on the Ullage Report: Gross ullage = X.XXX m (to nearest mm).

TEMPERATURE MEASUREMENT
Step 11: Continue lowering the UTI to the cargo temperature measurement points (typically top/middle/bottom of tank = 1/6, 3/6, 5/6 of cargo height).
Step 12: Pause at each level for 2-3 minutes to allow temperature probe to equilibrate.
Step 13: Record temperature at each level (°C). Calculate average temperature:
  T average = (T top + T middle + T bottom) / 3

FREE WATER INTERFACE
Step 14: Continue lowering the UTI until the interface detector signals the water layer beneath the oil.
Step 15: Record the depth from the reference point to the oil/water interface. This allows calculation of free water volume.
Step 16: Calculate free water ullage = reference point height - water interface depth.
Step 17: Convert to free water volume using the tank calibration table = free water level.

POST-GAUGING DOCUMENTATION
Step 18: Record in the Cargo Control Room and in the Ullage Report form:
  - Tank number and reference point ID
  - Gross ullage (m)
  - Trim and list at time of measurement
  - Corrected ullage (after applying trim correction from cargo capacity tables)
  - Temperature at top/middle/bottom (°C)
  - Free water interface depth (m)
  - Volume (m³ from tank calibration tables)
Step 19: Shore representative witnesses and co-signs the ullage report.
Step 20: Shore and ship figures compared. If discrepancy > 0.3%, open a marine protest.
"""))

# ======================================================================
# BUNKERING — Additional procedures  
# ======================================================================
DOCS.append(doc("Bunkering — Pre-Bunkering Meeting and OCIMF Ship-Shore Safety Checklist", "Bunkering checklist", """
Bunkering Pre-Operations Meeting and Safety Checklist
Based on OCIMF/ICS Ship-to-Ship Transfer Guide and MARPOL Annex I

PRE-BUNKERING MEETING (required before any bunker operation begins)
Step 1: Gather the Chief Engineer, duty engineer, OOW and deck rating responsible for bunker manifold watch.
Step 2: Confirm with the bunker barge/terminal representative:
  - Fuel grade and grade segregation (e.g., VLSFO and MGO must NOT be co-mingled)
  - Quantity to be delivered (cross-check ship's calculation for maximum receiving capacity)
  - Pumping rate — agree on initial starting rate (low rate) and maximum rate
  - Transfer pressure at ship's manifold — must not exceed the flange/hose rating
  - Emergency stop procedure: agree on hand signal (e.g., raised fist = STOP) and radio code word
Step 3: Confirm ship's receiving tanks:
  - Which tanks receive which grade
  - Order of tank filling (start with smallest tank, or as per plan)
  - High-level alarm settings for each tank
  - Last tank to be filled (must not exceed 95% capacity during operations)

OCIMF SHIP-BARGE SAFETY CHECKLIST (complete jointly before start)
Step 4: Complete the OCIMF Checklist Part A — Barge Inspector and Ship Officer verify:
  □ MARPOL Annex I: Does the barge have a valid IOPP Certificate?
  □ Are the hoses in good condition with no bulges, corrosion, or weeping?
  □ Do hose pressure ratings match or exceed maximum transfer pressure?
  □ Is the bunker manifold equipped with drip trays?
  □ Is oil spill response equipment ready (boom, absorbents, pump)?
  □ Are portable fire extinguishers placed at the manifold connection?
  □ Are all deck scuppers plugged with wooden/rubber plugs?
  □ Is the bunker station a designated no-smoking area with signage posted?
  □ Is there a means of communication confirmed on the same radio channel?
  □ Have emergency stop signals been agreed and understood by both parties?
  □ Is a continuous watch posted on deck throughout bunkering?
  □ Is the MARPOL continuous sampling point confirmed at the ship's manifold?

DURING BUNKERING
Step 5: Signal barge to start pumping at SLOW RATE (typically 10-30 m³/hour).
Step 6: Walk the line: inspect all hose connections for leaks as soon as oil starts flowing.
Step 7: Confirm oil is entering the correct tank. Check by taking a quick sounding after 5 minutes.
Step 8: Confirm the flowmeter on the barge is recording correctly.
Step 9: Once confirmed no leaks: signal barge to increase to the agreed maximum pumping rate.
Step 10: Post a continuous watch on deck at the manifold with a portable VHF.
Step 11: Take hourly tank soundings. Record on bunkering logsheet.
Step 12: Inform barge when 10% of ordered quantity remains. Reduce pump rate again (topping off).
Step 13: Inform barge when HIGH-HIGH LEVEL is approaching (5 minutes before). Barge to prepare for STOP.
Step 14: Signal STOP when all bunker received. Close ship-side manifold valve.
Step 15: Allow barge to blow through hose to drain remaining oil.
Step 16: Disconnect hose. Blank off manifold using ANSI blind flange.

COMPLETING DOCUMENTATION
Step 17: Obtain BDN from barge. Verify all required MARPOL fields are present.
Step 18: Compare delivered quantity (BDN) vs ship's calculated quantity (from tank sounding difference).
   If difference > 0.5%: add a protest note to the BDN before signing.
Step 19: Seal, label and store the MARPOL drip sample (both parties sign label).
Step 20: Make ORB Part I entry — Code C (Bunkering), Code D (Major Leaks Non-Operational Times).
Step 21: Sign BDN. Distribute copies: master file, Chief Engineer file, charterer.
"""))

# Save all docs
with open(OUT, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d) + "\n")

print(f"✅ Written {len(DOCS)} additional synthetic procedural documents to {OUT}")
print("\nTopics covered:")
for d in DOCS:
    print(f"  [{d['topic'][:40]}] {d['title'][:65]}")
