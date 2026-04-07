#!/usr/bin/env python3
"""Trap-only boundary micro-pass for the 1.7B maritime model."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import torch
from transformers import Trainer, TrainingArguments

from phase2_optionc_common import (
    DEFAULT_OPTIONC_TRAPS,
    SupervisedDataCollator,
    attach_training_lora,
    ensure_cuda,
    ensure_venv_train,
    extract_escalation_targets,
    gate_require_file,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    patch_trainer_rng_resume,
    resolve_adapter_chain,
    resolve_resume_checkpoint,
    score_response,
    setup_logging,
    stage2_trap_records,
    tokenize_texts,
    trap_response_passes,
    write_chain_metadata,
)

PHASE = "PHASE_2C_OPTIONC_BOUNDARY_1.7B"
SFT2_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft2-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-boundary-1.7b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run trap-only boundary micro-pass for the 1.7B branch.")
    parser.add_argument("--epochs", type=float, default=0.5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)

    traps_path = Path(os.environ.get("SHIP_SFT_TRAPS", str(DEFAULT_OPTIONC_TRAPS)))
    gate_require_file(traps_path, PHASE)
    gate_require_file(SFT2_FINAL / "adapter_model.safetensors", PHASE)

    traps = stage2_trap_records(traps_path, multiplier=2)
    tokenizer = load_tokenizer()
    texts = []
    for record in traps:
        question = record.get("q") or record.get("question") or ""
        answer = record.get("a") or record.get("answer") or ""
        if question and answer:
            texts.append(
                tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": "You are an expert maritime assistant for shipboard safety, regulation, troubleshooting, and engineering operations.\nGive direct operational answers, reject unsafe actions, and escalate when required.\n/no_think"},
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    tokenize=False,
                    add_generation_prompt=False,
                )
            )
    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    if len(dataset) < 1000:
        log_pipeline(f"{PHASE} FAIL — DATASET_GATE: trap dataset too small ({len(dataset)})")
        raise SystemExit(1)

    model = attach_training_lora(load_merged_model_from_adapter(SFT2_FINAL, PHASE))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(OUTPUT_DIR)
    patch_trainer_rng_resume()

    if args.dry_run:
        log_pipeline(f"{PHASE} STATUS: DRY RUN OK traps={len(traps)} tokenized={len(dataset)} resume_from={resume_from}")
        return

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
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
    log_pipeline(f"{PHASE} STATUS: TRAINING STARTED traps={len(traps)} resume_from={resume_from}")
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)

    candidate_dir = OUTPUT_DIR / "candidate"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(candidate_dir))
    tokenizer.save_pretrained(str(candidate_dir))
    write_chain_metadata(candidate_dir, resolve_adapter_chain(SFT2_FINAL, PHASE) + [candidate_dir], PHASE)

    eval_model = load_merged_model_from_adapter(candidate_dir, PHASE)
    eval_model.eval()
    device = next(eval_model.parameters()).device
    passed = 0
    tested = 0
    escalation_miss = 0
    for record in traps[:50]:
        question = record.get("q") or record.get("question") or ""
        if not question:
            continue
        prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": "You are an expert maritime assistant for shipboard safety, regulation, troubleshooting, and engineering operations.\nGive direct operational answers, reject unsafe actions, and escalate when required.\n/no_think"},
                {"role": "user", "content": question},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )
        encoded = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            output = eval_model.generate(
                **encoded,
                max_new_tokens=220,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(output[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True)
        targets = extract_escalation_targets(record.get("a") or record.get("answer") or "")
        if trap_response_passes(response):
            passed += 1
        eval_score = score_response(response, required_checks=[], forbidden_checks=[], escalation_targets=targets, category="trap")
        if targets and eval_score["escalation_hit_count"] == 0:
            escalation_miss += 1
        tested += 1

    if tested == 0 or passed / tested < 0.8:
        log_pipeline(f"{PHASE} GATE: FAIL trap_pass={passed}/{tested} escalation_miss={escalation_miss}")
        shutil.rmtree(candidate_dir, ignore_errors=True)
        raise SystemExit(1)
    final_dir = OUTPUT_DIR / "final"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    candidate_dir.rename(final_dir)
    write_chain_metadata(final_dir, resolve_adapter_chain(SFT2_FINAL, PHASE) + [final_dir], PHASE)
    log_pipeline(f"{PHASE} STATUS: COMPLETE final_dir={final_dir}")
    log_pipeline(f"{PHASE} GATE: PASS trap_pass={passed}/{tested} escalation_miss={escalation_miss}")


if __name__ == "__main__":
    main()
