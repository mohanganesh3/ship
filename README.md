<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0a192f,50:0d47a1,100:1565c0&height=220&section=header&text=Maritime%20AI&fontSize=72&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Shipboard%20Intelligence%20Engine&descSize=22&descColor=90caf9&descAlignY=55" width="100%"/>
</p>

<h3 align="center">
  A 1.7 billion parameter language model, purpose-built for life-safety maritime operations.<br/>
  Runs entirely offline on mobile devices. No cloud dependency. No RAG. No compromise.
</h3>

<p align="center">
  <a href="https://github.com/mohanganesh3/Maritime-AI/releases/download/v1.0.0/Maritime.apk"><strong>Download APK</strong></a> &nbsp;&middot;&nbsp;
  <a href="https://huggingface.co/mohanganesh3/maritime_model_v1"><strong>Model on HuggingFace</strong></a> &nbsp;&middot;&nbsp;
  <a href="#system-architecture"><strong>Architecture</strong></a> &nbsp;&middot;&nbsp;
  <a href="#the-6-phase-training-pipeline"><strong>Training Pipeline</strong></a> &nbsp;&middot;&nbsp;
  <a href="#mobile-application--react-native-edge-ai"><strong>Mobile App</strong></a>
</p>

<br/>

<table align="center">
<tr>
<td align="center"><b>Base Model</b></td>
<td align="center"><b>Format</b></td>
<td align="center"><b>Training Corpus</b></td>
<td align="center"><b>Data Sources</b></td>
<td align="center"><b>Pipeline</b></td>
<td align="center"><b>Compute</b></td>
</tr>
<tr>
<td align="center">Qwen3-1.7B</td>
<td align="center">GGUF Q4_K_M · 1.03 GB</td>
<td align="center">72M tokens + 500K QA pairs</td>
<td align="center">43 maritime sources</td>
<td align="center">6-phase CPT → ORPO</td>
<td align="center">Tesla K80 × 4</td>
</tr>
</table>

<br/>

---

## The Problem

A Chief Engineer is alone in the engine room at 0300 hours. Something is wrong with the auxiliary boiler. There is no internet. Shore support is 12 hours away. The closest manual is four decks up and 800 pages long.

In that moment, a wrong answer about crankcase entry procedure causes an explosion. A wrong answer about enclosed space oxygen levels causes a fatality. A wrong answer about MARPOL Annex I discharge limits causes an environmental disaster and a port detention.

This project exists because that scenario is real, and it happens every day on vessels around the world.

**Maritime AI is not a chatbot.** It is a domain-specific language model that was scraped from 43 authoritative maritime sources, distilled through a 235B-parameter teacher, trained across 6 research-grounded phases, and compressed into a 1 GB file that runs on a phone with no connectivity.

Every architectural decision traces to a published paper. Every quality gate has a mathematical threshold. The training data was collected under the same standard that classification societies use to certify vessels.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        MARITIME AI — COMPLETE SYSTEM ARCHITECTURE               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────────────── DATA COLLECTION LAYER ────────────────────────┐     │
│   │                                                                       │     │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │     │
│   │  │   IMO   │ │  SOLAS  │ │ MARPOL  │ │  STCW   │ │  IMDG   │       │     │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │     │
│   │       │            │           │            │           │             │     │
│   │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐       │     │
│   │  │  MAIB   │ │  EMSA   │ │  NTSB   │ │  DNV    │ │  Gard   │       │     │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │     │
│   │       │            │           │            │           │             │     │
│   │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐       │     │
│   │  │ClassNK  │ │ Lloyd's │ │  ABS    │ │ BIMCO   │ │ P&I Clubs│      │     │
│   │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘       │     │
│   │       └──────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘            │     │
│   │              ▼           ▼           ▼           ▼                   │     │
│   │         43 Custom Scrapers → PDF Extractors → Quality Filters       │     │
│   │                              │                                       │     │
│   │                    ┌─────────▼─────────┐                            │     │
│   │                    │  115,783 Chunks    │                            │     │
│   │                    │  (~72M Tokens)     │                            │     │
│   │                    │  Gold Standard     │                            │     │
│   │                    └─────────┬─────────┘                            │     │
│   └──────────────────────────────┼───────────────────────────────────────┘     │
│                                  │                                              │
│   ┌──────────────────────────────▼───────────────────────────────────────┐     │
│   │                    TEACHER DISTILLATION LAYER                        │     │
│   │                                                                       │     │
│   │  ┌───────────────────────────────────────────────────────┐           │     │
│   │  │          Qwen3-235B-A22B (142GB, Q4_K_M)              │           │     │
│   │  │          "The Teacher" — 4× llama-server instances    │           │     │
│   │  └───────────────────────┬───────────────────────────────┘           │     │
│   │                          │                                            │     │
│   │          ┌───────────────┼───────────────┐                           │     │
│   │          ▼               ▼               ▼                           │     │
│   │   ┌─────────────┐ ┌───────────┐ ┌──────────────┐                   │     │
│   │   │ 5 Question  │ │ IFD-Based │ │ MinHash      │                   │     │
│   │   │ Angles per  │ │ SuperFilter│ │ Deduplication│                   │     │
│   │   │ Chunk       │ │ (ACL 2024)│ │              │                   │     │
│   │   └──────┬──────┘ └─────┬─────┘ └──────┬───────┘                   │     │
│   │          └───────────────┼───────────────┘                           │     │
│   │                          ▼                                            │     │
│   │              ┌───────────────────────┐                               │     │
│   │              │   500K+ Q&A Pairs     │                               │     │
│   │              │   Gold Standard SFT   │                               │     │
│   │              └───────────┬───────────┘                               │     │
│   └──────────────────────────┼───────────────────────────────────────────┘     │
│                              │                                                  │
│   ┌──────────────────────────▼───────────────────────────────────────────┐     │
│   │                  6-PHASE TRAINING PIPELINE                           │     │
│   │                  (Tesla K80 × 4, fp16, QLoRA)                        │     │
│   │                                                                       │     │
│   │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐            │     │
│   │  │ Phase 1 │──▶│ Phase 2 │──▶│ Phase 3 │──▶│ Phase 4 │            │     │
│   │  │  CPT    │   │  SFT-1  │   │  SFT-2  │   │ Correct │            │     │
│   │  │ Domain  │   │ Reason  │   │ Direct  │   │ On-Pol  │            │     │
│   │  │ Adapt   │   │ /think  │   │/no_think│   │ icy     │            │     │
│   │  └─────────┘   └─────────┘   └─────────┘   └────┬────┘            │     │
│   │       │                                          │                  │     │
│   │       │  Gate: PPL↓15%  Gate: 70%     Gate: 60%  │                  │     │
│   │       │  Gen↑<10%       <think>       Trap Refuse│                  │     │
│   │       │                                          ▼                  │     │
│   │       │                                    ┌─────────┐             │     │
│   │       │                                    │ Phase 5 │             │     │
│   │       │                                    │  ORPO   │             │     │
│   │       │                                    │ β=0.1   │             │     │
│   │       │                                    └────┬────┘             │     │
│   │       │                                         │                   │     │
│   │       │                                         ▼                   │     │
│   │       │                                    ┌─────────┐             │     │
│   │       │                                    │ Phase 6 │             │     │
│   │       │                                    │Quantize │             │     │
│   │       │                                    │Q4_K_M   │             │     │
│   │       │                                    └────┬────┘             │     │
│   └───────┼─────────────────────────────────────────┼────────────────────┘     │
│           │                                         │                          │
│   ┌───────▼─────────────────────────────────────────▼────────────────────┐     │
│   │                      DEPLOYMENT LAYER                                │     │
│   │                                                                       │     │
│   │  ┌────────────────┐    ┌─────────────────────────────────────┐       │     │
│   │  │  HuggingFace   │    │     React Native Mobile App         │       │     │
│   │  │  Model Hub     │    │                                     │       │     │
│   │  │                │    │  ┌───────────┐  ┌────────────────┐  │       │     │
│   │  │ model.gguf     │───▶│  │ llama.rn  │  │ LLM Router     │  │       │     │
│   │  │ whisper-tiny   │    │  │ C++ mmap  │  │ Self-Classify  │  │       │     │
│   │  │ 1.03 GB        │    │  └─────┬─────┘  └───────┬────────┘  │       │     │
│   │  └────────────────┘    │        │                 │           │       │     │
│   │                        │        ▼                 ▼           │       │     │
│   │                        │  ┌─────────────────────────────┐    │       │     │
│   │                        │  │   Offline-First Inference    │    │       │     │
│   │                        │  │   • <think> / </think> mode  │    │       │     │
│   │                        │  │   • Context pruning          │    │       │     │
│   │                        │  │   • Safety alerts            │    │       │     │
│   │                        │  │   • FTS5 SQLite persistence  │    │       │     │
│   │                        │  │   • Whisper STT              │    │       │     │
│   │                        │  └─────────────────────────────┘    │       │     │
│   │                        └─────────────────────────────────────┘       │     │
│   └──────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Scale

| Metric | Value |
|--------|-------|
| **Total Python Files** | 198 (training, data pipeline, scrapers, generation) |
| **Total TypeScript/TSX Files** | 40 (React Native frontend) |
| **Custom Web Scrapers** | 43 sources (IMO, SOLAS, MAIB, DNV, ClassNK, Lloyd's, etc.) |
| **Raw Data Chunks** | 115,783 chunks (~72M tokens) |
| **Generated Q&A Pairs** | 500,000+ multi-angle distilled samples |
| **Training Phases** | 6 (CPT → SFT1 → SFT2 → Correction → ORPO → Quantize) |
| **Teacher Model** | Qwen3-235B-A22B (142GB, Q4_K_M) — 4 concurrent instances |
| **Student Model** | Qwen3-1.7B → fine-tuned → GGUF Q4_K_M (1.03 GB) |
| **Training Hardware** | 4× Tesla K80 (11GB each), 251GB RAM, 48 CPU threads |
| **Final Model Size** | 1.03 GB (Q4_K_M) / 1.17 GB (Q5_K_M) |
| **Frontend** | React Native + Expo + llama.rn + Whisper STT |
| **Deployment** | [HuggingFace Hub](https://huggingface.co/mohanganesh3/maritime_model_v1) |

---

## Repository Structure

```
ship/
├── training/                          # 🧠 Model Training Pipeline
│   ├── run_cpt_1.7b.py               #    Phase 1: Continued Pre-Training (946 lines)
│   ├── run_sft1_1.7b.py              #    Phase 2: SFT Stage 1 — Reasoning (/think)
│   ├── run_sft2_1.7b.py              #    Phase 3: SFT Stage 2 — Direct (/no_think)
│   ├── run_correction_1.7b.py        #    Phase 4: On-Policy Correction
│   ├── run_orpo_1.7b.py              #    Phase 5: ORPO Preference Alignment
│   ├── quantize_1.7b.py              #    Phase 6: GGUF Quantization
│   ├── phase2_optionc_common.py      #    Core reasoning & scoring engine (1,355 lines)
│   ├── run_cpt_4b.py                 #    4B model variant pipeline
│   ├── run_sft1_4b.py                #    4B SFT Stage 1
│   ├── run_sft2_4b.py                #    4B SFT Stage 2
│   ├── run_orpo_4b.py                #    4B ORPO
│   ├── quantize_4b.py                #    4B Quantization
│   ├── run_tapt_1.7b.py              #    Task-Adaptive Pre-Training
│   ├── build_local_benchmark_1p7b.py #    Benchmark construction
│   ├── build_local_corrections_1p7b.py#   Correction dataset builder
│   ├── build_local_orpo_pairs_1p7b.py #   ORPO pair generator
│   ├── audit_signatures.py           #    Model signature auditing
│   └── checkpoints/                  #    Saved model checkpoints
│
├── ship/maritime_pipeline/            # 📊 Data Engineering Battalion
│   ├── scrapers/                     #    43 custom web scrapers
│   │   ├── imo_scraper.py            #      International Maritime Organization
│   │   ├── maib_scraper.py           #      UK Marine Accident Investigation Branch
│   │   ├── emsa_scraper.py           #      European Maritime Safety Agency
│   │   ├── ntsb_scraper.py           #      US National Transportation Safety Board
│   │   ├── dnv_scraper.py            #      Det Norske Veritas classification society
│   │   ├── classnk_scraper.py        #      Nippon Kaiji Kyokai
│   │   ├── lloyds_register_scraper.py#      Lloyd's Register
│   │   ├── abs_scraper.py            #      American Bureau of Shipping
│   │   ├── bimco_scraper.py          #      Baltic & Intl Maritime Council
│   │   ├── gard_scraper.py           #      Gard P&I Club
│   │   ├── safety4sea_scraper.py     #      Safety4Sea portal
│   │   ├── marineinsight_scraper.py  #      Marine Insight
│   │   └── ... (43 total)            #      + 30 more specialized scrapers
│   ├── chunking/                     #    Intelligent document chunking
│   ├── extraction/                   #    PDF & HTML text extraction
│   │   └── pdf_extractor.py
│   ├── filtering/                    #    IFD-based quality filtering
│   │   └── quality_filter.py
│   ├── dedup/                        #    MinHash deduplication
│   │   └── minhash_dedup.py
│   ├── config.py                     #    Pipeline configuration
│   ├── db.py                         #    Pipeline progress database
│   └── data/final/                   #    Gold Standard outputs
│       ├── cpt_corpus.jsonl          #      34,988 records (~72M tokens)
│       ├── general_replay.jsonl      #      4,772 records (anti-forgetting)
│       ├── sft_curated.jsonl         #      Curated SFT training data
│       ├── sft_curated_traps.jsonl   #      Adversarial safety traps
│       ├── orpo_pairs_1.7b.jsonl     #      ORPO preference pairs
│       ├── eval_set.jsonl            #      Held-out evaluation set
│       ├── cpt_val_maritime.jsonl    #      1,288 validation records
│       └── cpt_val_general.jsonl     #      98 general validation records
│
├── scripts/                           # 🔧 Generation & Orchestration
│   ├── comprehensive_maritime_generator.py  # 500K multi-provider generation (854 lines)
│   ├── generate_wave1.py             #    Wave 1 teacher distillation
│   ├── filter_wave1.py               #    IFD-based SuperFiltering
│   ├── syllabus_generator.py         #    A-Z domain syllabus generator
│   ├── syllabus_plan.py              #    Master syllabus planning
│   ├── orchestrated_60k_generator.py #    60K batch orchestrator
│   ├── quality_audit.py              #    Automated quality auditing
│   ├── coverage_dashboard.py         #    Domain coverage tracking
│   └── validate_teacher.py           #    Teacher model validation
│
├── frontend/                          # 📱 React Native Mobile Application
│   ├── app/                          #    Expo Router pages
│   │   ├── (tabs)/index.tsx          #      Home screen — thread list
│   │   ├── (tabs)/new.tsx            #      New conversation
│   │   ├── (tabs)/settings.tsx       #      App settings
│   │   └── chat/[threadId].tsx       #      Chat conversation screen
│   ├── components/                   #    UI Components
│   │   ├── MessageBubble.tsx         #      Chat message rendering
│   │   ├── ThinkingBlock.tsx         #      <think> reasoning display
│   │   ├── ThinkingGlow.tsx          #      Animated thinking indicator
│   │   ├── InputTray.tsx             #      Message input with voice
│   │   ├── SafetyAlert.tsx           #      Critical safety warnings
│   │   ├── MarkdownRenderer.tsx      #      Rich text rendering
│   │   ├── InitialSetupScreen.tsx    #      Model download & setup
│   │   ├── ModelLoadingScreen.tsx    #      GGUF loading progress
│   │   └── QuickActionChips.tsx      #      Quick action shortcuts
│   ├── services/                     #    Core Services
│   │   ├── modelBridge.ts            #      LLM inference bridge (757 lines)
│   │   ├── ModelProvisioner.ts       #      Bulletproof model download (503 lines)
│   │   ├── inferencePolicy.ts        #      Turn routing & mode control
│   │   ├── responseProfiles.ts       #      Deterministic response paths
│   │   ├── VoiceService.ts           #      Whisper STT integration
│   │   ├── PerformanceMonitor.ts     #      Thermal & OOM monitoring
│   │   ├── BackgroundDownloadManager.ts #   Background download tracking
│   │   └── Logger.ts                 #      Structured logging
│   ├── stores/                       #    State Management (Zustand)
│   │   ├── chatStore.ts              #      Chat & streaming state
│   │   ├── threadStore.ts            #      Thread list management
│   │   └── appStore.ts               #      Global app state
│   ├── database/                     #    Offline Persistence
│   │   ├── schema.ts                 #      SQLite + FTS5 schema
│   │   └── operations.ts            #      CRUD operations
│   ├── constants/                    #    Configuration
│   │   ├── model.ts                  #      Model paths, prompts, params
│   │   ├── theme.ts                  #      Maritime design system
│   │   └── fonts.ts                  #      Typography configuration
│   └── providers/
│       └── ThemeProvider.tsx         #      Dark/light mode provider
│
├── deploy/                            # 🚀 Deployment Artifacts
│   ├── maritime-1.7b-local-q4km.gguf #    Production model (1.03 GB)
│   ├── maritime-1.7b-local-q5km.gguf #    High-quality variant (1.17 GB)
│   └── maritime-1.7b-local-f16.gguf  #    Full precision reference (3.2 GB)
│
├── configs/                           #    Training configurations
├── TRAINING-PLAN.md                   #    722-line research-grounded plan
├── ULTIMATE_MARITIME_AI_PLAN.md       #    2,361-line master execution plan
└── MARITIME_AI_TECHNICAL_HANDOFF.md   #    Technical handoff specification
```

---

## Phase 0 — Data Engineering

> **Months of effort. 43 custom scrapers. 115,783 chunks. This is the foundation everything else is built on.**

### The Data Collection Philosophy

We did not use a single off-the-shelf dataset. Every piece of training data was **collected, extracted, validated, chunked, and filtered** by our own pipeline. This was a deliberate decision — maritime safety data must be traceable to authoritative sources.

### Source Coverage Map

```
┌─────────────────────────────────────────────────────────────────┐
│                 43 CUSTOM WEB SCRAPERS                          │
│                 Maritime Data Collection Battalion               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ══════ REGULATORY BODIES ══════                                │
│  │ IMO          │ International Maritime Organization            │
│  │ EMSA         │ European Maritime Safety Agency                │
│  │ MCA          │ UK Maritime & Coastguard Agency                │
│  │ Paris MOU    │ Port State Control memorandum                  │
│                                                                  │
│  ══════ ACCIDENT INVESTIGATION ══════                           │
│  │ MAIB         │ UK Marine Accident Investigation Branch        │
│  │ NTSB         │ US National Transportation Safety Board        │
│  │ BSU          │ German Federal Bureau of Maritime Casualty     │
│  │ NSIA         │ Norwegian Safety Investigation Authority       │
│  │ Dutch Safety │ Dutch Safety Board maritime reports            │
│  │ CHIRP        │ Confidential Hazardous Incident Reports       │
│                                                                  │
│  ══════ CLASSIFICATION SOCIETIES ══════                         │
│  │ DNV          │ Det Norske Veritas                             │
│  │ ClassNK      │ Nippon Kaiji Kyokai                            │
│  │ Lloyd's      │ Lloyd's Register of Shipping                   │
│  │ ABS          │ American Bureau of Shipping                    │
│  │ IACS         │ Intl Association of Classification Societies   │
│                                                                  │
│  ══════ P&I CLUBS & INSURERS ══════                             │
│  │ Gard         │ Gard P&I insurance                             │
│  │ Skuld        │ Skuld mutual insurance                         │
│  │ Standard Club│ Standard Club P&I                              │
│  │ NE P&I       │ North of England P&I                           │
│  │ Steamship    │ Steamship Mutual                               │
│  │ UK P&I       │ UK P&I Club                                    │
│  │ ITOPF        │ Intl Tanker Owners Pollution Federation        │
│                                                                  │
│  ══════ INDUSTRY ORGANIZATIONS ══════                           │
│  │ BIMCO        │ Baltic & International Maritime Council        │
│  │ Hellenic     │ Hellenic Shipping News                         │
│  │ Safety4Sea   │ Safety4Sea intelligence platform               │
│  │ Marine Insight│ Marine Insight technical articles             │
│  │ Maritime Exec│ Maritime Executive news                        │
│  │ gCaptain     │ gCaptain maritime news                         │
│  │ Splash247    │ Splash maritime news                           │
│                                                                  │
│  ══════ ACADEMIC / RESEARCH ══════                              │
│  │ OpenAlex (×3)│ Open academic graph — maritime papers          │
│                                                                  │
│  + Specialized scrapers for bunkering, COW, ESE, FWG, gauging   │
│                                                                  │
│  Total: 43 scrapers → 115,783 chunks → ~72 Million tokens       │
└─────────────────────────────────────────────────────────────────┘
```

### Data Processing Pipeline

```
Raw Web Pages / PDFs
        │
        ▼
┌───────────────┐     ┌────────────────┐     ┌──────────────────┐
│  43 Scrapers  │────▶│ PDF Extractor  │────▶│ Quality Filter   │
│  (Parallel)   │     │ pdf_extractor  │     │ quality_filter   │
└───────────────┘     └────────────────┘     └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │   Intelligent     │
                                              │   Chunking       │
                                              │   (512-2048 tok) │
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  MinHash Dedup   │
                                              │  minhash_dedup   │
                                              └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  115,783 Chunks  │
                                              │  chunks.jsonl    │
                                              │  Gold Standard   │
                                              └──────────────────┘
```

### Teacher Distillation — 500K+ Q&A Generation

We used a **Qwen3-235B-A22B** (142GB Q4_K_M) teacher model running across **4 concurrent llama-server instances** to distill knowledge into structured Q&A pairs:

```
┌────────────────────────────────────────────────────────────────┐
│              MULTI-PROVIDER DISTILLATION ENGINE                 │
│              comprehensive_maritime_generator.py (854 lines)    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Teacher  │  │ Teacher  │  │ Teacher  │  │ Teacher  │      │
│  │ :8000    │  │ :8001    │  │ :8002    │  │ :8003    │      │
│  │ Qwen3    │  │ Qwen3    │  │ Qwen3    │  │ Qwen3    │      │
│  │ 235B     │  │ 235B     │  │ 235B     │  │ 235B     │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│       └──────────────┼───────────┬─┘              │            │
│                      ▼           ▼                ▼            │
│              ┌───────────────────────────┐                     │
│              │  5 Question Angles/Chunk  │                     │
│              │  • Practical scenario     │                     │
│              │  • Troubleshooting        │                     │
│              │  • Procedure / Checklist  │                     │
│              │  • Regulation reference   │                     │
│              │  • Safety-critical        │                     │
│              └─────────────┬─────────────┘                     │
│                            │                                    │
│              + External APIs for volume scaling:                │
│              ┌─────────┐ ┌──────────┐ ┌──────────┐            │
│              │ Gemini  │ │ Cerebras │ │   Groq   │            │
│              │ 2.5     │ │ LLaMA-8B │ │ LLaMA-8B │            │
│              │ Flash   │ │ instant  │ │ instant  │            │
│              └─────────┘ └──────────┘ └──────────┘            │
│                                                                 │
│  Coverage: 100+ maritime categories                            │
│  Distribution: Weighted by safety-criticality                  │
│  Validation: Per-sample JSON schema + forbidden phrase filter  │
│  Output: 500,000+ Q&A pairs                                   │
└────────────────────────────────────────────────────────────────┘
```

---

## The 6-Phase Training Pipeline

> **Every phase has a mathematical gate. If it fails, training stops. No exceptions.**

This pipeline implements findings from three convergent research streams:

| Research | Source | Key Finding |
|----------|--------|-------------|
| **openPangu Embedded** | Huawei, Sep 2025 | Two-stage curriculum SFT (reasoning-first, then concise) outperforms flat mixed training |
| **Qwen3 Technical Report** | Alibaba, Apr 2025 | Off-policy distillation in /think + /no_think modes, followed by on-policy refinement |
| **ORPO** | arXiv:2403.07691 | Combines SFT + preference optimization in one objective, eliminating DPO distribution shift |
| **SuperFiltering** | ACL 2024 | IFD via GPT-2 is consistent with 13B model orderings for data quality filtering |
| **Nature Comp. Materials 2025** | Multiple | DAPT+TAPT outperforms DAPT alone by 2-5% |

### Phase 1: CPT — Continued Pre-Training

**Goal:** Inject maritime domain knowledge into base Qwen3-1.7B without destroying general capabilities.

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: CONTINUED PRE-TRAINING (run_cpt_1.7b.py, 946 lines) │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Base Model: Qwen3-1.7B (fp16, device_map={"": 0})             │
│  LoRA Config: r=128, alpha=128, all projection layers           │
│  Optimizer: AdamW, lr=2e-5, cosine schedule                     │
│  Batch: micro=1, grad_accum=32 (effective batch=32)             │
│  Sequence Length: 512 tokens                                     │
│  Precision: fp16 only (K80 has no bf16 support)                 │
│                                                                  │
│  ┌─────────────────── CURRICULUM STAGES ──────────────────┐    │
│  │                                                         │    │
│  │  Stage 1 (0-10%):    50% Maritime / 50% General        │    │
│  │  Stage 2 (10-85%):   80% Maritime / 20% General  ◄─── │    │
│  │  Stage 3 (85-100%):  70% Maritime / 30% General        │    │
│  │                                                         │    │
│  │  The 3-stage curriculum prevents catastrophic           │    │
│  │  forgetting by maintaining general knowledge replay.    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  Innovation: CurriculumPackedIterableDataset                    │
│  ─────────────────────────────────────────                      │
│  • Pre-tokenizes entire corpus into uint32 binary arrays        │
│  • Uses np.memmap for O(1) RAM — reads tokens from disk         │
│  • Dynamic mixing ratio switches mid-training via callback      │
│  • Packed sequences (no padding waste)                          │
│                                                                  │
│  ┌─────────── GATE CHECK ───────────┐                          │
│  │ Maritime PPL drop:    ≥ 15%  ✅  │  Achieved: 74.5% drop   │
│  │ General PPL increase: ≤ 10%  ✅  │  Achieved: <2% increase │
│  │ If FAIL → training ABORTS        │                          │
│  └──────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: SFT Stage 1 — Reasoning Mode (`/think`)

**Goal:** Teach the model to produce DeepSeek-style `<think>` reasoning traces before answering.

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: SFT STAGE 1 — REASONING (run_sft1_1.7b.py)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: CPT checkpoint (LoRA merged into base weights)          │
│  Data: /think examples from sft_curated.jsonl                   │
│  New LoRA: r=32, alpha=32 (lighter than CPT)                   │
│  LR: 2e-4 (higher for SFT), NEFTune noise alpha=5             │
│                                                                  │
│  Training Format (Qwen3 chat template):                         │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ <|im_start|>system                                    │      │
│  │ You are an expert maritime assistant... /think         │      │
│  │ <|im_end|>                                            │      │
│  │ <|im_start|>user                                      │      │
│  │ A crew member has collapsed in the sewage tank...     │      │
│  │ <|im_end|>                                            │      │
│  │ <|im_start|>assistant                                 │      │
│  │ <think>                                               │      │
│  │ This is a life-critical emergency. Sewage tanks are   │      │
│  │ high-risk enclosed spaces with H2S and methane...     │      │
│  │ </think>                                              │      │
│  │ DO NOT enter immediately. Follow this sequence:       │      │
│  │ 1. Raise alarm, call master/chief engineer...         │      │
│  │ <|im_end|>                                            │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌─────────── GATE CHECK ───────────┐                          │
│  │ 50 unseen questions evaluated    │                          │
│  │ ≥ 70% must produce <think>       │                          │
│  │ block with > 20 words            │                          │
│  │ If FAIL → pipeline ABORTS        │                          │
│  └──────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: SFT Stage 2 — Direct Mode (`/no_think`) + Safety Traps

**Goal:** Teach concise direct responses AND adversarial safety refusals.

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: SFT STAGE 2 — DIRECT + TRAPS (run_sft2_1.7b.py)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: SFT1 checkpoint (merged)                                │
│  Data Sources:                                                   │
│    • /no_think examples (factual, regulatory, safety)           │
│    • Safety trap examples (sft_curated_traps.jsonl)             │
│    • Synthetic ThinkFollow pairs (auto-generated)               │
│                                                                  │
│  ThinkFollow Synthesis Logic:                                    │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Input: "How to perform enclosed space entry?"        │      │
│  │  Full Answer: "1. Ventilate for 30min. 2. Test O2..."│      │
│  │                        │                              │      │
│  │                        ▼                              │      │
│  │  Synthesized: "Just give me the most critical step    │      │
│  │  for: How to perform enclosed space entry?"           │      │
│  │  Answer: "Ventilate for 30min."                       │      │
│  │                                                       │      │
│  │  Forces conciseness AFTER reasoning is learned.       │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌─────────── GATE CHECK ───────────┐                          │
│  │ 50 adversarial trap questions    │                          │
│  │ ≥ 60% must refuse with exact:    │                          │
│  │ "I don't have sufficient         │                          │
│  │  information about this           │                          │
│  │  specific topic."                 │                          │
│  │ If FAIL → pipeline ABORTS        │                          │
│  └──────────────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 4–5: On-Policy Correction + ORPO Alignment

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 4: ON-POLICY CORRECTION                                  │
│  Student generates → Teacher scores → Correction training       │
├─────────────────────────────────────────────────────────────────┤
│  The student model answers questions from its own distribution. │
│  The 235B teacher grades each answer. Failures are corrected.   │
│  This closes the gap between training data and real inference.  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PHASE 5: ORPO PREFERENCE ALIGNMENT (run_orpo_1.7b.py)        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Config: beta=0.1, lr=8e-6, 1 epoch, batch=1, grad_accum=8    │
│                                                                  │
│  Synthetic Error Vectors (R1-R4):                               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  R1 (Regulatory): "shall" → "should"                  │      │
│  │     Makes mandatory requirements sound optional        │      │
│  │                                                        │      │
│  │  R2 (Safety): Remove first critical step               │      │
│  │     Deletes the most important action in a procedure   │      │
│  │                                                        │      │
│  │  R3 (Units): "kPa" → "bar"                            │      │
│  │     Introduces unit conversion errors in calculations  │      │
│  │                                                        │      │
│  │  R4 (Completeness): Truncate procedural answers        │      │
│  │     Removes the final verification/reporting steps     │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  By penalizing these exact semantic shifts, the model learns    │
│  superhuman precision on regulatory language, safety steps,     │
│  and unit accuracy — the things that matter most at sea.        │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 6: Quantization & Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 6: QUANTIZATION (quantize_1.7b.py)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LoRA Merge → FP16 → llama.cpp convert → GGUF                  │
│                                                                  │
│  Output Variants:                                                │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  Q4_K_M  │  1.03 GB  │  Production (mobile)   ◄──── │      │
│  │  Q5_K_M  │  1.17 GB  │  High-quality fallback       │      │
│  │  F16     │  3.21 GB  │  Reference / benchmarking     │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  Deployed to: huggingface.co/mohanganesh3/maritime_model_v1    │
│  Includes: model.gguf + whisper-tiny.bin (voice engine)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Critical Engineering Breakthroughs

### Tesla K80 Compatibility Hacks

The Tesla K80 (Kepler architecture, compute capability 3.7) lacks `bf16` support and Flash Attention. We engineered around every limitation:

| Challenge | Solution | File |
|-----------|----------|------|
| No `bf16` support | Strict `fp16=True, bf16=False` across all phases | All `run_*.py` |
| 11GB VRAM limit | QLoRA r=128 (CPT) / r=32 (SFT) + gradient accumulation | `run_cpt_1.7b.py` |
| OOM on data loading | `np.memmap` uint32 binary cache (zero-copy reads) | `run_cpt_1.7b.py:243` |
| Checkpoint resume crash | `_sanitize_checkpoint_for_transformers_resume()` strips corrupt RNG states | `run_cpt_1.7b.py:148` |
| Transformers/TRL mismatch | `PatchedORPOTrainer` wraps `ORPOTrainer` for v4.51.3/v0.11.0 compat | `phase2_optionc_common.py` |
| PyTorch uint32 missing | Custom `torch.uint32` polyfill shim | Training environment |
| Dual venv isolation | `.venv/` (generation) vs `.venv-train/` (training) with `ensure_venv_train()` gate | All `run_*.py` |

---

## Mobile Application — React Native Edge AI

> **The model runs entirely on-device. No server. No API calls. The phone IS the inference engine.**

### Inference Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                REACT NATIVE INFERENCE ARCHITECTURE                │
│                (frontend/services/modelBridge.ts — 757 lines)    │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  User Message                                                     │
│       │                                                           │
│       ▼                                                           │
│  ┌─────────────────────────────────────────────┐                 │
│  │           ZERO-SHOT LLM ROUTER              │                 │
│  │  n_predict: 160, temperature: 0.08          │                 │
│  │                                              │                 │
│  │  The model self-classifies into:             │                 │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────┐ │                 │
│  │  │  Domain    │ │ Risk Level │ │ Response │ │                 │
│  │  │ engine-room│ │ critical   │ │ checklist│ │                 │
│  │  │ bridge-nav │ │ standard   │ │ explain  │ │                 │
│  │  │ compliance │ │ low        │ │ converse │ │                 │
│  │  │ safety     │ │            │ │          │ │                 │
│  │  └────────────┘ └────────────┘ └──────────┘ │                 │
│  └──────────────────────┬──────────────────────┘                 │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────┐                 │
│  │         CONTEXT PRUNING ENGINE              │                 │
│  │  trimMessagesToContext()                      │                 │
│  │                                              │                 │
│  │  while (tokenCount > MAX_PROMPT_TOKENS):     │                 │
│  │      llamaContext.tokenize(messages)          │                 │
│  │      drop oldest turn                        │                 │
│  │                                              │                 │
│  │  Guarantees: NEVER exceeds context window    │                 │
│  │  Uses C++ tokenizer for exact count          │                 │
│  └──────────────────────┬──────────────────────┘                 │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────┐                 │
│  │         STREAMING INFERENCE + TAG PARSER    │                 │
│  │  llama.rn (C++ mmap → ARM NEON)             │                 │
│  │                                              │                 │
│  │  onToken callback:                           │                 │
│  │  ┌────────────────────────────────────┐     │                 │
│  │  │  tagBuffer accumulates chunks      │     │                 │
│  │  │  Scans for <think> / </think>      │     │                 │
│  │  │  Routes reasoning → ThinkingBlock  │     │                 │
│  │  │  Routes response → MessageBubble   │     │                 │
│  │  │  Tracks thinkTime duration         │     │                 │
│  │  └────────────────────────────────────┘     │                 │
│  └──────────────────────┬──────────────────────┘                 │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────┐                 │
│  │          PERSISTENCE LAYER                   │                 │
│  │  SQLite + FTS5 (full-text search)            │                 │
│  │  All conversations stored offline            │                 │
│  │  Instant message search across all threads   │                 │
│  └─────────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

### Bulletproof Model Download (`ModelProvisioner.ts` — 503 lines)

Deploying a 1.03 GB model to mobile devices over unreliable maritime connectivity required a custom download engine:

```
┌──────────────────────────────────────────────────────────────────┐
│              BULLETPROOF DOWNLOAD PROTOCOL                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Expected: EXACTLY 1,107,409,280 bytes (±256 slack)              │
│                                                                   │
│  HTTP 206 (Partial Content)                                       │
│  └─▶ Resume from existing bytes ✓                                │
│                                                                   │
│  HTTP 200 (Range Ignored)                                         │
│  └─▶ Server ignored resume request                               │
│  └─▶ DELETE corrupt appended file                                │
│  └─▶ Restart from byte 0                                         │
│                                                                   │
│  HTTP 416 (Range Not Satisfiable)                                │
│  └─▶ Check if file is already complete                           │
│  └─▶ If size matches → mark done                                │
│  └─▶ If size wrong → delete & retry                             │
│                                                                   │
│  Oversized file detected                                          │
│  └─▶ DELETE corrupt file, restart fresh                          │
│                                                                   │
│  .maritime_done marker written ONLY after                        │
│  byte-exact verification passes                                  │
│                                                                   │
│  Fallback URLs:                                                   │
│  1. huggingface.co (primary)                                     │
│  2. hf-mirror.com (China fallback)                               │
│  Max retries: 8 per artifact                                     │
└──────────────────────────────────────────────────────────────────┘
```

### Frontend Component Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                 REACT NATIVE COMPONENT MAP                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  App Layout (_layout.tsx)                                         │
│  ├── ThemeProvider (dark mode default)                            │
│  ├── Tab Navigator                                                │
│  │   ├── Home Tab (index.tsx)                                    │
│  │   │   ├── ThreadListItem (pinned, sorted)                    │
│  │   │   └── QuickStartTile (common actions)                    │
│  │   ├── New Chat Tab (new.tsx)                                  │
│  │   │   ├── QuickActionChips (pre-built prompts)               │
│  │   │   └── InputTray (text + voice input)                     │
│  │   └── Settings Tab (settings.tsx)                             │
│  │       ├── Model info display                                  │
│  │       └── Theme toggle                                        │
│  └── Chat Screen (chat/[threadId].tsx)                           │
│      ├── ScreenHeader (thread title, back nav)                   │
│      ├── MessageBubble (user + assistant)                        │
│      │   ├── MarkdownRenderer (rich formatting)                  │
│      │   ├── ThinkingBlock (<think> content)                     │
│      │   └── ThinkingGlow (animated indicator)                   │
│      ├── SafetyAlert (critical warning banner)                   │
│      ├── TypingIndicator (streaming dots)                        │
│      └── InputTray                                                │
│          ├── Text input                                           │
│          ├── Voice button (Whisper STT)                           │
│          └── Think mode toggle (/think vs /no_think)             │
│                                                                   │
│  Services Layer                                                   │
│  ├── modelBridge.ts      (LLM inference, 757 lines)             │
│  ├── ModelProvisioner.ts (download engine, 503 lines)            │
│  ├── VoiceService.ts     (Whisper STT, 269 lines)               │
│  ├── PerformanceMonitor.ts (thermal/OOM guard)                   │
│  └── inferencePolicy.ts (routing rules)                          │
│                                                                   │
│  State Management (Zustand)                                       │
│  ├── chatStore.ts   (messages, streaming, thinking)              │
│  ├── threadStore.ts (thread CRUD, pin, search)                   │
│  └── appStore.ts    (model status, global config)                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Deployment

### HuggingFace Hub

The production model is deployed at **[huggingface.co/mohanganesh3/maritime_model_v1](https://huggingface.co/mohanganesh3/maritime_model_v1)** with the following artifacts:

| Artifact | Size | Purpose |
|----------|------|---------|
| `model.gguf` | 1.03 GB | Q4_K_M quantized — production mobile inference |
| `whisper-tiny.bin` | 74 MB | Whisper tiny — voice-to-text in noisy engine rooms |

### Local Deployment Artifacts

Three quantization variants are available in `deploy/`:

| File | Size | Use Case |
|------|------|----------|
| `maritime-1.7b-local-q4km.gguf` | 1.03 GB | Mobile devices (4-8 GB RAM) |
| `maritime-1.7b-local-q5km.gguf` | 1.17 GB | Tablets / higher accuracy |
| `maritime-1.7b-local-f16.gguf` | 3.21 GB | Full precision benchmarking |

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Base Model** | Qwen3-1.7B | Student model backbone |
| **Teacher Model** | Qwen3-235B-A22B (142GB) | Knowledge distillation source |
| **Training Framework** | PyTorch 2.1.2 + CUDA 11.8 | GPU training |
| **Fine-Tuning** | PEFT (QLoRA) + TRL (ORPO) | Parameter-efficient training |
| **Serving (Training)** | llama.cpp / llama-server | Teacher model inference |
| **Quantization** | llama.cpp GGUF converter | FP16 → Q4_K_M / Q5_K_M |
| **Data Pipeline** | Custom Python (43 scrapers) | Web scraping, extraction, filtering |
| **Data Quality** | MinHash dedup + IFD filter | Deduplication and quality scoring |
| **Frontend** | React Native + Expo SDK 51 | Cross-platform mobile app |
| **Mobile Inference** | llama.rn (C++ bindings) | On-device GGUF inference |
| **Voice Engine** | Whisper Tiny (77MB) | Speech-to-text for maritime use |
| **Local Storage** | expo-sqlite + FTS5 | Offline conversation persistence |
| **State Management** | Zustand | Lightweight reactive state |
| **Model Hosting** | HuggingFace Hub | Model distribution |
| **Generation APIs** | Gemini 2.5 / Cerebras / Groq | Supplementary data generation |

---

## Documentation

| Document | Lines | Purpose |
|----------|-------|---------|
| [`TRAINING-PLAN.md`](TRAINING-PLAN.md) | 722 | Research-grounded training lifecycle with citations |
| [`ULTIMATE_MARITIME_AI_PLAN.md`](ULTIMATE_MARITIME_AI_PLAN.md) | 2,361 | Master execution plan with every task, script, and gate |
| [`MARITIME_AI_TECHNICAL_HANDOFF.md`](MARITIME_AI_TECHNICAL_HANDOFF.md) | 112 | Technical specification for deployment integration |

---

## Getting Started

### Prerequisites

- Python 3.10+ with CUDA support
- Node.js 18+ and npm
- Android SDK (for mobile build)
- 4+ GB RAM device (for inference)

### Training (requires GPU)

```bash
# Activate training environment
source .venv-train/bin/activate

# Phase 1: Continued Pre-Training
CUDA_VISIBLE_DEVICES=0 python training/run_cpt_1.7b.py

# Phase 2: SFT Stage 1 (Reasoning)
CUDA_VISIBLE_DEVICES=0 python training/run_sft1_1.7b.py

# Phase 3: SFT Stage 2 (Direct + Safety)
CUDA_VISIBLE_DEVICES=0 python training/run_sft2_1.7b.py

# Phase 5: ORPO Alignment
CUDA_VISIBLE_DEVICES=0 python training/run_orpo_1.7b.py

# Phase 6: Quantize to GGUF
python training/quantize_1.7b.py
```

### Mobile App Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npx expo start

# Build Android APK
npx expo run:android
```

### Data Generation

```bash
# Activate generation environment
source .venv/bin/activate

# Run the 500K multi-provider generator
python scripts/comprehensive_maritime_generator.py

# Run quality audit
python scripts/quality_audit.py
```

---

## Research References

1. **openPangu Embedded** (Huawei, Sep 2025) — Curriculum SFT for billion-parameter models
2. **Qwen3 Technical Report** (Alibaba, Apr 2025) — Off-policy + on-policy distillation recipe
3. **ORPO: Monolithic Preference Optimization** (arXiv:2403.07691) — Combined SFT + preference alignment
4. **SuperFiltering** (ACL 2024) — IFD-based data quality scoring
5. **DAPT+TAPT** (Nature Computational Materials, 2025) — Domain + task adaptive pre-training


<p align="center">
  <br/>
  <strong>Built with months of research, hundreds of papers, and zero compromises.</strong><br/>
  <em>Because at sea, there is no second chance.</em><br/><br/>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:1565c0,50:0d47a1,100:0a192f&height=120&section=footer" width="100%"/>
</p>
