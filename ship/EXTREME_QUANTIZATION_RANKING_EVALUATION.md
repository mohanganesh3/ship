# RANKING EVALUATION: Extreme Quantization (BitNet 1.58-bit / 2-bit / Ultra-Low Bit Models)

**Approach Under Evaluation:** Instead of using a 1.7B model at Q4 quantization (~1.2GB), use a LARGER model (3-7B) with extreme quantization (1-2 bit) to fit on mobile, getting more knowledge capacity at the same memory footprint. Alternatively, use BitNet b1.58 architecture models that are NATIVELY ternary-weight {-1, 0, 1} and run with integer-only arithmetic via bitnet.cpp. The hypothesis: more parameters at lower precision > fewer parameters at higher precision for knowledge-intensive applications.

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** Must fit in 1-2 GB of RAM on mobile  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH SOURCES ANALYZED

| Paper / Resource | Key Finding for This Evaluation |
|---|---|
| **BitNet — "Scaling 1-bit Transformers for Large Language Models"** (Wang et al., 2023; arXiv:2310.11453) | Original 1-bit transformer architecture. Replaces Linear layers with BitLinear layers using binary {-1, 1} weights. Demonstrated that 1-bit transformers can scale following similar laws to full-precision. **Critical limitation: the original BitNet used binary weights and required training from scratch. Quality was notably below FP16 at the same model size, making it impractical for knowledge-intensive applications.** |
| **BitNet b1.58 — "The Era of 1-bit LLMs: All Large Language Models are in 1.58 Bits"** (Ma, Wang et al., 2024; arXiv:2402.17764) | Upgraded to ternary weights {-1, 0, 1} = 1.58 bits per weight ($\log_2(3)$). Claims to MATCH full-precision (FP16/BF16) Transformer LLMs at the same model size and training tokens for both perplexity and end-task performance. Uses INT8 additions for matrix multiply instead of FP16 multiply-add — 71.4x energy savings for matrix multiplication. **THE foundational claim: ternary weights lose no quality if trained natively. But the key caveat: "requires training from scratch" — you cannot post-training quantize an existing model to 1.58-bit without massive quality loss.** |
| **bitnet.cpp — Microsoft's Official Inference Framework** (GitHub: microsoft/BitNet) | Official inference runtime for 1-bit LLMs. On ARM CPUs: 1.37-5.07x speedup, 55.4-70.0% energy reduction. On x86 CPUs: 2.37-6.17x speedup, 71.9-82.2% energy reduction. Can run a 100B BitNet model on a single CPU at 5-7 tokens/sec (human reading speed). Official model: BitNet-b1.58-2B-4T (2.4B parameters). Demo shows 3B model running on Apple M2. **Directly validates mobile deployment. The 2B-4T model at ~0.4 GB is extraordinary for mobile. ARM kernel optimization (TL1 kernel) specifically enables phone deployment. Latest update (Jan 2026) adds further CPU optimization with 1.15-2.1x additional speedup.** |
| **HuggingFace 1.58-bit Fine-tuning Blog** (Sep 2024; huggingface.co/blog/1_58_llm_extreme_quantization) | Attempted to fine-tune a Llama3 8B model to 1.58-bit. **CRITICAL FINDINGS FOR OUR USE CASE:** (1) Converting pretrained weights to ternary immediately causes loss to spike to ~13 (from 1.45 unquantized) — the model "loses all of its prior information." (2) Even group_size=2 quantization causes catastrophic information loss. (3) Required "warmup quantization" — gradually increasing a lambda from 0 to 1 over training. (4) After 10B tokens of fine-tuning: outperforms BitNet 7B trained on 100B tokens from scratch. (5) After 100B tokens: still lags behind original Llama3 8B. (6) **"Fine-tuning the model in low-bit mode on a specific dataset causes it to lose much of its general knowledge."** This single finding is DEVASTATING for our maritime use case — if we fine-tune a BitNet model on maritime data, it forgets everything else. |
| **BiLLM — "Pushing the Limit of Post-Training Quantization for LLMs"** (Huang et al., 2024; arXiv:2402.04291) | Post-training quantization to 1.08-bit weights. Achieves 8.41 perplexity on LLaMA2-70B. Uses structured salient weight selection + binary residual approximation. Binarization of 7B model in 0.5 hours on single GPU. **KEY INSIGHT: BiLLM ONLY works well on VERY LARGE models (70B). At 7B scale with 1-bit weights: perplexity is 29.79 for LLaMA2-7B (vs 5.47 FP16). That's a 5.4x perplexity increase — catastrophic for knowledge tasks. Extreme PTQ at small model sizes produces garbage.** |
| **GPTQ — "Accurate Post-Training Quantization for Generative Pre-trained Transformers"** (Frantar et al., 2022; arXiv:2210.17323; ICLR 2023) | One-shot weight quantization using approximate second-order information. At 3-4 bit: negligible accuracy degradation. At 2-bit: "reasonable accuracy." Quantizes 175B model in 4 GPU hours. **Well-established method. The important data point: even GPTQ, the gold standard for PTQ, only claims "reasonable" accuracy at 2-bit — not "good," not "comparable to FP16." For a maritime safety chatbot where accuracy is critical, "reasonable" is insufficient.** |
| **AWQ — "Activation-aware Weight Quantization for LLM Compression and Acceleration"** (Lin et al., 2023; arXiv:2306.00978; MLSys 2024 Best Paper) | Identifies that only 1% of weights are salient (determined by activation distribution, not weight magnitude). Scales salient channels to protect them during quantization. No backpropagation needed. TinyChat framework achieves 3x speedup over FP16 on mobile GPUs. **Deployed 70B Llama-2 on mobile GPUs using 4-bit. AWQ is optimized for 4-bit, not 2-bit. The approach's core insight — protecting salient weights — helps at 4-bit but cannot save quality at 2-bit where too many weight values must be collapsed.** |
| **LoftQ — "LoRA-Fine-Tuning-Aware Quantization"** (Li et al., 2023; arXiv:2310.08659) | Simultaneously quantizes LLM and finds proper low-rank LoRA initialization. Alleviates discrepancy between quantized and full-precision model. "Highly effective" in 2-bit and 2/4-bit mixed precision regimes. **Best paper for our scenario: domain-specific fine-tuning + quantization together. LoftQ suggests that if you quantize+LoRA simultaneously, you can partially recover quality lost at 2-bit. But even LoftQ shows significant gaps vs 4-bit at knowledge tasks.** |
| **LLaMA3 Quantization Empirical Study** (Huang et al., 2024; arXiv:2404.14047) | Comprehensive evaluation of 10 PTQ and LoRA-FT methods at 1-8 bits on LLaMA3. **THE MOST RELEVANT EMPIRICAL STUDY. Key finding: "LLaMA3 still suffers from non-negligible degradation in linguistic and visual contexts, particularly under ultra-low bit widths." Highlights "the significant performance gap at low bit-width that needs to be addressed." Even with the best methods (GPTQ, AWQ), 2-bit LLaMA3-8B has severely degraded performance compared to 4-bit on knowledge benchmarks.** |
| **QServe — W4A8KV4 Quantization** (Lin et al., 2024; arXiv:2405.04532) | System co-design for efficient LLM serving with 4-bit weights, 8-bit activations, 4-bit KV cache. Key insight: "the efficiency of LLM serving on GPUs is critically influenced by operations on low-throughput CUDA cores." Achieves 1.2-3.5x throughput improvement. **Validates that 4-bit (W4) is the practical sweet spot for quantized deployment. The industry is optimizing systems around W4, not W2. Ecosystem maturity strongly favors 4-bit.** |
| **GGUF Format & llama.cpp Quantization Types** (Gerganov et al., 2023-present) | The standard format for quantized model deployment on edge devices. Supports Q2_K, Q3_K, Q4_K, Q5_K, Q6_K, Q8 quantization types. **Q4_K_M is the community consensus sweet spot — best quality-to-size ratio. Q2_K exists but is widely acknowledged to produce poor quality at small model sizes. The llama.cpp community (millions of users) has empirically converged on Q4 as the floor for usable quality.** |

---

## THE FUNDAMENTAL QUESTION THIS EVALUATION MUST ANSWER

**Is a 7B model at 2-bit quantization better than a 1.7B model at 4-bit quantization for a knowledge-intensive maritime chatbot running on a mobile phone?**

### The Answer: No. The Math is Seductive but the Empirics are Brutal.

The information-theoretic argument for extreme quantization is elegant:

```
INFORMATION-THEORETIC ARGUMENT:
    
    7B model @ 2-bit: 7B × 2 bits = 14 Gbit of weight information
    1.7B model @ 4-bit: 1.7B × 4 bits = 6.8 Gbit of weight information
    
    The 7B@2-bit has 2.06x MORE raw information capacity!
    Memory usage: 7B × 2 / 8 = 1.75 GB  (fits on phone)
    vs.           1.7B × 4 / 8 = 0.85 GB (fits easily on phone)
    
    At equal memory budget (~1.75 GB):
    7B @ 2-bit  = 14 Gbit → MORE knowledge?
    3.5B @ 4-bit = 14 Gbit → SAME raw bits
    
    So why not go bigger and lower?
```

**The argument collapses on three empirical realities:**

```
┌────────────────────────────────────────────────────────────────────────┐
│        WHY 7B@2-BIT LOSES TO 1.7B@4-BIT FOR KNOWLEDGE TASKS          │
│                                                                        │
│  REALITY 1: QUANTIZATION ERROR IS NON-LINEAR                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ At 4-bit: 16 representable values per weight                    │  │
│  │ At 2-bit: 4 representable values per weight                     │  │
│  │                                                                  │  │
│  │ Going from 4→2 bit doesn't halve quality — it QUARTERS the      │  │
│  │ representable weight space.                                      │  │
│  │                                                                  │  │
│  │ Each weight in a 7B model at 2-bit can only be one of 4 values. │  │
│  │ The quantization error per weight is MUCH larger:                │  │
│  │   4-bit MSE: ε₄ ≈ Δ²/12 where Δ = range/16                    │  │
│  │   2-bit MSE: ε₂ ≈ Δ²/12 where Δ = range/4                     │  │
│  │   ε₂/ε₄ = 16 (quantization error is 16x WORSE at 2-bit)       │  │
│  │                                                                  │  │
│  │ This error COMPOUNDS across layers. A 7B model with 32 layers   │  │
│  │ accumulates 32 rounds of 16x-worse quantization noise.          │  │
│  │ A 1.7B model with 24 layers has 24 rounds of clean 4-bit.      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  REALITY 2: KNOWLEDGE IS STORED IN WEIGHT PRECISION                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ LLMs store factual knowledge in MLP weight matrices (Meng et    │  │
│  │ al., 2022 — "Locating and Editing Factual Associations in GPT"). │  │
│  │                                                                  │  │
│  │ Each fact = a specific weight configuration.                     │  │
│  │ "SOLAS Chapter II-2 Regulation 10 requires CO2 systems to be    │  │
│  │  tested every 2 years" is encoded as precise weight values.     │  │
│  │                                                                  │  │
│  │ At 2-bit, that precise configuration is CRUSHED into 4 values.  │  │
│  │ The model might remember "SOLAS has fire safety regulations"    │  │
│  │ but NOT "Regulation 10, CO2 systems, 2-year interval."          │  │
│  │                                                                  │  │
│  │ At 4-bit (16 values), the specific configuration has 4x more   │  │
│  │ precision to preserve the exact factual association.             │  │
│  │                                                                  │  │
│  │ For a maritime chatbot, PRECISION OF FACTS > BREADTH OF FACTS.  │  │
│  │ A wrong regulation number is worse than saying "I don't know."  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  REALITY 3: EMPIRICAL EVIDENCE IS OVERWHELMINGLY AGAINST 2-BIT        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ BiLLM on LLaMA2-7B at 1.08-bit: perplexity 29.79               │  │
│  │ LLaMA2-7B at FP16: perplexity 5.47                              │  │
│  │ → 5.4x degradation. Knowledge recall? Devastated.               │  │
│  │                                                                  │  │
│  │ GPTQ at 2-bit: "reasonable accuracy" (their words, not "good")  │  │
│  │                                                                  │  │
│  │ LLaMA3 quantization study: "significant performance gap at      │  │
│  │ ultra-low bit widths" even with best available methods           │  │
│  │                                                                  │  │
│  │ HuggingFace 1.58-bit fine-tuning: Llama3-8B-1.58 100B tokens   │  │
│  │ STILL LAGS behind original Llama3-8B on average benchmarks      │  │
│  │                                                                  │  │
│  │ llama.cpp community consensus: Q4_K_M is the FLOOR for usable   │  │
│  │ quality. Q2_K is for "model archaeologists" who want to SEE     │  │
│  │ what breaks, not for production use.                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  CONCLUSION:                                                           │
│  7B@2-bit has more raw bits but WORSE effective information due to     │
│  compounding quantization error. The 1.7B@4-bit retains facts more    │
│  precisely. For knowledge-intensive maritime QA:                       │
│                                                                        │
│  1.7B @ Q4_K_M ≫ 7B @ Q2_K                                           │
│                                                                        │
│  The larger model's extra capacity is wasted on quantization noise.    │
└────────────────────────────────────────────────────────────────────────┘
```

### The Native BitNet Exception — And Why It Doesn't Help

The above analysis applies to **post-training quantization** (PTQ) — taking a FP16 model and compressing it to 2-bit. There is one exception: **native BitNet b1.58** models, which are trained from scratch with ternary weights.

Native BitNet b1.58 allegedly matches FP16 quality at the same model size because the model LEARNS to represent information in {-1, 0, 1} — there is no quantization error because the weights were never full-precision to begin with.

**But this doesn't help our maritime chatbot for three reasons:**

```
REASON 1: TRAINING FROM SCRATCH
    BitNet b1.58 requires training from scratch.
    See: PRETRAINING_FROM_SCRATCH_RANKING_EVALUATION.md
    Score: 62/100 — primarily because maritime data scarcity
    ($100K-$300K) makes from-scratch training economically irrational.
    
    BitNet from scratch = from-scratch costs + all from-scratch limitations
    
REASON 2: FINE-TUNING TO 1.58-BIT DESTROYS KNOWLEDGE
    HuggingFace blog: Converting Llama3 8B to 1.58-bit via fine-tuning:
    - Even group_size=2 causes loss to spike from 1.45 → ~11
    - "Loses all of its prior information"
    - "Fine-tuning in low-bit mode on a specific dataset causes it 
       to lose much of its general knowledge"
    
    There is NO PRACTICAL PATH from an existing pretrained model to a 
    1.58-bit model that retains domain knowledge. You must train from 
    scratch or accept catastrophic knowledge loss.
    
REASON 3: MODEL ECOSYSTEM IS NEARLY EMPTY
    Official BitNet models as of Feb 2026:
    - BitNet-b1.58-2B-4T (Microsoft official, 2.4B params)
    - bitnet_b1_58-large (0.7B)
    - bitnet_b1_58-3B (3.3B)
    - Llama3-8B-1.58-100B-tokens (8B, HF experiment — lags FP16)
    - Falcon3 family 1.58-bit variants (1B-10B)
    
    NONE of these have maritime knowledge.
    NONE can be fine-tuned with maritime data without destroying 
    their existing knowledge (per HuggingFace findings).
    
    The only path to a maritime BitNet model is training from scratch
    with maritime data included in the pre-training corpus.
```

### What About the Middle Ground? 3-4 bit "Aggressive" Quantization?

If extreme (1-2 bit) quantization fails for knowledge tasks, what about pushing further into the 3-bit range to fit a slightly larger model?

```
MIDDLE GROUND ANALYSIS:
    
    Option A: 1.7B @ Q4_K_M = ~1.2 GB
    Option B: 3B  @ Q3_K_M  = ~1.4 GB  (3B × 3.4 avg bits / 8)
    Option C: 3B  @ Q4_K_M  = ~1.8 GB  (tight fit on 4GB phones)
    Option D: 7B  @ Q2_K    = ~2.1 GB  (tight fit on 4GB phones)
    
    Quality ranking (empirically validated by llama.cpp community):
    Option C > Option B > Option A >> Option D
    
    3B @ Q4 beats 7B @ Q2 by a massive margin.
    3B @ Q3 is debatable vs 1.7B @ Q4 — depends on model quality.
    
    THE SWEET SPOT for mobile with knowledge tasks:
    → Largest model that fits at Q4 quantization.
    → Currently: 3B-3.8B models at Q4 in ~1.8-2.2 GB.
    → NOT 7B at extreme quantization.
```

This analysis reveals that "extreme quantization" as defined (sub-3-bit) is NOT the optimal strategy. If you want to maximize knowledge per byte on mobile:

**Use the largest model that fits at Q4 (the quality floor), not a larger model at Q2.**

---

## TWO DISTINCT APPROACHES WITHIN "EXTREME QUANTIZATION"

This evaluation considers the approach as having two feasible variants, scored in combination:

| Variant | Description | Feasibility | Quality |
|---------|-------------|-------------|---------|
| **A: PTQ Extreme (2-bit on existing model)** | Take Qwen2.5-7B → AWQ/GPTQ to Q2 → deploy | Easy & cheap | Poor — severe knowledge degradation |
| **B: Native BitNet (1.58-bit from scratch)** | Train 3-7B model natively in ternary weights → deploy via bitnet.cpp | Very expensive & complex | Potentially good but unproven for domain-specific tasks |

Neither variant solves the core problem: getting deep maritime knowledge into a model that runs on mobile with high factual accuracy.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. Knowledge Retention — Score: 4/10

**The approach's CRITICAL weakness for a knowledge-intensive chatbot.**

Extreme quantization's impact on knowledge depends entirely on which variant:

**PTQ at 2-bit (Variant A):** Knowledge retention is catastrophically poor at small model sizes.

The most relevant empirical data comes from the LLaMA3 quantization study (arXiv:2404.14047): "LLaMA3 still suffers from non-negligible degradation in linguistic and visual contexts, particularly under ultra-low bit widths." This is on LLaMA3-8B — a strong model with extensive pretraining. Even it can't survive 2-bit PTQ.

BiLLM's results on LLaMA2-7B are even more damning: perplexity goes from 5.47 (FP16) to 29.79 (1.08-bit). For context, a perplexity of 29.79 means the model is essentially guessing semi-randomly. Factual knowledge — the kind we need for SOLAS regulations, diesel engine troubleshooting, and MARPOL annex details — is the FIRST thing to disappear under extreme quantization because it requires the most precision in weight values.

GPTQ, the most established method, describes 2-bit results as achieving "reasonable accuracy" — a tellingly modest claim from the method's own authors. For a maritime safety chatbot where wrong answers about fire-fighting systems or enclosed space entry could be dangerous, "reasonable" is not adequate.

**Native BitNet b1.58 (Variant B):** In theory, knowledge retention matches FP16 because the model is trained to use ternary weights natively. The BitNet b1.58 paper claims perplexity/performance parity with FP16 models at the same size and training tokens (note: this has some empirical nuance that is model and evaluation-dependent). But this requires training from scratch WITH the maritime domain data — inheriting all the limitations scored in the from-scratch evaluation (data scarcity, compute cost).

**The fine-tuning middle path is a dead end:** HuggingFace's 1.58-bit fine-tuning research conclusively showed that converting a pretrained model to 1.58-bit via fine-tuning "causes it to lose much of its general knowledge." Even with warmup quantization techniques and 100B tokens of retraining, the model lags behind the original. For maritime: any domain knowledge injected via fine-tuning at 1.58-bit would come at the cost of the model's general language abilities, conversational coherence, and safety behavior.

**Why not 3 or lower:** BiLLM demonstrates extreme PTQ CAN work at very large scale (70B@1-bit achieves 8.41 perplexity), but we're constrained to models that fit on mobile phones (1-7B). At these sizes, the information density per parameter is already low — removing further precision pushes below the minimum viable threshold for factual recall.

### 2. Inference Cost — Score: 10/10

**The approach's undeniable SUPERPOWER — the best inference economics of any method.**

BitNet b1.58 running via bitnet.cpp on ARM CPUs:
- **1.37-5.07x speedup** over FP16 on ARM processors (phones)
- **55.4-70.0% energy reduction** — critical for mobile battery life
- **INT8 addition only** — no floating-point multiplication needed for weight × activation
- **71.4x energy savings** for matrix multiplication operations vs FP16
- **100B model on single CPU at 5-7 tokens/sec** (human reading speed)

Latest optimizations (Jan 2026): parallel kernel implementations with configurable tiling add **1.15-2.1x additional speedup** across hardware platforms.

For 2-bit PTQ models (not native BitNet):
- ~2x memory bandwidth savings vs 4-bit → proportionally faster on memory-bound inference
- KV-cache reduction proportional to bit-width (with W2A8KV4 schemes)
- Estimated ~1.5-2x faster than Q4 at equivalent model size

This score of 10 reflects that extreme quantization is literally designed to minimize inference cost. No other approach achieves the same combination of speed, memory, and energy efficiency. For mobile deployment where battery life and latency matter:

```
Inference comparison (estimated, 3B model on iPhone 15):
    
    FP16:       ~12 GB, won't run
    Q8:         ~3.2 GB, barely fits, ~5 tok/sec
    Q4_K_M:     ~1.8 GB, comfortable, ~15 tok/sec
    Q2_K:       ~1.0 GB, very comfortable, ~25 tok/sec
    BitNet 1.58: ~0.6 GB, trivial, ~30-40 tok/sec (integer-only)
    
    BitNet inference is BY FAR the most phone-friendly.
```

### 3. Training Cost — Score: 5/10

**Mixed — depends entirely on which variant is used.**

**Variant A (PTQ on existing model):** The quantization step itself is trivially cheap:
- GPTQ: 4 GPU-hours for a 175B model → seconds to minutes for a 7B model
- AWQ: No backpropagation, just calibration — minutes on a single GPU
- Cost: effectively $0 for the quantization step

But you still need the maritime-knowledge-injected base model. If you SFT/CPT a 7B model with maritime data ($50-$2,000) and then quantize to 2-bit, the total cost is the base training cost. The quantization adds negligible overhead.

**The problem:** You spend $50-$2,000 injecting maritime knowledge... and then the 2-bit quantization destroys much of it. You're paying for knowledge injection and then compressing away the knowledge.

**Variant B (Native BitNet from scratch):** Requires pre-training from scratch with ternary weights. Microsoft trained BitNet-b1.58-2B-4T on 4T tokens — computational cost comparable to full pre-training. Estimated $100K-$500K for a 3-7B model.

HuggingFace's fine-tuning alternative required 10-100B tokens to approach (but not match) FP16 quality of the base model. At 100B tokens for an 8B model, that's still $50K+ in compute.

**Why 5/10:** If you use Variant A (PTQ), training cost is irrelevant — it's just the base model training cost. But the approach doesn't actually HELP with knowledge (scores 4/10 there), so the low quantization cost is meaningless. If you use Variant B (native BitNet), training cost is expensive. The weighted average lands at 5: cheap for the quantization step, expensive for the knowledge injection that actually matters.

### 4. Data Efficiency — Score: 5/10

**Another dimension with variant-dependent scoring.**

**PTQ Variant:** Data-efficient for the quantization step itself. AWQ explicitly requires NO backpropagation and does not overfit the calibration set — it "generalizes to different domains and modalities without overfitting." GPTQ needs a small calibration set (typically 128-256 samples). LoftQ combines quantization with LoRA in one step.

But there's a cruel irony: the data-efficient quantization step DESTROYS the domain knowledge that was painstakingly injected through the data-intensive SFT/CPT step. You efficiently compress away the knowledge you inefficiently put in.

**Native BitNet Variant:** Requires full pre-training data (see from-scratch evaluation). BitNet-b1.58-2B-4T trained on 4T tokens. Maritime domain has ~200M tokens. Efficiency is poor.

**Fine-tuning to 1.58-bit:** HuggingFace showed 10B tokens were needed for partial recovery, 100B tokens for closer-to-parity. That's 10-100B tokens of general data JUST to recover general knowledge, before any maritime data is introduced. Extremely data-hungry.

**Why 5/10:** The quantization step is efficient but the overall pipeline (getting maritime knowledge into an extreme-quantized model) requires either massive from-scratch data (BitNet native) or wastes the domain data injected earlier (PTQ destroys fine-tuned knowledge).

### 5. Accuracy on Domain QA — Score: 3/10

**CRITICAL FAILURE for a maritime chatbot. This score alone should disqualify extreme quantization.**

Maritime domain QA requires:
- **Precise regulation references:** "MARPOL Annex VI, Regulation 14.1 limits SOx emissions to 0.50% m/m" — at 2-bit, the model might say "0.35%" or "Regulation 13" or "Annex V." Wrong answers are worse than no answer.
- **Exact numeric values:** Diesel engine injection timing in degrees, safety valve set pressures in bar, fire pump capacity in m³/hr — 2-bit quantization rounds these away.
- **Complex procedural sequences:** Enclosed space entry procedures have specific ordered steps. At 2-bit, the model might swap, skip, or hallucinate steps.
- **Multi-part regulatory compliance:** "Under STCW Section A-VIII/2 Part 3-1, the Master must ensure..." — this requires precise lookup from weight matrices, which 2-bit cannot support.

The LLaMA3 quantization study tested across multiple QA benchmarks and found "significant performance gap at low bit-width." Knowledge-intensive benchmarks (MMLU, ARC, TriviaQA) degrade faster than reasoning benchmarks at ultra-low precision because factual recall depends more on precise weight values.

**Comparison at equal memory budget:**

| Config | Estimated MMLU (rough, based on published data patterns) | Maritime QA Estimate |
|--------|------------------------------------------------------|---------------------|
| Llama3-8B FP16 | ~66% | Baseline (with SFT) |
| Llama3-8B Q4 | ~64% (-2%) | Minimal loss |
| Llama3-8B Q2 | ~45-50% (-20%) | Severe loss |
| Qwen2.5-1.5B Q4 | ~55-58% | Moderate (with SFT) |
| Qwen2.5-3B Q4 | ~62-65% | Good (with SFT) |

The 8B@Q2 model that fits in ~2GB scores WORSE on knowledge benchmarks than a 3B@Q4 model that also fits in ~2GB. The extra parameters are wasted on quantization noise.

**Why not 1 or 2:** If using native BitNet b1.58 from scratch with maritime data, domain QA accuracy could potentially match FP16 quality (per BitNet b1.58 claims). This theoretical possibility, plus the fact that LoftQ + fine-tuning can partially recover 2-bit quality, bumps the score above rock bottom.

### 6. Mobile Deployability — Score: 10/10

**Tied for the best score on any criterion — extreme quantization IS mobile optimization.**

This is the entire raison d'être of extreme quantization. The deployment characteristics are extraordinary:

**Memory footprint:**
- BitNet 3B: ~0.4 GB (ternary weights packed efficiently)
- BitNet 7B: ~0.9 GB (still easily fits on any modern phone)
- 7B @ Q2: ~1.75 GB (fits on most phones with 4GB+ RAM)
- Compare: 7B @ Q4: ~3.5 GB (tight on many phones)
- Compare: 7B FP16: ~14 GB (impossible on any phone)

**CPU compatibility via bitnet.cpp:**
- Optimized ARM kernels (TL1 kernel) specifically for phone processors
- Supports Apple Silicon (M-series chips in iPhones/iPads)
- Integer-only arithmetic — uses phone CPU's INT8 capabilities natively
- No GPU/NPU required (works on pure CPU — universal phone compatibility)

**Battery efficiency:**
- 55-70% energy reduction vs FP16 on ARM
- Critical for a mobile app — users won't tolerate a chatbot that drains battery
- INT8 operations consume far less power than FP16 on phone SoCs

**Startup time:**
- Smaller model files = faster loading from storage
- BitNet 3B at 0.4 GB loads in <2 seconds from flash storage
- Compare: 7B@Q4 at 3.5 GB takes 5-10 seconds to load

**Why 10/10:** No other approach achieves this level of mobile optimization. Extreme quantization literally transforms models too large for phones into models that run comfortably. The question isn't whether it deploys well — it's whether it retains enough knowledge to be useful (which is scored in other criteria).

### 7. Robustness — Score: 3/10

**Ultra-low bit models are fragile and unpredictable.**

Robustness in a maritime context means: the model gives consistent, reliable answers across different phrasings of the same question and doesn't produce dangerous hallucinations under normal use.

At 2-bit PTQ:
- **Quantization noise accumulates across transformer layers.** Each layer adds error. A 32-layer 7B model accumulates 32 rounds of 2-bit quantization noise vs 24 rounds of 4-bit noise in a smaller model. The 2-bit noise per layer is ~16x worse (see information-theoretic analysis above).
- **Outlier activations cause disproportionate damage.** LLMs have activation outliers that are critical for model behavior. At 4-bit, these outliers can be approximately represented. At 2-bit, they're crushed to the nearest of 4 values — potentially flipping the output entirely. AWQ was designed to protect these salient channels, but its protection is less effective at 2-bit.
- **Temperature sensitivity increases.** At 2-bit, the model's probability distributions are noisier, making sampling more erratic. Small changes in temperature have larger effects on output quality.
- **Input sensitivity is amplified.** The same factual question phrased differently can produce wildly different answers because the quantization noise interacts differently with different input embeddings.

**Native BitNet b1.58 is potentially more robust** (the model learned to function with ternary weights, so its behavior is self-consistent). But this is theoretical — there are no published robustness studies on BitNet b1.58 models for domain-specific QA.

**For maritime safety:** A chatbot that gives correct enclosed space entry procedures 80% of the time and dangerous incomplete procedures 20% of the time is WORSE than no chatbot at all. Robustness is not optional in a safety-critical domain.

### 8. Catastrophic Forgetting — Score: 5/10

**Quantization IS a form of permanent, irreversible information loss — not "forgetting" in the traditional sense, but functionally identical.**

When you quantize a 7B model from FP16 to 2-bit:
- Each weight goes from 65,536 representable values to 4 representable values
- The information lost is permanent — there is no "un-quantizing" back to full quality
- The lost information includes factual associations, nuanced relationships, and domain knowledge
- This is analogous to catastrophic forgetting after CPT, but:
  - **Worse:** The loss is structural (precision) rather than directional (gradient updates)
  - **There is no selective protection:** Every weight loses precision, not just the ones being updated
  - **No EWC, LoRA, or learning rate tricks can mitigate it** (the weights are already written)

Fine-tuning AFTER extreme quantization is particularly dangerous:
- The HuggingFace 1.58-bit blog confirms: fine-tuning at ultra-low precision "causes it to lose much of its general knowledge"
- LoftQ attempts to address this by finding good LoRA initialization during quantization, but at 2-bit, the gap is still significant
- Any maritime SFT on a 2-bit model risks further destabilizing already fragile weights

**For native BitNet b1.58 trained from scratch:** No forgetting by definition — same as from-scratch pretraining. This pulls the score up from 3 to 5.

**The cruel pipeline:** Many users would want to: (1) CPT existing model with maritime data → (2) SFT on maritime Q&A → (3) Quantize to 2-bit for mobile. Step 3 permanently destroys much of the knowledge from steps 1 and 2. You cannot pipeline domain injection and extreme quantization without significant loss.

### 9. Maintenance — Score: 5/10

**Update mechanics depend heavily on variant.**

**PTQ Variant (update workflow):**
1. Update base model with new maritime regulations (via CPT/SFT on FP16 model) — cheap
2. Re-quantize to 2-bit — trivially cheap and deterministic
3. Re-deploy — standard OTA update

This workflow is actually reasonable from a maintenance perspective. GPTQ/AWQ quantization is deterministic and reproducible — the same model always produces the same quantized output. Re-quantization costs minutes, not hours.

**BUT:** The quality degradation from step 2 applies equally to updated knowledge. Every maintenance cycle loses the same fraction of knowledge. You're maintaining a model that's permanently below the quality threshold you need.

**Native BitNet Variant (update workflow):**
1. Re-train from scratch with updated maritime data — $100K+
2. Or: Fine-tune existing BitNet model with new data — loses general knowledge (per HF findings)
3. No practical incremental update path

**Why 5/10:** The PTQ variant has a clean, cheap maintenance workflow (update base model → re-quantize → deploy). But the fundamental quality problem persists through every update. The BitNet variant has no practical maintenance path. Average: 5.

### 10. Proven at Small Scale — Score: 3/10

**Extreme quantization for knowledge tasks at small scale is essentially UNPROVEN.**

**What IS proven:**
- 4-bit quantization (Q4) on 1-7B models: extensively proven, millions of users via llama.cpp, GGUF ecosystem
- BitNet b1.58 inference on CPU: proven by bitnet.cpp demo and Microsoft's official 2B-4T model
- GPTQ/AWQ at 4-bit: proven in production (MLSys best paper, deployed at scale)

**What is NOT proven:**
- 2-bit quantization on <7B models for knowledge-intensive QA: NO published success cases
- Native BitNet for domain-specific knowledge (maritime, medical, legal): NO published examples
- BitNet fine-tuning that retains domain knowledge: EXPLICITLY SHOWN TO FAIL by HuggingFace
- Any extreme quantization approach deployed as a domain-specific mobile chatbot: NO precedents

**The ecosystem maturity gap:**

| Quantization Level | Runtime Support | Model Availability | Production Deployments | Domain-Specific Results |
|------|------|------|------|------|
| 4-bit (Q4) | llama.cpp, MLC-LLM, TensorRT, ONNX, CoreML | Thousands of models | Millions of users | YES (many domains) |
| 3-bit (Q3) | llama.cpp | Hundreds of models | Some users | Limited |
| 2-bit (Q2) | llama.cpp (Q2_K), GPTQ | Dozens of models | Experimental | NONE published |
| 1.58-bit (BitNet) | bitnet.cpp only | <10 models | Microsoft demo only | NONE published |

**The software supply chain is immature:**
- bitnet.cpp supports only specific model architectures and kernels
- No iOS/Android SDK for bitnet.cpp (command-line only as of Feb 2026)
- No CoreML/NNAPI support for 1.58-bit inference
- Building a mobile app with bitnet.cpp would require custom native code and significant engineering
- Compare: llama.cpp has mature iOS/Android integration with 4-bit models running in production apps

**Why not 1/10:** BitNet-b1.58-2B-4T EXISTS and RUNS on ARM CPUs. Microsoft has committed significant resources (28.5K GitHub stars, active development). The technology is real and advancing rapidly. The Falcon3 family has 1.58-bit variants. It's unproven for our use case but not vaporware. The trajectory from Oct 2024 (bitnet.cpp 1.0) to Feb 2026 (GPU kernels, optimized ARM, official 2B model) shows rapid maturation.

---

## COMPLETE SCORING TABLE

| Criterion | Score | Weight | Rationale |
|---|:---:|:---:|---|
| 1. Knowledge Retention | 4/10 | Critical | PTQ 2-bit destroys factual knowledge — BiLLM 7B goes from 5.47→29.79 perplexity. Knowledge stored in weight precision; 4 values per weight cannot encode precise facts. Native BitNet avoids this but requires from-scratch training. |
| 2. Inference Cost | 10/10 | Important | Best possible: BitNet uses INT8 addition only, 71.4x energy savings, 1.37-5.07x ARM speedup. 0.4 GB for a 3B model. No approach is faster or more efficient at inference. |
| 3. Training Cost | 5/10 | Critical | PTQ quantization step is trivially cheap ($0, minutes). But native BitNet requires from-scratch training ($100K+). Fine-tuning to 1.58-bit requires 10-100B tokens. Split verdict. |
| 4. Data Efficiency | 5/10 | Critical | PTQ needs only small calibration set (efficient). But injecting domain knowledge at ultra-low precision is self-defeating — you efficiently compress away the knowledge you put in. |
| 5. Accuracy on Domain QA | 3/10 | Critical | CRITICAL FAILURE. Maritime QA needs precise regulation numbers, temperatures, procedures. 2-bit models hallucinate these. 8B@Q2 scores worse than 3B@Q4 on MMLU. "Reasonable accuracy" (GPTQ) ≠ production accuracy. |
| 6. Mobile Deployability | 10/10 | Important | Perfect: 0.4 GB for 3B model, ARM kernel optimization, no GPU needed, 55-70% energy reduction, loads in <2s. THE reason this approach exists. |
| 7. Robustness | 3/10 | Important | 2-bit quantization noise compounds across layers (16x worse per layer vs 4-bit). Outlier activations crushed. Input sensitivity amplified. Inconsistent answers to same question. |
| 8. Catastrophic Forgetting | 5/10 | Important | Quantization = permanent irreversible information loss. Fine-tuning after 2-bit quantization further destabilizes weights. HF blog: "loses much of its general knowledge." Native BitNet avoids this if trained from scratch. |
| 9. Maintenance | 5/10 | Moderate | PTQ variant: clean re-quantize workflow (minutes, deterministic). But quality problem persists through every update. Native BitNet: no practical update path. |
| 10. Proven at Small Scale | 3/10 | Critical | No published domain-specific success at 2-bit. bitnet.cpp < 2 years old. No iOS/Android SDK. No production maritime/medical/legal chatbot at sub-3-bit. 4-bit ecosystem is 100x more mature. |

---

## TOTAL SCORE: 53/100

---

## KEY STRENGTHS (3)

### Strength 1: Unmatched Inference Efficiency — The Most Mobile-Friendly Approach by Far

Extreme quantization, especially native BitNet b1.58, achieves inference characteristics that no other approach can match:

- **0.4 GB for a 3B model** — this is extraordinary. A maritime chatbot at this size leaves >90% of the phone's RAM for other apps. Compare to 1.8 GB for 3B@Q4 or 3.5 GB for 7B@Q4.
- **Integer-only arithmetic** — BitNet's matmul uses INT8 additions instead of FP16 multiply-add operations. Mobile SoCs (Apple A-series, Qualcomm Snapdragon) have dedicated integer units that are faster and more energy-efficient than their FP units.
- **5-7 tokens/sec on CPU for 100B models** — Microsoft demonstrated a 100B parameter model running at human reading speed on a single CPU. For our 3-7B models, expect 40-100+ tokens/sec on modern phone CPUs.
- **55-70% energy reduction on ARM** — a maritime engineer using the chatbot during a watch doesn't want it draining their phone battery. BitNet's energy profile means continuous use is practical.
- **Sub-second first-token latency** — smaller model + faster operations = nearly instant response even on mid-range phones.

If inference cost were the only criterion, extreme quantization would be the obvious winner. The technology genuinely enables a new class of mobile AI applications.

### Strength 2: Fits Larger Model Architectures on Mobile — Future-Proofing

Even though our analysis shows 7B@2-bit doesn't beat 3B@4-bit for KNOWLEDGE tasks today, extreme quantization keeps the door open for a critical future scenario:

As BitNet b1.58 matures and larger natively-trained ternary models become available, the quality equation could flip. A natively-trained BitNet 7B model (no quantization error, ternary by design) at ~0.9 GB would:
- Have more parameters than 3B@Q4 (1.8 GB) at HALF the memory
- Potentially match FP16 7B quality (per BitNet b1.58 claims)
- Run significantly faster on ARM CPUs

The BitNet ecosystem is advancing rapidly:
- Oct 2024: bitnet.cpp 1.0
- Apr 2025: Official 2B-4T model
- May 2025: GPU kernels
- Jan 2026: Further CPU optimizations with 1.15-2.1x speedup
- Future: Larger models, GPU support, mobile SDKs

If Microsoft or the community releases a BitNet 7B natively-trained model with quality comparable to Llama-3-7B, and if domain-specific fine-tuning methods are developed that preserve quality (a big "if"), extreme quantization becomes the clear winner for mobile deployment.

### Strength 3: Quantization Can Be Combined With Other Approaches at Moderate (4-bit) Levels

While extreme (sub-3-bit) quantization fails for knowledge tasks, the research insights from AWQ and LoftQ are directly applicable to improving the standard 4-bit deployment pipeline:

- **AWQ's salient channel protection** — when quantizing a maritime-SFT'd model to Q4, AWQ's activation-aware approach preserves the most important weights (likely the ones encoding maritime facts learned during SFT).
- **LoftQ's quantization-aware LoRA** — instead of "train → quantize → hope for the best," you can quantize and initialize LoRA adapters simultaneously. This means: quantize base model to Q4, then maritime LoRA fine-tuning is already quantization-aware. Better quality at Q4 with a tiny LoRA overhead.
- **GPTQ's second-order information** — provides the most mathematically grounded quantization at any bit level, minimizing the quantization error that matters most for downstream performance.

These insights improve the 4-bit deployment path that other approaches (CPT, SFT) will ultimately use.

---

## KEY WEAKNESSES (3)

### Weakness 1: Factual Knowledge Destruction at Sub-4-bit — A Fundamental, Unsolvable Problem for PTQ

This is not a "needs more research" problem — it is an information-theoretic barrier. When you represent each weight with only 4 values (2-bit) instead of 16 values (4-bit) or 65,536 values (FP16), you permanently destroy fine-grained weight configurations that encode factual associations.

The evidence is consistent across every study:
- **BiLLM:** LLaMA2-7B perplexity 5.47 → 29.79 at 1.08-bit (5.4x degradation)
- **GPTQ authors:** "reasonable accuracy" at 2-bit (contrast: "negligible degradation" at 4-bit)
- **LLaMA3 quantization study:** "significant performance gap at ultra-low bit widths"
- **HuggingFace 1.58-bit:** 100B tokens of fine-tuning still lags FP16 Llama3-8B
- **llama.cpp community:** Q2_K is acknowledged as unusably poor for factual tasks

For a maritime chatbot where factual precision is the PRIMARY value proposition:
- "What is the minimum thickness for a hull plate under IACS UR S2?" — requires precise numeric recall
- "Describe the procedure for testing a CO2 fixed fire-fighting system" — requires ordered procedural steps
- "Under MARPOL Annex I, what is the maximum oil content for operational discharges?" — requires exact regulatory values

A model that gets these wrong 20-30% of the time due to quantization noise is DANGEROUS, not just inconvenient. Maritime regulations exist because people die when they're not followed correctly.

**No amount of engineering can fix this for PTQ.** The information is destroyed during quantization. AWQ protects 1% of salient weights — but maritime facts are distributed across millions of weights, not concentrated in 1%. GPTQ minimizes quantization error — but the error floor at 2-bit is still unacceptably high for factual QA.

### Weakness 2: The BitNet Ecosystem Is 18+ Months From Mobile-Ready Production

Even if native BitNet b1.58 solves the quality problem (no quantization error by design), the ecosystem is far from production-ready for a mobile chatbot:

**Model availability (Feb 2026):**
- BitNet-b1.58-2B-4T: the ONLY official production-quality model. Trained on 4T tokens, but it's a general-purpose model — no maritime knowledge.
- Falcon3 1.58-bit variants: available but not domain-specialized.
- No pipeline exists for injecting maritime domain knowledge into a 1.58-bit model post-training.

**Runtime maturity:**
- bitnet.cpp: command-line only. No iOS SDK. No Android SDK. No mobile framework integration.
- Building a mobile app with bitnet.cpp would require:
  - Compiling bitnet.cpp for iOS/Android ARM targets
  - Writing native C++ bindings
  - Custom UI/UX framework
  - Handling model loading, memory management, background execution on mobile OS
  - Apple App Store review (custom ML runtime may face scrutiny)
- Compare: llama.cpp has mature mobile integration (llama.swift, llama-android), production apps in App Store/Play Store, months of battle-testing

**Fine-tuning infrastructure:**
- No established pipeline for BitNet domain fine-tuning without knowledge loss
- HuggingFace's research showed the challenge — solutions don't exist yet
- The training tips from Microsoft ("Training Tips, Code and FAQ") are preliminary

**Timeline estimate:**
- Mobile SDK for bitnet.cpp: 6-12 months (if prioritized)
- Domain fine-tuning methods that preserve quality: 12-24 months (active research area)
- Multiple maritime-relevant BitNet models available: 24+ months
- Production-hardened mobile deployment pipeline: 18-24 months

For a maritime chatbot project with a NEAR-TERM deployment goal, extreme quantization via native BitNet is a future technology bet, not a current solution.

### Weakness 3: Wrong Tool for the Job — Optimizing the WRONG Constraint

Extreme quantization solves the problem of "how do I run a very large model on limited hardware?" But for a maritime mobile chatbot, this is NOT the binding constraint.

**The binding constraints for a maritime chatbot are:**

| Constraint | Is Extreme Quantization the Solution? |
|---|---|
| ① Knowledge accuracy | ❌ WORSE (quantization destroys facts) |
| ② Model fits on phone | ✅ YES (excellent mobile fit) |
| ③ Sufficient domain coverage | ❌ NEUTRAL or WORSE (no domain models exist) |
| ④ Reliable, safe answers | ❌ WORSE (quantization noise → more hallucination) |
| ⑤ Updateable with new regulations | ⚠️ MIXED (re-quantize works, but quality floor persists) |
| ⑥ Affordable to build | ⚠️ MIXED (PTQ is cheap, BitNet from scratch is expensive) |

Constraint ② (fitting on phone) is ALREADY SOLVED by standard 4-bit quantization. A 1.7B@Q4 model at ~1.2 GB runs comfortably on any phone from 2022 onwards. A 3B@Q4 at ~1.8 GB fits on any phone from 2023 onwards.

The problem that needs solving is NOT "how to fit an even bigger model on the phone" — it's "how to get maximum FACTUAL ACCURACY out of the model that ALREADY fits." Extreme quantization aggressively optimizes for mobile fit (already solved) at the cost of factual accuracy (the actual bottleneck).

**The car analogy:** The maritime chatbot is a delivery truck. The binding constraint is "can the truck carry the cargo safely?" (knowledge accuracy). Extreme quantization is "let's make the truck go 200 mph" — impressive engineering, but the cargo falls out of the faster truck. Standard 4-bit quantization is a truck that goes 60 mph with all cargo secure. The maritme chatbot needs 60 mph with secure cargo, not 200 mph with scattered cargo.

---

## VERDICT

**Extreme quantization scores 53/100 — a technically impressive approach that optimizes the WRONG dimension for a maritime knowledge chatbot.**

The approach achieves extraordinary inference efficiency (10/10) and mobile deployability (10/10) but fundamentally fails on the dimensions that matter most for a maritime chatbot: knowledge retention (4/10), domain QA accuracy (3/10), and robustness (3/10).

**The core thesis — "7B@2-bit beats 1.7B@4-bit for knowledge" — is FALSE for post-training quantization.** The 7B model has more raw parameter capacity, but 2-bit quantization destroys that capacity faster than 4-bit preserves it. Empirically, across every published study, sub-4-bit PTQ shows "significant performance gaps" on knowledge benchmarks while 4-bit shows "negligible degradation."

**The native BitNet exception is theoretically valid but practically unavailable.** If a native BitNet 7B model existed, was trained from scratch on maritime data, and could be fine-tuned without knowledge loss — THEN this approach would score 70-80/100. But that model doesn't exist, the training would cost $100K+, and fine-tuning 1.58-bit models without knowledge destruction is an unsolved research problem.

**Recommendation:** Use standard Q4 quantization on the largest model that fits on phone (~3B@Q4 ≈ 1.8GB). Apply AWQ or GPTQ for optimal 4-bit quality. Use the extreme quantization research insights (salient channel protection, quantization-aware LoRA via LoftQ) to improve 4-bit deployment, not to push below 4-bit. Revisit extreme quantization in 2027-2028 when native BitNet models are larger, more numerous, and have established domain fine-tuning methods.

**The physics of it:** 4-bit is the QUALITY FLOOR for factual LLMs at small scale. Below 4-bit, you're compressing faster than you're thinking. The quantization noise exceeds the signal for precise factual recall. Above 4-bit (Q5, Q6, Q8), you're trading mobile storage for marginal quality gains. Q4 is the Goldilocks zone — and the maritime chatbot should live there.

---

## BEST COMBINATION: How to Use Extreme Quantization Insights Without Sub-4-bit Deployment

```
RECOMMENDED: Extract the RESEARCH INSIGHTS, deploy at Q4.

THE KEY INSIGHT FROM EXTREME QUANTIZATION RESEARCH:
    Not all weights are equally important for knowledge preservation.
    AWQ showed 1% of weights (salient channels) carry disproportionate
    information. PROTECT these during quantization.

STEP 1: SELECT BASE MODEL (cost: $0)
    │   Qwen2.5-3B or SmolLM3-3B (largest model fitting phone at Q4)
    │   Fits at ~1.8 GB in Q4_K_M — comfortable on modern phones
    │
    ▼
STEP 2: INJECT MARITIME KNOWLEDGE (cost: $200-$2,000)
    │   CPT with maritime data (regulations, textbooks, synthetic)
    │   SFT with maritime Q&A pairs
    │   DPO alignment for safety-critical responses
    │
    ▼
STEP 3: QUANTIZE WITH AWQ/GPTQ — SMARTLY (cost: $0, minutes)
    │   Use AWQ (activation-aware) to protect salient weights:
    │   ├── Maritime knowledge is encoded in specific weight channels
    │   ├── AWQ identifies which channels carry maritime knowledge
    │   │   (via activation statistics on maritime calibration data)
    │   └── These channels get extra precision during Q4 quantization
    │
    │   Or use LoftQ for quantization-aware LoRA:
    │   ├── Quantize base model to Q4
    │   ├── Initialize LoRA adapters optimally for the quantized model
    │   └── Fine-tune LoRA on maritime data (quantization-aware from start)
    │
    ▼
STEP 4: DEPLOY ON MOBILE (cost: $0)
    │   llama.cpp (mature iOS/Android support)
    │   GGUF format Q4_K_M (community standard, battle-tested)
    │   3B model @ Q4: ~15 tok/sec on iPhone, <2 GB RAM
    │
    ▼
STEP 5: FUTURE-PROOF (cost: $0 now, revisit in 18-24 months)
        Monitor BitNet ecosystem maturity:
        ├── When BitNet 3-7B models with quality ≥ Q4 emerge
        ├── When mobile SDK for bitnet.cpp exists
        ├── When domain fine-tuning preserves knowledge
        └── THEN: Switch to BitNet for 2x memory savings + faster inference

TOTAL COST: $200-$2,000
TOTAL TIME: 2-5 days
MODEL SIZE: 3B @ Q4_K_M ≈ 1.8 GB

vs.

EXTREME QUANTIZATION APPROACH:
    Option A (PTQ 2-bit): Same cost, WORSE quality, smaller file
    Option B (Native BitNet): $100K+ cost, unproven quality, no maritime models

THE CORRECT USE OF EXTREME QUANTIZATION:
    → Use AWQ/GPTQ insights for BETTER 4-bit quantization
    → Use LoftQ for quantization-aware maritime fine-tuning
    → Monitor BitNet for FUTURE adoption (2027+)
    → Do NOT deploy sub-4-bit for knowledge-intensive chatbot in 2026
```

**The Decisive Answer to the Key Question:**

> **"Is a 7B@2-bit better than 1.7B@4-bit for a knowledge-intensive mobile chatbot?"**

**NO.** For post-training quantization, 1.7B@4-bit retains factual knowledge significantly better than 7B@2-bit. The additional parameters in the 7B model cannot compensate for the 16x-worse quantization error per weight. Empirical evidence from BiLLM, GPTQ, AWQ, and the LLaMA3 quantization study unanimously confirms that sub-4-bit PTQ produces "significant performance gaps" incompatible with factual QA requirements.

The optimal strategy is: **use the LARGEST model that fits at Q4 quantization.** For mobile phones in 2026 with 4-6 GB RAM, that's a **3B-3.8B model at Q4_K_M (1.8-2.2 GB)** — not a 7B model at Q2_K (2.1 GB). Same memory, dramatically better factual accuracy, proven deployment pipeline, battle-tested ecosystem.

**The future possibility:** If BitNet b1.58 native training matures and 7B+ models become available that match FP16 quality at 1.58 bits, the equation reverses entirely. A native BitNet 7B at ~0.9 GB would outclass any Q4 model. But that future is 18-24 months away, and training a maritime-specific BitNet model remains a $100K+ proposition. The pragmatic choice today is Q4 on the best available 3B model, with an eye toward BitNet migration when the ecosystem matures.
