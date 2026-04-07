#!/usr/bin/env python3
"""Local correction SFT pass for the 1.7B maritime model."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from transformers import Trainer, TrainingArguments

from phase2_optionc_common import (
    build_nothink_text,
    build_think_text,
    DEFAULT_CORRECTIONS_DATA,
    SupervisedDataCollator,
    attach_training_lora,
    ensure_cuda,
    ensure_venv_train,
    gate_require_file,
    gate_require_min_records,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    patch_trainer_rng_resume,
    read_jsonl,
    normalize_space,
    resolve_adapter_chain,
    resolve_resume_checkpoint,
    setup_logging,
    synthesize_reasoning,
    tokenize_texts,
    write_chain_metadata,
)

PHASE = "PHASE_3_LOCAL_CORRECTION_1.7B"
SFT2_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft2-1.7b/final")
BOUNDARY_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-boundary-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase3-local-correction-1.7b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local correction SFT for the 1.7B maritime branch.")
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)

    corrections_path = Path(os.environ.get("SHIP_CORRECTIONS_DATA", str(DEFAULT_CORRECTIONS_DATA)))
    base_adapter = Path(
        os.environ.get(
            "SHIP_CORRECTION_BASE",
            str(BOUNDARY_FINAL if (BOUNDARY_FINAL / "adapter_model.safetensors").exists() else SFT2_FINAL),
        )
    )
    output_dir = Path(os.environ.get("SHIP_CORRECTION_OUTPUT_DIR", str(OUTPUT_DIR)))
    gate_require_file(corrections_path, PHASE)
    gate_require_file(base_adapter / "adapter_model.safetensors", PHASE)

    records = read_jsonl(corrections_path)
    gate_require_min_records(records, 1, PHASE, "corrections")

    tokenizer = load_tokenizer()
    texts = []
    for record in records:
        question = record.get("q") or record.get("question") or ""
        answer = record.get("a") or record.get("answer") or ""
        if question and answer:
            category = normalize_space(record.get("category")).lower()
            if category in {"troubleshooting", "calculation"}:
                texts.append(build_think_text(tokenizer, question, answer, synthesize_reasoning(record, answer)))
            else:
                texts.append(build_nothink_text(tokenizer, question, answer))
    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    gate_require_min_records([{}] * len(dataset), 1, PHASE, "tokenized corrections")

    model = attach_training_lora(load_merged_model_from_adapter(base_adapter, PHASE))
    output_dir.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(output_dir)
    patch_trainer_rng_resume()

    if args.dry_run:
        log_pipeline(f"{PHASE} STATUS: DRY RUN OK records={len(records)} tokenized={len(dataset)} base_adapter={base_adapter} resume_from={resume_from}")
        return

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        overwrite_output_dir=False,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=5e-5,
        warmup_ratio=0.05,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        fp16=True,
        bf16=False,
        gradient_checkpointing=True,
        logging_steps=10,
        logging_first_step=True,
        save_steps=100,
        save_total_limit=2,
        dataloader_num_workers=0,
        dataloader_pin_memory=True,
        optim="adamw_torch",
        report_to="none",
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=dataset, data_collator=SupervisedDataCollator(tokenizer))
    log_pipeline(f"{PHASE} STATUS: TRAINING STARTED records={len(records)} base_adapter={base_adapter} resume_from={resume_from}")
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    write_chain_metadata(final_dir, resolve_adapter_chain(base_adapter, PHASE) + [final_dir], PHASE)
    log_pipeline(f"{PHASE} STATUS: COMPLETE final_dir={final_dir}")


if __name__ == "__main__":
    main()
