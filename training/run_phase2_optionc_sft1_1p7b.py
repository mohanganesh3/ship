#!/usr/bin/env python3
"""April 10 Option C Stage 1 trainer for the 1.7B maritime model."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

import torch
from transformers import Trainer, TrainingArguments

from phase2_optionc_common import (
    DEFAULT_OPTIONC_DATA,
    DEFAULT_REASONING_REPLAY,
    SupervisedDataCollator,
    attach_training_lora,
    ensure_cuda,
    ensure_venv_train,
    gate_require_file,
    load_cpt_merged_model,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    patch_trainer_rng_resume,
    prepare_stage1_texts,
    resolve_cpt_checkpoint,
    resolve_resume_checkpoint,
    setup_logging,
    stage1_optionc_records,
    stage1_replay_records,
    score_response,
    tokenize_texts,
    write_chain_metadata,
)

PHASE = "PHASE_2A_OPTIONC_SFT1_1.7B"
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft1-1.7b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Option C reasoning-first SFT for the 1.7B maritime model.")
    parser.add_argument("--epochs", type=float, default=1.0, help="Number of training epochs.")
    parser.add_argument("--max-length", type=int, default=512, help="Maximum sequence length.")
    parser.add_argument("--max-records", type=int, default=None, help="Optional cap for debugging.")
    parser.add_argument("--dry-run", action="store_true", help="Load data and model, then exit before training.")
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)

    optionc_data = Path(os.environ.get("SHIP_SFT_DATA", str(DEFAULT_OPTIONC_DATA)))
    replay_data = Path(os.environ.get("SHIP_SFT_REPLAY_DATA", str(DEFAULT_REASONING_REPLAY)))

    gate_require_file(optionc_data, PHASE)
    log_pipeline(f"{PHASE} STATUS: STARTING from CPT with Option C reasoning data")

    tokenizer = load_tokenizer()
    optionc_records = stage1_optionc_records(optionc_data)
    replay_records = stage1_replay_records(replay_data)
    texts = prepare_stage1_texts(tokenizer, optionc_records, replay_records, args.max_records)

    if len(texts) < 1500:
        log_pipeline(f"{PHASE} FAIL — DATASET_GATE: need >=1500 reasoning texts, got {len(texts)}")
        raise SystemExit(1)

    dataset = tokenize_texts(tokenizer, texts, max_length=args.max_length)
    if len(dataset) < 1500:
        log_pipeline(f"{PHASE} FAIL — TOKENIZE_GATE: tokenized dataset too small ({len(dataset)})")
        raise SystemExit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(OUTPUT_DIR)
    patch_trainer_rng_resume()
    model = attach_training_lora(load_cpt_merged_model(PHASE))

    if args.dry_run:
        log_pipeline(
            f"{PHASE} STATUS: DRY RUN OK optionc_records={len(optionc_records)} replay_records={len(replay_records)} tokenized={len(dataset)} resume_from={resume_from}"
        )
        return

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        overwrite_output_dir=False,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=1e-4,
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
        f"{PHASE} STATUS: TRAINING STARTED dataset={len(dataset)} optionc={len(optionc_records)} replay={len(replay_records)} resume_from={resume_from}"
    )
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)

    candidate_dir = OUTPUT_DIR / "candidate"
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(candidate_dir))
    tokenizer.save_pretrained(str(candidate_dir))
    write_chain_metadata(candidate_dir, [resolve_cpt_checkpoint(PHASE), candidate_dir], PHASE)

    eval_records = [record for record in optionc_records if record.get("mode") == "think"][:50]
    if len(eval_records) < 50:
        eval_records = optionc_records[:50]

    eval_model = load_merged_model_from_adapter(candidate_dir, PHASE)
    eval_model.eval()
    device = next(eval_model.parameters()).device
    passed = 0
    tested = 0
    for record in eval_records:
        question = record.get("q") or record.get("question") or ""
        if not question:
            continue
        prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": "You are an expert maritime assistant for shipboard safety, regulation, troubleshooting, and engineering operations.\nUse explicit reasoning before the final answer.\n/think"},
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
            escalation_targets=[],
            category="troubleshooting",
        )
        if "<think>" in response and "</think>" in response and score["trap_pass"]:
            passed += 1
        tested += 1

    if tested == 0 or passed / tested < 0.7:
        log_pipeline(f"{PHASE} GATE: FAIL reasoning_trace={passed}/{tested}")
        shutil.rmtree(candidate_dir, ignore_errors=True)
        raise SystemExit(1)

    final_dir = OUTPUT_DIR / "final"
    if final_dir.exists():
        shutil.rmtree(final_dir)
    candidate_dir.rename(final_dir)
    write_chain_metadata(final_dir, [resolve_cpt_checkpoint(PHASE), final_dir], PHASE)
    log_pipeline(f"{PHASE} STATUS: COMPLETE final_dir={final_dir}")
    log_pipeline(f"{PHASE} GATE: PASS reasoning_trace={passed}/{tested}")


if __name__ == "__main__":
    main()
