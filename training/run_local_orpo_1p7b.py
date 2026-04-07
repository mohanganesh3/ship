#!/usr/bin/env python3
"""Local ORPO run for the 1.7B maritime model."""

from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path

from datasets import Dataset as HFDataset
from trl import ORPOConfig, ORPOTrainer

from phase2_optionc_common import (
    DEFAULT_ORPO_DATA,
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
    resolve_adapter_chain,
    resolve_resume_checkpoint,
    setup_logging,
    write_chain_metadata,
)

PHASE = "PHASE_4_LOCAL_ORPO_1.7B"
CORRECTION_FINAL = Path("/home/mohanganesh/ship/training/checkpoints/phase3-local-correction-1.7b/final")
OUTPUT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase4-local-orpo-1.7b")
SMOKE_DIR = Path("/home/mohanganesh/ship/training/checkpoints/phase4-local-orpo-smoke-1.7b")


class PatchedORPOTrainer(ORPOTrainer):
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Fixed signature for Transformers 4.47+ compatibility."""
        return super().compute_loss(model, inputs, return_outputs=return_outputs)

    def log(self, logs, start_time=None, **kwargs):
        """Fixed signature for Transformers 4.47+ compatibility."""
        return super().log(logs)

    def get_batch_samples(self, *args, **kwargs):
        """Fixed signature collision between Trainer and ORPOTrainer."""
        # Detect if called by Trainer loop (3 positional args beyond self)
        if len(args) >= 2 or "epoch_iterator" in kwargs:
            from transformers import Trainer
            return Trainer.get_batch_samples(self, *args, **kwargs)
        return super().get_batch_samples(*args, **kwargs)

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None, **kwargs):
        """Fixed signature for Transformers 4.47+ compatibility."""
        return super().prediction_step(model, inputs, prediction_loss_only, ignore_keys=ignore_keys)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local ORPO for the 1.7B maritime branch.")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--data", type=Path, default=DEFAULT_ORPO_DATA)
    parser.add_argument("--base-adapter", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--smoke-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()

    ensure_venv_train(PHASE)
    ensure_cuda(PHASE)
    gate_require_file(args.data, PHASE)

    base_adapter = args.base_adapter or Path(os.environ.get("SHIP_ORPO_BASE", str(CORRECTION_FINAL)))
    output_dir = args.output_dir or Path(os.environ.get("SHIP_ORPO_OUTPUT_DIR", str(OUTPUT_DIR)))
    smoke_dir = args.smoke_dir or Path(os.environ.get("SHIP_ORPO_SMOKE_DIR", str(SMOKE_DIR)))
    gate_require_file(base_adapter / "adapter_model.safetensors", PHASE)

    pairs = read_jsonl(args.data)
    minimum = 16 if args.smoke else 300
    gate_require_min_records(pairs, minimum, PHASE, "orpo_pairs")
    if args.smoke:
        pairs = pairs[:16]

    dataset = HFDataset.from_list(
        [{"prompt": pair["prompt"], "chosen": pair["chosen"], "rejected": pair["rejected"]} for pair in pairs]
    )

    tokenizer = load_tokenizer()
    correction_model = attach_training_lora(load_merged_model_from_adapter(base_adapter, PHASE))

    output_dir = smoke_dir if args.smoke else output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    resume_from = resolve_resume_checkpoint(output_dir)
    patch_trainer_rng_resume()

    config = ORPOConfig(
        output_dir=str(output_dir),
        num_train_epochs=1.0,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=16,
        learning_rate=5e-5,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        beta=0.1,
        logging_steps=10,
        save_steps=100,
        save_total_limit=2,
        fp16=True,
        bf16=False,
        report_to="none",
        max_length=512,
        max_prompt_length=256,
        remove_unused_columns=False,
    )
    trainer_kwargs = {
        "model": correction_model,
        "args": config,
        "train_dataset": dataset,
    }
    signature = inspect.signature(ORPOTrainer.__init__)
    if "tokenizer" in signature.parameters:
        trainer_kwargs["tokenizer"] = tokenizer
    elif "processing_class" in signature.parameters:
        trainer_kwargs["processing_class"] = tokenizer
    trainer = PatchedORPOTrainer(**trainer_kwargs)

    log_pipeline(f"{PHASE} STATUS: TRAINING STARTED smoke={args.smoke} pairs={len(pairs)} resume_from={resume_from}")
    trainer.train(resume_from_checkpoint=str(resume_from) if resume_from is not None else None)

    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    if not args.smoke:
        write_chain_metadata(final_dir, resolve_adapter_chain(base_adapter, PHASE) + [final_dir], PHASE)
    log_pipeline(f"{PHASE} STATUS: COMPLETE smoke={args.smoke} final_dir={final_dir}")


if __name__ == "__main__":
    main()
