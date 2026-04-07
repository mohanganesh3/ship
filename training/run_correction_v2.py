#!/usr/bin/env python3
"""Correction-v2 training: targeted repair from Boundary-v2 base.

Key design:
- Base: Boundary-v2/final (merged-and-unloaded)
- Fresh LoRA r=16, alpha=32
- 10% warmup + cosine decay
- 600 balanced correction samples
- Fastref eval with ORPO entry thresholds

Usage:
    CUDA_VISIBLE_DEVICES=3 python run_correction_v2.py [--dry-run] [--epochs 1.0]
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

PHASE = "CORRECTION_V2_1.7B"

# Paths
BOUNDARY_V2_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/boundary-v2-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/correction-v2-1.7b")
CORRECTION_DATASET = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/correction_v2_dataset.jsonl"
)

# GPU selection: set CUDA_VISIBLE_DEVICES externally before launching this script


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Correction-v2 training for 1.7B maritime model")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    return parser.parse_args()


def build_training_texts(tokenizer, dataset_path: Path) -> list[str]:
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


def structural_pass(answer: str, category: str, item: dict) -> bool:
    """Structural correctness check — tests what actually matters at the gate level."""
    from phase2_optionc_common import (
        strip_think, REGULATORY_MODAL_CUES, TRAP_REJECTION_CUES, escalation_alias_match
    )
    text = strip_think(normalize_space(answer))
    lowered = text.lower()
    esc_targets = item.get("escalation_targets", [])
    esc_hit = (not esc_targets) or any(
        any(escalation_alias_match(t, line) for line in text.splitlines())
        for t in esc_targets
    )
    trap_ok = True
    if category == "trap":
        trap_ok = any(c in lowered for c in TRAP_REJECTION_CUES)
    modal_ok = True
    if category == "regulatory":
        modal_ok = any(c in lowered for c in REGULATORY_MODAL_CUES)
    do_not_ok = True
    if item.get("do_not") and category in ("trap", "safety", "regulatory"):
        do_not_ok = "do not" in lowered or "must not" in lowered or "prohibited" in lowered
    return esc_hit and trap_ok and modal_ok and do_not_ok


def run_fastref_eval(model, tokenizer, benchmark_path: Path, n_per_category: int = 10) -> dict:
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
            if structural_pass(answer, category, item):
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

    gate_require_file(CORRECTION_DATASET, PHASE)
    gate_require_dir(BOUNDARY_V2_FINAL, PHASE)

    tokenizer = load_tokenizer()

    texts = build_training_texts(tokenizer, CORRECTION_DATASET)
    if len(texts) < 100:
        log_pipeline(f"{PHASE} FAIL — DATASET_GATE: correction dataset too small ({len(texts)})")
        raise SystemExit(1)
    log_pipeline(f"{PHASE} STATUS: {len(texts)} training texts prepared")

    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    log_pipeline(f"{PHASE} STATUS: {len(dataset)} tokenized samples")
    import torch
    torch.cuda.empty_cache()

    # Load model from Boundary-v2 base (merge-and-unload)
    log_pipeline(f"{PHASE} STATUS: Loading merged model from {BOUNDARY_V2_FINAL}")
    model = load_merged_model_from_adapter(BOUNDARY_V2_FINAL, PHASE)

    # Attach fresh LoRA
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
            f"r={args.lora_r} alpha={args.lora_alpha} lr={args.lr} epochs={args.epochs}"
        )
        print(f"\n✅ DRY RUN OK: {len(dataset)} samples, r={args.lora_r}, alpha={args.lora_alpha}")
        return

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        overwrite_output_dir=False,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=args.lr,
        warmup_ratio=0.10,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        fp16=True,
        bf16=False,
        gradient_checkpointing=True,
        logging_steps=5,
        logging_first_step=True,
        save_steps=100,
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
    write_chain_metadata(
        candidate_dir,
        resolve_adapter_chain(BOUNDARY_V2_FINAL, PHASE) + [candidate_dir],
        PHASE,
    )

    # Fastref eval
    log_pipeline(f"{PHASE} STATUS: Running fastref eval (10/category)")
    eval_model = load_merged_model_from_adapter(candidate_dir, PHASE)
    eval_model.eval()

    fastref = run_fastref_eval(eval_model, tokenizer, DEFAULT_BENCHMARK, n_per_category=10)

    log_pipeline(f"{PHASE} FASTREF RESULTS:")
    for cat, res in sorted(fastref.items()):
        log_pipeline(f"  {cat}: {res['passed']}/{res['tested']} ({res['rate']}%)")
        print(f"  {cat}: {res['passed']}/{res['tested']} ({res['rate']}%)")

    fastref_path = OUTPUT_DIR / "fastref_correction_v2.json"
    fastref_path.write_text(json.dumps(fastref, indent=2), encoding="utf-8")

    # ORPO entry thresholds
    thresholds = {
        "regulatory": 40, "procedural": 40, "troubleshooting": 35,
        "safety": 60, "trap": 60, "calculation": 35,
    }
    gate_pass = True
    for cat, min_rate in thresholds.items():
        actual = fastref.get(cat, {}).get("rate", 0)
        if actual < min_rate:
            log_pipeline(f"  ❌ {cat}: {actual}% < {min_rate}% threshold")
            gate_pass = False

    if gate_pass:
        final_dir = OUTPUT_DIR / "final"
        if final_dir.exists():
            shutil.rmtree(final_dir)
        candidate_dir.rename(final_dir)
        write_chain_metadata(
            final_dir,
            resolve_adapter_chain(BOUNDARY_V2_FINAL, PHASE) + [final_dir],
            PHASE,
        )
        log_pipeline(f"{PHASE} STATUS: COMPLETE → {final_dir}")
        log_pipeline(f"{PHASE} GATE: PASS — meets ORPO entry thresholds")
        print(f"\n✅ CORRECTION-V2 PASSED — ready for ORPO or final eval")
    else:
        log_pipeline(f"{PHASE} GATE: FAIL — below ORPO thresholds")
        print(f"\n❌ CORRECTION-V2 FAILED — build Correction-v3 with failure-only data")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
