import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import buildPromptBank from './promptBank.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OUT_DIR = path.join(__dirname, 'output');
const BASE_URL = process.env.LLAMA_BASE_URL || 'http://127.0.0.1:8080';
const MODEL = process.env.LLAMA_MODEL || 'model.gguf';

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

  if (entry.id === 'math-002') {
    if (!/\b72\b/.test(content)) {
      score = Math.min(score, 0.3);
      issues.push('math_energy_incorrect');
    }
  }

  if (entry.risk === 'critical') {
    const hasImmediate = /\b(immediate|immediately|first|stop|isolate|alarm|muster|emergency)\b/.test(content);
    if (!hasImmediate) {
      score = Math.min(score, 0.4);
      issues.push('critical_no_immediate_action_language');
    }
  }

  if (entry.category === 'regulatory') {
    const hasCaveat = /\b(flag|class|sms|company|port state|local regulation|depends)\b/.test(content);
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

  const startsWithChecklist = /^\s*1\./.test(answerText || '');
  if ((entry.category === 'math-sanity' || entry.category === 'coding-random') && startsWithChecklist) {
    score = Math.min(score, 0.5);
    issues.push('format_mismatch_for_simple_query');
  }

  return { score, issues };
}

function stripTemplateLabels(line) {
  return line
    .replace(/^\s*\d+\.\s*\*\*(AESTHETIC & EXPERT CONTEXT|TECHNICAL LOGIC|NUMERICAL PRECISION|CITATION|ENGINE ROOM CONTEXT|IMMEDIATE CONTROL|VERIFICATION INPUTS|CORRECTIVE ACTION|DOCUMENTATION\/COMMUNICATION|DO NOT|ESCALATE TO)\*\*:\s*/i, '')
    .replace(/^\s*\d+\.\s*/i, '')
    .trim();
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

  const cleanedLines = raw
    .split('\n')
    .map((line) => stripTemplateLabels(line))
    .filter(Boolean)
    .filter((line) => !/^citation\b/i.test(line))
    .filter((line) => !(entry.category === 'math-sanity' || entry.category === 'coding-random') || !/^do not:/i.test(line))
    .filter((line) => !(entry.category === 'math-sanity' || entry.category === 'coding-random') || !/^escalate to:/i.test(line));

  return cleanedLines.join('\n').trim();
}

function buildRawPrompt(profileId, entry) {
  if (entry.category === 'math-sanity') {
    return {
      endpoint: '/completion',
      body: {
        prompt:
          profileId === 'raw_v2'
            ? `General question outside maritime scope.\nReturn only the final numeric answer on one line.\nQuestion: ${entry.prompt}\nAnswer:`
            : `Answer only with the final numeric answer.\nQuestion: ${entry.prompt}\nAnswer:`,
        n_predict: 40,
        temperature: profileId === 'raw_v2' ? 0.15 : 0.2,
        top_p: profileId === 'raw_v2' ? 0.4 : 0.5,
        top_k: 8,
        stop: ['\n'],
      },
    };
  }

  if (entry.category === 'coding-random') {
    const lang = /javascript|typescript/i.test(entry.prompt)
      ? 'javascript'
      : /python/i.test(entry.prompt)
        ? 'python'
        : 'text';
    return {
      endpoint: '/completion',
      body: {
        prompt:
          profileId === 'raw_v2'
            ? `General question outside maritime scope.\nOutput only ${lang} code in one fenced block.\nTask: ${entry.prompt}\n\`\`\`${lang}\n`
            : `Output only ${lang} code in one fenced block.\nTask: ${entry.prompt}\n\`\`\`${lang}\n`,
        n_predict: 220,
        temperature: profileId === 'raw_v2' ? 0.24 : 0.28,
        top_p: profileId === 'raw_v2' ? 0.55 : 0.6,
        top_k: 12,
        stop: ['```'],
      },
    };
  }

  if (entry.category === 'regulatory') {
    return {
      endpoint: '/completion',
      body: {
        prompt:
          profileId === 'raw_v2'
            ? `Role: Compliance officer onboard vessel\nQuestion: ${entry.prompt}\nRules: Keep it practical. Separate what must be logged, what must be reported, and what depends on flag, class, company SMS, or port rules. No citations. No invented rule numbers.\nAnswer:\n1.`
            : `Shipboard compliance answer.\nQuestion: ${entry.prompt}\nGive a concise practical answer. Include what must be logged, what must be reported, and what depends on flag, class, or company procedures.\nAnswer:\n1.`,
        n_predict: 200,
        temperature: profileId === 'raw_v2' ? 0.24 : 0.32,
        top_p: profileId === 'raw_v2' ? 0.62 : 0.72,
        top_k: 16,
        repeat_penalty: profileId === 'raw_v2' ? 1.05 : 1.02,
      },
    };
  }

  if (entry.risk === 'critical' || entry.category === 'machinery') {
    return {
      endpoint: '/completion',
      body: {
        prompt:
          profileId === 'raw_v2'
            ? `Role: Chief Engineer\nTask: Emergency engine-room response\nQuestion: ${entry.prompt}\nRules: Start with immediate actions. Then likely causes. Then safe next checks. Use short numbered steps. Do not invent readings, pressures, or citations. Do not add generic 'Do not' or 'Escalate to' lines unless directly relevant.\nAnswer:\n1.`
            : `Shipboard emergency checklist.\nScenario: ${entry.prompt}\nGive numbered immediate actions, likely causes, and safe next checks.\n1.`,
        n_predict: 220,
        temperature: profileId === 'raw_v2' ? 0.24 : 0.35,
        top_p: profileId === 'raw_v2' ? 0.62 : 0.72,
        top_k: profileId === 'raw_v2' ? 12 : 16,
        repeat_penalty: profileId === 'raw_v2' ? 1.05 : 1.02,
      },
    };
  }

  if (entry.category === 'bridge-deck' || entry.category === 'cargo') {
    return {
      endpoint: '/completion',
      body: {
        prompt:
          profileId === 'raw_v2'
            ? `Role: OOW or deck officer\nQuestion: ${entry.prompt}\nRules: Give only a short practical checklist for the bridge or deck team. No citations. No generic escalation line. No invented facts.\nAnswer:\n1.`
            : `Bridge or deck response.\nQuestion: ${entry.prompt}\nGive a concise action checklist.\n1.`,
        n_predict: 180,
        temperature: profileId === 'raw_v2' ? 0.24 : 0.34,
        top_p: profileId === 'raw_v2' ? 0.62 : 0.72,
        top_k: profileId === 'raw_v2' ? 12 : 16,
        repeat_penalty: profileId === 'raw_v2' ? 1.05 : 1.02,
      },
    };
  }

  return {
    endpoint: '/completion',
    body: {
      prompt: `Question: ${entry.prompt}\nAnswer:`,
      n_predict: 180,
      temperature: 0.3,
      top_p: 0.7,
      top_k: 16,
    },
  };
}

const PROFILES = [
  {
    id: 'chat_baseline',
    async run(entry) {
      const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: MODEL,
          stream: false,
          max_tokens: 220,
          temperature: 0.5,
          top_p: 0.8,
          top_k: 20,
          chat_template_kwargs: { enable_thinking: false },
          messages: [
            {
              role: 'system',
              content:
                'You are a shipboard maritime assistant. Prioritize safety-critical immediate action and practical checklists. If the question is not maritime, answer directly without ship-safety boilerplate.',
            },
            {
              role: 'user',
              content: entry.prompt,
            },
          ],
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();
      const raw = data?.choices?.[0]?.message?.content || data?.choices?.[0]?.message?.reasoning_content || '';
      return {
        raw,
        cleaned: cleanAnswer(entry, raw),
      };
    },
  },
  {
    id: 'raw_v1',
    async run(entry) {
      const spec = buildRawPrompt('raw_v1', entry);
      const res = await fetch(`${BASE_URL}${spec.endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec.body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();
      const raw = data?.content || '';
      return {
        raw,
        cleaned: cleanAnswer(entry, raw),
      };
    },
  },
  {
    id: 'raw_v2',
    async run(entry) {
      const spec = buildRawPrompt('raw_v2', entry);
      const res = await fetch(`${BASE_URL}${spec.endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec.body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();
      const raw = data?.content || '';
      return {
        raw,
        cleaned: cleanAnswer(entry, raw),
      };
    },
  },
];

async function run() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const prompts = getSmokePrompts();
  const started = Date.now();
  const results = [];

  for (const entry of prompts) {
    const profileResults = {};
    for (const profile of PROFILES) {
      try {
        const answer = await profile.run(entry);
        profileResults[profile.id] = {
          ...answer,
          score: scoreAnswer(entry, answer.cleaned),
          error: null,
        };
      } catch (error) {
        profileResults[profile.id] = {
          raw: '',
          cleaned: '',
          score: scoreAnswer(entry, ''),
          error: String(error?.message || error),
        };
      }
    }
    results.push({
      ...entry,
      profiles: profileResults,
    });
  }

  const summary = {};
  for (const profile of PROFILES) {
    const subset = results.map((r) => r.profiles[profile.id]);
    summary[profile.id] = {
      meanScore: subset.reduce((acc, cur) => acc + cur.score.score, 0) / subset.length,
      errors: subset.filter((cur) => cur.error).length,
    };
  }

  const winner = [...PROFILES]
    .map((p) => ({ id: p.id, ...summary[p.id] }))
    .sort((a, b) => b.meanScore - a.meanScore)[0];

  const payload = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    model: MODEL,
    prompts: prompts.length,
    runtimeSec: Number(((Date.now() - started) / 1000).toFixed(1)),
    winner,
    summary,
    results,
  };

  await fs.writeFile(
    path.join(OUT_DIR, 'profile-compare.smoke.json'),
    JSON.stringify(payload, null, 2),
  );

  const lines = [];
  lines.push('# Profile Comparison Report');
  lines.push('');
  lines.push(`- Generated: ${payload.generatedAt}`);
  lines.push(`- Model: ${payload.model}`);
  lines.push(`- Base URL: ${payload.baseUrl}`);
  lines.push(`- Prompts: ${payload.prompts}`);
  lines.push(`- Runtime: ${payload.runtimeSec}s`);
  lines.push(`- Winner: ${winner.id} (mean=${winner.meanScore.toFixed(3)})`);
  lines.push('');
  lines.push('| Profile | Mean score | Errors |');
  lines.push('|---|---:|---:|');
  for (const profile of PROFILES) {
    lines.push(`| ${profile.id} | ${summary[profile.id].meanScore.toFixed(3)} | ${summary[profile.id].errors} |`);
  }
  lines.push('');

  for (const result of results) {
    lines.push(`## ${result.id} · ${result.category}`);
    lines.push('');
    lines.push(`Prompt: ${result.prompt}`);
    lines.push('');
    for (const profile of PROFILES) {
      const item = result.profiles[profile.id];
      lines.push(`### ${profile.id}`);
      lines.push(`- Score: ${item.score.score.toFixed(2)}${item.error ? ` (error: ${item.error})` : ''}`);
      if (item.score.issues.length) {
        lines.push(`- Issues: ${item.score.issues.map(mdEscape).join(', ')}`);
      }
      lines.push('');
      lines.push('Raw:');
      lines.push('```text');
      lines.push((item.raw || '[empty]').trim());
      lines.push('```');
      lines.push('');
      lines.push('Cleaned:');
      lines.push('```text');
      lines.push((item.cleaned || '[empty]').trim());
      lines.push('```');
      lines.push('');
    }
  }

  await fs.writeFile(path.join(OUT_DIR, 'profile-compare.smoke.md'), lines.join('\n'));
  console.log(JSON.stringify(payload.winner, null, 2));
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
