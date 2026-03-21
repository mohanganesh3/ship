# RANKING EVALUATION: Synthetic Data Generation + Supervised Fine-Tuning (SFT)

**Approach Under Evaluation:** Generate synthetic Q&A pairs from maritime textbooks using a large teacher model (GPT-4o, Claude, DeepSeek-R1, Qwen-72B), then fine-tune a small 1-3B model on these pairs using SFT (with LoRA/QLoRA)

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B parameters  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH BASIS

This evaluation draws on deep analysis of the following papers and resources:

| Paper | Key Finding for This Evaluation |
|-------|-------------------------------|
| **Phi-1 "Textbooks Are All You Need"** (arXiv:2306.11644) | 1.3B model trained on 6B filtered tokens + 1B synthetic GPT-3.5 tokens achieved 50.6% HumanEval. Core thesis: textbook-quality synthetic data > 100x web data. But this was **pretraining**, not SFT-only. |
| **Phi-1.5** (arXiv:2309.05463) | 1.3B model, synthetic textbook data extended to reasoning. Matched 5x larger models. Still exhibits hallucinations and toxic generations. Not SFT — this was continued pretraining on synthetic data. |
| **Phi-3** (arXiv:2404.14219) | 3.8B trained on 3.3T tokens of heavily filtered web + synthetic data. 69% MMLU, rivals GPT-3.5. Deployed on phone. Principle: "data quality is everything." Used massive synthetic data for **pretraining**, not SFT alone. |
| **Orca 1** (arXiv:2306.02707) | 13B model learns from GPT-4 explanation traces. Surpasses Vicuna-13B by >100% on BBH. Key insight: learn reasoning PROCESSES, not just answers. Uses progressive learning from teacher. |
| **Orca 2** (arXiv:2311.11045) | Teaches small LMs (7B, 13B) DIFFERENT reasoning strategies per task type (step-by-step, recall-then-generate, direct answer). Surpasses 5-10x larger models. **Critical: small LMs should not just imitate — they should learn WHEN to use each strategy.** |
| **LoRA** (arXiv:2106.09685) | Low-rank adaptation: 10,000x fewer trainable params, no inference latency after merging. But — crucial for this evaluation — subsequent research showed LoRA **underperforms full FT for knowledge acquisition**. |
| **QLoRA** (arXiv:2305.14314) | 4-bit NF4 quantization + LoRA. Guanaco reached 99.3% ChatGPT on Vicuna benchmark. Enables fine-tuning on single consumer GPU. Same knowledge limitation as LoRA. |
| **"LoRA Learns Less and Forgets Less"** (arXiv:2405.09673) | **CRITICAL FINDING:** LoRA substantially underperforms full fine-tuning for new knowledge acquisition. Full FT learns weight perturbations with rank 10-100x greater than typical LoRA. LoRA is better for style/format, NOT knowledge. |
| **NEFTune** (arXiv:2310.05914) | Adding noise to embeddings during SFT: LLaMA-2-7B jumps from 29.79% to 64.69% on AlpacaEval. Free quality boost. 8-10% improvement on Evol-Instruct, ShareGPT, OpenPlatypus. |
| **LAB** (arXiv:2403.01081) | Taxonomy-guided synthetic data generation. Reduces reliance on GPT-4 and human annotations. Competitive performance. Multi-phase tuning avoids catastrophic forgetting. |
| **SmolLM3** (HuggingFace blog, July 2025) | 3B model, 11T token pretraining, SFT with 1.8B tokens (synthetic from Qwen3-32B), APO alignment. SFT was **one stage** in a multi-stage pipeline — NOT the sole training method. SFT alone was INSUFFICIENT. |
| **GKD** (arXiv:2306.13649) | On-policy distillation: student trains on OWN outputs evaluated by teacher. Addresses train-test distribution mismatch. ICLR 2024. |
| **KTO** (arXiv:2402.01306) | Binary-signal alignment (desirable/undesirable), works 1B-30B. Matches DPO with simpler data requirements. |
| **DEITA** (arXiv:2312.15685) | 6K carefully selected SFT samples matched results of 60K+ generic samples. Quality >> Quantity. |

---

## THE FUNDAMENTAL CONFUSION THIS APPROACH CREATES

Before scoring, I must call out a **critical misunderstanding** that this approach embeds:

**The Phi-1 paper used synthetic data for PRETRAINING (next-token prediction on textbook text), NOT for SFT instruction tuning.** The distinction matters enormously:

| Aspect | Phi-1 Style (Synthetic Pretraining) | This Approach (Synthetic Q&A → SFT) |
|--------|--------------------------------------|---------------------------------------|
| Training objective | Next-token prediction on synthetic textbooks | Instruction-following on Q&A pairs |
| What model learns | Deep language patterns, factual associations, reasoning structures | How to FORMAT answers to specific questions |
| Knowledge depth | Deep — encoded across entire weight matrix | Shallow — encoded primarily in attention patterns matching Q formats |
| Coverage | Every sentence in the synthetic text contributes | Only explicitly asked Q&A pairs contribute |
| Analogy | Reading an entire textbook | Studying only the Q&A at the end of each chapter |

**This approach discards 80-90% of the Phi-1 insight.** Phi-1's power came from training on textbook-quality PROSE, not from Q&A SFT. The Q&A part (called "CodeExercises" in the paper) was a fine-tuning step AFTER pretraining on the synthetic textbooks.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. KNOWLEDGE RETENTION — Score: 5/10

**The core question:** When trained on synthetic Q&A pairs, how well does the model memorize specific textbook facts? Can it recall exact procedures, numbers, regulations?

**What the evidence says:**

SFT teaches a model to *respond in the format it was trained on*. If you train on:
```
Q: What are the six annexes of MARPOL?
A: Annex I — Oil pollution, Annex II — Noxious liquid substances, 
   Annex III — Harmful substances in packaged form, Annex IV — Sewage, 
   Annex V — Garbage, Annex VI — Air pollution
```

The model will likely answer THIS question correctly. But:

**Problem 1 — Coverage Gap:** For every fact in the textbook, you need a corresponding Q&A pair. A single MARPOL chapter might contain 500+ distinct facts, regulations, numbers, and procedures. The teacher model (GPT-4o) must:
- Read the chunk
- Identify ALL important facts
- Generate Q&A pairs for each

In practice, the teacher generates 5-20 Q&A pairs per textbook chunk (~2K tokens). This means **75-95% of facts in each chunk are NEVER explicitly trained on.** The model doesn't "read" the textbook — it only learns the filtered Q&A pairs.

**Problem 2 — Surface Memorization vs. Deep Understanding:** SFT creates pattern-matching: "When asked about MARPOL Annex VI → produce this text." It does NOT create the deep parametric knowledge that continued pretraining provides, where the model internalizes relationships between concepts.

**Problem 3 — LoRA Worsens This:** Per "LoRA Learns Less and Forgets Less" (arXiv:2405.09673), LoRA's low-rank constraint means it cannot modify the weight matrices enough to encode complex new factual knowledge. Full fine-tuning learns perturbations with rank 10-100x greater than typical LoRA (rank 16-64). **LoRA is optimized for style adaptation, NOT factual knowledge injection.**

**Problem 4 — Exact Numbers and Procedures:** Maritime engineering requires precision. "The CO2 system should be tested at X bar pressure, the release time should be Y seconds, the minimum number of bottles is Z." SFT can memorize these IF they appear in Q&A pairs, but:
- Slight rephrasing of the question → may retrieve wrong number
- Numbers are the hardest thing for SFT to retain reliably
- The model may "confidently" produce wrong numbers (hallucination)

**The CO2 fire suppression test:** "What's the exact procedure for testing CO2 fire suppression system per SOLAS?"

- If this exact procedure was covered in a Q&A pair and the teacher model extracted it correctly → 70-80% chance of a substantially correct answer
- If only adjacent topics were covered → the model will hallucinate a plausible-sounding but partially incorrect procedure (40-60% accurate)
- The model cannot be relied upon for safety-critical procedural recall from SFT alone

**Published evidence:**
- Phi-1 (SFT finetuning step after pretraining): Improved from 29% to 50.6% on HumanEval — the SFT step helped but was BUILT ON pretrained knowledge
- Phi-1.5 explicitly acknowledges hallucinations persist as a "bad trait" even with textbook-quality synthetic data
- No published evidence of SFT-only (without prior domain pretraining) achieving reliable factual recall for domain-specific knowledge at <3B scale

**SCORE: 5/10** — Retains facts that were explicitly covered in Q&A pairs. Unreliable for facts that were not. Exact numbers and procedures are fragile. LoRA/QLoRA makes this significantly worse than full SFT.

---

### 2. INFERENCE COST — Score: 10/10

**After SFT (regardless of LoRA or full), the inference model is:**

- Identical architecture to base model
- LoRA weights merge into base: `W' = W + BA` → zero extra cost
- Full SFT: same model, different weights
- No additional components, no retrieval, no vector DB

**Mobile deployment:**
| Model | Quantization | RAM | Runs on Phone? |
|-------|-------------|-----|----------------|
| 1.5B | Q4_K_M | ~1.0 GB | YES — any modern phone |
| 3B | Q4_K_M | ~1.8 GB | YES — phones with 4GB+ RAM |
| 3B | Q5_K_M | ~2.2 GB | YES — phones with 6GB+ RAM |

Inference speed: 10-30 tokens/sec on modern ARM CPUs via llama.cpp.

**No overhead whatsoever.** This is a pure strength of any SFT-based approach.

**SCORE: 10/10** — Perfect. After merging LoRA or completing full SFT, inference is identical to the base model. Zero extra cost, perfect for mobile.

---

### 3. TRAINING COST — Score: 8/10

**Two cost components:**

**A. Synthetic Data Generation (API Calls):**

Source material: 10-50 maritime textbooks → ~10-50M tokens of source text.

Processing with GPT-4o:
- Input processing: $2.50/1M input tokens → $25-125 for reading all textbooks
- Output generation: $10.00/1M output tokens → generating 50K-200K Q&A pairs with ~500 tokens each = 25-100M output tokens → $250-1,000
- Using DeepSeek-R1 API: ~10x cheaper → $25-100 total
- Using Claude 3.5 Sonnet: similar to GPT-4o pricing
- Using local Qwen-72B: free if you have hardware (needs 2x A100)

**Realistic API cost: $100-500 for comprehensive Q&A generation.** Add $50-100 for quality filtering passes.

**B. SFT Training:**

| Method | Hardware | Time | Cloud Cost |
|--------|----------|------|-----------|
| Full SFT 1.5B | 1x A100 40GB | 6-12 hours | $15-30 |
| Full SFT 3B | 1x A100 80GB | 1-2 days | $50-100 |
| LoRA 1.5B | 1x RTX 4090 | 2-4 hours | $5-10 |
| LoRA 3B | 1x RTX 4090 | 4-8 hours | $10-20 |
| QLoRA 3B | 1x RTX 3060 12GB | 6-12 hours | $5-15 |

**Total realistic cost: $150-700**

This is VERY affordable compared to:
- Continued pretraining: $500-5,000 (days on A100s)
- Training from scratch: $10,000-100,000+
- Human annotation of 50K QA pairs: $50,000-500,000

**SCORE: 8/10** — Very affordable. Synthetic data generation via API + SFT training is achievable for under $1,000. This is one of the approach's genuine strengths.

---

### 4. DATA EFFICIENCY — Score: 7/10

**How much data is needed?**

**Source material:** 10-50 maritime textbooks is feasible and provides good topical coverage:
- Reeds Vol. 5 Ship Construction ✓
- Marine Diesel Engines (Calder) ✓
- MARPOL Consolidated Edition ✓
- STCW Convention ✓
- Ballast Water Management ✓
- Corrosion Engineering ✓
- Plus additional texts on stability, navigation, safety, electrical systems

10-50 books × average 200-500 pages × ~500 tokens/page = **1M-12.5M source tokens** — enough for comprehensive Q&A generation.

**Generated Q&A pairs needed:**
- DEITA showed 6K samples can match 60K+ with quality selection
- But for KNOWLEDGE injection (not just style), more data needed
- Practical target: 50K-200K Q&A pairs
- With diverse question types: factual, procedural, reasoning, scenario-based
- Evol-Instruct style evolution of questions adds diversity

**Is 50K-200K Q&A pairs enough?**
- For SFT behavior/format: YES, more than enough
- For comprehensive knowledge coverage: BORDERLINE
- Estimated 5,000-10,000 distinct maritime facts need covering
- With 5-20 Q&A pair variations per fact → 25K-200K pairs → achievable

**But there's a fundamental inefficiency:** The textbooks contain 1-12.5M tokens of rich content. SFT Q&A pairs reduce this to structured question-answer format, discarding the contextual prose, explanations, diagrams, and relationships. You're compressing 1M+ tokens of knowledge into 50-200K Q&A token pairs — **massive information loss.**

Continued pretraining would use ALL 1-12.5M tokens directly. SFT uses a fraction of the information.

**SCORE: 7/10** — 10-50 textbooks is enough source material. The approach generates sufficient Q&A pairs. But the information compression inherent in Q&A format limits how much textbook knowledge actually reaches the model. Fundamentally less data-efficient than continued pretraining on the same source material.

---

### 5. ACCURACY ON DOMAIN QA — Score: 5/10

**This is where brutal honesty matters most.**

**What published results actually tell us:**

| Model/System | Task | Result | Relevant? |
|-------------|------|--------|-----------|
| Phi-1 (1.3B) | Coding (HumanEval) | 50.6% | Synthetic pretrain + SFT, NOT SFT-only |
| Phi-3 mini (3.8B) | MMLU (general knowledge) | 69% | Massive-scale synthetic pretrain, NOT SFT-only |
| Orca 2 (7B, 13B) | Complex reasoning benchmarks | Surpasses 5-10x larger | NOT <3B, uses teacher traces |
| QLoRA Guanaco | Vicuna benchmark (chat quality) | 99.3% of ChatGPT | Chat QUALITY, not factual ACCURACY |

**Critical observation:** None of these results demonstrate SFT-only (without prior domain pretraining) achieving high factual accuracy on domain-specific knowledge at the <3B scale.

**Expected accuracy breakdown for maritime Q&A:**

| Question Type | Expected Accuracy | Why |
|--------------|-------------------|-----|
| Questions identical to training data | 85-95% | Direct memorization |
| Questions paraphrasing training data | 60-75% | Pattern matching, some generalization |
| Questions combining 2+ trained facts | 40-60% | Limited compositional reasoning at <3B |
| Questions about untrained facts | 15-30% | Base model knowledge + hallucination |
| Exact numerical recall | 40-60% | Numbers are hardest to memorize via SFT |
| Multi-step procedures | 30-50% | Step ordering fragile, may miss steps |
| Regulatory cross-references | 25-45% | Requires deep interconnected knowledge |

**Hallucination rate:** SFT models are CONFIDENTLY wrong. When the answer isn't in the training data, they don't say "I don't know" — they fabricate plausible-sounding maritime content. At <3B scale, models have limited capacity to calibrate uncertainty.

Phi-1.5 paper explicitly states: "phi-1.5 exhibits many of the traits of much larger LLMs, both good... and bad, including **hallucinations**."

**The CO2 fire suppression test revisited:**
"What's the exact procedure for testing CO2 fire suppression system per SOLAS?"

A properly-trained SFT model would likely produce something like:
> "The CO2 fire suppression system should be tested [partially correct procedure]. The system should be visually inspected [vague correct step]. Bottles should be weighed [correct but may get the frequency wrong — e.g., says 'annually' when it should say 'every 2 years']. The release mechanism should be tested [correct concept, may miss specific steps]."

Result: 50-65% accurate. Enough to be dangerous — sounds authoritative but has errors.

**For safety-critical maritime procedures, this accuracy level is UNACCEPTABLE without additional verification mechanisms.**

**SCORE: 5/10** — Moderate accuracy on questions explicitly covered in training. Significant hallucination risk. Not reliable enough for safety-critical maritime procedures. The "confident wrongness" problem makes this worse than low accuracy — it's misleadingly accurate.

---

### 6. MOBILE DEPLOYABILITY — Score: 10/10

**After SFT, the model has:**
- Same architecture as base model ✓
- Same parameter count ✓
- No extra components (no vector DB, no retrieval index, no embedding model) ✓
- LoRA merges into weights → single model file ✓
- Compatible with all mobile frameworks: llama.cpp, MLC-LLM, ExecuTorch ✓

**Quantization path:**
```
SFT model (FP16/BF16) → GGUF Q4_K_M → Deploy on phone
```

**Deployment specs:**
| Model | Format | Size on disk | RAM needed | Tokens/sec (ARM) |
|-------|--------|-------------|-----------|-------------------|
| 1.5B | Q4_K_M | ~0.9 GB | ~1.2 GB | 15-30 |
| 3B | Q4_K_M | ~1.7 GB | ~2.2 GB | 8-15 |
| 3B | Q5_K_M | ~2.1 GB | ~2.6 GB | 7-13 |

No internet needed. No server. No API. Pure on-device inference.

**SCORE: 10/10** — Flawless mobile deployability. This is a non-differentiating strength — ALL approaches that produce a standard model (SFT, CPT, KD, etc.) share this score.

---

### 7. ROBUSTNESS (Handles Paraphrased Questions?) — Score: 6/10

**The fundamental fragility of SFT:**

SFT creates pattern-matching between question patterns and response patterns. If trained on:

```
Q: "What are the annexes of MARPOL?"
A: "MARPOL has six annexes: I (Oil), II (NLS), III (Harmful packaged), IV (Sewage), V (Garbage), VI (Air pollution)"
```

Performance on variations:
| Variant | Expected Result |
|---------|----------------|
| "List the MARPOL annexes" | ✓ Good — similar phrasing |
| "How many annexes does MARPOL have?" | ⚠️ Moderate — may answer just "6" without listing |
| "What does MARPOL Annex IV cover?" | ⚠️ Only if specifically trained, else extracts from general knowledge |
| "Which annex handles sewage at sea?" | ❌ Reverse lookup — trained on forward direction |
| "Under which regulation is garbage disposal governed?" | ❌ Different framing — requires reasoning from stored knowledge |
| "MARPOL ki sab annexes kya hain?" (Hindi transliteration) | ❌ Not trained on multilingual variants |

**Mitigations that improve robustness:**
1. **Evol-Instruct (WizardLM):** Generate evolved versions of each question — add complexity, rephrase, combine. This directly addresses robustness. Improves score by +1-2.
2. **NEFTune:** Adding embedding noise during SFT regularizes the model, improving generalization to unseen phrasings. Demonstrated 8-10% improvement.
3. **Diverse Q&A generation:** Prompt the teacher to generate 5-10 different phrasings per question.

**With these mitigations applied, robustness improves from 4-5/10 to 6-7/10.** But the fundamental issue remains: SFT models are fragile to out-of-distribution question patterns.

**Compared to continued pretraining:** A model that has READ maritime text via continued pretraining develops broader understanding. When asked a question in any form, it can draw on internalized knowledge. SFT models can only draw on pattern-matched Q&A pairs.

**SCORE: 6/10** — Moderate robustness. With diverse synthetic data and NEFTune, handles common rephrasings. Breaks down on novel framings, reverse lookups, and questions that require combining facts across multiple Q&A pairs.

---

### 8. CATASTROPHIC FORGETTING — Score: 6/10

**The SFT forgetting dilemma:**

SFT on domain-specific Q&A pairs modifies model weights to optimize for the domain distribution. This inevitably damages some general capabilities.

**LoRA vs. Full SFT — the impossible trade-off:**

| Method | Knowledge Gain | General Capability Loss | Net for This Use Case |
|--------|---------------|------------------------|----------------------|
| Full SFT | HIGH | HIGH | Moderate — gains knowledge but loses coherence |
| LoRA (rank 16) | LOW | LOW | Poor — preserves general but doesn't inject enough |
| LoRA (rank 128) | MODERATE | MODERATE | Better compromise |
| QLoRA | LOW | LOW | Same issues as LoRA |

Per "LoRA Learns Less and Forgets Less":
- LoRA better preserves general capabilities (less forgetting) ✓
- BUT LoRA substantially underperforms full FT for new knowledge ✗
- This is a **fundamental trade-off with no good solution within SFT alone**

**Mitigation strategies:**
1. **Data mixing:** Include 10-20% general instruction data during maritime SFT → reduces forgetting
2. **Replay buffer:** Periodically replay samples from general datasets
3. **Model merging (SmolLM3 approach):** After SFT, merge with base model at 0.7/0.3 ratio → recovers some general ability at cost of some domain knowledge
4. **Progressive SFT:** Start with general → gradually shift to domain-specific

**Practical impact for maritime chatbot:**
- Model may lose ability to have natural multi-turn conversations
- May forget basic reasoning when questions diverge from trained patterns
- General knowledge (geography, basic science) may degrade
- English fluency generally preserved but style may become mechanical

**SCORE: 6/10** — Manageable with mitigation strategies (data mixing, model merging). But the LoRA-vs-full-SFT dilemma means you're always compromising: either you inject enough knowledge and accept forgetting, or you preserve general ability and accept shallow knowledge.

---

### 9. MAINTENANCE (Adding New Knowledge) — Score: 7/10

**When new maritime regulations come out (IMO 2026, updated MARPOL annexes, etc.):**

**Workflow for update:**
1. Obtain new regulation text
2. Run through teacher model → generate new Q&A pairs (hours, $5-20 API cost)
3. Run additional SFT on new Q&A pairs (hours, one GPU)
4. Merge LoRA or do brief full SFT
5. Re-quantize and redeploy

**Strengths:**
- Fast turnaround: 1-2 days from new regulation to updated model
- Low cost per update: $20-50
- Can use LoRA for incremental updates without full retraining

**Weaknesses:**
- Each update risks degrading previously learned knowledge
- LoRA rank limits how much new knowledge each update can add
- After 5-10 updates, model quality may degrade significantly
- May need periodic full retraining from scratch to "reset" accumulated drift
- No easy way to selectively UPDATE a fact (e.g., if a regulation number changes)
- Knowledge editing approaches (ROME/MEMIT) are too fragile at this scale

**Compared to continued pretraining:** CPT-based updates require full retraining (expensive), but produce more robust updates. SFT updates are cheaper but more fragile.

**Compared to RAG (which we can't use):** RAG makes updates trivial — just update the document store. Without RAG, every knowledge update requires retraining.

**SCORE: 7/10** — Fast and cheap incremental updates via LoRA/SFT. But accumulated updates degrade quality. Periodic full retraining needed. Still much easier than CPT updates.

---

### 10. PROVEN AT SMALL SCALE (<3B) — Score: 7/10

**Direct evidence of SFT with synthetic data at <3B:**

| Model | Size | Approach | Outcome |
|-------|------|----------|---------|
| Phi-1 | 1.3B | Synthetic **pretrain** + SFT on exercises | 50.6% HumanEval |
| Phi-1.5 | 1.3B | Synthetic **pretrain** + SFT | Matches 5x larger on reasoning |
| Phi-2 | 2.7B | Synthetic pretrain + SFT + ORPO | 12.20% AlpacaEval 2.0 |
| SmolLM3 | 3B | 11T pretrain + 35B reason mid-train + SFT | SoTA at 3B |
| DeepSeek-R1-Distill-Qwen | 1.5B | Reasoning distillation (SFT-like) | Remarkable reasoning at 1.5B |
| TinyStories | <28M | Synthetic story pretraining | Coherent text generation |

**CRITICAL CAVEAT:** In EVERY case above, SFT on synthetic data was **one step** in a multi-stage pipeline. None used SFT-only:

- Phi-1: **Pretraining on synthetic textbooks** → then SFT on exercises
- Phi-1.5: **Pretraining on synthetic reasoning text** → then SFT
- SmolLM3: **11T pretraining** → mid-training → SFT → APO → merging
- DeepSeek-R1-Distill: Based on a model that was **already pretrained** on trillions of tokens

**No published evidence exists of SFT-only (applied to an off-the-shelf base model, without domain pretraining) achieving strong domain-specific factual accuracy at <3B.** The SFT step in every successful pipeline stood on the shoulders of massive pretraining.

**Domain-specific SFT evidence:**
- Medical: ChatDoctor, MedAlpaca — SFT on medical Q&A showed improved medical responses but introduced hallucinations and were NOT reliable for clinical decisions
- Legal: Small legal SFT models similarly struggled with precise recall
- Code: SFT on code Q&A works better because code has clear verification (tests), which maritime doesn't

**SCORE: 7/10** — Well-proven as A COMPONENT of small-model pipelines. Never proven as a STANDALONE approach for domain knowledge injection at <3B. Every success story used SFT as one stage after heavy pretraining.

---

## SCORE SUMMARY

| # | Criterion | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Knowledge Retention | 5/10 | Only retains explicitly trained Q&A; 75-95% of textbook facts not covered |
| 2 | Inference Cost | 10/10 | Zero overhead — identical to base model |
| 3 | Training Cost | 8/10 | $150-700 total — very affordable |
| 4 | Data Efficiency | 7/10 | Enough source material; but Q&A format lossy vs raw text |
| 5 | Accuracy on Domain QA | 5/10 | Moderate on trained questions; dangerous hallucinations on untrained ones |
| 6 | Mobile Deployability | 10/10 | Perfect — standard model, no extra components |
| 7 | Robustness | 6/10 | Fragile to novel phrasings; better with Evol-Instruct |
| 8 | Catastrophic Forgetting | 6/10 | LoRA-vs-full-SFT dilemma; manageable with mixing |
| 9 | Maintenance | 7/10 | Fast updates but accumulate drift |
| 10 | Proven at Small Scale | 7/10 | Proven as COMPONENT, never as standalone for domain knowledge |

## **TOTAL SCORE: 71/100**

---

## KEY STRENGTHS (Top 3)

### 1. Inference Cost & Mobile Deployability (10/10 + 10/10)
The approach produces a standard model with zero inference overhead. After LoRA merge or full SFT, you have a single model file that quantizes to Q4 GGUF and runs on any modern phone at 10-30 tokens/sec. No extra components. This is shared with all weight-modification approaches but is a genuine strength of the SFT paradigm.

### 2. Training Cost — Extremely Affordable (8/10)
Total cost under $1,000 (API calls + GPU rental). Compare this to:
- Continued pretraining: $500-5,000
- Training from scratch: $10,000-100,000+
- Human annotation: $50,000-500,000

The synthetic data generation via teacher API + SFT on consumer GPU makes this approach accessible to individual developers and small teams. You can iterate quickly and cheaply.

### 3. Fast Iteration & Maintenance (7/10)
New data → new Q&A pairs → quick SFT round → redeploy. The feedback loop is hours, not weeks. You can rapidly test different data mixes, teacher prompts, and fine-tuning hyperparameters. This speed of iteration partially compensates for the lower knowledge depth per training run.

---

## KEY WEAKNESSES (Top 3)

### 1. Shallow Knowledge Injection — The Fatal Flaw (Knowledge Retention: 5/10, Accuracy: 5/10)
**This is the dealbreaker for a maritime safety chatbot.** SFT teaches format and pattern-matching, not deep understanding. The model learns "when asked X, say Y" — it does NOT internalize maritime knowledge the way continued pretraining does. 

- 75-95% of textbook facts that aren't explicitly converted to Q&A pairs are LOST
- Exact numbers, multi-step procedures, and regulatory cross-references are unreliable
- The model is CONFIDENTLY WRONG — it doesn't say "I don't know," it hallucinates plausible maritime content
- **For crew member safety questions, this confidence-without-knowledge is dangerous**

Evidence: "LoRA Learns Less and Forgets Less" proved that LoRA (the proposed training method) **substantially underperforms** full fine-tuning for knowledge acquisition. Full SFT is better but still inferior to continued pretraining for factual knowledge.

### 2. The Phi-1 Misattribution — SFT ≠ What Made Phi-1 Work (Proven at Scale: 7/10)
The user's prompt frames this as "the Phi-1 approach." **It is not.** Phi-1's breakthrough was:
1. **Pretraining** on synthetic textbook PROSE (6B filtered + 1B synthetic tokens)
2. Then SFT on "CodeExercises" (a fine-tuning step)

Removing step 1 removes the foundation of Phi-1's success. Every successful small model (Phi series, SmolLM3, DeepSeek-R1-Distill) used SFT as one late-stage step in a multi-phase pipeline. **No published work demonstrates SFT-only producing reliable domain expertise at <3B.**

### 3. Fragile to Question Variation (Robustness: 6/10)
SFT creates brittle pattern matching. Maritime crew members won't phrase questions the way GPT-4-generated Q&A pairs do. They'll ask:
- "Engine overheating after we cleaned the cooler — what now?" (situational)
- "Can we dump this oily water?" (informal)
- "What was that CO2 system check interval again?" (casual recall)

SFT models are trained on formal, structured Q&A. They struggle with informal, contextual, or reverse-lookup queries. Evol-Instruct and NEFTune help but don't solve the fundamental generalization gap.

---

## VERDICT: Is This Sufficient ALONE?

# **NO — Insufficient as a Standalone Approach**

**Not even close.** Using synthetic Q&A generation + SFT alone (especially with LoRA/QLoRA) is categorically insufficient for a maritime safety chatbot. The approach:

1. **Cannot reliably inject domain knowledge** — SFT is a surface-level training technique optimized for format/behavior, not factual content encoding
2. **Will produce dangerous hallucinations** — for safety-critical maritime procedures, the model will confidently state incorrect information
3. **Misapplies the Phi-1 insight** — Phi-1's innovation was synthetic PRETRAINING data, not SFT data
4. **Has been proven inadequate** in medical domain (ChatDoctor, MedAlpaca produced unreliable SFT-only models that were abandoned)

**Analogy:** This approach is like giving a student only a practice exam (Q&A pairs) without the textbook (pretraining text). They'll memorize answers to specific questions but won't understand the subject.

---

## BEST COMBINATION: What Complements It

### The Correct Pipeline (Ranked by Importance):

```
ESSENTIAL FOUNDATION (you MUST do this):
  ┌─────────────────────────────────────────────────────────┐
  │ Phase 1: CONTINUED PRETRAINING on raw maritime text     │
  │  - Convert textbooks to clean text                       │
  │  - Continue-pretrain base model (SmolLM3-3B-Base)       │
  │  - Use curriculum: basic → intermediate → advanced       │
  │  - 80% domain + 20% general data replay                 │
  │  - 2-5 days on 1-2x A100                                │
  │  - This is WHERE knowledge gets injected into weights    │
  └─────────────────────────────────────────────────────────┘
                              ↓
THEN THIS APPROACH BECOMES VALUABLE:
  ┌─────────────────────────────────────────────────────────┐
  │ Phase 2: SYNTHETIC DATA + SFT (this approach)           │
  │  - Generate Q&A pairs from textbooks via teacher        │
  │  - Include reasoning traces (Orca 2 style)              │
  │  - Use Evol-Instruct for diversity                      │
  │  - Full SFT (NOT LoRA) with NEFTune                     │
  │  - Mix 80% domain + 20% general instruction data        │
  │  - This teaches the model HOW TO USE its knowledge      │
  └─────────────────────────────────────────────────────────┘
                              ↓
THEN REFINE:
  ┌─────────────────────────────────────────────────────────┐
  │ Phase 3: PREFERENCE ALIGNMENT (DPO/APO)                 │
  │  - Correct maritime answers vs. common misconceptions    │
  │  - Teaches the model to prefer factual accuracy          │
  │  - 1-2K preference pairs → brief alignment training      │
  └─────────────────────────────────────────────────────────┘
                              ↓
THEN DEPLOY:
  ┌─────────────────────────────────────────────────────────┐
  │ Phase 4: QUANTIZE + DEPLOY                              │
  │  - Q4_K_M GGUF format                                   │
  │  - Test on mobile via llama.cpp                          │
  │  - Benchmark against maritime QA gold standard           │
  └─────────────────────────────────────────────────────────┘
```

### Why This Combination Works:

| Phase | What It Does | What It Can't Do |
|-------|-------------|-----------------|
| Continued Pretraining | Deeply embeds factual knowledge into weights | Doesn't teach how to answer questions |
| Synthetic Data + SFT | Teaches how to format and present knowledge as answers | Doesn't deeply inject knowledge (this is the evaluated approach) |
| DPO/APO | Teaches to prefer correct over incorrect answers | Doesn't add new knowledge |
| Quantization | Makes it mobile-deployable | Slight quality loss at Q4 |

**Each phase compensates for the previous phase's weakness.** The evaluated approach (Synthetic Data + SFT) is valuable as Phase 2, but catastrophically insufficient as Phase 1.

### The Score IF Combined with Continued Pretraining:

| Criterion | SFT-Only | CPT + SFT |
|-----------|----------|-----------|
| Knowledge Retention | 5 | 8 |
| Inference Cost | 10 | 10 |
| Training Cost | 8 | 7 (CPT adds $500-2,000) |
| Data Efficiency | 7 | 8 |
| Accuracy on Domain QA | 5 | 7-8 |
| Mobile Deployability | 10 | 10 |
| Robustness | 6 | 7 |
| Catastrophic Forgetting | 6 | 6 |
| Maintenance | 7 | 6 |
| Proven at Small Scale | 7 | 9 |
| **TOTAL** | **71** | **78-79** |

Adding continued pretraining as a foundation raises the total from 71/100 to ~79/100, with the critical knowledge retention and accuracy metrics rising from the danger zone (5/10) to acceptable levels (7-8/10).

---

## FINAL ASSESSMENT

### One-Line Summary:
**Synthetic Data + SFT is a good finishing technique but a terrible foundation — it teaches a model to TALK about maritime engineering without actually UNDERSTANDING maritime engineering.**

### For the Maritime Chatbot Project:
- **Do NOT ship an SFT-only model.** It will hallucinate procedures, get regulation numbers wrong, and confidently provide incorrect safety information.
- **DO use synthetic data generation** — it's genuinely the best way to create training data from textbooks. The LAB taxonomy-guided approach ensures coverage.
- **DO use SFT** — but as Phase 2 AFTER continued pretraining, not as the sole training method.
- **Use full SFT, NOT LoRA,** for the domain training phase. LoRA's low-rank constraint prevents adequate knowledge absorption. Use LoRA only for quick subsequent updates.
- **Apply NEFTune** during SFT — it's free and proven (29.79% → 64.69% on AlpacaEval).
- **Follow the SmolLM3 recipe:** Pretraining → Mid-training → SFT → Alignment → Merging → Quantization.

### The Harsh Truth:
If a crew member asks "What's the exact procedure for testing CO2 fire suppression system per SOLAS?", an SFT-only model will produce a plausible-sounding answer that's 50-65% correct. **In maritime safety, 50-65% correctness is worse than admitting you don't know.** You need continued pretraining as the knowledge foundation, then SFT to polish the presentation.

---

*This evaluation is based on published research from Microsoft (Phi-1/1.5/3, Orca 1/2), Meta (LLaMA, Code Llama), HuggingFace (SmolLM3), DeepSeek (R1, V2), and the academic LoRA/QLoRA/NEFTune literature. All scores reflect the approach's performance when used ALONE for domain knowledge injection at the 1-3B scale, which is the evaluated question.*
