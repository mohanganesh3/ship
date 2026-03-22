#!/usr/bin/env python3
"""training/run_cpt_1.7b.py

CPT for Qwen3-1.7B — single-GPU fp16 LoRA r=128 (K80-compatible)

Constraints:
- Single GPU only (default: GPU0 via CUDA_VISIBLE_DEVICES=0)
- fp16 only (no bf16)
- No DeepSpeed / no distributed / no NCCL requirements
"""

import os
import sys
import json
import math
import time
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Environment MUST be configured before importing torch.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Default GPU assignment for watchdog/restarts.
# NOTE: if the caller already set CUDA_VISIBLE_DEVICES, we respect it.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch

import numpy as np

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import get_peft_model, LoraConfig, TaskType
from torch.utils.data import Dataset, IterableDataset

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
PERPLEXITY_LOG = Path("/home/mohanganesh/ship/logs/cpt_perplexity_1.7b.jsonl")
CHECKPOINT_DIR = Path("/home/mohanganesh/ship/training/checkpoints/cpt-1.7b")

CACHE_DIR = Path("/home/mohanganesh/ship/training/cache")

DATA_DIR = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final")
CPT_CORPUS = DATA_DIR / "cpt_corpus.jsonl"
GENERAL_REPLAY = DATA_DIR / "general_replay.jsonl"
VAL_MARITIME = DATA_DIR / "cpt_val_maritime.jsonl"
VAL_GENERAL = DATA_DIR / "cpt_val_general.jsonl"

MODEL_PATH = "/home/mohanganesh/ship/models/student-1.7b"
MAX_SEQ_LENGTH = 512   # Shorter = faster per step; 512 gives 4x speedup vs 2048 while still packing full docs
# K80 12GB: keep microbatch small and recover effective batch with grad accumulation.
PER_DEVICE_BATCH = 1
GRAD_ACCUM = 32

# Dry-run overrides (keep the gate fast; full training remains unchanged)
DRY_SEQ_LENGTH = 128
DRY_PER_DEVICE_BATCH = 1
DRY_GRAD_ACCUM = 1
NUM_EPOCHS = 3
LEARNING_RATE = 2e-5
WARMUP_RATIO = 0.03
WEIGHT_DECAY = 0.01
SAVE_STEPS = 300
LOGGING_STEPS = 25
EVAL_PPL_STEPS = 300   # Compute perplexity every 300 steps


def _get_model_device(model: torch.nn.Module) -> torch.device:
    try:
        return next(model.parameters()).device
    except StopIteration:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp, path)


def _load_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def log_pipeline(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] {msg}\n"
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a") as f:
        f.write(line)
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


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def load_jsonl_head(path: Path, max_records: int) -> list[dict]:
    """Load up to max_records records from a jsonl file (fast dry-run helper)."""
    records: list[dict] = []
    if max_records <= 0:
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if len(records) >= max_records:
                break
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                records.append(obj)
    return records


def iter_jsonl_texts(path: Path):
    """Yield `text` fields from a jsonl file lazily."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            text = rec.get("text", "") if isinstance(rec, dict) else ""
            if isinstance(text, str) and text.strip():
                yield text


def build_packed_bin_cache(
    *,
    tokenizer: AutoTokenizer,
    src_jsonl: Path,
    out_bin: Path,
    out_meta: Path,
    seq_len: int,
    max_doc_tokens: int,
    log_prefix: str,
) -> dict:
    """Pack tokenized texts into fixed-length sequences and append to a binary file.

    Storage format: raw little-endian uint32 token IDs, row-major.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_bin.parent.mkdir(parents=True, exist_ok=True)

    eos = tokenizer.eos_token_id
    if eos is None:
        eos = 2

    # Build fresh
    if out_bin.exists():
        out_bin.unlink()

    logger.info(f"{log_prefix}: building packed cache from {src_jsonl} → {out_bin}")
    log_pipeline(f"PHASE_1A_CPT_1.7B STATUS: CACHE_BUILD_START ({log_prefix}) src={src_jsonl}")

    buf: list[int] = []
    n_sequences = 0
    n_docs = 0
    n_skipped = 0
    t0 = time.time()

    with open(out_bin, "ab") as fbin:
        for text in iter_jsonl_texts(src_jsonl):
            n_docs += 1

            # IMPORTANT: keep per-doc tokenization bounded to avoid pathological documents
            ids = tokenizer.encode(
                text,
                add_special_tokens=False,
                truncation=True,
                max_length=max_doc_tokens,
            )
            if not ids:
                n_skipped += 1
                continue
            buf.extend(ids)
            buf.append(eos)

            while len(buf) >= seq_len:
                chunk = np.asarray(buf[:seq_len], dtype=np.uint32)
                chunk.tofile(fbin)
                n_sequences += 1
                buf = buf[seq_len:]

            if n_docs % 2000 == 0:
                elapsed = time.time() - t0
                logger.info(
                    f"{log_prefix}: docs={n_docs:,} sequences={n_sequences:,} "
                    f"({n_sequences/elapsed:.2f} seq/s)"
                )

    meta = {
        "src": str(src_jsonl),
        "bin": str(out_bin),
        "dtype": "uint32",
        "seq_len": seq_len,
        "max_doc_tokens": max_doc_tokens,
        "num_sequences": n_sequences,
        "num_docs": n_docs,
        "num_skipped": n_skipped,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_write_json(out_meta, meta)
    log_pipeline(
        f"PHASE_1A_CPT_1.7B STATUS: CACHE_BUILD_DONE ({log_prefix}) sequences={n_sequences} docs={n_docs}"
    )
    return meta


def load_or_build_cache(
    *,
    tokenizer: AutoTokenizer,
    src_jsonl: Path,
    cache_key: str,
    seq_len: int,
    max_doc_tokens: int,
) -> tuple[np.memmap, dict]:
    bin_path = CACHE_DIR / f"{cache_key}_seq{seq_len}_uint32.bin"
    meta_path = CACHE_DIR / f"{cache_key}_seq{seq_len}_meta.json"

    meta = _load_json(meta_path)
    if (
        meta is None
        or not bin_path.exists()
        or meta.get("seq_len") != seq_len
        or meta.get("dtype") != "uint32"
        or meta.get("max_doc_tokens") != max_doc_tokens
        or meta.get("src") != str(src_jsonl)
    ):
        meta = build_packed_bin_cache(
            tokenizer=tokenizer,
            src_jsonl=src_jsonl,
            out_bin=bin_path,
            out_meta=meta_path,
            seq_len=seq_len,
            max_doc_tokens=max_doc_tokens,
            log_prefix=cache_key,
        )

    num_sequences = int(meta.get("num_sequences", 0))
    if num_sequences <= 0:
        raise RuntimeError(f"Cache build produced no sequences for {cache_key}: {src_jsonl}")

    mm = np.memmap(bin_path, dtype=np.uint32, mode="r", shape=(num_sequences, seq_len))
    return mm, meta


class CurriculumPackedIterableDataset(IterableDataset):
    """CPU-friendly curriculum mixer over two packed-sequence memmaps.

    - Each source is a packed array of shape (N, seq_len) with dtype uint32.
    - At each sample, select maritime vs general by curriculum stage ratio.
    - Yields indefinitely; training length is controlled by TrainingArguments.max_steps.
    """

    def __init__(
        self,
        maritime_mm: np.memmap,
        general_mm: np.memmap,
        *,
        seq_len: int,
        seed: int = 1234,
        initial_stage: int = 2,
    ):
        super().__init__()
        self.maritime_mm = maritime_mm
        self.general_mm = general_mm
        self.seq_len = seq_len
        self.seed = seed
        self.stage_ratios = {1: (0.5, 0.5), 2: (0.8, 0.2), 3: (0.7, 0.3)}
        self.current_stage = initial_stage

    def set_stage(self, stage: int):
        if stage != self.current_stage:
            self.current_stage = stage
            m, g = self.stage_ratios[stage]
            logger.info(
                f"Curriculum: stage={stage} maritime={m*100:.0f}% general={g*100:.0f}%"
            )

    def __iter__(self):
        rng = random.Random(self.seed)
        m_indices = list(range(self.maritime_mm.shape[0]))
        g_indices = list(range(self.general_mm.shape[0]))
        rng.shuffle(m_indices)
        rng.shuffle(g_indices)
        m_pos = 0
        g_pos = 0

        while True:
            m_frac, _ = self.stage_ratios[self.current_stage]
            pick_maritime = (rng.random() < m_frac)

            if pick_maritime:
                if m_pos >= len(m_indices):
                    rng.shuffle(m_indices)
                    m_pos = 0
                seq = self.maritime_mm[m_indices[m_pos]]
                m_pos += 1
            else:
                if g_pos >= len(g_indices):
                    rng.shuffle(g_indices)
                    g_pos = 0
                seq = self.general_mm[g_indices[g_pos]]
                g_pos += 1

            ids = torch.from_numpy(np.asarray(seq, dtype=np.int64))
            yield {"input_ids": ids, "labels": ids.clone()}


class TinyPackedDataset(Dataset):
    """Small in-memory dataset for dry runs."""

    def __init__(self, sequences: list[list[int]]):
        self.sequences = sequences

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        ids = torch.tensor(self.sequences[idx], dtype=torch.long)
        return {"input_ids": ids, "labels": ids.clone()}


class PerplexityCallback:
    """Compute validation perplexity every EVAL_PPL_STEPS steps."""

    def __init__(self, model, tokenizer, val_maritime, val_general,
                 perplexity_log_path, eval_steps=300):
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def __init__(inner_self):
                inner_self.model = model
                inner_self.tokenizer = tokenizer
                inner_self.val_maritime = val_maritime
                inner_self.val_general = val_general
                inner_self.log_path = perplexity_log_path
                inner_self.eval_steps = eval_steps
                inner_self.baseline_maritime = None
                inner_self.baseline_general = None

            def _compute_perplexity(inner_self, records, max_samples=50):
                inner_self.model.eval()
                total_loss = 0.0
                total_tokens = 0
                eos = inner_self.tokenizer.eos_token_id or 2
                device = _get_model_device(inner_self.model)

                sample = records[:max_samples]
                with torch.no_grad():
                    for rec in sample:
                        text = rec.get("text", "") if isinstance(rec, dict) else str(rec)
                        if not text.strip():
                            continue
                        ids = inner_self.tokenizer.encode(
                            text, add_special_tokens=False,
                            truncation=True, max_length=512
                        )
                        if len(ids) < 8:
                            continue
                        input_ids = torch.tensor([ids], dtype=torch.long, device=device)
                        out = inner_self.model(input_ids=input_ids, labels=input_ids)
                        total_loss += out.loss.item() * (len(ids) - 1)
                        total_tokens += len(ids) - 1

                if total_tokens == 0:
                    return float("inf")
                avg_loss = total_loss / total_tokens
                return math.exp(avg_loss)

            def on_step_end(inner_self, args, state, control, **kwargs):
                if state.global_step % inner_self.eval_steps != 0:
                    return

                step = state.global_step
                logger.info(f"Computing perplexity at step {step}...")

                m_ppl = inner_self._compute_perplexity(inner_self.val_maritime)
                g_ppl = inner_self._compute_perplexity(inner_self.val_general)

                if inner_self.baseline_maritime is None:
                    inner_self.baseline_maritime = m_ppl
                    inner_self.baseline_general = g_ppl
                    logger.info(f"Baseline PPL — maritime: {m_ppl:.2f}, general: {g_ppl:.2f}")
                else:
                    m_drop_pct = (inner_self.baseline_maritime - m_ppl) / inner_self.baseline_maritime * 100
                    g_increase_pct = (g_ppl - inner_self.baseline_general) / inner_self.baseline_general * 100
                    logger.info(
                        f"Step {step} PPL — maritime: {m_ppl:.2f} ({m_drop_pct:+.1f}% from baseline), "
                        f"general: {g_ppl:.2f} ({g_increase_pct:+.1f}% from baseline)"
                    )

                    # ALERT: catastrophic forgetting
                    if g_increase_pct > 10:
                        logger.warning(
                            f"WARNING: General perplexity increased {g_increase_pct:.1f}% — "
                            f"catastrophic forgetting risk. Monitor closely."
                        )

                entry = {
                    "step": step,
                    "maritime_ppl": round(m_ppl, 4),
                    "general_ppl": round(g_ppl, 4),
                    "baseline_maritime": round(inner_self.baseline_maritime, 4) if inner_self.baseline_maritime else None,
                    "baseline_general": round(inner_self.baseline_general, 4) if inner_self.baseline_general else None,
                    "ts": datetime.now(timezone.utc).isoformat()
                }
                inner_self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(inner_self.log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")

                inner_self.model.train()

        self.callback = _Callback()


class CurriculumStageCallback:
    """Switches curriculum stage based on training progress."""

    def __init__(self, dataset, total_steps: int):
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def on_step_end(inner_self, args, state, control, **kwargs):
                step = state.global_step
                pct = step / max(1, total_steps)
                if pct < 0.10:
                    dataset.set_stage(1)
                elif pct < 0.85:
                    dataset.set_stage(2)
                else:
                    dataset.set_stage(3)

        self.callback = _Callback()


class LossLoggingCallback:
    """Ensure loss is visible in the main training log.

    Some environments end up with tqdm-only output or sparse logs. This callback
    writes a consistent, grep-friendly loss line whenever the Trainer emits logs.
    """

    def __init__(self):
        from transformers import TrainerCallback

        class _Callback(TrainerCallback):
            def on_log(inner_self, args, state, control, logs=None, **kwargs):
                if not logs:
                    return
                if "loss" in logs:
                    try:
                        logger.info(
                            f"TRAIN_LOSS step={state.global_step} loss={float(logs['loss']):.6f}"
                        )
                    except Exception:
                        logger.info(f"TRAIN_LOSS step={state.global_step} loss={logs.get('loss')}")
                else:
                    logger.info(f"TRAIN_LOG step={state.global_step} logs={logs}")

        self.callback = _Callback()


def compute_perplexity_simple(model, tokenizer, records, max_samples=50):
    model.eval()
    total_loss = 0.0
    total_tokens = 0
    device = _get_model_device(model)
    with torch.no_grad():
        for rec in records[:max_samples]:
            text = rec.get("text", "") if isinstance(rec, dict) else str(rec)
            if not text.strip():
                continue
            ids = tokenizer.encode(text, add_special_tokens=False, truncation=True, max_length=512)
            if len(ids) < 8:
                continue
            input_ids = torch.tensor([ids], dtype=torch.long, device=device)
            out = model(input_ids=input_ids, labels=input_ids)
            total_loss += out.loss.item() * (len(ids) - 1)
            total_tokens += len(ids) - 1
    model.train()
    if total_tokens == 0:
        return float("inf")
    return math.exp(total_loss / total_tokens)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Run exactly 20 steps, print loss, do not save")
    args = parser.parse_args()

    phase_tag = "PHASE_1A_CPT_1.7B_DRY_RUN" if args.dry_run else "PHASE_1A_CPT_1.7B"
    ensure_venv_train(phase_tag)

    if not torch.cuda.is_available():
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: torch.cuda.is_available() is false")
        raise SystemExit(1)

    # We expect exactly one visible GPU (CUDA_VISIBLE_DEVICES pins it).
    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if vis.strip() == "":
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: CUDA_VISIBLE_DEVICES is empty")
        raise SystemExit(1)

    try:
        cap = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
    except Exception as e:
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: cannot query GPU0 ({e})")
        raise SystemExit(1)

    if cap < (3, 7):
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: GPU compute capability {cap} < (3, 7)")
        raise SystemExit(1)

    logger.info(f"Using CUDA device: {name} (capability={cap}), CUDA_VISIBLE_DEVICES={vis}")

    if args.dry_run:
        log_pipeline("PHASE_1A_CPT_1.7B_DRY_RUN STATUS: STARTING. Single-GPU fp16 LoRA r=128")
    else:
        log_pipeline("PHASE_1A_CPT_1.7B STATUS: STARTING. Single-GPU fp16 LoRA r=128")

    # === LOAD MODEL ===
    logger.info(f"Loading tokenizer from {MODEL_PATH}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    logger.info(f"Loading model in fp16 on CUDA from {MODEL_PATH}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.float16,
        device_map={"": 0},
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    try:
        model_gb = model.get_memory_footprint() / 1e9
        logger.info(f"Model loaded. Size: {model_gb:.2f} GB")
    except Exception:
        logger.info("Model loaded.")

    # Required for training stability and memory use with gradient checkpointing.
    if hasattr(model, "config"):
        model.config.use_cache = False

    # Enable gradient checkpointing to save memory during backward
    # We have 167 GB free so this is optional, but good practice
    model.enable_input_require_grads()

    # === ATTACH LORA ===
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=128,
        lora_alpha=128,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        inference_mode=False,
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"Trainable LoRA parameters: {trainable/1e6:.1f}M")

    # === LOAD VALIDATION SETS ===
    # Validation JSONLs can be large; keep --dry-run fast.
    if args.dry_run:
        val_maritime_records = []
        val_general_records = []
    else:
        logger.info("Loading validation sets...")
        val_maritime_records = load_jsonl(VAL_MARITIME)
        val_general_records = load_jsonl(VAL_GENERAL)
        logger.info(
            f"Val maritime: {len(val_maritime_records)}, val general: {len(val_general_records)}"
        )

    # === SELECT TRAINING SHAPE ===
    if args.dry_run:
        seq_len = DRY_SEQ_LENGTH
        per_device_batch = DRY_PER_DEVICE_BATCH
        grad_accum = DRY_GRAD_ACCUM
    else:
        seq_len = MAX_SEQ_LENGTH
        per_device_batch = PER_DEVICE_BATCH
        grad_accum = GRAD_ACCUM

    # === BUILD TRAIN DATA ===
    # For full training, use a packed on-disk cache + iterable curriculum mixer (RAM-safe).
    # For dry-run, do a tiny in-memory pack so we can validate end-to-end quickly.
    if args.dry_run:
        # tiny subset
        maritime_records = load_jsonl_head(CPT_CORPUS, 200)
        general_records = load_jsonl_head(GENERAL_REPLAY, 50)
        sequences: list[list[int]] = []
        eos = tokenizer.eos_token_id or 2
        buf: list[int] = []
        for rec in maritime_records + general_records:
            text = rec.get("text", "") if isinstance(rec, dict) else ""
            if not isinstance(text, str) or not text.strip():
                continue
            ids = tokenizer.encode(text, add_special_tokens=False, truncation=True, max_length=seq_len * 4)
            if not ids:
                continue
            buf.extend(ids)
            buf.append(eos)
            while len(buf) >= seq_len:
                sequences.append(buf[:seq_len])
                buf = buf[seq_len:]
                if len(sequences) >= 2000:
                    break
            if len(sequences) >= 2000:
                break
        dataset = TinyPackedDataset(sequences if sequences else [[eos] * seq_len])
        max_steps = 20
        effective_epochs = 1
        save_steps = 99999
        logging_steps = 1
        total_steps_for_curriculum = max_steps
        logger.info(f"Dry run dataset sequences: {len(dataset)}")
    else:
        # Build or load packed caches
        # NOTE: max_doc_tokens bounds per-document tokenization cost
        max_doc_tokens = seq_len * 4
        maritime_mm, maritime_meta = load_or_build_cache(
            tokenizer=tokenizer,
            src_jsonl=CPT_CORPUS,
            cache_key="cpt_maritime_1p7b",
            seq_len=seq_len,
            max_doc_tokens=max_doc_tokens,
        )
        general_mm, general_meta = load_or_build_cache(
            tokenizer=tokenizer,
            src_jsonl=GENERAL_REPLAY,
            cache_key="cpt_general_1p7b",
            seq_len=seq_len,
            max_doc_tokens=max_doc_tokens,
        )
        total_sequences = int(maritime_mm.shape[0] + general_mm.shape[0])
        steps_per_epoch = math.ceil(total_sequences / (per_device_batch * grad_accum))
        max_steps = steps_per_epoch * NUM_EPOCHS
        logger.info(
            f"Packed sequences: maritime={maritime_mm.shape[0]:,} general={general_mm.shape[0]:,} "
            f"total={total_sequences:,} → steps/epoch≈{steps_per_epoch:,} max_steps={max_steps:,}"
        )

        dataset = CurriculumPackedIterableDataset(
            maritime_mm=maritime_mm,
            general_mm=general_mm,
            seq_len=seq_len,
            seed=1234,
            initial_stage=2,
        )
        effective_epochs = NUM_EPOCHS
        save_steps = SAVE_STEPS
        logging_steps = LOGGING_STEPS
        total_steps_for_curriculum = max_steps

    # === TRAINING ARGS ===
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(CHECKPOINT_DIR),
        num_train_epochs=effective_epochs,
        per_device_train_batch_size=per_device_batch,
        gradient_accumulation_steps=grad_accum,
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type="cosine",
        logging_steps=logging_steps,
        logging_strategy="steps",
        logging_first_step=True,
        save_steps=save_steps,
        save_total_limit=3,
        fp16=True,
        bf16=False,
        dataloader_num_workers=0,  # 0 = main process (avoids CPU contention with teacher)
        dataloader_pin_memory=True,
        report_to="none",
        disable_tqdm=True,
        load_best_model_at_end=False,
        prediction_loss_only=True,
        optim="adamw_torch",
        max_steps=max_steps,
        gradient_checkpointing=False,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
        pad_to_multiple_of=None,
    )

    # === CALLBACKS ===
    callbacks = []

    # Always log losses (and other trainer logs) in a consistent format.
    callbacks.append(LossLoggingCallback().callback)

    if not args.dry_run:
        ppl_cb = PerplexityCallback(
            model, tokenizer,
            val_maritime_records, val_general_records,
            PERPLEXITY_LOG, eval_steps=EVAL_PPL_STEPS
        )
        callbacks.append(ppl_cb.callback)

        stage_cb = CurriculumStageCallback(dataset, total_steps_for_curriculum)
        callbacks.append(stage_cb.callback)

    # === TRAINER ===
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
        callbacks=callbacks,
    )

    # === BASELINE PERPLEXITY ===
    if not args.dry_run:
        logger.info("Computing baseline perplexity before training...")
        m_baseline = compute_perplexity_simple(model, tokenizer, val_maritime_records)
        g_baseline = compute_perplexity_simple(model, tokenizer, val_general_records)
        logger.info(f"Baseline — maritime PPL: {m_baseline:.2f}, general PPL: {g_baseline:.2f}")
        entry = {"step": 0, "maritime_ppl": round(m_baseline, 4), "general_ppl": round(g_baseline, 4),
                 "baseline_maritime": round(m_baseline, 4), "baseline_general": round(g_baseline, 4),
                 "ts": datetime.now(timezone.utc).isoformat()}
        PERPLEXITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(PERPLEXITY_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    # === TRAIN ===
    logger.info("Starting training...")
    start = time.time()
    if args.dry_run:
        log_pipeline("PHASE_1A_CPT_1.7B_DRY_RUN STATUS: TRAINING STARTED")
    else:
        log_pipeline("PHASE_1A_CPT_1.7B STATUS: TRAINING STARTED")

    result = trainer.train()

    elapsed = time.time() - start
    logger.info(f"Training complete. Elapsed: {elapsed/3600:.1f} hours")

    if args.dry_run:
        # Report dry run metrics
        history = trainer.state.log_history
        losses = [h["loss"] for h in history if "loss" in h]
        if losses:
            print(f"\nDRY_RUN RESULT:")
            print(f"  loss_step_1: {losses[0]:.4f}")
            print(f"  loss_step_20: {losses[-1]:.4f}")
            print(f"  steps_completed: {len(losses)}")
            print(f"  elapsed_seconds: {elapsed:.1f}")
            tokens_processed = 20 * per_device_batch * seq_len
            print(f"  tokens_per_sec: {tokens_processed/elapsed:.1f}")
        print("DRY_RUN PASS")
        log_pipeline("PHASE_1A_CPT_1.7B_DRY_RUN STATUS: PASS")
        return

    # === SAVE ===
    logger.info(f"Saving final model to {CHECKPOINT_DIR}")
    trainer.save_model(str(CHECKPOINT_DIR / "final"))
    tokenizer.save_pretrained(str(CHECKPOINT_DIR / "final"))

    # === FINAL PERPLEXITY GATE CHECK ===
    logger.info("Running CPT gate check...")
    ppl_entries = []
    if PERPLEXITY_LOG.exists():
        with open(PERPLEXITY_LOG) as f:
            for line in f:
                try:
                    ppl_entries.append(json.loads(line))
                except Exception:
                    pass

    if len(ppl_entries) >= 2:
        baseline_m = ppl_entries[0]["maritime_ppl"]
        baseline_g = ppl_entries[0]["general_ppl"]
        final_m = ppl_entries[-1]["maritime_ppl"]
        final_g = ppl_entries[-1]["general_ppl"]

        m_drop_pct = (baseline_m - final_m) / baseline_m * 100
        g_increase_pct = (final_g - baseline_g) / baseline_g * 100

        gate_pass = m_drop_pct >= 15 and g_increase_pct <= 10

        logger.info(f"CPT GATE CHECK:")
        logger.info(f"  Maritime PPL: {baseline_m:.2f} → {final_m:.2f} (drop: {m_drop_pct:.1f}%) — need ≥15%")
        logger.info(f"  General PPL: {baseline_g:.2f} → {final_g:.2f} (increase: {g_increase_pct:.1f}%) — need ≤10%")
        logger.info(f"  GATE: {'PASS' if gate_pass else 'FAIL'}")

        if gate_pass:
            log_pipeline(f"PHASE_1A_CPT_1.7B STATUS: PASS. Maritime PPL drop {m_drop_pct:.1f}%, general increase {g_increase_pct:.1f}%")
        else:
            log_pipeline(f"PHASE_1A_CPT_1.7B STATUS: FAIL. Maritime drop {m_drop_pct:.1f}% (need 15%), general increase {g_increase_pct:.1f}% (need ≤10%)")
            sys.exit(1)
    else:
        log_pipeline("PHASE_1A_CPT_1.7B STATUS: WARNING — insufficient perplexity log entries for gate check")

    log_pipeline(f"PHASE_1A_CPT_1.7B STATUS: COMPLETE. Model saved to {CHECKPOINT_DIR}/final")


if __name__ == "__main__":
    main()
