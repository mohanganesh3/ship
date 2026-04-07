#!/usr/bin/env python3
"""Boundary-v2 training: safety/trap/regulatory boundary from SFT2 base.

Key changes from v1:
- LoRA r=16 (reduced from 32 to prevent forgetting)
- 10% warmup + cosine decay
- Uses curated 320-sample dataset with quality gates
- Merge-and-unload pattern (no adapter stacking)
- Fastref eval: 10/category from v2 benchmark

Usage:
    python run_boundary_v2.py [--dry-run] [--epochs 0.75]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from transformers import Trainer, TrainingArguments

from phase2_optionc_common import (
    DEFAULT_BENCHMARK,
    SYSTEM_PROMPT_NOTHINK,
    SYSTEM_PROMPT_THINK,
    SupervisedDataCollator,
    ensure_cuda,
    ensure_venv_train,
    gate_require_dir,
    gate_require_file,
    generate_response,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    normalize_space,
    patch_trainer_rng_resume,
    read_jsonl,
    resolve_adapter_chain,
    resolve_resume_checkpoint,
    score_response,
    setup_logging,
    tokenize_texts,
    write_chain_metadata,
)

PHASE = "BOUNDARY_V2_1.7B"

# Paths
SFT2_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft2-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/boundary-v2-1.7b")
BOUNDARY_DATASET = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/boundary_v2_dataset.jsonl"
)

# GPU selection: set CUDA_VISIBLE_DEVICES externally before launching this script


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Boundary-v2 training for 1.7B maritime model")
    parser.add_argument("--epochs", type=float, default=0.75)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (reduced from 32)")
    parser.add_argument("--lora-alpha", type=int, default=32)
    return parser.parse_args()


def build_training_texts(tokenizer, dataset_path: Path, max_length: int) -> list[str]:
    """Build training texts from the boundary-v2 dataset."""
    records = read_jsonl(dataset_path)
    texts = []
    for r in records:
        q = r.get("q") or r.get("question") or ""
        a = r.get("a") or r.get("answer") or ""
        if not q or not a:
            continue
        text = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": SYSTEM_PROMPT_NOTHINK},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ],
            tokenize=False,
            add_generation_prompt=False,
        )
        texts.append(text)
    return texts


def structural_pass(answer: str, category: str, item: dict) -> tuple[bool, dict]:
    """Lightweight structural scorer for fastref gate.
    Checks what matters structurally, not verbatim required_checks.
    """
    from phase2_optionc_common import (
        strip_think, normalize_space as ns, REGULATORY_MODAL_CUES,
        TRAP_REJECTION_CUES, escalation_alias_match
    )
    text = strip_think(ns(answer))
    lowered = text.lower()

    # 1. Escalation check (alias-aware)
    escalation_targets = item.get("escalation_targets", [])
    esc_hit = not escalation_targets or any(
        any(escalation_alias_match(t, line) for line in text.splitlines())
        for t in escalation_targets
    )

    # 2. Trap rejection (for trap category)
    trap_ok = True
    if category == "trap":
        trap_ok = any(cue in lowered for cue in TRAP_REJECTION_CUES)

    # 3. Modal language (for regulatory)
    modal_ok = True
    if category == "regulatory":
        modal_ok = any(cue in lowered for cue in REGULATORY_MODAL_CUES)

    # 4. Do-not slot (must contain a prohibition line)
    do_not_items = item.get("do_not", [])
    do_not_ok = True
    if do_not_items and category in ("trap", "safety", "regulatory"):
        do_not_ok = "do not" in lowered or "must not" in lowered or "prohibited" in lowered

    passed = esc_hit and trap_ok and modal_ok and do_not_ok
    return passed, {
        "esc_hit": esc_hit, "trap_ok": trap_ok,
        "modal_ok": modal_ok, "do_not_ok": do_not_ok
    }


def run_fastref_eval(model, tokenizer, benchmark_path: Path, n_per_category: int = 10) -> dict:
    """Run fast-reference eval on n items per category."""
    benchmark = read_jsonl(benchmark_path)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in benchmark:
        cat = normalize_space(item.get("category", "")).lower()
        grouped[cat].append(item)

    results = {}
    for category, items in grouped.items():
        subset = items[:n_per_category]
        passed = 0
        for item in subset:
            mode = "think" if category in ("troubleshooting", "calculation") else "no_think"
            answer = generate_response(model, tokenizer, item["question"], mode=mode, max_new_tokens=300)
            ok, detail = structural_pass(answer, category, item)
            if ok:
                passed += 1
        tested = len(subset)
        rate = (passed / tested * 100.0) if tested else 0.0
        results[category] = {"tested": tested, "passed": passed, "rate": round(rate, 2)}

    return results


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)

    # Gates
    gate_require_file(BOUNDARY_DATASET, PHASE)
    gate_require_dir(SFT2_FINAL, PHASE)

    # Load tokenizer
    tokenizer = load_tokenizer()

    # Build training texts
    texts = build_training_texts(tokenizer, BOUNDARY_DATASET, args.max_length)
    if len(texts) < 100:
        log_pipeline(f"{PHASE} FAIL — DATASET_GATE: boundary dataset too small ({len(texts)})")
        raise SystemExit(1)
    log_pipeline(f"{PHASE} STATUS: {len(texts)} training texts prepared")

    # Tokenize
    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    log_pipeline(f"{PHASE} STATUS: {len(dataset)} tokenized samples")

    # Load model from SFT2 base (merge-and-unload pattern)
    log_pipeline(f"{PHASE} STATUS: Loading merged model from {SFT2_FINAL}")
    model = load_merged_model_from_adapter(SFT2_FINAL, PHASE)

    # Attach FRESH LoRA with reduced rank (r=16 instead of r=32)
    # Critical: enable_input_require_grads first (matches attach_training_lora pattern)
    if hasattr(model, "peft_config"):
        delattr(model, "peft_config")
    model.enable_input_require_grads()
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(OUTPUT_DIR)
    patch_trainer_rng_resume()

    if args.dry_run:
        log_pipeline(
            f"{PHASE} STATUS: DRY RUN OK samples={len(dataset)} "
            f"r={args.lora_r} alpha={args.lora_alpha} lr={args.lr} epochs={args.epochs} resume={resume_from}"
        )
        print(f"\n✅ DRY RUN OK: {len(dataset)} samples, r={args.lora_r}, alpha={args.lora_alpha}")
        return

    # Training arguments — 10% warmup + cosine decay
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        overwrite_output_dir=False,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=args.lr,
        warmup_ratio=0.10,  # 10% warmup (research: prevents gradient shock)
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        fp16=True,
        bf16=False,
        gradient_checkpointing=True,
        logging_steps=5,
        logging_first_step=True,
        save_steps=50,
        save_total_limit=2,
        dataloader_num_workers=0,
        dataloader_pin_memory=True,
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=SupervisedDataCollator(tokenizer),
    )

    log_pipeline(f"{PHASE} STATUS: TRAINING STARTED samples={len(dataset)} resume={resume_from}")
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)

    # Save candidate
    candidate_dir = OUTPUT_DIR / "candidate"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(candidate_dir))
    tokenizer.save_pretrained(str(candidate_dir))
    write_chain_metadata(candidate_dir, resolve_adapter_chain(SFT2_FINAL, PHASE) + [candidate_dir], PHASE)

    # Fastref eval: 10 per category
    log_pipeline(f"{PHASE} STATUS: Running fastref eval (10/category)")
    eval_model = load_merged_model_from_adapter(candidate_dir, PHASE)
    eval_model.eval()

    fastref = run_fastref_eval(eval_model, tokenizer, DEFAULT_BENCHMARK, n_per_category=10)

    # Log results
    log_pipeline(f"{PHASE} FASTREF RESULTS:")
    for cat, res in sorted(fastref.items()):
        log_pipeline(f"  {cat}: {res['passed']}/{res['tested']} ({res['rate']}%)")
        print(f"  {cat}: {res['passed']}/{res['tested']} ({res['rate']}%)")

    # Save fastref results
    fastref_path = OUTPUT_DIR / "fastref_boundary_v2.json"
    fastref_path.write_text(json.dumps(fastref, indent=2), encoding="utf-8")

    # Gate: trap >= 60%, safety >= 50% (lower bar than final)
    trap_rate = fastref.get("trap", {}).get("rate", 0)
    safety_rate = fastref.get("safety", {}).get("rate", 0)

    if trap_rate >= 60 and safety_rate >= 50:
        # Promote to final
        final_dir = OUTPUT_DIR / "final"
        if final_dir.exists():
            shutil.rmtree(final_dir)
        candidate_dir.rename(final_dir)
        write_chain_metadata(final_dir, resolve_adapter_chain(SFT2_FINAL, PHASE) + [final_dir], PHASE)
        log_pipeline(f"{PHASE} STATUS: COMPLETE → {final_dir}")
        log_pipeline(f"{PHASE} GATE: PASS trap={trap_rate}% safety={safety_rate}%")
        print(f"\n✅ BOUNDARY-V2 PASSED: trap={trap_rate}%, safety={safety_rate}%")
    else:
        log_pipeline(f"{PHASE} GATE: FAIL trap={trap_rate}% safety={safety_rate}% (need trap>=60 safety>=50)")
        print(f"\n❌ BOUNDARY-V2 FAILED: trap={trap_rate}%, safety={safety_rate}%")
        print("  → Rebuild dataset (don't repeat training)")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
