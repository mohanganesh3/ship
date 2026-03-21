# RANKING EVALUATION: Reasoning Distillation (DeepSeek-R1 Style)

**Approach Under Evaluation:** Using a large reasoning model (DeepSeek-R1-671B, QwQ-32B, o1) to generate detailed chain-of-thought (CoT) reasoning traces for maritime questions, then training a small model (1-3B) on these traces so it learns HOW to reason step-by-step through maritime problems. This is "reasoning distillation" — transferring reasoning *patterns*, not just answers.

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
| **DeepSeek-R1** (arXiv:2501.12948, Nature 2025) | 671B MoE model trained via pure RL (GRPO) develops emergent reasoning (self-verification, reflection, dynamic strategy). **Distilled to Qwen-1.5B using 800K reasoning traces → 83.9% MATH-500** (vs GPT-4o's 74.6%). Distilling R1 into Qwen-1.5B, 7B, 14B, 32B, Llama-8B, 70B. Proved reasoning patterns transfer across scales. But: this was MATH/CODE reasoning, not domain-specific factual recall. |
| **s1: Simple test-time scaling** (arXiv:2501.19393) | Only **1,000 curated reasoning traces** + SFT on Qwen2.5-32B-Instruct → exceeds o1-preview by 27% on MATH/AIME. "Budget forcing" controls test-time compute (force "Wait" tokens to extend thinking). Key data criteria: difficulty, diversity, quality. Proves small datasets work for reasoning distillation — but again, on MATH, not domain QA. |
| **Orca 1** (arXiv:2306.02707) | 13B model learns from GPT-4 explanation traces. Surpasses Vicuna-13B by >100% on BBH. Key insight: learn reasoning PROCESSES from teacher, not just final answers. Progressive learning from weaker to stronger teachers. Foundational work for reasoning distillation. |
| **Orca 2** (arXiv:2311.11045) | Teaches small LMs (7B, 13B) DIFFERENT reasoning strategies per task type — step-by-step, recall-then-generate, recall-reason-generate, direct answer. **Critical: small LMs should not just imitate — they should learn WHEN to use each strategy.** Surpasses 5-10x larger models on zero-shot reasoning. But: 7B minimum, not proven at 1.5B. |
| **GKD (On-Policy Distillation)** (arXiv:2306.13649, ICLR 2024) | On-policy knowledge distillation: student trains on its OWN generated outputs scored by teacher. Addresses train-test distribution mismatch that plagues standard SFT distillation. Better for auto-regressive models than standard KD. Key for reasoning chains where student's distribution diverges from teacher's. |
| **Self-Rewarding Language Models** (arXiv:2401.10020, ICML 2024) | Model itself serves as judge via LLM-as-a-Judge prompting during iterative DPO training. Both instruction-following AND reward quality improve simultaneously. Llama 2 70B surpasses GPT-4 0613 on AlpacaEval. Relevant because reasoning quality could be self-improved — but requires large model capacity. |
| **Open-R1** (HuggingFace blog + GitHub, Jan 2025) | Community reproduction of DeepSeek-R1. Three planned steps: (1) replicate R1-Distill via SFT on reasoning traces, (2) replicate pure RL pipeline (GRPO), (3) base model → SFT → RL multi-stage. Missing pieces: exact datasets, training hyperparameters, scaling laws. Confirms the distillation recipe is SFT on teacher-generated CoT traces. |
| **GRPO** (DeepSeekMath, arXiv:2402.03300) | Group Relative Policy Optimization: eliminates the separate critic/reward model by comparing outputs within a group. More compute-efficient than PPO. Used in DeepSeek-R1-Zero to incentivize reasoning from scratch in base models. Relevant for RL-based reasoning enhancement but requires verifiable reward signals. |
| **Qwen3** (arXiv:2505.09388) | 36T tokens, thinking/non-thinking hybrid mode. Strong-to-weak distillation produces good reasoning models at 1/10 GPU cost. Qwen3-1.7B achieves MMLU 62.63. The thinking mode generates explicit CoT, adding tokens to output. Budget control via `enable_thinking` flag. |
| **Phi-3** (arXiv:2404.14219) | 3.8B model runs on iPhone 14 at 12+ tok/s. **Critical admission: "The model simply does not have the capacity to store too much factual knowledge."** Even at 3.8B on 3.3T tokens — factual recall is a fundamental capacity limitation. Reasoning distillation doesn't solve this. |
| **"LoRA Learns Less and Forgets Less"** (arXiv:2405.09673) | LoRA substantially underperforms full fine-tuning for knowledge acquisition. Full FT learns weight perturbations with rank 10-100x greater than typical LoRA. Relevant because reasoning trace SFT via LoRA would be doubly limited — weak at injecting both reasoning patterns AND factual knowledge. |
| **"Don't Stop Pretraining"** (arXiv:2004.10964) | Domain-adaptive pretraining on unlabeled domain text consistently improves downstream tasks. The foundational paper for domain knowledge injection. Reasoning distillation is complementary but NOT a substitute. |

---

## THE FUNDAMENTAL QUESTION THIS EVALUATION MUST ANSWER

**Does teaching a 1.5B model HOW to reason about maritime problems also teach it WHAT it needs to know about maritime engineering?**

The answer is nuanced. Let me break it down precisely:

**What DeepSeek-R1 distillation actually did:**
1. DeepSeek-R1 (671B MoE) was trained via RL to produce long chain-of-thought reasoning traces before answering
2. 800K samples were generated: question → `<think>` long reasoning trace `</think>` → final answer
3. Small models (Qwen-1.5B through Llama-70B) were SFT'd on these 800K samples
4. The small models learned to PRODUCE similar reasoning traces — they mimic the thinking pattern

**What the distilled models gained:**
- Ability to break problems into steps
- Self-verification ("let me check this...")
- Dynamic strategy adaptation
- Working through multi-step logic

**What the distilled models did NOT gain:**
- New factual knowledge not in their base model weights
- Domain-specific expertise
- Knowledge of maritime regulations, procedures, or engineering principles
- The ability to look up specific values or thresholds

**This is the crux:** DeepSeek-R1-Distill-Qwen-1.5B achieves 83.9% on MATH-500 because mathematical reasoning is a *skill* — you learn patterns and procedures (algebra, calculus, number theory), not specific facts. The base Qwen2.5-Math-1.5B already knew mathematical notation and operations; the reasoning traces taught it to USE that knowledge systematically.

**Maritime domain is fundamentally different from math:** A ship engineer asking "diagnose high exhaust temperature" needs:
1. KNOWLEDGE of what components affect exhaust temperature (turbocharger, fuel injectors, scavenge air, cylinder liners, piston rings, exhaust valve timing)
2. KNOWLEDGE of normal operating parameters
3. REASONING to systematically eliminate possibilities

Reasoning distillation provides (3) but NOT (1) and (2). Without domain knowledge in the weights, the model has nothing meaningful to reason ABOUT.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. KNOWLEDGE RETENTION — Score: 3/10

**The core question:** Does reasoning distillation help the model remember maritime facts, or just reasoning patterns?

**Answer: Just reasoning patterns. This is the critical failure mode.**

**Evidence:**

- **DeepSeek-R1's distilled models were not evaluated on factual recall.** The benchmarks were AIME (competition math), MATH-500 (math problems), GPQA-Diamond (graduate-level reasoning), LiveCodeBench (code), Codeforces (competitive programming). NONE of these test domain-specific factual knowledge. Not one.

- **The 800K reasoning traces contained reasoning PATTERNS, not domain knowledge.** The training data was: "Here's a hard math/code problem → here's how to think through it step by step → here's the answer." The maritime equivalent would be: "Here's a diagnostic scenario → think through possible causes → here's the diagnosis." But the maritime scenario requires the model to ALREADY KNOW what the possible causes are, what the normal parameters are, what the component names mean.

- **A 1.5B model's knowledge capacity is fixed.** Reasoning distillation doesn't add parameters or expand the weight matrices. The model has the same ~3.4GB of weights (FP16) storing the same amount of factual information. What changes is HOW the model uses its existing knowledge, not what knowledge it has.

- **Phi-3's documented limitation applies even more strongly here.** The Phi-3 paper (3.8B, trained on 3.3T tokens) admits: *"The model simply does not have the capacity to store too much factual knowledge."* Reasoning distillation doesn't change the model's capacity — it just changes how the model deploys that capacity.

**The maritime knowledge test:**

Q: "What is the minimum CO2 concentration limit for enclosed space entry?"

- A base Qwen-1.5B model: Might guess a number based on general training data. Unreliable.
- A reasoning-distilled Qwen-1.5B model: Will produce a nice chain-of-thought trace: *"Let me think about this step by step. CO2 concentration in enclosed spaces... I need to recall the safety threshold... According to safety guidelines, the maximum allowable CO2 concentration..."* — and then produce a WRONG number, because the reasoning structure is beautiful but the underlying factual knowledge is absent or unreliable.

**The reasoning chain makes hallucination WORSE, not better:** A direct wrong answer ("0.3%") is obviously wrong to a knowledgeable user. A wrong answer wrapped in plausible step-by-step reasoning ("Let me consider the ISGOTT guidelines... the threshold for enclosed space entry is typically based on the TWA (Time-Weighted Average)... the recommended limit is 0.3%...") is **more dangerous** because it sounds authoritative. The real answer is 0.5% (5000 ppm) per IMO guidelines, but the confident reasoning trace creates a false sense of reliability.

**What reasoning distillation preserves:**
- General reasoning patterns (breaking problems into parts, checking intermediate steps)
- Whatever factual knowledge was already in the base model from pretraining
- Mathematical/logical reasoning capabilities

**What reasoning distillation does NOT preserve:**
- Maritime-specific facts, regulations, values, thresholds, procedures
- Domain terminology relationships (unless in base model)
- Cross-references between regulations (which annex covers what)
- Exact procedural steps for maintenance, emergency, or compliance tasks

**SCORE: 3/10** — Reasoning distillation is explicitly NOT a knowledge injection technique. It teaches reasoning patterns, not domain facts. For a maritime chatbot that must recall specific regulations, procedures, and engineering values, this approach scores near the bottom for knowledge retention. The model will reason eloquently about topics it doesn't actually know.

---

### 2. INFERENCE COST — Score: 4/10

**This is the hidden killer for mobile deployment.**

**The core problem:** Reasoning distillation teaches the model to THINK before answering. This thinking manifests as long chains of tokens wrapped in `<think>...</think>` tags. On mobile, every token costs time and battery.

**Concrete token generation analysis:**

A standard (non-reasoning) model answering "What causes high exhaust temperature?":
```
Possible causes include fouled turbocharger, worn fuel injector nozzles, 
blocked scavenge air ports, excessive cylinder liner wear, incorrect fuel 
injection timing, and insufficient cooling water flow. Check turbocharger 
first as it's the most common cause.
```
**~50 tokens. At 15 tok/s on iPhone 15 = ~3.3 seconds.**

A reasoning-distilled model answering the same question:
```
<think>
The user is asking about high exhaust temperature on a marine diesel engine. 
Let me think through the possible causes systematically.

First, I need to consider the air supply side:
- Turbocharger efficiency: if the turbocharger is fouled or damaged, the 
  scavenge air pressure drops, leading to incomplete combustion and higher 
  exhaust temperatures
- Scavenge air cooler: if blocked, the charge air temperature rises
- Scavenge ports: if blocked, insufficient air enters the cylinder

Next, the fuel side:
- Fuel injection timing: late injection means fuel burns later in the 
  expansion stroke, pushing heat into the exhaust
- Fuel injector nozzle condition: worn or blocked nozzles cause poor 
  atomization
- Fuel quality: high viscosity or water contamination

Then, the mechanical side:
- Piston rings: worn rings allow blow-by, reducing combustion efficiency
- Cylinder liner wear: increased clearance
- Exhaust valve: damaged or leaking valve

Let me also consider operational factors:
- Engine overload condition
- Ambient sea water temperature affecting cooling

I should present these in a logical diagnostic order, starting with the 
most common causes.
</think>

High exhaust temperature in a marine diesel engine can be caused by:

1. **Air Supply Issues:** Fouled turbocharger (most common), blocked 
   scavenge air cooler, obstructed scavenge ports
2. **Fuel System Issues:** Incorrect injection timing, worn injector 
   nozzles, poor fuel quality
3. **Mechanical Wear:** Worn piston rings, cylinder liner degradation, 
   leaking exhaust valve
4. **Operational Factors:** Engine overload, high sea water temperature

Begin diagnosis by checking turbocharger condition and scavenge air 
pressure.
```
**~250-400 tokens total (thinking + answer). At 15 tok/s on iPhone 15 = ~17-27 seconds.**

**That's a 5-8x latency increase for the SAME question.** On a mid-range Android phone at 10 tok/s, this becomes 25-40 seconds — far too slow for a responsive chatbot experience.

**Can you skip the thinking tokens?**

Technically, the `<think>` tokens can be hidden from the user (not displayed). But they STILL MUST BE GENERATED. The model's correct answer at the end DEPENDS on the reasoning chain that precedes it. If you truncate the thinking, the answer quality degrades back to non-reasoning-model levels — defeating the entire purpose.

**What about Qwen3's thinking mode toggle?** Qwen3 supports `enable_thinking=False` to skip CoT. But:
- In non-thinking mode, the model reverts to standard behavior — no reasoning benefit
- You've paid the TRAINING cost of reasoning distillation but aren't using the capability
- The model wasn't optimized for non-thinking maritime QA, so quality is suboptimal in both modes

**What about s1's "budget forcing"?** The s1 paper's budget forcing technique (appending "Wait" to extend thinking, or truncating early) allows test-time compute control. But:
- Budget forcing was demonstrated on 32B models, not 1.5B
- Truncating reasoning in small models is risky — they need more reasoning steps, not fewer
- On mobile, even a "short" reasoning trace (100 tokens) adds 5-10 seconds of latency

**Battery and thermal impact:**
- Generating 300 tokens per query vs 50 tokens = 6x more compute
- Sustained inference generates heat, potentially triggering thermal throttling on phones
- Battery drain per query increases proportionally
- Over a work shift of 50 queries: ~1,500 seconds of active inference vs ~250 seconds

**The fundamental tradeoff:** Reasoning distillation trades INFERENCE COST for REASONING QUALITY. This is the opposite of what mobile deployment needs. Mobile deployment needs fast, efficient, single-pass inference. Reasoning distillation adds multi-step internal deliberation that is valuable for complex reasoning (math olympiad problems) but expensive for factual QA (maritime regulations).

**SCORE: 4/10** — CoT reasoning generates 4-8x more tokens than direct answers. On mobile hardware at 10-25 tok/s, this pushes response times from 3-5 seconds to 15-40 seconds. The increased latency, battery drain, and thermal load are significant penalties for mobile deployment. Some mitigation is possible (thinking mode toggle, budget forcing) but these partially negate the reasoning benefit.

---

### 3. TRAINING COST — Score: 5/10

**Two-phase cost: (1) generating reasoning traces from teacher, (2) training the student.**

**Phase 1: Generating maritime reasoning traces from a large teacher model**

This is the expensive part. You need a powerful reasoning model to generate detailed CoT traces for maritime questions.

| Teacher Model | Access Method | Cost per 1M output tokens | Est. for 800K samples |
|---|---|---|---|
| DeepSeek-R1 (API) | API | $2.19/1M output tokens | ~$1,750 (assuming ~1K tokens avg output) |
| GPT-4o | API | $15.00/1M output tokens | ~$12,000 |
| Claude 3.5 Sonnet | API | $15.00/1M output tokens | ~$12,000 |
| QwQ-32B (self-hosted) | Local A100×2 | $2.20/hr × ~100 hrs | ~$220 + setup |
| DeepSeek-R1-Distill-32B | Local A100×1 | $1.10/hr × ~80 hrs | ~$88 + setup |

**But do you actually need 800K samples?**

DeepSeek used 800K for GENERAL reasoning across math, code, science, and more. For maritime only:
- The domain is narrow: ~20-30 topic areas (SOLAS, MARPOL, diesel engines, ship construction, etc.)
- s1 demonstrated that 1,000 high-quality traces can be incredibly effective
- A maritime-focused dataset might need 5,000-50,000 traces covering all topics and reasoning types
- But each trace needs to be high quality, diverse, and contain actual maritime domain knowledge

**Problem: Where do the maritime reasoning traces come from?**

For math, DeepSeek-R1 just solves math problems — the questions are abundant and verifiable. For maritime:
- You need to CREATE maritime reasoning questions first (from textbooks)
- The teacher model must KNOW maritime content to reason about it correctly
- DeepSeek-R1/GPT-4o have general maritime knowledge but may not know specific regulation details
- If the teacher hallucinates a maritime fact in its reasoning trace, the student learns the hallucination as truth

This creates a circular dependency: to generate high-quality maritime reasoning traces, you need a model that already has deep maritime knowledge. But that's what you're trying to create.

**Phase 2: Training the student model**

| Resource | Estimated Cost |
|---|---|
| SFT on 50K reasoning traces (1.7B model, full FT) | ~$5-20 (2-8 hours on A100) |
| SFT on 800K traces (if you generate that many) | ~$50-200 (10-40 hours on A100) |
| QLoRA training (reduced memory) | ~50% of full FT cost |

**Total estimated cost:**

| Scenario | Teacher API | Student Training | Data Creation | Total |
|---|---|---|---|---|
| Minimal (5K traces, DeepSeek API) | ~$11 | ~$5 | ~$0 (automated) | ~$16 |
| Moderate (50K traces, DeepSeek API) | ~$110 | ~$20 | ~$50 (curation) | ~$180 |
| Full reproduction (800K, GPT-4o) | ~$12,000 | ~$200 | ~$500 (curation) | ~$12,700 |
| Self-hosted teacher (QwQ-32B) | ~$220 | ~$20 | ~$50 | ~$290 |

**Why not higher score:**
- Generating reasoning traces is 5-50x more expensive per sample than generating simple Q&A pairs (because each trace is 500-2000 tokens vs 50-200 tokens for Q&A)
- Teacher inference is the bottleneck, not student training
- Quality control is harder — you need to verify that the teacher's reasoning chain is factually correct for maritime content, which requires domain expert review
- If the teacher model makes maritime errors in the reasoning trace, you've created expensive poisonous training data

**SCORE: 5/10** — Moderate to high training cost driven primarily by teacher model API costs for generating long reasoning traces. The per-sample cost is 5-50x higher than simple Q&A generation because reasoning traces are long (500-2000 tokens each). Quality control requiring domain expertise adds further cost. Self-hosted QwQ-32B is the cheapest viable teacher but needs 2×A100.

---

### 4. DATA EFFICIENCY — Score: 5/10

**The question: How many reasoning traces does a 1.5B model need to learn maritime reasoning?**

**What the research says:**

| Paper | Dataset Size | Result |
|---|---|---|
| DeepSeek-R1 distillation | 800K samples | MATH-500: 83.9% (1.5B), 92.8% (7B) |
| s1 | 1,000 samples (s1K) | Exceeds o1-preview on MATH (+27%) — but on 32B model |
| Orca 1 | 5M explanation traces | Surpasses Vicuna-13B by >100% on BBH |
| Orca 2 | "Carefully curated" subset | Surpasses 5-10x larger models — but on 7B/13B, not 1.5B |
| DEITA | 6K samples | Matched 60K+ on alignment (but not domain knowledge) |

**The data efficiency paradox for reasoning distillation:**

**Reasoning distillation is data-efficient for REASONING patterns** — s1 showed 1,000 traces suffice to teach a 32B model when to think harder. The reasoning SKILL (step-by-step analysis, self-verification, backtracking) can be learned from relatively few examples.

**But reasoning distillation is data-INEFFICIENT for KNOWLEDGE** — because each reasoning trace is 500-2000 tokens but contains only ~5-10 domain facts embedded in the reasoning. Most of the tokens are reasoning structure ("Let me think about this...", "First, I should consider...", "Wait, let me check..."). The fact-to-token ratio is extremely low compared to:
- Continued pretraining (every token is domain content)
- Simple Q&A SFT (concise factual content)

**Calculation for maritime domain:**

If you generate 10,000 maritime reasoning traces:
- Average trace length: ~800 tokens (thinking) + ~200 tokens (answer) = ~1,000 tokens
- Total tokens: 10M tokens
- Factual content: ~10-15% of tokens = ~1-1.5M tokens of actual maritime facts
- Comparative: 10M tokens of continued pretraining on raw maritime text = ~10M tokens of dense domain content (10x more efficient for knowledge)

**The data content problem:**

For reasoning traces to work for maritime, the traces MUST contain correct maritime facts. But:
1. The teacher model (DeepSeek-R1, GPT-4o) has broad but shallow maritime knowledge
2. The teacher may get specific regulation numbers wrong (e.g., wrong SOLAS chapter reference)
3. The teacher may reason correctly but from incorrect premises
4. Quality-checking 10,000+ reasoning traces for maritime accuracy requires domain experts

**Example of the data quality problem:**

Teacher-generated trace (potentially flawed):
```
<think>
The user asks about CO2 fire suppression testing intervals. Let me recall...
SOLAS Chapter II-2, Regulation 14 covers fire suppression systems. The CO2 
system must be inspected annually and the bottles weighed every... I think 
it's every 2 years for weighing and every 10 years for hydraulic testing...
</think>

CO2 bottles should be weighed every 2 years and hydrostatically tested 
every 10 years per SOLAS requirements.
```

Is this correct? The student model will learn this reasoning chain regardless of whether the facts are right. If the interval is actually different under the specific SOLAS amendment in force, the student has now learned a confidently-reasoned wrong answer.

**For comparison — what s1 proved about data efficiency:**
- s1K used only 1,000 samples but they were EXTREMELY carefully curated
- Selection criteria: difficulty (hard problems), diversity (cover many topics), quality (verified correct)
- This curation is straightforward for math (answers are verifiable) but very hard for maritime (requires domain experts)

**SCORE: 5/10** — Reasoning distillation is efficient for teaching reasoning PATTERNS (few thousand traces may suffice) but highly inefficient for injecting domain KNOWLEDGE (the fact-to-token ratio is ~10x worse than raw text pretraining). The curation problem (ensuring maritime factual accuracy in teacher-generated traces) further reduces effective data efficiency. s1K's extreme data efficiency (1,000 samples) works for reasoning skills but was not demonstrated for domain-specific factual QA.

---

### 5. ACCURACY ON DOMAIN QA — Score: 4/10

**The central question for a maritime chatbot: will reasoning distillation make the model answer maritime questions accurately?**

**Short answer: It makes the model answer MORE CONFIDENTLY but not necessarily MORE CORRECTLY.**

**Breaking down maritime QA into types:**

| Question Type | Example | Does Reasoning Distillation Help? |
|---|---|---|
| **Factual recall** | "What are the 6 annexes of MARPOL?" | NO — requires knowledge, not reasoning |
| **Numerical precision** | "What's the max sulfur content in fuel in SECA zones?" | NO — requires specific value memorization |
| **Procedural** | "Describe the procedure for enclosed space entry" | PARTIALLY — reasoning helps organize steps, but steps must be known |
| **Diagnostic/Troubleshooting** | "Engine vibration after overhaul — causes?" | YES — systematic elimination reasoning is valuable |
| **Regulatory interpretation** | "Does MARPOL Annex VI apply to ships in Arctic waters?" | PARTIALLY — logical reasoning helps, but requires regulatory knowledge |
| **Scenario-based** | "Fire in engine room during port call — immediate actions?" | PARTIALLY — helps prioritize steps, but steps must be known |

**Analysis by question type:**

**For factual recall (40-50% of maritime QA):** Reasoning distillation provides zero benefit. No amount of `<think>` tokens helps you recall "MARPOL Annex I = Oil, Annex II = Noxious Liquids, Annex III = Harmful Substances in Packaged Form..." if that knowledge isn't in the weights. The model will produce a beautiful reasoning trace that arrives at a wrong or incomplete list.

**For diagnostic/troubleshooting (20-30% of maritime QA):** This is WHERE reasoning distillation genuinely shines. A trained CoT model can systematically work through: "High exhaust temperature → check turbocharger → check fuel timing → check piston rings..." This mirrors how the DeepSeek-R1 model excels at multi-step math problems. However, the model must KNOW the valid diagnostic tree — the reasoning pattern alone doesn't tell it that worn piston rings cause blow-by which reduces compression which causes incomplete combustion.

**For procedural questions (15-20%):** Partial benefit. Reasoning helps organize steps in the right order. But the actual steps must come from stored knowledge. "Step 1: Stop all work and evacuate, Step 2: Muster crew, Step 3: Sound alarm..." — each step is a fact the model must recall.

**Comparison with DeepSeek-R1's benchmark performance:**

| Benchmark | Tests | R1-Distill-Qwen-1.5B | Relevance to Maritime QA |
|---|---|---|---|
| MATH-500 | Mathematical reasoning | 83.9% | LOW — math reasoning ≠ domain factual QA |
| AIME 2024 | Competition math | 28.9% | NONE — no factual recall component |
| GPQA-Diamond | Graduate reasoning | 33.8% | MODERATE — some science reasoning applies |
| LiveCodeBench | Code generation | 16.9% | NONE |
| Codeforces | Competitive programming | Rating 954 | NONE |

**Notice: The 1.5B model scores 83.9% on MATH but only 33.8% on GPQA-Diamond.** GPQA requires both reasoning AND knowledge (graduate-level science). The sharp drop from 83.9% to 33.8% reveals exactly the limitation: when domain knowledge is required alongside reasoning, performance drops dramatically, especially at 1.5B scale.

**For maritime QA specifically, I estimate:**
- Pure factual recall questions: ~25-35% accuracy (base model level, reasoning distillation doesn't help)
- Diagnostic/troubleshooting: ~50-65% accuracy (reasoning structure helps organize, but limited by knowledge)
- Procedural/safety: ~30-45% accuracy (some reasoning benefit, but steps must be known)
- Overall domain QA accuracy: ~35-45%

**This is not meaningfully better than an SFT-only approach on Q&A pairs** (estimated 45-55% accuracy), and significantly worse than CPT + SFT (estimated 65-75% accuracy).

**The confidence calibration problem:**
A reasoning-distilled model doesn't just get things wrong — it gets things wrong with elaborate justification. For a maritime safety chatbot, this is arguably WORSE than a model that simply says "I don't know." The reasoning trace creates false authority:

```
<think>
Let me carefully consider the minimum freeboard requirements. The 
International Load Line Convention establishes freeboard tables based on 
vessel type and length... For a Type B vessel of 150m, I should recall 
the tabular freeboard value... I believe it's approximately 2,850mm for 
summer conditions...
</think>

For a Type B vessel of 150m LOA, the minimum summer freeboard under the 
International Load Line Convention is approximately 2,850mm.
```

This sounds authoritative. The reasoning chain is structurally correct. But the specific number may be wrong. A crew member reading this would trust it more than a terse wrong answer because the reasoning chain provides false evidence of knowledge.

**SCORE: 4/10** — Reasoning distillation genuinely helps for diagnostic/troubleshooting questions (~20-30% of maritime QA) but provides minimal benefit for factual recall (~40-50% of maritime QA). Overall estimated accuracy of ~35-45% is insufficient for a safety-critical maritime chatbot. The enhanced confidence of reasoning traces without underlying domain knowledge makes the model MORE dangerously wrong, not less.

---

### 6. MOBILE DEPLOYABILITY — Score: 6/10

**The model size is unchanged. But the output behavior changes significantly.**

**Model itself — same deployment characteristics as any SFT:**
- Qwen-1.5B at 4-bit GGUF: ~1.0-1.2 GB
- Peak RAM: ~1.8-2.2 GB (model + KV cache + runtime)
- Serves via llama.cpp, MLC-LLM, ExecuTorch

**But the KV cache is larger and inference runs longer:**

Reasoning models produce much longer output sequences. The KV cache grows with generated tokens:

| Metric | Standard Model | Reasoning Model | Impact |
|---|---|---|---|
| Average output length | 50-100 tokens | 300-800 tokens | 5-8x more tokens |
| KV cache memory (Qwen-1.7B, 800 tokens) | ~50MB | ~200-400MB | +150-350MB RAM |
| Peak RAM (model + KV cache) | ~2.0 GB | ~2.5-3.0 GB | May exceed low-end phone memory |
| Inference time per query (iPhone 15) | 3-7 sec | 20-55 sec | Unacceptable UX |
| Inference time per query (mid-range Android) | 5-10 sec | 30-80 sec | Very poor UX |
| Battery per query | ~0.01-0.03% | ~0.05-0.15% | 5x worse |

**The KV cache problem on low-RAM phones:**
- iPhone SE / budget Android (3-4GB total RAM): After OS, system services, and the app, only ~1.5-2.5GB available for the model. A standard model fits comfortably. A reasoning model with 800-token output may cause memory pressure, leading to app kills or OOM.
- The KV cache for 800 output tokens on a 28-layer, 16-head model is substantial
- Context window must accommodate user question + reasoning trace + answer

**Can you mitigate with thinking mode toggle?**
- Qwen3 supports `enable_thinking` flag
- Could offer "quick answer" mode (no CoT, fast) vs "detailed reasoning" mode (full CoT, slow)
- But this requires the model to be good at BOTH modes — reasoning distillation typically optimizes for thinking mode only
- If you mostly use non-thinking mode, why did you pay for reasoning distillation?

**Streaming helps but doesn't solve:**
- Can stream the `<think>` tokens as a progress indicator
- User sees "thinking..." with details appearing
- Reduces perceived latency but not actual latency
- Users may find 30+ seconds of "thinking" frustrating for simple factual questions

**The UX design dilemma:**
A maritime chatbot user is a ship engineer or officer asking a quick question during work. They want an answer in 2-5 seconds, not a 30-second philosophical treatise. The reasoning distillation model is designed for problems where deep thinking is valuable (math olympiad). For "What's the SOPEP drill interval?" the thinking overhead is pure waste.

**SCORE: 6/10** — The model file size and format are identical to any SFT model (perfect for mobile). But the dramatically increased output length (5-8x more tokens) degrades latency, increases memory pressure from KV cache, drains battery faster, and creates a poor UX for simple (majority of) maritime queries. The model is deployable but the user experience suffers significantly compared to a non-reasoning model.

---

### 7. ROBUSTNESS — Score: 7/10

**This is ONE of the two genuine strengths of reasoning distillation.**

**Why reasoning distillation improves robustness:**

1. **Rephrasing resistance:** A reasoning model processes the question through explicit internal deliberation before answering. "What causes high exhaust temp?" and "Why is my exhaust running hot?" both trigger the same reasoning chain: identify the components involved → consider each possible cause → eliminate unlikely ones → present likely causes. The reasoning process normalizes different phrasings into the same underlying analytical framework.

2. **Self-verification:** DeepSeek-R1-style models learn to check their own answers during the thinking phase. "Wait, let me verify that..." appears frequently in reasoning traces. This catch-and-correct behavior can prevent some hallucinations — though it requires the model to have the knowledge to verify against.

3. **Handling of complex/multi-part questions:** "If the main engine turbocharger fails and we're in a Special Area under MARPOL Annex I, what are our obligations for engine operation and waste disposal?" — A reasoning model will decompose this into sub-problems (turbocharger failure implications, MARPOL Annex I Special Area requirements) and address each systematically. A standard model might miss one part.

4. **Resistance to misleading questions:** "Is it true that SOLAS requires lifeboats on both sides of the ship?" — A reasoning model is more likely to think through this: "Let me consider what SOLAS actually requires... Chapter III, Regulation 31... lifeboats shall be on each side of the ship sufficient for total complement... wait, that depends on vessel type..." The reasoning process creates a buffer against simply agreeing with the premise.

**Limitations of this robustness:**

- Self-verification only works if the model has the correct knowledge to verify WITH
- For maritime-specific facts the model doesn't know, the reasoning trace will process incorrect premises and arrive at wrong conclusions — just through a more robust-looking process
- The robustness gain is primarily structural (better question decomposition) not factual (better knowledge access)

**Comparison with Orca 2's approach:**
Orca 2 explicitly teaches small LMs to select the RIGHT reasoning strategy per task type:
- Simple factual recall → direct answer (no reasoning overhead)
- Complex diagnosis → step-by-step reasoning
- Regulatory interpretation → recall-then-generate

This task-adaptive approach would be ideal for maritime: most questions need direct factual answers (no reasoning), while ~20-30% benefit from detailed reasoning. But Orca 2 was demonstrated at 7B/13B, not 1.5B.

**SCORE: 7/10** — Reasoning distillation meaningfully improves robustness to rephrasing, multi-part questions, and misleading premises. The systematic reasoning process normalizes diverse input phrasings. However, robustness to factual errors is NOT improved — the model reasons more carefully about things it still doesn't know. This is the second-largest genuine benefit of reasoning distillation (after troubleshooting capability).

---

### 8. CATASTROPHIC FORGETTING — Score: 6/10

**Reasoning distillation via SFT carries the same forgetting risks as any SFT approach.**

**The specific forgetting concern:**

When you SFT a base model on 800K reasoning traces, you're teaching it a specific OUTPUT PATTERN (long `<think>` blocks followed by structured answers). This can override the model's original response patterns. Specifically:

1. **Format forgetting:** The model may lose the ability to give SHORT, DIRECT answers. After training on thousands of long reasoning traces, every answer may come with unnecessary deliberation — even for simple questions. This is a well-documented problem with reasoning-distilled models (DeepSeek-R1 usage guidelines explicitly warn about this).

2. **Knowledge forgetting from SFT:** Any SFT modifies the model's weight distribution. Training on reasoning traces (which are mostly reasoning STRUCTURE, not domain content) may push the model AWAY from the general knowledge distribution it learned during pretraining. In effect, the model trades some general knowledge capacity for reasoning pattern storage.

3. **Language/register shift:** If the reasoning traces are primarily in formal English with specific reasoning vocabulary ("Let me consider...", "Upon reflection..."), the model may become less good at understanding informal maritime queries from crew members ("engine's running weird after we cleaned the cooler").

**Mitigation strategies:**
- Mix 10-20% non-reasoning, direct-answer examples in training data
- Use a low learning rate (2e-5 or lower) for SFT on reasoning traces
- Keep training short (2-3 epochs max)
- Include some general instruction-following data to maintain base capabilities

**Comparison with other approaches:**
- CPT forgetting risk: MODERATE (changes knowledge distribution)
- SFT forgetting risk: LOW-MODERATE (mostly changes output format)
- Reasoning distillation forgetting risk: MODERATE (changes both output format and reasoning behavior)

**The Orca 2 insight is relevant here:** Orca 2 found that teaching small models to IMITATE large model behavior can actually HARM the small model — because the small model doesn't have the capacity to replicate the large model's reasoning. Instead, Orca 2 teaches small models to use DIFFERENT (simpler) strategies matched to their capacity. Reasoning distillation that forces a 1.5B model to produce R1-style long reasoning traces may exceed the model's capacity, leading to degraded quality.

**SCORE: 6/10** — Catastrophic forgetting risk is moderate and manageable with standard mitigations. The unique risk is that reasoning distillation may cause "format forgetting" (model can't give short answers anymore) and may exceed the 1.5B model's capacity to faithfully reproduce complex reasoning patterns. These are not catastrophic but require careful hyperparameter tuning and data mixing.

---

### 9. MAINTENANCE — Score: 5/10

**Updating reasoning traces when maritime regulations change:**

**The update workflow:**
1. Identify changed regulations (e.g., new EEXI requirements, updated MARPOL annex)
2. Create new maritime questions about the changed content
3. Run teacher model (DeepSeek-R1/GPT-4o) to generate new reasoning traces
4. Mix new traces with existing training data
5. Re-run SFT on the student model
6. Validate that new knowledge is learned without forgetting old knowledge
7. Re-quantize and redeploy

**Problems with this workflow:**

**Problem 1 — Teacher knowledge lag:** When IMO adopts a new amendment, the teacher model (DeepSeek-R1, GPT-4o) may not know about it yet. These large models are periodically updated but not continuously. You might need to inject the new regulation text into the teacher's context window and have it reason about it — but this is prompt engineering, not the teacher's internalized knowledge.

**Problem 2 — Reasoning trace conflicts:** If old traces contain reasoning about superseded regulations ("Under the current MARPOL Annex VI, the global sulfur cap is 3.5%..." — which was true before 2020 but is now 0.50%), and new traces contain the updated value, the model receives conflicting signals. Reasoning traces make this WORSE than simple Q&A because the wrong fact is embedded in a long reasoning chain that reinforces it.

**Problem 3 — Full retraining needed:** You can't easily do incremental reasoning distillation. Adding 100 new traces to 50,000 existing ones and re-doing SFT requires retraining from the base model (or from a checkpoint), which is a full training cycle.

**Problem 4 — Evaluation complexity:** For standard QA, you verify "Did the model answer correctly?" For reasoning models, you also need to verify "Did the model reason correctly?" — because a correct final answer reached through incorrect reasoning (e.g., right number for wrong reasons) is still a problem if the reasoning is displayed to the user.

**Comparison with alternatives:**
- RAG: Simply update the document store. Instant. Zero retraining.
- SFT on Q&A: Add new Q&A pairs, quick retrain. Simple to verify.
- CPT on new text: Run incremental CPT on new regulation text. Moderate effort.
- Reasoning distillation: Regenerate traces, retrain, validate reasoning chains. Most complex.

**SCORE: 5/10** — Maintenance is more complex than standard SFT because reasoning traces are harder to update (embedded in long chains), harder to verify (must check reasoning AND conclusion), and require teacher model access for regeneration. The full retrain cycle is similar to other SFT approaches, but quality control is harder because you're maintaining reasoning quality, not just answer quality.

---

### 10. PROVEN AT SMALL SCALE (<3B) — Score: 7/10

**What has actually been proven:**

| Model | Base | Size | Training | Key Result | Relevance |
|---|---|---|---|---|---|
| DeepSeek-R1-Distill-Qwen-1.5B | Qwen2.5-Math-1.5B | 1.5B | 800K reasoning traces SFT | MATH-500: 83.9%, AIME: 28.9% | HIGH — proves reasoning distillation works at 1.5B |
| DeepSeek-R1-Distill-Qwen-7B | Qwen2.5-Math-7B | 7B | 800K reasoning traces SFT | MATH-500: 92.8%, AIME: 55.5% | MODERATE — shows scaling from 1.5B→7B |
| s1-32B | Qwen2.5-32B-Instruct | 32B | 1K curated traces SFT | Exceeds o1-preview on MATH/AIME | LOW — 32B not mobile-deployable |
| Orca 2 | Llama-2 | 7B, 13B | Strategy-adaptive reasoning | Surpasses 5-10x larger models | MODERATE — 7B minimum, strategy selection |

**What has been proven:**
1. ✅ Reasoning distillation from 671B → 1.5B works (DeepSeek-R1 paper)
2. ✅ 1.5B models CAN learn step-by-step reasoning from traces
3. ✅ The distilled 1.5B beats GPT-4o (a 200x+ larger model) on math benchmarks
4. ✅ Smaller datasets (1K-50K) can be effective for reasoning patterns (s1)

**What has NOT been proven:**
1. ❌ Reasoning distillation for DOMAIN-SPECIFIC factual QA at any scale
2. ❌ Reasoning distillation improving factual recall (all benchmarks test reasoning, not recall)
3. ❌ Reasoning distillation on mobile with acceptable latency
4. ❌ Reasoning distillation for non-STEM domains (medicine, law, maritime, etc.)
5. ❌ Long reasoning traces being useful at 1.5B scale for practical QA (as opposed to math competitions)

**The critical gap:** ALL published reasoning distillation results are on MATH, CODE, and LOGIC benchmarks. These are domains where:
- The challenge is REASONING, not KNOWLEDGE
- Answers are VERIFIABLE (mathematical proof, test cases)
- The reasoning pattern is GENERAL (not domain-specific)

No published work has shown reasoning distillation improving, say, medical QA accuracy (where factual knowledge is essential), or legal analysis (where regulatory knowledge is essential), or maritime troubleshooting (where engineering knowledge is essential). The transferability of reasoning distillation results from STEM benchmarks to domain-specific factual QA is an unproven assumption.

**One counter-argument worth noting:** DeepSeek-R1-Distill-Qwen-1.5B achieves a Codeforces rating of 954, which requires not just logic but knowledge of data structures, algorithms, and implementation patterns. This suggests the distillation transferred SOME procedural knowledge alongside reasoning patterns. However, competitive programming knowledge was already in the base Qwen2.5-Math-1.5B model — the distillation activated it effectively. Maritime knowledge is NOT in Qwen's base weights at the same depth.

**SCORE: 7/10** — Strong proof that reasoning distillation works at 1.5B specifically (DeepSeek-R1-Distill-Qwen-1.5B is a landmark result). But the proof is entirely in STEM reasoning domains. Zero evidence for domain-specific factual QA improvement. The gap between "proven to work for math reasoning" and "proven to work for maritime factual QA" is significant and should not be glossed over.

---

## SCORE SUMMARY

| # | Criterion | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Knowledge Retention | **3/10** | Does NOT inject domain knowledge. Teaches reasoning patterns only. The model will reason eloquently about things it doesn't know. |
| 2 | Inference Cost | **4/10** | CoT generates 5-8x more tokens. Mobile latency goes from 3-5s to 20-55s. Battery drain 5x worse. |
| 3 | Training Cost | **5/10** | Teacher API for long reasoning traces is 5-50x more expensive per sample than Q&A generation. Quality control requires domain experts. |
| 4 | Data Efficiency | **5/10** | Efficient for reasoning patterns (~1K-50K traces). Inefficient for knowledge injection (fact-to-token ratio is ~10x worse than CPT). |
| 5 | Accuracy on Domain QA | **4/10** | Helps diagnostic/troubleshooting (~20-30% of queries). Doesn't help factual recall (~40-50% of queries). Overall ~35-45% accuracy. |
| 6 | Mobile Deployability | **6/10** | Model file identical. But KV cache grows with long output, latency 5-8x worse, poor UX for simple queries. |
| 7 | Robustness | **7/10** | Genuine strength. Systematic reasoning normalizes diverse phrasings, handles multi-part questions, resists misleading premises. |
| 8 | Catastrophic Forgetting | **6/10** | Moderate risk. Unique concern: "format forgetting" (model can't give short answers) + capacity mismatch at 1.5B. |
| 9 | Maintenance | **5/10** | More complex than standard SFT — must regenerate traces, validate reasoning chains, handle teacher knowledge lag. |
| 10 | Proven at Small Scale | **7/10** | Proven spectacularly for MATH at 1.5B. Zero evidence for domain-specific factual QA at any scale. |

## **TOTAL SCORE: 52/100**

---

## KEY STRENGTHS (Top 3)

### 1. Diagnostic/Troubleshooting Capability (Accuracy: partial, Robustness: 7/10)
Reasoning distillation genuinely excels at the 20-30% of maritime QA that involves systematic diagnosis. "What causes high exhaust temperature?", "Vibration after overhaul — what went wrong?", "Diagnosing turbocharger surging" — these are multi-step elimination problems structurally similar to the math/logic reasoning that DeepSeek-R1 distillation was designed for. A reasoning-distilled model will systematically work through possible causes, check and eliminate, and arrive at likely diagnoses. This is a REAL and MEANINGFUL improvement over standard SFT for this specific category of questions. No other approach (CPT, SFT, DPO) directly teaches this systematic reasoning behavior.

### 2. Robustness to Diverse Phrasings and Complex Questions (7/10)
The explicit `<think>` phase creates a normalization layer between diverse user inputs and the model's response. Whether a user asks "Why is the engine overheating?", "Engine temp is through the roof", or "What would cause elevated exhaust gas temperatures on a 6-cylinder, 2-stroke crosshead engine?" — the reasoning phase maps all of these to the same underlying analytical framework. This is particularly valuable for maritime chatbots where users range from deck cadets to chief engineers with different technical vocabularies. Multi-part questions ("If the turbocharger fails AND we're in a Special Area AND carrying IMDG cargo...") are decomposed rather than overwhelmed.

### 3. Proven Reasoning Transfer at 1.5B (7/10)
DeepSeek-R1-Distill-Qwen-1.5B is a genuine landmark: a 1.5B model beating GPT-4o on MATH-500 (83.9% vs 74.6%). This proves beyond doubt that reasoning PATTERNS can be distilled from 671B to 1.5B. The mechanism works. The reasoning traces produced by the small model are coherent, include self-verification, and demonstrate genuine analytical capability. This is not an incremental improvement — it's a paradigm shift in what small models can do. The question is not WHETHER reasoning distillation works at small scale (it does, proven), but whether it works for DOMAIN-SPECIFIC FACTUAL QA (unproven).

---

## KEY WEAKNESSES (Top 3)

### 1. ★ CRITICAL: Does NOT Inject Domain Knowledge — The Fundamental Mismatch (Knowledge: 3/10, Accuracy: 4/10)
**This is the fatal flaw for the maritime chatbot use case.** Reasoning distillation teaches the model HOW to think, not WHAT to know. For a maritime chatbot where 40-50% of queries are factual recall ("What are the MARPOL Annex VI emission limits?", "What's the SOLAS Chapter III lifeboat requirement?", "At what pressure should CO2 bottles be tested?"), reasoning distillation provides essentially zero benefit.

The DeepSeek-R1 breakthrough was in MATH, where the challenge is reasoning ability, not knowledge. Mathematics is built on a small set of known axioms and operations — the model already "knows" arithmetic, algebra, and calculus from pretraining. The distillation taught it to APPLY that knowledge through systematic reasoning.

Maritime engineering is the opposite: it's built on thousands of specific facts (regulation values, material properties, procedural steps, equipment specifications) that exist in specialized textbooks and IMO publications. The model does NOT know these from pretraining. Teaching it to reason step-by-step about topics it doesn't know produces beautifully structured wrong answers.

**Analogy:** Reasoning distillation is like teaching someone how to solve puzzles without giving them the puzzle pieces. The technique is valuable, but without the content knowledge, the technique produces nothing useful.

### 2. Inference Cost Makes Mobile UX Unacceptable (Inference Cost: 4/10, Mobile: 6/10)
The defining feature of reasoning models — thinking before answering — is also a mobile deployment liability. Generating 300-800 tokens of `<think>` content before producing a 50-100 token answer means:
- 5-8x longer response time (20-55 seconds vs 3-7 seconds on iPhone 15)
- Unacceptable for the primary use case (ship engineer asking a quick question during a watch)
- Higher memory pressure from the extended KV cache
- 5x more battery consumption per query
- Thermal throttling risk during sustained use

A thinking mode toggle (answer with or without reasoning) can mitigate this, but then you're not using the reasoning capability for most queries. This raises the question: if you're mostly using non-thinking mode, why invest in reasoning distillation at all?

### 3. Confident Wrong Answers Are More Dangerous Than Simple Wrong Answers (Accuracy: 4/10)
A standard model answering "What's the minimum freeboard for a Type B vessel?" might say "approximately 2,800mm" — clearly an estimate, the user knows to verify.

A reasoning-distilled model says:
> *"Let me work through this. The International Load Line Convention, 1966 as amended, provides tabular freeboards. For a Type B vessel, Table B applies. I need to consider the vessel length... For a 150m vessel, the tabular freeboard is... 2,850mm. Then I should apply corrections for block coefficient, depth, superstructure, and bow height. The summer freeboard would be approximately 2,850mm before corrections."*

This sounds like expert analysis. A crew member would trust this answer. But the specific number may be wrong — and the elaborate reasoning creates an unwarranted impression of accuracy. **In maritime safety, a confidently wrong answer wrapped in plausible reasoning is more dangerous than an obviously uncertain one.** The reasoning trace functions as a Gish gallop of false authority.

---

## VERDICT: Is Reasoning Distillation Sufficient ALONE?

# **NO. Emphatically NO.**

**Reasoning distillation ALONE is the WRONG approach for a maritime factbot.** It addresses a problem (reasoning ability) that is secondary to the primary problem (domain knowledge). It's like perfecting your exam technique before attending any classes — the technique is valuable, but without the coursework, you'll fail.

**Reasoning distillation scores 52/100 as a standalone approach** — the lowest of the three approaches evaluated so far (CPT: 61, SFT: 71), and for good reason:
- CPT at least injects domain knowledge (albeit imperfectly)
- SFT at least teaches Q&A behavior on domain content
- Reasoning distillation teaches NEITHER domain knowledge NOR domain-specific Q&A — it teaches general reasoning patterns applicable primarily to STEM problem-solving

**However:** Reasoning distillation has a specific and valuable role in a combined pipeline, specifically for the 20-30% of maritime queries that involve diagnostic reasoning and troubleshooting. It should NOT be the foundation, but it can be a powerful enhancement.

---

## BEST COMBINATION: Where Reasoning Distillation Belongs

### The Correct Role: Phase 3 of a 5-Phase Pipeline

```
PHASE 1: CONTINUED PRETRAINING (CPT) — Foundation [ESSENTIAL]
    │   • Full-weight CPT on raw maritime text (textbooks, IMO conventions)
    │   • Injects domain KNOWLEDGE into weights
    │   • Model learns: terminology, concepts, facts, relationships
    │   • OUTPUT: Maritime-aware base model
    │
    ▼
PHASE 2: SYNTHETIC QA SFT — Chatbot Behavior [ESSENTIAL]
    │   • SFT on teacher-generated Q&A pairs from maritime content
    │   • Model learns: question parsing, answer formatting, knowledge retrieval
    │   • Include: factual recall, procedural, regulatory questions
    │   • OUTPUT: Maritime chatbot that can answer domain questions
    │
    ▼
PHASE 3: REASONING DISTILLATION — Enhancement [VALUABLE BUT OPTIONAL]
    │   • Generate reasoning traces ONLY for diagnostic/troubleshooting questions
    │   • Use Orca 2 strategy: teach WHEN to reason vs. when to answer directly
    │   • Selective: ~2,000-5,000 traces for complex scenarios specifically
    │   • NOT for factual recall questions (those don't need reasoning)
    │   • Include "thinking mode toggle" for user control
    │   • OUTPUT: Maritime chatbot with enhanced diagnostic capability
    │
    ▼
PHASE 4: PREFERENCE ALIGNMENT (DPO/GRPO) — Safety [RECOMMENDED]
    │   • Prefer correct answers over plausible wrong ones
    │   • Teach model to express uncertainty ("I'm not certain" vs confident hallucination)
    │   • Critical for safety-critical maritime applications
    │   • OUTPUT: Safety-aligned maritime chatbot
    │
    ▼
PHASE 5: QUANTIZE + DEPLOY — Mobile [REQUIRED]
        • Q4_K_M GGUF → ~1.0-1.2 GB
        • Enable thinking mode toggle (fast mode default, reasoning on request)
        • Deploy with llama.cpp / MLC-LLM
        • OUTPUT: Production mobile maritime chatbot
```

### Why Phase 3, NOT Phase 1:

| Order | What Happens | Result |
|---|---|---|
| Reasoning distillation FIRST, then CPT + SFT | Model learns to reason → then knowledge injected → reasoning may be partially overwritten by subsequent training | Wasteful — reasoning patterns degraded by later training |
| CPT + SFT FIRST, then reasoning distillation | Model has knowledge → then learns to REASON about its knowledge → reasoning applies to actual domain content | Optimal — reasoning applied to existing knowledge |

**Reasoning distillation is multiplicative, not additive:** It MULTIPLIES the value of existing knowledge by teaching the model to use it systematically. Reasoning × 0 knowledge = 0 useful output. Reasoning × strong knowledge = strong diagnostic capability.

### The Orca 2 Insight Applied to Maritime:

Instead of applying R1-style reasoning to ALL queries, use Orca 2's task-adaptive approach:

| Query Type | Strategy | Reasoning? | Example |
|---|---|---|---|
| Factual recall | Direct answer | NO (2-5 sec) | "What's the SOLAS Chapter III lifeboat requirement?" |
| Simple procedural | Recall-then-generate | NO (3-7 sec) | "What are the steps for enclosed space entry?" |
| Diagnostic | Step-by-step CoT | YES (15-30 sec) | "Engine vibrating after overhaul — causes?" |
| Complex regulatory | Recall-reason-generate | YES (15-30 sec) | "Does MARPOL VI apply in Arctic + SECA?" |
| Emergency | Direct answer (fast) | NO (2-5 sec) | "CO2 system activated accidentally — immediate actions?" |

This means ~70-80% of queries get fast direct answers (good mobile UX) and ~20-30% get enhanced reasoning (worth the latency for complex problems).

---

## FINAL ASSESSMENT

| Aspect | Rating |
|---|---|
| **Reasoning Distillation Alone** | **Insufficient** (52/100) — Worst standalone score. Wrong tool for the job. |
| **As Phase 3 Enhancement** (after CPT + SFT) | **Valuable** (adds ~5-8 points to pipeline score, especially for troubleshooting) |
| **For Diagnostic/Troubleshooting only** | **Strong** (8/10 for this specific question category) |
| **For Factual Recall** | **Useless** (1/10 — doesn't help at all, may make things worse) |

### Comparative Standalone Scores:

| Approach | Total Score | Best Role |
|---|---|---|
| Continued Pretraining (CPT) | 61/100 | Phase 1 — Knowledge foundation |
| Synthetic Data + SFT | 71/100 | Phase 2 — Chatbot behavior + factual QA |
| **Reasoning Distillation** | **52/100** | **Phase 3 — Diagnostic reasoning enhancement** |

### One-Line Summary:
**Reasoning distillation teaches a model HOW to think about maritime problems without teaching it WHAT to think about — it's a powerful amplifier of existing knowledge, but a useless substitute for it.**

### For the Ship Crew Member:
- **Asking "What's the CO2 system test interval?"** → Reasoning distillation adds zero value. CPT + SFT handles this.
- **Asking "Engine overheating after turbocharger cleaning — what went wrong?"** → Reasoning distillation is genuinely valuable. The model systematically considers: Was reassembly correct? Were bearings aligned? Was the nozzle ring properly fitted? Is there an air leak in the exhaust system? This is WHERE reasoning distillation earns its keep.
- **Net assessment:** ~70% of maritime queries don't benefit from reasoning distillation. ~30% benefit significantly. Build the knowledge foundation first (CPT + SFT), then add reasoning as an enhancement.

---

*This evaluation is based on published research from DeepSeek (R1, R1-Distill, DeepSeekMath/GRPO), Stanford/UW (s1), Microsoft (Orca 1/2, Phi-3), Google (GKD), Meta (Self-Rewarding LMs), HuggingFace (Open-R1, SmolLM3), and the Qwen team (Qwen3). All scores reflect the approach's performance when used ALONE for building a maritime factual QA chatbot at the 1-3B scale on mobile devices, which is the evaluated question. Reasoning distillation scores higher as a COMPONENT of a multi-phase pipeline (see Best Combination section).*
