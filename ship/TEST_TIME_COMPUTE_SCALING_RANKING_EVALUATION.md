# RANKING EVALUATION: Test-Time Compute Scaling (Think Longer, Not Train Bigger)

**Approach Under Evaluation:** Instead of making models bigger or training them more, let small models THINK LONGER at inference time. Use Chain-of-Thought reasoning, budget forcing, self-consistency, best-of-N sampling, and built-in thinking modes to extract more accurate answers from a smaller model at the cost of longer inference time. The premise: a 1B model that thinks for 30 seconds can outperform a 3B model that answers instantly.

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B parameters  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH SOURCES ANALYZED

| Paper / Resource | Key Finding for This Evaluation |
|---|---|
| **s1: Simple test-time scaling** (Muennighoff, Yang, Shi et al., 2025; arXiv:2501.19393) | Curated 1,000 reasoning traces (s1K dataset). Developed "budget forcing" — appending "Wait" tokens when the model tries to stop thinking early, forcing it to double-check and often self-correct. s1-32B (SFT on Qwen2.5-**32B**-Instruct) exceeded o1-preview on MATH and AIME24 by up to 27%. Budget forcing extrapolated from 50% to 57% on AIME24. **CRITICAL CORRECTION: The user's description claims "a 1B model exceeding o1-preview." This is INCORRECT. s1 used a 32B base model, NOT 1B. The paper does NOT demonstrate this at small scale. The 1,000-example training is data-efficient, but the base model is massive.** |
| **DeepSeek-R1: Incentivizing Reasoning via RL** (DeepSeek-AI, 2025; arXiv:2501.12948; published in Nature 2025) | Pure RL (no human-labeled reasoning trajectories) produces emergent self-reflection, verification, and dynamic strategy adaptation. Reasoning patterns from large R1 model can be **distilled to smaller models** including Qwen2.5-1.5B. **Key for our case: distillation of reasoning to 1.5B models is explicitly demonstrated, but with significant quality degradation. The distilled 1.5B is far below the full R1 on complex tasks.** |
| **Scaling LLM Test-Time Compute Optimally** (Snell, Lee, Xu, Kumar, 2024; arXiv:2408.03314) | Analyzed two mechanisms: (1) searching against process-based verifiers, (2) adaptive distribution updates at test time. Compute-optimal strategy improves efficiency 4x over best-of-N. **CRITICAL FINDING: "On problems where a smaller base model attains somewhat non-trivial success rates, test-time compute can be used to outperform a 14x larger model." The qualifier "non-trivial success rates" is KEY — if the 1B model has ~0% chance of knowing a specific MARPOL regulation, no amount of test-time compute compensates. TTC only amplifies existing capability, it does not create new knowledge.** |
| **Self-Consistency Improves Chain of Thought Reasoning** (Wang, Wei, Schuurmans et al., 2022; arXiv:2203.11171; ICLR 2023) | Sample diverse reasoning paths, select most consistent answer via majority vote. Boosts CoT across benchmarks: GSM8K +17.9%, SVAMP +11.0%, AQuA +12.2%, StrategyQA +6.4%, ARC-challenge +3.9%. **Important: all gains are on REASONING tasks (arithmetic, common sense reasoning). No evaluation on factual recall. Self-consistency requires N complete generations — on mobile, this multiplies inference cost by N.** |
| **Tree of Thoughts: Deliberate Problem Solving** (Yao, Yu, Zhao et al., 2023; arXiv:2305.10601; NeurIPS 2023) | Explores multiple reasoning paths with lookahead and backtracking. Game of 24: GPT-4 with CoT only 4%, ToT achieved 74%. **Spectacular for search-like reasoning tasks. But requires multiple model calls per problem — potentially 10-50x more inference compute. On a mobile phone CPU, this means minutes per answer. Also: ToT's gains are on tasks requiring EXPLORATION AND SEARCH, not factual recall. Maritime regulatory questions rarely require search — they require KNOWLEDGE.** |
| **Large Language Monkeys: Scaling via Repeated Sampling** (Brown, Juravsky, Ehrlich et al., 2024; arXiv:2407.21787) | Coverage (fraction of problems solved by ANY sample) scales log-linearly with sample count. SWE-bench Lite: 15.9% with 1 sample → 56% with 250 samples. **DEVASTATING FINDING for our use case: "In domains without automatic verifiers, common methods for picking from a sample collection (majority voting and reward models) plateau beyond several hundred samples and fail to fully scale with the sample budget." Maritime QA has no automatic verifier — we can't programmatically check if a SOLAS answer is correct. This severely limits repeated sampling's benefit.** |
| **OpenAI o1: Learning to Reason with LLMs** (OpenAI, 2024; openai.com/index/learning-to-reason-with-llms/) | RL teaches model to use chain of thought productively. AIME 2024: 74% pass@1, 83% cons@64, 93% with 1000-sample re-ranking. GPQA Diamond: surpassed human PhD-level accuracy. Performance scales smoothly with both train-time and test-time compute. **Key insight: "o1 is not preferred on some natural language tasks, suggesting that it is not well-suited for all use cases." Thinking helps reasoning but can HURT conversational quality — relevant for a chatbot that must be friendly and conversational.** |
| **Qwen3 Technical Report** (Qwen Team, 2025; arXiv:2505.09388) | Models from 0.6B to 235B with unified thinking/non-thinking mode. Thinking budget mechanism allows adaptive compute allocation. Models at 0.6B and 1.7B include thinking capability. **MOST DIRECTLY RELEVANT: Qwen3-0.6B and Qwen3-1.7B are production models with built-in thinking mode at exactly our target scale. The thinking budget mechanism is budget forcing built into the model. Knowledge distillation from flagship models reduces training cost for smaller scales.** |
| **Chain-of-Thought Prompting** (Wei, Wang, Schuurmans et al., 2022; arXiv:2201.11903) | Original CoT paper. Adding "Let's think step by step" to prompts enables multi-step reasoning. Works best at scale — CoT provides little or no benefit for models below ~10B parameters in the original experiments. **CRITICAL: The original CoT paper found that CoT is an EMERGENT CAPABILITY that appears at scale. Sub-10B models showed minimal CoT benefit. Later work (R1 distillation, s1, Qwen3) has partially addressed this through explicit training for reasoning, but the fundamental capacity constraint remains.** |

---

## THE FUNDAMENTAL QUESTION THIS EVALUATION MUST ANSWER

**Can test-time compute scaling compensate for a smaller model? Can a 1B model with 30 seconds of thinking beat a 3B model with instant answers, for FACTUAL maritime questions with all knowledge baked into weights?**

### The Answer: Mostly No — TTC Amplifies Reasoning, Not Knowledge

Test-time compute scaling is one of the most important advances of 2024-2025. The results are spectacular — on math competitions, coding contests, and logical puzzles. But there is a fundamental category error in applying this to a maritime factual chatbot:

**TTC helps models REASON better over knowledge they ALREADY HAVE. It does NOT inject new knowledge.**

```
┌──────────────────────────────────────────────────────────────────────────┐
│              THE REASONING vs. KNOWLEDGE DISTINCTION                     │
│                                                                          │
│   WHAT TTC DOES WELL:                                                    │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │  "If a vessel's displacement is 15,000 tonnes and TPC is     │     │
│   │   22, how much will it sink if 440 tonnes of cargo is        │     │
│   │   loaded?"                                                    │     │
│   │                                                               │     │
│   │   → This is ARITHMETIC + REASONING. The model needs:          │     │
│   │     • Knowledge: TPC formula (sinkage = mass/TPC)             │     │
│   │     • Reasoning: 440/22 = 20 cm                               │     │
│   │                                                               │     │
│   │   CoT helps: "Let me think... TPC means tonnes per           │     │
│   │   centimetre immersion. So sinkage = 440/22 = 20 cm."        │     │
│   │                                                               │     │
│   │   TTC BENEFIT: HIGH — the step-by-step process               │     │
│   │   reduces calculation errors significantly                    │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│   WHAT TTC CANNOT DO:                                                    │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │  "What is the minimum fire pump capacity required under       │     │
│   │   SOLAS Chapter II-2 Regulation 10.2.2.4 for a cargo         │     │
│   │   vessel of 4,000 GT?"                                        │     │
│   │                                                               │     │
│   │   → This is PURE FACTUAL RECALL. The model either:            │     │
│   │     • HAS this fact in its weights → answers correctly        │     │
│   │     • DOES NOT have it → no amount of thinking helps          │     │
│   │                                                               │     │
│   │   CoT "thinking": "Let me think... SOLAS Chapter II-2...     │     │
│   │   fire pumps... I need to recall Regulation 10.2.2.4...      │     │
│   │   I'm not sure of the exact figure... maybe 140 m³/h?"       │     │
│   │                                                               │     │
│   │   TTC BENEFIT: ZERO — you cannot reason your way to          │     │
│   │   a specific regulatory number you never learned              │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│   MARITIME CHATBOT QUESTION DISTRIBUTION:                                │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │                                                               │     │
│   │   Pure Factual Recall ████████████████████████  ~55%          │     │
│   │   "What does MARPOL Annex I regulate?"                        │     │
│   │   "What is the STCW rest period requirement?"                 │     │
│   │                                                               │     │
│   │   Recall + Explanation ████████████  ~25%                     │     │
│   │   "Explain the diesel engine 4-stroke cycle"                  │     │
│   │   "Why is inert gas used in cargo tanks?"                     │     │
│   │                                                               │     │
│   │   Reasoning Over Domain Knowledge ██████  ~15%                │     │
│   │   "If lube oil temp rises and pressure drops, diagnose"       │     │
│   │   "Compare Type A and Type B vessels for freeboard"           │     │
│   │                                                               │     │
│   │   Complex Multi-step Problems ██  ~5%                         │     │
│   │   "Calculate trim change after shifting 200T of fuel"         │     │
│   │   "If CO2 system fails during tank testing with IG on..."     │     │
│   │                                                               │     │
│   │   TTC provides MEANINGFUL benefit: ~20% of questions          │     │
│   │   TTC provides MARGINAL benefit:   ~25% of questions          │     │
│   │   TTC provides ZERO benefit:       ~55% of questions          │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│   THE VERDICT: TTC helps with ~20% of maritime questions                 │
│   significantly, helps marginally with ~25%, and is useless              │
│   for over half of them. It CANNOT replace the need for                  │
│   maritime knowledge in the model's weights.                             │
└──────────────────────────────────────────────────────────────────────────┘
```

### The s1 "1B Model" Myth — Correcting the Record

The user's approach description states: *"s1 showed a 1B model exceeding o1-preview on AIME with just 1000 training examples!"*

**This is factually incorrect.** The s1 paper (arXiv:2501.19393) used **Qwen2.5-32B-Instruct** as the base model — a 32B parameter model, not 1B. The 1,000 training examples are data-efficient, but they were applied to a massive foundation.

What s1 actually showed:
- **32B model + 1K reasoning traces + budget forcing** → exceeds o1-preview on math
- **Budget forcing** → extrapolates from 50% to 57% on AIME24

At 1B scale, the picture is very different:
- Qwen3-0.6B and Qwen3-1.7B have built-in thinking modes, but their benchmark scores on reasoning tasks are dramatically lower than 8B+ models
- DeepSeek-R1 distilled to 1.5B shows improved reasoning but is far below the full R1
- The original CoT paper (Wei et al., 2022) found CoT provides minimal benefit below ~10B parameters

**The "think longer = beat bigger model" equation only holds when the smaller model has the KNOWLEDGE BASE to reason over. At 1B scale, knowledge capacity is the bottleneck, not reasoning depth.**

### What TTC Actually Offers for Maritime Mobile Chatbot

Test-time compute scaling is NOT a standalone approach. It is an **inference-time enhancement** that sits on top of whatever knowledge injection method you use. The correct framing is:

```
WRONG FRAMING:  "Use TTC INSTEAD of a bigger model"
RIGHT FRAMING:  "Use TTC ON TOP of a knowledge-injected small model"

WRONG:  1B model + TTC → beats 3B model (for factual maritime Q&A)
RIGHT:  1B model + CPT + SFT + TTC → beats same 1B model + CPT + SFT
        (but still likely worse than 3B model + CPT + SFT for factual recall)
```

The legitimate value proposition:
1. **Enable a 1B model to match a 1.5B model** on reasoning-heavy questions → saves ~500MB RAM on phone
2. **Improve reasoning quality** on the 20% of maritime questions involving multi-step analysis
3. **Enable self-correction** — the model catches its own errors during the thinking process
4. **Control accuracy/speed tradeoff** — simple questions get fast answers, complex ones get longer thinking

The illegitimate claim:
- A 1B model with TTC CANNOT match a 3B model on factual recall. The 3B model has 3x more parameters encoding 3x more factual knowledge. No amount of thinking recovers knowledge that was never learned.

---

## THE MOBILE INFERENCE COST REALITY

This is the crux of the tradeoff. TTC saves RAM (smaller model) but costs TIME and BATTERY:

```
┌────────────────────────────────────────────────────────────────────────┐
│                    MOBILE INFERENCE ARITHMETIC                         │
│                                                                        │
│   BASELINE: 3B Q4_K_M on iPhone 15 (A17 Pro)                          │
│   ├── RAM: ~2.4 GB                                                     │
│   ├── Speed: ~15-25 tokens/sec                                         │
│   ├── 200-token answer: ~8-13 seconds                                  │
│   └── Single forward pass, no overhead                                 │
│                                                                        │
│   TTC OPTION A: 1B Q4_K_M + Chain-of-Thought                          │
│   ├── RAM: ~0.8 GB (saves 1.6 GB — REAL ADVANTAGE)                    │
│   ├── Speed: ~30-50 tokens/sec (faster per token)                      │
│   ├── Thinking chain: ~300-800 tokens (hidden from user)               │
│   ├── Final answer: ~200 tokens (shown to user)                        │
│   ├── Total generation: 500-1000 tokens                                │
│   ├── Time: ~10-33 seconds                                             │
│   └── Power: comparable to baseline (more tokens but smaller model)    │
│                                                                        │
│   TTC OPTION B: 1B Q4_K_M + Self-Consistency (N=5)                    │
│   ├── RAM: ~0.8 GB (still small — good)                                │
│   ├── Generations: 5 × 500 tokens = 2,500 tokens                      │
│   ├── Time: ~50-165 seconds (1-3 MINUTES per question!)                │
│   ├── Power: 5x baseline — significant battery drain                   │
│   └── UX: Unacceptable wait time for mobile app                        │
│                                                                        │
│   TTC OPTION C: 1B Q4_K_M + Budget Forcing (extended thinking)        │
│   ├── RAM: ~0.8 GB                                                     │
│   ├── Thinking chain: ~500-2000 tokens (appending "Wait")              │
│   ├── Total generation: 700-2200 tokens                                │
│   ├── Time: ~14-73 seconds                                             │
│   ├── Average realistic: ~20-40 seconds                                │
│   └── UX: Borderline acceptable with "thinking..." animation           │
│                                                                        │
│   TTC OPTION D: 1B Q4_K_M + Tree of Thought                           │
│   ├── RAM: ~0.8 GB                                                     │
│   ├── Multiple reasoning branches: 3-10 branches × 300 tokens          │
│   ├── Total generation: 900-3000 tokens + selection overhead            │
│   ├── Time: ~30-100 seconds                                            │
│   ├── Requires tree management logic in app                             │
│   └── UX: Unacceptable for mobile chatbot                              │
│                                                                        │
│   VERDICT ON MOBILE:                                                    │
│   • CoT (Option A): ✅ VIABLE — similar time to baseline, saves RAM    │
│   • Budget Forcing (Option C): ⚠️  MARGINAL — 20-40s wait is long     │
│   • Self-Consistency (Option B): ❌ TOO SLOW — minutes per question    │
│   • Tree of Thought (Option D): ❌ TOO SLOW — minutes per question     │
│                                                                        │
│   PRACTICAL TTC ON MOBILE = CoT only, maybe budget forcing              │
│   The more powerful TTC techniques are infeasible on mobile              │
└────────────────────────────────────────────────────────────────────────┘
```

### The RAM Advantage is Real but Limited

A 1B model uses ~0.8 GB (Q4) vs a 3B model at ~2.4 GB. This saves ~1.6 GB of RAM — meaningful on a 6 GB phone. But:

- The 3B model can answer in 8-13 seconds with no overhead
- The 1B model with CoT takes 10-33 seconds
- The 1B model has **fundamentally less factual knowledge capacity**
- The 3B model at Q3 (~1.8 GB) offers a better tradeoff: more knowledge, less RAM than full Q4, faster than TTC

**The RAM savings from TTC are real, but achievable through quantization alone without the accuracy penalty of a smaller model.**

---

## CRITERION-BY-CRITERION EVALUATION

### 1. Knowledge Retention — Score: 3/10

**Test-time compute scaling is NOT a knowledge injection technique.**

This is the fundamental limitation that caps the entire evaluation. TTC helps a model USE knowledge it already has more effectively. It does not ADD knowledge. For a maritime chatbot where the explicit requirement is "all knowledge in weights":

- The model must already contain SOLAS, MARPOL, STCW, MLC, COLREG, diesel engineering, ship construction, stability calculations, firefighting systems, ballast water management, etc.
- TTC does NOTHING to put this knowledge into the weights
- A 1B model has ~1 billion parameters to encode ALL of this (plus English language, conversation ability, safety behavior)
- A 3B model has 3x more capacity for knowledge storage

**Evidence from Snell et al. (2408.03314):** "Test-time compute can outperform a 14x larger model" — but ONLY on problems where the smaller model has "non-trivial success rates." For specific maritime regulatory facts, a 1B model that was never trained on SOLAS may have a 0% success rate. TTC × 0% = 0%.

**Evidence from original CoT paper (Wei et al., 2022):** CoT shows minimal benefit below ~10B parameters. While Qwen3 and R1-distilled models have partially overcome this through explicit reasoning training, the fundamental capacity limitation at 1B scale remains.

**What TTC CAN do for knowledge access:**
- CoT can help the model systematically RETRIEVE knowledge it has: "Let me think about engine room fire safety... SOLAS Chapter II-2... fire detectors... CO2 systems... fire dampers..." — this sequential retrieval from weights IS enhanced by step-by-step thinking
- But this only retrieves knowledge that EXISTS in the weights — it cannot create knowledge from nothing

**Score justification:** 3/10 because TTC provides zero knowledge injection. The knowledge must come from elsewhere (CPT, SFT, pretraining). TTC alone with a generic 1B base model would have no maritime knowledge. The 3 points acknowledge that CoT-style sequential retrieval does mildly improve recall from existing weights.

### 2. Inference Cost — Score: 3/10

**TTC BY DEFINITION increases inference cost. That is the entire trade-off.**

The approach description explicitly acknowledges this: "Trade-off: more compute time vs better accuracy." On a mobile phone running on battery with no GPU, inference cost is a critical constraint.

**Concrete inference costs on ARM CPU:**

| Method | Tokens Generated | Time (1B Q4 @ 30 tok/s) | Battery Impact |
|---|---|---|---|
| Direct answer (no TTC) | ~200 | ~7 seconds | Baseline |
| Chain-of-Thought | ~500-800 | ~17-27 seconds | 2.5-4x |
| Budget Forcing | ~700-2000 | ~23-67 seconds | 3.5-10x |
| Self-Consistency (N=5) | ~2500-4000 | ~83-133 seconds | 12-20x |
| Best-of-N (N=3) | ~1500-2400 | ~50-80 seconds | 7-12x |
| Tree of Thought | ~1500-5000 | ~50-167 seconds | 7-25x |

**For a mobile chatbot, response time directly affects user experience:**
- 0-5 seconds: Excellent — feels instant
- 5-15 seconds: Good — acceptable with loading indicator
- 15-30 seconds: Marginal — users may abandon
- 30-60 seconds: Poor — competitive disadvantage
- 60+ seconds: Unacceptable — users uninstall

CoT pushes response times into the "marginal" zone. Self-consistency and Tree of Thought push into "unacceptable" territory. Only simple CoT is realistically deployable on mobile.

**The RAM savings partially offset this:** A 1B model uses 1.6 GB less RAM than a 3B model, leaving more room for the OS and other apps. But RAM is a one-time allocation — inference cost is paid on EVERY query. A maritime engineer using the chatbot during watch duty might ask 20-50 questions per session. At 25 seconds per question with CoT, that's 8-20 minutes of waiting vs 2-4 minutes with a direct-answer 3B model.

**Score justification:** 3/10 because TTC fundamentally trades inference efficiency for accuracy. On mobile, where compute is scarce and battery is finite, this trade-off is punishing. Only the lightest TTC techniques (simple CoT) are feasible.

### 3. Training Cost — Score: 9/10

**This is TTC's strongest dimension. The training cost is negligible.**

| TTC Training Method | Data Required | Compute | Cost |
|---|---|---|---|
| s1-style SFT for reasoning | ~1,000 reasoning traces | Hours on 1 GPU | ~$10-$50 |
| Budget forcing setup | Zero (inference trick) | Zero | $0 |
| Self-consistency | Zero (inference trick) | Zero | $0 |
| Best-of-N | Optional: train simple scoring function | Hours on 1 GPU | ~$10-$50 |
| Distill R1 reasoning to 1B | ~10K-100K thinking traces | Day on 1-4 GPUs | ~$50-$500 |
| Qwen3 thinking mode | Zero (pre-built) | Zero | $0 |

**Compare to other knowledge injection approaches:**
- Pre-training from scratch: $100K-$300K
- Continued Pre-Training: $50-$500  
- SFT alone: $10-$100
- TTC training: $0-$500

The s1 approach is remarkably data-efficient: 1,000 curated reasoning traces produce meaningful improvements. Budget forcing and self-consistency require zero training — they are pure inference-time techniques.

**Why not 10/10:** If you want to distill R1-quality reasoning into a 1B model, you need to generate or obtain reasoning traces and run SFT — this has a non-zero cost. Also, the TTC training does NOT include maritime knowledge injection, which must be done separately (adding CPT/SFT cost on top).

### 4. Data Efficiency — Score: 8/10

**Extremely data-efficient for the REASONING component.**

- s1 used exactly 1,000 training examples (the s1K dataset)
- Budget forcing requires zero additional data
- Self-consistency requires zero data
- Qwen3's thinking mode ships pre-trained

Three criteria validated by s1 for selecting reasoning traces: **difficulty, diversity, and quality** — each verified through ablations. 1,000 well-chosen examples suffice.

**The critical caveat:** This data efficiency applies to REASONING ABILITY, not to DOMAIN KNOWLEDGE. The s1K dataset taught the Qwen2.5-32B model how to think better — it did not teach it new facts about math. The model already knew math from its 18T-token pretraining.

For maritime: you'd need:
1. Reasoning traces: ~1,000 maritime reasoning examples → data-efficient ✅
2. Maritime knowledge: ~500M-5B tokens of domain text → NOT data-efficient (same as CPT)

TTC is data-efficient for what it does (teaching reasoning patterns), but it doesn't do what the maritime chatbot primarily needs (learn domain facts).

**Score justification:** 8/10 for reasoning data efficiency. The 2-point deduction acknowledges that TTC's data efficiency is for reasoning patterns, not domain knowledge — and the chatbot needs both.

### 5. Accuracy on Domain QA — Score: 4/10

**The critical question: does TTC improve maritime QA accuracy?**

**Analyzing by question type:**

| Question Type | % of Maritime QA | TTC Benefit | Example |
|---|---|---|---|
| Pure factual recall | ~55% | None (0%) | "What does MARPOL Annex VI regulate?" |
| Recall + explanation | ~25% | Marginal (5-15%) | "Explain why bilge water must be treated before discharge" |
| Reasoning over domain facts | ~15% | Significant (15-30%) | "If turbocharger rpm drops and exhaust temp rises, diagnose" |
| Complex multi-step problems | ~5% | Large (20-50%) | "Calculate final KG after loading sequence of 5 cranes" |

**Weighted average TTC improvement on maritime QA:**
$0.55 \times 0\% + 0.25 \times 10\% + 0.15 \times 22\% + 0.05 \times 35\% = 0 + 2.5 + 3.3 + 1.75 = 7.6\%$

**A ~7-8% improvement on domain QA from TTC alone.** This is meaningful but far from transformative.

**Evidence from the papers:**
- Self-consistency boosts GSM8K by 17.9% — but GSM8K is 100% math reasoning. Maritime QA is only ~20% reasoning-heavy.
- o1 improves AIME from 12% to 74% — but AIME is pure math competition. Maritime is mostly factual.
- ToT improves Game of 24 from 4% to 74% — but Game of 24 requires SEARCH, not knowledge.
- o1 "is not preferred on some natural language tasks" — conversational maritime explanations may actually SUFFER from overthinking.

**The 1B vs 3B knowledge gap:**
A 3B model has 3x the parameter count to store factual knowledge. Even with perfect TTC, the 1B model at Q4 stores ~0.8 GB of compressed knowledge vs ~2.4 GB in the 3B model. For factual maritime questions, this knowledge gap is insurmountable through reasoning alone.

**Self-consistency's verifier problem (from Large Language Monkeys):**
Brown et al. (2407.21787) found that "in domains without automatic verifiers, common methods for picking from a sample collection plateau beyond several hundred samples." Maritime QA has NO automatic verifier — you can't programmatically check if a SOLAS answer is correct. This means self-consistency and best-of-N have limited effectiveness for maritime.

**Score justification:** 4/10 because TTC provides meaningful improvement only on the ~20% of maritime questions involving reasoning, and the 1B model lacks the factual capacity of larger alternatives. The approach is genuinely useful for the reasoning-heavy minority of questions but irrelevant for the factual-recall majority.

### 6. Mobile Deployability — Score: 5/10

**Mixed. The model is small (good), but the inference pattern is hostile to mobile.**

**Advantages:**
- 1B Q4 model: ~0.8 GB RAM — excellent for mobile (leaves plenty for OS)
- Model file: ~600-800 MB storage — manageable
- llama.cpp / MLC-LLM support thinking tokens natively
- Qwen3-0.6B and Qwen3-1.7B are production models with built-in thinking mode
- No external server, no internet, no RAG infrastructure

**Disadvantages:**
- Extended generation time: 15-60+ seconds per query (CoT/budget forcing)
- Higher battery drain per query (more tokens generated)
- Screen shows "thinking..." for extended periods — poor UX
- Multiple generations (self-consistency, best-of-N) multiply all costs
- Tree of Thought requires complex tree management logic in the app
- Thinking tokens consume KV-cache memory — partially offsetting RAM savings
- User on a ship with limited charging may drain battery faster

**KV-cache reality for thinking tokens:**
A 1B model generating 1000 thinking tokens needs KV-cache for all 1000 tokens. At FP16, this is ~50-100 MB. Not huge, but it partially erodes the RAM advantage of using a smaller model. A 3B model generating 200 tokens (no TTC) uses similar KV-cache.

**Practical mobile TTC:**
- Simple CoT: ✅ Viable — adds 10-20 seconds, manageable with "thinking" UI
- Budget forcing (moderate): ⚠️ Borderline — 20-40 second waits
- Self-consistency/Best-of-N: ❌ Impractical — minutes per query
- Tree of Thought: ❌ Impractical — complex and slow

**Qwen3 thinking budget mechanism:** The adaptive compute allocation in Qwen3 is promising — simple questions get fast answers (non-thinking mode), complex ones trigger thinking. This is the most mobile-friendly TTC design, but still constrained by token generation speed on ARM CPUs.

**Score justification:** 5/10 — the model itself is highly deployable (small, efficient), but the extended inference pattern degrades mobile UX significantly. Only Simple CoT is practical on mobile, which limits TTC benefits to minimal improvements.

### 7. Robustness — Score: 6/10

**TTC improves robustness for reasoning tasks but introduces new failure modes.**

**Robustness improvements from TTC:**
- **Self-correction:** CoT and budget forcing allow the model to catch and fix errors during thinking: "Wait, let me reconsider... SOLAS Chapter II-2, not Chapter II-1..."
- **Diverse reasoning paths:** Self-consistency explores multiple approaches, reducing sensitivity to prompt phrasing
- **Safety through reasoning:** o1 showed "chain of thought reasoning contributed to capability improvements" in safety evaluations — the model reasons about safety rules rather than pattern-matching

**OpenAI o1 safety data:**
- Safe completions on challenging jailbreaks: GPT-4o 71.4% → o1 93.4%
- This improvement comes from the model REASONING about whether a request is harmful

**New failure modes from TTC:**
- **Overthinking simple questions:** "What does MARPOL stand for?" → The model launches into a 500-token reasoning chain about maritime pollution conventions when a one-line answer suffices. Qwen3's thinking/non-thinking mode addresses this, but incorrect mode selection wastes compute.
- **Reasoning chain errors propagating:** A wrong fact early in the chain corrupts all subsequent reasoning. In a 1000-token thinking chain, error probability increases with chain length.
- **Hallucination amplification:** Thinking longer gives the model more opportunities to generate plausible-sounding but incorrect reasoning. Without a verifier, these hallucinations are presented confidently.
- **Verbosity degradation in chatbot context:** o1 was "not preferred on some natural language tasks." A maritime chatbot should sometimes give concise, direct answers — TTC can make every response feel like a lecture.

**For maritime safety-critical context:**
The self-correction property is genuinely valuable — a model that says "Wait, I should check: is the sulphur limit 0.50% or 0.10% in ECAs? It's 0.10% in ECAs, 0.50% globally" is safer than one that confidently states the wrong figure. But this only works if both facts are in the model's weights.

**Score justification:** 6/10 — meaningful robustness improvements from self-correction, partially offset by new failure modes (overthinking, error propagation, hallucination amplification). The net effect is modestly positive for a maritime chatbot.

### 8. Catastrophic Forgetting — Score: 8/10

**TTC training is extremely lightweight — minimal forgetting risk.**

The reasoning capability is added via:
- SFT on ~1,000 reasoning traces (s1 approach) — too few examples to cause meaningful forgetting
- Or: using a model with built-in thinking mode (Qwen3) — zero additional training
- Or: budget forcing at inference time — zero training at all

**Compare to heavier knowledge injection:**
- CPT on 500M tokens: moderate forgetting risk (learning rate, epochs matter)
- Full SFT on 50K examples: moderate forgetting risk
- TTC SFT on 1K examples: negligible forgetting risk
- Budget forcing: zero forgetting risk (it's inference-time only)

**Evidence from s1:** The s1-32B model was fine-tuned on Qwen2.5-32B-Instruct with just 1,000 examples. The paper reports improved reasoning WITHOUT significant degradation on other tasks — confirming that lightweight SFT for reasoning patterns preserves existing capabilities.

**Caveat:** TTC training doesn't cause forgetting, but it also doesn't prevent forgetting from OTHER training steps. If you CPT a model for maritime knowledge (causing some forgetting) and then apply TTC training, the TTC doesn't recover what was lost during CPT.

**Score justification:** 8/10 — TTC training is too lightweight to cause meaningful forgetting. Budget forcing and self-consistency cause zero forgetting (inference-only). The 2-point deduction acknowledges that TTC must be combined with other methods (CPT/SFT) that DO carry forgetting risk.

### 9. Maintenance — Score: 8/10

**TTC mechanisms are independent of domain knowledge — easy to maintain.**

When maritime regulations change:
1. Update domain knowledge via CPT/SFT (standard process regardless of TTC)
2. TTC reasoning patterns remain valid — "think step-by-step" doesn't expire
3. Budget forcing works identically with updated knowledge
4. Self-consistency works identically
5. No TTC-specific retraining needed for new regulations

**The reasoning patterns are domain-agnostic:** "Let me break this problem into parts," "Wait, let me double-check," "First, I'll identify the relevant regulation, then apply it to this scenario" — these meta-reasoning strategies work regardless of whether MARPOL Annex VI refers to 0.50% or 0.10% sulphur limit.

**Compare to approaches where updates are harder:**
- From-scratch pretraining: $100K+ per update
- Merged models: require re-merging with updated components
- TTC: update the underlying model (via CPT/SFT), TTC continues working

**Score justification:** 8/10 — TTC is a stable layer that doesn't need updating when domain knowledge changes. The 2-point deduction: if the reasoning fine-tuning (s1-style) needs to be redone after each base model update, there's a small recurring cost.

### 10. Proven at Small Scale — Score: 3/10

**This is TTC's CRITICAL WEAKNESS for our use case. The evidence at 1-3B scale is thin.**

**What has been proven:**

| Model | Scale | TTC Method | Finding |
|---|---|---|---|
| s1-32B | **32B** | Budget forcing | Exceeds o1-preview on MATH/AIME |
| o1 | ~200B (est.) | RL + CoT | AIME 74%, GPQA > human PhD |
| DeepSeek-R1 | 671B MoE | RL + reasoning | Emergent self-reflection, Nature 2025 |
| R1-distilled-Qwen-1.5B | **1.5B** | Distilled reasoning | Improved reasoning vs base, but FAR below R1 |
| Qwen3-0.6B | **0.6B** | Built-in thinking mode | Available; benchmark scores dramatically lower than 8B+ |
| Qwen3-1.7B | **1.7B** | Built-in thinking mode | Available; better than 0.6B but still severely limited |

**What has NOT been proven:**
- ❌ A 1B model with TTC outperforming a 3B model on FACTUAL recall tasks
- ❌ TTC at 1B scale improving domain-specific QA (medical, legal, engineering, maritime)
- ❌ TTC at 1B scale producing answers competitive with larger models on knowledge-intensive benchmarks
- ❌ Budget forcing effectiveness at 1B scale (s1 used 32B)
- ❌ Self-consistency improving factual accuracy (all evidence is on reasoning tasks)

**The original Chain-of-Thought finding (Wei et al., 2022):**
CoT is an EMERGENT capability that appears at scale. The original paper found minimal benefit below ~10B parameters. While Qwen3 and R1 distillation have partially addressed this through explicit training for reasoning patterns at smaller scales, the fundamental observation stands: smaller models benefit less from thinking because they have less internal knowledge to compose during reasoning.

**Snell et al.'s crucial qualifier:**
"On problems where a smaller base model attains somewhat non-trivial success rates, test-time compute can be used to outperform a 14x larger model."

For maritime factual questions at 1B scale, the "non-trivial success rate" condition may not be met. If the base model has ~5% accuracy on specific SOLAS regulations, TTC might push it to ~10-15%. But a 3B model with 40% base accuracy doesn't need TTC to outperform this.

**Score justification:** 3/10 — impressive results at 32B+ scale, but minimal evidence at 1-3B scale for knowledge-intensive tasks. The user's key claim about s1 at 1B is factually incorrect. Qwen3's small models have thinking mode but benchmark scores reflect limited capacity. No evidence exists for TTC improving domain-specific factual QA at small scale.

---

## FINAL SCORING SUMMARY

| Criterion | Score | Weight | Rationale |
|---|:---:|:---:|---|
| 1. Knowledge Retention | 3/10 | Critical | TTC adds ZERO knowledge to the model. It amplifies reasoning over existing knowledge but cannot compensate for facts never learned. A 1B model has fundamentally less knowledge capacity than a 3B model. |
| 2. Inference Cost | 3/10 | Important | TTC BY DEFINITION increases inference cost — more tokens, more time, more battery. On mobile ARM CPU, CoT adds 10-20s per query. Self-consistency/ToT are impractical (minutes per query). |
| 3. Training Cost | 9/10 | Critical | Extremely cheap. s1 used 1,000 examples. Budget forcing is free (inference trick). Qwen3 thinking mode ships pre-built. $0-$500 for the reasoning component. |
| 4. Data Efficiency | 8/10 | Critical | 1,000 reasoning traces suffice (s1 proved this). Budget forcing needs zero data. But this efficiency applies to REASONING patterns, not domain KNOWLEDGE — maritime facts still need CPT/SFT. |
| 5. Accuracy on Domain QA | 4/10 | Critical | ~55% of maritime questions are pure factual recall where TTC provides ZERO benefit. ~20% are reasoning-heavy where TTC helps significantly. Weighted improvement: ~7-8%. Cannot overcome 1B model's knowledge limitations. |
| 6. Mobile Deployability | 5/10 | Important | Model is small (0.8 GB RAM) — great for mobile. But extended inference (15-60s) degrades UX. Only simple CoT is practical on mobile. Self-consistency and ToT are infeasible on ARM CPU. |
| 7. Robustness | 6/10 | Important | Self-correction during thinking improves reliability. But overthinking, error propagation, and hallucination amplification introduce new failure modes. Net: modestly positive. |
| 8. Catastrophic Forgetting | 8/10 | Important | TTC training is too lightweight to cause forgetting (~1K examples). Budget forcing and self-consistency are inference-only (zero forgetting risk). |
| 9. Maintenance | 8/10 | Moderate | Reasoning patterns are domain-agnostic and don't expire. When regulations update, only the underlying knowledge needs updating — TTC layer carries over unchanged. |
| 10. Proven at Small Scale | 3/10 | Critical | s1 used 32B, NOT 1B. Impressive results above 10B but thin evidence at 1-3B. Original CoT paper found minimal benefit below 10B. No evidence of TTC improving domain-specific factual QA at small scale. |

---

## TOTAL SCORE: 57/100

---

## KEY STRENGTHS (3)

### Strength 1: Nearly Zero Training Cost — The Cheapest Enhancement Available

Test-time compute scaling is spectacularly cheap to implement:
- **s1-style SFT:** 1,000 reasoning traces, single GPU, hours of training, ~$10-$50
- **Budget forcing:** Zero training. Append "Wait" tokens at inference. Cost: $0
- **Self-consistency:** Zero training. Run model N times, vote. Cost: $0
- **Qwen3 thinking mode:** Ships pre-built in the model. Cost: $0

Compare this to any knowledge injection method:
- CPT: $50-$500 and hours-days of GPU time
- SFT: $10-$100 and hours of GPU time
- From-scratch: $100K-$300K and weeks of multi-GPU time

TTC can be added ON TOP of any knowledge-injected model for nearly free. It's not an alternative to CPT/SFT — it's a complement that costs almost nothing to add.

The s1K finding is remarkable: from 50 million possible training examples, 1,000 well-chosen reasoning traces (selected by difficulty, diversity, and quality criteria) produced a model that exceeded o1-preview on math. This level of data efficiency is unmatched by any other training approach.

### Strength 2: Self-Correction Capability — The Model Catches Its Own Errors

Budget forcing's mechanism is genuinely powerful for a safety-critical maritime domain:

```
WITHOUT BUDGET FORCING:
User: "What is the SOLAS requirement for fire pumps on a 4000 GT cargo vessel?"
Model: "Under SOLAS, two fire pumps are required."  ← may be wrong, no self-check

WITH BUDGET FORCING:
User: "What is the SOLAS requirement for fire pumps on a 4000 GT cargo vessel?"
Model (thinking): "SOLAS Chapter II-2... fire pumps... for cargo vessels above 
1000 GT, at least two independently driven fire pumps. Wait, let me verify — 
is it two or three for vessels above 4000 GT? I recall that vessels above 
certain tonnage may need an emergency fire pump in addition... Actually, for 
4000 GT cargo vessels, two main fire pumps are required, each capable of 
delivering the required flow simultaneously."
Model (answer): "Under SOLAS Chapter II-2, a 4000 GT cargo vessel requires 
two independently driven fire pumps."
```

The "Wait" mechanism forces the model to pause and reconsider — catching errors that a single forward pass would miss. For maritime safety information where incorrect answers could contribute to dangerous situations, this self-verification behavior is valuable.

**o1's safety evidence supports this:** Challenging jailbreak resistance jumped from 71.4% (GPT-4o) to 93.4% (o1) — the model's ability to REASON about safety rules is more robust than pattern-matching them.

### Strength 3: Decoupled from Knowledge Injection — Works as a Universal Enhancer

TTC is not a standalone approach — it's a multiplier that enhances whatever base approach you use:

```
Base Model Accuracy × TTC Enhancement = Final Accuracy

1B + CPT (50% maritime QA) × TTC (+8%) = 54% maritime QA
1B + CPT + SFT (60% maritime QA) × TTC (+8%) = 65% maritime QA  
3B + CPT + SFT (70% maritime QA) × TTC (+8%) = 76% maritime QA
```

This universality means:
- TTC doesn't conflict with any other approach
- You lose nothing by adding it
- It can be toggled on/off per query (Qwen3's thinking budget mechanism)
- Maintenance is independent — update knowledge through CPT/SFT, TTC continues working
- No catastrophic forgetting risk from combining it with other methods

---

## KEY WEAKNESSES (3)

### Weakness 1: Cannot Compensate for Missing Knowledge — The Fundamental Category Error

The premise "a 1B model that thinks longer can beat a 3B model that answers instantly" commits a fundamental category error by confusing REASONING with KNOWLEDGE.

**The math competition results that inspired TTC scaling are misleading for factual QA:**

| Task | Nature | Why TTC Helps |
|---|---|---|
| AIME (math competition) | Pure REASONING over known axioms | Model knows math rules, TTC helps apply them correctly |
| Game of 24 | SEARCH over known arithmetic | Model knows four operations, TTC explores combinations |
| Coding (Codeforces) | REASONING + SEARCH over known syntax | Model knows Python/C++, TTC plans algorithms |
| **Maritime QA** | **Mostly FACTUAL RECALL** | **Model either knows the fact or doesn't — thinking can't help** |

You cannot think your way to knowing the MARPOL Annex I discharge requirement of 15 ppm oil content. Either that fact is in the model's weights or it isn't. A 1B model has ~3x fewer parameters to store facts than a 3B model — this is a hard physical limit that no amount of test-time compute overcomes.

**Snell et al. explicitly state this qualifier:** TTC works when the small model has "non-trivial success rates." For specific maritime regulatory facts at 1B scale, success rates may be near zero, making TTC worthless for those questions.

**The user's claim about s1 is factually wrong:** s1 used a 32B base model, not 1B. At 32B, the model has massive knowledge capacity — budget forcing helps it USE that knowledge better. At 1B, the knowledge simply isn't there to be used better.

### Weakness 2: Inference Cost Penalty is Particularly Hostile to Mobile Deployment

TTC converts a fast, single-pass inference into a slow, extended generation. This hits mobile phones hardest:

**Battery arithmetic:**
- iPhone 15 battery: ~3,349 mAh
- Neural engine power: ~1-5W during inference
- A 1B model at 30 tok/s with simple CoT (~500 tokens): ~17 seconds
- 50 questions per study session: 50 × 17s = ~14 minutes of continuous neural engine activity
- Battery drain per session: ~0.4-2% of battery (CoT) vs ~0.15-0.7% (no CoT)

This seems small, but consider:
- Self-consistency (N=5): 5x the battery drain = ~2-10% per study session
- A marine engineer using the chatbot throughout an 8-hour watch: significant cumulative drain
- Older devices with degraded batteries: the drain percentage is worse
- Hot engine rooms: battery performs worse in heat, reducing available capacity further

**UX impact:**
The maritime user asks: "What's the minimum rest hour requirement under STCW?" This is a 5-second answer. With CoT, the model thinks for 20 seconds about STCW rest requirements, regulation history, and exceptions before giving the same answer. The thinking adds latency with ZERO accuracy improvement for this factual question.

**Qwen3's thinking budget partially addresses this** by routing simple factual questions to non-thinking mode. But the routing must be accurate — if the model incorrectly classifies a factual question as complex and triggers thinking mode, every query suffers unnecessary delay.

### Weakness 3: Not Proven at Small Scale — The Evidence is for 32B+, Not 1B

Every headline result for TTC scaling comes from large models:

| Achievement | Model Size | 1B Equivalent Evidence |
|---|---|---|
| s1 exceeds o1-preview on AIME | 32B | ❌ Not tested at 1B |
| o1 achieves 74% on AIME 2024 | ~200B (est.) | ❌ Not available at 1B |
| DeepSeek-R1 surpasses human PhD on GPQA | 671B MoE | ❌ Distilled 1.5B far below R1 |
| ToT achieves 74% on Game of 24 | GPT-4 (~1T est.) | ❌ Not tested at 1B |
| Self-consistency +17.9% on GSM8K | PaLM-540B | ❌ Gains much smaller at 1B |

**The original Chain-of-Thought paper (Wei et al., 2022) explicitly found:**
- CoT shows flat or negative effects below ~10B parameters
- The reasoning capability EMERGES at scale — it's not present at small scale

While Qwen3 (0.6B, 1.7B) and R1-distilled models have partially addressed this through explicit training for reasoning patterns, the improvements are modest compared to large-scale results:

- Qwen3-0.6B with thinking mode: dramatically worse than Qwen3-8B
- R1-distilled-Qwen-1.5B: improved over base but nowhere near R1 quality
- No published benchmark shows 1B + TTC outperforming 3B direct on factual QA

**The uncomfortable truth:** TTC scaling might even HURT at 1B scale. If the model's internal representations are too coarse to support multi-step reasoning (due to limited parameter count), forcing it to think longer doesn't produce better answers — it produces longer wrong answers. A 1B model "thinking" about SOLAS regulations it barely knows may generate plausible-sounding but incorrect reasoning chains, giving the user FALSE CONFIDENCE in wrong answers.

---

## VERDICT

**Test-time compute scaling scores 57/100 — a powerful inference enhancement miscast as a standalone approach for a maritime chatbot.**

TTC is one of the most exciting AI developments of 2024-2025. The results on math, coding, and reasoning benchmarks are extraordinary. But applying TTC to a maritime factual chatbot on mobile commits three fundamental mismatches:

1. **Knowledge vs. Reasoning mismatch:** Maritime QA is ~55% factual recall where TTC provides zero benefit. TTC shines on reasoning tasks (math, coding, logic), not knowledge-intensive factual QA.

2. **Scale mismatch:** All impressive TTC results use models ≥32B. At 1-3B, the evidence is thin, and the original CoT research suggests minimal benefit below 10B parameters.

3. **Platform mismatch:** TTC trades compute time for accuracy. On mobile phones (limited compute, limited battery, latency-sensitive UX), this trade-off is particularly unfavorable. Only simple CoT is practical on mobile.

**The physics analogy:** TTC is like giving an engineer more TIME on an exam. If the engineer KNOWS the material but rushes, more time helps enormously (fixing calculation errors, double-checking, trying alternative approaches). But if the engineer NEVER STUDIED the material, more time just means staring at the page longer. A 1B model without maritime training is the engineer who never studied — all the time in the world won't help.

**TTC's correct role in our pipeline:** It's a cheap, effective LAST MILE enhancement, not a foundational approach:

```
WRONG:  "Use TTC instead of a bigger model or CPT"
RIGHT:  "Use CPT + SFT to inject maritime knowledge, THEN add TTC as a bonus"
```

---

## BEST COMBINATION: TTC as Enhancement Layer, Not Foundation

```
RECOMMENDED: TTC as the final layer of a knowledge-first pipeline

STEP 1: SELECT BASE MODEL (cost: $0)
    │   Qwen3-1.7B (has built-in thinking/non-thinking mode)
    │   OR Qwen2.5-1.5B (need external TTC training)
    │   
    │   Qwen3 PREFERRED because thinking mode is already built in,
    │   including thinking budget mechanism for adaptive compute
    │
    ▼
STEP 2: INJECT MARITIME KNOWLEDGE via CPT (cost: $50-$500)
    │   This is where the KNOWLEDGE enters the weights.
    │   TTC cannot skip this step. No amount of thinking
    │   compensates for missing domain knowledge.
    │   
    │   CPT on maritime corpus: ~500M-2B tokens
    │   Result: model with maritime knowledge in weights
    │
    ▼
STEP 3: FINE-TUNE FOR MARITIME Q&A via SFT (cost: $10-$100)
    │   Maritime instruction pairs: ~10K-50K examples
    │   Include reasoning-style examples (step-by-step explanations)
    │   
    │   If using Qwen2.5 base: add ~1K reasoning traces (s1-style)
    │   If using Qwen3 base: thinking mode already present
    │
    ▼
STEP 4: ADD TTC ENHANCEMENT LAYER (cost: $0-$50)
    │   
    │   For Qwen3-1.7B:
    │   ├── Configure thinking budget: adaptive per query
    │   ├── Simple factual questions → non-thinking mode (fast)
    │   ├── Reasoning questions → thinking mode (slower but better)  
    │   └── Cost: $0 (already built in)
    │   
    │   For Qwen2.5-1.5B:
    │   ├── Apply budget forcing at inference time
    │   ├── Add "Let's think step by step" to complex queries
    │   └── Cost: $0 (inference trick)
    │
    ▼
STEP 5: QUANTIZE & DEPLOY (cost: $0)
    │   Q4_K_M for mobile: ~1.0 GB for 1.7B model
    │   Mobile framework: llama.cpp or MLC-LLM
    │
    ▼
DEPLOYED BEHAVIOR:

    User: "What does MARPOL stand for?"
    → Non-thinking mode: "MARPOL stands for the International 
       Convention for the Prevention of Pollution from Ships."
    → Time: 2-3 seconds ✅

    User: "If turbocharger RPM drops and exhaust temp rises 
           simultaneously, what could be wrong?"
    → Thinking mode: [thinks for 10-15 seconds about turbocharger
       mechanics, exhaust system, possible causes, checks reasoning]
    → Answer: "This combination suggests fouling of the turbine 
       side. The reduced RPM means less air compression, while 
       higher exhaust temp indicates incomplete expansion..."
    → Time: 15-20 seconds ✅ (acceptable for complex question)

TOTAL PIPELINE COST: $60-$650
RESULT: Maritime knowledge (from CPT/SFT) +
        Enhanced reasoning on complex questions (from TTC) +
        Fast answers on simple questions (from adaptive thinking) +
        Self-correction capability on safety-critical answers
```

### Why This Combination Works

1. **Knowledge comes from CPT** (not TTC) — this is non-negotiable
2. **Reasoning enhancement comes from TTC** — cheap and effective for the 20% of questions that benefit
3. **Adaptive compute comes from thinking budget** — simple questions are fast, complex ones are slow-but-better
4. **Self-correction comes from budget forcing** — valuable for safety-critical maritime answers
5. **Cost is minimal** — TTC adds $0-$50 to the CPT+SFT pipeline

### What TTC Should NOT Be Used For

- ❌ Replacing a larger model (3B) with a smaller one (1B) — the knowledge gap is real
- ❌ Replacing CPT/SFT for knowledge injection — TTC adds zero knowledge
- ❌ Self-consistency or Tree of Thought on mobile — too slow
- ❌ Extended budget forcing (>30s thinking) on mobile — poor UX
- ❌ Expecting TTC to compensate for inadequate training

---

## ANSWERING THE KEY QUESTION

> **Can test-time compute compensate for a smaller model? Can a 1B model with 30s of thinking beat a 3B model with instant answer, for FACTUAL maritime questions?**

**NO, for the majority of maritime questions.**

For **factual recall** (~55% of maritime QA): A 1B model with 30 seconds of thinking will NOT beat a 3B model that answers instantly. The 3B model has 3x more parameters storing 3x more factual knowledge. No amount of thinking creates knowledge that doesn't exist in the weights.

For **reasoning over known facts** (~20% of maritime QA): A 1B model with thinking CAN match or beat a 3B model that answers instantly, IF both models know the relevant facts. The 1B model's step-by-step reasoning compensates for its weaker single-pass reasoning capacity.

For **complex multi-step problems** (~5% of maritime QA): A 1B model with extended thinking CAN beat a 3B model's instant answer, as systematic decomposition and self-checking genuinely outperforms reflexive answering on complex tasks.

**Overall weighted verdict:** A 1B model + TTC beats a 3B model on ~15-20% of maritime questions, ties on ~10-15%, and loses on ~65-75%. For a maritime chatbot, the 3B model with no TTC is the better choice. The BEST choice is a knowledge-injected model (CPT+SFT) of whatever size fits on the phone, WITH TTC as a cheap enhancement layer.

**Bottom line:** Test-time compute scaling is a spectacular technique for reasoning-heavy tasks but a poor fit as a standalone approach for a factual maritime chatbot on mobile. Use it as an enhancement layer on top of a knowledge-injected model, not as a substitute for knowledge injection. The user's premise that "a 1B model that thinks for 30 seconds can outperform a 3B model that answers instantly" is approximately correct for math and coding, but incorrect for factual domain QA where knowledge — not reasoning — is the bottleneck.
