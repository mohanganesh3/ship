#!/usr/bin/env python3
"""April 10 Option C Stage 2 trainer for the 1.7B maritime model."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import torch
from transformers import Trainer, TrainingArguments

from phase2_optionc_common import (
    DEFAULT_OPTIONC_DATA,
    DEFAULT_OPTIONC_TRAPS,
    SupervisedDataCollator,
    attach_training_lora,
    ensure_cuda,
    ensure_venv_train,
    gate_require_file,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    patch_trainer_rng_resume,
    prepare_stage2_texts,
    resolve_adapter_chain,
    resolve_resume_checkpoint,
    score_response,
    setup_logging,
    stage2_nothink_records,
    stage2_trap_records,
    synthesize_thinkfollow,
    trap_response_passes,
    tokenize_texts,
    write_chain_metadata,
)

PHASE = "PHASE_2B_OPTIONC_SFT2_1.7B"
SFT1_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft1-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft2-1.7b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Option C concise/trap SFT for the 1.7B maritime model.")
    parser.add_argument("--epochs", type=float, default=1.0, help="Number of training epochs.")
    parser.add_argument("--max-length", type=int, default=512, help="Maximum sequence length.")
    parser.add_argument("--trap-multiplier", type=int, default=2, help="Oversampling factor for trap examples.")
    parser.add_argument("--max-records", type=int, default=None, help="Optional cap for debugging.")
    parser.add_argument("--dry-run", action="store_true", help="Load data and model, then exit before training.")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)

    optionc_data = Path(os.environ.get("SHIP_SFT_DATA", str(DEFAULT_OPTIONC_DATA)))
    traps_data = Path(os.environ.get("SHIP_SFT_TRAPS", str(DEFAULT_OPTIONC_TRAPS)))

    gate_require_file(optionc_data, PHASE)
    gate_require_file(traps_data, PHASE)
    gate_require_file(SFT1_FINAL / "adapter_model.safetensors", PHASE)

    log_pipeline(f"{PHASE} STATUS: STARTING from Stage 1 checkpoint")

    tokenizer = load_tokenizer()
    nothink_records = stage2_nothink_records(optionc_data)
    trap_records = stage2_trap_records(traps_data, multiplier=args.trap_multiplier)
    thinkfollow_records = synthesize_thinkfollow(nothink_records, count=200)
    texts = prepare_stage2_texts(tokenizer, nothink_records, trap_records, thinkfollow_records, args.max_records)

    if len(texts) < 4000:
        log_pipeline(f"{PHASE} FAIL — DATASET_GATE: need >=4000 concise texts, got {len(texts)}")
        raise SystemExit(1)

    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    if len(dataset) < 4000:
        log_pipeline(f"{PHASE} FAIL — TOKENIZE_GATE: tokenized dataset too small ({len(dataset)})")
        raise SystemExit(1)

    model = attach_training_lora(load_merged_model_from_adapter(SFT1_FINAL, PHASE))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(OUTPUT_DIR)
    patch_trainer_rng_resume()

    if args.dry_run:
        log_pipeline(
            f"{PHASE} STATUS: DRY RUN OK nothink={len(nothink_records)} traps={len(trap_records)} thinkfollow={len(thinkfollow_records)} tokenized={len(dataset)} resume_from={resume_from}"
        )
        return

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        overwrite_output_dir=False,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=8e-5,
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

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=SupervisedDataCollator(tokenizer),
    )

    log_pipeline(
        f"{PHASE} STATUS: TRAINING STARTED dataset={len(dataset)} nothink={len(nothink_records)} traps={len(trap_records)} thinkfollow={len(thinkfollow_records)} resume_from={resume_from}"
    )
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)

    candidate_dir = OUTPUT_DIR / "candidate"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(candidate_dir))
    tokenizer.save_pretrained(str(candidate_dir))
    write_chain_metadata(candidate_dir, resolve_adapter_chain(SFT1_FINAL, PHASE) + [candidate_dir], PHASE)

    eval_model = load_merged_model_from_adapter(candidate_dir, PHASE)
    eval_model.eval()
    device = next(eval_model.parameters()).device
    eval_records = trap_records[:50]
    tested = 0
    passed = 0
    missing_escalation = 0
    for record in eval_records:
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
        score = score_response(
            response,
            required_checks=[],
            forbidden_checks=[],
            escalation_targets=record.get("escalation_targets", []),
            category="trap",
        )
        if trap_response_passes(response):
            passed += 1
        if record.get("escalation_targets") and score["escalation_hit_count"] == 0:
            missing_escalation += 1
        tested += 1
    if tested == 0 or passed / tested < 0.8:
        log_pipeline(f"{PHASE} GATE: FAIL trap_pass={passed}/{tested} missing_escalation={missing_escalation}")
        shutil.rmtree(candidate_dir, ignore_errors=True)
        raise SystemExit(1)
    final_dir = OUTPUT_DIR / "final"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    candidate_dir.rename(final_dir)
    write_chain_metadata(final_dir, resolve_adapter_chain(SFT1_FINAL, PHASE) + [final_dir], PHASE)
    log_pipeline(f"{PHASE} STATUS: COMPLETE final_dir={final_dir}")
    log_pipeline(f"{PHASE} GATE: PASS trap_pass={passed}/{tested} missing_escalation={missing_escalation}")


if __name__ == "__main__":
    main()
