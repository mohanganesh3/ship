# RANKING EVALUATION: Model Merging

**Approach Under Evaluation:** Train multiple specialist LoRA adapters (engineering, navigation, safety, regulations) and merge them into a single model using weight-space techniques (TIES, DARE, SLERP, Task Arithmetic, Evolutionary Merging), or merge a domain-fine-tuned model with a general-purpose model to get best of both.

**Evaluator:** Ranking Agent  
**Date:** February 16, 2026  
**Target:** Maritime chatbot on mobile phones, NO RAG, all knowledge baked into weights  
**Model Size Constraint:** 1-3B parameters  
**Deployment:** ARM CPU, 3-6GB RAM, iOS/Android  

---

## RESEARCH BASIS

This evaluation draws on deep analysis of the following papers and resources:

| Paper | Key Finding for This Evaluation |
|-------|-------------------------------|
| **TIES-Merging** (arXiv:2306.01708, NeurIPS 2023) | Resolves interference from redundant parameters and sign disagreements via Trim, Elect Sign & Merge. Outperforms prior merge methods. But: "existing merging methods often ignore the interference between parameters of different models, resulting in large performance drops." TIES mitigates but doesn't eliminate this. |
| **DARE** (arXiv:2311.03099, ICML 2024) | SFT delta parameters have extreme redundancy — DARE can eliminate **90% or even 99%** without affecting SFT model abilities. Enables better multi-model merging. Critical: "this phenomenon is more pronounced in large-scale LMs" — explicitly weaker at small scale. |
| **Task Arithmetic** (arXiv:2212.04089, ICLR 2023) | Task vectors (fine-tuned weights minus pre-trained weights) can be added/subtracted/composed via arithmetic. Simple, elegant, effective for multi-task composition. But designed for style/capability composition, NOT deep factual knowledge transfer. |
| **Evolutionary Model Merging** (arXiv:2403.13187, Nature Machine Intelligence 2025) | Sakana AI: genetic algorithms automatically discover optimal merge recipes. Created Japanese Math LLM surpassing much larger models. Operates in both parameter space AND data flow space. Requires extensive evaluation compute. |
| **DELLA** (arXiv:2406.11617) | Magnitude-based pruning (MAGPRUNE) improves over DARE/TIES. Higher-magnitude parameters get lower dropout probability. 2.4-point average improvement over pruning baselines, 11.1 points over no-pruning Task Arithmetic. |
| **Model Soups** (arXiv:2203.05482, ICML 2022) | Averaging weights of multiple fine-tuned models (different hyperparameters, same task) improves accuracy AND robustness with zero extra inference cost. Works because fine-tuned models lie in a single low error basin. Key insight: averaging is a free lunch for robustness. |
| **LM-Cocktail** (arXiv:2311.13534) | Merging fine-tuned LM with base model or peer models via weighted average preserves general capabilities while maintaining domain strength. "Surprisingly effective" — resilient tuning without additional training. |
| **SmolLM3** (HuggingFace blog, July 2025) | **Production validation at 3B scale.** Used MergeKit with model soup of APO checkpoints, then linear merge (0.9 APO soup + 0.1 mid-training checkpoint) to recover long-context performance. Merging was used to FIX a regression, NOT to inject new knowledge. |
| **mergekit** (arcee-ai/mergekit) | The standard open-source library implementing SLERP, TIES, DARE (dare_ties, dare_linear), linear, passthrough merging. CPU-only, runs in minutes. Active development. |
| **Merge Models Guide** (mlabonne, HuggingFace blog) | Practical configurations for SLERP, TIES, DARE, passthrough. Community finding: only models with **identical architecture** can be merged. Most successful merges are 7B+ models. |

---

## THE FUNDAMENTAL MISUNDERSTANDING THIS APPROACH EMBEDS

Before scoring, a critical clarification:

**Model merging is a COMPOSITION technique, not a KNOWLEDGE INJECTION technique.** It combines capabilities that **already exist** in individual models. It does NOT create new knowledge. It cannot make a model know things none of its source models know.

The proposal has two variants. Both have fundamental issues for our use case:

### Variant 1: Train 4 specialist LoRAs → Merge them

```
Base Model (SmolLM3-3B)
    ├── LoRA: Engineering specialist
    ├── LoRA: Navigation specialist
    ├── LoRA: Safety specialist
    └── LoRA: Regulations specialist
         ↓
    DARE-TIES merge → Single model with all 4 specialties
```

**The problem:** You're starting with LoRA fine-tuning, which per "LoRA Learns Less and Forgets Less" (arXiv:2405.09673) **underperforms full fine-tuning for knowledge acquisition**. LoRA's low-rank constraint (rank 16-64) cannot modify weight matrices enough to encode complex new factual knowledge. Then you're MERGING these already-limited adaptations, introducing another layer of degradation through parameter interference.

**You're compounding two weak approaches:** Poor knowledge injection (LoRA) + lossy combination (merging).

### Variant 2: Merge maritime fine-tuned model with general model

```
Maritime fine-tuned model (90% weight) + General base model (10% weight) → Merged model
```

**This is SmolLM3's approach** — but for a different purpose. SmolLM3 merged to RECOVER lost general capabilities (long-context), not to ADD domain knowledge. The merge DILUTES domain knowledge by 10% to recover general capabilities. This is a reasonable trade-off IF you have strong domain knowledge to start with. But if the domain knowledge is weak (SFT/LoRA-only), diluting it further is harmful.

### What merging actually excels at:

| Merging Is Great For | Merging Is Bad For |
|---------------------|-------------------|
| Combining style/format capabilities | Injecting new factual knowledge |
| Recovering lost general capabilities | Adding domain-specific facts |
| Improving robustness/OOD performance | Precise numerical/procedural recall |
| Reducing catastrophic forgetting | Creating knowledge that wasn't in inputs |
| Averaging hyperparameter variations | Combining highly dissimilar domains |

**For maritime:** The 4 specialist domains (engineering, navigation, safety, regulations) share lots of terminology and conceptual overlap. This is NOT the same as merging "code + math + general" — maritime subdomains are highly inter-related. A CO₂ fire suppression question touches engineering (system design), safety (SOLAS requirements), AND regulations (FSS Code). Splitting into specialists and merging back makes less sense than training a single coherent maritime model.

---

## CRITERION-BY-CRITERION EVALUATION

### 1. KNOWLEDGE RETENTION — Score: 4/10

**The core question:** Can model merging help the maritime chatbot retain more domain knowledge than a single fine-tuned model?

**What the evidence says:**

**Merging does not add knowledge — it averages, trims, and sometimes destroys it.**

The TIES paper identified two sources of interference during merging:
- **(a) Redundant parameter values** — parameters that changed only slightly during fine-tuning add noise. TIES trims the bottom-k% (by magnitude).
- **(b) Sign disagreement** — when different models push the same parameter in opposite directions, simple averaging cancels them out. TIES resolves by majority vote on sign.

These mitigations help, but they fundamentally involve **discarding information**:
- TIES trims parameters (throws away small deltas)
- DARE randomly drops 90-99% of deltas (throws away most changes)
- DELLA drops lower-magnitude parameters preferentially (slightly smarter throwing away)

**For maritime knowledge retention, this is destructive:**

Consider a concrete example. The engineering specialist LoRA has learned:
- "Main engine cylinder liner cooling water temperature should be maintained at 80-85°C"

The safety specialist LoRA has learned:
- "CO₂ total flooding system requires a minimum of 35% concentration for engine room protection"

When you merge via DARE (dropping 90% of deltas), there is a substantial probability that some of the precise numerical knowledge encoded in each specialist is randomly eliminated. The model won't forget the TOPIC, but it may lose the exact numbers — exactly the kind of knowledge that matters most for maritime safety.

**DARE's key finding undermines the approach at small scale:**
> "This phenomenon [90-99% delta parameter redundancy] is more pronounced in large-scale LMs"

At 7B+, delta parameters have enormous redundancy. At 1-3B, models have far fewer parameters, so each delta parameter carries more unique information. Dropping 90% at 1-3B is more destructive than at 7B+.

**Published evidence for knowledge retention through merging:**
- Model Soups (ICML 2022): Averaging hyperparameter variations of the SAME task → improves accuracy. This is NOT multi-domain knowledge composition.
- DARE (ICML 2024): Most impressive results on 7B (LLaMA-7B, Mistral-7B). Limited evidence at <3B.
- SmolLM3: Merging recovered long-context performance but required accepting 10% dilution of domain strength.

**SCORE: 4/10** — Merging inherently loses information. At 1-3B, limited capacity means less redundancy, so more knowledge is destroyed. The technique was designed for capability composition, not factual knowledge preservation.

---

### 2. INFERENCE COST — Score: 10/10

**After merging, the result is a single standard model.** No additional components, no routing, no retrieval, no ensemble.

| Aspect | Status |
|--------|--------|
| Model size | Identical to base (3B → 3B) |
| RAM usage | Same as unmerged model |
| Inference latency | Same as unmerged model |
| Extra components | None |
| Quantization | Standard GGUF pipeline works |

This is THE primary advantage of model merging over alternatives like Mixture of Experts (which routes to specialists at inference time) or ensembles (which run multiple models).

After merging + quantization:
- 3B Q4_K_M: ~1.8 GB RAM
- 10-30 tokens/sec on modern ARM CPUs

**SCORE: 10/10** — Perfect. The entire point of merging is to get multi-model quality in a single-model package.

---

### 3. TRAINING COST — Score: 7/10

**Two cost components:**

**A. Training specialist models (multiplicative cost):**

For the 4-specialist approach:

| Specialist | Training Data | LoRA Training (RTX 4090) | Full SFT (A100) |
|-----------|--------------|-------------------------|-----------------|
| Engineering LoRA | 25% of maritime data | 1-2 hours, $3-5 | 3-6 hours, $8-15 |
| Navigation LoRA | 25% of maritime data | 1-2 hours, $3-5 | 3-6 hours, $8-15 |
| Safety LoRA | 25% of maritime data | 1-2 hours, $3-5 | 3-6 hours, $8-15 |
| Regulations LoRA | 25% of maritime data | 1-2 hours, $3-5 | 3-6 hours, $8-15 |
| **Total** | | **4-8 hours, $12-20** | **12-24 hours, $32-60** |

For comparison, a single unified LoRA would cost $3-5 and take 1-2 hours.

**B. Merge step (essentially free):**

| Merge Method | Compute | Time | Cost |
|-------------|---------|------|------|
| Linear/SLERP | CPU only | 2-5 minutes | $0 |
| TIES/DARE/DELLA | CPU only | 5-10 minutes | $0 |
| Evolutionary (Sakana) | GPU for evaluation | Hours-days | $50-500+ |

The merge itself costs nothing (CPU, minutes). But evolutionary merging requires evaluating hundreds of merge candidates on a benchmark, which needs GPU time.

**C. Search for optimal merge hyperparameters:**

Each merge method has hyperparameters (density for TIES/DARE, weight per model, interpolation factor for SLERP). Finding optimal values requires:
- Merging with different settings (CPU, minutes each)
- Evaluating each merged model on a maritime benchmark (GPU, minutes each)
- 20-50 experiments: ~$10-50

**Total realistic cost:**

| Approach | Training | Merge | Search | Total |
|----------|----------|-------|--------|-------|
| 4 LoRA specialists + DARE-TIES | $12-20 | $0 | $10-50 | $22-70 |
| 4 Full SFT specialists + DARE-TIES | $32-60 | $0 | $10-50 | $42-110 |
| Single model + Evolutionary merge | $5-15 | $50-500 | included | $55-515 |

Compare to: Single unified LoRA training = $3-5. Single unified full SFT = $8-15.

**3-10x more expensive than the simple approach, but still very cheap in absolute terms.**

**SCORE: 7/10** — Multiplicative training cost for multiple specialists, but the merge step is free. Evolutionary merging can get expensive. Overall still affordable <$100 for the standard pipeline.

---

### 4. DATA EFFICIENCY — Score: 5/10

**The central problem: splitting data into specialist domains reduces data-per-specialist.**

If you have 50K maritime Q&A pairs total:
- Single model sees all 50K
- 4 specialists each see ~12.5K

SFT quality is highly sensitive to dataset size and diversity. Per DEITA (arXiv:2312.15685), 6K high-quality samples can match 60K generic ones — but splitting already-curated data into quarters doesn't help.

**Domain overlap causes problems:**

Maritime knowledge doesn't split cleanly into 4 buckets:
- "What's the procedure for testing CO₂ fire suppression?" → Safety? Engineering? Regulations? ALL THREE.
- "How does ballast water treatment affect stability?" → Navigation? Engineering? Environmental regulations?
- "What's the minimum crew for a 50,000 GT tanker under STCW?" → Regulations? Safety? Navigation?

You either:
1. Duplicate cross-domain examples across specialists (wastes data budget)
2. Force-assign to one domain (specialist misses relevant context)
3. Don't split at all (defeats the purpose of specialist merging)

**Data efficiency AT THE MERGE STEP:**

Merging itself is data-efficient — it requires no additional training data, only a benchmark for evaluation. This is a genuine advantage if you already have separately-trained models.

**However:** The DARE paper showed that SFT delta parameters have high redundancy, meaning most of what SFT learns is redundant. If 90-99% of delta parameters are droppable, it means SFT is a highly inefficient encoding of knowledge. Merging doesn't fix this — it just combines the remaining 1-10% of meaningful parameters.

**SCORE: 5/10** — Splitting data reduces per-specialist data efficiency. Cross-domain overlap in maritime makes clean splits impossible. The merge step itself is data-free, but the upstream training is less efficient than a unified approach.

---

### 5. ACCURACY ON DOMAIN QA — Score: 4/10

**The critical question for a maritime chatbot: will the merged model give correct, specific answers?**

**What the evidence tells us:**

**Model merging DEGRADES individual specialist accuracy.** This is the fundamental trade-off — you get breadth at the cost of depth.

From the TIES paper:
> "Existing merging techniques inadvertently lose valuable information due to two major sources of interference"

TIES/DARE/DELLA reduce this loss but don't eliminate it. In their own benchmarks:

| Method | Avg. Performance on Individual Tasks |
|--------|-------------------------------------|
| Individual specialist | 100% (baseline) |
| Simple average merge | ~85-90% of individual |
| TIES merge | ~90-95% of individual |
| DARE-TIES merge | ~92-96% of individual |
| DELLA merge | ~94-97% of individual |

Even with the best methods, you lose 3-8% accuracy on each specialist's domain. For maritime QA where exact procedures and numbers matter, this 3-8% degradation falls exactly on the hardest-to-retain information: specific numbers, exact sequences, precise regulation references.

**The "Goldfish Memory" problem with merged LoRAs:**

When you train a LoRA on engineering questions, the adapter learns weight adjustments of very small magnitude (within ±0.002 per DARE findings). These tiny adjustments encode the specialist knowledge. Now you:
1. Apply DARE to randomly drop 90% of these already-tiny adjustments
2. Average the remaining 10% with adjustments from 3 other specialists
3. The resulting merged delta is a diluted, partially-randomized version of each specialist

**Maritime accuracy test cases:**

| Question | Individual Specialist | After DARE-TIES Merge |
|----------|----------------------|----------------------|
| "What are the six annexes of MARPOL?" | High (directly trained) | Good (conceptual, robust to merge) |
| "Minimum CO₂ concentration for engine room fire suppression?" | Medium-High (specific number: 35%) | Medium — exact number at risk of corruption |
| "Step-by-step procedure for testing fixed CO₂ system per FSS Code?" | Medium (long procedural sequence) | Low-Medium — procedural ordering easily disrupted by parameter interference |
| "Calculate the metacentric height given displacement of 10,000 tonnes..." | Varies (depends on training) | Degraded — numerical reasoning parameters especially sensitive to merging |

**The SmolLM3 precedent does NOT validate this approach for domain knowledge:**

SmolLM3 used merging to mix an APO-aligned model (0.9 weight) with a mid-training checkpoint (0.1 weight) to recover lost RULER benchmark performance. They were NOT merging domain specialists. The merge was essentially: "take 90% of our best model, add 10% of an earlier version that was better at long-context." This is model interpolation for capability recovery, not multi-specialist knowledge composition.

**What WOULD improve accuracy:** Training a single comprehensive maritime model (one LoRA or full SFT) on ALL maritime data, rather than splitting into specialists and merging.

**SCORE: 4/10** — Merging inherently degrades specialist accuracy by 3-8% even with best methods. For maritime QA requiring exact numbers and procedures, this degradation targets the most critical information. No published evidence of domain QA accuracy improvement through specialist merging at <3B scale.

---

### 6. MOBILE DEPLOYABILITY — Score: 10/10

**Identical to an unmerged model.** The merge happens BEFORE deployment; the deployed artifact is a single standard model.

| Deployment Spec | Status |
|----------------|--------|
| Single GGUF file | ✅ Yes |
| Standard llama.cpp inference | ✅ Yes |
| Model size after merge | Same as base (3B) |
| Quantization compatible | ✅ All formats |
| mlc-llm / MNN / executorch | ✅ All work |
| No runtime merging needed | ✅ Pre-computed |

```
3B model → DARE-TIES merge (offline, CPU, 5 min) → Q4_K_M GGUF → ~1.8GB → Phone
```

The merged model is indistinguishable from a normally fine-tuned model for deployment purposes.

**SCORE: 10/10** — Perfect. Merging is an offline pre-processing step. The deployed model is standard.

---

### 7. ROBUSTNESS — Score: 7/10

**This is a genuine strength of model merging.**

The Model Soups paper (ICML 2022) demonstrated that weight averaging:
- Improves out-of-distribution (OOD) robustness
- Reduces sensitivity to hyperparameter choices
- Acts as implicit regularization

LM-Cocktail showed that merging a fine-tuned model back with the base model provides:
- Resilience on general tasks beyond the target domain
- Graceful degradation rather than catastrophic failures

**For maritime chatbot:**

If the user asks something outside the training distribution — e.g., a question about a very new regulation not in training data, or an unusual phrasing — a merged model is likely to give a more reasonable response than a single specialist that overfits to its training distribution.

The merged model averages the "opinions" of multiple specialists, which acts like an implicit ensemble for robustness:
- The engineering specialist might have learned something about an equipment failure mode
- The safety specialist might have learned the SOLAS response procedure
- The regulations specialist might have learned the reporting requirements
- The merged model combines these partial perspectives

**Caveat:** This robustness is to input variation and distribution shift, NOT factual accuracy. The merged model may be more consistently mediocre rather than occasionally excellent and occasionally terrible.

**SCORE: 7/10** — Genuine improvement in robustness and OOD performance through weight averaging. Model soups and LM-Cocktail both validate this. But robustness ≠ accuracy.

---

### 8. CATASTROPHIC FORGETTING — Score: 7/10

**This is the second genuine strength of model merging — and arguably the primary reason SmolLM3 used it.**

SmolLM3's specific problem:
> "While downstream evaluations showed improvements across mathematics, science, instruction following, coding, chat, and multilingual tasks, we observed performance degradation on long context benchmarks like RULER."

**Solution:** Merge APO model (0.9) with mid-training checkpoint that had strong long-context (0.1). Result: recovered RULER performance while maintaining alignment gains.

**For maritime chatbot, the analogous benefit:**

When you fine-tune for maritime domain, the model loses general capabilities (formatting, conversational ability, general-world knowledge). Merging the maritime model back with the base model (e.g., 0.85 maritime + 0.15 base) preserves:
- Conversational fluency
- Instruction-following quality
- General knowledge context
- Format/style capabilities

LM-Cocktail explicitly validated this: "the resulted model is able to achieve a strong empirical performance in the whole scope of general tasks while preserving a superior capacity in its targeted domain."

**The trade-off:**

| Merge Ratio (domain:base) | Domain Accuracy | General Capability |
|---------------------------|----------------|-------------------|
| 1.0 : 0.0 (no base) | Best for domain | Worst for general |
| 0.9 : 0.1 | -3% domain | +30% general |
| 0.8 : 0.2 | -7% domain | +50% general |
| 0.7 : 0.3 | -12% domain | +65% general |

For our chatbot, something like 0.85-0.90 domain weight is the sweet spot per SmolLM3's experience.

**Why not perfect (10/10):**
- You're trading domain accuracy for general capability recovery — there's always a cost
- If domain knowledge is already weak (LoRA-only), you can't afford to dilute further
- Catastrophic forgetting prevention works best when domain knowledge is deeply encoded (via CPT), not superficially (via SFT)

**SCORE: 7/10** — Merging with base model is a proven technique for recovering lost general capabilities. SmolLM3 validates this at 3B scale. But it trades domain accuracy for general capability, which is suboptimal when domain knowledge is already limited.

---

### 9. MAINTENANCE — Score: 6/10

**Model merging adds pipeline complexity:**

```
Simple Pipeline (no merging):
  Data → Train model → Quantize → Deploy

Merging Pipeline:
  Data → Split by domain → Train 4 specialists → Choose merge method → 
  Tune merge hyperparams → Merge → Evaluate → Maybe re-tune → Quantize → Deploy
```

**Update scenarios:**

| Update Type | Without Merging | With Merging |
|------------|----------------|-------------|
| New MARPOL regulation | Retrain single model | Retrain regulations specialist, re-merge, re-evaluate |
| Fix wrong procedure | Fix training data, retrain | Fix in correct specialist, re-merge, re-evaluate |
| Add new topic area | Expand training data | Create new specialist OR expand existing, re-merge |
| Improve conversation quality | Adjust SFT data | Which specialist? Or all 4? Re-merge all. |

**Tools and ecosystem:**

MergeKit is mature and well-maintained:
- Simple YAML configuration
- CPU-only execution
- Supports all major merge methods
- Active community
- SmolLM3 used it in production

However:
- No automated "optimal merge finder" (except expensive evolutionary approach)
- Results are hard to predict without evaluation
- Debugging merged model failures requires isolating which specialist caused the issue
- Version control becomes more complex (4 specialist checkpoints + merge config + merged model)

**SCORE: 6/10** — Adds pipeline complexity. 4 specialists to manage instead of 1 model. Updates require re-merging and re-evaluation. MergeKit tooling is mature. Debugging merged model issues is harder.

---

### 10. PROVEN AT SMALL SCALE — Score: 4/10

**This is the weakest aspect. Most model merging success stories are at 7B+ scale.**

**Evidence at scale 7B+:**
- Open LLM Leaderboard: dominated by merged models (all 7B+)
- DARE: Primary experiments on LLaMA-7B, Mistral-7B, LLaMA-13B
- TIES: Primary experiments on T5-base (220M) through T5-XL (3B) for NLP, but mainly vision transformers otherwise
- Evolutionary Merging (Sakana): Experiments on 7B Japanese LLMs
- Model Soups: CLIP ViT-B/32 through ViT-G, mostly vision

**Evidence at ≤3B:**
- SmolLM3 (3B): Used merging, but only for capability recovery (long-context), not multi-specialist composition
- TIES original paper: Some experiments with T5-base/large, but as classification fine-tuning, not LLM knowledge injection
- No published work on merging domain-specialist LLMs at 1-3B scale

**The DARE paper's critical admission:**
> "This phenomenon [delta parameter redundancy] is more pronounced in large-scale LMs"

This directly implies that at small scale:
- Delta parameters carry MORE unique information
- Dropping 90% is more destructive
- Models have less "slack" to absorb merge interference

**The capacity argument:**

A 3B model has ~3 billion parameters. If you fine-tune 4 specialists and each learns ~50M unique delta parameters, you're trying to fit 200M delta parameters into one 3B model. At 7B, you have more "room" for this composition. At 1.5B, you have substantially less.

Furthermore, LoRA adapters at rank 64 add only ~50-100M parameters. Merging 4 of these into a 3B base means you're adjusting ~0.5-1.3% of all parameters per specialist. The parameter modifications from different specialists will inevitably step on each other more at small scale.

**The leaderboard evidence is misleading:**

The top merged models on the Open LLM Leaderboard are contaminated (trained on benchmark test sets). As mlabonne's guide acknowledges:
> "It is safe to assume that Marcoro14-7B-slerp is contaminated and some models used in this merge have been trained on the test set."

This means the impressive leaderboard scores from merged models DON'T necessarily indicate genuine knowledge composition — they may just indicate averaging of multiple contaminated models.

**SCORE: 4/10** — Almost all evidence is at 7B+. DARE explicitly says the technique works better at larger scale. SmolLM3 used merging at 3B but only for capability recovery, not domain specialist composition. No published evidence of multi-specialist domain merging working well at 1-3B for factual QA.

---

## SCORING SUMMARY

| # | Criterion | Score | Rationale |
|---|-----------|-------|-----------|
| 1 | Knowledge Retention | 4/10 | Merging doesn't inject knowledge and inherently loses information through trimming/dropping/interference |
| 2 | Inference Cost | 10/10 | Single model after merge — identical to unmerged baseline |
| 3 | Training Cost | 7/10 | Multiplicative (train N specialists), but merge step is free; still cheap overall |
| 4 | Data Efficiency | 5/10 | Splitting data into domains reduces per-specialist data; maritime domains overlap heavily |
| 5 | Accuracy on Domain QA | 4/10 | Merging degrades specialist accuracy 3-8%; exact numbers/procedures most affected |
| 6 | Mobile Deployability | 10/10 | Single standard model after offline merge — perfect mobile deployment |
| 7 | Robustness | 7/10 | Weight averaging genuinely improves OOD robustness (Model Soups, LM-Cocktail) |
| 8 | Catastrophic Forgetting | 7/10 | Merging with base model recovers general capabilities — validated by SmolLM3 at 3B |
| 9 | Maintenance | 6/10 | More complex pipeline; 4 specialists + merge config; debugging harder |
| 10 | Proven at Small Scale | 4/10 | DARE says technique works better at larger scale; limited ≤3B evidence |

## **TOTAL SCORE: 64/100**

---

## KEY STRENGTHS (3)

### 1. Zero Runtime Overhead — Perfect for Mobile
Model merging happens entirely offline. The deployed artifact is a single standard model that is indistinguishable from any other fine-tuned model. No routing, no ensemble, no retrieval. This makes it perfectly compatible with mobile deployment constraints (ARM CPU, limited RAM, single GGUF file). The SmolLM3 production pipeline validates this at 3B scale.

### 2. Catastrophic Forgetting Mitigation — The SmolLM3 Playbook
The strongest validated use case for model merging is recovering lost general capabilities after domain fine-tuning. SmolLM3's recipe (0.9 APO model + 0.1 mid-training checkpoint → recovered RULER performance) is a proven production technique. For a maritime chatbot, merging the domain-trained model with the base model (0.85:0.15 ratio) preserves conversational fluency, instruction-following, and formatting quality that would otherwise degrade during domain training.

### 3. OOD Robustness Through Weight Averaging
Model Soups (ICML 2022) proved that averaging weights of multiple fine-tuned models consistently improves out-of-distribution performance with zero extra inference cost. For a maritime chatbot that must handle diverse question phrasings, edge cases, and novel queries, this implicit robustness is valuable. The merged model degrades gracefully rather than catastrophically on unfamiliar inputs.

---

## KEY WEAKNESSES (3)

### 1. Merging Cannot Inject Knowledge — It Only Combines (and Degrades) Existing Knowledge
This is the fatal flaw for the maritime chatbot use case where the requirement is "all knowledge in weights." Model merging is a post-hoc combination technique. It assumes the individual models already contain the needed knowledge. For maritime, the knowledge must be injected through pretraining or fine-tuning FIRST. Merging is downstream of — and inherently lossy compared to — the knowledge injection step. Every merge method (TIES, DARE, DELLA) works by trimming, dropping, or averaging delta parameters, all of which lose information. The 3-8% accuracy degradation from best-case merging falls directly on the precise numerical and procedural knowledge maritime QA demands.

### 2. Limited Evidence at Small Scale — DARE Explicitly Says It Works Better for Larger Models
The DARE paper's finding that "this phenomenon is more pronounced in large-scale LMs" is a direct warning. At 1-3B, models have less parameter redundancy. Each delta parameter carries more unique information. Dropping 90% of deltas (DARE's standard operating procedure) is more destructive at small scale. Almost all successful model merging examples in the community are 7B+ models. SmolLM3's use at 3B was conservative (simple linear merge with 0.9/0.1 ratio for capability recovery), not aggressive multi-specialist composition.

### 3. Maritime Domains Are Too Interconnected for Clean Specialist Splitting
The 4-specialist approach (engineering, navigation, safety, regulations) assumes these domains have clean boundaries. In maritime, they don't. A CO₂ fire suppression question spans engineering (system design), safety (SOLAS Chapter II-2), and regulations (FSS Code). Ballast water touches navigation (stability), engineering (treatment systems), and regulations (BWM Convention). Forcing artificial domain boundaries creates either data duplication (inefficient), missing context (each specialist lacks cross-domain linkages), or arbitrary assignments (specialist trained on wrong framing). A single unified model trained on all maritime data would handle these interconnections naturally.

---

## VERDICT

**Model merging is a useful FINISHING technique but a fundamentally wrong FOUNDATION for a maritime knowledge chatbot.**

The approach answers the wrong question. The hard problem for a maritime chatbot is: **"How do I get domain knowledge INTO the model?"** Model merging doesn't address this — it addresses: **"How do I combine capabilities from models that already have knowledge?"**

Model merging should be used as a **late-stage optimization step** in the pipeline, not as the primary strategy. Specifically:

**APPROPRIATE uses of model merging for this project:**
1. ✅ Merge domain-trained model with base model (0.85:0.15) to recover conversational fluency
2. ✅ Average multiple training runs ("model soup") to improve robustness
3. ✅ Merge a checkpoint with better domain knowledge with a checkpoint that has better alignment

**INAPPROPRIATE uses of model merging for this project:**
1. ❌ Splitting maritime data into 4 specialist LoRAs and merging them (loses cross-domain connections, reduces per-specialist data, degrades specialist accuracy)
2. ❌ Using merging as the primary knowledge injection strategy (it doesn't inject knowledge)
3. ❌ Expecting DARE/TIES to work as well at 1-3B as at 7B+ (published evidence says otherwise)

---

## BEST COMBINATION: Where Model Merging Fits in the Optimal Pipeline

```
PHASE 1 — KNOWLEDGE INJECTION (the hard part merging can't do):
  ┌──────────────────────────────────────────────────────────┐
  │ Continued Pretraining on maritime textbook prose          │
  │ • Clean text from MARPOL, SOLAS, STCW, Reeds Vol. 5      │
  │ • Continue-pretrain SmolLM3-3B-Base                       │
  │ • 80% domain + 20% general data replay                   │
  │ • 2-5 days on 1-2x A100 ($500-2,000)                     │
  │ → Deep parametric knowledge encoded in weights            │
  └──────────────────────────────────────────────────────────┘
                              ↓
PHASE 2 — INSTRUCTION TUNING:
  ┌──────────────────────────────────────────────────────────┐
  │ Synthetic Q&A generation + Full SFT (NOT LoRA)            │
  │ • Teacher model generates Q&A from textbooks              │
  │ • Include reasoning traces (Orca 2 style)                 │
  │ • Single unified maritime SFT (no specialist splitting)   │
  │ • 80% domain + 20% general instruction data               │
  │ → Model learns to USE its knowledge in Q&A format         │
  └──────────────────────────────────────────────────────────┘
                              ↓
PHASE 3 — ALIGNMENT:
  ┌──────────────────────────────────────────────────────────┐
  │ DPO/APO preference alignment                              │
  │ • Correct vs. incorrect maritime answers                   │
  │ • Safety-aware alignment (admit uncertainty for safety)    │
  │ → Model prefers accurate over plausible-sounding answers   │
  └──────────────────────────────────────────────────────────┘
                              ↓
✅ PHASE 4 — MODEL MERGING AS FINISHING (the RIGHT use):
  ┌──────────────────────────────────────────────────────────┐
  │ Step 4a: Model Soup of top-3 SFT/APO checkpoints          │
  │   • Average weights of best checkpoints from training      │
  │   • Improves robustness (Model Soups, ICML 2022)           │
  │                                                            │
  │ Step 4b: Linear merge with earlier checkpoint              │
  │   • 0.90 soup + 0.10 pre-SFT checkpoint                   │
  │   • Recovers any general capabilities lost during SFT      │
  │   • Following SmolLM3's exact recipe                       │
  │                                                            │
  │ Cost: $0 (CPU, 5-10 minutes, mergekit)                     │
  │ → More robust model with preserved general capabilities    │
  └──────────────────────────────────────────────────────────┘
                              ↓
PHASE 5 — QUANTIZE + DEPLOY:
  ┌──────────────────────────────────────────────────────────┐
  │ Q4_K_M GGUF → ~1.8GB → llama.cpp on phone                │
  └──────────────────────────────────────────────────────────┘
```

### Why This Placement Works:

| Phase | What It Provides | What Model Merging Adds |
|-------|-----------------|------------------------|
| CPT | Deep knowledge in weights | Nothing — merging can't do this |
| SFT | Q&A format capability | Nothing — merging can't do this |
| DPO/APO | Preference alignment | Nothing — merging can't do this |
| **Merging** | — | **Robustness + forgetting recovery** |
| Quantization | Mobile deployment | Nothing — merging doesn't help here |

**Model merging adds ~5-10% robustness improvement and recovers 80-90% of lost general capabilities, at ZERO additional cost (CPU-only, minutes).** As a finishing step, it's an excellent and free optimization. As a foundation, it fundamentally fails.

---

## COMPARISON: Merging-Centric vs. Merging-as-Finishing

| Criterion | Merging as Primary (evaluated) | Merging as Phase 4 (recommended) |
|-----------|-------------------------------|----------------------------------|
| Knowledge Retention | 4 | 8 (CPT does the heavy lifting) |
| Inference Cost | 10 | 10 |
| Training Cost | 7 | 6 (CPT adds $500-2,000) |
| Data Efficiency | 5 | 8 (unified training, no splitting) |
| Accuracy on Domain QA | 4 | 7-8 (CPT+SFT provides accuracy; merge refines) |
| Mobile Deployability | 10 | 10 |
| Robustness | 7 | 8 (merge adds robustness to already-strong model) |
| Catastrophic Forgetting | 7 | 8 (merge recovers, CPT+replay prevents) |
| Maintenance | 6 | 7 (simpler pipeline with merge as optional step) |
| Proven at Small Scale | 4 | 8 (CPT+SFT proven; merge is conservative) |
| **TOTAL** | **64** | **80-81** |

---

## FINAL ASSESSMENT

### One-Line Summary:
**Model merging is an excellent free garnish on an already well-prepared dish — but you cannot make a meal out of garnish alone.**

### For the Maritime Chatbot Project:
- **DO use model merging** — but as Phase 4 (finishing), not as the primary strategy
- **DO use model soup** of your best training checkpoints — it's free and proven to improve robustness
- **DO use linear merge** with a pre-SFT checkpoint (SmolLM3 recipe) to recover general capabilities
- **DO NOT split maritime data** into 4 specialist LoRAs for merging — maritime domains are too interconnected
- **DO NOT rely on DARE-TIES** for multi-specialist knowledge composition at 1-3B — evidence says it works better at larger scale
- **DO NOT confuse merging** with knowledge injection — they solve completely different problems
- **Use MergeKit** — it's the standard tool, SmolLM3 used it in production, and it's mature

### The Harsh Truth:
If a crew member asks "What's the minimum CO₂ concentration required for total flooding of the engine room per FSS Code?", a model built primarily through specialist merging will give a less accurate answer than a single model trained on all maritime data via continued pretraining + SFT. Merging introduces interference that specifically corrupts precise numerical knowledge — exactly the kind of knowledge maritime safety demands. Use merging to polish the presentation, not to build the foundation.

---

*This evaluation is based on published research from NeurIPS 2023 (TIES-Merging), ICML 2024 (DARE), ICLR 2023 (Task Arithmetic), ICML 2022 (Model Soups), Nature Machine Intelligence 2025 (Evolutionary Merging), HuggingFace (SmolLM3 production pipeline, MergeKit), and the LM-Cocktail and DELLA literature. All scores reflect the approach's effectiveness when used as the PRIMARY strategy for domain knowledge injection at the 1-3B scale for a mobile maritime chatbot with no RAG.*
