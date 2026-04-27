import { inferTurnPolicy } from '../../services/inferencePolicy.ts';

const checks = [
  {
    name: 'greeting small talk',
    prompt: 'Hello',
    mode: 'no_think',
    expect: {
      domain: 'general-chat',
      risk: 'low',
      isSmallTalk: true,
      overlayIncludes: ['This is a conversational turn, not an emergency response.', '1-3 natural sentences'],
      maxTokensAtMost: 120,
    },
  },
  {
    name: 'engine-room critical alarm',
    prompt: 'Main engine crankcase mist detector alarm during full ahead. What immediate actions should we take?',
    mode: 'no_think',
    expect: {
      domain: 'engine-room',
      risk: 'critical',
      overlayIncludes: ['Engine room watch or engineering team', 'Critical safety rule', '/no_think'],
      maxTokensAtLeast: 480,
    },
  },
  {
    name: 'bridge watch scenario',
    prompt: 'As OOW at 0200 in restricted visibility, summarize safe bridge watch priorities.',
    mode: 'think',
    expect: {
      domain: 'bridge-navigation',
      risk: 'high',
      overlayIncludes: ['Bridge watch team or pilotage support', '/think', 'short topic phrase'],
      maxTokensAtLeast: 448,
    },
  },
  {
    name: 'compliance records',
    prompt: 'What records are required for MARPOL Annex VI fuel oil changeover before entering an ECA?',
    mode: 'no_think',
    expect: {
      domain: 'compliance',
      risk: 'high',
      overlayIncludes: ['what must be recorded', 'what must be reported'],
      maxTokensAtLeast: 400,
    },
  },
  {
    name: 'medical response',
    prompt: 'Medical emergency onboard: chest pain in engine room. What should the crew do first?',
    mode: 'think',
    expect: {
      domain: 'medical',
      risk: 'critical',
      overlayIncludes: ['telemedical', 'Critical safety rule'],
      maxTokensAtLeast: 480,
    },
  },
  {
    name: 'incomplete MARPOL fragment',
    prompt: 'What are the MARPOL regulations regarding',
    mode: 'no_think',
    expect: {
      domain: 'compliance',
      risk: 'high',
      needsClarification: true,
      overlayIncludes: ['ask one short clarifying question instead of guessing'],
      maxTokensAtLeast: 400,
    },
  },
  {
    name: 'quick chip compliance topic',
    prompt: 'MARPOL ECA limits',
    mode: 'think',
    expect: {
      domain: 'compliance',
      risk: 'high',
      isBareTopicPrompt: true,
      overlayIncludes: ['short topic phrase', '/think'],
      maxTokensAtLeast: 400,
    },
  },
  {
    name: 'oily bilge discharge classification',
    prompt: 'Can we discharge oily bilge water while alongside in port if the OWS is operational?',
    mode: 'no_think',
    expect: {
      domain: 'compliance',
      risk: 'high',
      overlayIncludes: ['what must be recorded', 'what must be reported'],
      maxTokensAtLeast: 400,
    },
  },
  {
    name: 'out-of-domain coding',
    prompt: 'Write a Python function that returns the first non-repeating character in a string.',
    mode: 'no_think',
    expect: {
      domain: 'out-of-domain',
      risk: 'low',
      isNonMaritime: true,
      overlayIncludes: ['outside the app main maritime scope', 'concrete runnable code'],
      maxTokensAtMost: 320,
    },
  },
  {
    name: 'out-of-domain math',
    prompt: 'What is 2+2? Give only the final numeric answer.',
    mode: 'no_think',
    expect: {
      domain: 'out-of-domain',
      risk: 'low',
      isNonMaritime: true,
      overlayIncludes: ['final numeric result'],
      maxTokensAtMost: 96,
    },
  },
];

for (const check of checks) {
  const policy = inferTurnPolicy(check.prompt, check.mode);

  if (policy.domain !== check.expect.domain) {
    throw new Error(`${check.name}: expected domain=${check.expect.domain}, got ${policy.domain}`);
  }
  if (policy.risk !== check.expect.risk) {
    throw new Error(`${check.name}: expected risk=${check.expect.risk}, got ${policy.risk}`);
  }
  if (typeof check.expect.isNonMaritime === 'boolean' && policy.isNonMaritime !== check.expect.isNonMaritime) {
    throw new Error(`${check.name}: expected isNonMaritime=${check.expect.isNonMaritime}, got ${policy.isNonMaritime}`);
  }
  if (typeof check.expect.isSmallTalk === 'boolean' && policy.isSmallTalk !== check.expect.isSmallTalk) {
    throw new Error(`${check.name}: expected isSmallTalk=${check.expect.isSmallTalk}, got ${policy.isSmallTalk}`);
  }
  if (typeof check.expect.needsClarification === 'boolean' && policy.needsClarification !== check.expect.needsClarification) {
    throw new Error(`${check.name}: expected needsClarification=${check.expect.needsClarification}, got ${policy.needsClarification}`);
  }
  if (typeof check.expect.isBareTopicPrompt === 'boolean' && policy.isBareTopicPrompt !== check.expect.isBareTopicPrompt) {
    throw new Error(`${check.name}: expected isBareTopicPrompt=${check.expect.isBareTopicPrompt}, got ${policy.isBareTopicPrompt}`);
  }
  for (const needle of check.expect.overlayIncludes) {
    if (!policy.systemOverlay.includes(needle)) {
      throw new Error(`${check.name}: system overlay missing "${needle}"`);
    }
  }
  if (
    typeof check.expect.maxTokensAtLeast === 'number' &&
    policy.tuning.maxOutputTokens < check.expect.maxTokensAtLeast
  ) {
    throw new Error(
      `${check.name}: expected maxOutputTokens >= ${check.expect.maxTokensAtLeast}, got ${policy.tuning.maxOutputTokens}`,
    );
  }
  if (
    typeof check.expect.maxTokensAtMost === 'number' &&
    policy.tuning.maxOutputTokens > check.expect.maxTokensAtMost
  ) {
    throw new Error(
      `${check.name}: expected maxOutputTokens <= ${check.expect.maxTokensAtMost}, got ${policy.tuning.maxOutputTokens}`,
    );
  }
}

console.log(`policy verification passed (${checks.length} cases)`);
