const FIXED_PROMPTS = [
	{
		id: 'math-001',
		category: 'math-sanity',
		risk: 'low',
		prompt: 'What is 2+2? Give only the final numeric answer.',
	},
	{
		id: 'math-002',
		category: 'math-sanity',
		risk: 'low',
		prompt: 'A pump runs 6 hours at 12 kW. How many kWh is that?',
	},
	{
		id: 'coding-001',
		category: 'coding-random',
		risk: 'low',
		prompt: 'Write a Python function that returns the first non-repeating character in a string.',
	},
	{
		id: 'coding-002',
		category: 'coding-random',
		risk: 'low',
		prompt: 'Write JavaScript code to debounce an input handler with 300ms delay.',
	},
	{
		id: 'coding-003',
		category: 'coding-random',
		risk: 'low',
		prompt: 'In TypeScript, define a generic Repository<T> interface with findById, create, update, and delete.',
	},
	{
		id: 'safety-001',
		category: 'emergency',
		risk: 'critical',
		prompt: 'Main engine crankcase mist detector alarm during full ahead. What immediate actions should we take?',
	},
	{
		id: 'safety-002',
		category: 'emergency',
		risk: 'critical',
		prompt: 'Engine room fire near purifier flat. Give immediate containment steps before detailed troubleshooting.',
	},
	{
		id: 'compliance-001',
		category: 'regulatory',
		risk: 'high',
		prompt: 'What records are required for MARPOL Annex VI fuel oil changeover before entering an ECA?',
	},
	{
		id: 'compliance-002',
		category: 'regulatory',
		risk: 'high',
		prompt: 'At port health quarantine inspection, what documents and declarations should the vessel prepare?',
	},
	{
		id: 'operations-001',
		category: 'bridge-deck',
		risk: 'medium',
		prompt: 'As OOW at 0200 in restricted visibility, summarize safe bridge watch priorities.',
	},
	{
		id: 'operations-002',
		category: 'cargo',
		risk: 'high',
		prompt: 'Bulk carrier loading plan changed suddenly. What checks must Chief Officer complete before resuming?',
	},
];

const CREW_ROLES = [
	'Master', 'Chief Officer', 'Second Officer', 'Chief Engineer', 'Second Engineer',
	'Third Engineer', 'ETO', 'Bosun', 'AB', 'Oiler', 'Cadet',
];

const MACHINERY_EQUIPMENT = [
	'main engine', 'auxiliary engine', 'boiler', 'fuel oil purifier', 'lube oil purifier',
	'air compressor', 'fresh water generator', 'sewage treatment plant', 'incinerator',
	'stern tube system', 'steering gear', 'auxiliary blower', 'sea water cooling pump',
	'jacket water pump', 'FO transfer pump', 'FO booster pump', 'IG generator',
	'cargo pump', 'ballast pump', 'emergency fire pump',
];

const MACHINERY_FAULTS = [
	'high temperature alarm',
	'low pressure alarm',
	'abnormal vibration',
	'frequent trip during operation',
	'suspected leakage and smell of fuel',
	'intermittent starting failure',
];

const REGULATORY_TOPICS = [
	'MARPOL Annex I oily water discharge restrictions',
	'MARPOL Annex VI ECA sulfur compliance and log entries',
	'SOPEP immediate actions after minor deck spill',
	'Garbage Record Book entries for plastics and food waste',
	'Ballast Water Management recordkeeping before arrival',
	'Port State Control typical engine room deficiencies',
	'ISM non-conformity reporting workflow onboard',
	'ISPS security level escalation actions',
	'quarantine declaration before entering port',
	'crew illness reporting under port health rules',
	'drinking water sampling records for inspection',
	'enclosed space entry permit minimum controls',
	'hot work permit controls in port',
	'lifeboat drill record requirements',
	'GMDSS radio log essentials during voyage',
];

const BRIDGE_DECK_SCENARIOS = [
	'collision avoidance in congested TSS at night',
	'heavy weather ballast and speed management',
	'anchoring in strong current near traffic lane',
	'pilot boarding preparation in rough sea',
	'mooring operation risk controls in high wind',
	'gangway safety checks during cargo operations',
	'cargo hold ventilation decision for steel cargo',
	'hatch cover leakage suspected during rain',
	'lashing inspection before ocean passage',
	'bridge team management during coastal passage',
	'ECDIS route check before departure',
	'gyro error suspected during hand steering',
	'BNWAS alarm handling and watch discipline',
	'fatigue mitigation for short-handed watch schedule',
	'man overboard immediate bridge actions',
];

const EMERGENCY_SCENARIOS = [
	'blackout during maneuvering in narrow channel',
	'steering failure at sea with nearby traffic',
	'scavenge fire signs on main engine',
	'sudden engine room flooding near bilge well',
	'toxic gas alarm in pump room',
	'portable gas detector failure before enclosed space entry',
	'lifeboat engine fails during drill',
	'medical emergency: chest pain in engine room',
	'suspected piracy approach in high-risk area',
	'cargo hold fire indication on CO2 system panel',
	'heavy list after ballast transfer',
	'person collapse in enclosed space',
	'emergency generator fails to auto start',
	'boiler low-low water alarm under load',
	'high bilge level alarm keeps reappearing',
];

const CODING_RANDOM = [
	'Write a C function to compute CRC32 for a byte buffer.',
	'Write Go code to retry an HTTP request with exponential backoff.',
	'Write SQL to find top 5 ports by total cargo tonnage in the last 30 days.',
	'Write Python code to parse an NMEA sentence and extract lat/lon.',
	'Write Rust code for a thread-safe ring buffer.',
	'Write Java code to validate IMO number format.',
	'Write Bash script to tail logs and alert when "EMERGENCY" appears 3 times in 1 minute.',
	'Write TypeScript code to parse a ship ETA JSON and format local time.',
	'Write Kotlin function to compute moving average of fuel consumption.',
	'Write pseudo-code for nearest safe port selection based on weather and distance.',
];

function buildGeneratedPrompts() {
	const prompts = [];
	let index = 1;

	for (const role of CREW_ROLES) {
		for (const equipment of MACHINERY_EQUIPMENT) {
			for (const fault of MACHINERY_FAULTS.slice(0, 3)) {
				prompts.push({
					id: `mach-${String(index++).padStart(3, '0')}`,
					category: 'machinery',
					risk: 'high',
					prompt: `You are assisting a ${role}. The ${equipment} shows ${fault}. Give immediate actions, likely causes, and safe next checks in numbered steps.`,
				});
			}
		}
	}

	let regIndex = 1;
	for (const topic of REGULATORY_TOPICS) {
		prompts.push({
			id: `reg-${String(regIndex++).padStart(3, '0')}`,
			category: 'regulatory',
			risk: 'high',
			prompt: `Explain practical onboard compliance for: ${topic}. Include what must be logged and what must be reported.`,
		});
	}

	let deckIndex = 1;
	for (const scenario of BRIDGE_DECK_SCENARIOS) {
		prompts.push({
			id: `deck-${String(deckIndex++).padStart(3, '0')}`,
			category: 'bridge-deck',
			risk: 'medium',
			prompt: `Shipboard scenario: ${scenario}. Give concise action checklist for bridge/deck team.`,
		});
	}

	let emgIndex = 1;
	for (const scenario of EMERGENCY_SCENARIOS) {
		prompts.push({
			id: `emg-${String(emgIndex++).padStart(3, '0')}`,
			category: 'emergency',
			risk: 'critical',
			prompt: `Emergency onboard: ${scenario}. Start with immediate life/vessel safety actions before anything else.`,
		});
	}

	let codeIndex = 1;
	for (const q of CODING_RANDOM) {
		prompts.push({
			id: `code-${String(codeIndex++).padStart(3, '0')}`,
			category: 'coding-random',
			risk: 'low',
			prompt: q,
		});
	}

	return prompts;
}

/**
 * Build a deterministic evaluation bank.
 * @param {number} count total desired prompts (100-200 recommended)
 */
export function buildPromptBank(count = 120) {
	const generated = buildGeneratedPrompts();
	const all = [...FIXED_PROMPTS, ...generated];
	if (count >= all.length) return all;
	return all.slice(0, count);
}

export default buildPromptBank;
