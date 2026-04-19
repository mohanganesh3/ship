import * as FileSystem from 'expo-file-system/legacy';
import { initLlama } from 'llama.rn';
import {
  DEFAULT_SYSTEM_PROMPT,
  MODEL_DISPLAY_NAME,
  MODEL_RUNTIME_CONTEXT_TOKENS,
  MODEL_STOP_WORDS,
  RESERVED_OUTPUT_TOKENS,
} from '../constants/model';
import { useAppStore } from '../stores/appStore';
import { logger } from './Logger';
import { ModelProvisioner } from './ModelProvisioner';
import { PerformanceMonitor } from './PerformanceMonitor';
import {
  appendModeControlInstruction,
  inferTurnPolicy,
  inferTurnPolicyWithOverrides,
  rewriteLatestUserMessageForInference,
  type TurnDomain,
  type TurnPolicy,
  type TurnPolicyOverrides,
  type TurnRisk,
} from './inferencePolicy';
import { buildDeterministicReply, buildFewShotMessages } from './responseProfiles';

let llamaContext: any = null;
let loadPromise: Promise<void> | null = null;
let isGenerating = false;
const TAG = 'LLM-BRIDGE';
const MAX_CONTEXT_TOKENS = MODEL_RUNTIME_CONTEXT_TOKENS;
const MAX_PROMPT_TOKENS = MAX_CONTEXT_TOKENS - RESERVED_OUTPUT_TOKENS;
const MAX_DIALOGUE_MESSAGES = 20;

const THINK_OPEN_TAG = '<think>';
const THINK_CLOSE_TAG = '</think>';
const THINK_TAG_PREFIXES = [
  '<', '<t', '<th', '<thi', '<thin', '<think',
  '</', '</t', '</th', '</thi', '</thin', '</think',
];

const KNOWN_SPECIAL_TOKENS = [
  '<|im_start|>',
  '<|im_end|>',
  '<|endoftext|>',
  '<|eot_id|>',
  '<s>',
  '</s>',
];

type RouterResponseStyle =
  | 'conversational'
  | 'direct'
  | 'checklist'
  | 'clarify'
  | 'numeric'
  | 'code';

type RouterConfidence = 'low' | 'medium' | 'high';

interface RouterDecision {
  domain?: TurnDomain;
  risk?: TurnRisk;
  responseStyle?: RouterResponseStyle;
  crewContext?: string;
  confidence?: RouterConfidence;
  useHistory?: boolean;
}

interface RoutedTurn {
  policy: TurnPolicy;
  useHistory: boolean;
}

const ROUTER_SYSTEM_PROMPT = `You are a strict routing policy for a shipboard assistant.
Return exactly one JSON object and nothing else.

Allowed domain values:
- general-chat
- general-maritime
- engine-room
- bridge-navigation
- deck-cargo
- compliance
- medical
- electrical
- out-of-domain

Allowed risk values:
- low
- medium
- high
- critical

Allowed responseStyle values:
- conversational
- direct
- checklist
- clarify
- numeric
- code

Rules:
- Greetings, thanks, casual chat, or identity questions are general-chat with conversational style and low risk.
- Incomplete fragments or dangling prompts use responseStyle=clarify.
- Non-maritime coding requests use out-of-domain with responseStyle=code.
- Non-maritime calculations use out-of-domain with responseStyle=numeric.
- Prefer responseStyle=direct for explanations, topic questions, or knowledge requests.
- Use responseStyle=checklist only when the user explicitly wants steps/checks/actions or the situation is operational and safety-sensitive.
- Set useHistory=false when the latest user message starts a fresh topic, greeting, or unrelated request, even if earlier messages were about an emergency or procedure.
- Set useHistory=true only when the latest user message clearly depends on the previous turn or uses prior context.
- Regulatory, MARPOL, OWS, records, reporting, certificates, discharge permissions, and inspections use compliance.
- Engine room alarms, machinery faults, purifier, pump, bilge, boiler, or crankcase issues use engine-room.
- Bridge watch, navigation, pilotage, restricted visibility, COLREG, or ECDIS issues use bridge-navigation.
- Cargo, deck, mooring, loading, discharge, hatch, or ballast transfer issues use deck-cargo.
- Medical injuries, chest pain, collapse, burns, breathing, medevac, or telemedical issues use medical.
- Power failure, blackout, switchboard, breaker, earth fault, or emergency generator issues use electrical.
- If life, vessel, cargo, machinery, or pollution danger is immediate, set risk=critical.
- Use the dominant intent of the latest user message, not the older assistant reply.

Schema:
{"domain":"general-chat","risk":"low","responseStyle":"conversational","crewContext":"short phrase","confidence":"high","useHistory":false}`;

interface GenerateOptions {
  messages: Array<{ role: string; content: string }>;
  thinkMode: 'think' | 'no_think';
  onToken: (token: string) => void;
  onThinkToken?: (token: string) => void;
  onThinkStart?: () => void;
  onThinkEnd?: (thinkTime: number) => void;
  onComplete: (totalTokens: number) => void;
  onError?: (err: string) => void;
}

function pruneMessages(
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>
): Array<{ role: 'user' | 'assistant' | 'system'; content: string }> {
  const system = messages.find(m => m.role === 'system');
  const dialogue = messages.filter(m => m.role !== 'system');
  if (dialogue.length <= MAX_DIALOGUE_MESSAGES) return messages;
  const recent = dialogue.slice(-MAX_DIALOGUE_MESSAGES);
  return system ? [system, ...recent] : recent;
}

function injectFewShotMessages(
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>,
  examples: Array<{ role: 'user' | 'assistant'; content: string }>,
): Array<{ role: 'user' | 'assistant' | 'system'; content: string }> {
  if (!examples.length) return messages;

  const normalizedExamples = examples
    .map((example) => ({
      role: example.role,
      content: String(example.content || '').trim(),
    }))
    .filter((example) => example.content.length > 0);

  if (!normalizedExamples.length) return messages;

  const systemMessage = messages[0]?.role === 'system' ? messages[0] : null;
  const dialogue = systemMessage ? messages.slice(1) : messages;
  return systemMessage
    ? [systemMessage, ...normalizedExamples, ...dialogue]
    : [...normalizedExamples, ...dialogue];
}

async function buildInferenceMessages(
  messages: Array<{ role: string; content: string }>,
  thinkMode: 'think' | 'no_think',
): Promise<{
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>;
  policy: TurnPolicy;
}> {
  const prepared = messages
    .filter(m =>
      ['user', 'assistant', 'system'].includes(m.role) &&
      typeof m.content === 'string' &&
      m.content.trim().length > 0,
    )
    .map(m => ({
      role: m.role as 'user' | 'assistant' | 'system',
      content: m.content.trim(),
    }));

  const systemContent =
    prepared.find(m => m.role === 'system')?.content ?? DEFAULT_SYSTEM_PROMPT;
  const dialogue = prepared.filter(
    (m): m is { role: 'user' | 'assistant'; content: string } => m.role !== 'system',
  );
  const lastUserIndex = (() => {
    for (let index = dialogue.length - 1; index >= 0; index -= 1) {
      if (dialogue[index].role === 'user') return index;
    }
    return -1;
  })();
  const lastUserMessage = lastUserIndex === -1 ? '' : dialogue[lastUserIndex].content;
  const fallbackPolicy = inferTurnPolicy(lastUserMessage, thinkMode);
  const routedTurn = await routeTurnWithModel(dialogue, lastUserMessage, thinkMode);
  const policy = routedTurn?.policy ?? fallbackPolicy;
  const useHistory =
    routedTurn?.useHistory ??
    inferHistoryCarryFallback(dialogue, lastUserMessage, policy);
  const scopedDialogue = selectDialogueForTurn(dialogue, lastUserIndex, policy, useHistory);

  const scopedLastUserIndex = (() => {
    for (let index = scopedDialogue.length - 1; index >= 0; index -= 1) {
      if (scopedDialogue[index].role === 'user') return index;
    }
    return -1;
  })();

  const augmentedDialogue = scopedDialogue.map((message, index) => {
    if (message.role !== 'user' || index !== scopedLastUserIndex) return message;
    return {
      ...message,
      content: appendModeControlInstruction(
        rewriteLatestUserMessageForInference(message.content, policy),
        thinkMode,
      ),
    };
  });

  return {
    policy,
    messages: pruneMessages([
      {
        role: 'system',
        content: [systemContent, policy.systemOverlay].filter(Boolean).join('\n\n'),
      },
      ...augmentedDialogue,
    ]),
  };
}

function shouldPurgeDownloadedModel(err: unknown): boolean {
  const msg = String((err as any)?.message ?? err ?? '').toLowerCase();
  return (
    msg.includes('gguf') ||
    msg.includes('header') ||
    msg.includes('magic') ||
    msg.includes('tensor') ||
    msg.includes('failed to load') ||
    msg.includes('unable to load') ||
    msg.includes('not found') ||
    msg.includes('no such file') ||
    msg.includes('corrupt')
  );
}

function cleanToken(raw: string): string {
  return KNOWN_SPECIAL_TOKENS.reduce((acc, token) => acc.split(token).join(''), raw);
}

function extractFirstJsonObject(raw: string): string | null {
  let depth = 0;
  let start = -1;

  for (let index = 0; index < raw.length; index += 1) {
    const char = raw[index];
    if (char === '{') {
      if (depth === 0) start = index;
      depth += 1;
    } else if (char === '}') {
      if (depth === 0) continue;
      depth -= 1;
      if (depth === 0 && start !== -1) {
        return raw.slice(start, index + 1);
      }
    }
  }

  return null;
}

function parseRouterDecision(raw: string): RouterDecision | null {
  const json = extractFirstJsonObject(raw);
  if (!json) return null;

  try {
    const parsed = JSON.parse(json) as RouterDecision;
    const validDomains: TurnDomain[] = [
      'general-chat',
      'general-maritime',
      'engine-room',
      'bridge-navigation',
      'deck-cargo',
      'compliance',
      'medical',
      'electrical',
      'out-of-domain',
    ];
    const validRisks: TurnRisk[] = ['low', 'medium', 'high', 'critical'];
    const validStyles: RouterResponseStyle[] = [
      'conversational',
      'direct',
      'checklist',
      'clarify',
      'numeric',
      'code',
    ];
    const validConfidence: RouterConfidence[] = ['low', 'medium', 'high'];

    if (!parsed.domain || !validDomains.includes(parsed.domain)) return null;
    if (!parsed.risk || !validRisks.includes(parsed.risk)) return null;
    if (!parsed.responseStyle || !validStyles.includes(parsed.responseStyle)) return null;
    if (parsed.confidence && !validConfidence.includes(parsed.confidence)) return null;
    if (typeof parsed.useHistory !== 'undefined' && typeof parsed.useHistory !== 'boolean') return null;

    return {
      domain: parsed.domain,
      risk: parsed.risk,
      responseStyle: parsed.responseStyle,
      crewContext:
        typeof parsed.crewContext === 'string' ? parsed.crewContext.trim().slice(0, 80) : undefined,
      confidence: parsed.confidence ?? 'medium',
      useHistory: parsed.useHistory ?? true,
    };
  } catch {
    return null;
  }
}

function inferHistoryCarryFallback(
  dialogue: Array<{ role: 'user' | 'assistant'; content: string }>,
  lastUserMessage: string,
  policy: TurnPolicy,
): boolean {
  if (!dialogue.length) return false;
  if (policy.responseStyle === 'conversational') return false;
  if (policy.responseStyle === 'numeric' || policy.responseStyle === 'code') return false;

  const trimmed = lastUserMessage.trim().toLowerCase();
  if (!trimmed) return false;

  if (
    /^(?:and|also|then|so|why|how|what about|what if|can we|can you|should we|should i|same|continue|go on|tell me more)\b/.test(trimmed)
  ) {
    return true;
  }

  if (/\b(?:it|that|this|those|them|same|above|earlier|previous|your answer)\b/.test(trimmed)) {
    return true;
  }

  return false;
}

function selectDialogueForTurn(
  dialogue: Array<{ role: 'user' | 'assistant'; content: string }>,
  lastUserIndex: number,
  policy: TurnPolicy,
  useHistory: boolean,
): Array<{ role: 'user' | 'assistant'; content: string }> {
  if (lastUserIndex === -1) return [];
  if (!useHistory) return [dialogue[lastUserIndex]];

  const localWindow =
    policy.responseStyle === 'conversational'
      ? 2
      : policy.responseStyle === 'clarify'
        ? 4
        : policy.historyWindow;

  return dialogue.slice(Math.max(0, lastUserIndex + 1 - localWindow), lastUserIndex + 1);
}

function buildRouterTranscript(
  dialogue: Array<{ role: 'user' | 'assistant'; content: string }>,
  lastUserMessage: string,
): string {
  const history = dialogue
    .slice(-6)
    .map(message => `${message.role === 'assistant' ? 'Assistant' : 'User'}: ${message.content}`)
    .join('\n');

  return [
    'Conversation context:',
    history || '(no prior context)',
    '',
    'Latest user message:',
    lastUserMessage,
  ].join('\n');
}

function routingOverridesFromDecision(decision: RouterDecision): TurnPolicyOverrides {
  return {
    domain: decision.domain,
    risk: decision.risk,
    responseStyle: decision.responseStyle,
    crewContext: decision.crewContext,
    isNonMaritime: decision.domain === 'out-of-domain',
    isSmallTalk: decision.domain === 'general-chat',
    needsClarification: decision.responseStyle === 'clarify',
    asksCoding: decision.responseStyle === 'code',
    asksMath: decision.responseStyle === 'numeric',
  };
}

async function routeTurnWithModel(
  dialogue: Array<{ role: 'user' | 'assistant'; content: string }>,
  lastUserMessage: string,
  thinkMode: 'think' | 'no_think',
): Promise<RoutedTurn | null> {
  if (!llamaContext || !lastUserMessage.trim()) return null;

  let raw = '';

  await (llamaContext as any).completion(
    {
      messages: [
        { role: 'system', content: ROUTER_SYSTEM_PROMPT },
        { role: 'user', content: buildRouterTranscript(dialogue, lastUserMessage) },
      ],
      enable_thinking: false,
      n_predict: 160,
      stop: [...MODEL_STOP_WORDS, '\nUser:', '\nAssistant:'],
      temperature: 0.08,
      top_p: 0.2,
      top_k: 8,
      min_p: 0,
      repeat_penalty: 1.02,
      presence_penalty: 0,
      frequency_penalty: 0,
      penalty_repeat: 1.02,
      penalty_present: 0,
      penalty_freq: 0,
      penalty_last_n: 32,
      dry_multiplier: 0,
      dry_base: 1.75,
      dry_allowed_length: 2,
      dry_penalty_last_n: 0,
      dry_sequence_breakers: ['\n', ':', '"', '*'],
    },
    (data: { token?: string }) => {
      if (!data?.token) return;
      raw += cleanToken(data.token);
    },
  );

  const decision = parseRouterDecision(raw);
  if (!decision || decision.confidence === 'low') {
    logger.warn(TAG, `Router fallback: raw=${raw.trim() || '[empty]'}`);
    return null;
  }

  logger.info(
    TAG,
    `Router decision domain=${decision.domain} risk=${decision.risk} style=${decision.responseStyle} confidence=${decision.confidence} useHistory=${decision.useHistory}`,
  );

  return {
    policy: inferTurnPolicyWithOverrides(
      lastUserMessage,
      thinkMode,
      routingOverridesFromDecision(decision),
    ),
    useHistory: decision.useHistory ?? true,
  };
}

async function trimMessagesToContext(
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>,
  thinkMode: 'think' | 'no_think',
): Promise<Array<{ role: 'user' | 'assistant' | 'system'; content: string }>> {
  if (!llamaContext?.getFormattedChat || !llamaContext?.tokenize) {
    return pruneMessages(messages);
  }

  let candidate = [...messages];

  while (candidate.length > 2) {
    try {
      const formatted = await llamaContext.getFormattedChat(candidate, null, {
        enable_thinking: thinkMode === 'think',
      });
      const prompt = (formatted as any)?.prompt ?? '';
      const mediaPaths = (formatted as any)?.media_paths;
      const tokenized = await llamaContext.tokenize(prompt, { media_paths: mediaPaths });
      if ((tokenized?.tokens?.length ?? 0) <= MAX_PROMPT_TOKENS) {
        return candidate;
      }
    } catch (err) {
      logger.warn(TAG, `Token-aware pruning failed, falling back: ${String(err)}`);
      return pruneMessages(messages);
    }

    const firstDialogueIndex = candidate.findIndex(m => m.role !== 'system');
    if (firstDialogueIndex === -1) return candidate;
    candidate = candidate.filter((_, i) => i !== firstDialogueIndex);
  }

  return candidate;
}

export async function loadModel(): Promise<void> {
  const store = useAppStore.getState();
  if (llamaContext) {
    store.setModelStatus('active');
    store.setModelLoadProgress(1);
    return;
  }

  if (loadPromise) {
    logger.info(TAG, 'Awaiting active model load...');
    return loadPromise;
  }

  loadPromise = (async () => {
    store.setModelStatus('loading');
    store.setModelLoadProgress(0.08);

    try {
      const safety = await PerformanceMonitor.checkHardwareSafety();
      if (!safety.isSafe) {
        throw new Error('Hardware resources insufficient for local model inference.');
      }

      store.setModelLoadProgress(0.2);

      const modelPath = ModelProvisioner.getInternalModelPath();
      const exists = await ModelProvisioner.isModelProvisioned();
      if (!exists) {
        const err = new Error('REPROVISION_NEEDED');
        (err as any).needsReprovision = true;
        throw err;
      }

      store.setModelLoadProgress(0.4);
      logger.info(TAG, `Loading ${MODEL_DISPLAY_NAME} from: ${modelPath}`);

      llamaContext = await initLlama({
        model: modelPath,
        use_mmap: true,
        use_mlock: false,
        no_extra_bufts: true,
        n_ctx: MODEL_RUNTIME_CONTEXT_TOKENS,
        n_batch: 128,
        n_ubatch: 64,
        n_threads: 4,
        n_gpu_layers: 0,
        flash_attn_type: 'off',
      } as any);

      store.setModelLoadProgress(1);
      store.setModelStatus('active');
      logger.info(TAG, `${MODEL_DISPLAY_NAME} ready (ctx=${MODEL_RUNTIME_CONTEXT_TOKENS})`);
    } catch (err: any) {
      logger.error(TAG, 'loadModel failed', err);
      if (!err?.needsReprovision && shouldPurgeDownloadedModel(err)) {
        try {
          const base = FileSystem.documentDirectory!;
          await FileSystem.deleteAsync(base + '.maritime_done', { idempotent: true });
          await FileSystem.deleteAsync(base + 'model.gguf', { idempotent: true });
          logger.info(TAG, 'Corrupt model purged — will re-download on next launch.');
        } catch (cleanupErr) {
          logger.warn(TAG, `Could not purge model: ${String(cleanupErr)}`);
        }
      }
      store.setModelLoadProgress(0);
      store.setModelStatus('error');
      throw err;
    } finally {
      loadPromise = null;
    }
  })();

  return loadPromise;
}

export async function generateResponse(options: GenerateOptions): Promise<void> {
  const { messages, thinkMode, onToken, onThinkToken, onThinkStart, onThinkEnd, onComplete, onError } = options;

  if (isGenerating) {
    logger.warn(TAG, 'Already generating — ignoring duplicate call');
    return;
  }

  try {
    if (!llamaContext) {
      await loadModel();
    }
    if (!llamaContext) throw new Error('Cannot initialize LLM engine');

    isGenerating = true;
    let totalTokens = 0;
    let isThinking = false;
    let thinkStartMs = 0;
    let tagBuffer = '';

    const runtimeThinkMode: 'think' | 'no_think' = thinkMode;
    const inferenceInput = await buildInferenceMessages(messages, runtimeThinkMode);
    const policy = inferenceInput.policy;
    const tuning = policy.tuning;
    const lastUserMessage =
      [...messages].reverse().find((message) => message.role === 'user')?.content?.trim() ?? '';
    const deterministicReply = buildDeterministicReply(policy, lastUserMessage);

    if (deterministicReply) {
      logger.info(TAG, `Deterministic reply path domain=${policy.domain} style=${policy.responseStyle}`);
      onToken(deterministicReply);
      onComplete(Math.max(1, deterministicReply.split(/\s+/).filter(Boolean).length));
      return;
    }

    const preparedMessages = await trimMessagesToContext(
      injectFewShotMessages(inferenceInput.messages, buildFewShotMessages(policy)),
      runtimeThinkMode,
    );

    logger.logInference(
      'START',
      `msgs=${preparedMessages.length} mode=${runtimeThinkMode} domain=${policy.domain} risk=${policy.risk} temp=${tuning.temperature} max=${tuning.maxOutputTokens}`,
    );

    const startThinking = () => {
      if (isThinking) return;
      isThinking = true;
      thinkStartMs = Date.now();
      onThinkStart?.();
    };

    const endThinking = () => {
      if (!isThinking) return;
      isThinking = false;
      const dur = (Date.now() - thinkStartMs) / 1000;
      onThinkEnd?.(dur);
    };

    const emitChunk = (chunk: string) => {
      const clean = cleanToken(chunk);
      if (!clean) return;
      if (isThinking) {
        onThinkToken?.(clean);
      } else {
        onToken(clean);
      }
    };

    const pendingPrefixLen = (text: string): number => {
      let maxLen = 0;
      for (const prefix of THINK_TAG_PREFIXES) {
        if (text.endsWith(prefix)) maxLen = Math.max(maxLen, prefix.length);
      }
      return maxLen;
    };

    await (llamaContext as any).completion(
      {
        messages: preparedMessages,
        enable_thinking: runtimeThinkMode === 'think',
        reasoning_format: runtimeThinkMode === 'think' ? 'deepseek' : undefined,
        n_predict: tuning.maxOutputTokens,
        stop: MODEL_STOP_WORDS,
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
      },
      (data: { token: string; content?: string; reasoning_content?: string }) => {
        totalTokens++;

        // Always use raw tag parser via data.token.
        // data.content includes raw <think> tags for this model so the
        // structured path cannot be used — it would bypass tag splitting.
        const raw = data.token;
        if (!raw) return;

        tagBuffer += raw;

        while (true) {
          const openIdx = tagBuffer.indexOf(THINK_OPEN_TAG);
          const closeIdx = tagBuffer.indexOf(THINK_CLOSE_TAG);

          let nextIdx = -1;
          let nextTag: 'open' | 'close' | null = null;
          if (openIdx !== -1 && (closeIdx === -1 || openIdx < closeIdx)) {
            nextIdx = openIdx;
            nextTag = 'open';
          } else if (closeIdx !== -1) {
            nextIdx = closeIdx;
            nextTag = 'close';
          }

          if (nextIdx === -1 || !nextTag) break;

          if (nextIdx > 0) emitChunk(tagBuffer.slice(0, nextIdx));
          tagBuffer = tagBuffer.slice(
            nextIdx + (nextTag === 'open' ? THINK_OPEN_TAG.length : THINK_CLOSE_TAG.length),
          );

          if (nextTag === 'open') startThinking();
          else endThinking();
        }

        const keep = pendingPrefixLen(tagBuffer);
        const readyLen = tagBuffer.length - keep;
        if (readyLen > 0) {
          emitChunk(tagBuffer.slice(0, readyLen));
          tagBuffer = tagBuffer.slice(readyLen);
        }
      },
    );

    if (tagBuffer) {
      const clean = cleanToken(tagBuffer);
      if (clean) {
        if (isThinking) onThinkToken?.(clean);
        else onToken(clean);
      }
    }

    if (isThinking) endThinking();

    onComplete(totalTokens);
    logger.logInference('COMPLETE', `tokens=${totalTokens}`);
  } catch (err: any) {
    logger.error(TAG, 'generateResponse error', err);
    onError?.(err?.message || 'Inference failed');
    throw err;
  } finally {
    isGenerating = false;
  }
}

export async function abortGeneration(): Promise<void> {
  logger.info(TAG, 'Aborting generation');
  isGenerating = false;
  if (llamaContext) {
    try {
      await (llamaContext as any).stopCompletion();
    } catch {
      // ignore
    }
  }
}

export function unloadModel(): void {
  logger.info(TAG, 'Unloading model');
  llamaContext = null;
  loadPromise = null;
  isGenerating = false;
  const store = useAppStore.getState();
  store.setModelStatus('unloaded');
  store.setModelLoadProgress(0);
}
