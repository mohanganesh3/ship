#!/usr/bin/env python3
"""
Synthetic Procedural Document Generator.
Creates detailed step-by-step procedures for maritime operations
based on IMO regulations, ISM Code, MARPOL, SOLAS, and STCW.

These documents are based on publicly documented regulatory requirements
and industry-standard practices — all public domain / open access information.
"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "extracted_text")
OUT = os.path.join(DATA_DIR, "synthetic_procedures.jsonl")
os.makedirs(DATA_DIR, exist_ok=True)

def doc(title, topic, text):
    return {"title": title, "source": "synthetic_regulatory_procedures",
            "topic": topic, "text": text.strip(),
            "scraped_at": datetime.utcnow().isoformat()}

DOCS = []

# ======================================================================
# FWG — FRESH WATER GENERATOR PROCEDURES
# ======================================================================
DOCS.append(doc("Fresh Water Generator (FWG) Starting Procedure", "FWG startup procedure", """
Fresh Water Generator (FWG) Starting Procedure — Based on Standard Marine Engineering Practice

The fresh water generator (FWG) produces potable water by evaporating seawater using waste heat from the main engine jacket water. The following procedure is used to start a typical single-stage evaporator type FWG.

PRE-START CHECKS
Step 1: Ensure the vessel is at sea and main engine is running at normal sea load. The FWG should not be operated in port or within 20 nautical miles of land (WHO requirement) to avoid contaminated water intake.
Step 2: Check the shell-side vacuum. The FWG operates under vacuum (approximately 90-95 mbar absolute). Open the vacuum gauge cock and verify the vacuum pump is running.
Step 3: Check that the sea chest valves are open and seawater cooling water flow is available.
Step 4: Verify that the distillate pump, brine pump, and ejector pump are in ready condition.
Step 5: Check that the salinometer is calibrated and functional. Acceptable salinity for potable water is ≤ 2 parts per million (ppm) by international standards, though many SMS systems require ≤ 0.5 ppm.
Step 6: Ensure the freshwater storage tank has sufficient capacity to receive distillate.

STARTING PROCEDURE
Step 7: Start the ejector pump. This creates and maintains the vacuum within the shell.
Step 8: Open the seawater feed valve to allow seawater into the evaporator chamber (feed side).
Step 9: Open the jacket water inlet valve to allow hot jacket water (approximately 85-90°C) to flow through the heating coils/plates.
Step 10: Monitor the shell pressure gauge. Vacuum should build to approximately -0.8 to -0.9 bar gauge within 5-10 minutes.
Step 11: As vacuum builds and heating water enters, evaporation will commence. Observe the sight glass on the distillate side for water droplets.
Step 12: Start the distillate pump after water collection begins in the shell base.
Step 13: Start the brine pump to remove accumulated brine from the evaporator shell.

SALINOMETER MONITORING
Step 14: Open the salinometer sample valve. Allow salinometer to stabilize (approximately 2-3 minutes).
Step 15: Read the salinity value. If salinity is > 2 ppm (or the vessel-specific limit in the SMS), open the three-way dump valve to direct distillate to overboard instead of the freshwater tank.
Step 16: Continue monitoring salinometer every 15 minutes during operation.
Step 17: Only when salinity is within acceptable limits should the three-way valve be positioned to direct distillate to the freshwater tank.

NORMAL OPERATION
Step 18: Log the FWG operating parameters every 4 hours in the Engine Room Logbook:
  - Shell vacuum (mbar)
  - Jacket water inlet temperature (°C)
  - Jacket water outlet temperature (°C)
  - Distillate flow rate (litres/hour)
  - Brine salinity (ppm)
  - Freshwater tank level
Step 19: Monitor the brine density. If brine becomes too concentrated, scale will form on heating surfaces. Adjust brine pump output accordingly.
Step 20: Check distillate pump suction and delivery pressures.

SECURING THE FWG
Step 21: Close the jacket water inlet valve.
Step 22: Allow the shell to cool for approximately 5 minutes.
Step 23: Stop the distillate pump.
Step 24: Stop the brine pump.
Step 25: Stop the ejector pump.
Step 26: Close seawater feed valve.
Step 27: Open the vacuum-breaking valve to restore atmospheric pressure in the shell.
Step 28: Close salinometer sample valve.
Step 29: Record the shutdown time and total distillate produced in the Engine Room Logbook.

MAINTENANCE NOTES
The FWG heating surfaces should be cleaned with citric acid solution (typically 5% solution) when:
  - Distillate production rate falls by more than 20% compared to design output
  - Shell vacuum becomes difficult to maintain
  - Jacket water outlet temperature rises abnormally
  
Frequency of chemical cleaning: typically every 500-1000 operating hours per manufacturer's recommendation.
"""))

DOCS.append(doc("Fresh Water Generator Salinometer Calibration and Salinity Control", "FWG startup procedure", """
Salinometer Calibration and Salinity Control Procedures for Fresh Water Generator

PURPOSE
The salinometer measures the electrical conductivity of FWG distillate to determine chloride content (salinity). Unchecked high salinity can introduce harmful microorganisms and chemicals into the potable water system.

ACCEPTABLE LIMITS
WHO standard for shipboard potable water: chloride content ≤ 250 mg/L
IMO/SOLAS requirement: continuous salinometer monitoring with automatic dump valve
Common SMS requirement: ≤ 2 ppm (some vessels set ≤ 0.5 ppm as alarm level)
Alarm setpoint: typically 2 ppm; High-High alarm: 5 ppm → automatic dump

CALIBRATION PROCEDURE
Step 1: Prepare reference solutions using NaCl dissolved in fresh water:
  - 2 ppm reference solution: dissolve 2 mg NaCl in 1 litre distilled water
  - 10 ppm reference solution: dissolve 10 mg NaCl in 1 litre distilled water
Step 2: Flush salinometer cell with distilled water.
Step 3: Fill salinometer cell with 2 ppm reference solution.
Step 4: Adjust salinometer reading to exactly 2 ppm using calibration screw/potentiometer.
Step 5: Flush with 10 ppm solution, verify reading is within ±0.5 ppm of 10 ppm.
Step 6: Re-flush with distilled water and verify reading returns to 0.
Step 7: Record calibration in Engine Room Maintenance Log with date and calibrator's name.

DUMP VALVE TEST
Step 8: With FWG running, temporarily increase sample valve opening to simulate high salinity.
Step 9: Verify automatic three-way dump valve shifts to overboard position when setpoint is exceeded.
Step 10: Verify alarm sounds in engine room and bridge (or MCC).
Step 11: Record test result in Planned Maintenance System (PMS).

TROUBLESHOOTING HIGH SALINITY
Causes and corrective actions:
- Cause: Sea water carry-over (mist carry-over): Check demister pads for fouling, reduce evaporation rate
- Cause: Heating surface leak (tube/plate failure): Pressurize shell-side with compressed air and inspect heating water for contamination
- Cause: Poor vacuum: Check ejector nozzle for erosion, inspect suction line for air leaks
- Cause: Salinometer cell contamination: Clean and re-calibrate salinometer
"""))

# ======================================================================
# TANK GAUGING / ULLAGE PROCEDURES
# ======================================================================
DOCS.append(doc("Cargo Tank Ullage Measurement — Procedure for Oil Tankers", "Tank gauging / ullage", """
Cargo Tank Ullage/Gauging Procedure — Oil Tankers
Based on OCIMF/ICS International Safety Guide for Oil Tankers and Terminals (ISGOTT) and IMO MARPOL requirements.

DEFINITIONS
Ullage: The distance from the top reference point of the tank to the surface of the liquid.
Innage (Sounding): The distance from the tank bottom (or datum plate) to the liquid surface.
Reference point: The highest point of the tank designated for ullage measurement, marked on the tank dome or hatch coaming.
Trim correction: Applied when the vessel is not on even keel to adjust raw gauge readings.
List correction: Applied when the vessel has a list.

PRE-MEASUREMENT SAFETY CHECKS
Step 1: Check atmosphere in cargo tank using a calibrated gas detector. Oxygen content must be ≥ 20.9% (if manned entry required) and hydrocarbon content must be < 1% LEL for safe gauging operations near the tank opening.
Step 2: If the tank is under inert gas (IG) or under vapour pressure, use a closed gauging system (radar level gauge, servo gauge, or hermetically sealed float) — do not open the tank.
Step 3: Verify that the inert gas system is maintaining slight positive pressure (25-50 mm WG) in the cargo tank.
Step 4: Check wind direction. Position yourself upwind of any cargo tank opening.
Step 5: Use anti-static clothing and ensure personal gas detector is active.
Step 6: Obtain Permit to Work (PTW) if opening any tank dome.

GAUGING METHODS
A) CLOSED GAUGING (preferred for pressurised/IG-protected tanks):
Step 7: Access the tank through the closed gauge point (small vapour lock fitting on the tank top).
Step 8: Insert a calibrated tape measure or portable gauging device through the closed gauge slot.
Step 9: Lower the float/plumb bob until it touches the liquid surface.
Step 10: Read the ullage directly from the tape at the reference mark.
Step 11: Record gross ullage in centimetres.

B) UTI (Ullage Temperature Interface) GAUGE:
Step 12: Lower UTI probe through the closed gauge point slowly.
Step 13: Read the liquid level (ullage), liquid temperature at various depths, and interface level (water/oil interface).
Step 14: Record all readings: ullage (cm), temperature at top/middle/bottom (°C), free water level (cm from bottom).
Step 15: Withdraw probe slowly to avoid vapour release.

CORRECTION CALCULATION
Step 16: Apply trim correction using the vessel's Trim and Stability Booklet tables.
  Corrected ullage = Gross ullage ± Trim correction
  (Positive trim with cargo forward: subtract correction from aft tanks, add to forward tanks)
Step 17: Apply list correction if vessel list > 0.5°.
Step 18: Apply temperature correction to volume using the vessel's cargo capacity tables and GOV (Gross Observed Volume) tables.
Step 19: Calculate volume: Cross-reference corrected ullage in the tank capacity tables to obtain volume in cubic metres or barrels.
Step 20: Apply Volume Correction Factor (VCF) to convert observed volume to volume at 15°C (standard conditions).
  GSV (Gross Standard Volume) = GOV × VCF

DOCUMENTATION
Step 21: Record all gauging data in the Cargo Log / Ullage Report:
  - Date and time of gauging
  - Tank number
  - Gross ullage (cm)
  - Trim at time of gauging
  - Corrected ullage (cm)
  - Temperature (°C)
  - GOV (m³ or barrels)
  - GSV at 15°C
  - Free water (cm)
Step 22: Compare figures with ship's figures and terminal's independent figures.
  Accepted maximum difference (shore/ship): ± 0.5% per OCIMF/ISGOTT guidelines.
"""))

# ======================================================================
# CRUDE OIL WASHING PROCEDURES
# ======================================================================
DOCS.append(doc("Crude Oil Washing (COW) Procedure — Full Step-by-Step Operation", "Crude oil washing procedure", """
Crude Oil Washing (COW) Complete Operating Procedure
Reference: MARPOL Annex I, Regulation 33; IMO Resolution A.446(XI); ISGOTT Chapter 8

LEGAL BACKGROUND
COW is mandatory on crude oil tankers >20,000 DWT under MARPOL Annex I. The COW system uses crude oil itself as a solvent to clean tank residue, reducing oily residue substantially and allowing near-complete cargo discharge.

PRE-COW CHECKS
Step 1: Verify IMO COW approval is endorsed on vessel's COW Operations Manual.
Step 2: Ensure vessel has a valid COW Operations Manual approved by flag state.
Step 3: Confirm crude oil washing log (Form A — Record of Oil) is ready.
Step 4: Check that inert gas (IG) plant is operational. O₂ content in cargo tanks must be ≤ 8% by volume before and throughout COW. Do NOT commence COW if O₂ > 8%.
Step 5: Verify inert gas pressure in all tanks: minimum +25 mm WG (water gauge).
Step 6: Check all COW machine (fixed tank washing machine) hydraulic connections are tight.
Step 7: Test COW machines in rotation mode on deck (with water first if last operation was water wash).
Step 8: Identify tanks to be crude washed per the pre-planned schedule.
Step 9: Notify terminal representative that COW is to be conducted.
Step 10: Record start time in COW log.

COW DURING DISCHARGE OPERATION
Step 11: Begin discharging cargo from the selected tank.
Step 12: Once tank is 70-80% discharged, open the COW supply line from the cargo line (crude oil supply to washing machines).
Step 13: Open individual tank washing machine manifold valves for the tank being washed.
Step 14: Start COW pump (or use main cargo pump as COW pump) at designed pressure (typically 8-10 bar).
Step 15: Verify COW machines are rotating by observing the rotation indicator on deck (mechanical flag/spinner).
Step 16: Bottom washing (first stage): wash the bottom of the tank. Duration: approximately 2-3 hours for a typical 20,000 m³ tank.
Step 17: Monitor O₂ content in the tank being washed via fixed detection system. If O₂ exceeds 8%, stop COW immediately and recirculate inert gas.
Step 18: Once bottom wash complete, commence top washing (second stage): angle machines upward to wash upper strakes and frames.
Step 19: Continue discharging while COW in progress, ensuring pump suction does not lose prime.

COMPLETING COW
Step 20: Drain COW pump and lines on completion.
Step 21: Close all COW machine manifold valves.
Step 22: Close COW supply valve from cargo line.
Step 23: Check final tank bottom level using UTI gauge.
Step 24: Allow slops to drain from tank to slop tank.
Step 25: Record finish time, tank numbers washed, and COW machine hours in COW log (ORB Part I entries E-F per MARPOL).

ENTRY IN OIL RECORD BOOK (ORB)
Step 26: Complete ORB Part I, Code E (Ballasting / Cleaning of oil fuel tanks):
  - Date / vessel name / port
  - Tank identification
  - Whether crude oil washing or water washing
  - Signature of officer in charge
Step 27: Master countersigns ORB entry.

PROHIBITED DISCHARGES
Never discharge crude oil wash residues overboard except:
- Via the oil discharge monitoring equipment (ODME) as permitted ballast/tank washing water
- At >50 nautical miles from land
- Vessel en route
- Discharge rate ≤ 30 litres per nautical mile
- Total quantity ≤ 1/15,000 of cargo

All slops from COW must be retained onboard and discharged to shore reception facilities or processed via ODME if the above criteria are met.
"""))

# ======================================================================
# BUNKERING CHECKLIST
# ======================================================================
DOCS.append(doc("Bunkering Checklist and Procedure — Step-by-Step Guide", "Bunkering checklist", """
Ship Bunkering Procedure and Safety Checklist
Reference: OCIMF/ICS Ship-to-Ship Transfer Guide; MARPOL Annex I; SOLAS Chapter II-2; SMS Requirements

PHASE 1 — PRE-BUNKERING PLANNING
Step 1: Receive bunker nomination from vessel operators specifying:
  - Grade of fuel: HFO, VLSFO (0.5% S), LSMGO, LSFO, MDO/MGO
  - Quantity required (metric tonnes)
  - Bunkering port, berth, and time
Step 2: Calculate bunker quantity required using:
  Required = (next voyage consumption × safety margin 10%) - bunker on board (BOB)
Step 3: Verify tank capacity available for proposed bunker grade. Segregate fuel grades correctly.
Step 4: Check MARPOL Annex VI: confirm sulphur content of fuel is compliant with:
  - All voyages: ≤ 0.5% S (VLSFO requirement post 2020)
  - In Emission Control Areas (ECA): ≤ 0.1% S
Step 5: Notify Chief Engineer and Master. Complete pre-bunkering plan.
Step 6: Arrange sampling in advance: MARPOL Annex VI requires continuous drip sample taken at the ship's bunker manifold throughout entire delivery.

PHASE 2 — PRE-BUNKERING SAFETY CHECKS (Complete BEFORE hose connection)
Step 7: Conduct pre-bunkering meeting with all involved crew:
  - Designate Officer in Charge (OIC) — typically Chief Engineer or duty engineer
  - Assign crew to bunker manifold, overflow alarm station, and tank top watch
  - Establish communication signals (verbal, radio, and manual)
  - Review emergency shutdown procedure
Step 8: Complete Joint Inspection Checklist with barge/terminal representative (OCIMF/ICS standard):
  □ Manifold pressure rating confirmed matching
  □ Bunker hoses inspected — free of defects, rated pressure adequate
  □ All scuppers plugged to prevent any spill reaching sea
  □ Drip trays positioned under all manifold connections
  □ Fire extinguishers ready at manifold (minimum 2 × 9 kg dry powder)
  □ Bunker station is no-smoking zone
  □ Portable VHF/radio on same channel as barge
  □ Ship-barge link (phone or radio) tested
  □ Emergency stop procedure agreed, hand signals agreed
  □ Emergency contact list posted at manifold

PHASE 3 — HOSE CONNECTION AND START
Step 9: Chief Engineer checks all tank sounding/ullage gauges and records in Bunker Report.
Step 10: Connect bunker hose to manifold — inspect hose flange gasket before making up.
Step 11: Tighten all bolts. Test connection by opening manifold valve briefly at low pressure.
Step 12: Set overflow monitoring: position crew at overflow tank vent/ullage point.
Step 13: Request barge to commence pumping at SLOW rate.
Step 14: Open ship-side manifold valve.
Step 15: Confirm flow on deck by checking hose pressure and monitoring receiving tank ullage.
Step 16: Increase to full pumping rate once line is charged and no leaks are observed.
Step 17: Begin MARPOL continuous sample collection from ship-side manifold throughout pumping.

PHASE 4 — DURING BUNKERING
Step 18: Monitor tank ullages every 15 minutes. Record in Bunker Report.
Step 19: Call for STOP pumping at HIGH-HIGH LEVEL alarm setpoint (usually 95% of tank capacity).
Step 20: Transfer to next tank if topping up multiple grades. Ensure no cross-contamination.
Step 21: If overflow alarm activates: immediately signal barge to stop pumping. Investigate before resuming.
Step 22: Keep scuppers plugged throughout. Any spill: activate ship's oil spill procedure.

PHASE 5 — COMPLETION
Step 23: When all bunkers received, signal barge to reduce flow rate then stop pumping.
Step 24: Close manifold valve on ship side.
Step 25: Blow-back hose (barge blows compressed air through hose) to drain hose into manifold.
Step 26: Disconnect hose. Blank off manifold. Remove drip tray (check no oil).
Step 27: Obtain Bunker Delivery Note (BDN) from barge. BDN must state:
  - Date, vessel name, port
  - Fuel grade and quantity delivered (MT)
  - Density at 15°C
  - Sulphur content (% m/m with test method)  
  - Flash point (≥ 60°C required by MARPOL Annex I)
  - Delivery date and ship/barge names
Step 28: Take final tank soundings. Calculate total received by BOTH ullage method and comparing BDN.
Step 29: Retain MARPOL sample (sealed, labelled, signed by OIC and barge rep) for minimum 12 months.
Step 30: Make ORB Part I entry (Code C — Ballasting or Cleaning) and Fuel Oil Bunker Record.
Step 31: Complete MARPOL Annex VI Fuel Oil Changeover Log if switching fuel grades (ECA entry/exit).

SPILL RESPONSE
- Immediately activate ship's Oil Pollution Emergency Plan (SOPEP)
- Stop pumping
- Contain spill using portable booms/absorbents
- Notify port authority and flag state
- Record in ORB (Code F — Accidental or Other Exceptional Discharge)
"""))

# ======================================================================
# APEM PASSAGE PLANNING
# ======================================================================
DOCS.append(doc("Passage Planning Procedure (APEM) — Full Step-by-Step Guide", "APEM passage planning", """
Passage Planning Procedure — APEM (Appraise, Plan, Execute, Monitor)
Reference: IMO Resolution A.893(21) Guidelines for Voyage Planning; SOLAS Chapter V Regulation 34; MCA MGN 315

LEGAL REQUIREMENT
SOLAS Chapter V, Regulation 34 requires ALL vessels to carry out a passage plan before commencing any voyage. The plan must be in place before the vessel leaves berth.

STAGE 1 — APPRAISE (Preparation/Information Gathering)
Step 1: Identify the voyage: departure port, waypoints, arrival port, estimated passage time.
Step 2: Review all relevant nautical publications:
  □ Sailing Directions (Pilot Books) — check for known hazards, currents, tidal streams
  □ List of Lights — verify major lights expected on passage
  □ Tide Tables — determine HW/LW times for tidal ports/restricted waters
  □ Tidal Stream Atlases — determine favourable/adverse streams
  □ Notices to Mariners (NtM) — confirm charts are fully corrected and current T&P notices noted
  □ NAVTEX and Admiralty Sailing Directions: check for recent warnings
Step 3: Review charts on passage (highest scale charts for ports, approaches, coastal passages):
  □ Ensure all charts are fully corrected and the latest edition
  □ Note any new dangers (wrecks, newly charted obstructions) from NtMs
Step 4: Identify navigational hazards along the route:
  - Traffic Separation Schemes (TSS) — COLREGS Rule 10
  - Shallow patches, depth restrictions
  - Restricted areas (firing ranges, marine protected areas)
  - Vessel Traffic Services (VTS) — reporting requirements
  - Areas of restricted visibility or ice
  - Load line zones applicable
Step 5: Determine weather routing plan:
  - Review weather forecasts (Inmarsat-C, NAVTEX, BNO)
  - Identify likely weather windows and potential bad weather
  - Select safest route options

STAGE 2 — PLAN (Creating the Written Passage Plan)
Step 6: Select waypoints and lay off the track on charts using parallel rulers and compass.
Step 7: Calculate courses between waypoints (True Course, then apply variation and deviation for Compass Course).
Step 8: Calculate distances for each leg and total voyage distance.
Step 9: Estimate speed and calculate ETAs for each waypoint, port approaches, and critical points.
Step 10: Mark on chart:
  - Wheel-over positions (WOP) for each turn
  - Clearing bearings (to remain clear of hazards)
  - Anchor berths if emergency anchoring is needed
  - No-go areas (shaded or cross-hatched)
  - Safe speed limits in traffic separation/congested areas
  - Reporting points for VTS
Step 11: Write Night Order Book and prepare Bridge Watch Handover information.
Step 12: Brief the Master (or complete Master's Approval form) — Master must formally approve the passage plan before departure.

STAGE 3 — EXECUTE (Implementing the Passage Plan)
Step 13: At departure, verify all chart corrections are up to date. Set and verify ECDIS route if vessel fitted.
Step 14: Enter critical points and checking waypoints in ECDIS and radar.
Step 15: Execute voyage maintaining a proper lookout per COLREGS Rule 5.
Step 16: Record all position fixes at intervals appropriate to the navigational risk:
  - Port approaches / coastal waters: every 15-30 minutes (or more frequently as required)
  - Ocean passages: every 1-2 hours (celestial, GPS cross-checked)
Step 17: Maintain Bridge Navigation Watch Alarm System (BNWAS) as required.
Step 18: Follow all traffic separation schemes per COLREGS Rule 10.
Step 19: Report to VTS as required.
Step 20: Apply tidal stream corrections when crossing tidal areas.

STAGE 4 — MONITOR (Ongoing Updating of the Plan)
Step 21: Compare actual track against planned track using GPS overlay on chart.
Step 22: Update ETAs as actual conditions (wind, current, engine performance) differ from plan.
Step 23: Monitor weather continuously. Amend plan if conditions deteriorate beyond safe parameters.
Step 24: Take sea pilot if required by port authority or Master's decision.
Step 25: When deviating from the plan: notify Master immediately and annotate the plan with reason and time.

SPECIFIC MANDATORY CHECKS — PORT APPROACH
Step 26: Identify and confirm the pilot station position.
Step 27: Reduce speed for pilot embarkation at least 30 minutes before ETA pilot station.
Step 28: Prepare anchor(s) — at anchor stations if required by the port/anchorage.
Step 29: Inform engine room of maneuvering requirements: "Finished With Sea Watch."
Step 30: Check all navigation lights are correct for the maneuver.
"""))

# ======================================================================
# DRYDOCKING CHECKLIST
# ======================================================================
DOCS.append(doc("Ship Drydocking Preparation and Indocking Checklist", "Drydocking checklist", """
Drydocking Preparation and Indocking Procedure Checklist
Reference: ISM Code; Class Society Survey Requirements; Drydocking Superintendent Guidance

PRE-DRYDOCK PREPARATION (Weeks Before Docking)
Step 1: Prepare the Repair List (Specification): document all defects, outstanding class conditions, statutory requirements, and planned maintenance to be carried out in drydock. Categories include:
  - Class-required items (Special Survey, Intermediate Survey, periodical survey)
  - Statutory items (MARPOL equipment, LSA, fire detection)
  - Owner-elected items (hull painting, propeller polishing, valve overhauls)
  - Defects identified during voyage (logged in Deck/Engine Room Logs)
Step 2: Confirm drydock dates, drydock dimensions, and dock facilities with shipyard.
Step 3: Order parts and materials for all repair items well in advance.
Step 4: Arrange attendance of relevant class society attending surveyor.
Step 5: Ensure all bunker tanks for ballast, FO, FW, etc. are prepared per docking plan (some tanks may need to be empty for dock blocks to be placed correctly).

TANK PREPARATION (2-3 Days Before)
Step 6: Pump out all ballast tanks. Ensure all cargo tanks are empty, cleaned, and gas-free as required.
Step 7: Note: Some void spaces need to be empty to reduce vessel's weight on keel blocks. The ship must be trimmed and listed per the drydock block plan.
Step 8: Prepare trim and stability calculation for undocking and docking conditions.

DAY OF DOCKING
Step 9: Brief all crew on roles during docking:
  - Officer on watch to monitor drafts
  - Chief Engineer to monitor machinery status
  - Deck department to handle mooring lines in dock
Step 10: Verify pilot/dock master arrangements.
Step 11: Verify that dock gate and flooding/pumping operations schedule is agreed with dock foreman.
Step 12: Confirm keel block positions against ship's block plan distributed to shipyard.
Step 13: Assign crew to watch drafts fore and aft during pumping down.

DURING PUMPING DOWN
Step 14: As dock is pumped down, officer reports draft readings every 30 cm to Master and Superintendent.
Step 15: When vessel lands on keel blocks: Dock Foreman confirms "all blocks taking weight."
Step 16: Check vessel for list. If list develops, take corrective action (shift ballast/bunker if possible, or report to dock master for side spur wedges).
Step 17: Once vessel is sitting correctly on blocks, open shore side gangway.
Step 18: Shut down seawater-cooled systems (main sea chests are now high and dry):
  - Main engine sea water cooling
  - Generator sea water cooling
  - Air conditioning sea water
  - Fire pump and bilge pump sea suction (shift to dock supply)

POST-DOCKING CHECKS
Step 19: Carry out draft survey (Note: in drydock, waterline is no longer applicable — use displacement method).
Step 20: Allow classification society surveyor to carry out hull gauging, keel plate inspection, propeller inspection.
Step 21: Record all propeller blade dimensions, rudder pintle clearances, and stern tube measurements in the hull survey record.
Step 22: Before any underwater hot work: ensure gas-free certificate obtained by shipyard safety officer.
Step 23: Maintain engine room watch during drydock to monitor bilgewater accumulation (condensation, rain ingress).

UNDOCKING CHECKLIST
Step 24: Ensure all sea chest blanks are removed.
Step 25: Ensure all anodes have been replaced/renewed as specified.
Step 26: Verify hull paint has been applied and quality-checked.
Step 27: Confirm propeller polishing is done and propeller shaft seal integrity tested.
Step 28: Close all sea valves prior to flood-up.
Step 29: Confirm rudder is amidships and propeller is clear of any staging.
Step 30: Complete sea trial (or dock trial) on all main propulsion and auxiliary machinery.
Step 31: Obtain class certificate or letter of compliance from attending surveyor before departure.
"""))

# ======================================================================
# MASTER OVERRIDE
# ======================================================================
DOCS.append(doc("Master's Authority and Override Principle — ISM Code Requirements", "Master override", """
Master's Authority Over-ride: ISM Code Requirements and Practical Application
Reference: IMO Resolution A.741(18) ISM Code, Clause 5 and 6; STCW Convention; MLC 2006

LEGAL BASIS
ISM Code, Section 5.1: "The Company shall clearly define and document the Master's responsibility with regard to:
  .1 implementing the safety and environmental protection policy of the Company;
  .2 motivating the crew in the observation of that policy;
  .3 issuing appropriate orders and instructions in a clear and simple manner;
  .4 verifying that specified requirements are observed; and
  .5 reviewing the SMS and reporting its deficiencies to the shore-based management."

ISM Code, Section 5.2 (Critical Clause): "The Company shall ensure that the SMS operated on board the ship contains a clear statement emphasizing the Master's authority. The Company shall establish in the SMS that the Master has the overriding authority and the RESPONSIBILITY to make decisions with respect to safety and pollution prevention and to request the Company's assistance as may be necessary."

WHAT MASTER OVERRIDE MEANS
The Master has the absolute right and duty to:
1. Override any commercial, operational, or scheduling pressure from owners, charterers, or managers when safety or environmental protection is at risk.
2. Refuse to depart port if the vessel is not seaworthy.
3. Deviate from approved voyage instructions when urgent safety concerns require it.
4. Request assistance from the Company without this being considered a failure of performance.
5. Issue orders that differ from Company standing orders if the situation demands it.

COMMON SCENARIOS WHERE MASTER OVERRIDE IS EXERCISED
Scenario 1 — Adverse weather
"The Master decided not to depart because weather forecasts showed force 8 winds in the port approaches. Despite charterer's pressure for on-time departure, the Master exercised override authority. The delay was 12 hours until conditions moderated."

Scenario 2 — Crew fatigue
"Following an extended port stay with continuous cargo operations, the Master determined that watch officers were fatigued beyond STCW rest hour minimums. The Master delayed departure by 8 hours to provide mandatory rest, exercising override authority under MLC 2006 Article IV requirements."

Scenario 3 — Equipment deficiency
"The main engine exhaust gas boiler was found cracked by the Engineer Officer. Despite commercial pressure to sail, the Master refused departure under ISM Code override authority until the Class surveyor inspected and issued a letter of compliance."

PROCEDURE FOR EXERCISING MASTER OVERRIDE
Step 1: Master documents the specific safety concern in the Official Log Book with date, time, and nature of the threat.
Step 2: Master notifies the Company (Owner/Manager) by the most rapid means available (telex, email, Inmarsat-C, phone) stating:
  - Nature of safety concern
  - Action taken (delay, rerouting, refusal of orders)
  - Assistance required
Step 3: Master retains a copy of all communications.
Step 4: If assistance is needed from the Company, Company must respond promptly per ISM Code Section 6.1.3: "The Company shall ensure that the Master is provided with the necessary support so that the Master's duties can be safely performed."
Step 5: Master's decision stands regardless of commercial consequences until Company responds with a satisfactory solution.
Step 6: Resolution is documented in the Official Log Book with outcome and time.

PROTECTION FROM RETALIATION
MLC 2006, Title 5, Regulation 5.1.5: Seafarers who report defects or safety concerns have legal protection against retaliation.
The Master's exercise of override authority is protected by law and cannot constitute grounds for dismissal or commercial penalty.

JUST CULTURE PRINCIPLE
Modern shipping embraces the "Just Culture" model (promoted by CHIRP Maritime, IMO, and flag states):
- Errors and near-misses should be reported without fear of blame
- Systemic failures are investigated rather than blaming individuals
- Deliberate violations are the only category subject to disciplinary action
- Master override exercised in good faith is never a disciplinary matter
"""))

# ======================================================================
# ENCLOSED SPACE ENTRY PERMIT
# ======================================================================
DOCS.append(doc("Enclosed Space Entry Permit Procedure — Full Step-by-Step Compliance", "Enclosed space entry permit", """
Enclosed Space Entry Permit Procedure
Reference: IMO MSC-MEPC.2/Circ.10 (Revised Recommendations for Entering Enclosed Spaces aboard Ships); SOLAS Regulation XI-1/7; STCW; SMS Requirements

DEFINITION OF ENCLOSED SPACES
Any space of limited opening for entry and exit, inadequate ventilation, and not designed for continuous worker occupancy. Examples:
- Cargo holds (especially after grain/coal/chemical cargo)
- Void spaces, ballast tanks, cofferdams
- Pump rooms, compressor rooms, fan rooms
- Chain lockers, bow thruster spaces
- Sewage treatment tank, any storage tank
- Double-bottom tanks, wing tanks
- Boilers, reheaters, mud boxes
- CO₂ flooding rooms, gas bottle rooms

WHY ENCLOSED SPACES ARE DANGEROUS
1. Oxygen deficiency: < 19.5% O₂ = immediately dangerous to life; normal is 20.9%
2. Toxic gas: H₂S (hydrogen sulphide in sewage tanks, crude oil tanks — IDLH 50 ppm)
3. Flammable gas: hydrocarbon vapour in fuel/cargo tanks
4. Asphyxiation without warning: CO₂ accumulation in unventilated spaces
5. Inert atmosphere: spaces purged with N₂ or CO₂ for inertage

MANDATORY REQUIREMENTS (SOLAS XI-1/7 effective Jan 2015)
1. Appropriate instruments for O₂ and toxic/flammable gas measurement
2. Suitable recovery/resuscitation equipment ready at entrance
3. Permit to work system covering enclosed space entry
4. Training records for all crew on enclosed space entry
5. Enclosed space entry drills at regular intervals

PHASE 1 — PRE-ENTRY RISK ASSESSMENT
Step 1: Identify the enclosed space and the work to be done inside.
Step 2: Assign Responsible Officer (typically Chief Officer or Chief Engineer, depending on space).
Step 3: Identify hazards:
  □ What was the previous content of the space?
  □ Any possibility of gas generation (organic decomposition, cargo residue)?
  □ Is the space connected to any system that could introduce gas or liquid?
  □ Could inert gas enter the space from the IG system?
Step 4: Isolate the space: close and blank off all valves, pumps, steam lines, etc. that could admit cargo, fluid, or gas.
Step 5: Affix "Do Not Operate" locks/tags (Lockout/Tagout) on all isolations.

PHASE 2 — ATMOSPHERE TESTING
Step 6: Ventilate the space mechanically for at least 30 minutes before testing.
Step 7: Using a calibrated multi-gas detector (O₂, %LEL hydrocarbons, H₂S, CO), test the atmosphere:
  - At the entrance level (top)
  - At mid-height
  - At the bottom of the space
Step 8: Compare readings against safe limits:
  □ O₂: ≥ 20.8% (minimum 19.5%)
  □ Flammable gas: < 1% LEL (equivalent to < 10% of LFL)
  □ H₂S: < 1 ppm (ACGIH TLV); < 10 ppm (emergency limit)
  □ CO: < 25 ppm (ACGIH TLV)
Step 9: Record all test results and instrument serial number, calibration date on the Permit to Work.
Step 10: If atmosphere is NOT safe — continue ventilation and re-test after 30 minutes. Do NOT enter.

PHASE 3 — ISSUING PERMIT TO WORK
Step 11: Responsible Officer completes the Enclosed Space Entry Permit:
  □ Space identification (cargo hold #, ballast tank position, etc.)
  □ Date and time of entry
  □ Names of all persons authorised to enter
  □ Atmosphere test results
  □ Rescue equipment checklist:
     - Lifeline and harness at entrance
     - Breathing apparatus (SCBA) worn by entrant if required, and standby set by entry point
     - Resuscitator at entrance
     - Thermal rescue stretcher
  □ Communication method (radio, voice, visual)
  □ Attendant's name (must remain at entrance throughout — cannot enter to assist)
  □ Rescue plan
Step 12: Master or designated senior officer signs and authorises the permit.
Step 13: Post a copy of the permit at the entry point of the space.

PHASE 4 — ENTRY PROCEDURE
Step 14: Assign an Attendant at all times outside the entrance. The Attendant must remain there and cannot enter.
Step 15: Entrant dons lifejacket or harness with lifeline if required by the risk assessment.
Step 16: If toxic gas present: entrant wears SCBA (self-contained breathing apparatus) — not just a filter mask.
Step 17: Entrants carry personal gas detector inside the space.
Step 18: Establish communication schedule: entrant communicates with Attendant every 5 minutes minimum.
Step 19: Work begins inside space.

PHASE 5 — RESCUE PROCEDURE
If entrant does not respond to communication:
Step 20: Attendant calls for help — NEVER enters alone.
Step 21: Raise general alarm (7 short + 1 long blast on ship's whistle, or internal alarm).
Step 22: Duty Officer or Rescue Team proceeds to the space.
Step 23: Rescue Team: minimum 2 persons with SCBA enter to assist entrant.
Step 24: Entrant is extracted using lifeline and harness.
Step 25: Begin resuscitation if required.
Step 26: Notify Master and prepare casualty for medical assistance.

PERMIT CLOSURE
Step 27: On completion of work, all entrants account for themselves at exit.
Step 28: Responsible Officer closes the permit (signs off with time).
Step 29: Remove all tools and equipment from the space.
Step 30: Close and secure the space.
Step 31: Retain completed permit for at least 3 months in the permit file.

NOTE: The Permit to Work must be reissued if:
- The work changes in nature during the task
- There is a break in work longer than 1 hour
- The atmosphere test readings approach alarm limits during the task
"""))

# Save all docs
with open(OUT, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d) + "\n")

print(f"✅ Written {len(DOCS)} synthetic procedural documents to {OUT}")
print("\nTopics covered:")
for d in DOCS:
    print(f"  [{d['topic'][:40]}] {d['title'][:60]}")
