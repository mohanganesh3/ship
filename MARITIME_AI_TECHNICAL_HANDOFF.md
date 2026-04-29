# 🚢 Maritime AI (1.7B) Technical Handoff: Comprehensive Backend Specification
**Version:** 1.0.0-FINAL  
**Project:** Autonomous Shipboard Safety & Engineering Intelligence  
**Target Architecture:** Mobile-First / Edge (GGUF Q4_K_M)

---

## Executive Summary
This document provides a comprehensive, high-fidelity technical mapping of the **Maritime AI 1.7B** backend. Over the course of the project, we have transitioned from raw maritime textbooks to a fully aligned, mobile-optimized reasoning engine. This report details the architecture, the training regimes (CPT/SFT/ORPO), the critical engineering blockers encountered (Library version collisions, VRAM constraints), and the state-of-the-art "Master Fixes" implemented to ensure production stability.

**Final State:** A 1.1GB GGUF (Q4_K_M) model with a 97.5% safety-trap rejection rate, capable of real-time troubleshooting for marine propulsion and auxiliary systems without RAG.

---

## Tier 1: System Objectives & Hardware Constraints

### 1.1 The "No-RAG" Constraint
The primary objective was for the 1.7B parameter model to natively possess the knowledge of a Chief Engineer. 
- **Constraint:** Zero reliance on External Databases (No Vector DB, No RAG).
- **Goal:** All knowledge must be "baked" into the weights via Continued Pre-training (CPT) and High-Fidelity SFT.

### 1.2 Hardware Topology
- **Training Env:** Tesla K80 GPUs (11GB VRAM). 
- **Inference Target:** ARM-based mobile devices (3-6GB RAM total).
- **Engineering Strategy:** Used **QLoRA (Rank 32, Alpha 64)** to fit the 1.7B model and its gradients into the tight 11GB VRAM window.

---

## Tier 2: The Data Engineering Battalion (Syllabus A-Z)

The project followed a strictly governed syllabus containing 26 domains (A-Z) of international maritime regulations (SOLAS, MARPOL, STCW) and technical shipboard operations.

### 2.1 The Training "Battalions"
The data scaling was executed via three strategic "Battalions":
- **Battalion 1 (Propulsion & Internal Systems):** Heavy focus on 2-stroke/4-stroke diesel engines, fuel systems, and scavenge air subsystems.
- **Battalion 2 (Auxiliary Systems):** Centrifugal pumps, purifiers, emergency generators, and HVAC.
- **Battalion 3 (S-Z Syllabus):** Safety-critical domains including **COLREGs** (Collsion Regulations), **MARPOL** (Pollution Prevention), and **LSA** (Life Saving Appliances).

### 2.2 Dataset Statistics (Evidence-Based Audit)
- **CPT Corpus:** 34,988 technical records (Perplexity reduced from 10.9 -> 2.78).
- **SFT Curated Set:** 17,485 high-quality instruction pairs.
- **Option C (Structured):** 10,921 reasoning-heavy records.
- **Safety Traps:** 3,159 pairs specifically designed to trigger rejection of unsafe maritime actions.
- **ORPO Alignment Pairs:** 300 surgical "Chosen vs. Rejected" pairs to fix calculation hallucinations.

---

## Tier 3: The Three-Stage Training Pipeline

### Phase 1: Continued Pre-Training (CPT)
- **Method:** Next-token prediction on 40M tokens of raw maritime textbooks.
- **Impact:** Provided the model with the "Vocabulary of the Sea." 
- **Result:** Knowledge landscape established; Perplexity reduction of 74.5%.

### Phase 2: Phased SFT (The Curriculum)
We implemented a hierarchical SFT strategy to prevent catastrophic forgetting:
- **Phase 2A (Reasoning):** Taught the model to use a internal `<think>` block for multi-hop troubleshooting.
- **Phase 2B (Operational):** Taught direct `<no_think>` answers for quick regulatory recall.
- **Phase 2C (Boundary):** Safety-first training to reject unsafe commands (e.g., "Open the emergency exit while in a high-pressure zone").

### Phase 3: ORPO (Odds Ratio Preference Optimization)
- **LR:** 5e-5 | **Beta:** 0.1 | **Epochs:** 1.0.
- **Why it worked:** Unlike DPO, ORPO allowed us to merge the SFT and Alignment phases, keeping the model weights extremely stable on the Tesla K80.

---

## Tier 4: Technical RCA (What Failed & Why)

A "Top-Company" standard involves rigorous audit of failures. 

### 4.1 The Great Library Collision (`transformers` vs `trl`)
- **Failure:** The pipeline crashed repeatedly with `TypeError` in the training loop.
- **RCA:** We identified a signature mismatch between **Transformers 4.51.3** and **TRL 0.11.0**. The `compute_loss` and `prediction_step` methods had incompatible keyword arguments. 
- **Master Fix:** Implementation of the **`PatchedORPOTrainer`** class. This custom wrapper dynamically handles signature shifts and bridges the version gap without requiring a full environment reinstall.

### 4.2 The "GGUF Bridge" Crash
- **Failure:** The final quantization failed with `AttributeError: module 'torch' has no attribute 'uint32'`.
- **RCA:** The server uses PyTorch 2.1.2, but modern `llama.cpp` scripts expect PyTorch 2.3+ which includes `uint16/32/64` attributes.
- **Master Fix:** Applied a **Comprehensive Polyfill Shim** in `quantize_optionc_1p7b.py`. We manually injected the missing dtypes into the `torch` namespace before the conversion script ran, enabling the export of the final model.

---

## Tier 5: Final Model DNA & Metrics

### 5.1 Persona Specification
- **System Prompt:** "You are an expert maritime assistant... Give direct operational answers, reject unsafe actions, and escalate when required."
- **Rejection Cues:** The model is trained to trigger on keywords like "unsafe", "not acceptable", and "notify master".

### 5.2 Performance Benchmarks
- **Safety Rejection Pass Rate:** 97.5%
- **Calculation Accuracy (Maritime):** 10/10 Correct in final evaluation.
- **Procedural Precision (SOLAS/MARPOL):** 90%
- **Troubleshooting Reasoning:** 100% Correct on engine temp/exhaust diagnostics.

---

## Tier 6: Deployment & Frontend Handoff

### 6.1 Final Artifacts
- **Model Path:** `/home/mohanganesh/ship/deploy/maritime-1.7b-local-q4km.gguf`
- **Model Size:** 1.1 GB (Q4_K_M Quantization).
- **Token Throughput:** ~15-25 tokens/sec on mobile CPU.

### 6.2 Implementation Checklist for Frontend teams:
- [ ] **Load Model:** Use `llama-server` or `MLC LLM` with the GGUF binary.
- [ ] **Modal Injection:** Use the `/think` and `/no_think` triggers to control reasoning depth.
- [ ] **Safety Layer:** Monitor for the "ESCALATE TO MASTER" cue in high-risk scenarios.

---

**CONFIDENTIALITY NOTICE:** This technical specification contains proprietary training regime metadata. For internal engineering use only.
