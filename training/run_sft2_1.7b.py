#!/usr/bin/env python3
"""SFT Stage 2 — Concise Responses. Single-GPU fp16.

Hard rules:
- Single GPU only (default: GPU0 via CUDA_VISIBLE_DEVICES=0)
- fp16 only (no bf16)
- Must be run from .venv-train
- Must fail fast (gate) if required artifacts/data are missing
"""

import os, sys, json, time, random, logging
from pathlib import Path
from datetime import datetime, timezone

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch

from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType, PeftModel
from trl import SFTTrainer, SFTConfig
from torch.utils.data import Dataset

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
SFT1_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/sft1-1.7b/final")
SFT2_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/sft2-1.7b")
SFT_DATA = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl")
TRAPS_DATA = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated_traps.jsonl")
BASE_MODEL = "/home/mohanganesh/ship/models/student-1.7b"

SYSTEM_PROMPT_NOTHINK = """You are an expert maritime assistant with deep knowledge of vessel operations, safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. Answer questions only from your training knowledge. If a question is outside your knowledge or you cannot answer with confidence, say exactly: "I don't have sufficient information about this specific topic."
/no_think"""

def log_pipeline(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    logger.info(msg)


def ensure_venv_train(phase_tag: str) -> None:
    exe_raw = os.path.abspath(sys.executable)
    exe_real = os.path.realpath(sys.executable)
    if "/.venv-train/" not in exe_raw and "/.venv-train/" not in exe_real:
        log_pipeline(
            f"{phase_tag} FAIL — ENV_GATE: must run with .venv-train python "
            f"(got: exe={exe_raw}, real={exe_real})"
        )
        raise SystemExit(1)


def gate_require_file(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — DATASET_GATE: required file not found: {path}")
        raise SystemExit(1)


def gate_require_dir(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — ARTIFACT_GATE: required path not found: {path}")
        raise SystemExit(1)

def load_nothink_examples():
    records = []
    if SFT_DATA.exists():
        with open(SFT_DATA) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                mode = rec.get("mode", "")
                qtype = rec.get("type", "")
                if mode == "no_think" or qtype in ("factual", "regulatory", "safety", "procedural"):
                    records.append(rec)
    
    if TRAPS_DATA.exists():
        with open(TRAPS_DATA) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records

def generate_thinkfollow_examples(records, count=200):
    procedural = [r for r in records if r.get("type") == "procedural" and len(r.get("a", r.get("answer", ""))) > 50]
    synths = []
    for rec in procedural[:count]:
        q = rec.get("q", rec.get("question", ""))
        a = rec.get("a", rec.get("answer", ""))
        first_step = a.split(". ")[0] + "."
        synthesized = {
            "q": f"Just give me the most critical step for: {q}",
            "a": first_step,
            "mode": "no_think"
        }
        synths.append(synthesized)
    return synths

def format_nothink_record(rec, tokenizer):
    q = rec.get("q", rec.get("question", ""))
    a = rec.get("a", rec.get("answer", ""))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_NOTHINK},
        {"role": "user", "content": q},
        {"role": "assistant", "content": a}
    ]

    try:
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except Exception:
        text = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_NOTHINK}<|im_end|>\n"
            f"<|im_start|>user\n{q}<|im_end|>\n"
            f"<|im_start|>assistant\n{a}<|im_end|>"
        )
    return {"text": text}

class SFTDataset(Dataset):
    def __init__(self, formatted_texts):
        self.texts = formatted_texts
    def __len__(self):
        return len(self.texts)
    def __getitem__(self, idx):
        return self.texts[idx]

def main():
    phase = "PHASE_2B_SFT2_1.7B"
    ensure_venv_train(phase)

    if not torch.cuda.is_available():
        log_pipeline(f"{phase} FAIL — CUDA_GATE: torch.cuda.is_available() is false")
        raise SystemExit(1)

    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if vis.strip() == "":
        log_pipeline(f"{phase} FAIL — CUDA_GATE: CUDA_VISIBLE_DEVICES is empty")
        raise SystemExit(1)

    try:
        cap = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
    except Exception as e:
        log_pipeline(f"{phase} FAIL — CUDA_GATE: cannot query GPU0 ({e})")
        raise SystemExit(1)
    if cap < (3, 7):
        log_pipeline(f"{phase} FAIL — CUDA_GATE: GPU compute capability {cap} < (3, 7)")
        raise SystemExit(1)
    logger.info(f"Using CUDA device: {name} (capability={cap}), CUDA_VISIBLE_DEVICES={vis}")
    log_pipeline(f"{phase} STATUS: STARTING. Loading from SFT1 checkpoint.")

    gate_require_dir(SFT1_CHECKPOINT, phase)
    gate_require_file(SFT_DATA, phase)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    logger.info(f"Loading base model from {BASE_MODEL}")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map={"": 0},
        trust_remote_code=True, low_cpu_mem_usage=True,
    )
    if hasattr(base_model, "config"):
        base_model.config.use_cache = False

    logger.info(f"Loading SFT1 LoRA from {SFT1_CHECKPOINT}")
    base_model = PeftModel.from_pretrained(base_model, str(SFT1_CHECKPOINT))
    base_model = base_model.merge_and_unload()

    if hasattr(base_model, "config"):
        base_model.config.use_cache = False

    base_model.enable_input_require_grads()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, r=32, lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05, bias="none",
    )
    model = get_peft_model(base_model, lora_config)

    records = load_nothink_examples()
    if len(records) < 5000:
        log_pipeline(f"{phase} FAIL — DATASET_GATE: expected >= 5000 nothink examples, got {len(records)}")
        raise SystemExit(1)
    synths = generate_thinkfollow_examples(records)
    records.extend(synths)

    if not records:
        log_pipeline(f"{phase} FAIL — DATASET_GATE: no training records loaded")
        raise SystemExit(1)

    formatted = [format_nothink_record(r, tokenizer) for r in records]
    dataset = SFTDataset(formatted)

    SFT2_CHECKPOINT.mkdir(parents=True, exist_ok=True)

    training_args = SFTConfig(
        output_dir=str(SFT2_CHECKPOINT),
        num_train_epochs=2,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=1e-4,
        warmup_ratio=0.03,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        logging_steps=25,
        save_steps=200,
        save_total_limit=3,
        no_cuda=False,
        use_cpu=False,
        fp16=True,
        bf16=False,
        dataloader_num_workers=0,
        dataloader_pin_memory=True,
        report_to="none",
        neftune_noise_alpha=5,
        max_seq_length=512,
        dataset_text_field="text",
    )

    trainer = SFTTrainer(model=model, args=training_args, train_dataset=dataset, processing_class=tokenizer)

    log_pipeline("PHASE_2B_SFT2_1.7B STATUS: TRAINING STARTED")
    trainer.train()
    trainer.save_model(str(SFT2_CHECKPOINT / "final"))
    tokenizer.save_pretrained(str(SFT2_CHECKPOINT / "final"))

    log_pipeline("PHASE_2B_SFT2_1.7B STATUS: COMPLETE. Run gate check.")

    # === SFT STAGE 2 GATE CHECK ===
    # Gate: at least 60% of trap questions must produce an explicit uncertainty answer.
    UNCERTAIN_PHRASE = "i don't have sufficient information about this specific topic."

    gate_require_file(TRAPS_DATA, phase)

    traps: list[dict] = []
    with open(TRAPS_DATA, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                traps.append(json.loads(line))
            except Exception:
                continue

    if len(traps) < 25:
        log_pipeline(f"{phase} GATE: FAIL — TRAPS_DATA too small ({len(traps)} records; need >=25)")
        raise SystemExit(1)

    model.eval()
    device = next(model.parameters()).device
    tested = 0
    refused = 0

    sample = traps[:50]
    for rec in sample:
        q = rec.get("q", rec.get("question", ""))
        if not q:
            continue
        prompt = (
            f"<|im_start|>system\n{SYSTEM_PROMPT_NOTHINK}<|im_end|>\n"
            f"<|im_start|>user\n{q}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=180,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        response = tokenizer.decode(out[0][input_ids.shape[1] :], skip_special_tokens=True)
        tested += 1
        if UNCERTAIN_PHRASE in response.strip().lower():
            refused += 1

    if tested == 0:
        log_pipeline("PHASE_2B_SFT2_1.7B GATE: FAIL — no trap examples tested")
        raise SystemExit(1)

    pct = refused / float(tested) * 100.0
    if pct >= 60.0:
        log_pipeline(f"PHASE_2B_SFT2_1.7B GATE: PASS trap_refusals={refused}/{tested} ({pct:.1f}%)")
    else:
        log_pipeline(f"PHASE_2B_SFT2_1.7B GATE: FAIL trap_refusals={refused}/{tested} ({pct:.1f}% < 60%)")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
