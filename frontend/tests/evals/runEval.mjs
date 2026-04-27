import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import buildPromptBank from './promptBank.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const OUT_DIR = path.join(__dirname, 'output');
const BASE_URL = process.env.LLAMA_BASE_URL || 'http://127.0.0.1:8080/v1';
const MODEL = process.env.LLAMA_MODEL || 'maritime_model_v1';
const PROFILE_DEFAULTS = {
  smoke: 12,
  standard: 30,
  full: 120,
};

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

function parseCliArgs(argv) {
  const parsed = {};

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];

    if (arg === '--profile' || arg === '-p') {
      parsed.profile = argv[i + 1];
      i += 1;
      continue;
    }

    if (arg === '--count') {
      parsed.count = Number(argv[i + 1]);
      i += 1;
      continue;
    }

    if (arg === '--offset') {
      parsed.offset = Number(argv[i + 1]);
      i += 1;
      continue;
    }

    if (arg === '--max-tokens') {
      parsed.maxTokens = Number(argv[i + 1]);
      i += 1;
      continue;
    }

    if (!arg.startsWith('-') && parsed.count == null) {
      parsed.count = Number(arg);
    }
  }

  return parsed;
}

function sanitizeNumber(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

function resolveProfile(value) {
  const profile = String(value || 'smoke').trim().toLowerCase();
  return profile in PROFILE_DEFAULTS ? profile : 'smoke';
}

function selectPrompts(profile, count, offset) {
  const allPrompts = buildPromptBank(9999);
  const basePrompts = profile === 'smoke'
    ? SMOKE_PROMPT_IDS
      .map((id) => allPrompts.find((entry) => entry.id === id))
      .filter(Boolean)
    : allPrompts;

  return {
    allPrompts,
    prompts: basePrompts.slice(offset, offset + count),
  };
}

function buildRunTag(profile, offset, promptCount) {
  const parts = [profile, `n${promptCount}`];
  if (offset > 0) {
    parts.push(`from${offset + 1}`);
  }
  return parts.join('-');
}

const cliArgs = parseCliArgs(process.argv.slice(2));
const PROFILE = resolveProfile(process.env.EVAL_PROFILE || cliArgs.profile || 'smoke');
const COUNT = sanitizeNumber(
  process.env.EVAL_COUNT ?? cliArgs.count ?? PROFILE_DEFAULTS[PROFILE],
  PROFILE_DEFAULTS[PROFILE],
);
const OFFSET = sanitizeNumber(process.env.EVAL_OFFSET ?? cliArgs.offset ?? 0, 0);
const MAX_TOKENS = sanitizeNumber(process.env.EVAL_MAX_TOKENS ?? cliArgs.maxTokens ?? 220, 220);

const { allPrompts, prompts } = selectPrompts(PROFILE, COUNT, OFFSET);
const RUN_TAG = buildRunTag(PROFILE, OFFSET, prompts.length);

if (prompts.length === 0) {
  throw new Error(`No prompts selected (profile=${PROFILE}, count=${COUNT}, offset=${OFFSET}).`);
}

function scoreAnswer(entry, answer) {
  const content = (answer?.content || '').toLowerCase();
  const normalized = content.replace(/\s+/g, ' ').trim();
  const issues = [];
  let score = 1;

  if (!content.trim()) {
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
    const hasCode = /```|\bfunction\b|\bdef\b|\bclass\b|\bconst\b|\bfn\b/.test(answer?.content || '');
    if (!hasCode) {
      score = Math.min(score, 0.6);
      issues.push('coding_answer_without_code_signals');
    }
  }

  const looksLikeGenericSafetyTemplate = /do not:\s*continue the unsafe action|escalate to:\s*(master|chief engineer|rcc|mrcc)/.test(content);
  if ((entry.category === 'math-sanity' || entry.category === 'coding-random') && looksLikeGenericSafetyTemplate) {
    score = Math.min(score, 0.25);
    issues.push('off_topic_maritime_template');
  }

  const startsWithChecklist = /^\s*1\./.test(answer?.content || '');
  if ((entry.category === 'math-sanity' || entry.category === 'coding-random') && startsWithChecklist) {
    score = Math.min(score, 0.5);
    issues.push('format_mismatch_for_simple_query');
  }

  return { score, issues };
}

async function chatOnce(prompt, enableThinking, temperature = 0.55) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);

  try {
    const res = await fetch(`${BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model: MODEL,
        stream: false,
        max_tokens: MAX_TOKENS,
        temperature,
        top_p: 0.95,
        top_k: 20,
        min_p: 0,
        repeat_penalty: 1.08,
        reasoning_format: 'deepseek',
        chat_template_kwargs: {
          enable_thinking: enableThinking,
        },
        messages: [
          {
            role: 'system',
            content: 'You are a shipboard maritime assistant. Prioritize safety-critical immediate action and practical checklists. Do not invent legal approvals or unsupported limits.',
          },
          {
            role: 'user',
            content: prompt,
          },
        ],
      }),
    });

    if (!res.ok) {
      const t = await res.text();
      throw new Error(`HTTP ${res.status}: ${t.slice(0, 300)}`);
    }

    const data = await res.json();
    const msg = data?.choices?.[0]?.message || {};

    return {
      content: msg?.content || '',
      reasoning_content: msg?.reasoning_content || '',
      usedFallback: false,
      raw: data,
    };
  } finally {
    clearTimeout(timeout);
  }
}

async function chatWithThinkFallback(prompt, enableThinking) {
  const primary = await chatOnce(prompt, enableThinking);
  const missingFinal = enableThinking && !String(primary.content || '').trim();
  if (!missingFinal) return primary;

  const fallback = await chatOnce(prompt, false, 0.5);
  return {
    ...fallback,
    reasoning_content: primary.reasoning_content || '',
    usedFallback: true,
  };
}

function mdEscape(v) {
  return String(v ?? '').replace(/\|/g, '\\|');
}

async function run() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const started = Date.now();

  const results = [];

  console.log(`[eval] base_url=${BASE_URL} model=${MODEL} profile=${PROFILE} prompts=${prompts.length} offset=${OFFSET}`);

  for (let i = 0; i < prompts.length; i += 1) {
    const p = prompts[i];
    console.log(`[eval] (${i + 1}/${prompts.length}) ${p.id} ${p.category}`);

    let think;
    let noThink;
    let thinkError = null;
    let noThinkError = null;

    try {
      think = await chatWithThinkFallback(p.prompt, true);
    } catch (e) {
      thinkError = String(e?.message || e);
      think = { content: '', reasoning_content: '', usedFallback: false, raw: null };
    }

    try {
      noThink = await chatOnce(p.prompt, false);
    } catch (e) {
      noThinkError = String(e?.message || e);
      noThink = { content: '', reasoning_content: '', usedFallback: false, raw: null };
    }

    const thinkScore = scoreAnswer(p, think);
    const noThinkScore = scoreAnswer(p, noThink);

    results.push({
      ...p,
      think,
      noThink,
      thinkScore,
      noThinkScore,
      thinkError,
      noThinkError,
    });
  }

  const elapsedSec = ((Date.now() - started) / 1000).toFixed(1);

  const summary = {
    generatedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    model: MODEL,
    profile: PROFILE,
    requestedCount: COUNT,
    offset: OFFSET,
    totalAvailablePrompts: allPrompts.length,
    runTag: RUN_TAG,
    prompts: prompts.length,
    elapsedSec: Number(elapsedSec),
    byMode: {
      think: {
        meanScore: results.reduce((a, r) => a + r.thinkScore.score, 0) / results.length,
        errors: results.filter((r) => r.thinkError).length,
        fallbackRuns: results.filter((r) => r.think.usedFallback).length,
      },
      noThink: {
        meanScore: results.reduce((a, r) => a + r.noThinkScore.score, 0) / results.length,
        errors: results.filter((r) => r.noThinkError).length,
      },
    },
    byCategory: {},
  };

  const categories = [...new Set(results.map((r) => r.category))];
  for (const c of categories) {
    const subset = results.filter((r) => r.category === c);
    summary.byCategory[c] = {
      count: subset.length,
      thinkMean: subset.reduce((a, r) => a + r.thinkScore.score, 0) / subset.length,
      noThinkMean: subset.reduce((a, r) => a + r.noThinkScore.score, 0) / subset.length,
    };
  }

  const resultsJson = JSON.stringify({ summary, results }, null, 2);
  await fs.writeFile(path.join(OUT_DIR, 'eval-results.json'), resultsJson);
  await fs.writeFile(path.join(OUT_DIR, `eval-results.${RUN_TAG}.json`), resultsJson);

  const lines = [];
  lines.push('# Maritime Model Evaluation Report');
  lines.push('');
  lines.push(`- Generated: ${summary.generatedAt}`);
  lines.push(`- Model: ${summary.model}`);
  lines.push(`- Profile: ${summary.profile}`);
  lines.push(`- Offset: ${summary.offset}`);
  lines.push(`- Total bank size: ${summary.totalAvailablePrompts}`);
  lines.push(`- Prompts: ${summary.prompts}`);
  lines.push(`- Runtime: ${summary.elapsedSec}s`);
  lines.push('');
  lines.push('## Mode-level summary');
  lines.push('');
  lines.push(`- Think mean score: ${summary.byMode.think.meanScore.toFixed(3)} (errors: ${summary.byMode.think.errors})`);
  lines.push(`- Think fallback runs (empty final answer recovered): ${summary.byMode.think.fallbackRuns}`);
  lines.push(`- No-think mean score: ${summary.byMode.noThink.meanScore.toFixed(3)} (errors: ${summary.byMode.noThink.errors})`);
  lines.push('');
  lines.push('## Category summary');
  lines.push('');
  lines.push('| Category | Count | Think mean | No-think mean |');
  lines.push('|---|---:|---:|---:|');
  for (const c of categories) {
    const s = summary.byCategory[c];
    lines.push(`| ${c} | ${s.count} | ${s.thinkMean.toFixed(3)} | ${s.noThinkMean.toFixed(3)} |`);
  }
  lines.push('');
  lines.push('## All answers (think vs no-think)');
  lines.push('');

  for (const r of results) {
    lines.push(`### ${r.id} · ${r.category} · risk=${r.risk}`);
    lines.push('');
    lines.push(`**Prompt**: ${r.prompt}`);
    lines.push('');
    lines.push(`**Think score**: ${r.thinkScore.score.toFixed(2)} ${r.thinkScore.issues.length ? `(issues: ${r.thinkScore.issues.join(', ')})` : ''}`);
    if (r.thinkError) lines.push(`**Think error**: ${r.thinkError}`);
    lines.push('');
    lines.push('**Think answer**');
    lines.push('');
    lines.push('```text');
    lines.push((r.think.content || '').trim() || '[empty]');
    lines.push('```');
    lines.push('');
    lines.push(`**No-think score**: ${r.noThinkScore.score.toFixed(2)} ${r.noThinkScore.issues.length ? `(issues: ${r.noThinkScore.issues.join(', ')})` : ''}`);
    if (r.noThinkError) lines.push(`**No-think error**: ${r.noThinkError}`);
    lines.push('');
    lines.push('**No-think answer**');
    lines.push('');
    lines.push('```text');
    lines.push((r.noThink.content || '').trim() || '[empty]');
    lines.push('```');
    lines.push('');
  }

  const reportMarkdown = lines.join('\n');
  await fs.writeFile(path.join(OUT_DIR, 'eval-report.md'), reportMarkdown);
  await fs.writeFile(path.join(OUT_DIR, `eval-report.${RUN_TAG}.md`), reportMarkdown);

  const failures = results.filter((r) => r.thinkScore.score < 0.7 || r.noThinkScore.score < 0.7 || r.thinkError || r.noThinkError);
  const failLines = ['# Evaluation Failure Buckets', ''];
  for (const f of failures) {
    failLines.push(`- ${f.id} (${f.category}): think=${f.thinkScore.score.toFixed(2)} no-think=${f.noThinkScore.score.toFixed(2)}; issues=[${[...f.thinkScore.issues, ...f.noThinkScore.issues].join(', ')}]`);
  }
  const failureMarkdown = failLines.join('\n');
  await fs.writeFile(path.join(OUT_DIR, 'eval-failures.md'), failureMarkdown);
  await fs.writeFile(path.join(OUT_DIR, `eval-failures.${RUN_TAG}.md`), failureMarkdown);

  console.log(`[eval] done. outputs in ${OUT_DIR}`);
}

run().catch((err) => {
  console.error('[eval] fatal:', err);
  process.exit(1);
});
