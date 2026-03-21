# MASTER SYNTHESIS: PART 4
**DOCUMENT TITLE:** Technical Implementation & Generative Pipeline
**SOURCE:** Extrapolated directly from the corpus.

## 1. PRETRAINING, KNOWLEDGE INJECTION & DATA
A foundational limit identified across the evaluations: **"Test-Time Compute (TTC) generates zero new facts."** Because the deployment is offline and models are mathematically constrained to 1-3B parameters, factual maritime knowledge (laws, procedures, specs) *requires* physical weight alteration prior to inference.

**Data Sourcing Strategy:**
- Highly specialized literature (GMDSS logs, IMO conventions, marine engineering manuals) forms the core corpus.
- The open-source data availability rating is "Poor." Free domains like Dutch NSIA reports provide an initial backbone.
- Structured web-crawls, semantic textbook parsing (via multi-modal chunking tools like Marker), and parsed EPA regulatory PDFs are required to build the raw knowledge injection stream.

**Phase 1: Continued Pretraining (CPT)**
- **Focus:** 500M to 1B+ raw tokens encompassing exclusively maritime lexicons, laws, and specifications.
- **Goal:** Shift the model's core probabilistic matrix away from unaligned general internet data to exact maritime physics/bureaucracy.
- **Mechanism:** QLoRA-based unsloth CPT pipelines with an 80/20 mix: 80% specialized maritime knowledge and 20% general replay (to avoid catastrophic forgetting of base English/grammar functionality). No format labels required.

## 2. INSTRUCTION TUNING & REASONING DISTILLATION
**Phase 2: Supervised Fine-Tuning (SFT)**
- **Focus:** Question-answering formatting mapping (Instruction/Response pairs).
- **Synthetic Augmentation (no paid APIs):** Run a **local teacher model** on the 4‑GPU machine to generate 50k–100k grounded Q/A pairs strictly referenced against the Phase 1 raw documentation.
- **Quality Control:** Implement DEITA/Evol-Instruct quality filters. Remove verbose "Yes, I can help with that" robotic replies.
- **Goal:** Structure the output layer logically so the model understands *how* to answer queries like a marine engineer without hallucinating outside domain parameters.

## 3. ALIGNMENT & TEST-TIME SCALING
**Phase 3: Preference ALignment (ORPO)**
- Offline hardware cannot support massive Reward Models required for standard RLHF setups.
- **ORPO Solution:** Odds Ratio Preference Optimization directly integrates alignment and SFT into a single step—saving up to 50% VRAM during training while teaching the model the difference between a "safe" ship procedure and a "fatal" miscalculation.

**Phase 4: Test-Time Compute (TTC) Dynamic Routing**
- "Thinking" algorithms (o1/s1 budgets) exponentially increase CPU draw and drain mobile battery levels by generating massive hidden Chain-of-Thought logs.
- Because a 1B edge device model fails entirely at complex math unless prompted to "think", TTC loops are strictly reserved for logic/math pathways (e.g., Voyage planning, Stability calculations, Navigation equations) which represent only ~20% of maritime user queries.
- **Budget Forcing:** A custom system prompt wrapper dynamically injects the `<think>` protocol only when specific syntax conditions are met. Factual lookup requests (e.g., "What is the SOLAS regulation for lifeboats?") simply bypass TTC for instantaneous zero-battery-drain responses since CPT encoded that information structurally.