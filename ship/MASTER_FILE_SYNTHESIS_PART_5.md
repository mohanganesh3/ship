# MASTER SYNTHESIS: PART 5
**DOCUMENT TITLE:** Strategic Innovations & Final Action Plan
**SOURCE:** Extrapolated directly from the corpus.

## 1. STRATEGIC EDGE INNOVATIONS (THE "SECRET SAUCE")
Deploying AI onboard ships without internet presents highly specific constraints that conventional Silicon Valley scaling logic ignores. The corpus validates specific technical workarounds:

**A. The "Knowledge vs Reasoning" Schism:**
- You cannot fix a lack of knowledge via reasoning (Test-time compute). 
- If the model doesn't mathematically know that a 2-stroke diesel engine operates differently than a 4-stroke, no amount of CoT prompting will materialize that fact.
- CPT (Continued Pretraining) is heavily enforced to patch knowledge gaps, while TTC is strictly a framework layer designed specifically to improve the *application* of math. 

**B. Bypassing RAG Hardware Bottlenecks:**
- Traditional RAG architectures rely fundamentally on heavy vector database embeddings and memory-bound context recall. 
- The system substitutes RAG with profound CPT training passes. All facts are baked into the core weights. The model functions as a monolithic encyclopedia.

**C. Battery-Conscious Inference:**
- The deployment limits token generation dynamically based on query structures to solve battery thermal throttling. (Applying TTC exclusively to logic queries).

## 2. FINAL ACTION PLAN AND TIMELINE BLUEPRINT
The synthesized deployment track is clear:

### Step 1: Data Accumulation and Cleansing
1. Build aggressive web scrapers / PDF OCR pipelines (Marker/PDF2Text) for strictly maritime domain sources.
2. Filter through explicit legal data (STCW, MARPOL, SOLAS) using automated heuristics.
3. Establish a baseline of 500M high-quality unstructured markdown tokens.

### Step 2: CPT (Continued Pretraining)
1. Initialize **Qwen3-1.7B-Base**.
2. Run QLoRA via Unsloth on a single cloud GPU (e.g., H100 or A100) using the 80/20 domain/replay mix.
3. Validate perplexity scores specifically on maritime text to confirm knowledge injection success without catastrophic forgetting.

### Step 3: SFT and Synthetic QA Generation
1. Use a **local teacher** (running on the 4‑GPU machine) to generate thousands of complex diagnostic synthetic scenarios strictly constrained to the CPT data corpus.
2. Apply DEITA complexity filters to isolate the top 10% highest quality responses.
3. Merge SFT via ORPO, reinforcing safety alignment simultaneously.

### Step 4: Quantization, Packaging, and Local Deployment
1. Export the finalized model to `.GGUF` at **Q4_K_M** logic.
2. Embed into `llamafile` for a single-click cross-platform executable wrapper.
3. Hardcode dynamic routing system prompts into Open WebUI/KoboldCpp customized offline frontends. 
4. Deploy entirely isolated via thumb-drives directly to vessel computing stacks.

---
**SYNTHESIS DEPLOYMENT SUMMARY: COMPLETE.** 
*(B1-B9 Mappings across all 22 components verified and finalized).*