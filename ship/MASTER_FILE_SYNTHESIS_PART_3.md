# MASTER SYNTHESIS: PART 3
**DOCUMENT TITLE:** Architecture, Constraints, & Model Selection
**SOURCE:** Derived purely from the B1-B9 taxonomies in the 22 extracted evaluation files.

## 1. PROJECT OBJECTIVES AND HARDWARE CONSTRAINTS
The primary objective is to engineer a localized, entirely offline maritime AI chatbot embedded on mobile edge devices running on ARM CPUs with strictly 3-6 GB RAM limits. 

**Absolute Limitations:**
- **No Cloud/Internet:** Devices operate at sea where satellite internet is prohibitively expensive or nonexistent. The entire knowledge base must be encapsulated directly within the model's weights. RAG is severely deprioritized due to device capability variants, although some theoretical pipeline discussions evaluate SQLite/ChromaDB as fallback mechanisms. 
- **Inference Hardware:** The system lacks dedicated GPUs. Decoding is routed exclusively over local CPU architecture.
- **Memory Ceiling:** The combined OS, KV cache, and loaded model binary must not exceed the strict 3-6 GB ecosystem, limiting absolute model dimensions to the 1B–3B parameter band.

## 2. BASE MODEL SELECTION
Through exhaustive cross-examination, large 7B+ cloud counterparts are structurally incompatible. The candidate field restricts tightly around 1-3B sizes:

**Winner: Qwen3-1.7B**
- Best overall ratio of logic retention to size.
- Pre-equipped with dual "thinking/non-thinking" parameter pathways.
- With Q4_K_M quantization (GGUF via Unsloth exporter), it compacts to less than ~1.5 GB.

**CPU-Centric Alternative: LFM2-1.2B**
- Employs a hybrid convolution and grouped query attention (GQA) architecture replacing pure transformers.
- Decodes nearly 2x faster specifically on CPUs compared to equivalent standard algorithms.

**Other Evaluated Baselines:**
- **Granite 3.3 2B:** Features high math/coding functionality but heavier quantization loads.
- **SmolLM2-1.7B:** Extremely high-quality synthetic SFT basis, but lacks Qwen3's built-in reasoning routing logic.
- **Phi-1.5 / Phi-4-Mini:** Math-heavy but suffers from factual hallucinations known as the "Phi-1 Misattribution Trap."

## 3. ARCHITECTURE VECTORS
**Edge Inference Engine:**
- `llama.cpp` (and sub-wrapper `Ollama`) represents the deployment core purely due to its zero-dependency C++ compilation, maximizing token generation on localized ARM sets.
- `llamafile` / `KoboldCpp` act as self-contained executable deployment structures providing maximum simplicity (zero installation for crew interfaces).

**Quantization Directives:**
- All deployments enforce a **Q4_K_M** (4-bit normal float) mapping structure.
- Going further down to 2-bit or Extreme Quantization degrades factual knowledge extraction heavily, causing unacceptable safety-critical hallucination overlaps.
- GGUF formatting handles matrix calculation overhead seamlessly across platforms.