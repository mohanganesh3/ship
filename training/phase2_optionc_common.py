#!/usr/bin/env python3
"""Shared helpers for the April 10 post-CPT Option C phase-2 pipeline."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import torch
from peft import LoraConfig, PeftModel, TaskType, get_peft_model
from torch.utils.data import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

LOGGER = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
BASE_MODEL = "/home/mohanganesh/ship/models/student-1.7b"
CPT_CHECKPOINT_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/cpt-1.7b")
SFT1_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft1-1.7b")
SFT2_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-sft2-1.7b")
BOUNDARY_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/phase2-optionc-boundary-1.7b")
CORRECTION_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/phase3-local-correction-1.7b")
ORPO_ROOT = Path("/home/mohanganesh/ship/training/checkpoints/phase4-local-orpo-1.7b")
SFT1_FINAL = SFT1_ROOT / "final"
SFT2_FINAL = SFT2_ROOT / "final"
BOUNDARY_FINAL = BOUNDARY_ROOT / "final"
CORRECTION_FINAL = CORRECTION_ROOT / "final"
ORPO_FINAL = ORPO_ROOT / "final"
CHAIN_METADATA = "base_chain.json"
DEFAULT_OPTIONC_DATA = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated_optionc_1p7b.jsonl"
)
DEFAULT_OPTIONC_TRAPS = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated_traps_optionc_1p7b.jsonl"
)
DEFAULT_REASONING_REPLAY = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl"
)
DEFAULT_BENCHMARK = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/local_benchmark_v2_1p7b.jsonl"
)
DEFAULT_CORRECTIONS_DATA = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_corrections_optionc_1p7b.jsonl"
)
DEFAULT_ORPO_DATA = Path(
    "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/orpo_pairs_optionc_1p7b.jsonl"
)

SYSTEM_PROMPT_THINK = """You are an expert maritime assistant for shipboard safety, regulation, troubleshooting, and engineering operations.
Use explicit reasoning before the final answer.
/think"""

SYSTEM_PROMPT_NOTHINK = """You are an expert maritime assistant for shipboard safety, regulation, troubleshooting, and engineering operations.
Give direct operational answers, reject unsafe actions, and escalate when required.
/no_think"""

TRAP_REJECTION_CUES = (
    "do not",
    "must not",
    "unsafe",
    "stop",
    "cannot",
    "not acceptable",
    "never",
)

TRAP_ESCALATION_CUES = (
    "escalate",
    "notify",
    "inform",
    "call the master",
    "call master",
    "master",
    "chief engineer",
    "tmas",
    "rcc",
    "mrcc",
)

NEGATION_CUES = (
    "do not",
    "must not",
    "cannot",
    "can not",
    "may not",
    "never",
    "not permitted",
    "not allowed",
    "unsafe",
    "stop",
    "prohibited",
)

REGULATORY_MODAL_CUES = (
    "shall",
    "must",
    "required",
    "requirement",
    "prohibited",
    "prohibit",
    "cannot",
    "may not",
    "not permitted",
    "not allowed",
    "mandatory",
)

CHECK_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "while",
    "your",
    "their",
    "there",
    "have",
    "has",
    "had",
    "been",
    "being",
    "will",
    "would",
    "should",
    "could",
    "about",
    "after",
    "before",
    "under",
    "over",
    "then",
    "than",
    "they",
    "them",
    "were",
    "what",
    "when",
    "where",
    "which",
    "since",
    "because",
    "through",
    "until",
    "only",
    "just",
    "also",
    "still",
    "onto",
    "upon",
    "very",
    "more",
    "most",
    "been",
    "such",
    "our",
    "are",
    "can",
    "all",
    "any",
}

META_HEADING_CUES = {
    "context",
    "inspection context",
    "ship security plan context",
    "background",
    "scenario",
    "logical error",
    "aesthetic & expert context",
    "aesthetic and expert context",
    "expert context",
}

ACTIONABLE_CUES = {
    "activate",
    "check",
    "confirm",
    "contact",
    "document",
    "ensure",
    "evacuate",
    "inform",
    "inspect",
    "isolate",
    "maintain",
    "must",
    "notify",
    "obtain",
    "only if",
    "preserve",
    "prohibited",
    "record",
    "report",
    "required",
    "requires",
    "review",
    "secure",
    "shall",
    "should",
    "stop",
    "suspend",
    "test",
    "verify",
}

ESCALATION_ROLE_CUES = {
    "master",
    "chief engineer",
    "chief officer",
    "chief mate",
    "dpa",
    "flag state",
    "company",
    "port state control",
    "psc",
    "tmas",
    "rcc",
    "mrcc",
    "bridge team",
    "security officer",
    "ship security officer",
    "medical officer",
    "terminal",
}

ESCALATION_ALIAS_MAP: dict[str, str] = {
    "master": "Master",
    "ship's master": "Master",
    "the master": "Master",
    "captain": "Master",
    "chief engineer": "Chief Engineer",
    "c/e": "Chief Engineer",
    "the chief engineer": "Chief Engineer",
    "chief officer": "Chief Officer",
    "chief mate": "Chief Officer",
    "dpa": "DPA",
    "designated person ashore": "DPA",
    "flag state": "Flag State",
    "company": "Company",
    "port state control": "Port State Control",
    "psc": "Port State Control",
    "tmas": "TMAS",
    "rcc": "RCC",
    "mrcc": "RCC",
    "bridge team": "Bridge Team",
    "security officer": "Security Officer",
    "ship security officer": "Security Officer",
    "sso": "Security Officer",
    "cso": "Company Security Officer",
    "company security officer": "Company Security Officer",
    "medical officer": "Medical Officer",
    "terminal": "Terminal",
    "class surveyor": "Class Surveyor",
    "classification society": "Class Surveyor",
}


def resolve_escalation_alias(raw: str) -> str:
    """Map a raw escalation target to its canonical form."""
    lowered = normalize_space(raw).lower().strip("., ")
    if lowered in ESCALATION_ALIAS_MAP:
        return ESCALATION_ALIAS_MAP[lowered]
    for alias_key, canonical in ESCALATION_ALIAS_MAP.items():
        if alias_key in lowered:
            return canonical
    return normalize_space(raw).strip("., ").title()


def escalation_alias_match(target: str, candidate: str) -> bool:
    """Check if a benchmark escalation target matches a candidate string, using alias resolution."""
    target_canon = resolve_escalation_alias(target)
    candidate_lower = normalize_space(candidate).lower()
    # Direct canonical match
    if target_canon.lower() in candidate_lower:
        return True
    # Check all aliases of the canonical target
    for alias_key, canon in ESCALATION_ALIAS_MAP.items():
        if canon == target_canon and alias_key in candidate_lower:
            return True
    return False

CHECKPOINT_PATTERN = re.compile(r"checkpoint-(\d+)$")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")


def log_pipeline(message: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PIPELINE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{ts}] {message}\n")
    LOGGER.info(message)


def ensure_venv_train(phase_tag: str) -> None:
    exe_raw = os.path.abspath(sys.executable)
    exe_real = os.path.realpath(sys.executable)
    if "/.venv-train/" not in exe_raw and "/.venv-train/" not in exe_real:
        log_pipeline(
            f"{phase_tag} FAIL — ENV_GATE: must run with .venv-train python "
            f"(got: exe={exe_raw}, real={exe_real})"
        )
        raise SystemExit(1)


def ensure_cuda(phase_tag: str) -> None:
    if not torch.cuda.is_available():
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: torch.cuda.is_available() is false")
        raise SystemExit(1)
    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if not vis:
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: CUDA_VISIBLE_DEVICES is empty")
        raise SystemExit(1)
    try:
        capability = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
    except Exception as exc:  # pragma: no cover
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: cannot query GPU0 ({exc})")
        raise SystemExit(1)
    if capability < (3, 7):
        log_pipeline(f"{phase_tag} FAIL — CUDA_GATE: GPU compute capability {capability} < (3, 7)")
        raise SystemExit(1)
    LOGGER.info("Using CUDA device: %s (capability=%s), CUDA_VISIBLE_DEVICES=%s", name, capability, vis)


def gate_require_file(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — DATASET_GATE: required file not found: {path}")
        raise SystemExit(1)


def gate_require_dir(path: Path, phase_tag: str) -> None:
    if not path.exists():
        log_pipeline(f"{phase_tag} FAIL — ARTIFACT_GATE: required path not found: {path}")
        raise SystemExit(1)


def gate_require_min_records(records: list[dict], minimum: int, phase_tag: str, label: str) -> None:
    if len(records) < minimum:
        log_pipeline(f"{phase_tag} FAIL — DATASET_GATE: {label} has {len(records)} records (< {minimum})")
        raise SystemExit(1)


def normalize_space(text: str | None) -> str:
    return " ".join(str(text or "").split()).strip()


def normalize_multiline(text: str | None) -> str:
    raw = str(text or "").replace("\r\n", "\n")
    return "\n".join(line.rstrip() for line in raw.splitlines()).strip()


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def coalesce_question(record: dict) -> str:
    return normalize_space(record.get("q") or record.get("question") or record.get("prompt"))


def strip_think(answer: str) -> str:
    text = str(answer or "")
    while "<think>" in text and "</think>" in text:
        start = text.find("<think>")
        end = text.find("</think>") + len("</think>")
        text = f"{text[:start]} {text[end:]}"
    return normalize_multiline(text)


def extract_think(answer: str) -> str:
    text = str(answer or "")
    start = text.find("<think>")
    end = text.find("</think>")
    if start == -1 or end == -1 or end <= start:
        return ""
    return normalize_multiline(text[start + len("<think>") : end])


def synthesize_reasoning(record: dict, answer_text: str) -> str:
    domain = normalize_space(record.get("domain_letter") or record.get("domain_name") or "shipboard")
    sample_type = normalize_space(record.get("sample_type") or record.get("type") or "maritime")
    q = coalesce_question(record)
    steps = []
    answer_lines = [normalize_space(line) for line in str(answer_text).splitlines() if normalize_space(line)]
    for idx, line in enumerate(answer_lines[:3], start=1):
        steps.append(f"{idx}. Operational check: {line}")
    while len(steps) < 3:
        steps.append(
            f"{len(steps) + 1}. Operational check: verify the governing onboard limits, alarms, and authority chain before continuing."
        )
    return "\n".join(
        [
            f"1. Context: {sample_type} case in domain {domain}.",
            f"2. Question focus: {q or 'maritime safety decision'}.",
            f"3. Safety logic: isolate the immediate risk, confirm the critical inputs, then apply the governing procedure.",
            f"4. Evidence: {steps[0].split(':', 1)[1].strip()}",
        ]
    )


def record_answer(record: dict) -> str:
    return normalize_multiline(record.get("a") or record.get("answer") or record.get("response"))


def apply_chat(tokenizer, messages: list[dict]) -> str:
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    except Exception:
        chunks = []
        for message in messages:
            chunks.append(f"<|im_start|>{message['role']}\n{message['content']}<|im_end|>")
        return "\n".join(chunks)


def build_think_text(tokenizer, question: str, answer: str, thinking: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_THINK},
        {"role": "user", "content": question},
        {"role": "assistant", "content": f"<think>\n{thinking}\n</think>\n{answer}"},
    ]
    return apply_chat(tokenizer, messages)


def build_nothink_text(tokenizer, question: str, answer: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_NOTHINK},
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]
    return apply_chat(tokenizer, messages)


def load_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def resolve_cpt_checkpoint(phase_tag: str) -> Path:
    final_dir = CPT_CHECKPOINT_ROOT / "final"
    if final_dir.exists():
        return final_dir
    gate_require_dir(CPT_CHECKPOINT_ROOT, phase_tag)
    best_step = -1
    best_dir: Path | None = None
    for path in CPT_CHECKPOINT_ROOT.glob("checkpoint-*"):
        if not path.is_dir():
            continue
        try:
            step = int(path.name.split("-", 1)[1])
        except Exception:
            continue
        if step > best_step:
            best_step = step
            best_dir = path
    if best_dir is None:
        log_pipeline(f"{phase_tag} FAIL — ARTIFACT_GATE: no CPT checkpoint found under {CPT_CHECKPOINT_ROOT}")
        raise SystemExit(1)
    return best_dir


def load_cpt_merged_model(phase_tag: str):
    checkpoint = resolve_cpt_checkpoint(phase_tag)
    LOGGER.info("Loading base model from %s", BASE_MODEL)
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map={"": 0},
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    if hasattr(base_model, "config"):
        base_model.config.use_cache = False
    LOGGER.info("Loading CPT LoRA from %s", checkpoint)
    merged = PeftModel.from_pretrained(base_model, str(checkpoint))
    merged = merged.merge_and_unload()
    if hasattr(merged, "config"):
        merged.config.use_cache = False
    return merged


def merge_adapter_onto_model(model, adapter_dir: Path, phase_tag: str):
    gate_require_dir(adapter_dir, phase_tag)
    LOGGER.info("Loading LoRA from %s", adapter_dir)
    merged = PeftModel.from_pretrained(model, str(adapter_dir))
    merged = merged.merge_and_unload()
    if hasattr(merged, "config"):
        merged.config.use_cache = False
    return merged


def load_chain_metadata(adapter_dir: Path) -> list[Path] | None:
    meta_path = adapter_dir / CHAIN_METADATA
    if not meta_path.exists():
        return None
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    adapters = payload.get("adapters")
    if not isinstance(adapters, list):
        return None
    return [Path(item) for item in adapters if item]


def resolve_adapter_chain(adapter_dir: Path, phase_tag: str) -> list[Path]:
    adapter_dir = adapter_dir.resolve()
    metadata_chain = load_chain_metadata(adapter_dir)
    if metadata_chain:
        return [Path(item).resolve() for item in metadata_chain]

    cpt = resolve_cpt_checkpoint(phase_tag).resolve()
    marker = str(adapter_dir)
    if adapter_dir == cpt:
        return [cpt]
    if "phase2-optionc-sft1-1.7b" in marker:
        return [cpt, adapter_dir]
    if "phase2-optionc-sft2-1.7b" in marker:
        return resolve_adapter_chain(SFT1_FINAL, phase_tag) + [adapter_dir]
    if "phase2-optionc-boundary-1.7b" in marker:
        return resolve_adapter_chain(SFT2_FINAL, phase_tag) + [adapter_dir]
    if "phase3-local-correction-1.7b" in marker:
        base_dir = BOUNDARY_FINAL if (BOUNDARY_FINAL / "adapter_model.safetensors").exists() else SFT2_FINAL
        return resolve_adapter_chain(base_dir, phase_tag) + [adapter_dir]
    if "phase4-local-orpo" in marker:
        return resolve_adapter_chain(CORRECTION_FINAL, phase_tag) + [adapter_dir]
    return [adapter_dir]


def write_chain_metadata(adapter_dir: Path, adapters: list[Path], phase_tag: str) -> None:
    gate_require_dir(adapter_dir, phase_tag)
    payload = {
        "base_model": BASE_MODEL,
        "adapters": [str(Path(item).resolve()) for item in adapters],
    }
    (adapter_dir / CHAIN_METADATA).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_merged_model_from_adapter(adapter_dir: Path, phase_tag: str):
    chain = resolve_adapter_chain(adapter_dir, phase_tag)
    LOGGER.info("Loading base model from %s", BASE_MODEL)
    # Load on CPU to avoid massive GPU memory fragmentation during sequential merges
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    if hasattr(model, "config"):
        model.config.use_cache = False
    for layer, chain_item in enumerate(chain, start=1):
        LOGGER.info("Applying adapter %d/%d from %s", layer, len(chain), chain_item)
        model = merge_adapter_onto_model(model, chain_item, phase_tag)
    # Move to GPU only after all merges are complete
    LOGGER.info("Moving fully merged model to CUDA")
    model = model.to("cuda")
    torch.cuda.empty_cache()
    return model


def attach_training_lora(model):
    if hasattr(model, "peft_config"):
        delattr(model, "peft_config")
    model.enable_input_require_grads()
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=32,
        lora_alpha=64,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


class TokenizedDataset(Dataset):
    def __init__(self, items: list[dict]):
        self.items = items

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict:
        return self.items[index]


class SupervisedDataCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features: list[dict]) -> dict[str, torch.Tensor]:
        max_len = max(len(feature["input_ids"]) for feature in features)
        pad_id = self.tokenizer.pad_token_id
        input_ids = []
        attention_mask = []
        labels = []
        for feature in features:
            length = len(feature["input_ids"])
            pad = max_len - length
            input_ids.append(feature["input_ids"] + [pad_id] * pad)
            attention_mask.append(feature["attention_mask"] + [0] * pad)
            labels.append(feature["labels"] + [-100] * pad)
        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "labels": torch.tensor(labels, dtype=torch.long),
        }


def tokenize_texts(tokenizer, texts: Iterable[str], max_length: int) -> TokenizedDataset:
    items: list[dict] = []
    for text in texts:
        encoded = tokenizer(
            text,
            add_special_tokens=False,
            truncation=True,
            max_length=max_length,
        )
        if not encoded["input_ids"]:
            continue
        items.append(
            {
                "input_ids": encoded["input_ids"],
                "attention_mask": encoded["attention_mask"],
                "labels": list(encoded["input_ids"]),
            }
        )
    return TokenizedDataset(items)


def latest_checkpoint_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    best_step = -1
    best_dir: Path | None = None
    for path in root.iterdir():
        if not path.is_dir():
            continue
        match = CHECKPOINT_PATTERN.match(path.name)
        if not match:
            continue
        step = int(match.group(1))
        if step > best_step:
            best_step = step
            best_dir = path
    return best_dir


def final_adapter_exists(root: Path) -> bool:
    return (root / "final" / "adapter_model.safetensors").exists()


def disable_resume_rng_files(checkpoint_dir: Path, phase_tag: str) -> None:
    for path in checkpoint_dir.glob("rng_state*.pth"):
        disabled = path.with_suffix(path.suffix + ".disabled")
        if disabled.exists():
            continue
        path.rename(disabled)
        log_pipeline(f"{phase_tag} STATUS: disabled resume RNG file {disabled.name}")


def resolve_resume_checkpoint(output_dir: Path) -> Path | None:
    if final_adapter_exists(output_dir):
        return None
    checkpoint = latest_checkpoint_dir(output_dir)
    if checkpoint is not None:
        disable_resume_rng_files(checkpoint, output_dir.name)
    return checkpoint


def patch_trainer_rng_resume() -> None:
    from transformers import trainer as trainer_module

    current = trainer_module.Trainer._load_rng_state
    if getattr(current, "__name__", "") == "_patched_load_rng_state":
        return

    def _patched_load_rng_state(self, checkpoint):
        if checkpoint is None:
            return
        if self.args.world_size > 1:
            process_index = self.args.process_index
            rng_file = os.path.join(checkpoint, f"rng_state_{process_index}.pth")
            if not os.path.isfile(rng_file):
                trainer_module.logger.info(
                    "Didn't find an RNG file for process %s, reproducibility is not guaranteed.",
                    process_index,
                )
                return
        else:
            rng_file = os.path.join(checkpoint, "rng_state.pth")
            if not os.path.isfile(rng_file):
                trainer_module.logger.info(
                    "Didn't find an RNG file, reproducibility is not guaranteed for resumed training."
                )
                return

        checkpoint_rng_state = torch.load(rng_file, weights_only=False)
        random.setstate(checkpoint_rng_state["python"])
        import numpy as np

        np.random.set_state(checkpoint_rng_state["numpy"])
        torch.random.set_rng_state(checkpoint_rng_state["cpu"])
        if trainer_module.is_torch_xla_available():
            trainer_module.xm.set_rng_state(checkpoint_rng_state["xla"])

        is_distributed = self.args.parallel_mode == trainer_module.ParallelMode.DISTRIBUTED
        if torch.cuda.is_available():
            trainer_module.set_rng_state_for_device("CUDA", torch.cuda, checkpoint_rng_state, is_distributed)
        if trainer_module.is_torch_npu_available():
            trainer_module.set_rng_state_for_device("NPU", torch.npu, checkpoint_rng_state, is_distributed)
        if trainer_module.is_torch_hpu_available():
            trainer_module.set_rng_state_for_device("HPU", torch.hpu, checkpoint_rng_state, is_distributed)
        if trainer_module.is_torch_mlu_available():
            trainer_module.set_rng_state_for_device("MLU", torch.mlu, checkpoint_rng_state, is_distributed)
        if trainer_module.is_torch_musa_available():
            trainer_module.set_rng_state_for_device("MUSA", torch.musa, checkpoint_rng_state, is_distributed)

    trainer_module.Trainer._load_rng_state = _patched_load_rng_state


def deterministic_shuffle(records: list[dict], seed: int = 1337) -> list[dict]:
    out = list(records)
    random.Random(seed).shuffle(out)
    return out


def stage1_optionc_records(data_path: Path) -> list[dict]:
    records = []
    for record in read_jsonl(data_path):
        question = coalesce_question(record)
        answer = record_answer(record)
        if not question or not answer:
            continue
        mode = normalize_space(record.get("mode"))
        record_type = normalize_space(record.get("type")).lower()
        if mode == "think" or record_type in {"troubleshooting", "calculation", "diagnostic_multistep"}:
            records.append(record)
    return records


def stage1_replay_records(data_path: Path, max_calc: int = 512, max_other: int = 1024) -> list[dict]:
    if not data_path.exists():
        return []
    calc = []
    other = []
    for record in read_jsonl(data_path):
        question = coalesce_question(record)
        answer = record_answer(record)
        if not question or not answer:
            continue
        rtype = normalize_space(record.get("type")).lower()
        angle = normalize_space(record.get("angle")).lower()
        difficulty = normalize_space(record.get("difficulty_hint")).lower()
        blob = " ".join([rtype, angle, difficulty]).lower()
        if "calculation" in blob:
            calc.append(record)
        elif any(token in blob for token in ("troubleshooting", "diagnostic", "multi")):
            other.append(record)
    return deterministic_shuffle(calc, seed=1337)[:max_calc] + deterministic_shuffle(other, seed=1729)[:max_other]


def stage2_nothink_records(data_path: Path) -> list[dict]:
    records = []
    for record in read_jsonl(data_path):
        question = coalesce_question(record)
        answer = record_answer(record)
        if not question or not answer:
            continue
        if normalize_space(record.get("mode")) == "think":
            continue
        records.append(record)
    return records


def stage2_trap_records(traps_path: Path, multiplier: int = 2) -> list[dict]:
    records = []
    for record in read_jsonl(traps_path):
        question = coalesce_question(record)
        answer = record_answer(record)
        if not question or not answer:
            continue
        records.append(record)
    if multiplier <= 1:
        return records
    expanded = []
    for _ in range(multiplier):
        expanded.extend(records)
    return expanded


def synthesize_thinkfollow(records: list[dict], count: int = 200) -> list[dict]:
    procedural = []
    for record in records:
        if normalize_space(record.get("type")).lower() != "procedural":
            continue
        answer = record_answer(record)
        if len(answer.split()) < 25:
            continue
        procedural.append(record)
    synth = []
    for record in procedural[:count]:
        question = coalesce_question(record)
        answer = record_answer(record)
        first_line = normalize_space(answer.splitlines()[0] if answer.splitlines() else answer)
        synth.append(
            {
                "q": f"Give only the most critical immediate action for this case: {question}",
                "a": first_line or answer,
                "type": "procedural",
                "mode": "no_think",
                "sample_type": "thinkfollow",
            }
        )
    return synth


def prepare_stage1_texts(tokenizer, optionc_records: list[dict], replay_records: list[dict], max_records: int | None) -> list[str]:
    texts = []
    seen = set()
    combined = deterministic_shuffle(optionc_records, 1337) + deterministic_shuffle(replay_records, 2026)
    for record in combined:
        question = coalesce_question(record)
        answer = strip_think(record_answer(record))
        if not question or not answer:
            continue
        key = question.lower()
        if key in seen:
            continue
        seen.add(key)
        thinking = normalize_multiline(record.get("thinking")) or extract_think(record_answer(record))
        if not thinking:
            thinking = synthesize_reasoning(record, answer)
        texts.append(build_think_text(tokenizer, question, answer, thinking))
        if max_records is not None and len(texts) >= max_records:
            break
    return texts


def prepare_stage2_texts(
    tokenizer,
    nothink_records: list[dict],
    trap_records: list[dict],
    thinkfollow_records: list[dict],
    max_records: int | None,
) -> list[str]:
    texts = []
    combined = (
        deterministic_shuffle(nothink_records, 4242)
        + deterministic_shuffle(trap_records, 5151)
        + deterministic_shuffle(thinkfollow_records, 6262)
    )
    for record in combined:
        question = coalesce_question(record)
        answer = record_answer(record)
        if not question or not answer:
            continue
        texts.append(build_nothink_text(tokenizer, question, answer))
        if max_records is not None and len(texts) >= max_records:
            break
    return texts


def trap_response_passes(text: str) -> bool:
    lowered = normalize_space(text).lower()
    return any(token in lowered for token in TRAP_REJECTION_CUES) and any(
        token in lowered for token in TRAP_ESCALATION_CUES
    )


def text_contains_any(text: str, checks: list[str]) -> bool:
    lowered = normalize_space(text).lower()
    return any(normalize_space(check).lower() in lowered for check in checks if normalize_space(check))


def answer_lines(answer: str) -> list[str]:
    lines = []
    for line in normalize_multiline(answer).splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line))
        if norm:
            lines.append(norm)
    return lines


def canonicalize_check_line(line: str) -> str:
    norm = normalize_space(line).replace("**", "")
    if not norm:
        return ""
    if ":" in norm:
        head, tail = norm.split(":", 1)
        head_norm = normalize_space(head).lower()
        tail_norm = normalize_space(tail)
        if head_norm.startswith("do not"):
            return f"Do not: {tail_norm}" if tail_norm else "Do not:"
        if head_norm.startswith("escalate to"):
            return f"Escalate to: {tail_norm}" if tail_norm else "Escalate to:"
        if any(cue in head_norm for cue in META_HEADING_CUES):
            return ""
        if "citation" in head_norm or head_norm == "context" or head_norm.endswith("context"):
            return ""
        if head_norm.startswith("numerical") and not re.search(r"\d", tail_norm):
            return ""
        if tail_norm:
            return tail_norm
    return norm


def is_meta_or_context_line(line: str) -> bool:
    lowered = normalize_space(line).lower()
    if not lowered:
        return True
    if any(cue in lowered for cue in META_HEADING_CUES):
        return True
    if lowered.startswith(("assuming ", "given ", "because ", "since ")):
        return True
    if lowered.startswith(("we're ", "we are ", "our vessel ", "currently ")):
        return not any(cue in lowered for cue in ACTIONABLE_CUES)
    return False


def looks_actionable_check(line: str) -> bool:
    lowered = normalize_space(line).lower()
    if not lowered or is_meta_or_context_line(lowered):
        return False
    if any(cue in lowered for cue in ACTIONABLE_CUES):
        return True
    return bool(re.search(r"\d", lowered) and any(cue in lowered for cue in REGULATORY_MODAL_CUES))


def forbidden_match(target: str, candidate: str) -> bool:
    target_norm = canonicalize_check_line(target)
    candidate_norm = canonicalize_check_line(candidate)
    if not target_norm or not candidate_norm:
        return False
    target_lower = target_norm.lower()
    candidate_lower = candidate_norm.lower()
    if target_lower in candidate_lower:
        return True

    target_words = keyword_tokens(target_norm)
    candidate_words = keyword_tokens(candidate_norm)
    if not target_words or not candidate_words:
        return False

    overlap = target_words & candidate_words
    overlap_ratio = len(overlap) / max(1, len(target_words))
    if numeric_tokens(target_norm) and not numeric_tokens(target_norm).issubset(numeric_tokens(candidate_norm)):
        return False
    return overlap_ratio >= 0.8


def expand_check_candidates(line: str) -> list[str]:
    canonical = canonicalize_check_line(line)
    if not canonical:
        return []

    if re.search(r"(?:^|\s)1\.\s", canonical):
        prefix = ""
        numbered_start = re.search(r"(?:^|\s)(1\.\s)", canonical)
        if numbered_start and numbered_start.start() > 0:
            prefix = normalize_space(canonical[: numbered_start.start()].rstrip(":"))
        numbered = re.split(r"\s+(?=\d+\.\s)", canonical[numbered_start.start() :] if numbered_start else canonical)
        expanded = []
        for item in numbered:
            stripped = normalize_space(re.sub(r"^\d+\.\s*", "", item))
            if not stripped:
                continue
            if prefix:
                expanded.append(normalize_space(f"{prefix} {stripped}"))
            else:
                expanded.append(stripped)
        if expanded:
            return expanded

    sentences = [normalize_space(chunk) for chunk in re.split(r"(?<=[.!?])\s+", canonical) if normalize_space(chunk)]
    if len(sentences) > 1 and len(canonical.split()) > 18:
        return sentences[:2]
    return [canonical]


def keyword_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9%]+", normalize_space(text).lower())
    return {token for token in tokens if (token.isdigit() or len(token) > 2) and token not in CHECK_STOPWORDS}


def numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", normalize_space(text).lower()))


def semantic_match(target: str, candidate: str) -> bool:
    target_norm = canonicalize_check_line(target)
    candidate_norm = canonicalize_check_line(candidate)
    if not target_norm or not candidate_norm:
        return False
    target_lower = target_norm.lower()
    candidate_lower = candidate_norm.lower()
    if target_lower in candidate_lower or candidate_lower in target_lower:
        return True

    target_words = keyword_tokens(target_norm)
    candidate_words = keyword_tokens(candidate_norm)
    if not target_words or not candidate_words:
        return False

    overlap = target_words & candidate_words
    overlap_count = len(overlap)
    required_overlap = 1 if len(target_words) <= 2 else 2 if len(target_words) <= 5 else 3
    if overlap_count < required_overlap:
        return False

    target_numbers = numeric_tokens(target_norm)
    if target_numbers and not target_numbers.issubset(numeric_tokens(candidate_norm)):
        return False

    return (overlap_count / max(1, len(target_words))) >= 0.4


def response_lines_for_scoring(answer: str) -> list[str]:
    stripped = strip_think(answer)
    lines = [canonicalize_check_line(line) for line in answer_lines(stripped)]
    lines = [line for line in lines if line]
    full = canonicalize_check_line(stripped)
    if full:
        lines.append(full)
    return lines


def line_has_negation(line: str) -> bool:
    lowered = normalize_space(line).lower()
    return any(cue in lowered for cue in NEGATION_CUES)


def extract_required_checks(answer: str, limit: int = 2) -> list[str]:
    lines = []
    fallback = []
    for line in answer_lines(answer):
        for canonical in expand_check_candidates(line):
            lowered = canonical.lower()
            if not canonical:
                continue
            if lowered.startswith("do not:") or lowered.startswith("escalate to:"):
                continue
            if is_meta_or_context_line(canonical):
                continue
            if looks_actionable_check(canonical):
                lines.append(canonical)
            else:
                fallback.append(canonical)
    if not lines:
        lines = fallback
    if not lines:
        for line in answer_lines(answer):
            canonical = canonicalize_check_line(line)
            if canonical.lower().startswith("do not:"):
                lines.append(canonical)
    return lines[:limit]


def extract_forbidden_checks(answer: str, limit: int = 2) -> list[str]:
    found = []
    for line in answer_lines(answer):
        canonical = canonicalize_check_line(line)
        lowered = canonical.lower()
        if lowered.startswith("do not:"):
            found.append(canonical.split(":", 1)[1].strip() if ":" in canonical else canonical)
    return found[:limit]


def extract_escalation_targets(answer: str) -> list[str]:
    for line in answer_lines(answer):
        canonical = canonicalize_check_line(line)
        lowered = canonical.lower()
        if lowered.startswith("escalate to:"):
            payload = canonical.split(":", 1)[1].strip() if ":" in canonical else canonical
            parts = re.split(r",| and ", payload)
            filtered = [
                normalize_space(part)
                for part in parts
                if normalize_space(part)
                and any(role in normalize_space(part).lower() for role in ESCALATION_ROLE_CUES)
            ]
            if filtered:
                return filtered
            return [normalize_space(parts[0])] if parts and normalize_space(parts[0]) else []
    return []


def paraphrase_question(question: str, category: str, domain: str) -> str:
    q = normalize_space(question)
    prefix_map = {
        "regulatory": f"For domain {domain}, confirm this compliance point:",
        "procedural": f"In a real shipboard watch for domain {domain}, what is the required action:",
        "troubleshooting": f"In domain {domain}, diagnose and act on this case:",
        "safety": f"In domain {domain}, handle this safety situation:",
        "trap": f"In domain {domain}, reject the unsafe shortcut in this case:",
        "calculation": f"In domain {domain}, work through this calculation or threshold case:",
    }
    prefix = prefix_map.get(category, f"In domain {domain}, answer this case:")
    return f"{prefix} {q}"


def benchmark_record_from_source(record: dict, category: str, benchmark_id: str, source_tag: str) -> dict:
    question = paraphrase_question(coalesce_question(record), category, normalize_space(record.get("domain_letter") or "UNK"))
    answer = record_answer(record)
    return {
        "id": benchmark_id,
        "category": category,
        "domain": normalize_space(record.get("domain_letter") or "UNK"),
        "subtopic_id": normalize_space(record.get("subtopic_id")),
        "question": question,
        "reference_answer": answer,
        "required_checks": extract_required_checks(answer),
        "forbidden_checks": extract_forbidden_checks(answer),
        "escalation_targets": extract_escalation_targets(answer),
        "source": source_tag,
    }


def infer_category(record: dict) -> str:
    rtype = normalize_space(record.get("type")).lower()
    if rtype == "trap":
        return "trap"
    if rtype == "regulatory":
        return "regulatory"
    if rtype == "procedural":
        return "procedural"
    if rtype == "safety":
        return "safety"
    if rtype in {"troubleshooting", "diagnostic_multistep", "diagnostic"}:
        return "troubleshooting"
    if rtype == "calculation":
        return "calculation"
    return "procedural"


def score_response(
    response: str,
    *,
    required_checks: list[str],
    forbidden_checks: list[str],
    escalation_targets: list[str],
    category: str,
    do_not: list[str] | None = None,
) -> dict:
    text = strip_think(normalize_multiline(response))
    lowered = text.lower()
    line_candidates = [canonicalize_check_line(line) for line in answer_lines(text)]
    line_candidates = [line for line in line_candidates if line]
    candidates = list(line_candidates)
    full_candidate = canonicalize_check_line(text)
    if full_candidate:
        candidates.append(full_candidate)
    required_hits = [
        check for check in required_checks if any(semantic_match(check, candidate) for candidate in candidates)
    ]
    forbidden_hits = [
        check
        for check in forbidden_checks
        if any(forbidden_match(check, candidate) and not line_has_negation(candidate) for candidate in line_candidates)
    ]
    # Alias-aware escalation matching
    escalation_hits = [
        target
        for target in escalation_targets
        if any(escalation_alias_match(target, candidate) for candidate in candidates)
    ]
    # Check do_not slot: response should contain a "Do not:" line
    do_not_checks = do_not or []
    do_not_hits = []
    if do_not_checks:
        response_do_not_lines = [
            c for c in line_candidates if canonicalize_check_line(c).lower().startswith("do not:")
        ]
        for prohibition in do_not_checks:
            for rl in response_do_not_lines:
                payload = rl.split(":", 1)[1].strip() if ":" in rl else rl
                if semantic_match(prohibition, payload):
                    do_not_hits.append(prohibition)
                    break
    has_modal = any(cue in lowered for cue in REGULATORY_MODAL_CUES)
    trap_ok = trap_response_passes(text) if category == "trap" else True
    if category == "regulatory" and not has_modal:
        trap_ok = False
    passed = len(required_hits) == len(required_checks) and not forbidden_hits and (
        not escalation_targets or bool(escalation_hits)
    )
    if category in ("trap", "regulatory"):
        passed = passed and trap_ok
    return {
        "pass": passed,
        "required_hit_count": len(required_hits),
        "required_total": len(required_checks),
        "forbidden_hits": forbidden_hits,
        "escalation_hit_count": len(escalation_hits),
        "escalation_total": len(escalation_targets),
        "do_not_hit_count": len(do_not_hits),
        "do_not_total": len(do_not_checks),
        "trap_pass": trap_ok,
        "has_modal": has_modal,
    }


def question_sort_key(record: dict) -> str:
    return f"{normalize_space(record.get('domain_letter'))}\t{normalize_space(record.get('subtopic_id'))}\t{coalesce_question(record).lower()}"


def bucket_records_by_domain(records: list[dict]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {}
    for record in records:
        domain = normalize_space(record.get("domain_letter") or "UNK")
        buckets.setdefault(domain, []).append(record)
    for key in buckets:
        buckets[key] = sorted(buckets[key], key=question_sort_key)
    return buckets


def round_robin_pick(records: list[dict], n: int) -> list[dict]:
    buckets = bucket_records_by_domain(records)
    domains = sorted(buckets.keys())
    picked: list[dict] = []
    seen = set()
    while len(picked) < n and domains:
        next_domains = []
        for domain in domains:
            bucket = buckets[domain]
            if not bucket:
                continue
            candidate = bucket.pop(0)
            qkey = coalesce_question(candidate).lower()
            if qkey in seen:
                if bucket:
                    next_domains.append(domain)
                continue
            seen.add(qkey)
            picked.append(candidate)
            if bucket and len(picked) < n:
                next_domains.append(domain)
            if len(picked) >= n:
                break
        domains = next_domains
    return picked


def extract_numeric_candidates(record: dict) -> bool:
    blob = " ".join(
        [
            normalize_space(record.get("subtopic")),
            normalize_space(record.get("q") or record.get("question")),
            normalize_space(record.get("a") or record.get("answer")),
            normalize_space(record.get("difficulty_hint")),
        ]
    ).lower()
    patterns = (
        " bar",
        " rpm",
        " kw",
        " mm",
        " cm",
        " m ",
        "%",
        "kpa",
        "ppm",
        "gm",
        "kg",
        "temperature",
        "limit",
        "interval",
        "hours",
        "minutes",
        "pressure",
        "clearance",
        "feed rate",
        "calculation",
    )
    return any(token in blob for token in patterns)


def merge_adapter_into_base(adapter_dir: Path, output_dir: Path, phase_tag: str) -> Path:
    gate_require_dir(adapter_dir, phase_tag)
    output_dir.mkdir(parents=True, exist_ok=True)
    model = load_merged_model_from_adapter(adapter_dir, phase_tag)
    tokenizer = load_tokenizer()
    model.save_pretrained(str(output_dir), safe_serialization=True)
    tokenizer.save_pretrained(str(output_dir))
    return output_dir


def generate_response(model, tokenizer, question: str, *, mode: str = "no_think", max_new_tokens: int = 220) -> str:
    system_prompt = SYSTEM_PROMPT_NOTHINK if mode == "no_think" else SYSTEM_PROMPT_THINK
    prompt = apply_chat(
        tokenizer,
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    try:
        generation_prompt = tokenizer.apply_chat_template(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception:
        generation_prompt = f"{prompt}\n<|im_start|>assistant\n"
    device = next(model.parameters()).device
    encoded = tokenizer(generation_prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output[0][encoded["input_ids"].shape[1] :], skip_special_tokens=True)
