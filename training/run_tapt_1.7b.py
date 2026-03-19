#!/usr/bin/env python3
"""TAPT for Qwen3-1.7B: 1 epoch on chunks.jsonl, LR=6e-6, GPU 0

Task-Adaptive Pretraining (TAPT) familiarizes the model with the exact text style
it will see during SFT. Runs on the raw maritime chunk texts for 1 epoch.

Loads from the best CPT checkpoint and saves merged weights for SFT to load.
"""
import os
import json
import logging
import torch
from pathlib import Path
from datetime import datetime, timezone

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import get_peft_model, LoraConfig, TaskType, PeftModel
from torch.utils.data import Dataset

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

BASE_MODEL = "/home/mohanganesh/ship/models/student-1.7b"
CHUNKS_FILE = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/chunks.jsonl")
CPT_CHECKPOINT_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/cpt-1.7b")
TAPT_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/tapt-1.7b")
PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
PPL_LOG = Path("/home/mohanganesh/ship/logs/cpt_perplexity_1.7b.jsonl")


def log_pipeline(msg: str):
    """Log to both console and pipeline execution log."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(PIPELINE_LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    logger.info(msg)


def find_best_cpt_checkpoint() -> str | None:
    """Find the best CPT checkpoint based on perplexity logs."""
    # Prefer final checkpoint if it exists
    final_dir = CPT_CHECKPOINT_ROOT / "final"
    if final_dir.exists() and (final_dir / "adapter_model.safetensors").exists():
        logger.info(f"Using final CPT checkpoint: {final_dir}")
        return str(final_dir)
    
    if not CPT_CHECKPOINT_ROOT.exists():
        logger.error(f"CPT checkpoint root not found: {CPT_CHECKPOINT_ROOT}")
        return None
    
    # Find all numbered checkpoints
    checkpoints = sorted(
        [d for d in CPT_CHECKPOINT_ROOT.iterdir() 
         if d.is_dir() and d.name.startswith("checkpoint-")],
        key=lambda d: int(d.name.split("-")[1])
    )
    
    if not checkpoints:
        logger.error("No CPT checkpoints found")
        return None
    
    # Try to find best PPL checkpoint from logs
    if PPL_LOG.exists():
        try:
            entries = [json.loads(l) for l in PPL_LOG.read_text().splitlines() if l.strip()]
            if entries:
                best = min(entries, key=lambda e: e.get("maritime_ppl", float('inf')))
                best_step = best.get("step", 0)
                if best_step > 0:
                    # Find nearest checkpoint to best step
                    nearest = min(checkpoints, 
                                  key=lambda d: abs(int(d.name.split("-")[1]) - best_step))
                    logger.info(f"Using checkpoint {nearest.name} (best PPL at step {best_step})")
                    return str(nearest)
        except Exception as e:
            logger.warning(f"Could not parse PPL log: {e}")
    
    # Fallback to latest checkpoint
    logger.info(f"Using latest checkpoint: {checkpoints[-1].name}")
    return str(checkpoints[-1])


class ChunkDataset(Dataset):
    """Dataset that packs maritime text chunks into fixed-length sequences."""
    
    def __init__(self, tokenizer, max_length: int = 512):
        self.samples = []
        eos = tokenizer.eos_token_id or 2
        
        # Load all chunk texts
        texts = []
        logger.info(f"Loading chunks from {CHUNKS_FILE}...")
        with open(CHUNKS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    text = rec.get("text", "")
                    if text.strip():
                        texts.append(text)
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"Loaded {len(texts)} chunks, tokenizing...")
        
        # Pack texts into fixed-length sequences
        buffer = []
        for text in texts:
            ids = tokenizer.encode(
                text, 
                add_special_tokens=False,
                truncation=True, 
                max_length=max_length * 2
            )
            ids.append(eos)
            buffer.extend(ids)
            
            while len(buffer) >= max_length:
                self.samples.append(buffer[:max_length])
                buffer = buffer[max_length:]
        
        logger.info(f"TAPT dataset: {len(self.samples)} packed sequences of length {max_length}")

    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        ids = torch.tensor(self.samples[idx], dtype=torch.long)
        return {"input_ids": ids, "labels": ids.clone()}


def main():
    log_pipeline("PHASE_TAPT_1.7B: STARTING LR=6e-6 1epoch chunks.jsonl GPU0")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    logger.info(f"Loading base model: {BASE_MODEL}")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="cuda:0",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    # Load and merge CPT checkpoint
    cpt_ckpt = find_best_cpt_checkpoint()
    if cpt_ckpt:
        logger.info(f"Loading CPT checkpoint: {cpt_ckpt}")
        model = PeftModel.from_pretrained(base, cpt_ckpt)
        model = model.merge_and_unload()
        logger.info("CPT LoRA merged into base weights")
    else:
        model = base
        log_pipeline("PHASE_TAPT_1.7B: WARNING - No CPT checkpoint found, using base model")
    
    # Enable gradient computation for inputs
    model.enable_input_require_grads()
    
    # Apply new LoRA config for TAPT
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=128,
        lora_alpha=128,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Load dataset
    dataset = ChunkDataset(tokenizer, max_length=512)
    
    if len(dataset) == 0:
        log_pipeline("PHASE_TAPT_1.7B: FAIL - No data loaded from chunks.jsonl")
        return
    
    # Create output directory
    TAPT_CHECKPOINT.mkdir(parents=True, exist_ok=True)
    
    # Training arguments
    # With 115k chunks packed into ~50k sequences at batch 2 * accum 8 = effective 16
    # That's ~3125 steps per epoch
    args = TrainingArguments(
        output_dir=str(TAPT_CHECKPOINT),
        num_train_epochs=1,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=8,
        learning_rate=6e-6,
        warmup_ratio=0.03,
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        logging_steps=50,
        save_steps=1000,
        save_total_limit=2,
        fp16=True,
        bf16=False,
        gradient_checkpointing=True,
        optim="adamw_torch",
        report_to="none",
        dataloader_num_workers=2,
        dataloader_pin_memory=True,
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
    )
    
    log_pipeline("PHASE_TAPT_1.7B: TRAINING STARTED")
    
    try:
        trainer.train()
        
        # Save final checkpoint
        final_dir = TAPT_CHECKPOINT / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(final_dir))
        tokenizer.save_pretrained(str(final_dir))
        
        log_pipeline("PHASE_TAPT_1.7B: COMPLETE - checkpoint saved to tapt-1.7b/final")
        
    except Exception as e:
        log_pipeline(f"PHASE_TAPT_1.7B: FAIL - Training error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
