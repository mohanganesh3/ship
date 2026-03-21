# 🚢 Next Steps Action Plan (No‑RAG, Local Teacher, Qwen3‑1.7B)

> **Winner (student / edge model): Qwen3‑1.7B.** Everything in this plan optimizes for baking maritime knowledge into this model’s weights and deploying it offline.

> **Goal:** ship an *offline*, *no‑RAG* maritime assistant where **all domain knowledge is baked into the weights** of **Qwen3‑1.7B**, trained via **CPT → synthetic SFT/distillation (DEITA‑filtered) → ORPO**, then deployed as **GGUF Q4_K_M** with **dynamic test‑time compute (TTC) routing**.
>
> **Key constraint update:** **No paid teacher APIs.** All synthetic generation is produced on the available **4‑GPU machine** (multi‑day runs are acceptable).

---

## 0) Ground truth: what the key papers actually claim (quick reference)

These are the papers we rely on for the recipe (all arXiv abs pages were fetched in this session):

- **ORPO** — *ORPO: Monolithic Preference Optimization without Reference Model* (arXiv:2403.07691)
  - Core takeaway: you can fold preference optimization into the SFT objective (no reference model) while still benefiting from SFT-style convergence.
- **DEITA** — *What Makes Good Data for Alignment?* (arXiv:2312.15685)
  - Core takeaway: measure/choose data along **complexity, quality, diversity**; their DEITA-selected sets show strong results with far fewer examples.
- **NEFTune** — *NEFTune: Noisy Embeddings Improve Instruction Finetuning* (arXiv:2310.05914)
  - Core takeaway: injecting noise into embeddings during finetuning can significantly improve instruction tuning quality.
- **Qwen3 Technical Report** (arXiv:2505.09388)
  - Core takeaway: unified **thinking vs non-thinking** modes + a **thinking budget** mechanism that supports dynamic routing.
- **s1** — *Simple test-time scaling* (arXiv:2501.19393)
  - Core takeaway: “budget forcing” / controlling thinking length can improve reasoning, but **their base is 32B** (not 1B).
- **Test-time compute scaling** — *Scaling LLM Test-Time Compute Optimally…* (arXiv:2408.03314)
  - Core takeaway: TTC helps most when the base model already has **non-trivial success** on the task; TTC cannot conjure missing domain facts.

---

## 1) Decide the concrete teacher stack (local, 4 GPUs)

We need **two teacher roles**:

1. **Knowledge teacher** (fast, high factual formatting quality): generates grounded Q/A pairs.
2. **Reasoning teacher** (optional, slower): generates diagnostic / calculation traces for the ~20% “hard reasoning” slice.

### Recommended local teacher candidates (pick 1–2)

- **Knowledge teacher (recommended first):** a strong instruction model in the **20–40B** class that fits tensor-parallel across 4 GPUs with quantization.
  - Examples (choose based on what your GPUs can handle): Qwen2.5‑32B‑Instruct / Qwen3‑32B‑Instruct (if available) or similar.
- **Reasoning teacher (optional):** a reasoning‑capable model (often slower) for troubleshooting traces.
  - Keep this dataset small at first (e.g., 2k–10k traces) to avoid “everything becomes long CoT” regression.

### Non‑negotiable constraint for teachers

- Teachers must be prompted to be **source‑grounded**: answers must be derivable from the provided chunk; otherwise output `INSUFFICIENT_CONTEXT`.

Deliverable: a short markdown note documenting:
- teacher model(s) chosen
- quantization format used (e.g., 4‑bit) and inference engine (vLLM / llama.cpp)
- expected context window

---

## 2) Build the “training corpus contract” (files + schemas)

This is what makes the pipeline reproducible.

### 2.1 Raw text (for CPT)

- **Input:** cleaned maritime text (Docling/Marker outputs), de-duplicated.
- **Output:** `cpt_corpus.jsonl` with fields:
  - `text`
  - `source_id` (file + page/chapter)
  - `domain_tag` (e.g., `MARPOL`, `SOLAS`, `ENGINES`, `NAV`)

### 2.2 Teacher prompts (for SFT + preference)

- **Chunk file:** `chunks.jsonl` with:
  - `chunk_id`, `text`, `metadata` (book, chapter, section)
- **Teacher output file (Q/A):** `sft_teacher.jsonl` with:
  - `chunk_id`
  - `question`
  - `answer`
  - `answer_type` (factual/procedural/safety/regulatory/troubleshooting)
  - `grounding` (short quote or bullet mapping to chunk; may be empty if teacher refuses)
  - `flags` (e.g., `INSUFFICIENT_CONTEXT`, `AMBIGUOUS`)

### 2.3 Preference pairs (for ORPO)

- **Preference output file:** `orpo_pairs.jsonl` with:
  - `prompt`
  - `chosen`
  - `rejected`
  - `reason` (why chosen is better)
  - `risk_tag` (safety-critical / maintenance / regulation / general)

---

## 2.4 How we use *all* datasets (end-to-end map)

When you hear “use all the dataset”, it’s important to realize we **don’t feed every file into one single finetune**.

We transform the data into **three different training signals**, and each signal is used at a different stage:

1. **Raw text** → teaches *knowledge + language patterns* (CPT)
2. **Instruction examples (Q/A)** → teaches *how to answer in our desired format* (SFT)
3. **Preference pairs** → teaches *what’s better/safer/more grounded* (ORPO)

### Dataset flow (what becomes what)

| Source data you have | What we convert it into | Used in which step | What it teaches | Notes / pitfalls |
|---|---|---|---|---|
| Maritime PDFs/books/manuals scraped + converted text | `cpt_corpus.jsonl` (raw text lines/paragraphs) | **CPT** | Domain vocabulary + factual associations | Must dedupe; keep metadata for audits; keep a held-out maritime validation slice |
| A *small* general English corpus (open, permissive) | `general_replay.jsonl` (raw text) | **CPT** (as replay mix) | Prevent catastrophic forgetting (basic English + common sense) | This is the “20% replay” in the 80/20 mix; keep it clean and non-domain |
| The same maritime corpus, but **chunked** (groundable excerpts) | `chunks.jsonl` | **Teacher generation input** | Enables grounded synthetic Q/A | Chunking is for generation; it’s not RAG at inference |
| Teacher outputs (grounded) | `sft_teacher.jsonl` → `sft_curated.jsonl` | **SFT** | Answer style + recall patterns + procedural formatting | Apply DEITA-style filtering; enforce concision for simple Qs |
| Teacher + student (or degraded answer) pairs | `orpo_pairs.jsonl` → `orpo_curated.jsonl` | **ORPO** | Safer behavior + uncertainty + fewer hallucinations | Rejected answers must be *plausible* but worse (ungrounded, unsafe, incomplete, wrong units) |
| Hand-written eval questions | `eval_set.jsonl` | **Evaluation only** | Measures progress | Never train on eval; version it; add “trap/unknown” tests |

### The 80/20 mix (what it means in practice)

- During **CPT**, batches are sampled so that about **80% tokens** come from `cpt_corpus.jsonl` (maritime) and **20% tokens** come from `general_replay.jsonl`.
- This is *not* about fairness; it’s a stability trick: the 20% keeps the model from “forgetting how to speak”.

### “Do we really need the general replay dataset?”

If you do 100% maritime CPT, you often get:

- degraded writing quality outside the domain
- worse instruction-following
- weird repetitiveness (model overfits narrow style)

So yes: even a small, clean general set helps.

### How ORPO pairs are produced (simple, local, reliable)

For each prompt, we need a **chosen** and a **rejected** answer.

Recommended generation pattern (all local):

1. **Prompt**: question + optionally the chunk reference *only during data creation*.
2. **Chosen**: generated by the knowledge teacher with strict grounding rules.
3. **Rejected**: generated by one of:
   - an **early student checkpoint** (realistic mistakes)
   - the teacher instructed to produce a *common failure mode* (missing a step, wrong unit, overconfident answer without grounding)
4. Optional: teacher (or a separate judge model) writes the `reason` field.

Key rule: ORPO works best when **rejected answers are close-but-wrong**, not obviously garbage.

---

## 3) Synthetic generation plan (local teacher) — do it in waves

Avoid “big bang generation”. Generate → filter → train → evaluate → iterate.

### Wave 1 (baseline)

- **Target:** 10k–20k Q/A pairs (no reasoning traces)
- **Purpose:** validate grounding, formatting, and student training loop end-to-end.

### Wave 2 (scale)

- **Target:** 50k–100k Q/A pairs
- Add **multi-angle variants** per key fact (DEITA suggests quality > quantity; multi-angle helps memorization).

### Wave 3 (reasoning slice)

- **Target:** 2k–10k reasoning traces
- Only for:
  - diagnostic trees
  - stability/voyage calculations
  - multi-step maintenance procedures

Deliverable: per-wave generation runbook (exact prompt templates + output validation rules).

---

## 4) DEITA-style filtering (the part that actually makes “days of generation” worth it)

DEITA’s framing is: measure each example along **complexity**, **quality**, **diversity**, then keep a high-value subset.

Practical plan:

1. **Hard filters (cheap):**
   - reject if `INSUFFICIENT_CONTEXT`
   - reject if answer too short for procedural questions
   - reject if forbidden phrases (“as an AI language model…”, generic boilerplate)
   - language detection: keep English (or explicitly allow multilingual later)

2. **Complexity score:**
   - heuristics: number of steps, presence of constraints, numeric reasoning, cross references inside chunk

3. **Quality score:**
   - format correctness
   - grounding evidence present
   - low hallucination risk markers (admits uncertainty when chunk lacks detail)

4. **Diversity selection:**
   - avoid duplicates / paraphrase spam
   - keep a balanced distribution across `answer_type` and `domain_tag`

Deliverable: a single `filter_report.jsonl` + final curated datasets:
- `sft_curated.jsonl`
- `orpo_curated.jsonl`

---

## 5) Training plan (Qwen3‑1.7B)

## 5.0 Final “winners” (what we actually do, based on all research)

From the repo’s rankings and the primary-paper grounding, the winning stack for **no‑RAG / knowledge‑in‑weights** is:

- **Base (edge):** **Qwen3‑1.7B** → quantize to **GGUF Q4_K_M**
- **Knowledge injection:** **CPT** on raw maritime text **with replay** (80/20 domain/general)
- **Usability + recall:** **Synthetic SFT / distillation** generated by a **local teacher**, then **DEITA‑style filtering**
- **Alignment polish:** **ORPO** (preference optimization without a reference model)
- **Latency control:** **Dynamic TTC routing** (thinking ON only when needed; target ~20% of turns)

What we *do not* rely on:

- **RAG at inference** (explicitly forbidden)
- **Paid teacher APIs** (explicitly forbidden)
- **Direct RL on the 1–3B student** for “reasoning” (research strongly suggests distillation is the practical path at this scale)

### Step A — CPT (80/20 domain/general)

- **Objective:** bake vocabulary + relationships into weights.
- **Data:** 80% maritime + 20% general replay (to reduce catastrophic forgetting).
- **Stop condition:** perplexity improves on a held-out maritime validation set *without* large regression on a small general English set.

### Step B — Synthetic SFT / distillation

- **Objective:** teach answer formats and “retrieval-like recall patterns” via multi-angle Q/A.
- **Data:** `sft_curated.jsonl`
- **Key risk:** overfitting to teacher verbosity → mitigate by enforcing concise answers on simple questions.

### Step C — ORPO

- **Objective:** safer behavior, better uncertainty, fewer confident hallucinations.
- **Data:** `orpo_curated.jsonl`

Deliverable: checkpoints and a short evaluation summary after each step.

---

## 5.4 Concrete training recipe (starter settings + gates)

This is the technically actionable version of the pipeline. Values are **starting points**; we tune after Wave 1.

### Stage A: CPT (domain adaptive pretraining)

**Data used:**

- 80% tokens from `cpt_corpus.jsonl` (maritime)
- 20% tokens from `general_replay.jsonl` (clean general text)

**Recommended settings (start):**

- sequence length: 2048 (raise later if stable)
- epochs: 2–5 (stop via validation, not by ego)
- LR: $1\times10^{-5}$ to $3\times10^{-5}$ (cosine decay; warmup 1–3%)
- weight decay: small (or default)

**Adapter vs full fine-tune guidance:**

- If you can afford it, prefer **full fine-tuning for CPT** (best for injecting *new knowledge*).
- If you must use adapters, use **high-rank QLoRA** for CPT (knowledge injection is the hardest part).

**Gate to proceed to SFT:**

- maritime validation perplexity improves materially
- general validation perplexity does **not** spike (we’re avoiding catastrophic forgetting)

### Stage B: SFT (synthetic instruction tuning)

**Data used:** `sft_curated.jsonl` (DEITA-filtered)

**Target composition (recommended starting distribution):**

- 40% factual
- 25% procedural
- 15% troubleshooting
- 10% safety
- 5% regulatory
- 5% out-of-domain refusals / “insufficient context”

**Recommended settings (start):**

- adapters are OK here (SFT is mostly format + crystallization)
- 1–3 epochs (watch overfitting: verbose / copyy teacher style)
- add **NEFTune-style embedding noise** during SFT (tune intensity; keep it modest)

**Gate to proceed to ORPO:**

- eval set: higher answer correctness + better formatting
- refusal behavior improves on “unknown” tests without over-refusing on known ones

### Stage C: ORPO (preference optimization)

**Data used:** `orpo_curated.jsonl`

**How we build preference pairs (local + realistic):**

- chosen: grounded teacher answer
- rejected: early-student answer *or* teacher-instructed failure mode (wrong units / missing step / ungrounded confident claim)

**Recommended settings (start):**

- keep pair count modest at first (quality > quantity)
- do short runs; ORPO is a *polish* layer, not a knowledge injector

**Gate to quantize/deploy:**

- hallucination rate on trap/unknown questions goes down
- safety/procedure questions become more structured (checklists, warnings)
- does not regress on basic factual recall compared to post-SFT

---

## 6) Evaluation harness (must exist before we scale generation)

Create an **offline eval set** (200–500 questions) with categories:

- regulatory basics (SOLAS/MARPOL)
- maintenance procedures
- troubleshooting
- safety
- numerical/units
- “unknown/insufficient info” tests

Metrics:
- exact-match / rubric scoring (for structured questions)
- refusal correctness (when chunk/knowledge should be absent)
- hallucination rate on “trap” questions

Deliverable: `eval_set.jsonl` + a scriptable scoring rubric document.

---

## 7) Deployment packaging (GGUF + dynamic TTC routing)

### GGUF quantization

- Quantize student to **GGUF Q4_K_M**.
- Validate:
  - RAM usage
  - tokens/sec
  - regression on eval set

### Dynamic TTC routing (runtime policy)

Use Qwen3’s thinking/non-thinking modes as an **adaptive budget**:

- Turn thinking **ON** for: calculations, diagnostics, ambiguous multi-step questions.
- Turn thinking **OFF** for: straightforward definitions, basic facts, short regulatory checks.

Deliverable:
- a routing policy doc (`routing_policy.md`)
- a set of test prompts verifying the router triggers ~20% of the time on your eval distribution.

---

## 8) “What to do next” — concrete 10-step sequence

1. Freeze the **teacher model choice** + inference engine on the 4‑GPU machine.
2. Produce `chunks.jsonl` (grounded excerpts) from the cleaned corpus.
3. Run **Wave 1** generation (10k–20k) + hard filters.
4. Implement DEITA-style scoring + select top set.
5. Train **CPT** (short run) → evaluate.
6. Train **SFT** on curated Wave 1 → evaluate.
7. Create ORPO preference pairs for the same domains → run **ORPO** → evaluate.
8. Only then scale to **Wave 2** (50k–100k).
9. Add **Wave 3** reasoning traces (2k–10k) if TTC questions underperform.
10. Quantize to GGUF Q4_K_M → package and test on target edge hardware.

---

## Notes (important realities)

- **No-RAG means no hot-swapping knowledge.** Any regulation update implies some retraining + re-quantization.
- TTC helps when the model already has the facts; it does not replace CPT/SFT.
- Keep reasoning traces limited: too many long traces can increase latency and make the assistant verbose.
