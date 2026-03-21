# 🚢 Maritime AI Assistant — Complete Production Training Plan
## March 2026 Edition · Research-Grounded · Autopilot-Ready

---

## Preamble: What This Plan Is and Why Every Decision Is Justified

This is a life-safety system. A Chief Engineer alone in the engine room at 0300 will use this. A Deck Officer in poor visibility will use this. A wrong answer from this model is not a user-experience problem — it is a potential casualty, a fire, a vessel loss. Every architectural decision in this plan is traceable to a specific research finding. Nothing is here because it "sounds right."

---

## System State (What Exists Right Now)

### Models on disk
- Teacher: `Qwen3-235B-A22B-Instruct-2507` Q4_K_M, 4 shards, 142 GB total
  - Path: `/home/mohanganesh/ship/models/teacher/Qwen_Qwen3-235B-A22B-Instruct-2507-Q4_K_M/`
- Student A (mobile): `Qwen3-1.7B` base weights
  - Path: `/home/mohanganesh/ship/models/student-1.7b/`
- Student B (tablet/laptop): `Qwen3-4B-Instruct-2507` weights
  - Path: `/home/mohanganesh/ship/models/student-4b/`

### Data artifacts on disk (all in `maritime_pipeline/data/final/`)
- `cpt_corpus.jsonl` — 34,988 records, ~72M tokens, maritime domain text
- `general_replay.jsonl` — 4,772 records, ~10M tokens, clean general English
- `cpt_val_maritime.jsonl` — 1,288 records, held-out, never train on this
- `cpt_val_general.jsonl` — 98 records, held-out, never train on this
- `chunks.jsonl` — 115,783 chunks with difficulty_hint, ready for teacher generation

### Infrastructure on disk
- `llama.cpp` built at `/home/mohanganesh/ship/llama.cpp/build/bin/llama-server`
- Python venv at `/home/mohanganesh/ship/.venv/`

### Training environment (verified)
- Separate training venv: `/home/mohanganesh/ship/.venv-train/` (keeps Wave 1 generation venv untouched)
- Verified via: `scripts/train_python.sh scripts/verify_train_env.py --model-path models/student-1.7b`
  - Python: 3.10.19
  - Torch: 2.1.2+cu118 (torch CUDA: 11.8)
  - CUDA: available, 4× Tesla K80 (sm_37)
  - Stack: Transformers + PEFT + TRL + DeepSpeed (no Unsloth, no bitsandbytes)
  - Verified load test:
    - Loads `Qwen3-1.7B` in fp16 on `cuda:0`
    - Attaches LoRA adapters via PEFT
    - Runs a forward pass and reports loss + VRAM usage
- Notes:
  - `transformers==4.51.3` is required to recognize `model_type: qwen3` for the local weights (see `models/student-1.7b/config.json`).
  - DeepSpeed import is configured to work without a CUDA toolkit (`CUDA_HOME` not set) in the training venv.

### What does NOT exist yet (must be built in this plan)
- `sft_teacher.jsonl` — teacher-generated raw Q/A pairs (Wave 1)
- `sft_curated.jsonl` — filtered, training-ready SFT data
- `orpo_pairs.jsonl` — preference pairs
- `orpo_curated.jsonl` — filtered preference pairs
- Trained model checkpoints (none yet)
- GGUF deploy artifacts (none yet)

---

## The Architecture: Why This Pipeline, Not Something Simpler

The pipeline below implements findings from three convergent research streams active in 2025:

**Stream 1 — openPangu Embedded (Huawei, Sep 2025):** Proved that for 1B-class models, a two-stage curriculum SFT (reasoning-first, then fast-response) combined with offline on-policy knowledge distillation achieves state-of-the-art among billion-parameter models, matching Qwen3-1.7B performance at 1B scale. The key innovation: training data complexity must be matched to the student's current capability, not set once at the start.

**Stream 2 — Qwen3 Technical Report (Alibaba, Apr 2025, updated Jul 2025):** The exact recipe used to train Qwen3-4B involves off-policy distillation in both /think and /no_think modes, followed by on-policy refinement where the student generates and the teacher corrects. This is not a suggestion — it is the documented method that produced the student model we are starting from.

**Stream 3 — Post-training in 2026 (multiple authors):** ORPO as the final alignment pass combines SFT and preference optimization in one objective, eliminating distribution shift between stages. For a domain-specific safety-critical model, this stability property is critical — DPO's sequential SFT-then-preference risks overwriting domain knowledge.

```
FULL PIPELINE (both student models follow this same sequence):

PHASE 0: Data + Infrastructure
  └── Teacher server setup + validation
  └── Wave 1 generation (115k chunks → 15k Q/A pairs)
  └── SuperFiltering (IFD) → sft_curated.jsonl

PHASE 1: CPT (Domain-Adaptive Pretraining)
  └── 3-stage curriculum (50/50 warmup → 80/20 main → 70/30 anneal)
  └── QLoRA r=128 on ALL layers including lm_head
  └── TAPT tail on chunk texts
  └── Gate: maritime perplexity ↓15%, general perplexity ↑<10%

PHASE 2A: SFT Stage 1 — Reasoning First (Think Mode)
  └── Train ONLY on /think examples (diagnostic + calculation, 20% of data)
  └── Purpose: build reasoning scaffold before compressing it
  └── Gate: troubleshooting eval ↑ from post-CPT baseline

PHASE 2B: SFT Stage 2 — Concise Responses (No-Think Mode)
  └── Train on remaining 80% of data (/no_think: factual, regulatory, procedural)
  └── Add ThinkFollow examples (200 multi-turn mode-switch dialogues)
  └── Gate: full eval set improves, INSUFFICIENT_CONTEXT rate ≥60% on traps

PHASE 3: On-Policy Correction Round
  └── Student generates answers → teacher scores and corrects
  └── Corrected pairs → SFT Round 2 (targeted, 1 epoch, low LR)
  └── Student mistakes → ORPO rejected pairs (best possible source)
  └── Gate: error types cluster into identifiable patterns

PHASE 4: ORPO Preference Polish
  └── beta=0.1, 1 epoch, close-but-wrong pairs only
  └── 4 rejection types: regulatory precision, missing safety step, unit error, plausible hallucination
  └── Gate: trap question refusals ≥80%, no factual regression

PHASE 5: GGUF Quantization + Validation
  └── Merge LoRA → fp16 HF format
  └── Convert to Q4_K_M GGUF
  └── Post-quant eval: if regulatory precision drops >3%, use Q5_K_M
  └── Final acceptance test: all 6 categories must hit thresholds

REPEAT entire Phase 1-5 for student-4b after student-1.7b completes
(or run in parallel if VRAM allows)
```

---

## PHASE 0 — Infrastructure Setup and Wave 1 Data Generation

### Task 0.1 — Start the Teacher Server

The teacher model is already downloaded. It must be served via llama.cpp before any generation can begin.

**What to build:** A startup script at `/home/mohanganesh/ship/scripts/start_teacher.sh` that:

1. Starts `llama-server` using the Q4_K_M GGUF shards from the teacher model directory
2. Uses CPU-only inference (no CUDA needed — K80s reserved for student training)
3. Binds to `localhost:8000` with an OpenAI-compatible API endpoint
4. Enables `-fmoe` flag (critical for MoE routing performance — without it, generation quality degrades)
5. Sets `--threads 40` (leave 8 threads for OS and other processes)
6. Sets `--ctx-size 8192` (maritime chunks can be long regulatory text)
7. Sets `--n-predict 300` (hard cap to prevent verbose outputs)

After starting, validate by sending a test prompt to `localhost:8000/v1/chat/completions` with a simple maritime question and confirming the response is grounded, concise, and follows the format.

**Run FOUR teacher server instances for maximum throughput:**
- Instance A: port 8000, CPU cores 0-11, 12 threads each
- Instance B: port 8001, CPU cores 12-23, 12 threads each
- Instance C: port 8002, CPU cores 24-35, 12 threads each
- Instance D: port 8003, CPU cores 36-47, 12 threads each

Four instances at ~9 tok/s each = ~36 tok/s aggregate. At ~350 tokens/sample: ~100,000 samples per day. 600,000 generation calls completes in approximately 6 days continuous.

### Task 0.2 — Wave 1 Generation Script

**What to build:** A generation script at `/home/mohanganesh/ship/scripts/generate_wave1.py`

**Input:** ALL 115,783 chunks from `maritime_pipeline/data/final/chunks.jsonl` — every single one.

**Generation volume (non-negotiable):**
Every chunk is processed with FIVE different question angles. Not one question per chunk. Five. This produces 115,783 × 5 = 578,915 generation calls for Mode A alone. After filtering, expect 300,000–400,000 survivors. Both student models — 1.7B and 4B — benefit from every additional training sample. More data at this quality level makes both models better at answering the questions that keep mariners alive.

Additionally, high-value chunks from the ten life-or-death categories listed below get TWO extra angles beyond the five standard ones, for a total of seven per high-value chunk.

**The five standard question angles (all chunks):**

Angle 1 — Direct knowledge: The single most important factual question a mariner needs answered from this chunk. Phrased exactly as a real mariner asks it in practice, not as a textbook question.

Angle 2 — Exception and condition: When does this NOT apply? What vessel classes, flag states, tonnage thresholds, trading area restrictions, or operational states change the answer? If no exception exists in the chunk, output INSUFFICIENT_CONTEXT for this angle only.

Angle 3 — Consequence and failure: What happens when this is ignored, misunderstood, or done wrong? What is the safety consequence, equipment failure, regulatory penalty, human injury, or vessel casualty? This angle must make the stakes explicit in the answer.

Angle 4 — Procedure and action: What must someone physically DO? Step-by-step. What is the sequence, the checks required, the tools needed, the people who must be present, the documentation required?

Angle 5 — Authority and accountability: How would a Chief Engineer, Master, Port State Control Inspector, Classification Society surveyor, or flag state auditor verify compliance with this? What documentation would they check, what would trigger a deficiency notice, what would cause detention?

**The ten life-or-death categories (get two extra angles beyond the five standard):**

The generation script identifies chunks belonging to these categories by keyword matching and source type. These categories are where wrong answers kill people or cause vessel losses:

T1 — Main engine failure at sea: propulsion loss in confined waters, adverse weather, near collision, emergency steering, anchor timing, distress obligations.

T2 — Fire in machinery spaces: CO2 system activation sequence, boundary cooling, ventilation shutdown, re-entry procedure, firefighter entry without self-contained breathing apparatus is fatal.

T3 — Flooding and progressive stability loss: cross-flooding, free surface effect, damage stability, list correction limits, the exact moment abandon ship becomes the only safe option.

T4 — Collision and grounding: immediate post-collision actions, compartment assessment sequence, Lloyd's Open Form, wreck marking, port authority notification timing.

T5 — Cargo emergencies: bulk cargo liquefaction at sea kills vessels. Container fire, dangerous goods spill, cargo shift and sudden list. These kill crews and vessels.

T6 — Man overboard: full MOB sequence, Williamson turn execution, rescue boat deployment timing, hypothermia management, the legal requirements when a recovered person does not survive.

T7 — Enclosed space entry: the single largest cause of preventable maritime deaths. Every step of the permit-to-work system. Atmosphere testing sequence. The standby person who cannot enter to rescue. The correct rescue procedure. Generates maximum training questions here.

T8 — Port State Control detention: what triggers detention, what constitutes a major non-conformity under ISM Code, MARPOL evidence that leads to prosecution, how to get a vessel released, flag state notification requirements.

T9 — Structural failure at sea: hull cracking in heavy weather, hatch cover failure, fatigue crack progression, class surveyor emergency notification, immediate seamanship response.

T10 — Medical emergency: Ship Captain's Medical Guide procedures, telemedicine consultation protocol, medevac decision criteria, death at sea — the documentation, the legal requirements, the body preservation obligations.

**Generation modes (strictly enforced):**
- 80% of generation calls → `/no_think` system prompt → factual, regulatory, procedural, safety Q/A
- 20% of generation calls → `/think` system prompt → diagnostic and calculation Q/A with reasoning traces
- `diagnostic_multistep` and `calculation` difficulty hint chunks always use `/think` mode
- All other difficulty hints use `/no_think` mode

**System prompt for /no_think generation (exact text):**
```
You are a maritime domain expert. You generate training data for an offline maritime AI assistant.

/no_think

STRICT RULES:
1. Generate exactly ONE question and answer from the provided text chunk.
2. The answer MUST be answerable ONLY from the chunk text. Do not use outside knowledge.
3. If the chunk does not contain sufficient information to answer a meaningful question, output exactly: {"q": null, "a": "INSUFFICIENT_CONTEXT", "type": "insufficient"}
4. WORD LIMITS by type — STRICTLY ENFORCED:
   - factual: 50 words maximum
   - regulatory: 100 words maximum. Must include "shall" or "must" if the chunk states an obligation.
   - safety: 120 words maximum. Must include the safety consequence if relevant.
   - procedural: 200 words maximum. Use numbered steps. Each step maximum 20 words.
   - troubleshooting: 150 words maximum. Structure as: symptom → cause → action.
   - calculation: 100 words maximum. Include formula, values, and units.
5. Output ONLY valid JSON. No preamble, no explanation.
6. Never start your answer with "According to", "Based on", or "The text states".

OUTPUT FORMAT:
{"q": "<question as a mariner would ask it>", "a": "<answer>", "type": "<factual|regulatory|safety|procedural|troubleshooting|calculation>", "chunk_id": "<chunk_id>"}
```

**System prompt for /think generation (exact text):**
```
You are a maritime domain expert. Think carefully before answering.

/think

STRICT RULES:
1. Generate exactly ONE question and answer from the provided text chunk.
2. The answer MUST be answerable ONLY from the chunk text.
3. Show your reasoning in <think>...</think> tags. Maximum 150 words in the thinking section.
4. Final answer maximum 80 words. Structure: symptom/problem → reasoning → conclusion → action.
5. Output ONLY valid JSON.

OUTPUT FORMAT:
{"q": "<diagnostic or calculation question>", "thinking": "<reasoning trace max 150 words>", "a": "<concise answer max 80 words>", "type": "<troubleshooting|calculation>", "chunk_id": "<chunk_id>"}
```

**Output:** appends each generated sample as a JSON line to `maritime_pipeline/data/generation/sft_teacher_wave1.jsonl`

**Resumable:** script tracks which chunk_ids have already been generated (reads existing output file) and skips them. Safe to restart after interruption.

**Round-robin load balancing:** distributes requests across both teacher server instances (port 8000 and 8001) for throughput.

**Immediate validation per sample:** before writing, check:
- Valid JSON format
- Answer word count within 1.5× the word limit
- No forbidden phrases: "as an AI", "I cannot", "language model", "my training data", "I don't have access"
- If any check fails, discard silently (do not write to output file)

**Progress reporting:** every 500 samples, print: samples generated, samples discarded (format failures), INSUFFICIENT_CONTEXT rate, estimated time remaining.

### Task 0.3 — SuperFiltering: IFD-Based Quality Selection

**What to build:** `/home/mohanganesh/ship/scripts/filter_wave1.py`

This runs after `sft_teacher_wave1.jsonl` is complete (or can run incrementally on batches).

**Stage 1 — Hard rejection (cheap, run first):**

Reject any sample where:
- `a` is `INSUFFICIENT_CONTEXT` AND `difficulty_hint` was `factual_simple` or `factual_technical` — the teacher should not be refusing simple factual questions
- Answer word count < 10 words for any type
- Answer word count < 40 words for `procedural` type (procedures need steps)
- Any forbidden phrase in answer
- For `regulatory` type: answer does not contain any of: `shall`, `must`, `require`, `prohibit`, `regulation`, `annex`, `convention`, `chapter`, `article`
- `type` field missing or not in valid set

**Stage 2 — IFD scoring (runs on CPU, uses GPT-2 124M):**

Load GPT-2 from HuggingFace (`gpt2`). For each sample, compute:
- `cond_ppl` = perplexity of the answer conditioned on the question (feed question + answer together, compute loss only on answer tokens)
- `uncond_ppl` = perplexity of the answer alone
- `ifd_score` = `cond_ppl / uncond_ppl`

Keep samples where `0.05 ≤ ifd_score ≤ 0.95`. Samples with IFD > 1.0 indicate misalignment between question and answer. Samples with IFD < 0.05 are trivially easy. Keep a controlled number of low-IFD samples (up to 500) for baseline factual grounding.

**Stage 3 — Diversity selection (embedding-based):**

Load `sentence-transformers/all-MiniLM-L6-v2`. Sort surviving samples by IFD score (highest first within each type category). For each candidate sample, compute embedding of `question + answer`. Add to selected set only if cosine distance to nearest neighbor in selected set exceeds 0.15. This prevents 500 near-identical questions about sulphur emission limits.

**Stage 4 — Type distribution enforcement:**

After IFD + diversity selection, enforce this final distribution via stratified sampling:
- factual (simple + technical combined): 30%
- procedural: 25%
- troubleshooting: 20%
- safety: 12%
- regulatory: 8%
- calculation: 5%

Within the `troubleshooting` category, enforce: 60% `/no_think` simple troubleshooting, 40% `/think` diagnostic traces. Within `calculation`, enforce: 100% `/think` traces with explicit reasoning.

**Target output:** `maritime_pipeline/data/final/sft_curated.jsonl` with at least 300,000 samples across all three modes. If fewer than 200,000 survive Mode A filtering alone, the generation run was cut short and must be extended before proceeding to training. More data is always better — never stop generation early to save time. The models will be better for every additional high-quality sample.

**Filter report:** write `maritime_pipeline/data/final/filter_report_wave1.json` with: input count, hard-rejected count with breakdown by reason, IFD-filtered count, diversity-filtered count, final count by type.

---

## PHASE 1 — CPT: Domain-Adaptive Pretraining

### Why CPT Before SFT

CPT is not instruction tuning. Its purpose is to make the model fluent in maritime domain language — so when SFT later teaches it to answer questions, the model can retrieve facts it actually knows rather than confabulating. A model that has never read MARPOL Annex VI cannot reliably answer questions about it no matter how good the SFT data is.

The research from 2025 confirms: CPT benefits most from breadth and diversity of domain text. SFT benefits from quality and specificity of instruction examples. These are separate passes serving different purposes.

### Task 1.1 — DeepSpeed Configuration for K80

The K80 does not support bf16. All training must use fp16. Create `/home/mohanganesh/ship/configs/ds_config_cpt.json`:

This config must have:
- `fp16.enabled: true` with `initial_scale_power: 16` (conservative start for K80)
- `bf16.enabled: false` (K80 cannot do bf16)
- ZeRO stage 3 with full CPU offload for both optimizer states and parameters
- `overlap_comm: true` to hide communication latency
- `contiguous_gradients: true` for memory efficiency

### Task 1.2 — CPT Training Script (Both Models)

**What to build:** `/home/mohanganesh/ship/training/run_cpt.py`

This script handles both student models using the same logic. The model path is a command-line argument: `--model student-1.7b` or `--model student-4b`.

**Data loading (3-stage curriculum):**

The script reads both `cpt_corpus.jsonl` and `general_replay.jsonl`. It implements a custom data sampler that adjusts the maritime/general mix based on training progress:

- Stage 1: first 10% of total training steps → 50% maritime tokens, 50% general tokens
- Stage 2: steps 10% to 85% → 80% maritime tokens, 20% general tokens
- Stage 3: final 15% of steps → 70% maritime tokens, 30% general tokens

The sampler tracks token count (not step count) to ensure the ratios are token-precise.

**LoRA configuration for CPT:**

- `r = 128` (high rank for knowledge injection — this is the most important CPT hyperparameter)
- `lora_alpha = 128`
- Target modules: ALL linear layers including `lm_head` — the language model head is critical for domain vocabulary injection
- `use_rslora = True` (rank-stabilized LoRA for stable convergence at high rank)
- `use_gradient_checkpointing = "unsloth"` (4× longer context for free)
- `load_in_4bit = True` (QLoRA base)
- `dtype = torch.float16` (K80 constraint)

**Training hyperparameters:**

- `learning_rate = 2e-5` (lower than SFT — CPT changes the model's knowledge base, not just behavior)
- `warmup_ratio = 0.03`
- `weight_decay = 0.01`
- `max_seq_length = 2048` (conservative for K80; the model supports 40k but K80 cannot handle it)
- `per_device_train_batch_size = 1`
- `gradient_accumulation_steps = 16` (effective batch = 16)
- `num_train_epochs = 2` for Stage 1 curriculum, `4` for Stage 2, `1` for Stage 3
- `lr_scheduler_type = "cosine"`

**VRAM estimates:**
- Qwen3-1.7B QLoRA r=128: approximately 4-5 GB VRAM → fits single K80 module (11 GB)
- Qwen3-4B QLoRA r=128: approximately 8-10 GB VRAM → fits single K80 module (11 GB, tight but viable)
- Run each model on 2 K80 modules using DeepSpeed ZeRO-3 for safety margin

**Checkpoint strategy:**
- Save checkpoint every 500 steps
- After every checkpoint, compute perplexity on both `cpt_val_maritime.jsonl` and `cpt_val_general.jsonl`
- Log both values to `training/logs/cpt_perplexity_log.jsonl`
- If general perplexity increases more than 10% from baseline in any checkpoint, increase general replay ratio by 5% for the next stage

**CPT gate (must pass before SFT begins):**

| Metric | Requirement | How to measure |
|---|---|---|
| Maritime held-out perplexity | ≥15% reduction from pre-CPT baseline | Compute on cpt_val_maritime.jsonl |
| General held-out perplexity | Must not increase by >10% from baseline | Compute on cpt_val_general.jsonl |
| Coherence check | Sample 20 completions from model on generic prompts | Manual review: model must produce coherent English |

**Do NOT proceed to SFT until all three CPT gates pass.**

### Task 1.3 — TAPT Tail (Task-Adaptive Pretraining)

After the main CPT run, add a short TAPT pass. This was confirmed by the 2025 domain adaptation research: familiarizing the model with the exact textual style it will encounter during SFT improves recall during inference.

**What this is:** train the post-CPT model for 1 additional epoch on the text content of `chunks.jsonl` only (not the Q/A format — just the raw chunk text). This familiarizes the model with the exact passages the teacher generated questions from.

**Settings:** same LoRA config as CPT, but learning rate reduced to `6e-6` (1/3 of CPT LR). 1 epoch only. No curriculum mixing — 100% chunk text from the chunks that will be used for SFT generation.

---

## PHASE 2 — Two-Stage Curriculum SFT

### Why Two Stages, Not One

The openPangu Embedded research (Sep 2025) confirmed what cognitive science predicts: reasoning skills must be explicitly learned before they can be compressed into implicit fast responses. A model trained on reasoning traces and concise answers simultaneously produces worse results on both modes.

The correct order is: teach the model HOW to reason about maritime problems first (Stage 1), then teach it to produce the answer directly without showing all the reasoning (Stage 2). After Stage 1, the model has internalized the reasoning structure. Stage 2 compresses that structure into fast outputs.

### Task 2.1 — SFT Stage 1: Reasoning First

**What to build:** `/home/mohanganesh/ship/training/run_sft_stage1.py`

**Data:** extract ALL samples from `sft_curated.jsonl` where `type` is `troubleshooting` or `calculation` AND the sample has a `thinking` field (i.e., was generated in `/think` mode). These are the samples with explicit reasoning traces.

Also include 200 hand-crafted ThinkFollow examples. These are multi-turn conversations where the user explicitly switches between `/think` and `/no_think` modes. They teach the model to follow mode instructions across turns. Each ThinkFollow example must cover one of these scenarios:
- Simple factual question (/no_think) followed by complex diagnostic (/think) in the same conversation
- Emergency procedure (/think) followed by simple definition lookup (/no_think)
- Calculation requiring multi-step reasoning (/think) with correct units in final answer

**LoRA configuration for SFT Stage 1:**
- `r = 32` (lower than CPT — SFT trains behavior, not new knowledge)
- `lora_alpha = 32`
- `use_rslora = True`
- Target modules: same as CPT but do NOT include `lm_head` for SFT

**Training hyperparameters:**
- `learning_rate = 2e-4`
- `num_train_epochs = 2`
- `per_device_train_batch_size = 1`
- `gradient_accumulation_steps = 8`
- `neftune_noise_alpha = 5` (embed noise improves instruction following; keep modest to preserve factual precision)

**Chat template:** MUST use Qwen3 chat template with explicit handling of `/think` and `/no_think` tokens. The system prompt for ALL SFT training (stages 1 and 2) is:

```
You are an expert maritime assistant with deep knowledge of vessel operations, safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. Answer questions only from your training knowledge. If a question is outside your knowledge or you cannot answer with confidence, say exactly: "I don't have sufficient information about this specific topic."
/no_think
```

Note: the `/no_think` default in the system prompt is overridden by `/think` in the user message for reasoning-mode samples.

**SFT Stage 1 gate:**

| Metric | Requirement |
|---|---|
| Troubleshooting eval questions | ≥60% correct root cause identification |
| Calculation eval questions | ≥50% numerical accuracy with correct units |
| Thinking trace present | 100% of /think-mode responses must have a `<think>...</think>` block |
| General coherence | Model still produces coherent English on non-maritime prompts |

### Task 2.2 — SFT Stage 2: Concise Responses

**What to build:** `/home/mohanganesh/ship/training/run_sft_stage2.py`

**Data:** ALL remaining samples from `sft_curated.jsonl` (the 80% that are `/no_think` mode: factual, regulatory, procedural, safety types) PLUS the 200 ThinkFollow examples. Do NOT include the Stage 1 reasoning-trace samples again — they have already been learned.

**LoRA configuration:** same as Stage 1 but:
- `learning_rate = 1e-4` (lower than Stage 1 — do not overwrite reasoning priors)
- `num_train_epochs = 2`

**SFT Stage 2 gate (full eval set):**

| Category | Requirement |
|---|---|
| Regulatory questions (100 questions) | ≥70% correct with proper modal verbs (shall/must/should used correctly) |
| Procedural questions (125 questions) | ≥65% procedure completeness (rubric checklist) |
| Troubleshooting questions (100 questions) | ≥65% correct root cause |
| Safety questions (75 questions) | ≥75% step completeness — this is the highest bar |
| Calculation questions (50 questions) | ≥55% correct answer with correct units |
| Trap questions — INSUFFICIENT_CONTEXT | ≥60% correct refusals |

If safety completeness falls below 75%, do NOT proceed to Phase 3. Re-examine the safety training data and regenerate additional safety examples targeting the specific gap.

---

## PHASE 3 — On-Policy Correction Round

### Why This Phase Exists

Off-policy training (where the teacher generates everything) cannot teach the student to recover from its own compounding errors. A model trained purely on teacher outputs learns what the correct answer looks like but not what to do when it starts going wrong. The on-policy round exposes the student's real failure modes and corrects them.

This phase also produces the ORPO rejected pairs automatically. The student's actual mistakes are the best possible source of close-but-wrong rejected answers — infinitely better than asking the teacher to simulate mistakes it would never naturally make.

### Task 3.1 — On-Policy Generation

**What to build:** `/home/mohanganesh/ship/scripts/generate_onpolicy.py`

**Process:**

1. Load the post-SFT-Stage-2 student model checkpoint
2. For each chunk in a 3,000-chunk sample from `chunks.jsonl` (prioritize regulatory_exception and diagnostic_multistep types):
   a. Generate a question using the teacher (as in Wave 1 generation)
   b. Have the student generate an answer to that question
   c. Have the teacher score the student's answer on a 1-5 scale:
      - Factual accuracy (is the answer correct based on the chunk?)
      - Procedural completeness (for procedural type: are all steps present?)
      - Modal precision (for regulatory type: correct use of shall/must/should?)
   d. Teacher outputs score + corrected answer if score < 4

3. Classification of results:
   - Score ≥ 4: student was correct → add (question, student_answer) to `sft_wave1b.jsonl`
   - Score < 4: student was wrong → add (question, teacher_correction) to `sft_wave1b.jsonl` AND add (question, teacher_correction, student_answer) to `orpo_pairs_onpolicy.jsonl`

**Teacher scoring system prompt:**
```
/no_think
You are evaluating an answer to a maritime question. Rate the answer 1-5 on each dimension and provide a corrected answer if the score is below 4.

Dimension 1 — Factual accuracy (1=wrong, 5=completely correct)
Dimension 2 — Completeness (1=major omissions, 5=complete)
Dimension 3 — Modal precision for regulatory answers (1=shall/should/must confused, 5=correct)

SOURCE CHUNK: {chunk_text}
QUESTION: {question}
STUDENT ANSWER: {student_answer}

Output JSON only:
{"factual": <1-5>, "completeness": <1-5>, "modal": <1-5>, "overall": <1-5>, "corrected_answer": "<only if overall < 4, else null>", "error_type": "<factual_error|missing_step|modal_error|hallucination|null>"}
```

### Task 3.2 — SFT Correction Pass

**What to build:** uses the same SFT training script but with `sft_wave1b.jsonl` as the data source.

This is a very short, targeted pass:
- `learning_rate = 5e-5` (very conservative — do not undo Stage 2 training)
- `num_train_epochs = 1` (one pass through the correction data only)
- `gradient_accumulation_steps = 8`
- Same LoRA config as SFT Stage 2

**After this pass, re-run the full eval set.** It should improve on the categories where the on-policy round found errors without regressing on categories where the student was already performing well.

---

## PHASE 4 — ORPO Preference Optimization

### What ORPO Does and Does Not Do

ORPO is a polish layer. It teaches the model the difference between good answers and subtly bad answers. It does NOT inject new knowledge — by this point the model must already know the facts. ORPO's value is in pushing the model to choose the better formulation when it already knows both.

For maritime safety, the four most important rejection types in priority order are:

**R1 — Regulatory precision:** "MARPOL Annex I **should** be applied" vs the correct "MARPOL Annex I **shall** be applied." This is legally catastrophic. A ship operating under "should" guidance instead of "shall" guidance may fail port state control and more importantly may fail to take mandatory safety actions.

**R2 — Missing critical safety step:** Answer is otherwise correct but omits one step that prevents injury or equipment damage. Example: "Open the crankcase inspection door" vs correct "Stop engine, wait 10 minutes for oil mist to clear, then open crankcase inspection door." The omitted wait prevents a crankcase explosion.

**R3 — Unit error:** Answer uses wrong unit. "Maximum SOx limit in ECA is 0.10 **percent**" vs correct "0.10 **percent by mass (m/m)**." Or giving a pressure in kPa when the manual uses bar. Mariners make decisions based on the units.

**R4 — Plausible hallucination:** Cites a regulation that doesn't apply to the vessel class in question. Sounds completely authoritative. Most dangerous because it's hardest to detect.

### Task 4.1 — Build ORPO Pairs

**What to build:** `/home/mohanganesh/ship/scripts/build_orpo_pairs.py`

**Source 1 — On-policy pairs (primary, ~2,000+ pairs):**
Already collected in `orpo_pairs_onpolicy.jsonl` from Phase 3. These are the highest-quality pairs because the rejected answers are real student mistakes.

**Source 2 — Teacher-generated R1 pairs (regulatory precision, ~500 pairs):**
For each sample in `sft_curated.jsonl` where `type == "regulatory"`, ask the teacher to generate a rejected version with a subtle modal error. Use this teacher prompt:

```
/no_think
You are generating training data. Given a correct maritime regulatory answer, produce a subtly wrong version.
QUESTION: {question}
CORRECT_ANSWER: {chosen_answer}
REJECTION_TYPE: R1_regulatory_precision (change "shall" to "should" OR cite a wrong regulation number OR omit a required exception clause)

The rejected answer must be plausible enough that a distracted mariner might act on it. Do NOT make it obviously wrong.
Output JSON only: {"rejected": "...", "error_introduced": "..."}
```

**Source 3 — Teacher-generated R2 pairs (missing safety step, ~300 pairs):**
For each sample where `type == "safety"` or the answer contains emergency procedure content, ask the teacher to produce a version with one critical safety step removed. Use same prompt structure as Source 2 but with REJECTION_TYPE: R2_missing_critical_safety_step.

**Final ORPO dataset assembly:**
- Combine all three sources
- Filter: keep only pairs where chosen and rejected are clearly different in quality but the rejected is not obviously garbage
- Target: 3,000 to 5,000 total pairs
- Write to `maritime_pipeline/data/final/orpo_curated.jsonl`

Schema per line:
```json
{"prompt": "...", "chosen": "...", "rejected": "...", "rejection_type": "R1|R2|R3|R4|on_policy", "risk_tag": "safety_critical|regulatory|maintenance|general"}
```

### Task 4.2 — ORPO Training

**What to build:** `/home/mohanganesh/ship/training/run_orpo.py`

**ORPO configuration:**
- `learning_rate = 8e-6`
- `beta = 0.1` (the lambda parameter from ORPO paper — do NOT exceed 0.2 for domain SFT)
- `lr_scheduler_type = "cosine"`
- `num_train_epochs = 1` (ORPO is a polish layer — 1 epoch is correct and sufficient)
- `per_device_train_batch_size = 1`
- `gradient_accumulation_steps = 16` (effective batch = 16)
- `disable_dropout = True` (always required for ORPO)
- `warmup_steps = 50`
- `fp16 = True`, `bf16 = False` (K80 constraint)
- `optim = "adamw_8bit"` (saves ~2 GB VRAM)

**Critical monitoring during ORPO:**
- Watch the training log for `rewards/chosen` and `rewards/rejected`
- `rewards/chosen` should be positive and slowly increasing
- `rewards/rejected` should be negative
- If `rewards/rejected` goes sharply negative within the first 100 steps, STOP and reduce beta to 0.05 — this indicates over-aggressive preference optimization that will damage factual recall

**ORPO gate:**

| Metric | Requirement |
|---|---|
| Trap question refusals | ≥80% correct refusals (up from ≥60% after SFT) |
| Safety step completeness | ≤5% regression from post-SFT-Stage2 |
| Factual recall | ≤3% regression from post-SFT-Stage2 |
| Regulatory modal precision | Improvement on regulatory eval slice |

If factual recall regresses by more than 3%, the ORPO run has overfit. Revert to pre-ORPO checkpoint and re-run with beta=0.05.

---

## PHASE 5 — Quantization and Deployment

### Task 5.1 — Merge and Convert

**Sequence:**

1. Load the post-ORPO model checkpoint using Unsloth
2. Merge LoRA adapters into base weights using `save_pretrained_merged` with `save_method="merged_16bit"`
3. Convert merged model to GGUF Q4_K_M using llama.cpp's `convert_hf_to_gguf.py`
4. Save to `/home/mohanganesh/ship/deploy/maritime-1.7b-q4km.gguf` (or maritime-4b-q4km.gguf)

**File size expectations:**
- Qwen3-1.7B Q4_K_M: approximately 1.1 GB → runs on 3 GB RAM mobile device
- Qwen3-4B Q4_K_M: approximately 2.5 GB → runs on 5 GB RAM tablet

### Task 5.2 — Post-Quantization Validation (Critical — Do Not Skip)

**After quantization, re-run the full eval set against the GGUF model via llama-server.**

Q4_K_M typically produces less than 1% quality drop on factual tasks. However, regulatory precision tasks — where the exact modal verb matters — can drop 2–3%. This is not acceptable for a life-safety system.

**Decision rule:**
- If regulatory precision drops ≤3% from the fp16 model: ship Q4_K_M
- If regulatory precision drops >3%: rebuild with Q5_K_M (~1.35 GB for 1.7B, ~3.1 GB for 4B) — the size increase is marginal and the precision preservation justifies it

### Task 5.3 — TTC Routing Policy

**What to build:** `/home/mohanganesh/ship/deploy/routing_policy.py`

A deterministic classifier that decides whether to send `/think` or `/no_think` to the model at inference time. No ML overhead — purely rule-based for predictability on edge hardware.

**Think triggers (always route to /think mode):**
- Keywords: `diagnose`, `troubleshoot`, `why`, `calculate`, `stability`, `what would happen`, `sequence of`, `won't start`, `doesn't start`, `failure mode`, `root cause`, `step by step`, `procedure for emergency`, `exception to`, `notwithstanding`
- Regex patterns: any number followed by a unit (`\b\d+\s*(bar|kPa|rpm|kW|hp|nm|knots|GRT|DWT)\b`), specific regulation references (`regulation\s+\d+`), MARPOL annex references (`annex\s+(i|ii|iii|iv|v|vi)\b`)
- Question structure: questions with more than 3 clauses joined by "and/but/however/if"

**No-think (default for everything else):** simple definitions, single-fact lookups, yes/no compliance questions with clear answers

**Calibration target:** the router should trigger `/think` on approximately 20% of typical maritime queries. Run the router against the eval set questions and confirm the trigger rate is between 15% and 25%.

### Task 5.4 — Final Acceptance Test

Run the complete eval set against the final GGUF model. The system is NOT deployment-ready until all thresholds are met:

| Category | Questions | Acceptance threshold |
|---|---|---|
| Regulatory compliance | 100 | ≥85% correct with proper modal verbs |
| Procedural step completeness | 125 | ≥80% rubric checklist completion |
| Troubleshooting root cause | 100 | ≥75% correct fault identification |
| Safety step completeness | 75 | ≥90% — highest bar, life-safety |
| Calculation accuracy | 50 | ≥80% correct with correct units |
| Trap question refusals | 25 | ≥80% explicit uncertainty acknowledgment |

If any category fails, the failure category identifies the stage to revisit:
- Regulatory failures → CPT or SFT Stage 2 data quality
- Procedural failures → Tier 1 book extraction quality or SFT data completeness
- Troubleshooting failures → NTSB/BSU chunk quality or SFT Stage 1 (reasoning)
- Safety failures → ORPO pair quality (R2 pairs)
- Trap failures → ORPO training or confidence calibration needed

---

## Running Both Models: Parallelism Strategy

You have 4 K80 modules (each ~11 GB). The training fits as follows:

**During CPT:**
- Run student-1.7b on modules 0 and 1 (ZeRO-3 across 2 modules)
- Run student-4b on modules 2 and 3 (ZeRO-3 across 2 modules)
- Teacher server runs entirely on CPU (no GPU needed for inference)
- Both CPT runs proceed in parallel

**During SFT and ORPO:**
- Each student fits on a single K80 module with QLoRA
- Run sequentially rather than in parallel to avoid memory pressure
- Complete the full pipeline for student-1.7b first (faster), then student-4b

**K80 CUDA environment:**
- Driver 470.256.02 ✅ already installed
- CUDA 11.4 ✅ already working (confirmed by your PyTorch 2.7.1+cu118)
- No bf16 → use fp16 everywhere
- Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128` to reduce fragmentation

---

## Wave 2 and Wave 3 (After Wave 1 Pipeline Validates)

Wave 2 and Wave 3 only begin after Wave 1 has completed the full pipeline (CPT → SFT → ORPO) and passed the final acceptance test.

**Wave 2 (50,000–100,000 samples):**
- Uses same generation and filtering pipeline as Wave 1
- Adds multi-angle variants: same fact asked from perspective of deck officer, chief engineer, and port state control inspector
- Incorporates Tier 2 book content (extract during Wave 1 training)
- On-policy correction round becomes the dominant data source (student is better by now)

**Wave 3 (2,000–10,000 reasoning traces only):**
- Only if troubleshooting or calculation categories scored below threshold in Wave 1 acceptance test
- Uses `/think` teacher mode exclusively
- Targets specifically the failure categories identified in Wave 1 acceptance test
- Used for SFT Stage 1 retraining only (not full pipeline rerun)

---

## Research Citations for Every Major Decision

| Decision | Source | Finding |
|---|---|---|
| Two-stage curriculum SFT (reasoning first, concise second) | openPangu Embedded (Sep 2025, arXiv:2509.26497) | State-of-the-art for 1B SLM; reasoning-first then fast-response consistently outperforms flat mixed SFT |
| Model-aware data complexity matching | Pangu Embedded 7B (May 2025, arXiv:2505.22375) | Training data that is too easy or too hard both produce suboptimal results; balanced difficulty matched to current student capacity achieves best performance |
| Off-policy + on-policy distillation two-phase | Qwen3 Technical Report (arXiv:2505.09388) | This is the exact recipe used to train Qwen3-4B from Qwen3-235B; on-policy round teaches recovery from student's own mistakes |
| SuperFiltering IFD via GPT-2 | SuperFiltering (ACL 2024, arXiv:2402.00530) | GPT-2 IFD ordering is consistent with 13B model orderings; enables efficient filtering without expensive scorer |
| ORPO over DPO for domain SFT | Post-training in 2026 (llm-stats.com, Mar 2026) | ORPO eliminates distribution shift between SFT and preference stages; reference-model-free; fewer FLOPs |
| beta=0.1 for ORPO | ORPO paper (arXiv:2403.07691) | Lambda=0.1 is the recommended default; higher values accelerate preference learning but damage domain knowledge retention |
| 1 epoch for ORPO | ORPO practitioner guides 2025 | Beyond 1 epoch, ORPO exhibits diminishing returns and increasing forgetting risk; polish, not main training |
| TAPT tail after CPT | Domain adaptation survey (Nature Computational Materials, 2025) | DAPT+TAPT consistently outperforms DAPT alone; familiarizing model with task-specific text improves downstream recall |
| QLoRA r=128 for CPT | Knowledge injection limits study (Nature, 2025) | Higher LoRA rank compensates for LoRA's structural limitation on new knowledge injection; r=128 provides ~100M trainable params on 4B |
| 3-stage curriculum CPT mix | Poro-2 CPT playbook (AMD ROCm, Jun 2025) | Fixed ratios produce suboptimal outcomes; warmup and anneal phases mitigate catastrophic forgetting |
| fp16 for K80 (no bf16) | K80 hardware specification (SM_37, Kepler architecture) | K80 Kepler architecture has no bf16 support; fp16 is the maximum reduced precision available |
| Q4_K_M deploy, Q5_K_M fallback | Quantization analysis studies 2025 | Q4_K_M: <1% quality drop on factual tasks; regulatory precision tasks can drop 2-3% and require Q5_K_M |
| neftune_noise_alpha=5 | NEFTune paper (arXiv:2310.05914); domain FT studies 2025 | Alpha=5 is conservative; higher values help general IF but hurt factual precision; wrong tradeoff for domain SFT |