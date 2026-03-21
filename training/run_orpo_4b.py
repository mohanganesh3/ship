#!/usr/bin/env python3
"""ORPO Preference Polish — CPU-only, 1 epoch, beta=0.1.

Hard rules:
- CPU-only fp32
- Must be run from .venv-train
- Must fail fast (gate) if required artifacts/data are missing
"""

import os, json, sys, logging, time, re
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("OMP_NUM_THREADS", "48")
os.environ.setdefault("MKL_NUM_THREADS", "48")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
torch.set_num_threads(48)

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import get_peft_model, LoraConfig, TaskType, PeftModel
from trl import ORPOTrainer, ORPOConfig
from datasets import Dataset as HFDataset

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
CORRECTION_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/correction-4b/final")
ORPO_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/orpo-4b")
BASE_MODEL = "/home/mohanganesh/ship/models/student-4b"
ORPO_DATA = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/orpo_pairs_4b.jsonl")
SFT_DATA = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl")

def log_pipeline(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    logger.info(msg)


def ensure_venv_train(phase_tag: str) -> None:
    exe = os.path.realpath(sys.executable)
    if "/.venv-train/" not in exe:
        log_pipeline(f"{phase_tag} FAIL — ENV_GATE: must run with .venv-train python (got: {exe})")
        raise SystemExit(1)


def gate_require_file(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — DATASET_GATE: required file not found: {path}")
        raise SystemExit(1)


def gate_require_dir(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — ARTIFACT_GATE: required path not found: {path}")
        raise SystemExit(1)

def load_orpo_pairs():
    pairs = []
    if ORPO_DATA.exists():
        with open(ORPO_DATA) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    pairs.append(json.loads(line))
                except Exception:
                    pass

    logger.info(f"Loaded {len(pairs)} on-policy ORPO pairs")

    # Augment with synthetic R1/R2/R3/R4 pairs if fewer than 1000
    if len(pairs) < 1000 and SFT_DATA.exists():
        sft_records = []
        with open(SFT_DATA) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    sft_records.append(json.loads(line))
                except Exception:
                    pass

        # R1: regulatory precision (shall → should)
        reg_records = [r for r in sft_records if r.get("type") == "regulatory"][:500]
        for rec in reg_records:
            q = rec.get("q", "")
            chosen = rec.get("a", "")
            if "shall" in chosen:
                rejected = chosen.replace("shall", "should", 1)
                pairs.append({
                    "prompt": q, "chosen": chosen, "rejected": rejected,
                    "rejection_type": "R1_regulatory", "risk_tag": "regulatory"
                })

        # R2: missing safety step (remove first sentence from safety answers)
        safety_records = [r for r in sft_records if r.get("type") == "safety"][:300]
        for rec in safety_records:
            q = rec.get("q", "")
            chosen = rec.get("a", "")
            sentences = [s.strip() for s in chosen.split(".") if s.strip()]
            if len(sentences) > 2:
                # Remove the first safety step
                rejected = ". ".join(sentences[1:]) + "."
                pairs.append({
                    "prompt": q, "chosen": chosen, "rejected": rejected,
                    "rejection_type": "R2_missing_safety_step", "risk_tag": "safety_critical"
                })

        # R3: unit error (kPa → bar, swap units in calculation answers)
        calc_records = [r for r in sft_records if r.get("type") == "calculation"][:200]
        for rec in calc_records:
            q = rec.get("q", "")
            chosen = rec.get("a", "")
            if "kPa" in chosen:
                rejected = chosen.replace("kPa", "bar")
                pairs.append({
                    "prompt": q, "chosen": chosen, "rejected": rejected,
                    "rejection_type": "R3_unit_error", "risk_tag": "maintenance"
                })

        logger.info(f"After augmentation: {len(pairs)} ORPO pairs total")

    return pairs

def main():
    phase = "PHASE_4_ORPO_4B"
    ensure_venv_train(phase)
    log_pipeline(f"{phase} STATUS: STARTING. beta=0.1, 1 epoch, CPU-only")

    gate_require_dir(CORRECTION_CHECKPOINT, phase)
    gate_require_file(ORPO_DATA, phase)

    pairs = load_orpo_pairs()
    if len(pairs) < 500:
        log_pipeline(f"{phase} STATUS: FAIL — GATE: only {len(pairs)} pairs, need ≥500")
        raise SystemExit(1)

    # Format for ORPOTrainer (needs 'prompt', 'chosen', 'rejected')
    formatted_pairs = []
    for p in pairs:
        formatted_pairs.append({
            "prompt": p.get("prompt", ""),
            "chosen": p.get("chosen", ""),
            "rejected": p.get("rejected", ""),
        })

    dataset = HFDataset.from_list(formatted_pairs)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float32, device_map="cpu",
        trust_remote_code=True, low_cpu_mem_usage=True
    )

    model = PeftModel.from_pretrained(base, str(CORRECTION_CHECKPOINT))
    model = model.merge_and_unload()
    logger.info("Correction LoRA merged.")

    model.enable_input_require_grads()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=32, lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.0, bias="none",
    )
    model = get_peft_model(model, lora_config)

    ORPO_CHECKPOINT.mkdir(parents=True, exist_ok=True)

    orpo_config = ORPOConfig(
        output_dir=str(ORPO_CHECKPOINT),
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=8e-6,
        warmup_steps=50,
        lr_scheduler_type="cosine",
        beta=0.1,           # ORPO lambda — do not increase
        logging_steps=25,
        save_steps=200,
        save_total_limit=2,
        no_cuda=True,
        use_cpu=True,
        fp16=False,
        bf16=False,
        dataloader_num_workers=0,
        dataloader_pin_memory=False,
        report_to="none",
        max_length=512,
        max_prompt_length=256,
        remove_unused_columns=False,
    )

    trainer = ORPOTrainer(
        model=model,
        args=orpo_config,
        train_dataset=dataset,
        processing_class=tokenizer,
    )

    log_pipeline("PHASE_4_ORPO_4B STATUS: TRAINING STARTED")

    # Watch for beta collapse during training
    # ORPOTrainer logs rewards/chosen and rewards/rejected
    # If rewards/rejected < -2 in first 100 steps, this is a red flag
    # We monitor the log file for this

    trainer.train()

    trainer.save_model(str(ORPO_CHECKPOINT / "final"))
    tokenizer.save_pretrained(str(ORPO_CHECKPOINT / "final"))

    log_pipeline("PHASE_4_ORPO_4B STATUS: COMPLETE. Run gate check now.")

if __name__ == "__main__":
    main()
