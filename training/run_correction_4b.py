#!/usr/bin/env python3
"""SFT Correction Pass. CPU-only.

Hard rules:
- CPU-only fp32
- Must be run from .venv-train
- Must fail fast (gate) if required artifacts/data are missing
"""

import os, sys, json, time, random, logging
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("OMP_NUM_THREADS", "48")
os.environ.setdefault("MKL_NUM_THREADS", "48")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
torch.set_num_threads(48)

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType, PeftModel
from trl import SFTTrainer, SFTConfig
from torch.utils.data import Dataset

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
SFT2_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/sft2-4b/final")
CORRECTION_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/correction-4b")
CORRECTIONS_DATA = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_corrections_4b.jsonl")
BASE_MODEL = "/home/mohanganesh/ship/models/student-4b"

SYSTEM_PROMPT = """You are an expert maritime assistant with deep knowledge of vessel operations, safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. Answer questions only from your training knowledge. If a question is outside your knowledge or you cannot answer with confidence, say exactly: "I don't have sufficient information about this specific topic."
/no_think"""

def log_pipeline(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


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

def load_corrections():
    records = []
    if CORRECTIONS_DATA.exists():
        with open(CORRECTIONS_DATA) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records

def format_record(rec, tokenizer):
    q = rec.get("q", rec.get("question", ""))
    a = rec.get("a", rec.get("answer", ""))
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": q},
        {"role": "assistant", "content": a}
    ]
    try:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except:
        text = f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n<|im_start|>user\n{q}<|im_end|>\n<|im_start|>assistant\n{a}<|im_end|>"
    return {"text": text}

class SFTDataset(Dataset):
    def __init__(self, texts): self.texts = texts
    def __len__(self): return len(self.texts)
    def __getitem__(self, idx): return self.texts[idx]

def main():
    phase = "PHASE_3_CORRECTION_4B"
    ensure_venv_train(phase)
    log_pipeline(f"{phase} STATUS: STARTING.")

    gate_require_dir(SFT2_CHECKPOINT, phase)
    gate_require_file(CORRECTIONS_DATA, phase)
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None: tokenizer.pad_token = tokenizer.eos_token

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float32, device_map="cpu", trust_remote_code=True, low_cpu_mem_usage=True,
    )

    base_model = PeftModel.from_pretrained(base_model, str(SFT2_CHECKPOINT))
    base_model = base_model.merge_and_unload()

    base_model.enable_input_require_grads()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=32, lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, bias="none",
    )
    model = get_peft_model(base_model, lora_config)

    records = load_corrections()
    if len(records) < 1000:
        log_pipeline(f"{phase} STATUS: FAIL — GATE: corrections={len(records)} (need >=1000)")
        raise SystemExit(1)
    formatted = [format_record(r, tokenizer) for r in records]
    dataset = SFTDataset(formatted)

    CORRECTION_CHECKPOINT.mkdir(parents=True, exist_ok=True)
    training_args = SFTConfig(
        output_dir=str(CORRECTION_CHECKPOINT),
        num_train_epochs=1,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=5e-5,
        lr_scheduler_type="cosine",
        logging_steps=25,
        save_steps=200,
        save_total_limit=3,
        no_cuda=True, use_cpu=True, fp16=False, bf16=False,
        dataloader_num_workers=0,
        dataloader_pin_memory=False, report_to="none",
        neftune_noise_alpha=None,
        max_seq_length=512,
        dataset_text_field="text",
    )
    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)
    trainer.train()
    trainer.save_model(str(CORRECTION_CHECKPOINT / "final"))
    tokenizer.save_pretrained(str(CORRECTION_CHECKPOINT / "final"))
    log_pipeline(f"{phase} STATUS: COMPLETE.")

if __name__ == "__main__":
    main()
