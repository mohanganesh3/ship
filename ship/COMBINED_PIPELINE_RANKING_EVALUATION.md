# RANKING EVALUATION: The Full Pipeline — CPT + Synthetic SFT + Knowledge Distillation from Large Teacher

**Approach Under Evaluation:** A multi-stage pipeline combining Continued Pretraining (CPT) on raw maritime text → Synthetic data generation by large teacher → SFT on synthetic Q&A pairs → DPO/GRPO alignment → Model merging → Quantization to GGUF. This mirrors the documented recipes of Phi-1/3, Orca 2, SmolLM3, and DeepSeek-R1-Distill.

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B parameters  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android, fully offline  

---

## RESEARCH BASIS

This evaluation is grounded in deep analysis of the foundational papers that define each stage of this pipeline:

| Paper / Source | Key Finding for This Combined Pipeline |
|---|---|
| **Phi-1 "Textbooks Are All You Need"** (arXiv:2306.11644) | 1.3B model achieves 50.6% HumanEval with only 7B tokens (6B filtered web + 1B synthetic GPT-3.5 textbooks). **Core principle this pipeline is built on:** data quality >> data quantity. Synthetic "textbook-quality" data can substitute for 100x web data. The synthetic data was used for *pretraining*, and a separate "CodeExercises" dataset was used for fine-tuning — a two-stage process. |
| **Phi-3 Technical Report** (arXiv:2404.14219) | 3.8B model rivals GPT-3.5. Runs on iPhone 14 at 12+ tok/s in 4-bit (1.8GB). Uses heavily filtered web + synthetic data for pretraining, then SFT + DPO for post-training. **CRITICAL ADMISSION:** *"The model simply does not have the capacity to store too much factual knowledge"* — recommends search augmentation for factual queries. This is a 3.8B model trained on 3.3T tokens. Our 1-3B model on 50M tokens will be far more constrained. |
| **Orca 1** (arXiv:2306.02707) | 13B model trained on GPT-4 explanation traces outperforms Vicuna-13B by >100% on BBH. Key insight: learn reasoning PROCESSES from the teacher, not just answers. Progressive learning: GPT-4 responses for complex tasks, ChatGPT for simpler ones. |
| **Orca 2** (arXiv:2311.11045) | Teaches small LMs (7B, 13B) to use DIFFERENT reasoning strategies per task type — step-by-step, recall-then-generate, recall-reason-generate, direct answer. Surpasses 5-10x larger models. **Critical for this pipeline:** small LMs should NOT just imitate teacher outputs. They should learn WHEN to use each strategy. Orca 2 was 7B minimum — no results at 1-3B. |
| **SmolLM3** (HuggingFace blog, July 2025) | 3B model, 11T pretraining tokens in 3 stages, then mid-training for long context + reasoning (35B tokens from OpenThoughts3 + Nemotron), then SFT (1.8B tokens, synthetic from Qwen3-32B), then APO alignment, then model merging. **THIS IS THE MOST DIRECTLY RELEVANT REFERENCE.** It validates the entire multi-stage pipeline at 3B scale. Key detail: SFT used 12 non-reasoning + 10 reasoning datasets, 4 epochs. APO used chosen=Qwen3-32B, rejected=Qwen3-0.6B. Model merging recovered long-context performance lost during alignment. |
| **DeepSeek-R1** (arXiv:2501.12948) | Pure RL can incentivize reasoning without human-labeled trajectories. More relevantly: DeepSeek-R1-Distill models (1.5B, 7B, 8B, 14B, 32B, 70B) were created by distilling R1's reasoning into smaller models via SFT on R1-generated reasoning traces. **DeepSeek-R1-Distill-Qwen-1.5B** proves distillation works at 1.5B scale. Published in Nature. |
| **"Don't Stop Pretraining"** (arXiv:2004.10964, ACL 2020) | Domain-adaptive pretraining (DAPT) on unlabeled domain text consistently improves downstream performance across 4 domains and 8 tasks. Task-adaptive pretraining (TAPT) helps even after DAPT. **Multi-phase adaptive pretraining is the gold standard.** This directly supports Step 1 (CPT) of the pipeline. |
| **QLoRA** (arXiv:2305.14314) | 4-bit NF4 quantization + LoRA enables fine-tuning 65B model on single 48GB GPU. Guanaco reached 99.3% ChatGPT on Vicuna benchmark. Makes multi-stage training feasible on consumer hardware. |
| **NEFTune** (arXiv:2310.05914) | Adding noise to embeddings during SFT: LLaMA-2-7B jumps 29.79% → 64.69% on AlpacaEval. Free 8-10% quality boost on Evol-Instruct and ShareGPT data. Applicable to Step 3 of the pipeline. |
| **DPO** (arXiv:2305.18290) | Reformulates RLHF as classification loss on preference pairs. Stable, performant, lightweight. No reward model needed. Enables Step 4 (alignment) without RL infrastructure. SmolLM3 used APO (a DPO variant) and found it more stable. |
| **Evol-Instruct** (arXiv:2304.12244, WizardLM) | Iteratively evolves instructions from simple → complex using LLM-driven mutation (add constraints, deepen, concretize, increase reasoning). Creates difficulty progressions. Directly relevant to generating progressively harder maritime Q&A in Step 2. |
| **DataComp-LM** (arXiv:2406.11794) | Systematic study of data quality impact on LM training. DCLM-Baseline (7B, 2.6T tokens) matches Llama 3 8B with 2x less compute. Data filtering and curation dominate model quality more than scale. Validates that data curation effort in Step 2 is the highest-ROI activity. |
| **"LoRA Learns Less and Forgets Less"** (arXiv:2405.09673) | LoRA substantially underperforms full FT for new knowledge acquisition but forgets less of prior knowledge. Full FT weight perturbations have rank 10-100x greater than typical LoRA. **Tension in the pipeline:** QLoRA is efficient but may bottleneck knowledge injection in CPT stage. |

---

## WHY THIS PIPELINE EXISTS — THE SYNTHESIS ARGUMENT

The core insight behind this combined pipeline is that **no single training technique alone is sufficient** for baking factual knowledge into a small model. Each stage addresses a specific failure mode of the others:

| Stage | What It Provides | What It Cannot Provide Alone |
|---|---|---|
| **CPT (Step 1)** | Domain vocabulary, conceptual relationships, statistical patterns of maritime text | Reliable factual recall, instruction-following, structured Q&A responses |
| **Synthetic Data Gen (Step 2)** | Explicit Q&A pairs covering key facts, diversity of question phrasings, difficulty progressions | n/a — this is a data generation step, not a training step |
| **SFT (Step 3)** | Instruction-following format, explicit memorization of Q&A pairs, response structure | Deep parametric knowledge beyond trained Q&A pairs, robustness to novel phrasings |
| **DPO/GRPO (Step 4)** | Preference alignment, refusal of out-of-domain questions, response quality polish | Knowledge — alignment does not ADD knowledge, only reshapes existing distributions |
| **Model Merging (Step 5)** | Robustness, recovery of capabilities lost during alignment stages, smoothing | New capabilities — merging interpolates, does not create |
| **Quantization (Step 6)** | Mobile-friendly deployment, ~75% size reduction | n/a — trading precision for size |

**The key argument is that CPT + SFT together do what neither does alone:** CPT gives the model a "feel" for the domain (vocabulary, co-occurrence patterns, conceptual clustering), and SFT crystallizes that diffuse knowledge into retrievable Q&A format. The teacher-generated synthetic data acts as a bridge — a **strong local teacher** reads the textbooks and produces training signal that a 3B model can absorb (no paid APIs).

This is genuinely the approach used by the most successful small models:
- **Phi-1:** Synthetic textbook pretraining + CodeExercises fine-tuning
- **Phi-3:** Filtered web + synthetic pretraining + SFT + DPO
- **SmolLM3:** 11T pretraining + mid-training + SFT (synthetic from Qwen3-32B) + APO + model merging
- **DeepSeek-R1-Distill:** SFT on R1-generated reasoning traces
- **Orca 2:** Teacher-generated explanation traces → SFT with strategy selection

---

## CRITERION-BY-CRITERION EVALUATION

### 1. Knowledge Retention — Score: 7/10

**The question:** Does the 3-step process (CPT → synthetic QA → SFT) successfully bake textbook knowledge into weights?

**What the evidence says — in favor:**

The multi-stage approach addresses the single biggest weakness of each individual technique:

- **CPT alone scores 4/10 on knowledge retention** (as evaluated in the CPT ranking). It teaches patterns but not retrievable facts. The model learns that "MARPOL" and "Annex VI" and "air pollution" cluster together, but can't reliably produce "Annex VI regulates SOx emissions with a 0.50% m/m global sulfur cap effective January 1, 2020."

- **SFT alone scores 5/10** (as evaluated in the SFT ranking). It teaches Q&A format but has coverage gaps — the teacher generates 5-20 Q&A pairs per textbook chunk, leaving 75-95% of facts untrained. And "LoRA Learns Less and Forgets Less" shows LoRA underperforms full FT for knowledge acquisition.

- **Combined, they should score higher than either alone.** CPT seeds the weight space with maritime distributional patterns. The model now has "soft" knowledge — it knows the conceptual territory. SFT then acts as a crystallization step, hardening specific facts into retrievable patterns. The synthetic Q&A pairs don't need to cover every fact because the CPT pre-exposure means the model already has partial representations that SFT can sharpen.

**Evidence this works in practice:**

- **SmolLM3** used exactly this approach (pretraining → SFT with synthetic data) and achieved SoTA performance at 3B, outperforming Llama-3.2-3B and Qwen2.5-3B on knowledge benchmarks (ARC, MMLU, BoolQ). The SFT stage used 1.8B tokens of synthetic data generated by Qwen3-32B.

- **DeepSeek-R1-Distill-Qwen-1.5B** proves that even at 1.5B, distillation from a powerful teacher into a pre-trained base model produces surprisingly capable results.

- **Phi-1's "Textbooks Are All You Need"** showed that synthetic textbook-quality data for pretraining + exercises for fine-tuning produced a 1.3B model that outperformed 10x larger models on code benchmarks.

**What still limits knowledge retention:**

- **Phi-3's own admission:** Even 3.8B trained on 3.3T tokens has "low performance on TriviaQA" because "the model simply does not have the capacity to store too much factual knowledge." A 1-3B model trained on ~50M maritime tokens + ~50K synthetic Q&A pairs will be MORE limited, not less.

- **Coverage remains finite.** Even with CPT pre-exposure, the model can only reliably recall facts that were explicitly reinforced by the SFT stage. CPT provides a "foundation of familiarity" but not reliable recall for edge-case facts (e.g., exact regulation thresholds for obscure MARPOL sub-amendments).

- **QLoRA may still bottleneck Step 1.** If CPT uses QLoRA for efficiency, the "LoRA Learns Less" finding means CPT may inject less domain knowledge than full fine-tuning would. However, full FT of even a 1.7B model on 50M tokens is feasible on a single A100 in a few hours, so this bottleneck is avoidable.

**Honest assessment:** This pipeline will reliably answer the "top 500" most important maritime questions covering 60-70% of what a marine engineer needs. The "long tail" of rare facts, obscure regulations, and cross-referenced details will still be unreliable. For a mobile chatbot without RAG, this is the best achievable result at 1-3B. But it is NOT equivalent to having the textbook on hand.

**Score justification:** 7/10 — Significant improvement over either CPT (4/10) or SFT (5/10) alone. The combination is genuinely synergistic: CPT provides the substrate that makes SFT dramatically more effective. But small model capacity remains a hard ceiling on factual recall. Docked 3 points because Phi-3 itself (3.8B, 3.3T tokens) admitted factual knowledge limitations, and our model is operating at orders of magnitude less data.

---

### 2. Inference Cost — Score: 10/10

**Zero additional overhead. Period.**

After the entire pipeline completes, the output is a single GGUF file — architecturally identical to the base model. Same parameter count, same layer structure, same inference path. The 6 training stages leave NO trace in the inference graph.

**Concrete specs for a 3B model (Q4_K_M GGUF):**
- **Model size:** ~1.8-2.0 GB on disk
- **RAM at inference:** ~2.5-3.0 GB (model + KV cache + runtime)
- **Tokens/second on iPhone 15 (A17 Pro):** ~15-25 tok/s (based on Phi-3 benchmarks: 12 tok/s on iPhone 14 for 3.8B at 4-bit)
- **Tokens/second on mid-range Android (Snapdragon 8 Gen 2):** ~10-20 tok/s
- **Time to first token:** <500ms
- **Typical response (100 tokens):** 4-10 seconds
- **Network required:** NONE (fully offline)
- **Battery drain:** Minimal (pure matrix multiply, no network I/O)

**For a 1.7B model (Q4_K_M GGUF):**
- **Model size:** ~1.0-1.2 GB on disk
- **RAM at inference:** ~1.5-2.0 GB
- **Tokens/second:** ~20-35 tok/s on modern smartphones

**Comparison to alternatives:**
| Approach | Inference Overhead |
|---|---|
| This pipeline (single model) | Zero — identical to base model |
| RAG | +50-200ms vector search + embedding compute + retrieval I/O |
| Ensemble / model soup at inference | 2-5x compute |
| Tool calling / API fallback | Network latency + API dependency |

**Score justification:** 10/10 — Perfect. The entire multi-stage training pipeline produces a deployment artifact that is indistinguishable from a vanilla quantized model at inference time. This is the entire POINT of baking knowledge into weights rather than using retrieval.

---

### 3. Training Cost — Score: 6/10

**This is the pipeline's biggest operational weakness.** Unlike CPT-only ($5-10) or SFT-only ($20-50), this pipeline has significant costs at multiple stages:

**Realistic cost breakdown:**

| Stage | Compute | API / Data Cost | Time | Total |
|---|---|---|---|---|
| **Step 1: CPT** on ~50M tokens, 3-5 epochs | A100 × 3-6 hrs | $0 | 3-6 hrs | $5-10 |
| **Step 2: Synthetic Data Gen** — 50K Q&A pairs via **local teacher** | 4-GPU box (local inference) | $0 API (compute-only) | multi-day OK (throughput-dependent) | $0 API |
| **Step 2b: Evol-Instruct** — Evolving 50K pairs through 2-3 difficulty levels | n/a | Additional ~$50-150 | 4-8 hrs | $50-150 |
| **Step 3: SFT** on 50K-150K pairs, 3 epochs | A100 × 2-4 hrs | $0 | 2-4 hrs | $3-7 |
| **Step 4: DPO/GRPO** | A100 × 2-4 hrs | Preference data gen: ~$30-60 | 2-4 hrs | $35-65 |
| **Step 5: Model Merging** | CPU × 10 mins | $0 | 10 mins | $0 |
| **Step 6: Quantization** | CPU × 5 mins | $0 | 5 mins | $0 |
| **TOTAL** | | | **~20-40 hrs** | **$193-532** |

**If using an alternative teacher model:**
- Still local (no paid APIs): choose the best open-weight teacher you can run on the 4-GPU box; higher teacher quality generally reduces filtering burden and improves student.

**If using a fully open alternative (self-hosted Qwen3-32B on A100):**
- Rental for 12-24 hrs generation: ~$15-30
- **Reduced total: $25-60**

**Context — is this expensive?**

For a commercial maritime training product: **No, this is cheap.** A single maritime textbook costs $50-150. A human domain expert creating Q&A pairs would charge $5,000+.

For an indie developer or researcher: **Yes, this is non-trivial.** Compared to just doing CPT ($5-10), the pipeline is 5-50x more expensive, primarily driven by the synthetic data generation cost.

**The real cost is iteration.** This pipeline will need to be run 3-5 times with different:
- Data generation prompts
- Q&A diversity strategies
- Evol-Instruct depth
- SFT hyperparameters
- DPO preference data

Multiply the single-run cost by 3-5x for realistic development: **$75-2,600** depending on choices.

**Score justification:** 6/10 — Manageable for a serious project but significantly more expensive than single-stage approaches. The teacher model API cost is the dominant factor and can be reduced by using open models. The compute cost is modest for 1-3B models. Total cost is reasonable for a commercial product but could be prohibitive for a hobbyist doing multiple iterations.

---

### 4. Data Efficiency — Score: 8/10

**The question:** Are 10-50 textbooks enough for this pipeline?

**This is where the pipeline genuinely shines.** The architecture is specifically designed to extract maximum value from limited domain data:

**Why this pipeline is data-efficient:**

1. **CPT extracts distributional knowledge from raw text.** Every sentence in the textbook contributes to the model's understanding of maritime vocabulary, concepts, and relationships — even filler text, section headers, and connecting prose. No hand-labeling needed.

2. **The teacher model AMPLIFIES the data.** A single textbook chunk of 2,000 tokens can generate:
   - 10-20 factual Q&A pairs
   - 5-10 procedural Q&A pairs
   - 3-5 troubleshooting scenarios
   - 2-3 safety-critical Q&A pairs
   - **And with Evol-Instruct:** each pair spawns 2-3 harder variants

   So 2,000 raw tokens → 60-100+ training Q&A pairs. A 50-page textbook chapter (~25K tokens) → 750-1,250 Q&A pairs.

3. **10 maritime textbooks = substantial corpus:**
   - "Reeds Vol. 5 Ship Construction" → ~200K tokens → ~7,500-12,500 Q&A pairs
   - MARPOL Consolidated → ~300K tokens → ~11,250-18,750 Q&A pairs  
   - STCW Convention → ~150K tokens → ~5,625-9,375 Q&A pairs
   - Marine Diesel Engines (Calder) → ~150K tokens → ~5,625-9,375 Q&A pairs
   - Corrosion Engineering → ~200K tokens → ~7,500-12,500 Q&A pairs
   - Plus 5 more textbooks → ~500K tokens → ~18,750-31,250 Q&A pairs
   
   **Total: ~1.5M raw tokens → 56,250-93,750 synthetic Q&A pairs**

   This is well within the range that works. SmolLM3's SFT used 1.8B tokens, but that was for general capabilities across many domains. A domain-specific maritime model can achieve strong coverage with 50K-100K focused pairs because the domain is narrow.

4. **"Textbooks Are All You Need" principle applies directly.** Phi-1 used only 1B synthetic tokens for its fine-tuning exercises and achieved breakout results. Our 50K-100K pairs represent ~50-100M tokens of Q&A data — more than enough for domain-specific SFT.

5. **DEITA** (arXiv:2312.15685) showed that 6K carefully selected SFT samples can match 60K+ generic samples. Quality and diversity matter more than raw count.

**What limits data efficiency:**

- **Coverage ceiling.** 10-50 textbooks cover the core curriculum but miss many edge cases, amendments, port-specific regulations, and manufacturer-specific technical details. MARPOL alone has undergone 30+ amendments since 2011.
- **Teacher model comprehension.** If GPT-4o misunderstands a maritime concept when generating Q&A pairs, that error propagates into training data. Maritime text contains specialized terminology that even GPT-4o can misinterpret.
- **Textbook ≠ complete knowledge.** Textbooks omit practical knowledge that experienced engineers have (troubleshooting heuristics, common failure modes, port-specific quirks).

**Score justification:** 8/10 — The pipeline is specifically designed for data-limited scenarios. The teacher model acts as a knowledge amplifier, and CPT on raw text requires no labeling. 10-50 textbooks is enough for a genuinely useful maritime study aid covering the main subjects. Docked 2 points because narrow domain coverage means edge-case failures, and teacher model errors in Q&A generation are hard to detect at scale.

---

### 5. Accuracy on Domain QA — Score: 7/10

**The question:** What accuracy should we expect on a maritime domain QA benchmark?

**There is no established maritime QA benchmark**, so I'll estimate by analogy to comparable tasks:

**Expected accuracy breakdown by question type:**

| Question Type | Example | Expected Accuracy | Why |
|---|---|---|---|
| **Factual recall (directly trained)** | "What are the 6 annexes of MARPOL?" | **85-90%** | Explicitly in synthetic Q&A data, reinforced by CPT |
| **Factual recall (indirectly covered)** | "What is the maximum sulfur content allowed in fuel oil in ECAs under MARPOL Annex VI?" | **65-75%** | Covered in CPT, may/may not have exact Q&A pair |
| **Procedural** | "Describe the steps for enclosed space entry" | **75-85%** | Likely generated as procedural Q&A, CPT provides supporting knowledge |
| **Reasoning / troubleshooting** | "The main engine oil mist detector alarm activates. What are the immediate actions?" | **60-70%** | Requires combining knowledge from CPT + structured response from SFT |
| **Cross-referencing** | "Which SOLAS Chapter covers fire protection, and how does it relate to the FSS Code?" | **50-60%** | Cross-reference reasoning is hard for small models; may hallucinate connections |
| **Numerical precision** | "What is the minimum freeboard for a Type A vessel of 100m length?" | **40-55%** | Exact table lookups are inherently difficult for LLMs without retrieval |
| **Novel phrasings of trained facts** | "Tell me about pollution rules for ship smoke" (→ MARPOL Annex VI) | **70-80%** | CPT helps with semantic similarity; Evol-Instruct creates phrasing diversity |
| **Out-of-domain** | "What's the best restaurant in Singapore port?" | **Depends on DPO training** | Should refuse if Step 4 trains refusal properly |

**Weighted overall estimate:** ~65-75% across a realistic mix of question types.

**Benchmarking by analogy:**
- **MedQA (medical domain QA, USMLE-style):** GPT-4 achieves 86%, fine-tuned 7B models achieve 45-55%, fine-tuned 70B models achieve 65-70%. Our 3B maritime model is in the "fine-tuned <7B" category → expect 45-65% on hard exam questions.
- **Orca 2 (7B):** Surpassed 5-10x larger models on complex reasoning, BUT this was 7B, not 1-3B, and the tasks were general-purpose, not domain-specific factual recall.
- **Phi-3 (3.8B):** 69% MMLU, but admitted poor TriviaQA performance. MMLU tests conceptual understanding; our maritime QA would test factual recall more heavily.

**Score justification:** 7/10 — Strong on directly trained content (which the pipeline maximizes through synthetic data generation), decent on related content (CPT provides conceptual scaffolding), weak on numerical precision and cross-referencing. The pipeline achieves the best accuracy available at 1-3B scale for this use case, but it won't match a RAG system with access to the actual textbooks.

---

### 6. Mobile Deployability — Score: 9/10

**This is a near-perfect score category for this pipeline.**

After Step 6 (quantization to Q4_K_M GGUF), the deployment artifact is a single file that runs via llama.cpp or MLC-LLM:

**Deployment specifications:**

| Metric | 1.7B Model | 3B Model |
|---|---|---|
| **GGUF file size (Q4_K_M)** | ~1.0-1.2 GB | ~1.8-2.0 GB |
| **RAM at inference** | ~1.5-2.0 GB | ~2.5-3.0 GB |
| **App total size (model + runtime)** | ~1.1-1.3 GB | ~1.9-2.1 GB |
| **Min device RAM** | 3 GB | 4 GB |
| **Tokens/sec (iPhone 15)** | ~25-35 | ~15-25 |
| **Tokens/sec (Snapdragon 8 Gen 2)** | ~20-30 | ~10-20 |
| **iOS compatibility** | iPhone 11+ (2019) | iPhone 12+ (2020) |
| **Android compatibility** | Most 2021+ devices | Most 2022+ flagship/midrange |
| **Offline capable** | Yes — fully | Yes — fully |
| **Battery drain per query** | Negligible | Negligible |

**Real-world precedents:**
- **Phi-3-mini (3.8B)** runs on iPhone 14 at 12 tok/s in 4-bit mode, using 1.8GB memory. Our 3B model would be slightly faster due to fewer parameters.
- **SmolLM3 (3B)** has official quantized checkpoints in the HuggingFace collection, validating that 3B models are the sweet spot for on-device deployment.
- **llama.cpp** and **MLC-LLM** both provide mature iOS/Android inference runtimes with Metal (iOS) and Vulkan/OpenCL (Android) GPU acceleration.

**Why not 10/10:**

The only limitation is that a 3B model at Q4_K_M still requires ~2GB app storage + ~3GB runtime RAM. This fits comfortably on flagship phones (6-12GB RAM) but may be tight on ultra-budget devices with 3GB RAM total. The 1.7B variant is safer for maximal compatibility.

Also: the Q4_K_M quantization introduces ~1-3% accuracy degradation compared to FP16 (based on published perplexity benchmarks of GGUF quantization). This is a minor but real cost of mobile deployment.

**Score justification:** 9/10 — The pipeline produces a model that is specifically optimized for mobile deployment. The quantized model fits within mobile constraints with room to spare. Docked 1 point for tight RAM on ultra-budget devices and minor quantization accuracy loss.

---

### 7. Robustness — Score: 7/10

**The question:** Can the model handle diverse question phrasings, informal language, broken English (common among international maritime crews), and edge cases?

**Why this pipeline improves robustness over single-stage approaches:**

1. **CPT teaches semantic similarity.** By training on raw maritime prose, the model learns that "ballast water treatment" and "BWT systems" and "ballast management" are semantically related. This means questions phrased in non-standard ways are more likely to activate the right internal representations.

2. **Evol-Instruct (Step 2) explicitly creates phrasing diversity.** By evolving each Q&A pair through multiple mutations:
   - "What are the MARPOL annexes?" → "List and briefly describe each annex of the MARPOL convention" → "A junior engineer asks you to explain the different parts of international pollution prevention regulation — what would you tell them?"
   - This creates training signal for diverse phrasings of the same underlying fact.

3. **DPO/GRPO (Step 4) teaches refusal for OOD queries.** By training with negative examples (out-of-domain questions with "I cannot answer this as it's outside my maritime knowledge" responses), the model learns to say "I don't know" rather than hallucinating.

4. **Model merging (Step 5) smooths decision boundaries.** Averaging multiple checkpoints reduces overfitting to specific phrasings in the training data, improving generalization.

**What still limits robustness:**

- **International English variants.** Maritime crews speak English as a 2nd/3rd/4th language. Questions like "Engine oil is going hot too much, what happen?" are realistic but unlikely to appear in Evol-Instruct outputs (which tend to generate "clean" English). Specific effort is needed to include broken/simplified English in the synthetic data.

- **Small model reasoning limitations.** A 1-3B model has limited capacity for multi-hop reasoning. Questions that require combining facts from different textbooks (e.g., "How does the SOLAS fire detection requirement interact with the MARPOL engine room ventilation regulation?") will often fail.

- **Adversarial robustness.** The model can be tricked into confident wrong answers by plausible-sounding but incorrect premises ("Since MARPOL Annex VII covers..."). Small models are particularly susceptible to prompt injection.

**Score justification:** 7/10 — The multi-stage pipeline significantly improves robustness over single-stage approaches through CPT's semantic grounding, Evol-Instruct's phrasing diversity, and DPO's refusal training. But small model capacity still limits complex reasoning, and international English variants need explicit attention.

---

### 8. Catastrophic Forgetting — Score: 6/10

**This is the pipeline's most underestimated risk.** Multi-stage training is a known vector for catastrophic forgetting, and this pipeline has FIVE sequential training stages before quantization.

**The forgetting cascade:**

| Stage | What's At Risk | Mitigation |
|---|---|---|
| **After CPT** | General language capabilities (base model was trained on diverse web data; CPT on maritime text may overwrite general knowledge) | Use low learning rate, limit epochs, use LoRA (which "forgets less" per arXiv:2405.09673) |
| **After SFT** | CPT-acquired maritime patterns may be partially overwritten by the Q&A format training | Use low learning rate, include general-capability samples in SFT mix |
| **After DPO** | SFT-acquired Q&A capabilities may shift; SmolLM3 explicitly reported **long-context performance degradation after APO** | Model merging with pre-DPO checkpoint (exactly what SmolLM3 did) |
| **After Quantization** | Q4_K_M introduces ~1-3% perplexity degradation across all capabilities uniformly | Use K-quant variants (Q4_K_M, Q5_K_M) rather than older quant methods |

**Evidence from SmolLM3:**

SmolLM3's team explicitly documented that their APO (DPO variant) stage **degraded long-context performance on RULER benchmarks**. They traced this to the reasoning mid-training stage conflicting with earlier capabilities. Their solution: model merging with a pre-alignment checkpoint (0.9 × APO model + 0.1 × mid-training checkpoint). This worked but required careful calibration.

**The maritime-specific forgetting risk:**

In our pipeline, the base model (e.g., Qwen3-1.7B) was trained on 36T tokens of diverse data. It knows how to:
- Answer questions about many topics
- Reason about general concepts
- Follow general instructions

After CPT on maritime text + SFT on maritime Q&A, the model may lose:
- General instruction-following quality
- Non-maritime knowledge (which may be useful for context, e.g., geography, chemistry for corrosion)
- Conversational fluency on non-domain topics

**This matters less for a dedicated maritime chatbot** (if the model only needs to answer maritime questions, losing knowledge about cooking recipes is irrelevant). But it matters if users ask tangentially related questions that require general knowledge (e.g., "What's the chemical formula for the sulfur compound regulated by MARPOL Annex VI?").

**Mitigations available:**

1. **LoRA for CPT:** "LoRA Learns Less and Forgets Less" — using LoRA during CPT preserves more base model knowledge at the cost of less domain knowledge injection. This is a genuine trade-off.
2. **Data mixing in SFT:** Include 10-20% general-capability samples (from Alpaca, ShareGPT, etc.) alongside maritime Q&A to preserve general instruction-following.
3. **Model merging with base:** After the full pipeline, merge with original base model weights (e.g., 0.7 × trained + 0.3 × base) to recover some general capabilities.
4. **Checkpoint selection:** Keep intermediate checkpoints and merge the best performers per evaluation dimension.

**Score justification:** 6/10 — Multi-stage training creates real forgetting risks at each transition. SmolLM3 documented this explicitly and had to use model merging to mitigate. The mitigations exist (LoRA, data mixing, model merging), but they require careful tuning and evaluation at each stage, adding complexity. Docked 4 points because this pipeline has the MOST stages of any approach (and thus the most opportunities for forgetting), and because the LoRA/full-FT trade-off means you must choose between knowledge injection and preservation.

---

### 9. Maintenance — Score: 5/10

**The question:** How hard is it to update the model when maritime regulations change?

**This is the Achilles' heel of any "all knowledge in weights" approach,** and the multi-stage pipeline makes it WORSE, not better, compared to single-stage approaches.

**Why maintenance is difficult:**

1. **The pipeline is sequential and non-modular.** To update knowledge about a new MARPOL amendment:
   - Re-run CPT on the updated text (or append new text and do additional CPT)
   - Re-generate synthetic Q&A pairs for the changed regulations
   - Re-run SFT (or do additional SFT on the new Q&A pairs)
   - Re-run DPO (or verify alignment still holds)
   - Re-merge models
   - Re-quantize
   - Re-deploy to all user devices

   Total update time: **1-3 days of compute + testing**, minimum.

2. **Incremental CPT risks catastrophic forgetting.** If you do a small CPT run on just the new MARPOL amendment text, you risk overwriting earlier training. If you redo CPT from scratch, you rebuild from Stage 1.

3. **Synthetic data regeneration is the bottleneck.** The teacher model must read the new regulation, understand what changed, generate Q&A pairs that reflect the updated (not old) information, and handle contradictions with previous data. This requires human oversight.

4. **Maritime regulations change frequently:**
   - IMO amendments: Annual (MEPC, MSC sessions)
   - MARPOL amendments: ~2-3 per year
   - SOLAS amendments: ~1-2 per year
   - New regulations (e.g., CII, EEXI, GHG strategy): Major updates every 2-3 years
   - Port state control focus areas: Change annually

   A model that can't update in <1 week is perpetually out of date.

**Comparison to RAG (which this approach explicitly rejects):**
- RAG update: Replace document in vector store → done in minutes
- This pipeline update: 1-3 days minimum

**Mitigations:**

- **Maintain a "regulation layer" using LoRA.** Keep the base trained model frozen and train regulation-specific LoRA adapters that can be swapped. This is technically feasible (swap LoRA adapters at inference time) but adds complexity and doesn't fully solve the problem because regulations often interact with each other.
- **Versioned model releases.** Treat model updates like app updates — quarterly release cycle. Acceptable for a study aid, unacceptable for a safety-critical compliance tool.
- **Hybrid approach.** Use the pipeline model for core knowledge and add a small RAG component for frequently changing regulations. But this contradicts the "NO RAG" constraint.

**Score justification:** 5/10 — The multi-stage pipeline is the HARDEST approach to maintain because updates must cascade through all stages. Maritime regulations change multiple times per year. The model will be outdated within months without active maintenance. This is the fundamental trade-off of "all knowledge in weights" — it's a static knowledge store in a dynamic regulatory environment.

---

### 10. Proven at Small Scale — Score: 8/10

**The question:** Is there evidence this combined pipeline works at 1-3B parameters?

**This is the pipeline's strongest category after inference cost.** The evidence is compelling:

**Direct evidence at 1-3B scale:**

1. **SmolLM3 (3B):** The single most relevant data point. HuggingFace's 3B model used the EXACT pipeline:
   - Multi-stage pretraining (11T tokens)
   - Mid-training for reasoning (35B tokens)
   - SFT with synthetic data from Qwen3-32B (1.8B tokens)
   - APO alignment (DPO variant)
   - Model merging (0.9 × APO + 0.1 × mid-training)
   - Outperforms Llama-3.2-3B and Qwen2.5-3B on knowledge and reasoning benchmarks
   - Competitive with 4B models (Qwen3-4B, Gemma3-4B)
   - Full recipe is open and reproducible

2. **DeepSeek-R1-Distill-Qwen-1.5B:** Distilled from DeepSeek-R1 via SFT on reasoning traces. Only 1.5B parameters. While focused on reasoning rather than domain knowledge, it proves that teacher → student distillation works at 1.5B.

3. **Phi-1 (1.3B):** Synthetic data pretraining + exercise fine-tuning at 1.3B achieved 50.6% HumanEval, outperforming models 10x its size. The original proof that data quality can substitute for scale.

**Indirect evidence at small scale:**

4. **Phi-3-mini (3.8B):** Full pipeline (filtered pretraining + SFT + DPO) runs on iPhone. 69% MMLU. Deployed successfully on mobile. Slightly larger than our target but validates the approach.

5. **Orca 2 (7B, 13B):** Teacher-generated training data + strategy-aware SFT. Surpassed 5-10x larger models. Not tested at <7B, but the principle (teacher distillation into small model) is validated.

6. **Qwen3-1.7B:** Trained with strong-to-weak distillation requiring only 1/10 GPU hours vs full training. Achieves MMLU 62.63 at 1.7B. Not the same pipeline but validates that multi-stage training works at this scale.

**What's NOT proven at small scale:**

- **Domain-specific factual recall at 1-3B.** All the above evidence is for GENERAL capabilities (code, reasoning, MMLU). None of these models were evaluated on their ability to bake in and recall specific domain facts from a limited corpus of textbooks. The maritime use case is fundamentally a knowledge-storage problem, and small models have limited capacity for this.

- **10-50 textbooks as source data at 1-3B.** The successful small models were trained on TRILLIONS of tokens. Our pipeline uses millions. The pipeline itself is proven, but not at our data scale.

**Score justification:** 8/10 — The multi-stage pipeline is the most empirically validated approach at 1-3B scale. SmolLM3 is an open-source, reproducible proof point at exactly 3B. DeepSeek-R1-Distill proves distillation at 1.5B. Phi-1 proves synthetic data quality at 1.3B. Docked 2 points because none of these proofs involve domain-specific factual recall from a small textbook corpus — the specific challenge of the maritime chatbot use case.

---

## SCORING SUMMARY

| # | Criterion | Score | Key Reasoning |
|---|---|---|---|
| 1 | Knowledge Retention | **7/10** | CPT + SFT synergy genuinely exceeds either alone; teacher amplifies limited data; but small model capacity is a hard ceiling on factual recall (Phi-3 admits this at 3.8B) |
| 2 | Inference Cost | **10/10** | Zero overhead — single GGUF file, identical to base model at inference |
| 3 | Training Cost | **6/10** | $60-530 total depending on teacher model choice; iteration multiplies cost 3-5x; API cost dominates |
| 4 | Data Efficiency | **8/10** | Pipeline is designed for limited data; teacher amplifies 10-50 textbooks into 50K-100K Q&A pairs; "Textbooks Are All You Need" principle applies |
| 5 | Accuracy on Domain QA | **7/10** | ~65-75% estimated across question types; strong on trained facts, weak on numerical precision and cross-referencing |
| 6 | Mobile Deployability | **9/10** | 1-2GB GGUF, 2-3GB RAM, 15-25 tok/s on iPhone 15; proven by Phi-3 and SmolLM3 |
| 7 | Robustness | **7/10** | CPT + Evol-Instruct + DPO each contribute to robustness; limited by small model reasoning capacity and international English variants |
| 8 | Catastrophic Forgetting | **6/10** | Most stages = most forgetting opportunities; SmolLM3 documented and solved this with model merging; mitigations exist but add complexity |
| 9 | Maintenance | **5/10** | Hardest approach to maintain; updates cascade through all stages; maritime regulations change frequently; fundamental weakness of "all in weights" |
| 10 | Proven at Small Scale | **8/10** | SmolLM3 (3B), DeepSeek-R1-Distill (1.5B), Phi-1 (1.3B) all validate the pipeline; not proven for domain-specific factual recall from limited corpus |

---

## TOTAL SCORE: 73/100

---

## KEY STRENGTHS (3)

### Strength 1: This Is How The Best Small Models Were Actually Built

This is not a theoretical proposal — it is the documented, reproducible recipe used by SmolLM3 (HuggingFace), Phi-3 (Microsoft), Orca 2 (Microsoft), and DeepSeek-R1-Distill (DeepSeek). Every component has been individually validated and the full pipeline has been demonstrated at the exact target scale (3B). SmolLM3's open recipe includes training configs, data mixtures, intermediate checkpoints, and wandb logs. This is the most battle-tested approach available for building small, capable, on-device language models.

### Strength 2: Synergistic Interaction Between CPT and SFT

The single most important insight is that CPT and SFT are **complementary, not redundant.** CPT alone scores 4/10 on knowledge retention; SFT alone scores 5/10. Combined, they score 7/10. This is not additive — it's synergistic. CPT creates a "soft" parametric landscape where maritime concepts are partially encoded in weight space. SFT then sharpens specific facts into retrievable patterns within this pre-conditioned landscape. The teacher model acts as a knowledge amplifier, reading textbooks with GPT-4o-level comprehension and generating training signal calibrated for the student model's capacity. This is the Orca 2 insight applied to domain knowledge: the student doesn't just imitate the teacher — it learns through the teacher.

### Strength 3: Perfect Mobile Deployment

Zero inference overhead. A single GGUF file that runs identically to the base model. 1-2GB on disk, 2-3GB RAM, 15-25 tok/s on modern smartphones, fully offline. This is the ONLY approach that simultaneously solves: (a) no network dependency, (b) no latency overhead, (c) fits in an app store download, (d) works on 3-year-old phones, (e) preserves battery life. The pipeline produces a deployment artifact that is indistinguishable from a simple offline model — all the complexity is in training, not inference.

---

## KEY WEAKNESSES (3)

### Weakness 1: Factual Recall Has a Hard Ceiling at 1-3B

Phi-3's own authors — who pioneered this approach — explicitly state that their 3.8B model "does not have the capacity to store too much factual knowledge." Their recommendation is to augment with a search engine for factual queries. Our 1-3B model, trained on orders of magnitude less data, will be even more limited. The pipeline maximizes what's achievable within this ceiling, but the ceiling exists. A marine engineer asking for the exact tank testing pressure specified in SOLAS Chapter II-1, Regulation 12, will often get a plausible but potentially wrong number. **For safety-critical applications, this model CANNOT be the sole reference.** It should be positioned as a study aid and quick reference, not as a replacement for the actual regulations.

### Weakness 2: Multi-Stage Pipeline Is Complex and Fragile

Six stages, each with its own hyperparameters, failure modes, and interaction effects. SmolLM3 documented that their alignment stage degraded long-context performance, requiring model merging to fix. Each stage transition is a potential point of catastrophic forgetting, distribution shift, or subtle quality regression that may not be caught without extensive evaluation. The pipeline requires expertise across CPT, synthetic data generation, SFT, preference alignment, model merging, AND quantization — each a subfield of its own. For a solo developer or small team, this is genuinely daunting. The total cost of 3-5 iterations ($75-2,600) is manageable financially but represents weeks of development time.

### Weakness 3: Maintenance Is the Structural Vulnerability

Maritime regulations change multiple times per year. Every update requires re-running parts of the pipeline: new CPT data, new synthetic Q&A, new SFT, re-verification of alignment, re-merging, re-quantization, re-deployment. There is no "hot swap" mechanism — you cannot insert new knowledge without retraining. RAG systems update their knowledge store in minutes; this pipeline takes days. For a study tool referencing stable textbook content, this is acceptable. For a compliance tool tracking active regulations, this is disqualifying. The NO RAG constraint makes this weakness structural and unfixable within the pipeline's architecture.

---

## VERDICT

**The CPT + Synthetic SFT + Knowledge Distillation pipeline scores 73/100 and is THE RECOMMENDED APPROACH for building a maritime chatbot on mobile phones with all knowledge in weights.**

This is not a high score in absolute terms — it reflects the genuine difficulty of the underlying problem (baking domain knowledge into a 1-3B model without retrieval augmentation). But it is the HIGHEST achievable score because:

1. **It is the empirically proven approach.** SmolLM3, Phi-3, Orca 2, and DeepSeek-R1-Distill all validate this pipeline at the target scale.
2. **Each alternative scores lower.** CPT alone (~55/100), SFT alone (~58/100), and other single-stage approaches cannot match the synergistic knowledge retention of the combined pipeline.
3. **It maximizes what's physically possible.** Given the constraints (1-3B parameters, no RAG, mobile deployment, domain-specific factual knowledge), this pipeline extracts the maximum value from each bit of training data.

**Recommended implementation order:**
1. Start with CPT on all available textbooks using full fine-tuning (not LoRA) of Qwen3-1.7B — it's affordable at this scale
2. Generate 50K-100K synthetic Q&A pairs using Qwen3-32B or DeepSeek-R1 (cheapest high-quality teacher)
3. Apply Evol-Instruct for 2-3 difficulty levels per pair
4. SFT with QLoRA + NEFTune, mixing 85% maritime + 15% general-capability data
5. DPO/APO using teacher-chosen pairs for alignment and refusal training
6. Model merging: checkpoint soup + base model merge for robustness
7. Quantize to Q4_K_M GGUF → deploy

**Critical positioning:** The resulting chatbot should be marketed as a **maritime study aid and quick reference tool**, NOT as a regulatory compliance tool or safety-critical decision support system. Its knowledge will be approximately 65-75% accurate across question types, which is excellent for studying and learning but insufficient for operational decisions at sea.

**Bottom line:** This is the state-of-the-art recipe. It exists because the AI research community spent 2023-2025 converging on exactly this pipeline architecture. Use it — but respect its limitations.
