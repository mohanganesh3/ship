import type { TurnPolicy } from './inferencePolicy';

export interface ChatExample {
  role: 'user' | 'assistant';
  content: string;
}

function normalizeWhitespace(value: string): string {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

export function buildDeterministicReply(
  policy: TurnPolicy,
  lastUserMessage: string,
): string | null {
  const trimmed = normalizeWhitespace(lastUserMessage);
  if (!trimmed) return null;

  const isConversationalTurn =
    policy.isSmallTalk ||
    (policy.domain === 'general-chat' && policy.responseStyle === 'conversational');

  if (!isConversationalTurn) return null;

  const lower = trimmed.toLowerCase();

  if (/\bwho are you\b/.test(lower)) {
    return "I'm Shipboard Maritime AI. I can help with ship operations, machinery, compliance, troubleshooting, and general onboard questions.";
  }

  if (/\bhow are you\b/.test(lower)) {
    return "I'm here and ready to help. Ask me about ship operations, machinery, compliance, troubleshooting, or any general onboard question.";
  }

  if (/\b(?:thanks|thank you|thx)\b/.test(lower)) {
    return "You're welcome. Send the next question whenever you're ready.";
  }

  if (/\b(?:bye|good night|see you)\b/.test(lower)) {
    return "Take care. I'll be here when you need me.";
  }

  return 'Hello. How can I help you today? I can help with ship operations, machinery, compliance, troubleshooting, or general onboard questions.';
}

export function buildFewShotMessages(policy: TurnPolicy): ChatExample[] {
  if (policy.isSmallTalk || policy.domain === 'general-chat') {
    return [
      { role: 'user', content: 'Hello' },
      {
        role: 'assistant',
        content:
          'Hello. How can I help you today? I can help with ship operations, machinery, compliance, troubleshooting, or general onboard questions.',
      },
    ];
  }

  if (policy.responseStyle === 'numeric') {
    return [
      {
        role: 'user',
        content: 'What is 2+2? Give only the final numeric answer.',
      },
      {
        role: 'assistant',
        content: '4',
      },
    ];
  }

  if (policy.responseStyle === 'code') {
    return [
      {
        role: 'user',
        content: 'Write a Python function that returns the first non-repeating character in a string.',
      },
      {
        role: 'assistant',
        content: `\`\`\`python
def first_non_repeating_char(text: str) -> str | None:
    counts = {}
    for char in text:
        counts[char] = counts.get(char, 0) + 1
    for char in text:
        if counts[char] == 1:
            return char
    return None
\`\`\``,
      },
    ];
  }

  if (policy.responseStyle === 'clarify') {
    return [
      {
        role: 'user',
        content: 'What are the MARPOL regulations regarding',
      },
      {
        role: 'assistant',
        content:
          'Which part do you mean: Annex I oily discharge, Annex VI fuel changeover, garbage, ballast water, or something else?',
      },
    ];
  }

  switch (policy.domain) {
    case 'compliance':
      return [
        {
          role: 'user',
          content:
            'Explain practical onboard compliance for fuel oil changeover before entering an ECA. Include what must be logged and what must be reported.',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Complete the fuel changeover before ECA entry and record the changeover details in the required logbook. Log the date, time, ship position, completion of changeover, and compliant fuel details, then report any inability to comply through company, flag, and port procedures. Final acceptance can depend on flag, class, company SMS, and local port rules.',
        },
      ];
    case 'engine-room':
    case 'electrical':
      return [
        {
          role: 'user',
          content:
            'Main engine low lube oil pressure alarm while underway. Give immediate actions, likely causes, and safe next checks.',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Treat low lube oil pressure as a protection issue. 1. Reduce load and be ready to stop if pressure does not recover within maker limits. 2. Verify local pressure, oil level, filters, pump suction, and visible leaks. 3. Likely causes include low oil level, blocked filter, pump fault, relief-valve issue, or bearing wear. 4. Do not bypass protection just to clear the alarm. 5. Log the alarm and inform the Chief Engineer.',
        },
      ];
    case 'bridge-navigation':
      return [
        {
          role: 'user',
          content:
            'As OOW in restricted visibility, summarize safe bridge watch priorities.',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Slow the situation down and keep bridge resource management tight. 1. Confirm safe speed, lookout, radar plotting, and sound signals. 2. Keep the Master informed early if risk or doubt is building. 3. Cross-check position, traffic, and ECDIS or radar information before altering course. 4. Log the restricted-visibility watch measures taken.',
        },
      ];
    case 'deck-cargo':
      return [
        {
          role: 'user',
          content:
            'Bulk carrier loading plan changed suddenly. What checks must the Chief Officer complete before resuming?',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Reconfirm stability, structure, and the safe loading sequence before restarting. 1. Recheck loading computer inputs, draft, trim, shear force, and bending moment. 2. Confirm hold distribution, ballast condition, and terminal sequence. 3. Stop if any limit or communication gap remains unresolved. 4. Record the change and brief the deck team and Master.',
        },
      ];
    case 'medical':
      return [
        {
          role: 'user',
          content:
            'Medical emergency onboard: chest pain in engine room. What should the crew do first?',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Make the scene safe and stop the person from working. 1. Move them away from machinery risk if possible and keep them at rest. 2. Monitor airway, breathing, consciousness, and pulse. 3. Inform the Master immediately and prepare telemedical contact early. 4. Record the time of onset, symptoms, and any vitals taken.',
        },
      ];
    default:
      return [];
  }
}
