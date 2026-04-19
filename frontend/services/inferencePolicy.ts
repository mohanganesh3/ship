export type ThinkMode = 'think' | 'no_think';

export type TurnDomain =
  | 'general-chat'
  | 'general-maritime'
  | 'engine-room'
  | 'bridge-navigation'
  | 'deck-cargo'
  | 'compliance'
  | 'medical'
  | 'electrical'
  | 'out-of-domain';

export type TurnRisk = 'low' | 'medium' | 'high' | 'critical';
export type ResponseStyle =
  | 'conversational'
  | 'direct'
  | 'checklist'
  | 'clarify'
  | 'numeric'
  | 'code';

export interface GenerationPolicy {
  temperature: number;
  top_p: number;
  top_k: number;
  min_p: number;
  repeat_penalty: number;
  presence_penalty: number;
  frequency_penalty: number;
  penalty_last_n: number;
  dry_multiplier?: number;
  dry_base?: number;
  dry_allowed_length?: number;
  dry_penalty_last_n?: number;
  dry_sequence_breakers?: string[];
  maxOutputTokens: number;
  thinkingBudgetTokens?: number;
  thinkingBudgetMessage?: string;
}

export interface TurnPolicy {
  thinkMode: ThinkMode;
  crewContext: string;
  domain: TurnDomain;
  risk: TurnRisk;
  responseStyle: ResponseStyle;
  isNonMaritime: boolean;
  isLiveNewsQuery: boolean;
  needsClarification: boolean;
  isBareTopicPrompt: boolean;
  isSmallTalk: boolean;
  asksCoding: boolean;
  asksMath: boolean;
  asksCreative: boolean;
  historyWindow: number;
  systemOverlay: string;
  tuning: GenerationPolicy;
}

export type TurnPolicyOverrides = Partial<
  Pick<
    TurnPolicy,
    | 'crewContext'
    | 'domain'
    | 'risk'
    | 'responseStyle'
    | 'isNonMaritime'
    | 'needsClarification'
    | 'isBareTopicPrompt'
    | 'isSmallTalk'
    | 'asksCoding'
    | 'asksMath'
    | 'asksCreative'
  >
>;

interface DomainProfile {
  crewContext: string;
  domain: TurnDomain;
}

const DRY_SEQUENCE_BREAKERS = ['\n', ':', '"', '*'];

const BASE_NO_THINK: Omit<GenerationPolicy, 'maxOutputTokens'> = {
  temperature: 0.7,
  top_p: 0.8,
  top_k: 20,
  min_p: 0,
  repeat_penalty: 1.03,
  presence_penalty: 0.85,
  frequency_penalty: 0.1,
  penalty_last_n: 128,
  dry_multiplier: 0,
  dry_base: 1.75,
  dry_allowed_length: 2,
  dry_penalty_last_n: 0,
  dry_sequence_breakers: DRY_SEQUENCE_BREAKERS,
};

const BASE_THINK: Omit<GenerationPolicy, 'maxOutputTokens'> = {
  temperature: 0.6,
  top_p: 0.95,
  top_k: 20,
  min_p: 0,
  repeat_penalty: 1.05,
  presence_penalty: 0.35,
  frequency_penalty: 0.05,
  penalty_last_n: 128,
  dry_multiplier: 0,
  dry_base: 1.75,
  dry_allowed_length: 2,
  dry_penalty_last_n: 0,
  dry_sequence_breakers: DRY_SEQUENCE_BREAKERS,
};

const SMALL_TALK_REGEX =
  /^(?:hi|hello|hey|yo|good morning|good afternoon|good evening|how are you|who are you|thanks|thank you|ok|okay|cool|nice|bye|good night)[!. ]*$/i;
const CODING_REGEX =
  /\b(?:code|coding|function|class|python|javascript|typescript|java|rust|go|sql|bash|regex|algorithm|api|json|typescript|react)\b/i;
const MATH_REGEX =
  /\b(?:calculate|solve|what is|how many|sum|difference|multiply|divide|equation|kwh|kw|mw|amps?|volts?|percentage|percent|final numeric answer|numeric answer)\b/i;
const CREATIVE_REGEX =
  /\b(?:poem|story|creative|rewrite|rephrase|caption|joke|lyrics|haiku|tagline)\b/i;
const LIVE_NEWS_REGEX =
  /\b(?:latest|today|current|recent|news|as of now|this week|newest)\b/i;
const SHIP_CONTEXT_REGEX =
  /\b(?:ship|vessel|onboard|on board|crew|bridge|engine room|chief engineer|chief officer|oow|master|bosun|cadet|port state|marpol|eca|ballast|bunker|bilge|purifier|boiler|pump|crankcase|scavenge|machinery|deck|cargo|pilot|radar|ecdis|colreg|logbook|sms|telemedical|lifeboat|steering gear)\b/i;
const COMPLIANCE_REGEX =
  /\b(?:marpol|annex|eca|record|logbook|certificate|declaration|inspection|audit|ism|isps|quarantine|documentation|document|report(?:ed|ing)?|flag|class|port state|sopep|garbage record book|bwm|changeover|ows|oily bilge|bilge water|discharge restrictions)\b/i;
const BRIDGE_REGEX =
  /\b(?:bridge|oow|restricted visibility|radar|ecdis|colreg|pilot|anchoring|traffic separation|tss|helm|watchkeeping|navigation|coastal passage|bnwas)\b/i;
const DECK_CARGO_REGEX =
  /\b(?:cargo|loading|discharge|mooring|gangway|lashing|hatch cover|bulk carrier|deck team|ballast transfer|hold fire|stowage|draft survey)\b/i;
const MEDICAL_REGEX =
  /\b(?:medical|injur|burn|fracture|chest pain|unconscious|collapse|first aid|medevac|telemedical|doctor|patient|breathing|airway)\b/i;
const ELECTRICAL_REGEX =
  /\b(?:blackout|switchboard|generator sync|generator synchron|breaker|electrical|power failure|short circuit|earth fault|emergency generator)\b/i;
const ENGINE_ROOM_REGEX =
  /\b(?:engine room|main engine|auxiliary engine|boiler|purifier|pump|compressor|fuel oil|lube oil|crankcase|scavenge|bilge|cooling water|shaft|stern tube|turbocharger|separator|machinery|alarm)\b/i;
const CRITICAL_REGEX =
  /\b(?:fire|flood|flooding|collision|grounding|man overboard|mob|crankcase mist|toxic gas|enclosed space|blackout during maneuvering|chest pain|unconscious|collapse|explosion|abandon ship|steering failure|emergency|immediate actions?)\b/i;
const DANGLING_FRAGMENT_REGEX =
  /\b(?:regarding|about|for|on|with|during|before|after|if|whether|because|due to|related to|concerning)\s*$/i;
const RAW_PROMPT_SYSTEM_PREFIX =
  'You are Shipboard Maritime AI, a conversational assistant for seafarers. Use maritime knowledge when relevant, but do not force emergency or textbook phrasing into casual turns.';

const DEFAULT_CREW_CONTEXT: Record<TurnDomain, string> = {
  'general-chat': 'Conversational onboard assistant',
  'general-maritime': 'Shipboard operations and crew support',
  'engine-room': 'Engine room watch or engineering team',
  'bridge-navigation': 'Bridge watch team or pilotage support',
  'deck-cargo': 'Deck watch, cargo watch, or mooring team',
  compliance: 'Master, Chief Officer, Chief Engineer, or audit/compliance prep',
  medical: 'Medical response or telemedical support',
  electrical: 'Engine room watch or electrical support',
  'out-of-domain': 'Non-maritime request',
};

function defaultCrewContextForDomain(domain: TurnDomain): string {
  return DEFAULT_CREW_CONTEXT[domain];
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

function wordCount(value: string): number {
  return normalizeWhitespace(value)
    .split(' ')
    .filter(Boolean).length;
}

function detectSmallTalk(message: string): boolean {
  const trimmed = normalizeWhitespace(message);
  if (!trimmed) return false;
  return SMALL_TALK_REGEX.test(trimmed);
}

function detectBareTopicPrompt(message: string): boolean {
  const trimmed = normalizeWhitespace(message);
  if (!trimmed) return false;
  if (/[?.!]/.test(trimmed)) return false;
  if (detectSmallTalk(trimmed)) return false;
  if (DANGLING_FRAGMENT_REGEX.test(trimmed)) return false;
  if (/\b(?:what|how|why|when|where|can|should|is|are|do|does|explain|summarize|give)\b/i.test(trimmed)) {
    return false;
  }
  const count = wordCount(trimmed);
  return count > 0 && count <= 5;
}

function detectNeedsClarification(message: string, isBareTopicPrompt: boolean, isSmallTalk: boolean): boolean {
  const trimmed = normalizeWhitespace(message);
  if (!trimmed || isBareTopicPrompt || isSmallTalk) return false;
  if (DANGLING_FRAGMENT_REGEX.test(trimmed)) return true;
  return false;
}

function inferDomainProfile(
  message: string,
  isSmallTalk: boolean,
  isNonMaritime: boolean,
): DomainProfile {
  const lower = normalizeWhitespace(message).toLowerCase();

  if (isSmallTalk) {
    return {
      crewContext: 'Conversational onboard assistant',
      domain: 'general-chat',
    };
  }

  if (MEDICAL_REGEX.test(lower)) {
    return {
      crewContext: 'Medical response or telemedical support',
      domain: 'medical',
    };
  }

  if (COMPLIANCE_REGEX.test(lower)) {
    return {
      crewContext: 'Master, Chief Officer, Chief Engineer, or audit/compliance prep',
      domain: 'compliance',
    };
  }

  if (BRIDGE_REGEX.test(lower)) {
    return {
      crewContext: 'Bridge watch team or pilotage support',
      domain: 'bridge-navigation',
    };
  }

  if (DECK_CARGO_REGEX.test(lower)) {
    return {
      crewContext: 'Deck watch, cargo watch, or mooring team',
      domain: 'deck-cargo',
    };
  }

  if (ELECTRICAL_REGEX.test(lower)) {
    return {
      crewContext: 'Engine room watch or electrical support',
      domain: 'electrical',
    };
  }

  if (ENGINE_ROOM_REGEX.test(lower)) {
    return {
      crewContext: 'Engine room watch or engineering team',
      domain: 'engine-room',
    };
  }

  if (isNonMaritime) {
    return {
      crewContext: 'Non-maritime request',
      domain: 'out-of-domain',
    };
  }

  if (SHIP_CONTEXT_REGEX.test(lower)) {
    return {
      crewContext: 'Shipboard operations and crew support',
      domain: 'general-maritime',
    };
  }

  return {
    crewContext: 'Non-maritime request',
    domain: 'out-of-domain',
  };
}

function inferRisk(
  message: string,
  domain: TurnDomain,
  isSmallTalk: boolean,
  isNonMaritime: boolean,
): TurnRisk {
  const lower = normalizeWhitespace(message).toLowerCase();

  if (isSmallTalk || isNonMaritime) return 'low';
  if (CRITICAL_REGEX.test(lower)) return 'critical';
  if (domain === 'medical') return 'critical';
  if (domain === 'compliance' || domain === 'engine-room' || domain === 'electrical') return 'high';
  if (domain === 'bridge-navigation' || domain === 'deck-cargo') return 'high';
  return 'medium';
}

function inferHistoryWindow(policy: {
  isSmallTalk: boolean;
  isNonMaritime: boolean;
  asksCoding: boolean;
  asksMath: boolean;
  risk: TurnRisk;
}): number {
  if (policy.isSmallTalk) return 8;
  if (policy.asksMath) return 8;
  if (policy.isNonMaritime) return 8;
  if (policy.risk === 'critical') return 18;
  if (policy.risk === 'high') return 16;
  return 12;
}

function inferResponseStyle(policy: {
  message: string;
  isSmallTalk: boolean;
  isNonMaritime: boolean;
  needsClarification: boolean;
  isBareTopicPrompt: boolean;
  asksCoding: boolean;
  asksMath: boolean;
  risk: TurnRisk;
}): ResponseStyle {
  const lower = normalizeWhitespace(policy.message).toLowerCase();

  if (policy.isSmallTalk) return 'conversational';
  if (policy.needsClarification) return 'clarify';
  if (policy.asksCoding) return 'code';
  if (policy.asksMath) return 'numeric';
  if (policy.risk === 'critical') return 'checklist';
  if (
    /\b(?:steps?|procedure|checklist|immediate actions?|what should we do|what should the crew do|what should we take|safe next checks|before resuming|priorities|summary of actions|what checks must|respond first)\b/i.test(
      lower,
    )
  ) {
    return 'checklist';
  }
  if (policy.isBareTopicPrompt || /\b(?:what is|explain|describe|summari[sz]e|limits|difference|meaning|why)\b/i.test(lower)) {
    return 'direct';
  }
  if (policy.isNonMaritime) return 'direct';
  return 'direct';
}

function buildTuning(policy: {
  thinkMode: ThinkMode;
  responseStyle: ResponseStyle;
  isSmallTalk: boolean;
  isNonMaritime: boolean;
  needsClarification: boolean;
  asksCoding: boolean;
  asksMath: boolean;
  risk: TurnRisk;
}): GenerationPolicy {
  const base = policy.thinkMode === 'think' ? BASE_THINK : BASE_NO_THINK;
  const tuning: GenerationPolicy = {
    ...base,
    maxOutputTokens: policy.thinkMode === 'think' ? 420 : 280,
  };

  if (policy.thinkMode === 'think') {
    tuning.thinkingBudgetTokens = 128;
    tuning.thinkingBudgetMessage = 'Wrap up the reasoning and provide the final answer now.';
  }

  if (policy.responseStyle === 'numeric') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.25 : 0.18;
    tuning.top_p = policy.thinkMode === 'think' ? 0.7 : 0.55;
    tuning.top_k = 8;
    tuning.presence_penalty = 0;
    tuning.frequency_penalty = 0;
    tuning.maxOutputTokens = 96;
    tuning.thinkingBudgetTokens = 64;
    return tuning;
  }

  if (policy.responseStyle === 'code') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.28 : 0.2;
    tuning.top_p = policy.thinkMode === 'think' ? 0.85 : 0.72;
    tuning.top_k = 16;
    tuning.presence_penalty = 0.05;
    tuning.frequency_penalty = 0.02;
    tuning.maxOutputTokens = 320;
    tuning.thinkingBudgetTokens = 80;
    return tuning;
  }

  if (policy.responseStyle === 'clarify') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.38 : 0.3;
    tuning.top_p = 0.7;
    tuning.top_k = 12;
    tuning.maxOutputTokens = policy.risk === 'high'
      ? (policy.thinkMode === 'think' ? 448 : 416)
      : 160;
    tuning.thinkingBudgetTokens = 48;
    return tuning;
  }

  if (policy.responseStyle === 'conversational') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.72 : 0.78;
    tuning.top_p = 0.9;
    tuning.top_k = 24;
    tuning.presence_penalty = policy.thinkMode === 'think' ? 0.7 : 1.05;
    tuning.frequency_penalty = policy.thinkMode === 'think' ? 0.08 : 0.12;
    tuning.maxOutputTokens = 120;
    tuning.thinkingBudgetTokens = 48;
    return tuning;
  }

  if (policy.risk === 'critical') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.52 : 0.48;
    tuning.top_p = policy.thinkMode === 'think' ? 0.88 : 0.74;
    tuning.top_k = 20;
    tuning.presence_penalty = policy.thinkMode === 'think' ? 0.2 : 0.28;
    tuning.frequency_penalty = 0.05;
    tuning.maxOutputTokens = policy.thinkMode === 'think' ? 560 : 480;
    tuning.thinkingBudgetTokens = 192;
    return tuning;
  }

  if (policy.responseStyle === 'checklist') {
    tuning.temperature = policy.thinkMode === 'think' ? 0.58 : 0.62;
    tuning.top_p = policy.thinkMode === 'think' ? 0.9 : 0.78;
    tuning.top_k = 20;
    tuning.presence_penalty = policy.thinkMode === 'think' ? 0.28 : 0.45;
    tuning.frequency_penalty = 0.06;
    tuning.maxOutputTokens = policy.risk === 'high'
      ? (policy.thinkMode === 'think' ? 480 : 420)
      : (policy.thinkMode === 'think' ? 420 : 360);
    tuning.thinkingBudgetTokens = policy.risk === 'high' ? 160 : 128;
    return tuning;
  }

  tuning.temperature = policy.thinkMode === 'think' ? 0.64 : 0.68;
  tuning.top_p = policy.thinkMode === 'think' ? 0.92 : 0.82;
  tuning.top_k = 20;
  tuning.presence_penalty = policy.thinkMode === 'think' ? 0.4 : 0.65;
  tuning.frequency_penalty = policy.thinkMode === 'think' ? 0.05 : 0.08;
  tuning.maxOutputTokens = policy.risk === 'high'
    ? (policy.thinkMode === 'think' ? 448 : 416)
    : (policy.thinkMode === 'think' ? 280 : 220);

  if (policy.isNonMaritime && !policy.asksCoding && !policy.asksMath) {
    tuning.maxOutputTokens = policy.thinkMode === 'think' ? 220 : 180;
  }

  return tuning;
}

function buildSystemOverlay(policy: {
  thinkMode: ThinkMode;
  crewContext: string;
  domain: TurnDomain;
  risk: TurnRisk;
  responseStyle: ResponseStyle;
  isSmallTalk: boolean;
  isNonMaritime: boolean;
  needsClarification: boolean;
  isBareTopicPrompt: boolean;
  asksCoding: boolean;
  asksMath: boolean;
  asksCreative: boolean;
}): string {
  const lines = [
    `Qwen mode control: /${policy.thinkMode}`,
    `Turn context: ${policy.crewContext}.`,
    'Understand the user intent before answering. Match the user tone, but stay calm, clear, and professional.',
    'Do not let old training templates dominate the answer. Choose the response shape that matches this turn.',
    'If the user message is incomplete or ends with a dangling fragment, ask one short clarifying question instead of guessing.',
    'If the user gives only a short topic phrase such as "MARPOL ECA limits" or "Fuel leak in purifier", treat it as a request for a concise practical explanation of that topic.',
    'Do not output generic placeholder lines such as "Do not: continue the unsafe action..." or "Escalate to: Master, Chief Engineer" unless the scenario clearly justifies them.',
    'Never use headings like "ENGINE ROOM CONTEXT", "TECHNICAL LOGIC", "NUMERICAL PRECISION", "Immediate Control", "Verification Inputs", "Corrective Action", "Documentation/Communication", "Do Not", or "Escalate To".',
    'Do not force numbered checklists unless this turn truly needs a checklist.',
  ];

  if (policy.thinkMode === 'think') {
    lines.push('In hidden reasoning, first decide: user intent, whether previous context is relevant, and the best response style. Only then draft the final answer.');
  }

  if (policy.isSmallTalk) {
    lines.push('This is a conversational turn, not an emergency response.');
    lines.push('Reply in 1-3 natural sentences like a polite helpful chatbot.');
    lines.push('Do not force maritime incidents, alarms, compliance language, or numbered steps into greetings or casual chat.');
    lines.push('You may briefly mention that you can help with ship operations, safety, compliance, and troubleshooting after answering naturally.');
  } else if (policy.isNonMaritime) {
    lines.push('This turn is outside the app main maritime scope. Start with exactly one short sentence noting that, then answer directly and briefly.');
    lines.push('Do not force shipboard alarms, checklists, or compliance language into this answer.');
    lines.push('If the user asks for coding, provide concrete runnable code. If the user asks for math, give the final numeric result clearly.');
  } else {
    switch (policy.domain) {
      case 'engine-room':
      case 'electrical':
        lines.push('Use engine-room language. Say what to slow, stop, isolate, place on standby, or monitor.');
        lines.push('For troubleshooting, give: immediate checks, likely causes, safe next checks, and when to escalate to the Chief Engineer or bridge.');
        break;
      case 'bridge-navigation':
        lines.push('Use bridge watch language with concise navigational priorities, lookout, communications, and rule-based cautions.');
        break;
      case 'deck-cargo':
        lines.push('Use deck and cargo language. Focus on checks, coordination, stability, permits, and stop-work triggers.');
        break;
      case 'compliance':
        lines.push('For compliance questions, separate what must be done, what must be recorded, what must be reported, and what depends on flag, class, company SMS, terminal, or port rules.');
        lines.push('Do not invent certificate validity, legal approvals, or exact statutory values when not provided.');
        break;
      case 'medical':
        lines.push('For medical questions, prioritize scene safety, airway/breathing/circulation, telemedical contact, and rapid escalation to the Master.');
        lines.push('Mention telemedical support when the case is acute or worsening.');
        break;
      default:
        lines.push('Stay conversational first, then become structured only if the user needs a practical action answer.');
        break;
    }
  }

  if (policy.asksMath) {
    lines.push('Give the final numeric result first. Add only a very short explanation if it helps.');
  }

  if (policy.asksCreative) {
    lines.push('Keep the response clean and human, not textbook-like or robotic.');
  }

  if (policy.responseStyle === 'clarify') {
    lines.push('Ask exactly one short clarifying question. Do not provide the full answer yet.');
  } else if (policy.responseStyle === 'conversational') {
    lines.push('Answer in 1-3 natural sentences. Do not turn this into a checklist or a lecture.');
  } else if (policy.responseStyle === 'direct') {
    lines.push('Lead with a short natural answer in plain English. Use short paragraphs or a few bullets only if they help.');
  } else if (policy.responseStyle === 'checklist') {
    lines.push('Lead with a one-line direct answer, then give a short numbered checklist with only the necessary steps.');
  } else if (policy.responseStyle === 'code') {
    lines.push('Provide the code first, then add only a brief note if needed.');
  } else if (policy.responseStyle === 'numeric') {
    lines.push('Give the final numeric result first and keep everything else minimal.');
  }

  if (policy.isBareTopicPrompt && policy.responseStyle === 'direct') {
    lines.push('Treat the prompt as a topic request and answer it directly without complaining that the question is short.');
  }

  if (policy.risk === 'critical') {
    lines.push('Critical safety rule: give immediate life, vessel, cargo, machinery, or pollution-control actions before asking follow-up questions.');
    lines.push('Ask at most two targeted clarifying questions after the first safe actions are already stated.');
    lines.push('End with what must be monitored, logged, reported, or escalated.');
  }

  return lines.join('\n');
}

export function appendModeControlInstruction(content: string, thinkMode: ThinkMode): string {
  const trimmed = String(content || '').trim();
  if (!trimmed) return `/${thinkMode}`;
  if (/(?:^|\n)\/(?:think|no_think)\s*$/i.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed}\n/${thinkMode}`;
}

export function rewriteLatestUserMessageForInference(message: string, policy: TurnPolicy): string {
  const trimmed = normalizeWhitespace(message);
  if (!trimmed) return trimmed;

  if (policy.responseStyle === 'clarify') {
    return `${trimmed}\nAsk one short clarifying question before answering fully.`;
  }

  if (policy.responseStyle === 'conversational') {
    return `${trimmed}\nReply naturally and briefly with no checklist.`;
  }

  if (policy.responseStyle === 'direct' && policy.isBareTopicPrompt) {
    return `Explain this topic briefly and practically for a seafarer: ${trimmed}`;
  }

  if (policy.responseStyle === 'numeric') {
    return `${trimmed}\nGive the final numeric result first.`;
  }

  if (policy.responseStyle === 'code') {
    return `${trimmed}\nProvide concrete runnable code.`;
  }

  if (policy.responseStyle === 'checklist') {
    return `${trimmed}\nStart with the direct answer, then give only the necessary practical steps.`;
  }

  return trimmed;
}

export function buildRawPromptSpec(
  messages: Array<{ role: string; content: string }>,
  policy: TurnPolicy,
): { prompt: string; stop: string[] } {
  const prepared = messages
    .filter((message) => ['user', 'assistant', 'system'].includes(message.role))
    .map((message) => ({
      role: message.role,
      content: String(message.content || '').trim(),
    }))
    .filter((message) => message.content.length > 0);

  const latestUserIndex = (() => {
    for (let index = prepared.length - 1; index >= 0; index -= 1) {
      if (prepared[index].role === 'user') return index;
    }
    return -1;
  })();

  const renderedTurns = prepared.map((message, index) => {
    let content = message.content;
    if (message.role === 'user' && index === latestUserIndex) {
      content = appendModeControlInstruction(
        rewriteLatestUserMessageForInference(content, policy),
        policy.thinkMode,
      );
    }

    if (message.role === 'assistant') return `Assistant: ${content}`;
    if (message.role === 'system') return `System: ${content}`;
    return `User: ${content}`;
  });

  const prompt = [
    RAW_PROMPT_SYSTEM_PREFIX,
    policy.systemOverlay,
    ...renderedTurns,
    'Assistant:',
  ]
    .filter(Boolean)
    .join('\n\n');

  return {
    prompt,
    stop: ['\nUser:', '\nSystem:'],
  };
}

export function inferTurnPolicy(lastUserMessage: string, thinkMode: ThinkMode): TurnPolicy {
  return buildTurnPolicy(lastUserMessage, thinkMode);
}

export function inferTurnPolicyWithOverrides(
  lastUserMessage: string,
  thinkMode: ThinkMode,
  overrides: TurnPolicyOverrides,
): TurnPolicy {
  return buildTurnPolicy(lastUserMessage, thinkMode, overrides);
}

function buildTurnPolicy(
  lastUserMessage: string,
  thinkMode: ThinkMode,
  overrides: TurnPolicyOverrides = {},
): TurnPolicy {
  const message = normalizeWhitespace(lastUserMessage);
  const isSmallTalk = detectSmallTalk(message);
  const asksCoding = CODING_REGEX.test(message);
  const asksMath = MATH_REGEX.test(message) || /\b\d+\s*[\+\-\*\/x]\s*\d+\b/.test(message);
  const asksCreative = CREATIVE_REGEX.test(message);
  const isLiveNewsQuery = LIVE_NEWS_REGEX.test(message);
  const isBareTopicPrompt = detectBareTopicPrompt(message);
  const hasShipContext = SHIP_CONTEXT_REGEX.test(message);
  const isNonMaritime = !isSmallTalk && !hasShipContext;
  const { crewContext, domain } = inferDomainProfile(message, isSmallTalk, isNonMaritime);
  const needsClarification = detectNeedsClarification(message, isBareTopicPrompt, isSmallTalk);
  const risk = inferRisk(message, domain, isSmallTalk, isNonMaritime);
  const responseStyle = inferResponseStyle({
    message,
    isSmallTalk,
    isNonMaritime,
    needsClarification,
    isBareTopicPrompt,
    asksCoding,
    asksMath,
    risk,
  });

  const policyBase = {
    thinkMode,
    crewContext,
    domain,
    risk,
    responseStyle,
    isNonMaritime,
    isLiveNewsQuery,
    needsClarification,
    isBareTopicPrompt,
    isSmallTalk,
    asksCoding,
    asksMath,
    asksCreative,
  } as const;

  const mergedBase = {
    ...policyBase,
    ...overrides,
    domain: overrides.domain ?? policyBase.domain,
    crewContext:
      overrides.crewContext ??
      (overrides.domain ? defaultCrewContextForDomain(overrides.domain) : policyBase.crewContext),
    risk: overrides.risk ?? policyBase.risk,
    responseStyle: overrides.responseStyle ?? policyBase.responseStyle,
    isNonMaritime:
      overrides.isNonMaritime ?? (overrides.domain === 'out-of-domain' ? true : policyBase.isNonMaritime),
    isSmallTalk:
      overrides.isSmallTalk ?? (overrides.domain === 'general-chat' ? true : policyBase.isSmallTalk),
    needsClarification: overrides.needsClarification ?? policyBase.needsClarification,
    isBareTopicPrompt: overrides.isBareTopicPrompt ?? policyBase.isBareTopicPrompt,
    asksCoding: overrides.asksCoding ?? policyBase.asksCoding,
    asksMath: overrides.asksMath ?? policyBase.asksMath,
    asksCreative: overrides.asksCreative ?? policyBase.asksCreative,
  };

  return {
    ...mergedBase,
    historyWindow: inferHistoryWindow(mergedBase),
    systemOverlay: buildSystemOverlay(mergedBase),
    tuning: buildTuning(mergedBase),
  };
}
