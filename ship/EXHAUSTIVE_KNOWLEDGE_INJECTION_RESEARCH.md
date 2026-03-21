# EXHAUSTIVE RESEARCH: Methods to Inject Domain-Specific Knowledge into Small Language Models (1-3B) WITHOUT RAG

**Date:** February 16, 2026  
**Purpose:** Maritime chatbot on mobile phones / ultra-low-resource devices  
**Constraint:** NO RAG — all knowledge must be embedded internally in the model  
**Target Model Size:** 1-3B parameters  
**Target Deployment:** Mobile phones (iOS/Android), edge devices with 2-6GB RAM  

> **Project constraint (important):** We assume **no paid teacher APIs**. Any references below to GPT-4/Claude/DeepSeek APIs are **historical research context**; for implementation we use a **local open-weight teacher** on the 4-GPU machine.

---

## TABLE OF CONTENTS
- [A. Continued Pretraining Approaches](#a-continued-pretraining-approaches)
- [B. Supervised Fine-Tuning Approaches](#b-supervised-fine-tuning-approaches)
- [C. Knowledge Distillation Approaches](#c-knowledge-distillation-approaches)
- [D. RL-Based Approaches](#d-rl-based-approaches)
- [E. Data-Centric Approaches](#e-data-centric-approaches)
- [F. Architecture Modification Approaches](#f-architecture-modification-approaches)
- [G. Knowledge Editing/Injection Approaches](#g-knowledge-editinginjection-approaches)
- [H. Hybrid/Combined Approaches](#h-hybridcombined-approaches)
- [I. Pre-training from Scratch Approaches](#i-pre-training-from-scratch-approaches)
- [J. Other Approaches](#j-other-approaches)
- [Final Ranking & Recommended Pipeline](#final-ranking--recommended-pipeline)

---

## A. CONTINUED PRETRAINING APPROACHES

### A1. Domain-Adaptive Continued Pretraining (DACP)

**What it does:** Takes a pretrained base model (e.g., Qwen2.5-1.5B, SmolLM3-3B, LLaMA-3.2-1B) and continues pretraining on domain-specific raw text (maritime textbooks converted to plain text). The model's weights are updated using the standard causal language modeling (next-token prediction) objective on the new domain corpus. This shifts the model's internal knowledge distribution toward maritime engineering without destroying general capabilities.

**How it injects domain knowledge:** By exposing the model to millions of tokens of maritime text (ship construction, MARPOL regulations, STCW conventions, marine diesel engines, corrosion engineering, ballast water management), the model's internal parameters absorb factual knowledge, terminology, relationships, and reasoning patterns specific to the maritime domain. The knowledge is encoded in the weight matrices — no external retrieval needed.

**Hardware needed for training:**
- Minimum: 1x A100 40GB or 2x RTX 3090/4090 (24GB each)
- For 1.5B model: ~16GB VRAM with gradient checkpointing + bf16
- For 3B model: ~24-40GB VRAM or use DeepSpeed ZeRO-2/3
- Training time: 2-7 days depending on corpus size and compute

**Inference resource requirements:**
- 1.5B model @ 4-bit: ~1GB RAM — YES runs on mobile
- 3B model @ 4-bit: ~2GB RAM — YES runs on mobile
- Can use llama.cpp, MLC-LLM, or ExecuTorch for mobile deployment

**Quality/accuracy for domain knowledge retention:**
- HIGH. Continued pretraining is the most proven method for injecting deep factual knowledge into model weights
- Well-demonstrated across medical (BioMedLM), legal (SaulLM), financial (FinGPT), and code domains
- Risk of catastrophic forgetting of general capabilities — mitigated by mixing general data (5-10%)

**Data requirements:**
- Minimum: 50M tokens of domain text (achievable from ~10-20 maritime textbooks)
- Optimal: 200M-1B tokens 
- Format: Raw text, chunked into training sequences (2048-4096 tokens)
- Need to convert EPUB/DJVU textbooks to clean text
- Supplement with maritime Wikipedia articles, IMO convention text, maritime Q&A forums

**Proven results at small scale (<3B):**
- phi-1 (1.3B) trained on "textbook quality" data achieved 50.6% on HumanEval — proving small models can absorb domain knowledge deeply
- phi-1.5 (1.3B) matched 5x larger models on reasoning by continued pretraining on high-quality data
- SmolLM3-3B: 3-stage pretraining on 11T tokens achieves SoTA at 3B scale
- BioMedLM (2.7B): Domain-specific pretraining on PubMed achieved strong biomedical QA

**Papers:**
- LLaMA (arXiv:2302.13971) — pretraining on public datasets
- phi-1 "Textbooks Are All You Need" (arXiv:2306.11644) — textbook-quality data for pretraining
- phi-1.5 (arXiv:2309.05463) — continued textbook training for reasoning
- SmolLM3 (huggingface.co/blog/smollm3) — 3-stage pretraining recipe
- OpenELM (arXiv:2404.14619) — efficient layer-wise scaling for pretraining

**Pros for maritime textbook knowledge without RAG:**
- Deepest knowledge integration possible — knowledge becomes part of the model
- No inference-time overhead — the model just "knows" the content
- Works with raw text — textbooks can be directly used after OCR/conversion
- Can absorb entire textbook contents if training data is sufficient
- Model maintains knowledge permanently after training

**Cons:**
- Requires significant compute for training (but one-time cost)
- Risk of catastrophic forgetting of general capabilities
- Maritime corpus may be small (<100M tokens), limiting effectiveness
- Need careful data cleaning from EPUB/DJVU sources
- May need multiple epochs on small corpora, risking overfitting

**SCORE: 9/10** — The single most important method for this use case. Maritime textbooks as training data is exactly the phi-1 "Textbooks Are All You Need" approach applied to a real domain.

---

### A2. Curriculum-Based Continued Pretraining

**What it does:** A refined version of DACP where training data is introduced in a structured curriculum — easier concepts first, harder ones later, mimicking how maritime cadets learn. Inspired by SmolLM3's 3-stage pretraining approach and phi-series curriculum design.

**How it injects domain knowledge:** Same mechanism as DACP but with staged learning:
- Stage 1 (60% of training): General maritime text + basic ship terminology 
- Stage 2 (25%): Technical content — MARPOL annexes, engine schematics, construction details
- Stage 3 (15%): Complex problem-solving — troubleshooting, regulation interpretation, safety scenarios

**Hardware needed:** Same as A1.

**Inference requirements:** Same as A1 — YES mobile compatible.

**Quality:** HIGHER than basic DACP — curriculum learning prevents catastrophic forgetting and improves retention of complex knowledge. SmolLM3 demonstrated this with their 3-stage approach (web→math/code→high-quality upsampling).

**Data requirements:**
- Same total volume as A1, but data must be organized by difficulty/topic
- Requires human curation to categorize maritime content by complexity
- Format: Multiple data mixtures at different ratios

**Proven results:** SmolLM3 (3B) used 3-stage training: Stage 1 (85% web, 12% code, 3% math for 8T tokens) → Stage 2 (75% web, 15% code, 10% math for 2T tokens) → Stage 3 (63% web, 24% code, 13% math for 1.1T tokens). This staged approach yielded better results than a single-stage mixture.

**Papers:** SmolLM3 blog, phi-1.5, Llama 3 (arXiv:2407.21783), Qwen2.5

**Pros:** Better knowledge retention, less forgetting, structured learning  
**Cons:** Requires careful data curation, more complex training pipeline

**SCORE: 9/10** — Perfect enhancement over basic DACP.

---

## B. SUPERVISED FINE-TUNING APPROACHES

### B1. Full Supervised Fine-Tuning (Full SFT)

**What it does:** Takes a pretrained (or continued-pretrained) model and fine-tunes ALL parameters on instruction-response pairs in the maritime domain. The model learns to follow instructions and produce correct, detailed answers about maritime topics.

**How it injects domain knowledge:** Through curated instruction-answer pairs: "Q: What are the six annexes of MARPOL? A: Annex I covers oil pollution, Annex II covers noxious liquid substances..." The model memorizes both the knowledge and the format for presenting it.

**Hardware needed:**
- 1.5B model: 1x A100 40GB or 2x RTX 4090
- 3B model: 2x A100 or DeepSpeed ZeRO-3 on consumer GPUs
- Training time: 1-3 days for typical SFT datasets (10K-100K examples)

**Inference requirements:** Same as base model — YES mobile compatible.

**Quality:** HIGH for knowledge that is directly covered in training data. However, SFT alone is less effective for deep factual knowledge compared to continued pretraining — it's better for learning FORMAT and BEHAVIOR than raw facts.

**Data requirements:**
- Minimum: 1K-10K high-quality instruction-response pairs
- Optimal: 10K-50K pairs covering all maritime topics
- Format: {"instruction": "...", "input": "...", "output": "..."} or chat format
- Must be manually or synthetically created from textbooks
- Quality >> Quantity (DEITA paper showed 6K samples can match 60K+ if selected well)

**Proven results:**
- Orca 2 (arXiv:2311.11045): Small LMs (7B, 13B) taught to reason via careful SFT, surpassing 5-10x larger models
- Tulu 3 (arXiv:2411.15124): SFT + DPO + RLVR pipeline on Llama 3.1 surpassed GPT-4o-mini
- DEITA (arXiv:2312.15685): 6K carefully selected SFT samples matched SOTA
- SmolLM3 SFT: 1.8B tokens (1B non-reasoning + 0.8B reasoning), 4 epochs

**Papers:** Orca 2, Tulu 3, DEITA, SmolLM3, LAB (arXiv:2403.01081)

**Pros:**
- Directly teaches the model HOW to answer maritime questions
- Can encode specific regulatory knowledge in exact format
- Relatively fast training
- Well-understood, mature technique

**Cons:**
- Knowledge coverage limited to what's in the training pairs
- Cannot teach deep understanding from SFT alone — needs pretraining first
- Risk of overfitting on small datasets
- High-quality maritime QA pairs must be created (costly/time-consuming)

**SCORE: 8/10** — Essential second step after continued pretraining, but should not be the only approach.

---

### B2. LoRA (Low-Rank Adaptation)

**What it does:** Instead of updating all model parameters, LoRA freezes the pretrained weights and injects trainable low-rank decomposition matrices (A and B) into each transformer layer. For a weight matrix W ∈ ℝ^(d×k), LoRA adds ΔW = BA where B ∈ ℝ^(d×r) and A ∈ ℝ^(r×k), with rank r << min(d,k). This reduces trainable parameters by 10,000x compared to full fine-tuning.

**How it injects domain knowledge:** The low-rank matrices learn domain-specific adaptations to the frozen base model. During inference, LoRA weights are merged into the base model (W' = W + BA), adding ZERO inference latency or memory overhead.

**Hardware needed:**
- 1.5B model: 1x RTX 3090/4090 (24GB) or even RTX 3060 (12GB) with r=16
- 3B model: 1x RTX 4090 or A100
- Training time: Hours to 1-2 days
- Memory: Typically 2-4x less than full fine-tuning

**Inference requirements:** After merging, SAME as base model — YES mobile compatible. LoRA weights merge into base model, no extra cost.

**Quality:** IMPORTANT FINDING from "LoRA Learns Less and Forgets Less" (arXiv:2405.09673):
- LoRA substantially **underperforms** full fine-tuning for new knowledge acquisition
- BUT LoRA better **preserves** general capabilities (less forgetting)
- Full fine-tuning learns perturbations with rank 10-100x greater than typical LoRA
- For KNOWLEDGE INJECTION specifically, LoRA alone is inadequate — it's better for style/behavior adaptation

**Data requirements:** Same as SFT (can use any instruction-tuning data format).

**Proven results:**
- LoRA (arXiv:2106.09685): On-par with full fine-tuning for GPT-3 on generation quality, but NOT for heavy knowledge injection
- Used extensively for domain adaptation but primarily for behavioral fine-tuning, not deep knowledge injection

**Papers:** LoRA (arXiv:2106.09685), "LoRA Learns Less and Forgets Less" (arXiv:2405.09673)

**Pros:**
- Extremely memory efficient — can fine-tune 3B model on consumer GPU
- No inference overhead after merging
- Can maintain multiple LoRA adapters for different sub-domains
- Less catastrophic forgetting than full fine-tuning
- Fastest training method

**Cons:**
- **CRITICAL LIMITATION**: LoRA learns LESS new knowledge than full fine-tuning
- Low rank limits capacity to absorb complex domain knowledge
- Not suitable as the primary knowledge injection method
- Better for formatting/style than factual content

**SCORE: 6/10** — Useful as an efficiency tool for SFT step, but inadequate as sole knowledge injection method. Use for behavior tuning AFTER domain pretraining.

---

### B3. QLoRA (Quantized LoRA)

**What it does:** Combines 4-bit quantization of the base model with LoRA fine-tuning. Uses three innovations: (a) NF4 data type optimized for normally distributed weights, (b) double quantization for quantization constants, (c) paged optimizers for memory management. Enables fine-tuning a 65B model on a single 48GB GPU.

**How it injects domain knowledge:** Same as LoRA but with a quantized base model, making the process extremely memory-efficient. The Guanaco model family (based on QLoRA) reached 99.3% of ChatGPT performance.

**Hardware needed:**
- 1.5B model: 1x RTX 3060 12GB (easily)
- 3B model: 1x RTX 3060 12GB or any consumer GPU
- Training time: Hours
- Memory: ~4x less than even standard LoRA

**Inference requirements:** YES mobile compatible (quantized model + merged LoRA).

**Quality:** Same limitations as LoRA for knowledge injection, but exceptional for budget-constrained training.

**Data requirements:** Same as LoRA/SFT.

**Proven results:** QLoRA (arXiv:2305.14314) — Guanaco models outperformed all previous open-source models. Fine-tuned 1000+ models across 8 datasets.

**Papers:** QLoRA (arXiv:2305.14314)

**Pros:** Ultra-low memory training, democratizes fine-tuning  
**Cons:** Same knowledge injection limitations as LoRA, quantization adds noise

**SCORE: 6/10** — Same score as LoRA. Excellent efficiency tool but not for deep knowledge injection.

---

### B4. DoRA (Weight-Decomposed Low-Rank Adaptation)

**What it does:** Decomposes pretrained weights into magnitude and direction components. Only applies LoRA to the direction component while learning the magnitude separately. This more closely mirrors the learning pattern of full fine-tuning.

**How it injects domain knowledge:** Better than LoRA for knowledge injection because the magnitude-direction decomposition captures more of what full fine-tuning learns, potentially bridging the "learns less" gap identified in the LoRA Learns Less paper.

**Hardware needed:** Slightly more than LoRA (~10-15% overhead for the magnitude component).

**Inference requirements:** Can be merged like LoRA — YES mobile compatible.

**Quality:** Consistently outperforms LoRA across tasks with the same number of trainable parameters.

**Data requirements:** Same as LoRA/SFT.

**Proven results:** KTO paper (arXiv:2402.01306) demonstrates alignment methods working at 1B-30B scale. DoRA shows improvements over LoRA even with same rank.

**Papers:** DoRA (arXiv:2402.01306 — related), VeRA, AdaLoRA

**Pros:** Better performance than LoRA, same merge-ability, minimal extra cost  
**Cons:** Still fundamentally limited by low-rank bottleneck for knowledge injection

**SCORE: 7/10** — Marginal improvement over LoRA for knowledge tasks.

---

### B5. GaLore (Gradient Low-Rank Projection)

**What it does:** Instead of constraining weight updates to low rank (like LoRA), GaLore projects gradients to a low-rank space during optimization, but allows the full-rank weight matrix to be updated. This achieves memory efficiency comparable to LoRA while approaching full fine-tuning performance.

**How it injects domain knowledge:** Enables full-rank weight updates (better for knowledge) with low memory footprint. The gradients are projected, not the weights — so the model can learn complex, high-rank knowledge patterns.

**Hardware needed:**
- Similar to LoRA memory footprint but with full fine-tuning quality potential
- 3B model trainable on single GPU with ~16-24GB

**Inference requirements:** Full model weights (no extra adapter) — YES mobile compatible after quantization.

**Quality:** Approaches full fine-tuning quality — significantly better than LoRA for knowledge-intensive tasks.

**Data requirements:** Same as full SFT.

**Proven results:** GaLore (arXiv:2403.07691 references, memory-efficient training research) — enables pretraining LLaMA-7B on single GPU.

**Papers:** GaLore-related research, memory-efficient optimizer research

**Pros:** Full-rank updates with LoRA-like memory, best of both worlds  
**Cons:** Slower training than LoRA, newer technique with less ecosystem support

**SCORE: 8/10** — Excellent for knowledge injection with constrained hardware.

---

### B6. NEFTune (Noisy Embeddings Fine-Tuning)

**What it does:** Adds uniform random noise to embedding vectors during fine-tuning. Remarkably simple technique that improves instruction-following quality dramatically. LLaMA-2-7B with Alpaca improved from 29.79% to 64.69% on AlpacaEval.

**How it injects domain knowledge:** Doesn't directly inject knowledge — it's a training regularization technique that improves the quality of fine-tuning. When applied during domain SFT, it helps the model generalize better from limited maritime training data.

**Hardware needed:** Zero additional hardware — just add noise during training.

**Inference requirements:** No change — YES mobile compatible.

**Quality:** 8-10% improvement on instruction-following benchmarks with no downside.

**Data requirements:** Same as whatever SFT method it augments.

**Proven results:** NEFTune (arXiv:2310.05914) — improvements across Alpaca, Evol-Instruct, ShareGPT, OpenPlatypus. Even models post-RLHF (LLaMA-2-Chat) benefited.

**Papers:** NEFTune (arXiv:2310.05914)

**Pros:** Free improvement, trivial to implement (1 line of code), no inference cost  
**Cons:** Doesn't add knowledge itself — just improves fine-tuning quality

**SCORE: 7/10** — Must-have augmentation technique. Apply it to ALL fine-tuning steps.

---

## C. KNOWLEDGE DISTILLATION APPROACHES

### C1. Standard Knowledge Distillation (Teacher-Student)

**What it does:** A large "teacher" model (e.g., GPT-4, Claude, Qwen-72B) generates responses to domain-specific questions. A small "student" model (1-3B) is trained to mimic the teacher's outputs (and optionally, internal representations/logits).

**How it injects domain knowledge:** The teacher model, which has broad knowledge including maritime topics, generates high-quality answers to maritime questions. The student learns not just the answers but the reasoning patterns. This transfers both factual knowledge and reasoning ability.

**Variants:**
1. **Response-level KD:** Student learns from teacher's text outputs
2. **Logit-level KD:** Student learns from teacher's full probability distribution
3. **Feature-level KD:** Student matches teacher's internal hidden states
4. **On-Policy KD (GKD):** Student trains on its OWN outputs evaluated by the teacher

**Hardware needed:**
- Teacher inference: API calls (GPT-4, Claude) or local inference of 70B+ model
- Student training: Same as SFT (1x consumer GPU for 1.5-3B model)
- Main cost: Teacher API calls for generating training data

**Inference requirements:** Only student model deployed — YES mobile compatible.

**Quality:** HIGH — this is how DeepSeek-R1 distilled reasoning into 1.5B and 7B models that rivaled much larger models.

**Data requirements:**
- Need: 10K-100K questions covering maritime domain
- Teacher generates: Answer + reasoning trace for each question
- Format: {"question": "...", "teacher_response": "...", "reasoning": "..."}
- Can be generated batch via API

**Proven results:**
- DeepSeek-R1 (arXiv:2501.12948): Distilled reasoning from 671B MoE model into 1.5B, 7B, 8B, 14B, 32B, 70B models. The 1.5B distilled model showed remarkable reasoning ability
- GKD (arXiv:2306.13649): On-policy distillation trains student on self-generated outputs evaluated by teacher — addresses distribution mismatch
- Orca 2 (arXiv:2311.11045): Taught small LMs (7B, 13B) different reasoning strategies per task type, surpassing 5-10x larger models

**Papers:** DeepSeek-R1, GKD, Orca 2

**Pros:**
- Can transfer complex reasoning patterns to tiny models
- Student model runs on mobile — only training needs large compute
- Teacher can be run locally on the 4-GPU box (no paid APIs required)
- Best quality-per-parameter ratio among all methods
- Proven at 1.5B scale (DeepSeek-R1-Distill-Qwen-1.5B)

**Cons:**
- Depends on teacher model being strong enough to follow strict grounding prompts (choose best local open-weight teacher available)
- Compute/time costs for local generation (multi-day runs acceptable)
- Student can't exceed teacher's knowledge
- Logit-level KD requires white-box access to teacher

**SCORE: 9/10** — Critical method. Use a **strong local teacher** to generate grounded maritime QA data (optionally with reasoning traces), then distill into the 1.5-3B student.

---

### C2. Reasoning-Trace Distillation (Chain-of-Thought Distillation)

**What it does:** Specifically distills the teacher's step-by-step reasoning process, not just final answers. The student learns to produce explicit reasoning chains that lead to correct maritime answers.

**How it injects domain knowledge:** The student model learns both WHAT maritime facts are correct AND HOW to reason about them. For example: "To determine if a vessel needs ballast water treatment, first check the BWM Convention ratification status of the flag state, then check the capacity..."

**Hardware needed:** Same as C1 (teacher for generation, standard GPU for student training).

**Inference requirements:** YES mobile compatible. May generate slightly longer responses due to reasoning traces.

**Quality:** HIGHER than standard KD for complex reasoning tasks. DeepSeek-R1-Distill models showed this conclusively.

**Data requirements:**
- Same as C1 but each example includes full reasoning chain
- Format: "Think step by step: [reasoning]... Therefore, the answer is [answer]"

**Proven results:**
- DeepSeek-R1 distillation: Pure RL on large model → distill reasoning into small models
- Orca 2: Different solution strategies (step-by-step, recall-then-generate, direct answer) for different task types
- SmolLM3: Reasoning mid-training with 35B tokens from reasoning traces

**Papers:** DeepSeek-R1, Orca 2, SmolLM3

**Pros:** Best for complex maritime problem-solving (troubleshooting engines, regulation interpretation)  
**Cons:** Longer training data, longer inference for reasoning mode

**SCORE: 9/10** — Essential for the maritime domain where reasoning about regulations and engineering problems is critical.

---

### C3. On-Policy Distillation / Generalized Knowledge Distillation (GKD)

**What it does:** Unlike standard KD where the student trains on a fixed dataset of teacher outputs, GKD trains the student on its OWN generated sequences, using the teacher to evaluate and score these sequences. This addresses the train-test distribution mismatch.

**How it injects domain knowledge:** The student generates maritime answers → teacher evaluates them → student improves based on teacher feedback. This iterative process better aligns the student's actual generation distribution.

**Hardware needed:** Higher than standard KD (need both teacher and student active during training).

**Inference requirements:** YES mobile compatible (only student deployed).

**Quality:** Superior to standard KD in multiple benchmarks (ICLR 2024).

**Data requirements:** Prompts/questions only — responses generated during training.

**Proven results:** GKD (arXiv:2306.13649) — demonstrated on summarization, translation, arithmetic reasoning.

**Papers:** GKD (arXiv:2306.13649)

**Pros:** Better generalization, addresses distribution mismatch  
**Cons:** More complex training loop, higher training cost (teacher must run during training)

**SCORE: 8/10** — Excellent refinement of KD, worth the added complexity.

---

### C4. Task-Specific Knowledge Distillation

**What it does:** Instead of general-purpose distillation, trains the student specifically on task types relevant to the deployment domain — for maritime: factual Q&A, regulation lookup, troubleshooting, safety scenario analysis.

**How it injects domain knowledge:** Each task type gets specialized training data from the teacher:
- Factual: "What is the minimum freeboard for a Type A ship of 100m length?"
- Procedural: "Describe the steps for starting an auxiliary diesel engine"
- Regulatory: "Under MARPOL Annex I, when may a ship discharge oily mixtures?"
- Troubleshooting: "Engine is overheating. Possible causes and remediation?"

**Hardware/Inference/Data:** Same as C1 but organized by task type.

**Quality:** Higher task-specific accuracy than general KD.

**Proven results:** Mistral 7B (arXiv:2310.06825) showed strong performance through task-specific optimization. Orca 2 showed different reasoning strategies per task type.

**Papers:** Mistral 7B, Orca 2

**Pros:** Targeted knowledge injection for actual use cases  
**Cons:** Need to enumerate all task types in advance

**SCORE: 8/10** — Smart refinement for maritime use case.

---

## D. RL-BASED APPROACHES

### D1. DPO (Direct Preference Optimization)

**What it does:** Replaces the complex RLHF pipeline (reward model + PPO) with a simple closed-form loss function. Takes pairs of (preferred, dispreferred) responses and directly optimizes the model to prefer correct responses. Eliminates need for reward model training and RL sampling.

**How it injects domain knowledge:** Creates paired maritime responses — one correct and one incorrect — and teaches the model to distinguish between them. Example:
- Preferred: "MARPOL Annex VI regulates air pollution from ships, including SOx and NOx emissions"
- Dispreferred: "MARPOL Annex VI deals with garbage management on ships" (incorrect)

**Hardware needed:**
- Same as SFT — manageable on consumer GPUs
- Needs: A reference model (the SFT checkpoint) kept frozen
- 1.5-3B model: 1-2x A100 or equivalent

**Inference requirements:** YES mobile compatible (standard model after training).

**Quality:** Equal or better than PPO-based RLHF, much simpler. Excellent for teaching factual correctness when paired data is available.

**Data requirements:**
- Minimum: 1K-10K preference pairs for maritime domain
- Format: (prompt, preferred_response, dispreferred_response)
- Can generate using teacher model: correct answer vs. common misconception
- Smaug/DPOP (arXiv:2402.13228): Showed DPO can reduce likelihood of preferred responses — DPOP fixes this

**Proven results:**
- DPO (arXiv:2305.18290): Matched or exceeded PPO on sentiment, summarization, dialogue
- Tulu 3 (arXiv:2411.15124): SFT + DPO + RLVR pipeline, surpassed GPT-4o-mini
- SmolLM3: Used APO (variant of DPO) for final alignment
- DPOP/Smaug (arXiv:2402.13228): Fixed DPO failure mode, first open LLM to exceed 80% on Open LLM Leaderboard

**Papers:** DPO, Smaug/DPOP, Tulu 3, SmolLM3

**Pros:**
- Simple to implement (cross-entropy-like loss)
- No reward model needed
- Excellent for teaching factual accuracy through contrast
- Proven at all scales including small models
- Computationally lightweight
- SmolLM3 demonstrated with APO variant at 3B scale

**Cons:**
- Needs curated preference pairs (manual effort)
- Does NOT add new knowledge — only refines existing knowledge
- Less effective if base model lacks maritime knowledge entirely
- Must be combined with pretraining/SFT that first establishes knowledge

**SCORE: 8/10** — Critical refinement step after knowledge injection. Teaches model to prefer correct maritime answers over plausible-sounding wrong ones.

---

### D2. ORPO (Odds Ratio Preference Optimization)

**What it does:** Eliminates both the reference model AND the separate SFT stage by combining supervised learning and preference optimization into a single monolithic objective. Applies a penalty for disfavored generation styles directly during SFT.

**How it injects domain knowledge:** Simultaneously teaches the model maritime content (SFT component) and preference alignment (odds ratio component). One training stage instead of two.

**Hardware needed:** Less than DPO (no reference model needed). 1.5-3B model easily on single consumer GPU.

**Inference requirements:** YES mobile compatible.

**Quality:** Tested on Phi-2 (2.7B), LLaMA-2 (7B), Mistral (7B). Phi-2 with ORPO achieved 12.20% on AlpacaEval 2.0, surpassing models up to 13B parameters.

**Data requirements:**
- Same preference pairs as DPO
- But training is single-stage (combined SFT + alignment)

**Proven results:** ORPO (arXiv:2403.07691) — Phi-2 (2.7B) surpassed larger models on IFEval and MT-Bench.

**Papers:** ORPO (arXiv:2403.07691)

**Pros:** Simpler pipeline (one stage instead of two), no reference model, works at 2.7B scale  
**Cons:** Less fine-grained control than separate SFT→DPO pipeline

**SCORE: 7/10** — Efficient single-stage alternative. Good for resource-constrained training.

---

### D3. GRPO (Group Relative Policy Optimization)

**What it does:** DeepSeek's RL method that eliminates the need for a value (critic) model entirely. Generates multiple responses per prompt, scores them with a reward function, and optimizes the policy using group-relative advantages. Used to develop DeepSeek-R1's reasoning capabilities.

**How it injects domain knowledge:** For maritime domain, create verifiable questions with ground-truth answers. Model generates multiple answers → correct ones get positive reward → model learns to produce correct maritime knowledge.

**Hardware needed:** Higher than DPO (need to generate multiple samples per prompt). 2-4x A100 recommended for 3B model.

**Inference requirements:** YES mobile compatible (standard model after training).

**Quality:** DeepSeek-R1 demonstrated that pure RL (GRPO) can produce emergent reasoning abilities including self-reflection and verification — without any labeled data.

**Data requirements:**
- Questions with verifiable answers (factual maritime questions)
- No need for human preference labels — just correct/incorrect verification
- Can use automated grading for maritime facts

**Proven results:** DeepSeek-R1 (arXiv:2501.12948) — reasoning capabilities emerged from RL alone, then distilled into 1.5B model.

**Papers:** DeepSeek-R1, GRPO

**Pros:** No human preference data needed, emergent reasoning, works for verifiable knowledge  
**Cons:** High training cost, complex implementation, may produce unstable training

**SCORE: 7/10** — Promising for maritime factual verification but high training cost for small teams.

---

### D4. RLVR (Reinforcement Learning with Verifiable Rewards)

**What it does:** Tulu 3's approach — uses RL with automatically verifiable rewards rather than human preferences. For domains where answers can be verified (math, coding, factual Q&A), the reward comes from checking correctness.

**How it injects domain knowledge:** Create maritime questions with definitive answers → model generates responses → automated checker verifies factual correctness → model receives reward signal.

**Hardware/Inference:** Same as GRPO.

**Quality:** Tulu 3 surpassed GPT-4o-mini using SFT + DPO + RLVR pipeline.

**Data requirements:** Verifiable maritime QA — "What is the minimum UMS manning level?" Answer: checkable against regulations.

**Proven results:** Tulu 3 (arXiv:2411.15124) — comprehensive post-training recipe surpassing proprietary models.

**Papers:** Tulu 3

**Pros:** Automated reward, no human labeling, proven in multi-stage pipeline  
**Cons:** Maritime answers must be machine-verifiable (not always possible)

**SCORE: 7/10** — Good for factual maritime knowledge that can be verified automatically.

---

### D5. KTO (Kahneman-Tversky Optimization)

**What it does:** Uses prospect theory to optimize LLMs from binary signals (good/bad) rather than paired preferences. Only needs to know whether an output is desirable, not which of two is better. Directly maximizes human utility function.

**How it injects domain knowledge:** Rate maritime model outputs as "desirable" or "undesirable" — no need for pairwise comparisons. Simpler labeling process.

**Hardware/Inference requirements:** Same as DPO. YES mobile compatible.

**Quality:** Matches or exceeds DPO performance from 1B to 30B scale.

**Proven results:** KTO (arXiv:2402.01306) — works at 1B scale, matching DPO with simpler data.

**Papers:** KTO (arXiv:2402.01306)

**Pros:** Simplest data requirement (binary labels), works at 1B scale  
**Cons:** Same limitation as DPO — refines, doesn't add knowledge

**SCORE: 7/10** — Easiest alignment method to implement. Binary labels for maritime answers.

---

### D6. Self-Play Fine-Tuning (SPIN)

**What it does:** The model plays against itself — current model generates responses, and the training objective is to distinguish model-generated responses from ground-truth human responses. Iterative self-improvement without an external teacher.

**How it injects domain knowledge:** Model learns to match ground-truth maritime answers by competing against its own previous generations. Progressively improves through self-play iterations.

**Hardware/Inference:** Same as DPO.

**Data requirements:** Only needs ground-truth responses (no preference pairs). Maritime textbook answers serve as ground truth.

**Proven results:** SPIN-style self-play shows improvement over standard SFT in multiple iterations.

**Papers:** SPIN (arXiv:2402.13228 — related), Self-Rewarding LMs

**Pros:** No external teacher or reward model needed  
**Cons:** Limited by initial model quality, may converge to local optima

**SCORE: 6/10** — Interesting but less effective than teacher-based distillation for domain knowledge.

---

## E. DATA-CENTRIC APPROACHES

### E1. Synthetic Data Generation from Textbooks

**What it does:** Uses a powerful LLM (GPT-4, Claude) to read maritime textbook content and generate diverse training data: Q&A pairs, multiple-choice questions, scenario-based problems, fill-in-the-blank, true/false, case studies, and conversational dialogues — all grounded in the textbook content.

**How it injects domain knowledge:** The textbook content is TRANSFORMED into various training formats that are more effective for model learning than raw text. This is the core phi-1 insight: "textbook quality" synthetic data is more effective than raw web data for training.

**Hardware needed:** Only API access to a strong teacher (GPT-4, Claude). No GPU needed for generation.

**Inference requirements:** N/A (data generation, not inference method).

**Quality:** This is arguably THE most important data-centric technique. phi-1 proved that 1B synthetic tokens of textbook quality outperformed 100B tokens of web data.

**Data requirements:**
- Input: Maritime textbook text (OCR from EPUB/DJVU)
- Output: 50K-500K synthetic training examples
- Format: Mix of instruction-following, QA, multiple choice, reasoning chains
- Cost: ~$50-500 in API calls depending on volume

**Proven results:**
- phi-1 (arXiv:2306.11644): 1.3B model trained on synthetic textbooks achieved 50.6% HumanEval — "textbook quality" data key insight
- phi-1.5 (arXiv:2309.05463): Extended to natural language reasoning with synthetic data
- TinyStories (arXiv:2305.07759): Sub-10M parameter models producing coherent text when trained on synthetic stories
- LAB (arXiv:2403.01081): Taxonomy-guided synthetic data generation, competitive with GPT-4-generated data
- SmolLM3: Mid-training on 35B tokens sourced from reasoning datasets; SFT synthetic data from Qwen3-32B

**Papers:** phi-1, phi-1.5, TinyStories, LAB, SmolLM3

**Pros:**
- Transforms static textbook content into dynamic training data
- Can generate unlimited volume from limited source material
- Different formats (QA, MCQ, scenarios) improve coverage
- Proven to be THE most effective approach for small model training
- Low cost compared to human annotation
- Textbooks provide authoritative, verified knowledge

**Cons:**
- Quality depends on teacher model's understanding of maritime domain
- May introduce teacher model errors/hallucinations
- Need quality filtering of generated data
- Maritime-specific terminology may challenge general LLMs

**SCORE: 10/10** — The SINGLE most important technique. This turns your maritime textbooks into a massive, high-quality training dataset. phi-1 proved this exact approach works.

---

### E2. Data Quality Filtering / Data Selection

**What it does:** Automatically scores and selects the highest-quality training data from a larger pool. Uses metrics like complexity, diversity, and quality to select the most educational examples.

**How it injects domain knowledge:** Ensures only the best maritime training examples are used — removing duplicates, errors, trivial examples, and overly complex examples. Quality >> Quantity.

**Hardware needed:** Minimal (scoring/filtering can run on CPU).

**Quality:** DEITA (arXiv:2312.15685) achieved SOTA with only 6K training examples — 10x less than baselines.

**Data requirements:** Input: Large pool of candidate training data. Output: Curated subset.

**Proven results:**
- DEITA: 6K SFT + 10K DPO samples achieved 7.55 MT-Bench, 90.06% AlpacaEval
- Measured data across complexity, quality, diversity dimensions

**Papers:** DEITA (arXiv:2312.15685)

**Pros:** Dramatically reduces training data needed, improves model quality  
**Cons:** Requires the large pool first, filtering heuristics may discard important edge cases

**SCORE: 8/10** — Critical for maximizing the value of limited maritime training data.

---

### E3. Curriculum Learning for Data Ordering

**What it does:** Orders training data from easy to hard, matching how humans learn. For maritime: basic terminology → component descriptions → system interactions → troubleshooting → complex regulatory scenarios.

**How it injects domain knowledge:** Progressive knowledge building mirrors textbook chapter ordering. The model develops foundational understanding before tackling complex topics.

**Data requirements:** Same data but with difficulty/complexity labels.

**Proven results:** SmolLM3 3-stage training, phi-series progressive training.

**Pros:** Better knowledge retention, less catastrophic forgetting  
**Cons:** Need to categorize all training data by difficulty

**SCORE: 7/10** — Good enhancement, especially with limited maritime data.

---

### E4. Data Mixing / Domain-General Replay

**What it does:** During domain-specific training, mixes in a portion (5-20%) of general-purpose training data to prevent catastrophic forgetting of general language abilities while absorbing maritime knowledge.

**How it injects domain knowledge:** Maintains balance between domain specialization and general capability. The model becomes maritime-expert while retaining ability to speak coherent English, follow instructions, and reason generally.

**Data requirements:** Maritime domain data + general instruction-following data (alpaca, dolly, etc.)

**Proven results:** Standard practice in all domain adaptation work. SmolLM3 maintained web data across all stages.

**Pros:** Prevents catastrophic forgetting, maintains general abilities  
**Cons:** Dilutes domain-specific training signal slightly

**SCORE: 8/10** — Essential practice for any domain-specific training.

---

### E5. LAB (Large-Scale Alignment for ChatBots) — Taxonomy-Guided Synthetic Data

**What it does:** Uses a structured taxonomy to systematically generate synthetic training data. A taxonomy tree defines all knowledge domains and subdomains, then synthetic data is generated to cover each node. Multi-phase tuning framework reduces reliance on expensive annotations.

**How it injects domain knowledge:** Create a maritime knowledge taxonomy:
```
Maritime Engineering
├── Ship Construction
│   ├── Hull types
│   ├── Materials
│   ├── Structural members
│   └── ...
├── Marine Propulsion
│   ├── Diesel engines
│   ├── Turbochargers
│   └── ...
├── Maritime Regulations
│   ├── MARPOL
│   ├── SOLAS
│   ├── STCW
│   └── BWM Convention
└── ...
```
Then systematically generate training data for each node.

**Proven results:** LAB (arXiv:2403.01081) — competitive with GPT-4-generated synthetic data, scalable.

**Pros:** Systematic coverage of entire domain, no gaps  
**Cons:** Need to build the taxonomy first

**SCORE: 9/10** — Excellent for ensuring complete coverage of maritime knowledge.

---

## F. ARCHITECTURE MODIFICATION APPROACHES

### F1. Post-Training Quantization (PTQ) — GPTQ, AWQ, GGUF

**What it does:** Reduces model precision from FP16/BF16 to INT4/INT3/INT2 after training. GPTQ uses one-shot weight quantization with calibration data. AWQ (Activation-Aware Weight Quantization) preserves salient weights. GGUF is llama.cpp's quantization format optimized for CPU inference.

**How it injects domain knowledge:** Doesn't inject knowledge — PRESERVES knowledge while making models mobile-deployable. A 3B model at Q4_K_M goes from ~6GB to ~2GB.

**Hardware needed:** Minimal — quantization runs on consumer hardware.

**Inference requirements:**
- 1.5B @ Q4: ~1GB RAM — runs on ANY phone
- 3B @ Q4: ~1.8-2GB RAM — runs on phones with 4GB+ RAM
- llama.cpp / MLC-LLM provide mobile-optimized inference

**Quality:** Q4 (4-bit) typically retains 95-99% of FP16 quality. Domain-specific knowledge well preserved.

**Data requirements:** Small calibration dataset (128-1024 samples of domain text).

**Proven results:** Virtually all mobile LLM deployments use 4-bit quantization. llama.cpp GGUF is the de facto standard.

**Papers:** GPTQ, AWQ, llama.cpp documentation

**Pros:** ESSENTIAL for mobile deployment, minimal quality loss at Q4  
**Cons:** Below Q4 (Q3, Q2), noticeable quality degradation

**SCORE: 9/10** — Non-negotiable for mobile deployment. Apply after all training is complete.

---

### F2. BitNet b1.58 (1-bit LLMs with Ternary Weights)

**What it does:** Replaces all standard linear layers with BitLinear layers where every weight is {-1, 0, 1}. This is NOT post-training quantization — it's training from scratch with ternary weights. Achieves par performance with FP16 models at same size while enabling massive speedups.

**How it injects domain knowledge:** Train a maritime-domain model from scratch with ternary weights. The knowledge is encoded in the ternary weight patterns.

**Hardware needed:**
- Training: Significant (need to train from scratch)
- BitNet b1.58 2B4T (arXiv:2504.12285) was trained on 4T tokens

**Inference requirements:** 
- 2B model: Dramatically reduced memory (ternary weights = ~0.5GB)
- Energy consumption reduced by ~70%
- CPU-only inference viable at high speed
- IDEAL for mobile phones

**Quality:** BitNet b1.58 2B4T matches leading 2B full-precision models on benchmarks covering language understanding, math, coding, and conversation.

**Data requirements:** Need to train from scratch — requires trillions of tokens (or start from BitNet-compatible framework).

**Proven results:** BitNet b1.58 2B4T (arXiv:2504.12285): 2B model, 4T tokens, matches full-precision peers. BitNet b1.58 (arXiv:2402.17764): Proposed the ternary weight scheme.

**Papers:** BitNet (arXiv:2310.08659 — original), BitNet b1.58 (arXiv:2402.17764), BitNet b1.58 2B4T (arXiv:2504.12285)

**Pros:**
- ULTIMATE mobile efficiency — ternary weights enable specialized hardware
- Near-zero multiplication cost (add/subtract only)
- Matches FP16 quality at 2B scale
- Released weights and inference code for GPU and CPU

**Cons:**
- Must train from scratch (cannot convert existing models)
- Very high training cost (4T tokens for 2B model)
- Limited ecosystem — not yet supported by standard frameworks for fine-tuning
- Cannot easily do domain continued pretraining on BitNet models yet

**SCORE: 7/10** — Future-looking approach perfect for mobile. Currently limited by inability to easily fine-tune for maritime domain. Outstanding for new pre-training if resources available.

---

### F3. LoftQ (LoRA-Fine-Tuning-Aware Quantization)

**What it does:** Simultaneously quantizes an LLM AND finds a proper low-rank initialization for subsequent LoRA fine-tuning. The quantization is specifically optimized to minimize the gap that LoRA needs to bridge, resulting in better fine-tuning outcomes on quantized models.

**How it injects domain knowledge:** Quantize base model → initialize LoRA to compensate for quantization error → fine-tune LoRA on maritime data. The quantization-aware initialization means less information loss.

**Hardware needed:** Same as QLoRA for training. Single consumer GPU.

**Inference requirements:** Highly mobile-friendly (quantized model + merged LoRA).

**Quality:** Significantly outperforms standard quantize-then-LoRA, especially at aggressive quantization (2-bit, 2/4-bit mixed).

**Proven results:** LoftQ (arXiv:2310.08659): Superior to QLoRA at 2-bit and mixed precision regimes.

**Papers:** LoftQ (arXiv:2310.08659)

**Pros:** Better quality at extreme quantization, designed for downstream fine-tuning  
**Cons:** More complex than QLoRA setup

**SCORE: 7/10** — Excellent for extreme mobile optimization (2-bit deployment).

---

### F4. Mixture of Experts (MoE) Architecture

**What it does:** Replaces dense feed-forward layers with multiple "expert" sub-networks and a gating mechanism. Only a subset of experts activate per token, giving the model more total parameters (knowledge capacity) with fewer active parameters per inference step.

**How it injects domain knowledge:** Different experts can specialize in different maritime sub-domains (propulsion, regulations, construction, safety). The gating mechanism routes maritime questions to the relevant experts.

**Hardware needed:** Training requires more memory (all experts must be in memory). DeepSeek-V2's 236B total / 21B active is an extreme example.

**Inference requirements:**
- Total parameters are larger BUT active parameters per token are smaller
- A 3B MoE with 1B active could work on mobile
- Memory for full model weights is higher than dense equivalent
- Current mobile frameworks have limited MoE support

**Quality:** Can store MORE knowledge in the same active compute budget.

**Data requirements:** Standard training data. Experts specialize automatically during training.

**Proven results:** DeepSeek-V2 (arXiv:2405.04434): 236B total, 21B active — top performance with efficient inference. Mixtral 8x7B: MoE outperforming LLaMA-2-70B.

**Papers:** DeepSeek-V2, Mixtral

**Pros:** Higher knowledge capacity per inference FLOP  
**Cons:** Higher total memory, limited mobile framework support, complex to train

**SCORE: 5/10** — Promising concept but mobile deployment of MoE is still challenging. Total model memory is the bottleneck for phones.

---

### F5. Structured Pruning

**What it does:** Removes entire neurons, attention heads, or layers from the model based on importance scores. Reduces model size while preserving most capabilities.

**How it injects domain knowledge:** Prune a larger domain-adapted model down to mobile size. Keep parameters most important for maritime knowledge, remove least important ones.

**Hardware/Inference:** Pruned model is smaller and faster — very mobile friendly.

**Quality:** 20-30% pruning typically retains 90-95% quality. Beyond 40%, quality drops significantly.

**Data requirements:** Small calibration dataset for importance scoring.

**Proven results:** Wanda, SparseGPT — demonstrated effective pruning of LLMs.

**Pros:** Reduces model size directly, can target non-maritime parameters  
**Cons:** Difficult to determine which parameters encode which knowledge, irreversible

**SCORE: 5/10** — Limited usefulness when starting with already-small 1-3B models.

---

### F6. Adapters (Bottleneck Adapters, Prefix Tuning, Prompt Tuning)

**What it does:** Adds small trainable modules (bottleneck layers, prefix tokens, or soft prompts) to a frozen model. Unlike LoRA which modifies existing weights, adapters add new parameters.

**Variants:**
- **Bottleneck Adapters:** Small MLP layers inserted between transformer layers
- **Prefix Tuning:** Learnable prefix tokens prepended to keys/values in attention
- **Prompt Tuning:** Learnable continuous vectors prepended to input
- **IA³:** Learned vectors that rescale keys, values, and FFN outputs

**How it injects domain knowledge:** New adapter parameters store maritime-specific information. The frozen base retains general knowledge, adapters add domain expertise.

**Hardware needed:** Very low — only adapter parameters are trained (0.1-1% of model).

**Inference requirements:** Small overhead from adapter modules. Generally mobile compatible after optimization.

**Quality:** Less effective than LoRA for LLMs. More architectural overhead than LoRA at inference.

**Data requirements:** Same as SFT.

**Proven results:** Widely used in pre-LLM era (BERT adapters). Less common for modern LLMs where LoRA dominates.

**Papers:** Adapter survey literature, IA³

**Pros:** Modular, multiple adapters for sub-domains, frozen base model  
**Cons:** Inference overhead (unlike LoRA which merges), generally inferior to LoRA for LLMs

**SCORE: 5/10** — LoRA is strictly superior for this use case. Adapters add inference cost.

---

## G. KNOWLEDGE EDITING/INJECTION APPROACHES

### G1. Knowledge Neurons Identification and Editing

**What it does:** Identifies which specific neurons in the network store particular factual knowledge (e.g., "the minimum freeboard for a Type A vessel is..."). Once identified, these "knowledge neurons" can be directly edited to update or inject facts.

**How it injects domain knowledge:** Locate neurons responsible for maritime facts → directly modify their activation patterns to encode correct maritime information. Surgical knowledge injection.

**Hardware needed:** Forward/backward passes for knowledge attribution. Standard GPU.

**Inference requirements:** Model size unchanged — YES mobile compatible.

**Quality:** VERY NARROW — good for correcting specific facts but cannot inject broad domain knowledge. Not suitable for teaching entire textbooks.

**Data requirements:** Specific fact triplets (subject, relation, object): "MARPOL Annex I → regulates → oil pollution"

**Proven results:** Research on knowledge neurons in LLMs shows that factual knowledge is localized, but editing approaches remain fragile and don't scale well.

**Papers:** Knowledge neurons research, ROME, MEMIT

**Pros:** Surgical precision for specific facts  
**Cons:** Doesn't scale to thousands of facts, fragile, may break model coherence

**SCORE: 3/10** — Not practical for injecting entire textbook knowledge. Useful only for correcting specific errors after main training.

---

### G2. ROME (Rank-One Model Editing) and MEMIT

**What it does:** ROME edits individual factual associations by modifying a single weight matrix using a rank-one update. MEMIT extends this to edit thousands of facts simultaneously.

**How it injects domain knowledge:** Could theoretically inject maritime facts as (subject, relation, object) triples. Edit model weights to encode: "BWM Convention → was adopted in → 2004", "SOLAS Chapter II-1 → covers → construction requirements", etc.

**Hardware needed:** Minimal — just matrix computations on local GPU.

**Inference requirements:** YES mobile compatible (model stays same size).

**Quality:** MEMIT can edit thousands of facts, but:
- Quality degrades with number of edits
- May introduce inconsistencies
- Cannot inject procedural or reasoning knowledge

**Data requirements:** Structured knowledge triples.

**Proven results:** MEMIT demonstrated editing up to 10K facts. Quality deteriorates beyond that.

**Pros:** Direct fact injection, no training required  
**Cons:** Cannot encode reasoning, limited to factual triples, quality degrades at scale

**SCORE: 4/10** — Interesting for supplementing, but not viable as primary method for textbook-scale knowledge.

---

### G3. Model Merging

**What it does:** Combines weights from multiple models (e.g., a maritime-specialized model and a general-purpose model) using techniques like linear interpolation, SLERP, TIES, or DARE. No additional training required.

**How it injects domain knowledge:** Train separate domain-specific models → merge with general model to get best of both worlds. Example: Merge a maritime-CPT model with the original base model at 0.7/0.3 ratio.

**Hardware needed:** Only CPU — simple weight arithmetic.

**Inference requirements:** Standard merged model — YES mobile compatible.

**Quality:** SmolLM3 used model merging as a POST-training step: APO-trained model merged with mid-training checkpoint at 0.9/0.1 ratio to recover long-context performance.

**Data requirements:** Two or more trained model checkpoints.

**Proven results:** SmolLM3 (merging APO + mid-training for long-context recovery), numerous community merges on HuggingFace.

**Papers:** SmolLM3 blog, MergeKit, TIES-Merging, DARE

**Pros:** No training, combine domain expertise with general capability, free to try  
**Cons:** Unpredictable results, may introduce conflicts, limited theoretical basis

**SCORE: 6/10** — Useful auxiliary technique for balancing domain expertise vs. general ability.

---

## H. HYBRID / COMBINED APPROACHES

### H1. The SmolLM3 Pipeline (RECOMMENDED REFERENCE PIPELINE)

**What it does:** The complete SmolLM3 training pipeline provides the gold standard for building a small, capable model:

1. **Architecture Design:** GQA, NoPE (every 4th layer), intra-document masking, tied embeddings
2. **3-Stage Pretraining:** 11T tokens with evolving data mixtures
3. **Mid-Training — Long Context:** 100B tokens for context extension (4K→32K→64K)
4. **Mid-Training — Reasoning:** 35B tokens of reasoning traces (4 epochs = 140B)
5. **SFT:** 1.8B tokens (1B non-reasoning + 0.8B reasoning), 4 epochs
6. **Alignment (APO):** Preference optimization with anchored DPO variant
7. **Model Merging:** Combine APO model with mid-training checkpoint
8. **Quantization:** GGUF for mobile deployment

**How it injects domain knowledge:** Each stage contributes:
- Pretraining: General + domain text → factual knowledge
- Mid-training: Reasoning patterns → problem-solving ability
- SFT: Instruction following → correct response format
- APO: Preference alignment → accurate answers over wrong ones
- Merging: Balance domain vs. general

**This is the template for our maritime chatbot pipeline.**

**SCORE: 10/10** — The gold standard. Adapt this pipeline for maritime domain.

---

### H2. The DeepSeek-R1 Distillation Pipeline

**What it does:**
1. Train a large model (671B) using RL (GRPO) to develop reasoning
2. Distill reasoning traces into small models (1.5B-70B)
3. Small distilled models inherit reasoning ability

**For maritime adaptation:**
1. Use a **strong local open-weight model** as the "teacher" (no paid APIs)
2. Generate maritime reasoning traces: "Let me think about this step by step. The MARPOL regulation states... Given the vessel's flag state... Therefore..."
3. Distill into our 1.5-3B maritime model

**Quality:** DeepSeek-R1-Distill-Qwen-1.5B showed remarkable reasoning at 1.5B scale.

**SCORE: 9/10** — Proven pipeline for transferring reasoning to tiny models.

---

### H3. The Orca 2 Pipeline (Teaching Reasoning Strategies)

**What it does:** Instead of imitation learning (match teacher outputs), Orca 2 teaches small models DIFFERENT reasoning strategies for different task types:
- Step-by-step reasoning for complex problems
- Recall-then-generate for knowledge questions
- Recall-reason-generate for analytical questions
- Direct answer for simple factual queries

**For maritime adaptation:**
- "What is the minimum freeboard?" → Direct answer
- "Explain why a ship might develop corrosion at the waterline" → Recall-reason-generate
- "A marine diesel engine is overheating after maintenance. Diagnose." → Step-by-step reasoning

**Quality:** Orca 2 (7B, 13B) surpassed 5-10x larger models on complex reasoning.

**SCORE: 9/10** — Teaching the maritime model WHEN to use different strategies is key.

---

### H4. The Complete Recommended Pipeline for Maritime Chatbot

**Combining the best of all approaches:**

**Phase 1: Data Preparation (E1 + E2 + E5)**
- Convert all maritime textbooks (EPUB/DJVU) to clean text
- Use GPT-4/Claude to generate synthetic QA, MCQ, scenarios, reasoning traces from textbook content
- Build taxonomy of maritime knowledge (LAB approach)
- Apply quality filtering (DEITA approach)
- Generate preference pairs (correct vs. incorrect maritime answers)
- Target: 200M+ tokens of raw text, 50K+ instruction pairs, 10K+ preference pairs

**Phase 2: Base Model Selection**
- SmolLM3-3B-Base or Qwen2.5-1.5B as starting model
- Choose based on mobile RAM constraints

**Phase 3: Continued Pretraining (A1 + A2)**
- Continue pretraining on maritime textbook text
- Use curriculum: basic terminology → technical details → complex scenarios
- Mix 80% maritime + 20% general data to prevent forgetting
- Apply NEFTune during training
- Duration: 2-5 days on 1-2x A100

**Phase 4: Knowledge Distillation SFT (C1 + C2 + B1)**
- Fine-tune on synthetic QA + reasoning traces from teacher
- Use full SFT (not LoRA) for maximum knowledge absorption
- Use NEFTune augmentation
- SmolLM3-style: 4 epochs over SFT dataset

**Phase 5: Preference Alignment (D1)**
- DPO or APO on maritime preference pairs
- Correct maritime answers vs. common misconceptions
- 1-2K steps of alignment

**Phase 6: Final Optimization (F1 + G3)**
- Model merging if needed (balance domain vs. general)
- Quantization to Q4_K_M for mobile deployment
- Test on mobile device with llama.cpp / MLC-LLM

**SCORE: 10/10** — This is the recommended end-to-end pipeline.

---

## I. PRE-TRAINING FROM SCRATCH APPROACHES

### I1. Pre-training a Domain-Specific Model from Scratch

**What it does:** Train a new 1-3B transformer model entirely from scratch on a curated mixture that heavily emphasizes maritime content alongside general text.

**How it injects domain knowledge:** Maritime content comprises 30-50% of training data from the start, deeply embedding domain knowledge into all model parameters.

**Hardware needed:**
- SUBSTANTIAL: 8-64x A100 GPUs for weeks to months
- SmolLM3 needed 384 H100 GPUs for 24 days for 11T tokens
- For smaller data (100B-500B tokens), could use 8x A100 for 1-2 weeks

**Inference requirements:** Same as any model of that size — YES mobile compatible after quantization.

**Quality:** Potentially highest quality but requires massive data and compute. Not practical unless you have significant resources.

**Data requirements:**
- Need 100B-1T+ tokens total
- Maritime content may only provide 100M-500M tokens
- Need to pad with general text data (FineWeb, DCLM, etc.)

**Proven results:**
- LLaMA (arXiv:2302.13971): Trained 7B-65B on public data, proved open models can compete
- phi-1 (arXiv:2306.11644): Only 1.3B params, trained on 7B tokens of textbook quality data
- SmolLM3: 3B, 11T tokens on 384 H100s
- BitNet b1.58 2B4T: 2B, 4T tokens

**Papers:** LLaMA, phi-1, phi-1.5, SmolLM3

**Pros:** Deepest possible knowledge integration, optimized from the ground up  
**Cons:** Extremely expensive, needs huge dataset, existing pretrained models are "good enough" to start from

**SCORE: 4/10** — Overkill. Continued pretraining from an existing base model achieves 90% of the benefit at 1/100th the cost.

---

### I2. TinyStories-Style Domain-Specific Pre-training

**What it does:** Inspired by TinyStories (arXiv:2305.07759) which showed that even sub-10M parameter models can produce coherent text when trained on SYNTHETIC stories. Apply the same principle: generate "TinyMaritime" — a synthetic corpus of simple maritime educational content.

**How it injects domain knowledge:** Use GPT-4 to generate thousands of simple maritime educational passages, explanations, and dialogues, then train (or continue-pretrain) on this synthetic corpus.

**Hardware needed:** Low (synthetic corpus is small).

**Quality:** TinyStories showed that DATA QUALITY compensates for model size. The same principle should apply to maritime domain.

**Proven results:** TinyStories (arXiv:2305.07759): Sub-28M parameter models producing fluent, consistent, multi-paragraph stories with grammar and reasoning.

**SCORE: 7/10** — Interesting approach for very small (sub-1B) models.

---

## J. OTHER APPROACHES

### J1. Embedding Tuning / Vocabulary Extension

**What it does:** Adds new tokens to the vocabulary for domain-specific terminology (e.g., "MARPOL", "STCW", "forecastle", "bulkhead", "scantlings") and trains their embeddings while optionally fine-tuning existing embeddings.

**How it injects domain knowledge:** Maritime terminology gets dedicated embeddings, improving the model's representation of domain concepts. More efficient tokenization of maritime text.

**Proven results:** Vocabulary sharing research (arXiv:2311.09071) showed LLMs possess more multilingual capability than expected through shared vocabulary. SmolLM3 used LLaMA 3.2 tokenizer with 128K vocabulary.

**Quality:** Marginal improvement — modern tokenizers (128K vocab) already handle most technical terms adequately.

**SCORE: 4/10** — Minimal impact for maritime domain since modern tokenizers are already extensive.

---

### J2. Test-Time Compute Scaling (Extended Thinking)

**What it does:** At inference time, allows the model to "think longer" by generating longer reasoning chains. SmolLM3 supports `/think` and `/no_think` modes. The model produces intermediate reasoning before the final answer.

**How it injects domain knowledge:** Doesn't inject knowledge — enables better USE of existing knowledge through reasoning.

**Inference requirements:** Higher latency (more tokens generated), more memory for KV cache. May be too slow for mobile in complex scenarios.

**Quality:** SmolLM3 saw massive improvements with thinking: AIME 2025: 36.7% vs 9.3%, LiveCodeBench: 30.0% vs 15.2%.

**Proven results:** SmolLM3, DeepSeek-R1, Qwen3 all support dual-mode inference.

**SCORE: 6/10** — Good for complex maritime reasoning (troubleshooting), but adds latency on mobile.

---

### J3. Tool Calling / Agentic Architecture

**What it does:** The model is trained to call external tools (calculators, lookup tables, unit converters) when needed. SmolLM3 supports tool calling with XML and Python tool formats.

**How it injects domain knowledge:** Maritime lookup tables (stability tables, tonnage calculations) can be provided as tools rather than memorized.

**Inference requirements:** Needs runtime tool execution — adds complexity on mobile.

**SCORE: 4/10** — Adds complexity for mobile deployment. Better to embed knowledge directly.

---

### J4. Context Distillation

**What it does:** Fine-tune the model so it behaves AS IF a long system prompt with maritime knowledge was provided, even when no prompt is given. The "system prompt behavior" is baked into the weights.

**How it injects domain knowledge:** Train the model with: "You are a maritime engineering expert with knowledge of MARPOL, SOLAS, STCW..." as system prompt → the model internalizes this behavior.

**Quality:** Good for setting domain-specific behavior patterns.

**Proven results:** Used by GPT-4, Claude for personality/capability calibration.

**SCORE: 7/10** — Good supplementary technique for establishing maritime expert persona.

---

### J5. Activation Editing / Representation Engineering

**What it does:** Identifies directions in activation space that correspond to specific behaviors or knowledge domains. At inference time, adds vectors along these directions to steer model outputs.

**How it injects domain knowledge:** Find the "maritime knowledge" direction in activation space, amplify it during inference. Research-stage technique.

**Quality:** Research-stage. Not proven for knowledge injection at scale.

**SCORE: 3/10** — Too experimental for production use.

---

## FINAL RANKING & RECOMMENDED PIPELINE

### Top 10 Methods by Score (for Maritime Textbook Knowledge on Mobile, No RAG):

| Rank | Method | Score | Category | Critical? |
|------|--------|-------|----------|-----------|
| 1 | **Synthetic Data from Textbooks (E1)** | 10/10 | Data-Centric | YES — Foundation |
| 2 | **Combined Pipeline (H4)** | 10/10 | Hybrid | YES — Meta-approach |
| 3 | **SmolLM3 Pipeline Reference (H1)** | 10/10 | Hybrid | YES — Template |
| 4 | **Continued Pretraining (A1)** | 9/10 | Cont. Pretrain | YES — Core |
| 5 | **Curriculum Pretraining (A2)** | 9/10 | Cont. Pretrain | YES — Enhancement |
| 6 | **Knowledge Distillation from Teacher (C1)** | 9/10 | KD | YES — Core |
| 7 | **Reasoning-Trace Distillation (C2)** | 9/10 | KD | YES — Core |
| 8 | **LAB Taxonomy-Guided Data (E5)** | 9/10 | Data-Centric | YES — Coverage |
| 9 | **Post-Training Quantization (F1)** | 9/10 | Architecture | YES — Deployment |
| 10 | **DeepSeek-R1 Distillation Pipeline (H2)** | 9/10 | Hybrid | RECOMMENDED |

### The Concrete Action Plan:

```
STEP 1: DATA INFRASTRUCTURE (Week 1-2)
├── Convert EPUB/DJVU maritime textbooks to clean text
├── Build maritime knowledge taxonomy (LAB approach)
├── Generate 50K-200K synthetic QA pairs via **local teacher** (E1; no paid APIs)
├── Generate reasoning traces for complex questions (C2)
├── Create 5K-10K preference pairs (correct vs wrong) (D1)
├── Apply quality filtering (E2/DEITA)
└── Target: 200M+ tokens raw text, 50K+ instruction pairs

STEP 2: MODEL SELECTION (Week 2)
├── Primary: SmolLM3-3B-Base (best at 3B scale)
├── Alternative: Qwen2.5-1.5B (if <3GB RAM required)
└── Benchmark base model on maritime QA before any training

STEP 3: CONTINUED PRETRAINING (Week 3-4)
├── Pretrain on maritime text corpus (80% domain + 20% general)
├── Use curriculum ordering (basic → advanced)
├── Apply NEFTune
├── 2-5 days on 1-2x A100 (or cloud equivalent)
└── Evaluate: maritime QA improvement over base

STEP 4: SFT WITH DISTILLATION (Week 4-5)
├── Full SFT on synthetic QA + reasoning traces
├── Use full fine-tuning (not LoRA) for max knowledge absorption
├── Apply NEFTune
├── Mix maritime SFT data with general instruction data (80/20)
├── 4 epochs following SmolLM3 recipe
└── Evaluate: conversational maritime QA quality

STEP 5: PREFERENCE ALIGNMENT (Week 5)
├── DPO or APO on maritime preference pairs
├── Correct answers vs. common misconceptions
├── Brief training (1-2K steps)
└── Evaluate: factual accuracy improvement

STEP 6: OPTIMIZE FOR MOBILE (Week 5-6)
├── Optional: Model merging (domain model + base for balance)
├── Quantize to Q4_K_M GGUF format
├── Test on mobile device (llama.cpp / MLC-LLM)
├── Benchmark: latency, memory, quality
└── Deploy

TOTAL TIMELINE: ~6 weeks
COMPUTE BUDGET: 1-2x A100 for 2-3 weeks + $200-500 API costs
```

### Key References Summary:

| Paper | Relevance |
|-------|-----------|
| phi-1 "Textbooks Are All You Need" | Core thesis: textbook-quality data >> web data for small models |
| phi-1.5 | Extended to natural language reasoning |
| SmolLM3 blog | Complete 3B model recipe: architecture + 3-stage pretraining + mid-training + SFT + APO + merging |
| DeepSeek-R1 | Reasoning distillation into 1.5B model |
| Orca 2 | Teaching small LMs multiple reasoning strategies |
| GKD | On-policy distillation addressing train-test mismatch |
| DPO | Simple preference optimization for factual accuracy |
| ORPO | Monolithic SFT + preference (tested on Phi-2 2.7B) |
| LoRA/QLoRA | Memory-efficient fine-tuning (use for SFT step if GPU-constrained) |
| "LoRA Learns Less" | CRITICAL FINDING: LoRA is inferior to full FT for knowledge injection |
| NEFTune | Free quality boost: add noise to embeddings during training |
| DEITA | 6K samples can match 60K+ with proper data selection |
| LAB | Taxonomy-guided synthetic data generation |
| TinyStories | Sub-10M models can produce coherent text with quality data |
| LLaMA | Open pretraining with public datasets |
| Llama 3 | Large-scale foundation model recipe |
| BitNet b1.58 2B4T | 1-bit 2B model matching full-precision, ultra-efficient for mobile |
| LoftQ | Better quantization for downstream fine-tuning |
| Tulu 3 | SFT + DPO + RLVR complete recipe, beat GPT-4o-mini |
| DPOP/Smaug | Fixed DPO failure modes |
| KTO | Binary-signal alignment, works at 1B scale |
| Qwen2.5-1M | Long context techniques (if needed for future) |

---

*This research document is comprehensive and covers ALL major methods for injecting domain knowledge into small language models without RAG. The recommended approach combines continued pretraining on maritime text, synthetic data generation from textbooks, knowledge distillation from teacher models, and preference alignment — following the proven SmolLM3 and DeepSeek-R1 recipes adapted for the maritime domain.*
