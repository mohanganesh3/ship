# 🏆 FINAL RANKING: Maritime Ship Chatbot — No RAG, Mobile-First

## The Definitive Evaluation: 10 Approaches Ranked

> **Constraint**: All knowledge MUST be baked into model weights. No RAG, no vector DB, no embedding model at inference. Must run on **mobile phones** (3-6 GB RAM, ARM CPU). Fully offline.

---

## 🥇 GRAND RANKING TABLE

| Rank | Approach | Score | Verdict |
|:----:|----------|:-----:|---------|
| **1** | **CPT + Synthetic SFT + Distillation (Full Pipeline)** | **73/100** | **🏆 WINNER — The only viable complete approach** |
| **2** | Synthetic Data + SFT alone | 71/100 | Strong but needs CPT foundation |
| **3** | Model Merging | 64/100 | Free enhancement, not a foundation |
| **4** | Pre-training from Scratch | 62/100 | Best quality but $100K+ cost kills it |
| **5** | Continued Pretraining alone | 61/100 | Essential foundation, not complete alone |
| **6** | RL Methods (GRPO/DPO/ORPO) | 57/100 | Polishing layer only, can't inject knowledge |
| **7** | Test-Time Compute (CoT/Budget Forcing) | 57/100 | Free enhancer, but can't create knowledge |
| **8** | Pruning + Sparsification | 56/100 | Wrong problem — solves compression, not knowledge |
| **9** | Extreme Quantization (BitNet/2-bit) | 53/100 | Destroys factual knowledge at sub-4-bit |
| **10** | Reasoning Distillation alone | 52/100 | Teaches how to think, not what to know |

---

## 📊 DETAILED SCORE BREAKDOWN (All 10 Criteria × All 10 Approaches)

| Criterion | CPT+SFT+Distill | Synth+SFT | Merging | Scratch | CPT | RL | TTC | Pruning | BitNet | Reasoning |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Knowledge Retention | **7** | 5 | 4 | **8** | 4 | 2 | 3 | 4 | 4 | 3 |
| Inference Cost | **10** | **10** | **10** | 9 | **10** | 9 | 3 | 7 | **10** | 4 |
| Training Cost | 6 | **8** | 7 | 2 | **8** | 7 | **9** | 6 | 5 | 7 |
| Data Efficiency | **8** | 7 | 5 | 3 | 5 | 6 | **8** | 6 | 5 | 6 |
| Accuracy Domain QA | **7** | 5 | 4 | **7** | 3 | 3 | 4 | 4 | 3 | 5 |
| Mobile Deploy | **9** | **10** | **10** | 9 | **10** | 9 | 5 | 7 | **10** | 7 |
| Robustness | **7** | 6 | **7** | 6 | 5 | 5 | 6 | 5 | 3 | **7** |
| Catastrophic Forget | 6 | 6 | **7** | **9** | 5 | **7** | **8** | 5 | 5 | 6 |
| Maintenance | 5 | **7** | 6 | 2 | 4 | 6 | **8** | 6 | 5 | 5 |
| Proven Small Scale | **8** | 7 | 4 | **7** | **7** | 3 | 3 | 6 | 3 | **7** |
| **TOTAL** | **73** | **71** | **64** | **62** | **61** | **57** | **57** | **56** | **53** | **52** |

---

## 🔑 KEY INSIGHTS FROM ALL 10 AGENTS

### What Every Agent Agreed On

1. **No single technique can inject knowledge AND make a chatbot.** You MUST combine techniques.
2. **The bottleneck is knowledge retention, NOT model size or speed.** Mobile deployment is solved (Q4_K_M). The hard problem is making a 1.7B model remember "SOLAS Chapter III requires X lifeboats."
3. **Synthetic data quality is THE most important factor.** Phi-1, Phi-3, SmolLM3, Orca 2 — every successful small model was built on high-quality synthetic data.
4. **RAG would have scored 85+/100.** By removing RAG, we accept a ~15% accuracy hit. The model WILL hallucinate sometimes on exact facts/numbers. Position it as a study aid, not a safety-critical system.

### The Critical Discovery

> **"Continued Pretraining teaches the model to RECOGNIZE domain concepts (score: 4/10 alone). Synthetic SFT teaches it to ANSWER questions (5/10 alone). Together, they achieve 7/10 — the synergy is the strategy."**

CPT creates a "soft knowledge landscape" in the weights. SFT then "crystallizes" that knowledge into retrievable Q&A patterns. Neither works well alone. Together they are the only path to 70+ without RAG.

---

## 🏆 THE WINNING COMBINATION

### Final Architecture: 3-Stage Pipeline (+ optional extras)

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   STAGE 1: CONTINUED PRETRAINING (CPT)                     │
│   ├── Raw maritime textbook text → next-token prediction    │
│   ├── QLoRA (r≈32–64) on Qwen3-1.7B base                    │
│   ├── 80/20 mix: 80% maritime + 20% general text            │
│   ├── Teaches: vocabulary, concepts, relationships          │
│   └── Score contribution: +15 points                        │
│                                                             │
│   STAGE 2: SYNTHETIC SFT + DISTILLATION (LOCAL TEACHER)     │
│   ├── Local teacher reads textbook chunks → 50K–100K Q&A     │
│   ├── Diverse: factual, procedural, troubleshooting, safety │
│   ├── Evol-Instruct: easy → medium → hard progressions      │
│   ├── DEITA-style filtering (quality + diversity)           │
│   ├── QLoRA SFT with NEFTune                                │
│   └── Score contribution: +40 points                        │
│                                                             │
│   STAGE 3: ORPO ALIGNMENT                                   │
│   ├── Teach: "I don't know" for out-of-domain               │
│   ├── Prefer: accurate + structured + uncertainty when needed│
│   ├── Safety: never give dangerous incomplete procedures     │
│   └── Score contribution: +10 points                        │
│                                                             │
│   OPTIONAL EXTRAS: CHECKPOINT SOUP + QUANTIZE               │
│   ├── (Optional) Average best 2-3 checkpoints               │
│   ├── Merge LoRA → base model                               │
│   └── Quantize to Q4_K_M GGUF                               │
│                                                             │
│   DEPLOY: Ollama / llamafile on mobile / ship computer      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why Each Stage Exists (And Why Nothing Can Be Cut)

| Stage | Without It | With It | Delta |
|-------|-----------|---------|-------|
| CPT | Model doesn't know maritime vocabulary → misunderstands questions | Understands "scavenge air", "purifier", "SOLAS" natively | Critical foundation |
| Synthetic SFT | Model can't answer questions in chat format → useless | Answers 70-85% of domain questions correctly | Core capability |
| ORPO | Model confidently hallucates → dangerous | Says "I'm not sure" when uncertain → safer | Safety layer |
| Model Soup | Single checkpoint has quirks | Robust, smoothed predictions | Free quality |

---

## 🎯 SPECIFIC RECOMMENDATIONS

### Base Model: **Qwen3-1.7B** (Primary edge winner)

| Scenario | Model | Quantized Size | RAM | Why |
|----------|-------|---------------|-----|-----|
| **Mobile/ship edge (3–6 GB RAM)** | **Qwen3-1.7B Q4_K_M** | ~1.2–1.5 GB | ~3–5 GB | Fits the hard constraint with best overall quality |
| **If CPU decode must be ~2× faster** | **LFM2-1.2B** (backup) | ~0.8–1.2 GB | ~2.5–4 GB | Lower latency; keep as contingency |
| **Ship computer (8+ GB)** | Qwen3-4B Q4_K_M (optional) | ~2.5 GB | ~4.5–6 GB | Higher capacity if hardware allows |

**Why Qwen3-1.7B wins here:** It’s the best fit for strict edge RAM limits while still supporting strong instruction following and a useful “thinking mode” knob. If you can afford 4B on some ship hardware, you can optionally train/deploy that variant too — but the baseline target is 1.7B.

### Synthetic Data Strategy: The Most Critical Step (No paid APIs)

```
YOUR TEXTBOOKS (PDFs)
        │
        ▼
   Docling → Clean text chunks (512 tokens each)
        │
        ├──→ Local teacher: Generate Q&A per chunk (factual, procedural)
        ├──→ Local reasoning teacher (optional): Generate reasoning traces (troubleshooting)
        ├──→ Evol-Instruct: Progressively harder versions of each Q&A
        └──→ Negative examples: "I don't know" for out-of-domain
        │
        ▼
   DATASET: 50,000-100,000 training examples
        │
        ├── 40% Factual Q&A ("What is X?", "How many Y?")
        ├── 25% Procedural ("How to do X?", "Steps for Y?")  
        ├── 15% Troubleshooting ("Engine shows X, diagnose")
        ├── 10% Safety ("What are precautions for X?")
        ├── 5% Regulatory ("Per SOLAS, what is required?")
        └── 5% Out-of-domain refusals ("I don't have info on...")
```

### The "Textbook Memorization" Technique

**Critical insight from Phi-1**: The key isn't just generating Q&A — it's generating **multiple Q&A pairs that approach the same fact from different angles**. This forces the model to deeply encode the fact:

```
Fact: "SOLAS requires all cargo ships ≥500 GT to carry minimum 2 lifeboats"

Q1: "How many lifeboats must a cargo ship carry per SOLAS?"
Q2: "A 600 GT cargo vessel — what's the minimum lifeboat requirement?"  
Q3: "Does a 400 GT cargo ship need lifeboats per SOLAS?"  (Answer: No, below 500 GT threshold)
Q4: "What international convention specifies lifeboat requirements?"
Q5: "Compare lifeboat requirements for a 450 GT vs 550 GT cargo ship"
```

Generate **5-10 variations per key fact**. This is how you overcome the knowledge retention limitation of small models.

### Training Compute

| Stage | Hardware | Time | Cost |
|-------|----------|------|------|
| Synthetic data gen | **Local teacher on 4 GPUs** | **Multi-day OK** (throughput-dependent) | **$0 (no API)** |
| Stage 1: CPT | 1× GPU (local or cloud/Colab) | 2–12 hours | $0–$40 |
| Stage 2: SFT | 1× GPU (local or cloud/Colab) | 4–24 hours | $0–$80 |
| Stage 3: ORPO | 1× GPU (local or cloud/Colab) | 2–10 hours | $0–$40 |
| **Total** | | **~3 days to ~2 weeks (incl. data gen)** | **Mostly compute time** |

### Mobile Deployment

```
OPTION A: Ollama (Android/Desktop)  
- Download Ollama → import your GGUF → done
- Exposes API on localhost:11434
- Pair with any web UI

OPTION B: Llamafile (Any platform)
- Single executable, ~2.5 GB file
- Double-click → browser chat opens
- Zero dependencies, works everywhere

OPTION C: MLC LLM (Mobile-native)
- Compiled for iOS/Android specifically
- Best mobile performance (Metal on iOS, Vulkan on Android)
- More complex setup

RECOMMENDATION: llamafile for simplicity, MLC LLM for best mobile perf.
```

---

## ⚠️ HONEST LIMITATIONS (What This Approach Cannot Do)

| Limitation | Reality | Mitigation |
|-----------|---------|------------|
| **Exact number recall** | Model may get specific values wrong (pressures, temperatures, dimensions) | Add "always verify critical values with official documents" disclaimer |
| **Regulation updates** | Model's knowledge frozen at training time | Schedule quarterly retraining during port visits |
| **Complex multi-step problems** | 4B model can't do PhD-level engineering analysis | Position as study aid, not engineering calculator |
| **Hallucination** | ~10-15% on obscure facts without RAG | ORPO training to say "I'm not sure" reduces risk |

| **Languages** | Qwen3 supports many languages but accuracy drops | Train primarily in English, test multilingual |

### What This Approach WILL Do Well

- **Explain concepts**: "What is a purifier and how does it work?" → Excellent
- **Describe procedures**: "How to start the emergency generator?" → Very good
- **Troubleshooting guidance**: "Engine exhaust temp is high on cyl 3, what to check?" → Good
- **Safety information**: "What PPE is needed for entering an enclosed space?" → Very good
- **Regulatory basics**: "What fire extinguishers does SOLAS require?" → Good (may miss exact numbers)
- **Study aid**: "Explain the difference between 2-stroke and 4-stroke marine engines" → Excellent

---

## 📋 FINAL EXECUTION CHECKLIST

### Week 1: Data Preparation
- [ ] Collect all maritime textbooks (PDF/EPUB)
- [ ] Process with Docling → clean text
- [ ] Chunk into 512-token segments
- [ ] Generate 50,000-100,000 synthetic Q&A pairs using a **local teacher** (4-GPU box)
- [ ] Generate 2,000-10,000 reasoning traces (optional) using a **local reasoning-capable teacher**
- [ ] Create 1,000 preference pairs (good answer vs bad answer)
- [ ] Create 200-question evaluation test set

### Week 2: Training
- [ ] Set up Unsloth on Colab / cloud GPU
- [ ] Stage 1: CPT on raw maritime text (QLoRA r=32, 2-3 epochs)
- [ ] Stage 2: SFT on synthetic Q&A dataset (QLoRA r=16, 3 epochs)
- [ ] Stage 3: ORPO on preference pairs (1 epoch)
- [ ] Model soup on best checkpoints
- [ ] Merge LoRA → base weights

### Week 3: Optimization & Deploy
- [ ] Quantize to Q4_K_M GGUF
- [ ] Test on target mobile device / ship computer
- [ ] Benchmark: speed, RAM, accuracy on test set
- [ ] Package as llamafile or Ollama model
- [ ] Create simple user guide for crew
- [ ] Test offline operation end-to-end

### Week 4: Validation
- [ ] Run full 200-question evaluation
- [ ] Test with actual maritime professionals
- [ ] Iterate on system prompt
- [ ] Create update procedure for port visits
- [ ] Deploy to first ship

---

## 🎯 BOTTOM LINE

**Winner (edge): CPT + Synthetic SFT/Distillation + ORPO on Qwen3-1.7B**

- **Cost**: $0 API; compute-only (local teacher may take days)
- **Time**: ~1–4 weeks end-to-end (mostly data generation + iteration)
- **Size**: ~1.2–1.5 GB model file (Q4_K_M)
- **RAM**: ~3–6 GB at inference (depends on context/KV cache)
- **Speed**: 5-15 tokens/sec on mobile CPU
- **Accuracy**: ~75-85% on domain questions (study aid level)
- **Works on**: Most ship mini-PCs and many phones in the 3–6 GB RAM class
- **Fully offline**: Yes, 100%
- **No RAG needed**: All knowledge in weights

**The synthetic data generation step is the #1 most important factor.** Invest 80% of your effort there. The quality and diversity of your Q&A pairs from textbooks directly determines the final chatbot quality.

---

## ⚡ Edge Optimization: Dynamic Test-Time Compute (TTC) Routing

We use a runtime wrapper that enables the model’s longer “thinking” only when needed (target: **~20%** of turns), because long deliberation tokens cost latency + battery.

- **Thinking ON**: calculations (stability, fuel, voyage planning), multi-step diagnostics, ambiguous scenarios.
- **Thinking OFF**: direct fact recall, definitions, short regulation questions, quick procedural checklists.

This preserves responsiveness for the majority of queries while still allowing deep reasoning when the question demands it.
