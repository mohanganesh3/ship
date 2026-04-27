import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import buildPromptBank from './promptBank.mjs';
import {
  appendModeControlInstruction,
  buildRawPromptSpec,
  inferTurnPolicy,
  rewriteLatestUserMessageForInference,
} from '../../services/inferencePolicy.ts';
import { DEFAULT_SYSTEM_PROMPT, MODEL_STOP_WORDS } from '../../constants/model.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.join(__dirname, 'output');
const BASE_URL = process.env.LLAMA_BASE_URL || 'http://127.0.0.1:8080';
const MODEL = process.env.LLAMA_MODEL || 'model.gguf';
const REASONING_FORMAT = 'deepseek';
const BAD_TEMPLATE_MARKER_REGEX =
  /\b(?:ENGINE ROOM CONTEXT|TECHNICAL LOGIC|NUMERICAL PRECISION|IMMEDIATE CONTROL|VERIFICATION INPUTS|CORRECTIVE ACTION|DOCUMENTATION\/COMMUNICATION|OPERATIONAL LOGIC|LIMITS & LIMITATIONS|ENGINE ROOM SAFETY CONTEXT)\b/i;
const GENERIC_FILLER_REGEX =
  /\bdo not:\s*continue the unsafe action|escalate to:\s*(?:master|chief engineer|rcc|mrcc|the chief engineer or master)\b/i;
const CRITICAL_ACTION_REGEX =
  /\b(immediate|immediately|first|stop|isolate|alarm|muster|reduce load|boundary cool|secure ventilation|shut\s*off|extinguish|activate|inform bridge)\b/i;

const SMOKE_PROMPT_IDS = [
  'math-001',
  'math-002',
  'coding-001',
  'coding-002',
  'safety-001',
  'safety-002',
  'compliance-001',
  'compliance-002',
  'operations-001',
  'operations-002',
  'mach-001',
  'mach-002',
];

function getSmokePrompts() {
  const all = buildPromptBank(9999);
  return SMOKE_PROMPT_IDS
    .map((id) => all.find((entry) => entry.id === id))
    .filter(Boolean);
}

function mdEscape(v) {
  return String(v ?? '').replace(/\|/g, '\\|');
}

function buildFewShotMessages(policy) {
  switch (policy.domain) {
    case 'compliance':
      return [
        {
          role: 'user',
          content:
            'Explain practical onboard compliance for fuel oil changeover before entering an ECA. Include what must be logged and what must be reported.\n/no_think',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Complete fuel changeover before ECA entry and record the changeover details in the required logbook.\n1. Log the date, time, ship position, completion of changeover, and compliant fuel quantity in each relevant tank.\n2. Report any inability to comply, equipment failure, or fuel non-availability through company, flag, and port procedures.\n3. What is accepted can depend on approved equivalent arrangements, local port rules, company SMS, and Administration requirements.',
        },
      ];
    case 'engine-room':
    case 'electrical':
      return [
        {
          role: 'user',
          content:
            'Main engine low lube oil pressure alarm while underway. Give immediate actions, likely causes, and safe next checks.\n/no_think',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Treat low lube oil pressure as a protection issue.\n1. Reduce load and be ready to stop or change over if pressure does not recover within maker limits.\n2. Verify local pressure, oil level, filters, pump suction, and any visible leak before restart or load recovery.\n3. Likely causes: low oil level, blocked filter, pump fault, relief-valve issue, or bearing wear.\n4. Do not bypass protection or keep running just to clear the alarm.\n5. Log the alarm, actions, and defect and inform the Chief Engineer.',
        },
      ];
    case 'bridge-navigation':
    case 'deck-cargo':
      return [
        {
          role: 'user',
          content:
            'Shipboard scenario: pilot boarding preparation in rough sea. Give concise action checklist for bridge/deck team.\n/no_think',
        },
        {
          role: 'assistant',
          content:
            '1. Confirm lee, boarding side, speed, freeboard, and abort criteria with the Master and pilot station.\n2. Rig the pilot ladder exactly as required and keep deck and bridge communications explicit.\n3. Keep engines and helm ready throughout the approach.\n4. If the arrangement is unsafe, do not force boarding; coordinate a safer plan.\n5. Log the arrangements, delay, or abnormal condition.',
        },
      ];
    case 'medical':
      return [
        {
          role: 'user',
          content:
            'Medical emergency onboard: chest pain in engine room. What should the crew do first?\n/no_think',
        },
        {
          role: 'assistant',
          content:
            'Direct answer: Make the scene safe and stop the person from further work.\n1. Move them away from machinery hazards if possible and keep them at rest.\n2. Monitor airway, breathing, consciousness, and pulse.\n3. Prepare telemedical contact early and record onset time, symptoms, and vitals if taken.\n4. Inform the Master immediately and prepare medevac support if symptoms are severe or worsening.',
        },
      ];
    default:
      return [];
  }
}

function cleanAnswer(entry, text) {
  const raw = String(text || '')
    .replace(/<think>[\s\S]*?<\/think>/gi, ' ')
    .replace(/<\/?think>/gi, ' ')
    .replace(/<\|[^|]+\|>/g, ' ')
    .trim();

  if (!raw) return '';

  if (entry.category === 'math-sanity') {
    const strict = raw.match(/\b(?:72|4)\b/);
    if (strict) return strict[0];
  }

  if (entry.category === 'coding-random') {
    const fenceMatch = raw.match(/```[a-zA-Z]*\n([\s\S]*?)```/);
    if (fenceMatch) return `\`\`\`\n${fenceMatch[1].trim()}\n\`\`\``;
    if (/\b(def|function|const|let|class)\b/.test(raw)) {
      return `\`\`\`\n${raw.trim()}\n\`\`\``;
    }
  }

  return raw
    .split('\n')
    .map((line) => line.replace(/^\s*\d+\.\s*\*\*[A-Z /]+\*\*:\s*/i, '').trim())
    .filter(Boolean)
    .filter((line) => !/^citation\b/i.test(line))
    .join('\n')
    .trim();
}

function scoreAnswer(entry, answerText) {
  const content = String(answerText || '').toLowerCase();
  const normalized = content.replace(/\s+/g, ' ').trim();
  const issues = [];
  let score = 1;

  if (!normalized) {
    score = 0;
    issues.push('empty_answer');
  }

  if (entry.id === 'math-001') {
    const strictMath = normalized === '4' || /^\**\s*4\s*\**\.?$/.test(normalized);
    if (!strictMath) {
      score = Math.min(score, 0.2);
      issues.push('math_2_plus_2_incorrect');
    }
  }

  if (entry.id === 'math-002' && !/\b72\b/.test(content)) {
    score = Math.min(score, 0.3);
    issues.push('math_energy_incorrect');
  }

  if (entry.risk === 'critical') {
    const hasImmediate = /\b(immediate|immediately|first|stop|isolate|alarm|muster|emergency|reduce load)\b/.test(content);
    if (!hasImmediate) {
      score = Math.min(score, 0.4);
      issues.push('critical_no_immediate_action_language');
    }
  }

  if (entry.category === 'regulatory') {
    const hasCaveat = /\b(flag|class|sms|company|port state|local regulation|depends|port rules)\b/.test(content);
    if (!hasCaveat) {
      score = Math.min(score, 0.7);
      issues.push('regulatory_no_scope_caveat');
    }
  }

  if (entry.category === 'coding-random') {
    const hasCode = /```|\bfunction\b|\bdef\b|\bclass\b|\bconst\b|\blet\b/.test(answerText || '');
    if (!hasCode) {
      score = Math.min(score, 0.6);
      issues.push('coding_answer_without_code_signals');
    }
  }

  const looksLikeGenericSafetyTemplate =
    /do not:\s*continue the unsafe action|escalate to:\s*(master|chief engineer|rcc|mrcc)/.test(content);
  if ((entry.category === 'math-sanity' || entry.category === 'coding-random') && looksLikeGenericSafetyTemplate) {
    score = Math.min(score, 0.25);
    issues.push('off_topic_maritime_template');
  }

  return { score, issues };
}

function shouldRetryThinkFinalAnswer(policy, answerText) {
  const normalized = String(answerText || '')
    .replace(/<\|[^|]+\|>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  if (!normalized) return true;
  if (BAD_TEMPLATE_MARKER_REGEX.test(normalized)) return true;
  if (policy.asksMath && !/\b\d+(?:\.\d+)?\b/.test(normalized)) return true;
  if (policy.risk === 'critical' && !CRITICAL_ACTION_REGEX.test(normalized)) return true;
  if (policy.risk !== 'low' && GENERIC_FILLER_REGEX.test(normalized)) return true;
  return false;
}

async function callRawCompletion(prompt, stop, tuning) {
  const res = await fetch(`${BASE_URL}/completion`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt,
      n_predict: tuning.maxOutputTokens,
      stop: [...MODEL_STOP_WORDS, ...(stop || [])],
      temperature: tuning.temperature,
      top_p: tuning.top_p,
      top_k: tuning.top_k,
      min_p: tuning.min_p,
      repeat_penalty: tuning.repeat_penalty,
      presence_penalty: tuning.presence_penalty,
      frequency_penalty: tuning.frequency_penalty,
      penalty_repeat: tuning.repeat_penalty,
      penalty_present: tuning.presence_penalty,
      penalty_freq: tuning.frequency_penalty,
      penalty_last_n: tuning.penalty_last_n,
      dry_multiplier: tuning.dry_multiplier,
      dry_base: tuning.dry_base,
      dry_allowed_length: tuning.dry_allowed_length,
      dry_penalty_last_n: tuning.dry_penalty_last_n,
      dry_sequence_breakers: tuning.dry_sequence_breakers,
    }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  return { raw: data?.content || '', usedFallback: false };
}

async function callChatCompletion(messages, thinkMode, tuning) {
  const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: MODEL,
      stream: false,
      max_tokens: tuning.maxOutputTokens,
      temperature: tuning.temperature,
      top_p: tuning.top_p,
      top_k: tuning.top_k,
      min_p: tuning.min_p,
      repeat_penalty: tuning.repeat_penalty,
      presence_penalty: tuning.presence_penalty,
      frequency_penalty: tuning.frequency_penalty,
      reasoning_format: REASONING_FORMAT,
      chat_template_kwargs: {
        enable_thinking: thinkMode === 'think',
      },
      messages,
    }),
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  const msg = data?.choices?.[0]?.message || {};
  return {
    raw: msg?.content || '',
    reasoning: msg?.reasoning_content || '',
    usedFallback: false,
  };
}

async function runAppPath(entry, thinkMode) {
  const baseMessages = [{ role: 'user', content: entry.prompt }];
  const policy = inferTurnPolicy(entry.prompt, thinkMode);
  const useRawPrompt =
    thinkMode === 'no_think' ||
    policy.asksMath ||
    policy.needsClarification ||
    (thinkMode === 'think' && policy.isNonMaritime);

  if (useRawPrompt) {
    const rawPromptSpec = buildRawPromptSpec(baseMessages, policy);
    const result = await callRawCompletion(rawPromptSpec.prompt, rawPromptSpec.stop, policy.tuning);
    return {
      path: 'raw',
      policy,
      ...result,
    };
  }

  const userPrompt = appendModeControlInstruction(
    rewriteLatestUserMessageForInference(entry.prompt, policy),
    thinkMode,
  );
  const messages = [
    {
      role: 'system',
      content: [DEFAULT_SYSTEM_PROMPT, policy.systemOverlay].filter(Boolean).join('\n\n'),
    },
    ...buildFewShotMessages(policy),
    {
      role: 'user',
      content: userPrompt,
    },
  ];

  const primary = await callChatCompletion(messages, thinkMode, policy.tuning);
  if (thinkMode === 'think' && shouldRetryThinkFinalAnswer(policy, primary.raw)) {
    const fallbackPolicy = inferTurnPolicy(entry.prompt, 'no_think');
    const fallbackRawPromptSpec = buildRawPromptSpec(baseMessages, fallbackPolicy);
    const fallback = await callRawCompletion(
      fallbackRawPromptSpec.prompt,
      fallbackRawPromptSpec.stop,
      fallbackPolicy.tuning,
    );
    return {
      path: 'chat_fallback',
      policy,
      raw: fallback.raw,
      reasoning: primary.reasoning || '',
      usedFallback: true,
    };
  }

  return {
    path: 'chat',
    policy,
    ...primary,
  };
}

async function run() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const prompts = getSmokePrompts();
  const started = Date.now();
  const results = [];
  const modes = ['no_think', 'think'];

  for (const entry of prompts) {
    const modeResults = {};
    for (const mode of modes) {
      try {
        const answer = await runAppPath(entry, mode);
        const cleaned = cleanAnswer(entry, answer.raw);
        modeResults[mode] = {
          ...answer,
          cleaned,
          score: scoreAnswer(entry, cleaned),
          error: null,
        };
      } catch (error) {
        modeResults[mode] = {
          raw: '',
          cleaned: '',
          score: scoreAnswer(entry, ''),
          error: String(error?.message || error),
        };
      }
    }
    results.push({
      ...entry,
      modes: modeResults,
    });
  }

  const summary = {};
  for (const mode of modes) {
    const subset = results.map((r) => r.modes[mode]);
    summary[mode] = {
      meanScore: subset.reduce((acc, cur) => acc + cur.score.score, 0) / subset.length,
      errors: subset.filter((cur) => cur.error).length,
      rawPaths: subset.filter((cur) => cur.path === 'raw').length,
      fallbacks: subset.filter((cur) => cur.usedFallback).length,
    };
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    model: MODEL,
    prompts: prompts.length,
    runtimeSec: Number(((Date.now() - started) / 1000).toFixed(1)),
    summary,
    results,
  };

  await fs.writeFile(
    path.join(OUT_DIR, 'app-path.smoke.json'),
    JSON.stringify(payload, null, 2),
  );

  const lines = [];
  lines.push('# App Path Smoke Report');
  lines.push('');
  lines.push(`- Generated: ${payload.generatedAt}`);
  lines.push(`- Model: ${payload.model}`);
  lines.push(`- Base URL: ${payload.baseUrl}`);
  lines.push(`- Prompts: ${payload.prompts}`);
  lines.push(`- Runtime: ${payload.runtimeSec}s`);
  lines.push('');
  lines.push('| Mode | Mean score | Errors | Raw paths | Fallbacks |');
  lines.push('|---|---:|---:|---:|---:|');
  for (const mode of modes) {
    lines.push(
      `| ${mode} | ${summary[mode].meanScore.toFixed(3)} | ${summary[mode].errors} | ${summary[mode].rawPaths} | ${summary[mode].fallbacks} |`,
    );
  }
  lines.push('');

  for (const result of results) {
    lines.push(`## ${result.id} · ${result.category}`);
    lines.push('');
    lines.push(`Prompt: ${result.prompt}`);
    lines.push('');
    for (const mode of modes) {
      const item = result.modes[mode];
      lines.push(`### ${mode}`);
      lines.push(
        `- Score: ${item.score.score.toFixed(2)}${item.error ? ` (error: ${item.error})` : ''}`,
      );
      lines.push(`- Path: ${item.path || 'error'}`);
      if (item.score.issues.length) {
        lines.push(`- Issues: ${item.score.issues.map(mdEscape).join(', ')}`);
      }
      lines.push('');
      lines.push('Raw:');
      lines.push('```text');
      lines.push((item.raw || '[empty]').trim());
      lines.push('```');
      if (item.reasoning) {
        lines.push('');
        lines.push('Reasoning:');
        lines.push('```text');
        lines.push(String(item.reasoning).trim() || '[empty]');
        lines.push('```');
      }
      lines.push('');
      lines.push('Cleaned:');
      lines.push('```text');
      lines.push((item.cleaned || '[empty]').trim());
      lines.push('```');
      lines.push('');
    }
  }

  await fs.writeFile(path.join(OUT_DIR, 'app-path.smoke.md'), lines.join('\n'));
  console.log(JSON.stringify(payload.summary, null, 2));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
