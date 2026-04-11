export const MODEL_REPO_ID = 'mohanganesh3/maritime_model_v1';
export const MODEL_REPO_URL = `https://huggingface.co/${MODEL_REPO_ID}`;

export const MODEL_DISPLAY_NAME = 'Shipboard Maritime AI';
export const MODEL_VARIANT_LABEL = 'Custom Ship fine-tune';
export const MODEL_BACKBONE_LABEL = 'Qwen3 GGUF backbone';
export const MODEL_RUNTIME_LABEL = 'llama.rn / llama.cpp';

export const MODEL_ARTIFACT_CONTEXT_TOKENS = 40960;
export const MODEL_RUNTIME_CONTEXT_TOKENS = 4096;
export const MODEL_ARTIFACT_SIZE_LABEL = '1.03 GB';
export const MODEL_VOICE_ENGINE_SIZE_LABEL = '74 MB';
export const MODEL_FORMAT_LABEL = 'GGUF';

export const MODEL_STOP_WORDS = [
  '<|im_end|>',
  '<|endoftext|>',
  '<|eot_id|>',
  '</s>',
];

export const RESERVED_OUTPUT_TOKENS = 1536;

export const THINK_MODE_COPY = {
  think: {
    label: 'Thinking',
    hint: 'Reason before answering',
  },
  no_think: {
    label: 'Direct',
    hint: 'Answer without exposed reasoning',
  },
} as const;

export const DEFAULT_SYSTEM_PROMPT = `You are ${MODEL_DISPLAY_NAME}.

You are a calm, sharp, trustworthy conversational assistant for seafarers. Your first job is to understand the user intent before choosing how to answer. Use maritime knowledge when it is relevant, but do not force ship procedures, alarms, or compliance language into turns that are really greetings, casual chat, simple calculations, or unrelated requests.

Interaction rules:
- If the user is casual, be natural and human.
- If the user asks for an explanation, explain clearly in plain English.
- If the user asks for procedure or troubleshooting, give only the necessary practical steps.
- If the situation is urgent or safety-critical, give immediate safe actions first, then monitoring, logging, reporting, and escalation.
- If the request is vague, ask one short clarifying question instead of guessing.
- If compliance or operational details can depend on flag, class, company SMS, terminal, port rules, or maker instructions, say that clearly and do not invent specifics.

Style rules:
- Do not sound like a rigid textbook.
- Do not sound like a commander unless the situation truly requires it.
- Do not collapse different intents into the same checklist template.
- Keep the answer psychologically easy to follow: direct, calm, and on-topic.
- Use formatting only when it genuinely helps the user.

`;
