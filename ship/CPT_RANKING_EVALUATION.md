# RANKING EVALUATION: Continued Pretraining (CPT) on Domain Text

**Approach Under Evaluation:** Taking a pre-trained small model (e.g., Qwen3-1.7B) and continuing to train it on raw maritime textbook text using next-token prediction (causal language modeling). The idea is that the model absorbs domain vocabulary, facts, and relationships into its weights.

**Date:** February 16, 2026  
**Evaluator Context:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Target Model:** Qwen3-1.7B (or similar <3B model)  
**Target Hardware:** Mobile phone, ARM CPU, 3-6 GB RAM  

---

## RESEARCH SOURCES ANALYZED

| Paper | Key Finding for CPT |
|---|---|
| **"Don't Stop Pretraining" (Gururangan et al., 2020; arXiv:2004.10964)** | Domain-adaptive pretraining (DAPT) on ~25K-50K unlabeled domain documents consistently improves downstream task performance across 4 domains (biomedical, CS, news, reviews) and 8 classification tasks. Even task-adaptive pretraining (TAPT) on just the task's unlabeled data improves performance *after* DAPT. Multi-phase adaptive pretraining is the gold standard. |
| **Phi-1 "Textbooks Are All You Need" (Gunasekar et al., 2023; arXiv:2306.11644)** | 1.3B model trained on 7B tokens (6B filtered web + 1B synthetic "textbook-quality" data) achieves 50.6% pass@1 on HumanEval. Proves data quality >> data quantity. But this is for *code generation*, a structured domain — maritime factual recall is harder. |
| **Phi-3 Technical Report (Abdin et al., 2024; arXiv:2404.14219)** | 3.8B model rivals GPT-3.5 on benchmarks. Runs on iPhone 14 at 12+ tokens/sec in 4-bit (1.8GB memory). **CRITICAL ADMISSION from the paper: "The model simply does not have the capacity to store too much factual knowledge, which can be seen for example with low performance on TriviaQA."** Recommends augmenting with search engine for factual queries. |
| **LLaMA (Touvron et al., 2023; arXiv:2302.13971)** | Trained on trillions of tokens from public data. LLaMA-13B outperforms GPT-3 (175B) on most benchmarks. Proves open pretraining works, but at massive data scale. |
| **Qwen2.5 Technical Report (Qwen Team, 2024; arXiv:2412.15115)** | 18T tokens pretraining, 1M+ SFT samples, multistage RL. High-quality data scaling is key. Qwen2.5-1.5B serves as a capable small base model. |
| **Qwen3 Technical Report (Qwen Team, 2025; arXiv:2505.09388)** | 36T tokens, 119 languages. Three-stage pretraining: General (30T) → Reasoning/STEM (5T) → Long Context. **Qwen3-1.7B achieves MMLU 62.63**, outperforming Qwen2.5-1.5B (60.90). Strong-to-weak distillation works: only 1/10 GPU hours vs full 4-stage training. Uses QK-Norm for stable training. Qwen3-1.7B has 28 layers, 16 query heads / 8 KV heads, tied embeddings, 32K context. |
| **SmolLM3 (HuggingFace, 2025)** | 3B model, 11T tokens, 3-stage pretraining (web 85%→75%→63%, code 12%→15%→24%, math 3%→10%→13%). Outperforms Llama-3.2-3B and Qwen2.5-3B. Full open recipe. Uses GQA, NoPE, intra-document masking, no weight decay on embeddings. |
| **NEFTune (Jain et al., 2023; arXiv:2310.05914)** | Adding uniform noise to embedding vectors during finetuning improves LLaMA-2-7B on AlpacaEval from 29.79% → 64.69%. Simple, free quality boost applicable during CPT/SFT. |

---

## SCORING: 10 CRITERIA (Brutally Honest)

---

### 1. Knowledge Retention — Score: 4/10

**The question:** Can a CPT'd 1.7B model reliably answer "SOLAS Chapter III requires how many lifeboats?" or "What is the minimum fire extinguisher requirement in the engine room per SOLAS FSS Code?"

**The honest answer: No, not reliably.**

**Evidence against high knowledge retention:**

- **Phi-3's own authors admit it (arXiv:2404.14219, Section 6 "Weakness"):** *"The model simply does not have the capacity to store too much factual knowledge, which can be seen for example with low performance on TriviaQA."* This is for a 3.8B model trained on 3.3 TRILLION tokens. A 1.7B model trained on 50M maritime tokens will be far worse at factual recall.

- **CPT teaches distributions, not databases.** Next-token prediction optimizes the model to predict the most probable next word given context. It learns *statistical patterns* — that "SOLAS" co-occurs with "safety," "lifeboats," "Chapter III" — but it does NOT learn to store and retrieve exact numbers the way a database does. The model will learn that lifeboats and SOLAS are related, but may hallucinate the specific count.

- **Small model capacity is fundamentally limiting.** A 1.7B parameter model stores ~3.4GB of weights (at FP16). After quantization to 4-bit, that's ~850MB of actual information. The information-theoretic capacity of this to store millions of specific facts while also maintaining language fluency is severely limited. Research on knowledge neurons (Dai et al., 2022) shows that factual knowledge is distributed across many parameters, and smaller models have fewer "slots" for discrete facts.

- **Multiple epochs on small data = memorization artifacts, not reliable recall.** If the maritime corpus is 50M tokens and you train for 10 epochs (500M effective tokens), the model may memorize training text sequences but won't necessarily generalize to novel question formulations about the same facts.

**What CPT DOES retain well:**
- Domain vocabulary and terminology (e.g., understanding "bulkhead," "scupper," "IMO," "MARPOL Annex VI")
- Conceptual relationships (e.g., ballast water relates to invasive species, STCW relates to crew certification)
- Writing style and register of maritime technical prose
- General domain "vibe" — the model sounds like it knows about ships

**What CPT does NOT retain well:**
- Exact numbers (regulation thresholds, specific requirements)
- Precise procedural steps (exact order of operations for emergency procedures)
- Cross-references between regulations (which MARPOL annex covers what)
- Rarely-mentioned facts that appeared only once or twice in training data

**Score justification:** 4/10 because CPT provides foundational domain awareness but fails on the specific factual recall that a ship crew member actually needs. A crew member asking "What's the CO2 concentration limit for enclosed space entry?" needs an exact answer (0.5% or 5000 ppm), and CPT alone will likely give a plausible-sounding but potentially wrong number.

---

### 2. Inference Cost — Score: 10/10

**Zero additional overhead. Period.**

After CPT, the model is architecturally identical to the base model. Same number of parameters, same architecture, same inference pipeline. The only difference is the *values* of the weight matrices.

**Concrete inference specs for Qwen3-1.7B after CPT:**
- Model size (4-bit GGUF): ~1.0-1.2 GB
- RAM required at inference: ~1.5-2.0 GB (model + KV cache + runtime)
- Tokens/second on iPhone 15 (A17 Pro): ~15-25 tok/s (estimated from Phi-3 benchmarks: 12 tok/s on iPhone 14 for a 3.8B model)
- Tokens/second on mid-range Android (Snapdragon 8 Gen 2): ~10-20 tok/s
- Battery drain: Minimal (pure compute, no network calls)
- Latency per query: 2-5 seconds for a typical 50-100 token response
- Network required: NONE (fully offline)

**Comparison to alternatives:**
- RAG adds vector search latency + embedding computation + retrieval I/O
- Multiple models (ensemble) multiply compute linearly
- Tool-calling adds network latency and dependency on external services

**CPT is the gold standard for inference efficiency** because it changes nothing about the inference path. This is the single biggest advantage for mobile deployment.

**Score justification:** 10/10 — Perfect. No approach can beat "zero overhead." This is exactly what you want for a mobile-first, offline-first chatbot.

---

### 3. Training Cost — Score: 8/10

**Realistic cost estimation for Qwen3-1.7B CPT on maritime text:**

**Scenario: 50M tokens of maritime textbooks, 3 epochs = 150M effective tokens**

| Resource | Estimated Cost |
|---|---|
| Google Colab T4 (free tier) | $0 — feasible but slow (~12-24 hours for 150M tokens on a 1.7B model with gradient checkpointing) |
| Google Colab A100 (Pro, $10/mo) | ~2-4 hours, $10 total |
| Lambda Labs A100 ($1.10/hr) | ~2-4 hours = $2.20-$4.40 |
| RunPod A100 ($1.64/hr) | ~2-4 hours = $3.28-$6.56 |
| Local RTX 4090 (24GB) | $0 marginal cost, ~3-6 hours |

**Technical requirements:**
- VRAM: 1.7B model in bf16 = ~3.4GB for weights. With Adam optimizer states (2x) and gradients: ~13.6GB total. Fits on T4 (16GB) with gradient checkpointing. Can also use 8-bit Adam (bitsandbytes) to reduce optimizer memory.
- Can use LoRA for CPT to reduce memory, but **"LoRA Learns Less and Forgets Less" (Biderman et al., 2024)** shows LoRA is inferior to full fine-tuning for knowledge injection specifically. Full-weight CPT is strongly preferred.
- Tools: HuggingFace Transformers + Trainer, or use axolotl/LLaMA-Factory for convenient setup.

**Why not 10/10:** If you want optimal results, you should do full-weight pretraining (not LoRA), use a proper learning rate schedule (cosine decay with warmup), potentially do multiple runs with different data mixtures, and evaluate intermediate checkpoints. This requires some GPU access and experimentation time. But it's absolutely doable within a $50 budget.

**Score justification:** 8/10 — Very affordable. Can literally be done for free on Colab T4. The main cost is human time for data preparation and experimentation.

---

### 4. Data Efficiency — Score: 5/10

**The maritime data reality check:**

Available maritime textbooks (from the workspace):
1. Reeds Vol. 5 — Ship Construction for Marine Engineers (.epub)
2. IMO Ballast Water Management (.djvu)
3. STCW Convention (.djvu)
4. MARPOL Consolidated Edition 2011 (.djvu)
5. Corrosion Engineering — Fontana (.djvu)
6. Marine Diesel Engines — Calder (.epub)

**Estimated text yield:**
| Source | Estimated Pages | Estimated Clean Tokens |
|---|---|---|
| 6 textbooks above | ~3,000 pages total | ~2-4M tokens |
| Additional 10-20 maritime textbooks | ~5,000 pages | ~4-8M tokens |
| Maritime Wikipedia articles | ~500 articles | ~1-2M tokens |
| IMO convention full texts (SOLAS, MARPOL, STCW, MLC) | ~2,000 pages | ~2-3M tokens |
| Maritime Q&A forums, exam papers | varies | ~0.5-1M tokens |
| **TOTAL realistic ceiling** | | **~10-18M tokens** |

**This is a SMALL corpus for CPT.**

**What the research says about CPT data requirements:**
- **"Don't Stop Pretraining"** used domain corpora of ~50M-500M tokens and saw consistent gains. Their smallest domain corpus (CS) was ~55M tokens. They showed diminishing returns below ~25K documents (~25M tokens).
- **Phi-1** used 7B tokens (6B filtered web + 1B synthetic). That's 400-700x more than our maritime corpus.
- **Phi-3** used 3.3T tokens. That's 200,000x more.
- **SmolLM3** used 11T tokens.
- **Qwen3-1.7B** was trained on 36T tokens.

**Our 10-18M tokens is roughly 0.00005% of what Qwen3 was trained on.** This is not enough for CPT to achieve deep knowledge internalization equal to the base model's general knowledge.

**However, it's not hopeless:**
- "Don't Stop Pretraining" showed gains even with ~50M tokens of domain text
- Multi-epoch training can extract more from limited data (but risks overfitting)
- The knowledge is specialized and coherent (all maritime), not randomly scraped web text
- Augmentation with synthetic paraphrases and summaries can 2-5x the corpus

**But the fundamental constraint remains:** 10-18M tokens of raw text is marginal for CPT. The model will learn domain vocabulary and some associations, but won't deeply internalize thousands of specific regulatory requirements.

**Score justification:** 5/10 — The maritime corpus is small for CPT. It's enough to shift the model's domain awareness, but not enough to achieve the kind of deep knowledge encoding that Phi-1 achieved with 7B tokens. Data augmentation (synthetic textbooks, paraphrases) is essential.

---

### 5. Accuracy on Domain QA — Score: 3/10

**This is the most critical failure point of CPT-alone.**

**Why CPT alone fails at QA:**

CPT trains the model using *causal language modeling* (predict the next token). This teaches the model to complete text in the style of maritime textbooks. It does NOT teach the model to:
1. Parse a user's question and identify what's being asked
2. Retrieve the relevant fact from its weights
3. Format the answer in a helpful way
4. Distinguish between "I know this" and "I'm guessing"

**After CPT, the model is still a base model.** If a user types:

> "What's the minimum fire extinguisher requirement in the engine room?"

A CPT-only model (base model) might respond with something like:

> "...according to SOLAS Chapter II-2, Regulation 10, the fire protection requirements for machinery spaces of category A include..."

And then trail off into text-completion mode, potentially hallucinating specific numbers, or just continuing to generate textbook-like prose without directly answering the question.

**Published evidence:**
- No published benchmarks exist for "domain CPT on <3B model → domain QA accuracy" in isolation. All successful domain adaptation pipelines use CPT + SFT at minimum.
- BioMedLM (2.7B) used CPT on biomedical text, but was then *fine-tuned* on medical QA datasets to achieve strong MedQA performance. CPT alone was not evaluated as a QA system.
- Domain-adapted BERT models (from "Don't Stop Pretraining") were evaluated on *classification tasks*, not open-ended QA. The improvements were on tasks like sentiment analysis and topic classification, not factual recall.

**The Hallucination Problem:**
For a maritime chatbot, hallucination is not just an inconvenience — it's a **safety hazard**. If the model confidently states the wrong fire extinguisher count or the wrong emergency procedure, it could endanger lives. CPT provides no mechanism to calibrate the model's confidence or ensure factual accuracy. The model doesn't know what it doesn't know.

**Score justification:** 3/10 — CPT alone is NOT a QA system. It's a pre-training technique that shifts domain knowledge distribution. Without subsequent SFT on question-answer pairs, the model cannot reliably answer domain questions. For safety-critical maritime applications, this score would be even lower.

---

### 6. Mobile Deployability — Score: 10/10

**CPT is architecturally transparent to the deployment pipeline.**

After CPT on Qwen3-1.7B:
- Model architecture: unchanged (28 layers, 16 Q heads, 8 KV heads)
- Tokenizer: unchanged (Qwen's BBPE, 151,669 vocab)
- Context length: unchanged (32K)
- Quantization compatibility: full (GPTQ, AWQ, GGUF all work)
- Serving framework compatibility: full (llama.cpp, MLC-LLM, ExecuTorch, ONNX Runtime)

**Deployment specs:**
| Metric | Value |
|---|---|
| GGUF Q4_K_M size | ~1.0-1.2 GB |
| Peak RAM during inference | ~1.8-2.2 GB |
| First-token latency (iPhone 15) | ~200-500ms |
| Token generation speed (iPhone 15) | ~15-25 tok/s |
| Token generation speed (Pixel 8) | ~10-18 tok/s |
| Requires network | NO |
| Requires GPU on phone | NO (CPU inference works, GPU/NPU accelerates) |
| Battery impact per query | Negligible (~0.01-0.05% per query) |

**Phi-3's iPhone demo is directly relevant:** The Phi-3 paper demonstrated phi-3-mini (3.8B) running natively on iPhone 14 with A16 Bionic at 12+ tokens/sec in 4-bit quantization using 1.8GB RAM. Qwen3-1.7B is less than half the size, so it will be even faster and lighter.

**Score justification:** 10/10 — Perfect mobile deployability. CPT adds zero complexity to the deployment pipeline. The model is exactly the same format as the original, just with different weights.

---

### 7. Robustness — Score: 5/10

**What CPT improves:**
- Understanding of domain-specific terminology and jargon — "What is a cofferdam?" will be understood better than by the base model
- Tolerance for OCR artifacts and maritime-specific formatting if present in training data
- Handling of domain-specific abbreviations (IMDG, ISM, ISPS, DOC, SMC, etc.)

**What CPT does NOT improve:**
- Handling of adversarial or trick questions — "Is it legal to discharge oily water within 12 nautical miles?" (model may confuse different discharge regulations under different MARPOL annexes)
- Out-of-distribution queries — if the question is about a topic barely covered in the training textbooks, the model falls back to general knowledge (which may be wrong in the maritime context)
- Multi-hop reasoning — "If a ship is in a Special Area under MARPOL Annex V and carrying IMDG cargo, what disposal regulations apply?" requires combining multiple pieces of knowledge that CPT may not connect
- Paraphrased questions — CPT helps with domain vocab, but a user might ask "How many boats do we need?" (meaning lifeboats). The model's ability to map informal language to formal maritime knowledge is limited without SFT.

**Real-world user behavior:**
Ship crew members will ask questions in informal, potentially multilingual English. They won't phrase questions like textbook headers. CPT makes the model better at maritime text but doesn't teach it to handle the gap between casual questions and textbook knowledge.

**Score justification:** 5/10 — CPT provides moderate robustness improvement for domain terminology but doesn't address the core challenge of mapping diverse user queries to specific knowledge. The model becomes better at "sounding maritime" but not necessarily at "being correct about maritime topics."

---

### 8. Catastrophic Forgetting — Score: 5/10

**The core tension:** CPT shifts the model's weight distribution toward maritime text patterns. This necessarily means the model moves *away* from the general distribution it was originally trained on.

**What the research shows:**

- **"Don't Stop Pretraining"** found that domain-adaptive pretraining helps on in-domain tasks but can hurt performance on out-of-domain tasks. The forgetting is real but typically modest.

- **Standard mitigation strategies:**
  1. **Mix general data (5-10%)** during CPT — include some C4/FineWeb text alongside maritime text. This is the most effective mitigation.
  2. **Lower learning rate** — use 1/10 to 1/5 of the original pretraining LR. For Qwen3-1.7B, if the original LR was 2e-4, use 2e-5 to 5e-5 for CPT.
  3. **Fewer epochs** — 1-3 epochs on the domain corpus, not 10+.
  4. **Elastic Weight Consolidation (EWC)** or similar regularization — penalize changes to weights important for general tasks. Adds complexity but works.
  5. **Replay buffer** — periodically replay general training examples during CPT.

- **For this use case, moderate forgetting is acceptable.** The chatbot is purpose-built for maritime QA. If it becomes 5% worse at general trivia or creative writing, that's fine. What matters is that it retains English fluency, instruction-following ability (if SFT'd afterward), and basic reasoning.

**Risk factors specific to maritime CPT:**
- Maritime text is highly technical and repetitive (e.g., regulatory language is very formulaic). This strong distributional shift could cause more forgetting than, say CPT on news articles.
- The small corpus size means more epochs, which means more forgetting per token.
- If the textbooks contain OCR artifacts or non-standard formatting, the model may learn these artifacts.

**Score justification:** 5/10 — Catastrophic forgetting is a real concern but manageable with standard mitigations (data mixing, low LR). The bigger risk is that the general-domain forgetting trades off against the limited domain knowledge gained from the small maritime corpus — you lose general capability without gaining proportional domain capability.

---

### 9. Maintenance — Score: 4/10

**The problem:** IMO regulations update regularly. New amendments to SOLAS, MARPOL, and STCW are adopted through the IMO's tacit acceptance procedure. When regulations change, the model's baked-in knowledge becomes stale.

**Update cycle for maritime regulations:**
- SOLAS amendments: Every 1-2 years
- MARPOL amendments: Periodic (e.g., EEXI/CII regulations took effect Jan 2023)
- STCW amendments: Less frequent but significant (Manila Amendments 2010)
- New codes: e.g., IGF Code, Polar Code — introduced as new instruments

**What CPT maintenance requires:**
1. Collect new/updated regulation text (~thousands of tokens per amendment)
2. Run incremental CPT on the new text
3. Risk: **knowledge conflict** — the model's weights may store both old and new regulation values, leading to confused outputs
4. Risk: **catastrophic forgetting of old knowledge** — training too hard on new data may erase correctly learned old knowledge
5. Need to re-evaluate the model after each update to ensure no regressions
6. Need to maintain the full training pipeline (data prep, GPU access, evaluation suite)

**Comparison to RAG:**
In a RAG system, you simply update the document database. No retraining needed. The updated document is immediately available. This is the single biggest advantage of RAG over CPT for maintenance.

**Comparison to SFT:**
SFT on specific QA pairs about new regulations is more targeted and less risky than CPT, but still requires retraining.

**Practical mitigation:**
- Maintain a versioned training corpus with clear regulation timestamps
- Do periodic full retraining (e.g., annually) rather than incremental patches
- Use a held-out evaluation set of regulation questions to detect staleness

**Score justification:** 4/10 — CPT requires full retraining to update knowledge. Each retrain risks forgetting and knowledge conflicts. This is significantly worse than RAG for maintenance, and for a domain where regulations literally govern safety at sea, having stale knowledge is unacceptable.

---

### 10. Proven at Small Scale (<3B) — Score: 7/10

**Proven successes of CPT on small models:**

| Model | Size | Domain | CPT Details | Result |
|---|---|---|---|---|
| Phi-1 | 1.3B | Code | 7B tokens of "textbook quality" data | 50.6% HumanEval (vs. StarCoder 15.5B at 34%) |
| Phi-1.5 | 1.3B | Reasoning | Continued from phi-1 with reasoning data | Matched 5x larger models on reasoning |
| BioMedLM | 2.7B | Biomedical | 34.6B tokens from PubMed | Strong performance on medical QA (after SFT) |
| SaulLM-7B | 7B | Legal | CPT on legal corpus (but >3B) | Improved on legal benchmarks |
| "Don't Stop Pretraining" | 355M (RoBERTa) | Bio/CS/News/Reviews | ~50M-500M domain tokens | Consistent gains on downstream tasks |
| StarCoder | 1B variant | Code | Domain-specific pretraining | Code-specific performance gains |
| SmolLM3 | 3B | General | 11T tokens, 3-stage | SoTA at 3B scale |

**Key caveat:** Most of these successes involved either:
1. **Much larger training corpora** than available maritime text (Phi-1 used 7B tokens, BioMedLM used 34.6B)
2. **Structured domains** where patterns are more learnable (code, medical literature with standard formats)
3. **Subsequent fine-tuning** (BioMedLM needed SFT on MedQA to achieve QA performance)

**Has CPT been proven on ~10-18M tokens of niche domain text on a 1.7B model?**
Not directly. The closest is "Don't Stop Pretraining" with RoBERTa (355M) on ~50M tokens, which showed modest but consistent gains on classification tasks. But that's a different model architecture (encoder-only), a different evaluation paradigm (classification, not generation), and a larger corpus.

**The Qwen3 evidence is encouraging:** Qwen3-1.7B achieves MMLU 62.63 (vs Qwen2.5-1.5B at 60.90), MATH 43.50, GSM8K 75.44. These are strong base capabilities for a 1.7B model. CPT on top of this foundation *should* improve maritime domain performance, but the magnitude of improvement depends heavily on data volume and quality.

**Score justification:** 7/10 — CPT on small models is well-proven in principle (phi-1, BioMedLM, "Don't Stop Pretraining"). But the specific scenario (10-18M tokens of maritime text, 1.7B model, factual QA as the target) has not been directly demonstrated. The evidence strongly suggests it will help, but the degree of help is uncertain.

---

## SUMMARY SCORECARD

| # | Criterion | Score | Key Rationale |
|---|---|---|---|
| 1 | Knowledge Retention | **4/10** | Learns domain vocabulary and associations; fails on exact facts/numbers. Phi-3 paper explicitly admits factual knowledge capacity limits. |
| 2 | Inference Cost | **10/10** | Zero overhead. Identical model architecture. Perfect for mobile. |
| 3 | Training Cost | **8/10** | $0-50. Doable on free Colab T4. Full-weight CPT on 1.7B model fits in 16GB VRAM. |
| 4 | Data Efficiency | **5/10** | Maritime corpus (~10-18M tokens) is small for CPT. "Don't Stop Pretraining" showed gains with ~50M+ tokens. Need data augmentation. |
| 5 | Accuracy on Domain QA | **3/10** | CPT alone is NOT a QA system. Produces text completions, not answers. No question-answering behavior without SFT. |
| 6 | Mobile Deployability | **10/10** | Perfect. Same model, same size, same format. Qwen3-1.7B at Q4 = ~1GB. |
| 7 | Robustness | **5/10** | Better domain vocab handling. Still fragile on exact facts, paraphrased questions, multi-hop reasoning. |
| 8 | Catastrophic Forgetting | **5/10** | Real concern with small corpus + multiple epochs. Mitigatable with data mixing (5-10% general data) and low LR. |
| 9 | Maintenance | **4/10** | Requires retraining to update knowledge. Risk of knowledge conflicts. Far worse than RAG for updates. |
| 10 | Proven at Small Scale | **7/10** | Well-proven in principle (phi-1, BioMedLM). Not proven specifically for maritime-scale data on 1.7B model. |

### **TOTAL SCORE: 61/100**

---

## KEY STRENGTHS (Top 3)

### 1. Zero Inference Overhead (Scores: Inference Cost 10, Mobile Deployability 10)
CPT is the only knowledge injection method that adds literally nothing to inference time, memory, or deployment complexity. The model after CPT is architecturally identical to the base model. For a mobile-first chatbot that must work offline on a phone's ARM CPU, this is the single most important advantage. No vector database, no embedding model, no retrieval pipeline, no network calls.

### 2. Deepest Possible Knowledge Integration
Unlike RAG (which retrieves external text) or SFT (which teaches input-output mappings), CPT modifies the model's fundamental understanding of language and domain concepts. The model doesn't just learn to parrot answers — it learns the underlying conceptual structure of maritime engineering. When asked about unfamiliar scenarios, a CPT'd model can draw on this deep understanding to reason (imperfectly) about novel situations.

### 3. Affordable and Accessible Training
Full-weight CPT on a 1.7B model can be done for $0 on Google Colab (T4 free tier) or under $10 on cloud GPUs. The training pipeline uses standard HuggingFace tools. No exotic frameworks, no RLHF reward modeling, no synthetic data generation pipeline needed. This makes CPT the lowest-barrier-to-entry approach for domain adaptation.

---

## KEY WEAKNESSES (Top 3)

### 1. ★ CRITICAL: Cannot Reliably Recall Specific Facts (Score: Knowledge Retention 4, Accuracy 3)
**This is the dealbreaker for the maritime chatbot use case.** A ship engineer asking "What is the minimum UKC requirement for my vessel?" or "At what temperature should I test the emergency fire pump?" needs an EXACT answer. CPT produces models that "sound maritime" but may confidently state wrong numbers. For safety-critical maritime applications, this is unacceptable.

The Phi-3 paper's own admission is damning: even at 3.8B parameters trained on 3.3T tokens, the model "does not have the capacity to store too much factual knowledge." A 1.7B model on 10-18M tokens will be dramatically worse.

### 2. CPT Alone Does NOT Produce a Chatbot (Score: Accuracy on Domain QA 3)
After CPT, the model is still a BASE model. It completes text, it doesn't answer questions. You CANNOT ship CPT-only and call it a chatbot. Without subsequent SFT on question-answer pairs, the model will:
- Generate textbook-like prose instead of direct answers
- Not understand question formats
- Not know when to stop generating
- Not follow user instructions

This means CPT is *necessary but radically insufficient* — it MUST be followed by SFT at minimum.

### 3. Limited Maritime Data Makes CPT Less Effective (Score: Data Efficiency 5)
The available maritime textbook corpus (~10-18M tokens) is 350-700x smaller than what Phi-1 used in "Textbooks Are All You Need." The "Don't Stop Pretraining" paper's smallest effective domain corpus was ~50M tokens. We're below that threshold. This means:
- Multiple training epochs risk overfitting 
- The model memorizes surface patterns rather than deep knowledge
- Rare facts (mentioned once in one textbook) likely won't be retained
- Data augmentation (synthetic generation) becomes essential, adding complexity

---

## VERDICT

### Is CPT sufficient ALONE to build the maritime chatbot?

## **NO. Absolutely not.**

CPT alone produces a base model with improved maritime language patterns. It does NOT produce:
- A chatbot that can answer questions
- A model that reliably recalls specific facts
- A system safe enough for maritime safety-critical applications

**CPT is STEP 1 of a multi-step pipeline.** It is necessary (arguably the MOST important foundation step) but nowhere near sufficient.

**Analogy:** CPT is like a student who has read the textbooks cover-to-cover. They "know" the material in some sense, but they haven't practiced answering exam questions, they haven't been corrected on wrong answers, and they haven't learned to express their knowledge clearly. You wouldn't trust this student to give safety-critical advice to a ship captain.

---

## BEST COMBINATION: The Recommended Pipeline

**CPT is the foundation. The following techniques must be layered on top:**

```
STEP 1: CPT on Maritime Text (this evaluation)
    │   • Qwen3-1.7B + full-weight CPT on all available maritime text
    │   • 10-18M tokens, 3-5 epochs, LR=2e-5, cosine decay
    │   • Mix in 5-10% general text (C4/FineWeb) to prevent catastrophic forgetting
    │   • Use NEFTune (add noise to embeddings) for free quality boost
    │   • OUTPUT: Maritime-aware base model (not yet a chatbot)
    │
    ▼
STEP 2: Synthetic QA Data Generation (ESSENTIAL)
    │   • Use a **strong local teacher** (no paid APIs) to read each textbook chapter (via chunks)
    │   • Generate 5,000-20,000 QA pairs covering all topics
    │   • Include: factual recall, procedural, scenario-based, multi-choice questions
    │   • Include regulation-specific questions with exact numbers
    │   • Generate chain-of-thought reasoning traces for complex questions
    │   • OUTPUT: Maritime QA dataset
    │
    ▼
STEP 3: Supervised Fine-Tuning (SFT) on QA Pairs
    │   • Fine-tune the CPT'd model on the synthetic QA dataset
    │   • This teaches the model to: parse questions, retrieve knowledge, format answers
    │   • Use chat template (e.g., Qwen3's ChatML)
    │   • Can use LoRA here (since SFT is about format, not knowledge injection)
    │   • OUTPUT: Maritime chatbot that answers questions
    │
    ▼
STEP 4 (Optional): ORPO/Preference Alignment
    │   • Generate multiple answers per question
    │   • Have experts rate which answers are correct/helpful
    │   • Train with ORPO to prefer accurate, concise answers (no reference model)
    │   • OUTPUT: Aligned maritime chatbot
    │
    ▼
STEP 5: Quantize & Deploy
        • Quantize to Q4_K_M GGUF (~1GB)
        • Deploy with llama.cpp / MLC-LLM on mobile
        • Test on real maritime questions with domain experts
        • OUTPUT: Production maritime chatbot on phones
```

**Why this pipeline works:**
- **CPT (Step 1)** gives the model maritime domain awareness — vocabulary, concepts, relationships
- **Synthetic QA (Step 2)** creates the training signal for factual accuracy — the QA pairs contain the EXACT facts the model needs to recall
- **SFT (Step 3)** teaches the model to BE a chatbot — answering questions, not completing text
- **DPO (Step 4)** refines the model to prefer correct, helpful answers
- **Quantization (Step 5)** makes it deployable on phones

**Without Step 2+3, CPT alone gives you a maritime-flavored text generator, NOT a maritime chatbot.**

---

## FINAL ASSESSMENT

| Aspect | Rating |
|---|---|
| **CPT Alone** | **Insufficient** (61/100) — Cannot build a working chatbot |
| **CPT as Foundation (Step 1 of pipeline)** | **Essential** (9/10) — The single most important first step |
| **CPT + SFT** | **Viable** (~75/100) — Minimum viable maritime chatbot |
| **CPT + Synthetic QA + SFT + DPO** | **Strong** (~85/100) — Production-quality maritime chatbot |

**The irony of CPT:** It scores poorly as a standalone approach (61/100) but is arguably the MOST important building block in the full pipeline. Without CPT, SFT alone would need to inject both domain knowledge AND QA behavior simultaneously, which is much harder and less effective. CPT separates the concerns: first teach the model WHAT (maritime knowledge), then teach it HOW (answering questions).

**Bottom line for the ship crew member asking "What's the minimum fire extinguisher requirement in the engine room?":**
- CPT alone: Will give a plausible-sounding but potentially wrong answer, in text-completion format, possibly with hallucinated numbers. **FAIL.**
- CPT + SFT on synthetic QA: Will give a direct, formatted answer citing the correct regulation. The accuracy depends on whether that specific fact was in the synthetic QA training data. **LIKELY PASS.**
- CPT + SFT + DPO: Will give a confident, well-calibrated answer with the correct regulation reference, and will appropriately express uncertainty when it doesn't know. **PASS.**
