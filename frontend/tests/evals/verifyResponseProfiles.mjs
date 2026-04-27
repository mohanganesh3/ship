import { inferTurnPolicy } from '../../services/inferencePolicy.ts';
import {
  buildDeterministicReply,
  buildFewShotMessages,
} from '../../services/responseProfiles.ts';

const helloPolicy = inferTurnPolicy('Hello', 'no_think');
const helloReply = buildDeterministicReply(helloPolicy, 'Hello');

if (!helloReply) {
  throw new Error('hello greeting: expected deterministic reply');
}
if (/^\s*1\./.test(helloReply)) {
  throw new Error(`hello greeting: should not be a checklist -> ${helloReply}`);
}
if (/\b(?:immediately|ballast|muster|escalate to:|do not:)\b/i.test(helloReply)) {
  throw new Error(`hello greeting: picked up procedural language -> ${helloReply}`);
}

const thanksPolicy = inferTurnPolicy('Thanks', 'no_think');
const thanksReply = buildDeterministicReply(thanksPolicy, 'Thanks');

if (!thanksReply || !/welcome/i.test(thanksReply)) {
  throw new Error(`thanks reply: unexpected output -> ${thanksReply}`);
}

const numericPolicy = inferTurnPolicy('What is 2+2? Give only the final numeric answer.', 'no_think');
const numericExamples = buildFewShotMessages(numericPolicy);
if (!numericExamples.some((message) => message.role === 'assistant' && message.content.trim() === '4')) {
  throw new Error('numeric few-shot: missing strict numeric example');
}

const enginePolicy = inferTurnPolicy(
  'Main engine low lube oil pressure alarm while underway. Give immediate actions, likely causes, and safe next checks.',
  'no_think',
);
const engineExamples = buildFewShotMessages(enginePolicy);
if (engineExamples.length < 2) {
  throw new Error('engine-room few-shot: expected user and assistant example');
}

console.log('response profile verification passed');
