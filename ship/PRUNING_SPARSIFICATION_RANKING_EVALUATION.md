# RANKING EVALUATION: Pruning + Sparsification (Deriving Small Models from Larger Pruned Models)

**Approach Under Evaluation:** Take a larger, more knowledgeable model (7B-13B) and systematically remove unnecessary weights, neurons, attention heads, or entire layers to produce a model small enough for mobile deployment (1-3B effective parameters). The hypothesis: a 7B model pruned to 3B-equivalent retains more knowledge than a natively 3B model because it inherits the larger model's richer weight representations. Techniques include unstructured pruning (SparseGPT, Wanda), structured pruning (Sheared LLaMA, Minitron), layer pruning (ShortGPT), width pruning (SliceGPT), and hybrid pruning + distillation pipelines.

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B effective parameters (must fit ≤2GB on mobile)  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH SOURCES ANALYZED

| Paper / Resource | Key Finding for This Evaluation |
|---|---|
| **SparseGPT — "Massive Language Models Can Be Accurately Pruned in One-Shot"** (Frantar & Alistarh, 2023; arXiv:2301.00774) | First demonstration that GPT-family models can be pruned to 50-60% unstructured sparsity in one-shot, without retraining, at minimal perplexity increase. Run on OPT-175B and BLOOM-176B in under 4.5 hours. Over 100 billion weights removed with negligible accuracy loss. Compatible with 2:4 semi-structured patterns and weight quantization. **CRITICAL LIMITATION: "minimal perplexity increase" is measured on GENERAL text. Perplexity is an AVERAGE metric — rare domain-specific tokens (maritime terminology, regulation numbers) can be disproportionately degraded. Also: unstructured sparsity requires sparse compute kernels that DO NOT EXIST on ARM mobile CPUs.** |
| **Wanda — "A Simple and Effective Pruning Approach for Large Language Models"** (Sun, Liu, Bair, Kolter, 2023; arXiv:2306.11695; ICLR 2024) | Prunes by weight magnitude × corresponding input activation, per output basis. No retraining or weight update needed. Significantly outperforms magnitude pruning alone, competitive with SparseGPT despite being much simpler. **Key advantage: zero retraining cost. Key disadvantage (same as SparseGPT): produces unstructured sparsity that doesn't accelerate inference on mobile ARM hardware. Also: importance scoring driven by CALIBRATION DATA — if calibration excludes maritime text, maritime-relevant weights face higher pruning risk.** |
| **ShortGPT — "The Unreasonable Ineffectiveness of the Deeper Layers"** (Gromov, Tirumala et al., 2024; arXiv:2403.17887; ICLR) | Discovers that up to HALF of transformer layers can be removed with minimal benchmark degradation, implying deep layers are underutilized by current pretraining. Uses layer similarity analysis + QLoRA healing. Each experiment fits on a single 40GB A100. **THE MOST PROVOCATIVE FINDING for our use case: if 50% of layers are "ineffective," removing them gives roughly a 2x size reduction for free. A 7B model (32 layers) pruned to 16 layers ≈ 3.5B effective parameters. But: the paper notes "shallow layers play a critical role in STORING KNOWLEDGE." Removing deep layers keeps knowledge but degrades REASONING — exactly the wrong trade-off for a chatbot that needs to compose answers from stored maritime facts.** |
| **LLM-Pruner — "On the Structural Pruning of Large Language Models"** (Ma, Fang, Wang, 2023; arXiv:2305.11627; NeurIPS 2023) | Task-agnostic structural pruning using gradient-based importance. Removes non-critical coupled structures. Performance recovered via LoRA tuning in 3 hours on 50K data. Tested on LLaMA, Vicuna, ChatGLM. **Key contribution: preserves multi-task ability after pruning. But: 50K recovery samples are GENERAL — domain-specific knowledge recovery is not addressed. Also: LoRA recovery has the same rank limitation documented in "LoRA Learns Less and Forgets Less" — insufficient for deep knowledge retention.** |
| **Sheared LLaMA — "Accelerating Language Model Pre-training via Structured Pruning"** (Xia, Gao, Zeng, Chen, 2023; arXiv:2310.06694) | **THE MOST RELEVANT PAPER.** Prunes LLaMA2-7B down to 1.3B and 2.7B parameter models. End-to-end targeted structured pruning: removes layers, heads, intermediate and hidden dimensions to a specified target shape. Uses dynamic batch loading to balance domain losses during continued training. Sheared-LLaMA outperforms Pythia, INCITE, OpenLLaMA, and TinyLlama at equivalent sizes. **Requires only 3% of compute compared to from-scratch training. But: the comparison baselines are 2023-era small models. Modern native 3B models (SmolLM3 trained on 11T tokens, Qwen2.5-3B trained on 18T tokens) are VASTLY stronger baselines that Sheared LLaMA was never compared against.** |
| **Minitron — "Compact Language Models via Pruning and Knowledge Distillation"** (Muralidharan et al., NVIDIA, 2024; arXiv:2407.14679) | **THE STRONGEST EMPIRICAL EVIDENCE.** Prunes Nemotron-4 15B → 8B and 4B using combined depth, width, attention, and MLP pruning + knowledge distillation retraining. Requires only <3% original training data and up to 40x fewer tokens per model. **Pruned 8B model achieves up to 16% MMLU improvement over training from scratch.** Comparable to Mistral 7B, Gemma 7B, Llama-3 8B. **Critical nuance: 16% improvement is vs. from-scratch with EQUIVALENT compute. If the from-scratch model had unlimited compute (like Qwen2.5 or SmolLM3), the advantage disappears. Also: pruning 15B→4B is a 3.75x compression — ambitious. The 15B source had rich knowledge because it was trained on massive data. Pruning PRESERVES that knowledge more efficiently than re-learning it, but it cannot EXCEED what the source model knew.** |
| **SliceGPT — "Compress Large Language Models by Deleting Rows and Columns"** (Ashkboos et al., 2024; arXiv:2401.15024; ICLR 2024) | Post-training sparsification by replacing weight matrices with smaller dense matrices. Reduces embedding dimension. On LLaMA2-70B: removes 25% parameters while maintaining 99% zero-shot performance. On Phi-2: 90% performance at 25% reduction. **Key insight: "computational invariance" in transformers. But: 25% parameter reduction = modest compression. A 7B → 5.25B model is still too large for mobile. You'd need to combine with quantization AND further pruning. At 25% slice + Q4 quantization, a 7B would be ~2.6GB — still tight on mobile. And Phi-2 (2.7B) lost 10% performance at only 25% pruning — domain-specific QA would degrade more.** |
| **BitNet b1.58** (Ma, Wang et al., 2024; arXiv:2402.17764) | Ternary weight models can match FP16 quality when trained from scratch. **Tangentially relevant: BitNet is "extreme pruning" in spirit (most of the weight space is eliminated). But it requires training from scratch — see PRETRAINING_FROM_SCRATCH_RANKING_EVALUATION.md for why this is prohibitive for maritime data.** |
| **LoRA Learns Less and Forgets Less** (Biderman et al., 2024; arXiv:2405.09673) | LoRA substantially underperforms full fine-tuning for new knowledge acquisition. Full FT learns perturbations with rank 10-100x greater than typical LoRA. **Directly relevant: most pruning methods use LoRA for post-pruning "healing." LLM-Pruner, ShortGPT, and others rely on LoRA recovery. If LoRA cannot adequately restore pruned knowledge, the recovery step is fundamentally limited.** |
| **Phi-3 Technical Report** (Abdin et al., 2024; arXiv:2404.14219) | 3.8B model trained on 3.3T tokens. Runs on phone. **"The model simply does not have the capacity to store too much factual knowledge."** This admission from Microsoft applies equally to pruned models — a 3B model has the same capacity limitations whether it was pruned from 7B or trained natively. |
| **llama.cpp / GGUF Ecosystem** (Gerganov et al., 2023-present) | The standard mobile inference framework. **Supports quantization (Q4_K_M etc.) but has NO support for sparse matrix operations.** A 50% sparse 7B model runs at the SAME speed and uses the SAME memory as a dense 7B model in llama.cpp. The zeros are stored and computed just like any other weight value. Only GGUF quantization (not sparsity) reduces mobile footprint. |

---

## THE FUNDAMENTAL QUESTION THIS EVALUATION MUST ANSWER

**Does pruning a 7B model to 3B-equivalent give better maritime QA than fine-tuning a native 3B model?**

### The Answer: Almost Certainly No — And the Reason Exposes the Approach's Category Error

The pruning hypothesis rests on a seductive but flawed chain of logic:

```
THE PRUNING HYPOTHESIS:

    PREMISE 1: A 7B model knows more than a 3B model
    PREMISE 2: Pruning removes "unnecessary" weights while preserving knowledge
    PREMISE 3: Therefore, 7B pruned to 3B > native 3B 
    
    Applied to maritime:
    PREMISE 4: A 7B model has more maritime knowledge than a 3B model
    PREMISE 5: Pruning preserves that maritime knowledge
    CONCLUSION: Pruned-7B-to-3B maritime chatbot > native 3B maritime chatbot
```

**Premises 1-2 have empirical support. Premises 4-5 are where it collapses:**

```
┌────────────────────────────────────────────────────────────────────────┐
│     WHY PRUNING FAILS FOR DOMAIN-SPECIFIC KNOWLEDGE ON MOBILE         │
│                                                                        │
│  PROBLEM 1: THE SOURCE MODEL HAS NO MARITIME KNOWLEDGE TO PRESERVE    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │  What does a general 7B model (Llama-2-7B, Mistral-7B) know     │  │
│  │  about maritime engineering?                                     │  │
│  │                                                                  │  │
│  │  • Basic: "SOLAS is about safety at sea" → YES, from Wikipedia  │  │
│  │  • Moderate: "MARPOL Annex VI covers air pollution" → MAYBE     │  │
│  │  • Specific: "CO2 system test interval per SOLAS FSS Code       │  │
│  │    Chapter 5 is 2 years, with bottles weighed and tested        │  │
│  │    at X bar pressure" → ALMOST CERTAINLY NOT                     │  │
│  │                                                                  │  │
│  │  Maritime content in general pretraining corpora:                │  │
│  │  • Common Crawl: ~0.01% maritime (generous estimate)             │  │
│  │  • Wikipedia: ~500 maritime articles out of 6.7M total           │  │
│  │  • Total maritime exposure: ~0.01% of training data              │  │
│  │                                                                  │  │
│  │  You cannot PRESERVE knowledge the model never HAD.              │  │
│  │  Pruning a 7B model with 0.01% maritime exposure to 3B           │  │
│  │  gives you a 3B model with 0.01% maritime exposure.              │  │
│  │                                                                  │  │
│  │  A native 3B model (Qwen2.5-3B) also has ~0.01% maritime        │  │
│  │  exposure — but was trained on 18T tokens (vs 7B's 2T tokens).  │  │
│  │  0.01% of 18T = 1.8B tokens of maritime-adjacent content.       │  │
│  │  0.01% of 2T = 0.2B tokens.                                     │  │
│  │  The native 3B model has SEEN MORE maritime content.             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  PROBLEM 2: UNSTRUCTURED SPARSITY DOESN'T WORK ON MOBILE             │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │  The pruning literature's flagship results are UNSTRUCTURED:     │  │
│  │  • SparseGPT: 50-60% unstructured sparsity                     │  │
│  │  • Wanda: similar unstructured sparsity                          │  │
│  │  • 2:4 semi-structured: supported only on NVIDIA A100+           │  │
│  │                                                                  │  │
│  │  On mobile ARM CPUs:                                             │  │
│  │  • No hardware sparse matrix multiply units                      │  │
│  │  • No CUDA cores for 2:4 structured sparsity                    │  │
│  │  • llama.cpp: NO sparse inference support                        │  │
│  │  • MLC-LLM: NO sparse inference support                         │  │
│  │  • ExecuTorch: NO unstructured sparse support                    │  │
│  │                                                                  │  │
│  │  A 50% sparse 7B model in GGUF format:                          │  │
│  │  • Still stores 7B weights (zeros occupy same space)             │  │
│  │  • Still requires full 7B matrix multiplications                 │  │
│  │  • Still needs ~4GB RAM at Q4 quantization                       │  │
│  │  • Runs at the SAME speed as a dense 7B                         │  │
│  │                                                                  │  │
│  │  Unstructured sparsity on mobile is                              │  │
│  │  COMPUTATIONALLY MEANINGLESS.                                    │  │
│  │                                                                  │  │
│  │  Only STRUCTURED pruning (removing entire layers/heads/dims)     │  │
│  │  produces a genuinely smaller model that benefits mobile.        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  PROBLEM 3: STRUCTURED PRUNING = JUST MAKING A SMALLER MODEL         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │  When you do structured pruning (Sheared LLaMA, Minitron):      │  │
│  │  • Remove entire layers, attention heads, hidden dimensions      │  │
│  │  • The result is a standard dense transformer                    │  │
│  │  • No special runtime needed — runs on any framework             │  │
│  │                                                                  │  │
│  │  But this means structured pruning is just a METHOD FOR          │  │
│  │  PRODUCING a smaller model. The output IS a 3B model.            │  │
│  │  It's NOT a "compressed 7B" in any operational sense.            │  │
│  │                                                                  │  │
│  │  The question then becomes:                                      │  │
│  │  "Is a 3B model DERIVED from 7B better than a 3B model          │  │
│  │   trained natively?"                                             │  │
│  │                                                                  │  │
│  │  In 2023 (Sheared LLaMA): YES — native 3B models were weak      │  │
│  │  In 2024 (Minitron): MAYBE — native models catching up          │  │
│  │  In 2026 (today): LIKELY NO — SmolLM3 (11T tokens), Qwen2.5-3B │  │
│  │  (18T tokens), Phi-3 (3.3T tokens) are all trained with far     │  │
│  │  more data than the source models pruning papers used.           │  │
│  │                                                                  │  │
│  │  Sheared LLaMA pruned from LLaMA2-7B (2T tokens)               │  │
│  │  → Beaten by SmolLM3-3B (11T tokens) trained natively           │  │
│  │                                                                  │  │
│  │  The pruning advantage was a TEMPORAL artifact of weak            │  │
│  │  small models in 2023. It has been superseded by better          │  │
│  │  native small model training recipes.                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  PROBLEM 4: PRUNING IS A DEPLOYMENT TECHNIQUE, NOT A                  │
│             KNOWLEDGE INJECTION TECHNIQUE                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                                                                  │  │
│  │  Pruning REMOVES information. By definition.                     │  │
│  │  • Unstructured: zeros out individual weights                    │  │
│  │  • Structured: removes entire compute blocks                     │  │
│  │  • Layer pruning: removes entire layers                          │  │
│  │                                                                  │  │
│  │  Pruning does NOT:                                               │  │
│  │  • Add maritime knowledge                                        │  │
│  │  • Improve domain-specific accuracy                              │  │
│  │  • Teach new facts or procedures                                 │  │
│  │  • Create new associations between concepts                      │  │
│  │                                                                  │  │
│  │  Our maritime chatbot's PRIMARY challenge is:                    │  │
│  │  "How to inject maritime knowledge into model weights"           │  │
│  │                                                                  │  │
│  │  Pruning does not address this challenge AT ALL.                 │  │
│  │  It addresses a different challenge:                              │  │
│  │  "How to make a large model fit on constrained hardware"         │  │
│  │                                                                  │  │
│  │  We already have a solution for hardware constraints:             │  │
│  │  Q4 quantization of a native 3B model → ~1.8GB → fits on phone  │  │
│  │                                                                  │  │
│  │  Pruning solves a SOLVED problem while ignoring the              │  │
│  │  UNSOLVED problem (knowledge injection).                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

### The Minitron Counter-Argument — And Why It Doesn't Apply Here

Minitron is the strongest evidence for pruning. NVIDIA pruned Nemotron-4 15B → 8B and 4B, achieving up to 16% MMLU improvement over training from scratch at equivalent compute. This is a real, significant result.

**But the Minitron result has critical caveats for our use case:**

| Minitron's Context | Our Context |
|---|---|
| Source: Nemotron-4 15B (proprietary, NVIDIA-scale pretraining) | Source: any open 7B model (LLaMA2, Mistral, Qwen) |
| Target: general-purpose LLM (MMLU, reasoning, etc.) | Target: maritime domain-specific chatbot |
| Baseline: from-scratch training with EQUIVALENT compute budget | Baseline: SOTA native 3B models trained on 11-18T tokens |
| Retraining: <3% of original data = still billions of tokens | Retraining: requires maritime data we don't have in the source |
| Hardware: datacenter GPUs (where sparse ops are accelerated) | Hardware: ARM CPUs (no sparse acceleration) |
| Knowledge: retained from 15B's massive pretraining | Knowledge: 7B source has minimal maritime knowledge |

**The 16% MMLU improvement was vs. a from-scratch model with the SAME COMPUTE BUDGET.** If you give the from-scratch model MORE compute (as modern SOTA small models have — SmolLM3 used 384 H100s × 24 days, far more than Minitron's retraining budget), the gap closes or reverses.

**Minitron's lesson is about EFFICIENCY, not QUALITY:** "If you already have a large pretrained model and want a smaller one QUICKLY, pruning + distillation is more COST-EFFECTIVE than training from scratch." This is true. But for domain-specific maritime knowledge, the source model doesn't have the knowledge we need, and the efficiency gain doesn't help.

### What Would Actually Work: CPT on 7B → Prune to 3B?

The one scenario where pruning could genuinely help:

```
HYPOTHETICAL PIPELINE:
    Step 1: Take Qwen2.5-7B (18T tokens pretraining, rich general knowledge)
    Step 2: CPT on maritime data (500M-2B tokens, $500-2,000)
    Step 3: Now you have a 7B model WITH maritime knowledge
    Step 4: Structured prune to 3B (Minitron/Sheared-LLaMA style, $500-2,000)
    Step 5: Distill knowledge from maritime-7B teacher to pruned-3B student
    Step 6: Quantize to Q4_K_M → ~1.8GB → deploy on phone
    
    TOTAL COST: $1,000-$4,000 + significant engineering complexity
    TIME: 1-2 weeks
    RESULT: A 3B model that inherits from a maritime-trained 7B model
```

**Compare to the simpler alternative:**

```
SIMPLER PIPELINE:
    Step 1: Take Qwen2.5-3B (18T tokens pretraining)
    Step 2: CPT on maritime data (500M-2B tokens, $50-500)
    Step 3: SFT + alignment ($50-200)
    Step 4: Quantize to Q4_K_M → ~1.8GB → deploy on phone
    
    TOTAL COST: $100-$700
    TIME: 2-3 days
    RESULT: A 3B model with maritime knowledge directly injected
```

**The pruning pipeline costs 3-10x more and takes 3-5x longer.** The marginal benefit (starting from a 7B maritime model vs. a 3B maritime model) is UNCERTAIN. The 7B model has more capacity to absorb maritime CPT, but after pruning to 3B, much of that extra capacity is lost. You're paying to fill a larger bucket and then pouring half of it out.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. Knowledge Retention — Score: 4/10

**The core question:** Does a pruned model retain maritime knowledge better than alternatives?

**Answer: No, because there's no maritime knowledge to retain in the first place.**

A general 7B model (LLaMA-2-7B, Mistral-7B, Qwen2.5-7B) has approximately the same maritime knowledge as a general 3B model — near zero for specific technical details. Maritime content constitutes approximately 0.01% of web pretraining data. Pruning this 7B model to 3B preserves whatever GENERAL knowledge survives the pruning process, but cannot manufacture maritime-specific knowledge that was never learned.

**What pruning research shows about knowledge retention during compression:**

- **SparseGPT at 50% sparsity:** Perplexity on WikiText-2 increases negligibly (e.g., from 5.68 to 5.87 for OPT-175B). But perplexity is a MEAN metric. Rare tokens — the kind that encode specific domain facts like "SOLAS FSS Code Chapter 5" — are disproportionately affected by pruning because their associated weight patterns are statistically less frequent and more likely to be classified as "unnecessary."

- **ShortGPT layer pruning:** Removing 25-50% of layers keeps MMLU roughly stable but degrades complex reasoning. Maritime QA requires compositional reasoning: "Under MARPOL Annex VI, what emission limits apply in Emission Control Areas for vessels built after 2016 with engines above 130 kW using marine diesel oil?" This requires combining knowledge from multiple regulatory sources — exactly the kind of multi-step reasoning that degrades with layer pruning.

- **Minitron 15B→4B:** 16% MMLU improvement over from-scratch at equivalent compute. But MMLU tests BROAD general knowledge. Maritime QA tests NARROW specific knowledge, which may sit in the "pruned away" portions of the weight space.

- **Sheared LLaMA 7B→2.7B:** Outperformed 2023-era 2.7B models. But: (a) LLaMA2-7B itself has minimal maritime knowledge, and (b) modern Qwen2.5-3B trained on 9x more data has surpassed Sheared LLaMA's general quality.

**The calibration set problem:** SparseGPT and Wanda compute importance scores based on a calibration dataset (typically 128 samples from C4 or WikiText). Maritime-relevant weights — the ones encoding associations between "SOLAS," "fire safety," "CO2 system," "2-year interval" — are evaluated for importance based on GENERAL text patterns. If a weight is critical for recalling fire suppression test procedures but unimportant for predicting the next word in a Wikipedia article, it will be pruned.

**The only way pruning helps retention:** If you first inject maritime knowledge into a 7B model via CPT, THEN prune with a maritime calibration set, you could preferentially preserve maritime-relevant weights. But this is a CPT+pruning pipeline where CPT does the actual knowledge injection work, and pruning is just a compression step.

**SCORE: 4/10** — Pruning cannot retain knowledge the model doesn't have. For a general-purpose 7B model → 3B prune, maritime knowledge retention is no better than a native 3B model. With maritime CPT before pruning, retention improves, but then CPT is doing the heavy lifting and pruning adds cost and complexity.

---

### 2. Inference Cost — Score: 7/10

**This is where pruning's promises and mobile reality diverge sharply.**

**Unstructured sparsity (SparseGPT, Wanda):**
- Produces sparse weight matrices where 50-60% of values are zero
- On NVIDIA GPUs with sparse tensor cores: 1.5-2x speedup
- On ARM CPUs: **ZERO speedup.** The standard GEMM (general matrix multiply) kernels in llama.cpp, MLC-LLM, and ExecuTorch do not skip zero-valued weights. Every multiplication is executed, zero or not.
- Memory footprint: UNCHANGED unless using a sparse storage format (CSR/CSC), which adds indexing overhead and is not supported by mobile inference frameworks
- **Result: A 50% sparse 7B model on mobile = a dense 7B model on mobile. 4GB+ RAM, 3-5 tok/s. TOO SLOW AND TOO LARGE.**

**2:4 Semi-structured sparsity:**
- 2 out of every 4 values must be zero — a constrained pattern
- Hardware acceleration ONLY on NVIDIA A100+ (Ampere architecture and later)
- ARM CPUs: **NO hardware support.** Apple Neural Engine has some acceleration, but not for 2:4 patterns in LLM weight matrices.
- **Dead end for mobile ARM.**

**Structured pruning (Sheared LLaMA, Minitron — the only viable path):**
- Removes entire layers, attention heads, or FFN dimensions
- Produces a standard dense model with fewer parameters
- This model runs identically to ANY dense model of the same size
- No special runtime, no sparse kernels needed
- A structurally-pruned 3B model = a dense 3B model in all operational aspects

**If using structured pruning:**
| Model | Quantization | RAM | Tokens/sec (ARM) | Mobile? |
|-------|-------------|-----|-------------------|---------|
| Pruned 7B → 3B | Q4_K_M | ~1.8 GB | 8-15 | YES |
| Pruned 7B → 2B | Q4_K_M | ~1.2 GB | 12-25 | YES |
| Native 3B | Q4_K_M | ~1.8 GB | 8-15 | YES |
| Sparse 7B (50%) | Q4_K_M | ~4.0 GB | 3-5 | BARELY |

**The 3-point deduction:**
1. The approach's flagship techniques (SparseGPT, Wanda) produce unusable results on mobile
2. Only structured pruning works, and it produces models indistinguishable from native models
3. The pruning literature creates a false expectation of "sparse inference speedup" that doesn't exist on mobile ARM hardware

**SCORE: 7/10** — If you restrict yourself to structured pruning, the resulting dense model has standard inference characteristics. But the approach is misleading: the most-cited pruning methods (SparseGPT, Wanda, 2:4 sparsity) provide ZERO mobile benefit. The score would be 9-10/10 if only structured pruning were considered, but the approach as described fundamentally mismatch mobile inference reality.

---

### 3. Training Cost — Score: 6/10

**Pruning itself is cheap. The total pipeline is moderate.**

**Cost of the pruning step alone:**

| Method | Hardware | Time | Cost |
|--------|----------|------|------|
| SparseGPT on 7B | 1x A100 | 1-2 hours | $3-6 |
| Wanda on 7B | 1x A100 | 10-30 minutes | $1-3 |
| Layer pruning (ShortGPT) | 1x A100 | Minutes + QLoRA healing 2-3 hours | $5-15 |
| SliceGPT on 7B | 1x A100 | 1-2 hours | $3-6 |
| Structured pruning (LLM-Pruner) | 1x A100 | LoRA recovery 3 hours | $10-20 |
| Sheared LLaMA (full pipeline) | GPUs for continued training on 0.4B tokens | Days | $500-2,000 |
| Minitron (full pipeline) | GPUs for distillation retraining | Days-weeks | $1,000-10,000 |

**But pruning alone doesn't give us a maritime chatbot.** The total pipeline must include maritime knowledge injection:

```
PIPELINE A: Prune first, then fine-tune
  Prune 7B → 3B (SparseGPT or structured): $5-2,000
  CPT pruned model on maritime data: $50-500
  SFT on maritime Q&A: $10-100
  TOTAL: $65-$2,600

PIPELINE B: Fine-tune first, then prune  
  CPT 7B model on maritime data: $500-2,000 (more expensive than 3B CPT)
  Prune maritime-7B → 3B: $5-2,000
  Recovery/healing fine-tuning: $50-500
  TOTAL: $555-$4,500

PIPELINE C: Minitron-style (prune + distill from teacher)
  CPT 7B on maritime data: $500-2,000
  Structured prune + distill to 3B: $1,000-5,000
  SFT + alignment: $50-200
  TOTAL: $1,550-$7,200

COMPARE TO SIMPLE ALTERNATIVES:
  CPT on native 3B + SFT: $100-$700
  CPT + SFT + DPO pipeline on 3B: $200-$2,000
```

**The pruning approach costs 2-10x more than direct fine-tuning of a native 3B model**, with no guaranteed quality improvement for domain-specific tasks.

**Why not lower:** The cost is still manageable (hundreds to low thousands of dollars, not $100K+ like from-scratch). The pruning step itself is remarkably cheap. Sheared LLaMA's "3% of from-scratch compute" is a genuine efficiency win for general-purpose model creation.

**Why not higher:** The multi-step pipeline adds engineering time and complexity beyond raw compute cost. You need expertise in both pruning and fine-tuning. The Minitron pipeline requires setting up knowledge distillation infrastructure. Time-to-result is 1-2 weeks vs. 2-3 days for simple CPT+SFT.

**SCORE: 6/10** — Moderate cost. Much cheaper than from-scratch training ($100K+) but 2-10x more expensive than direct CPT+SFT on a native 3B model ($100-$700). The added complexity and engineering time are real costs not captured in GPU hours alone.

---

### 4. Data Efficiency — Score: 6/10

**For the pruning step:** Extremely data-efficient. SparseGPT needs ~128 calibration samples. Wanda needs even less. Layer pruning similarity analysis needs zero training data.

**For recovery/healing:** Moderate data requirements.
- LLM-Pruner: 50K samples for LoRA recovery
- ShortGPT: Small QLoRA fine-tuning set
- Sheared LLaMA: 0.4B tokens for continued training
- Minitron: <3% of original pretraining data (still billions of tokens for a 15B source)

**For maritime knowledge injection:** Pruning contributes NOTHING to data efficiency for domain knowledge. You still need the same maritime data (500M-2B tokens of textbooks, regulations, and synthetic content) whether you're pruning or not.

**The calibration set is CRITICAL and often overlooked:**

SparseGPT and Wanda decide which weights to prune based on their importance as measured against a calibration set. If the calibration set is C4 or WikiText (as in the papers), weights important for maritime knowledge but unimportant for general text prediction will be pruned.

To preserve maritime knowledge during pruning, you'd need maritime-specific calibration data. This requires:
1. Already having clean maritime text (same data needed for CPT)
2. Running the pruning algorithm with domain-specific calibration
3. Potentially running multiple calibration passes to balance domain and general retention

This is feasible but adds a step. The pruning literature rarely discusses domain-specific calibration — it's an open research question whether SparseGPT/Wanda importance metrics even work correctly on domain-specific data.

**SCORE: 6/10** — The pruning step itself is very data-efficient. But for our purpose (maritime chatbot), the data requirements for knowledge injection are identical to any other approach. The calibration set consideration adds a subtle but important complication for domain-specific applications.

---

### 5. Accuracy on Domain QA — Score: 4/10

**This is the approach's critical failure for our specific use case.**

Pruning a general 7B model to 3B gives us a 3B model with GENERAL knowledge. For maritime domain QA, this is no better than — and possibly worse than — a native 3B model:

**Why possibly WORSE than native 3B:**

| Factor | Pruned 7B → 3B | Native 3B (e.g., Qwen2.5-3B) |
|--------|----------------|-------------------------------|
| Training data | Inherited from 7B source (e.g., LLaMA2: 2T tokens) | 18T tokens (Qwen2.5) or 11T tokens (SmolLM3) |
| Architecture | Modified — some layers/heads removed | Purpose-designed for 3B scale |
| Maritime exposure | ~0.2B tokens (0.01% of 2T) | ~1.8B tokens (0.01% of 18T) |
| Optimization | Weights optimized for 7B, then pruned | Weights optimized for 3B architecture directly |
| Quality post-pruning | Degraded from 7B quality by pruning | Trained to maximize 3B quality |

**The math is damning:** A native Qwen2.5-3B model may have been exposed to 9x MORE tokens of incidental maritime content than a LLaMA2-7B model, simply because it was trained on 9x more data. Pruning the LLaMA2-7B removes weights, further degrading whatever maritime traces exist.

**If you CPT on maritime data BEFORE pruning:**

The pipeline becomes: CPT 7B on maritime → Prune to 3B. This COULD outperform native CPT on 3B because:
- The 7B model has more capacity to absorb maritime knowledge during CPT
- More attention heads and layers means richer domain representations
- Pruning can then remove GENERAL knowledge that's less needed, potentially concentrating the remaining capacity on maritime

But empirical evidence for this is NONEXISTENT. No published work has demonstrated:
1. CPT on domain data → structured pruning → domain QA evaluation
2. Comparison of CPT-then-prune vs. direct CPT on smaller model
3. Whether pruning preferentially removes general over domain knowledge (or vice versa)

**Expected maritime QA performance (without prior maritime CPT):**

| Question Type | Pruned 7B→3B Expected | Native 3B Expected | Winner |
|--------------|----------------------|--------------------|-|
| "What is SOLAS?" | ~Correct | ~Correct | Tie |
| "List MARPOL annexes" | Partial | Partial | Tie |
| "CO2 system test interval per SOLAS FSS Code?" | Doesn't know | Doesn't know | Tie |
| "Engine room ventilation requirements?" | Vague/hallucinated | Vague/hallucinated | Tie |
| "STCW minimum sea service for OICEW?" | Doesn't know | Doesn't know | Tie |

Neither model has this knowledge. Pruning is orthogonal to the problem.

**SCORE: 4/10** — Pruning contributes nothing to domain QA accuracy. Without prior maritime CPT, a pruned 7B→3B model performs identically to a native 3B model on maritime questions — both fail on specific domain knowledge. With prior maritime CPT, the intermediate 7B step costs more and the benefit of CPT-then-prune over direct CPT-on-3B is hypothetical and unvalidated.

---

### 6. Mobile Deployability — Score: 7/10

**Depends entirely on which pruning method is used:**

**Structured pruning (Sheared LLaMA, Minitron, LLM-Pruner) → Perfect mobile deployment:**
- Produces a standard dense model
- Quantizable to Q4_K_M GGUF
- Compatible with llama.cpp, MLC-LLM, ExecuTorch
- Runs on any ARM CPU with sufficient RAM
- A pruned 7B → 3B at Q4 = ~1.8 GB = fits on 4GB+ phones

**Unstructured pruning (SparseGPT, Wanda) → NO mobile deployment benefit:**
- Sparse model still stored as full dense matrix (7B params including zeros)
- 7B at Q4 = ~4 GB → too large for most phones
- Zero inference speedup from sparsity on ARM
- Need sparse GGUF format (does not exist) or custom sparse kernels (not available)

**2:4 Structured sparsity → NO mobile deployment benefit:**
- Only accelerated by NVIDIA Ampere/Hopper tensor cores
- No ARM CPU acceleration
- Model size unchanged

**Layer pruning (ShortGPT) → Mobile-viable but with caveats:**
- Removing layers reduces model size proportionally
- 32 layers → 20 layers ≈ 37.5% reduction in model size
- But: remaining layers are standard → deployable
- Caveat: reasoning quality degrades, which affects chatbot usability

**The score reflects the split:**

| Method | Mobile-viable? | Speed benefit? | Size benefit? |
|--------|---------------|---------------|---------------|
| Structured pruning (layer/width removal) | YES | YES (smaller model) | YES |
| Unstructured sparsity (SparseGPT, Wanda) | NO extra benefit | NO | NO |
| 2:4 Sparsity | NO extra benefit | NO | NO |
| SliceGPT (embedding reduction) | YES | YES (smaller model) | YES (modest) |

**Three out of four major pruning paradigms provide NO mobile benefit.** Only structured pruning works, and it produces a model indistinguishable from any native dense model.

**SCORE: 7/10** — Structured pruning is mobile-viable (9-10). Unstructured sparsity is useless on mobile (2-3). The blended score reflects that the approach AS DESCRIBED includes multiple techniques, most of which don't help on ARM CPUs. If the user exclusively uses structured pruning, this would be 9/10.

---

### 7. Robustness — Score: 5/10

**Pruning reduces model redundancy, which inherently reduces robustness.**

Neural network robustness comes partly from redundant representations — multiple neurons/heads/layers encoding related but slightly different representations of the same concept. When you prune, you remove this redundancy. The model becomes more "efficient" but also more brittle.

**Evidence from pruning literature:**

- **SparseGPT/Wanda report perplexity, not robustness.** Perplexity measures average next-token prediction quality on a test set. It does NOT measure worst-case performance on unusual inputs, out-of-distribution queries, or adversarially-phrased questions. A model with 0.2 higher perplexity but identical average accuracy could have dramatically worse performance on edge cases.

- **ShortGPT (layer pruning) explicitly shows reasoning degradation:** Removing deep layers preserves factual recall (shallow layers store knowledge) but degrades complex reasoning. For a maritime chatbot, users ask compositional questions: "If we're in an ECA and the scrubber fails, what are our obligations under MARPOL Annex VI and what should we log?" This requires multi-step reasoning that degrades with layer pruning.

- **SliceGPT on Phi-2: 10% performance loss at only 25% pruning.** This suggests that smaller models are MORE sensitive to pruning than larger ones. A 7B model can tolerate 25% pruning; a 3B model might not tolerate any. And we're starting from 7B and pruning to 3B — a 57% reduction, far beyond what SliceGPT demonstrated.

- **Domain robustness is untested.** All pruning papers evaluate on GENERAL benchmarks (MMLU, Winogrande, ARC, etc.). No paper evaluates pruned models on domain-specific robustness — handling unusual phrasings of domain questions, combining domain facts in novel ways, or gracefully handling out-of-domain queries.

**For maritime chatbot robustness:**
- Pruned models may handle standard-phrasing questions adequately
- Unusual phrasings (crew members speak informally) → higher failure risk
- Compound questions requiring multiple knowledge sources → degraded by layer pruning
- Questions mixing maritime and general knowledge → weakened by capacity reduction

**SCORE: 5/10** — Pruning REDUCES robustness by removing redundancy. The model is optimized for average-case performance on calibration-like data but more brittle on edge cases. Layer pruning specifically degrades the compositional reasoning needed for complex maritime questions.

---

### 8. Catastrophic Forgetting — Score: 5/10

**Pruning IS controlled forgetting — the question is WHAT gets forgotten.**

The standard catastrophic forgetting discussion applies to models that learn new information at the cost of old information. Pruning has a different forgetting pattern:

**Pruning doesn't add new knowledge (so no traditional catastrophic forgetting).** Instead, pruning SELECTIVELY DESTROYS existing knowledge based on importance metrics.

**What gets preserved vs. forgotten during pruning:**

```
PRUNING IMPORTANCE METRICS:

    SparseGPT: Second-order approximation (Hessian-based)
    → Preserves weights with high curvature (important for loss)
    → Curvature computed on CALIBRATION data
    → Weights important for rare/domain-specific patterns 
       may have low curvature on general calibration data

    Wanda: |weight| × |activation|
    → Preserves weights that are BOTH large AND frequently activated
    → Maritime-specific weights may have low activation on general text
    → A weight encoding "STCW minimum sea service = 12 months" 
       has near-zero activation on Wikipedia text → gets pruned

    Layer pruning: Cosine similarity between layer inputs/outputs
    → Removes layers where input ≈ output (seemingly redundant)
    → But "redundant" on general text ≠ "redundant" on domain text
    → A layer critical for maritime reasoning may be "redundant" 
       for casual conversation
```

**The domain-specific forgetting risk:**

If you CPT a 7B model on maritime data and THEN prune, the pruning could preferentially destroy maritime knowledge because:
1. Maritime knowledge was recently injected (CPT) → sits in weight perturbations
2. Weight perturbations from CPT are SMALL relative to pretrained weights
3. Pruning importance metrics favor large, well-established weights
4. Recently-learned domain knowledge is therefore MORE LIKELY to be pruned

This is analogous to the "LoRA Learns Less and Forgets Less" phenomenon — the model's domain adaptations exist in a low-rank subspace that's vulnerable to compression.

**If you prune FIRST, then inject maritime knowledge:**
- The pruned model has less capacity to absorb new knowledge
- Fewer parameters = less room for new fact storage
- CPT/SFT on a pruned model may be less effective than on the full model

**Either ordering presents a forgetting/capacity problem.**

**SCORE: 5/10** — Pruning is inherently destructive to stored knowledge. When combined with domain-specific fine-tuning, either ordering creates risks: prune-then-CPT limits capacity for new knowledge; CPT-then-prune may preferentially destroy recently-learned domain knowledge. The importance metrics used by pruning algorithms are not designed to protect domain-specific knowledge.

---

### 9. Maintenance — Score: 6/10

**Maintaining a pruned model follows the same pattern as any other model of its final size.**

**Routine updates (new maritime regulations, updated SOLAS chapters):**
- SFT/LoRA on new Q&A pairs: identical to updating any 3B model
- No need to re-prune for incremental knowledge updates
- Cost: $20-200 per update cycle

**Major updates (significant new knowledge required):**
- Re-CPT the pruned model with new data: $50-500
- Same as maintaining any 3B model
- The pruning origin is irrelevant — the model IS a 3B model now

**The complication: if the pruned model underperforms, is it due to pruning or data?**
- Debugging is harder because you have an additional variable (pruning quality)
- If the model fails on certain question types, was it pruning damage or insufficient training data?
- The Minitron paper notes that different pruning axes (depth, width, attention) have different quality impacts — diagnosing issues requires understanding the pruning decisions

**Re-pruning considerations:**
- If the base 7B model is updated (e.g., LLaMA 3.2 → LLaMA 4), you'd need to re-prune from scratch
- Pruning decisions from the old model don't transfer to the new architecture
- This means re-running the entire pipeline for major model updates

**Compared to native 3B approach:**
- Native 3B model: base model → CPT → SFT → deploy. Update: new CPT/SFT.
- Pruned model: base 7B → (CPT) → prune → heal → SFT → deploy. Update: either update the 3B directly (same as native) or re-run from 7B (more expensive).
- The pruning step adds initial setup complexity but doesn't change the ongoing maintenance story

**SCORE: 6/10** — Day-to-day maintenance is identical to any 3B model. The pruning origin adds complexity to the initial pipeline and to major model refreshes (re-pruning from updated source). Slightly worse than native 3B maintenance due to the extra pipeline step.

---

### 10. Proven at Small Scale — Score: 6/10

**Structured pruning to small scale is well-demonstrated:**

| Paper | Source → Target | Result |
|-------|----------------|--------|
| Sheared LLaMA | LLaMA2-7B → 1.3B, 2.7B | Outperformed Pythia, INCITE, TinyLlama (2023 baselines) |
| Minitron | Nemotron-4 15B → 8B, 4B | +16% MMLU vs. from-scratch at same compute |
| LLM-Pruner | LLaMA-7B → various sizes | "Satisfactory capabilities" in zero-shot tasks |
| SliceGPT | LLaMA2-70B → 52B, Phi-2 → 2B | 90-99% zero-shot retention |
| ShortGPT | Various models → 50% depth | Minimal degradation on QA benchmarks |

**Caveats for our use case:**

1. **All results are on GENERAL benchmarks.** No domain-specific pruning study exists. We don't know how pruning affects domain QA performance.

2. **Baselines are outdated.** Sheared LLaMA (Oct 2023) beat Pythia-2.8B and TinyLlama-1.1B. But SmolLM3-3B (2025) outperforms both by a massive margin. The pruning advantage was a 2023 artifact.

3. **No maritime or similar domain-specific application.** Pruning has been demonstrated for general-purpose compression, code generation, and math. Never for technical domain QA.

4. **The 7B→3B pruning ratio is aggressive.** Most successful results prune 20-50% of parameters. A 7B→3B prune is a 57% reduction. Minitron's 15B→4B (73% reduction) is the most aggressive successful result, but it used NVIDIA-scale resources for distillation retraining.

5. **SparseGPT/Wanda (unstructured) are proven but USELESS on mobile.** Their impressive results (50-60% sparsity, minimal perplexity loss) don't translate to mobile deployment benefit.

6. **No published comparison of "pruned to 3B" vs. "best native 3B" using 2025 SOTA small models as the native baseline.** All comparisons used 2023-era small models that are now significantly outclassed.

**SCORE: 6/10** — Well-proven for general-purpose compression at small scale. But no domain-specific precedent, outdated comparison baselines, and a mismatch between the approach's strengths (unstructured sparsity on GPUs) and our deployment target (dense inference on ARM CPUs). The structured pruning subset is proven but produces results indistinguishable from native small models.

---

## FINAL SCORING SUMMARY

| Criterion | Score | Weight | Rationale |
|---|:---:|:---:|---|
| 1. Knowledge Retention | 4/10 | Critical | No maritime knowledge to retain in the source model. Pruning removes information; it cannot create domain knowledge. |
| 2. Inference Cost | 7/10 | Important | Structured pruning → standard model → normal inference. But unstructured/2:4 sparsity provides ZERO mobile ARM benefit. Misleading approach for mobile. |
| 3. Training Cost | 6/10 | Critical | Pruning itself is cheap ($5-20). Full pipeline with CPT + pruning + recovery is $1K-7K — 2-10x more than direct CPT on native 3B. |
| 4. Data Efficiency | 6/10 | Critical | Pruning step is very data-efficient (128 calibration samples). But maritime knowledge injection requires the same data as any other approach. |
| 5. Accuracy on Domain QA | 4/10 | Critical | Pruning contributes nothing to domain accuracy. Without maritime CPT, pruned 7B→3B ≈ native 3B on maritime QA. With maritime CPT, the intermediate 7B step is unvalidated overhead. |
| 6. Mobile Deployability | 7/10 | Important | Only structured pruning produces mobile-viable models. Unstructured and 2:4 sparsity are dead ends on ARM. When structured, deployment is identical to any dense model. |
| 7. Robustness | 5/10 | Important | Pruning removes redundancy → reduced robustness. Compositional reasoning degrades with layer pruning. Domain-specific robustness untested. |
| 8. Catastrophic Forgetting | 5/10 | Important | Pruning IS selective forgetting. Importance metrics biased toward general-text patterns. Recently-injected domain knowledge may be preferentially pruned. |
| 9. Maintenance | 6/10 | Moderate | Day-to-day maintenance identical to any 3B model. Pruning adds initial pipeline complexity and complicates major model refreshes. |
| 10. Proven at Small Scale | 6/10 | Critical | Well-proven for general compression. No domain-specific precedent. Comparison baselines are 2023-era models now surpassed by native SOTA small models. |

---

## TOTAL SCORE: 56/100

---

## KEY STRENGTHS (3)

### Strength 1: Cost-Effective Model Family Creation (Minitron Paradigm)

If your goal is to produce an ENTIRE FAMILY of models at different sizes (8B, 4B, 2B, 1B) from a single trained large model, pruning + distillation is dramatically more efficient than training each size from scratch. NVIDIA's Minitron demonstrated this convincingly: deriving 8B and 4B models from a 15B base required 40x fewer training tokens per model and achieved compute savings of 1.8x for the full family.

For a maritime chatbot project that might deploy on different devices (flagship phone → 3B, budget phone → 1.5B, embedded → 0.5B), the pipeline would be:

```
Train one 7B maritime model (CPT on maritime data)
├── Prune to 3B → flagship deployment
├── Prune to 1.5B → budget deployment  
└── Prune to 0.5B → embedded deployment
```

This is genuinely cheaper than running separate CPT+SFT for each target size. The pruning approach shines when you need MULTIPLE model sizes from ONE knowledge-injection effort.

### Strength 2: Pruning + Quantization Compose Well

SparseGPT demonstrated that pruning and quantization are COMPATIBLE and can be combined. A 7B model that is 50% sparse AND quantized to 4-bit would theoretically need half the compute of a dense 4-bit model — IF the hardware supports sparse operations. On future mobile hardware (Apple's Neural Engine, Qualcomm's Hexagon, or custom accelerators) that may support structured sparsity, the combination of pruning + quantization could deliver significantly better performance-per-watt than quantization alone.

This is a FUTURE-LOOKING advantage that doesn't help today's ARM CPUs but positions the approach well for 2027+ mobile silicon that may add sparse compute capabilities.

### Strength 3: The Pruning Step is Remarkably Cheap and Fast

SparseGPT prunes a 7B model in 1-2 hours on a single GPU ($3-6). Wanda does it in minutes. Even Sheared LLaMA's full pipeline requires only 3% of from-scratch compute. This means pruning can be added to almost any pipeline as an optional compression step with minimal cost:

- If it helps: great, you saved model size
- If it doesn't help: you lost only a few dollars and hours
- The cost of TRYING pruning is negligible compared to other approaches

This low barrier to experimentation is genuinely valuable. You can test whether pruning a maritime-CPT'd 7B model retains more knowledge than direct CPT on a native 3B model, and the cost of the experiment is $5-20.

---

## KEY WEAKNESSES (3)

### Weakness 1: Pruning Solves a Problem That's Already Solved — Category Error for Maritime Chatbot

**This is the fatal conceptual flaw.** Pruning answers the question: "How do we make a large model run on constrained hardware?" Our maritime chatbot project has a different question: "How do we inject maritime knowledge into a small model's weights?"

We can ALREADY deploy 3B models on phones using Q4 quantization (~1.8GB, 8-15 tok/sec). The hardware constraint IS SOLVED. What's NOT solved is getting maritime domain knowledge into those 3B parameters.

Pruning does nothing for knowledge injection. It is ORTHOGONAL to our core challenge. The approach is analogous to spending $5,000 on a high-end car suspension when the car has no engine — you've optimized the wrong system.

Every dollar and hour spent on pruning is a dollar and hour NOT spent on CPT (which actually injects maritime knowledge), SFT (which teaches the model to use that knowledge), or alignment (which ensures accurate, safe responses). The opportunity cost of pursuing pruning over knowledge injection is the approach's real weakness.

### Weakness 2: Unstructured Sparsity — The Approach's Flagship Technique — is Dead on Mobile

SparseGPT and Wanda are the most-cited, most-impressive pruning results. They achieve 50-60% sparsity with negligible quality loss. But on mobile ARM CPUs:

- No sparse matrix multiply hardware units
- No software support in llama.cpp, MLC-LLM, or ExecuTorch for sparse inference
- Sparse GGUF format does not exist
- The model runs at EXACTLY the same speed and uses EXACTLY the same memory as a dense model

This means the approach's best results are unrealizable on our target hardware. The impressive academicpaper numbers (50% compression! negligible quality loss!) translate to ZERO practical benefit on a phone.

2:4 semi-structured sparsity faces the same problem: it's accelerated only on NVIDIA Ampere+ GPUs, which do not exist in mobile phones.

Only structured pruning (removing entire layers/heads) produces genuine mobile benefits — but this is a much more aggressive operation with higher quality degradation, and the result is just a standard dense model (indistinguishable from a natively-trained small model).

### Weakness 3: Pruning Advantage is a Temporal Artifact — Modern Native Small Models Have Caught Up

Sheared LLaMA (Oct 2023) pruned LLaMA2-7B (2T tokens) to 2.7B and beat Pythia-2.8B and TinyLlama-1.1B. This was impressive in 2023, when native small models were weak.

In 2025-2026:
- SmolLM3-3B: trained on 11T tokens, outperforms Llama-3.2-3B, Qwen2.5-3B
- Qwen2.5-3B: trained on 18T tokens, strong across all benchmarks
- Qwen3-1.7B: trained on 36T tokens, MMLU 62.63
- Phi-3-mini: 3.8B, trained on 3.3T tokens, rivals GPT-3.5

These native small models are trained on 5-18x more data than the 7B source models used in pruning papers. The information disadvantage that made pruning attractive (small models weren't trained on enough data) has been eliminated by scaling up small model training.

**Pruning a 2023-era 7B model → 3B gives you a model WORSE than a 2025-era native 3B.** Even pruning a 2025-era 7B model → 3B is unlikely to beat a 2025-era native 3B that was purpose-designed for that scale.

The pruning literature's competitive advantage was a WINDOW that has now closed. The field has moved on: instead of pruning large models to small ones, researchers now focus on training better small models directly (the Phi-1/2/3 philosophy of data quality over model size).

---

## VERDICT

**Pruning + Sparsification scores 56/100 — a deployment optimization technique applied to a knowledge injection problem, solving the wrong challenge.**

The approach suffers from a fundamental **category error**: it is a MODEL COMPRESSION technique being evaluated as a KNOWLEDGE INJECTION technique. For our maritime chatbot, the bottleneck is not "how to fit a model on a phone" (already solved via Q4 quantization of native 3B models) but "how to get maritime knowledge into the model's weights" (unsolved by pruning).

**The sharp answer to the key question:**

> **"Does pruning a 7B model to 3B-equivalent give better maritime QA than fine-tuning a native 3B model?"**

**No.** For three reasons:
1. The 7B source model has negligible maritime knowledge — there's nothing extra to preserve
2. Unstructured sparsity (the approach's strongest technique) provides zero benefit on mobile ARM hardware
3. Modern native 3B models (trained on 11-18T tokens) are already stronger than 2023-era pruned-from-7B models

The only scenario where pruning adds value: if you first CPT a 7B model on maritime data (making it a "maritime 7B"), THEN prune to 3B, the resulting model MIGHT retain more maritime knowledge than directly CPT-ing a native 3B. But this is unvalidated, costs 2-10x more, and the marginal benefit is uncertain.

**Comparison to other evaluated approaches:**

| Approach | Score | Comment |
|---|:---:|---|
| SFT (Synthetic Data + Fine-Tuning) | 71/100 | Better — directly addresses knowledge problem |
| Pretraining From Scratch | 62/100 | Better for deep knowledge, worse on cost |
| CPT (Continued Pretraining) | 61/100 | Much better — directly injects domain knowledge |
| **Pruning + Sparsification** | **56/100** | **Solves wrong problem** |
| RL Methods (DPO/GRPO/etc.) | 57/100 | Similar score — also doesn't inject knowledge |
| Extreme Quantization | 53/100 | Worse — similar category error (compression vs. injection) |
| Reasoning Distillation | 52/100 | Worse — teaches reasoning without domain knowledge |

**Pruning's correct role:** It is a SUPPLEMENTARY technique, not a primary approach. In a complete pipeline:

```
CORRECT ROLE FOR PRUNING IN THE MARITIME CHATBOT:

    Step 1: Select best native 3B model (Qwen2.5-3B, SmolLM3-3B)     ← PRIMARY
    Step 2: CPT on maritime data (500M-2B tokens)                      ← PRIMARY
    Step 3: SFT on maritime Q&A with NEFTune                           ← PRIMARY
    Step 4: DPO/KTO alignment                                          ← PRIMARY
    Step 5: Q4_K_M quantization                                        ← PRIMARY
    Step 6: (OPTIONAL) If model too large, consider structured         ← SUPPLEMENTARY
            pruning to reduce by 10-20% before quantization
    Step 7: Deploy on phone                                            ← PRIMARY
    
    Pruning is Step 6 — optional, supplementary, NOT the strategy.
```

---

## BEST COMBINATION: How Pruning Can Supplement (Not Replace) a Knowledge Pipeline

```
RECOMMENDED: Pruning as optional compression step, not as strategy

PRIMARY PIPELINE (same as recommended in CPT/SFT evaluations):
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 1: SELECT BASE MODEL                              │
    │  Qwen2.5-3B or SmolLM3-3B (best native small models)  │
    │  Already trained on 11-18T tokens of diverse data       │
    │  Cost: $0                                               │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 2: CONTINUED PRETRAINING on maritime text          │
    │  Raw regulations + synthetic textbooks + maritime corpus │
    │  500M-2B tokens, multi-stage curriculum                  │
    │  Cost: $50-$500                                          │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 3: SYNTHETIC DATA + SFT                            │
    │  50K-200K Q&A pairs from textbooks + Evol-Instruct      │
    │  Full SFT with NEFTune                                   │
    │  Cost: $100-$500                                         │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 4: ALIGNMENT (DPO/KTO)                             │
    │  Maritime preference pairs                               │
    │  Cost: $50-$200                                          │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 5: QUANTIZE (Q4_K_M) → ~1.8GB                     │
    │  Standard GGUF quantization                              │
    │  Cost: $0 (minutes on any machine)                       │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
                    FITS ON PHONE? 
              ┌──── YES ──→ SHIP IT
              │
              └──── NO (tight on target hardware)
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Phase 6 (OPTIONAL): STRUCTURED PRUNING                   │
    │  Remove 10-20% of layers/heads via ShortGPT/LLM-Pruner │
    │  Brief LoRA healing with maritime calibration data       │
    │  Re-quantize → reduced footprint                         │
    │  Cost: $10-$50                                           │
    └─────────────────────────────────────────────────────────┘

TOTAL (without pruning): $200-$1,200
TOTAL (with optional pruning): $210-$1,250

WHEN PRUNING IS WORTH ADDING:
  ✓ Model is 10-20% too large for target hardware
  ✓ You need a model family (3B, 1.5B, 0.5B from one source)
  ✓ Future hardware with sparse acceleration becomes available
  ✓ You want to experiment (cost of trying is <$50)

WHEN PRUNING IS NOT WORTH ADDING:
  ✗ Native 3B already fits on target hardware (it does, at Q4)
  ✗ You're tempted to skip CPT and "just prune a bigger model"
  ✗ You expect unstructured sparsity to accelerate mobile inference
  ✗ You hope pruning will somehow inject domain knowledge
```

### The Experiment Worth Running (Budget: $50)

If you're curious whether prune-from-7B outperforms native-3B for maritime QA, here's a cheap experiment:

```
EXPERIMENT: Pruning value for maritime QA (estimated cost: $50)

    A) Qwen2.5-3B → CPT maritime → SFT → Q4 → evaluate
    B) Qwen2.5-7B → CPT maritime → Sheared-style prune to 3B → SFT → Q4 → evaluate
    
    Compare A vs B on:
    • 100 maritime QA questions (manually graded)
    • Perplexity on held-out maritime text
    • MMLU Medical/General Knowledge (proxy for knowledge retention)
    
    If B > A: pruning adds value, continue this path
    If B ≤ A: pruning doesn't help, use simpler pipeline
    
    Cost: ~$50 total (CPT on 7B is more expensive than 3B)
    Time: 2-3 days
```

This experiment is worth doing ONCE, but only after the primary CPT+SFT pipeline is established and benchmarked. Pruning is an optimization, not a foundation.

---

**Bottom line:** Pruning + Sparsification is the wrong tool for the job. Our maritime chatbot needs KNOWLEDGE, not COMPRESSION. We already have models that fit on phones (native 3B at Q4 = 1.8GB). What we lack is maritime expertise in those models. Every approach that INJECTS knowledge (CPT, SFT, knowledge distillation) outranks an approach that merely COMPRESSES existing models. Use pruning, if at all, as an optional final compression step after the real work of knowledge injection is complete.

---

*This evaluation is based on published research from IST Austria (SparseGPT), CMU (Wanda), Meta (ShortGPT), Princeton (Sheared LLaMA), NVIDIA (Minitron), Microsoft (SliceGPT), NUS (LLM-Pruner), and the broader LLM pruning and sparsification literature. All scores reflect the approach's contribution to a domain-specific maritime chatbot on mobile phones, not its general compression utility. Pruning is a valuable technique for model compression — it is simply not a knowledge injection technique, and our primary challenge is knowledge injection.*
