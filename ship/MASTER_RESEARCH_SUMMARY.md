# MASTER MARITIME AI RESEARCH SYNTHESIS (GROUNDED + TRACEABLE)

This file is the *single place* to understand the project’s research outputs, dataset audits, and implementation plan for an offline shipboard maritime chatbot.

**Important correction:** An earlier version of this file claimed “10/10 production-ready.” That is **not consistent** with the project’s own sufficiency and coverage-gap analyses. The grounded verdict across those documents is:

- **Not enough for production**; **borderline for a study-aid** at the current dataset size (~8.4M CPT tokens). (See `DATA_SUFFICIENCY_VERDICT.md` and `DATA_SUFFICIENCY_ANALYSIS.md`.)

## What this summary currently covers

This document is being rebuilt to be strictly file-grounded with traceability.

**Integrated (grounded) so far:**

- `DATA_SUFFICIENCY_VERDICT.md`
- `DATA_SUFFICIENCY_ANALYSIS.md`
- `DATASET_COVERAGE_GAP_ANALYSIS.md`
- `MISSING_TOPICS_AND_DATA_COLLECTION_PLAN.md`
- `FINAL_RANKING_AND_PLAN.md`
- `COMBINED_PIPELINE_RANKING_EVALUATION.md`
- `SHIP_AI_CHATBOT_PLAN.md` (partial)

**Not yet integrated (pending read + extraction into this master):**

- Remaining ranking evaluation documents (CPT/SFT/RL/DPO, quantization, model merging, pruning, etc.)
- `MARITIME_DATA_SOURCING_GUIDE.md` / `MARITIME_FREE_DATA_SOURCING_DEEP_RESEARCH.md`
- `Small_Language_Models_Edge_Devices_Report_2025.md`

## Integrity snapshot (MD inventory)

The following table is copied from `MD_INVENTORY.tsv` to provide a stable inventory of the markdown corpus (bytes/lines/sha256).

Note: this master file (`MASTER_RESEARCH_SUMMARY.md`) is actively being edited, so its current bytes/lines/hash will differ from the historical snapshot.

| file | bytes | lines | sha256 |
|---|---:|---:|---|
| COMBINED_PIPELINE_RANKING_EVALUATION.md | 44968 | 516 | 449e7cfc124392fd40248f89e493dcd2d0fdbc916df0607f27f17a7c93784e9b |
| CPT_RANKING_EVALUATION.md | 33787 | 472 | 52a789d79c2441c92f9018569a4ba2852c03c890d2f89826d01d336189a7042f |
| DATASET_COVERAGE_GAP_ANALYSIS.md | 50940 | 1083 | e7ff0ecf9cdb6972f1ead65f17a3d0ef7ff11b3fc94758fd7dc14ae7a2496ddd |
| DATA_SUFFICIENCY_ANALYSIS.md | 38183 | 604 | 3d7fc0b0d469013bfd7c665864004d2af8f25c9f1838a6df3fdbbcfb82dee7ea |
| DATA_SUFFICIENCY_VERDICT.md | 18367 | 338 | 823fcb36cc4fae4526c45d5358003c58149f9afe61e517e5138c302d87e509ea |
| EXHAUSTIVE_KNOWLEDGE_INJECTION_RESEARCH.md | 68967 | 1340 | a10dda77359c184e0300c480c7a6784cbfd1e35b76cba78fb4b67ef33fa211a1 |
| EXTREME_QUANTIZATION_RANKING_EVALUATION.md | 55909 | 685 | 63bea98a870a34acb2218be8e3ff63e4d2af93b3407928e0182e37477a710654 |
| FINAL_RANKING_AND_PLAN.md | 13781 | 266 | 72f0b56c1db032b1c7d9726f5dcc98481759833df74b1b6941d99b54b37171cf |
| MARITIME_DATA_SOURCING_GUIDE.md | 71240 | 1742 | 1c1b70551994811472ca11d32acd8ecf741bbcb3bb408b754978faa944cff6ac |
| MARITIME_FREE_DATA_SOURCING_DEEP_RESEARCH.md | 42716 | 1174 | 125f298e6044fd7a41578cf4762ad7064f15103b26474ceaa2e5f018f3817d8e |
| MISSING_TOPICS_AND_DATA_COLLECTION_PLAN.md | 25923 | 423 | 0698f6cf7b0ec2e6fda16f2d98334adeffb3cf54f03e221aba8a08662f835ac1 |
| MODEL_MERGING_RANKING_EVALUATION.md | 40466 | 616 | ccf40dc2e226c997b910761198816232ecd07e9d784d7b5ab6a1d94fa8507e8c |
| PRETRAINING_FROM_SCRATCH_RANKING_EVALUATION.md | 51258 | 598 | fede1f942876b24c5bf4921de97c8a2c3634d9860fcc014764ec75f5aa66c07e |
| PRUNING_SPARSIFICATION_RANKING_EVALUATION.md | 66609 | 856 | 87f7bb99363476f73a52a947748198169dbb256072b6c533997ddf96a2f56bb0 |
| QLORA_KNOWLEDGE_INJECTION_DEEP_DIVE.md | 78340 | 1198 | 6097792e1b2bb4384325991f9e8484a1eb7a828a81f7ad6b5c0b9f5c6a16ac3f |
| REASONING_DISTILLATION_RANKING_EVALUATION.md | 58750 | 747 | 5dbd16ca9ebe86e575eaadfd0931dcee7d59beef9b3785cf64ffc7f480d7ff77 |
| RL_METHODS_RANKING_EVALUATION.md | 54942 | 650 | 045aa13ac30262cab6ef11b789d6a16ac0ad6f1a2d549b9fb8a87e3654ada716 |
| SFT_RANKING_EVALUATION.md | 36550 | 580 | b2a13230fd48c5342318194436c85a943badb707e50b5a1bf49103133bcdad90 |
| SHIP_AI_CHATBOT_PLAN.md | 40828 | 1092 | 286fb94af09df83f8edd223679014426b747f4b255770ab1c58d2e2c4c670471 |
| Small_Language_Models_Edge_Devices_Report_2025.md | 296804 | 6040 | 02909e09e7c693a8ec8c090fc29c186369acf763c1cf71622c31bf9291897c99 |
| TEST_TIME_COMPUTE_SCALING_RANKING_EVALUATION.md | 58548 | 763 | 0ad4768c65653fdab29b18f3bfb06992bdaf243469e3c0db7eee71b250222824 |

## Dataset sufficiency: production vs study-aid (grounded)

### Bottom-line verdict

- **“❌ NOT ENOUGH FOR PRODUCTION — BORDERLINE FOR STUDY AID”** is the explicit verdict headline. (`DATA_SUFFICIENCY_VERDICT.md`, top section)
- The corpus is described as **8.4M tokens from ~100 books**, and presented as **3–6× below** the minimum effective CPT threshold for a 4B model. (`DATA_SUFFICIENCY_VERDICT.md`, “VERDICT” and “The Brutal Numbers”)

### Key numeric thresholds (as stated in-project)

From the “Brutal Numbers” table (`DATA_SUFFICIENCY_VERDICT.md`):

- CPT tokens: **8.4M (current)** vs **15–25M (study aid minimum)** vs **50–100M (production minimum)**
- Token-to-parameter ratio: **0.002:1 (current)** vs **0.005:1 (study aid minimum)** vs **0.015:1 (production minimum)**
- SFT Q&A pairs: **~32K planned** vs **30–50K (study aid)** vs **80–100K (production)**
- DPO pairs: **~10K planned** vs **10K (study aid)** vs **20K (production)**

### Safety constraint (non-negotiable)

The verdict doc contains an explicit warning that wrong answers about enclosed-space thresholds, firefighting systems, or lifeboat procedures can be fatal, and claims that at 8.4M tokens the model may provide confidently incorrect specific values **20–40%** of the time on safety-critical questions. (`DATA_SUFFICIENCY_VERDICT.md`, “⚠️ SAFETY WARNING”)

The longer analysis doc aligns: it calls the setup **“sufficient for a capable study aid, insufficient for safety-critical production without guardrails.”** (`DATA_SUFFICIENCY_ANALYSIS.md`, “VERDICT”)

## Coverage gap audit (grounded)

### Overall dataset health score

`DATASET_COVERAGE_GAP_ANALYSIS.md` scores the dataset at **4.5/10**, describing it as **“textbook-heavy and procedure-light”** and warning it will miss **40–50%** of daily operational questions. (Executive Summary)

### Highest-severity missing areas (examples)

From the same gap analysis (Executive Summary + missing-topics sections):

- Cargo operations (tanker/bulk/container) — critical
- Auxiliary machinery systems (OWS, FWG, purifiers, sewage, incinerator) — critical
- GMDSS / communications — critical
- ECDIS operations (not just regulatory resolution text) — critical
- Deck operations (mooring/anchoring/cranes) — severe
- Bunkering operations — severe
- Permit-to-work / enclosed space / hot work — safety-critical

## Missing topics + collection strategy (grounded)

`MISSING_TOPICS_AND_DATA_COLLECTION_PLAN.md` enumerates **90 missing topic areas** (with extensive sub-questions) and asserts a production target of **35–50M tokens**.

### Claimed existing scraper set

The plan claims **15 scrapers** exist under `maritime_pipeline/scrapers/`, and flags **4 duplicates to delete** (keep the `X_scraper.py` versions, delete the `scraper_X.py` versions). (`MISSING_TOPICS_AND_DATA_COLLECTION_PLAN.md`, Part 2)

However, in the current workspace, `maritime_pipeline/scrapers/` contains **many more than 15 scrapers**, and a glob search for `scraper_*.py` returned **no matches**. That suggests the “4 duplicate scrapers” instruction is either outdated or already applied.

### High-value free sources (as proposed)

The sufficiency verdict doc includes a “Tier 1: Free Data” plan with sources such as:

- GOV.UK MAIB reports (UK Open Government Licence)
- USCG NVICs
- NOAA Bowditch / Coast Pilot
- P&I club loss-prevention publications
- Classification society publications (DNV/IACS, etc.)

## Web verification of proposed “free” sources (grounded to fetch results)

Some URLs in the internal plans are verified as accessible; others are stale or blocked.

### Verified as accessible (this session)

- **UK Open Government Licence v3.0 terms**: explicitly permits copying, publishing, distributing, transmitting, adapting, and commercial/non-commercial use subject to attribution, with common exemptions (personal data, logos, third-party rights, etc.).
    - Source: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

- **COSWP (GOV.UK) withdrawn page still provides a PDF** (“2017 edition - amendment 2”) and states GOV.UK content is under OGL v3.0 except where otherwise stated.
    - Source: https://www.gov.uk/government/publications/code-of-safe-working-practices-for-merchant-seafarers-coswp

- **MAIB Atom feed** exists and lists report entries with `link rel="alternate"` HTML pages.
    - Source: https://www.gov.uk/maib-reports.atom

### Not verified / currently failing via automated fetch

- **NTSB marine accident report URLs** referenced in the plan returned “Page not found” in this session (multiple attempted NTSB paths).
- **ATSB marine reports URL** attempted returned HTTP 404.
- **USCG NVIC direct-PDF example URL** attempted returned HTTP 404 (suggesting some PDF deep links may change even when the index page works).
- **Gard / Everllence (formerly MAN-ES domain used in plan)** pages were blocked behind cookie/consent overlays or returned “not found,” preventing automated extraction here.

For these sources, the plan should treat them as **“candidate sources pending manual discovery of stable listing endpoints (sitemaps, feeds, API endpoints, or updated paths)”**.

## Interim recommendation (until full master synthesis is complete)

1. Treat the current system as a **study-aid tier** until corpus volume and procedure coverage improve.
2. Prioritize **procedure-heavy** sources to close the “procedure-light” gap.
3. Add explicit **safety guardrails** in the application layer (disclaimers + escalation-to-manual + uncertainty behavior), since the project’s own docs flag safety-critical failure modes.

## Pipeline ranking & constraint alignment (grounded)

### Final ranking outcome (NO-RAG, mobile-first)

`FINAL_RANKING_AND_PLAN.md` frames a hard constraint set (offline, mobile RAM limits, **no RAG; all knowledge baked into weights**) and ranks “**CPT + Synthetic SFT + Distillation (Full Pipeline)**” as the winner with a **73/100** total score.

It also explicitly notes that removing RAG costs accuracy (it states “RAG would have scored 85+/100” and that “the model WILL hallucinate sometimes on exact facts/numbers”), and recommends positioning as a **study aid** rather than safety-critical authority.

### Combined pipeline evaluation rationale

`COMBINED_PIPELINE_RANKING_EVALUATION.md` motivates the multi-stage approach as synergistic:

- CPT provides domain vocabulary/conceptual “substrate”
- Synthetic Q&A generation creates absorbable supervision
- SFT crystallizes responses into retrievable patterns
- DPO/GRPO is positioned as a *polishing / safety* layer rather than knowledge injection
- Model merging improves robustness; quantization enables on-device deployment

It also calls out a key tension: LoRA/QLoRA efficiency vs potentially weaker *new knowledge acquisition* (“LoRA Learns Less and Forgets Less”).

### Constraint mismatch to resolve: NO-RAG vs RAG

There is a **project-internal inconsistency** to resolve before implementation:

- `FINAL_RANKING_AND_PLAN.md` and multiple ranking docs are written under the constraint **NO RAG**.
- `SHIP_AI_CHATBOT_PLAN.md` includes an explicit **RAG architecture** (Chat UI → API server → Retrieval/Vector DB) and says “Two-pronged approach: RAG + Fine-tuning.”

This matters because it changes:

- **Safety posture** (RAG can provide verbatim citations; no-RAG must rely on guardrails + uncertainty)
- **Maintenance** (RAG updates can be minutes; baked-weights retraining is days)
- **Accuracy on exact numbers/reg clauses** (RAG typically wins)

Until this mismatch is resolved, downstream choices (data acquisition, evaluation, UI promises) are at risk of being internally contradictory.

