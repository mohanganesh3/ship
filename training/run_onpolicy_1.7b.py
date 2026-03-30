#!/usr/bin/env python3
"""On-Policy Correction Round — GPU student generation + teacher judgment.

Hard rules:
- Single GPU only (default: GPU0 via CUDA_VISIBLE_DEVICES=0)
- fp16 only (no bf16)
- Must be run from .venv-train
- Must fail fast (gate) if required artifacts/data are missing
"""

import os, sys, json, time, random, logging
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

import torch

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
SFT2_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/sft2-1.7b/final")
BASE_MODEL = "/home/mohanganesh/ship/models/student-1.7b"
SFT_DATA = Path(
    os.environ.get(
        "SHIP_SFT_DATA",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl",
    )
)
STUDENT_ANSWERS = Path(
    os.environ.get(
        "SHIP_STUDENT_ANSWERS",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/generation/student_answers_1.7b.jsonl",
    )
)
TEACHER_JUDGMENTS = Path(
    os.environ.get(
        "SHIP_TEACHER_JUDGMENTS",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/generation/teacher_judgments_1.7b.jsonl",
    )
)
SFT_CORRECTIONS = Path(
    os.environ.get(
        "SHIP_CORRECTIONS_DATA",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_corrections_1.7b.jsonl",
    )
)
ORPO_PAIRS = Path(
    os.environ.get(
        "SHIP_ORPO_DATA",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/orpo_pairs_1.7b.jsonl",
    )
)

TEACHER_PORTS = [8000, 8001, 8002, 8003]

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

def find_alive_teacher():
    if requests is None:
        return None
    for port in TEACHER_PORTS:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
            if r.status_code == 200:
                return port
        except Exception:
            pass
    return None

def call_teacher(port, messages, max_tokens=256):
    if requests is None:
        return None
    payload = {
        "model": "teacher",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    for attempt in range(3):
        try:
            r = requests.post(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                json=payload, timeout=120
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            time.sleep(5)
    return None

def main():
    phase = "PHASE_3_ONPOLICY_1.7B"
    ensure_venv_train(phase)
    if requests is None:
        log_pipeline(f"{phase} FAIL — DEPENDENCY_GATE: 'requests' not installed in this environment")
        raise SystemExit(1)

    random.seed(1337)
    torch.manual_seed(1337)

    if not torch.cuda.is_available():
        log_pipeline(f"{phase} FAIL — CUDA_GATE: torch.cuda.is_available() is false")
        raise SystemExit(1)

    vis = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    if vis.strip() == "":
        log_pipeline(f"{phase} FAIL — CUDA_GATE: CUDA_VISIBLE_DEVICES is empty")
        raise SystemExit(1)

    log_pipeline(f"{phase} STATUS: STARTING")

    gate_require_dir(SFT2_CHECKPOINT, phase)
    gate_require_file(SFT_DATA, phase)

    # Check teacher is alive
    teacher_port = find_alive_teacher()
    if teacher_port is None:
        log_pipeline("PHASE_3_ONPOLICY_1.7B STATUS: FAIL — no teacher server alive on any port")
        import sys; sys.exit(1)
    logger.info(f"Teacher server alive on port {teacher_port}")

    # Load student model
    logger.info("Loading student model (post-SFT2)...")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map={"": 0},
        trust_remote_code=True, low_cpu_mem_usage=True
    )
    if hasattr(base, "config"):
        base.config.use_cache = True
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    student_model = PeftModel.from_pretrained(base, str(SFT2_CHECKPOINT))
    student_model = student_model.merge_and_unload()
    student_model.eval()

    if hasattr(student_model, "config"):
        student_model.config.use_cache = True

    device = next(student_model.parameters()).device

    # Load questions from sft_curated
    all_records = []
    with open(SFT_DATA) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                all_records.append(json.loads(line))
            except Exception:
                pass

    if len(all_records) < 5000:
        log_pipeline(f"{phase} FAIL — DATASET_GATE: need at least 5000 records in sft_curated.jsonl, got {len(all_records)}")
        raise SystemExit(1)

    # Prioritize regulatory and diagnostic types
    priority = [r for r in all_records if r.get("type","") in ("regulatory","diagnostic_multistep","troubleshooting")]
    other = [r for r in all_records if r not in priority]
    sample_records = (priority + other)[:5000]
    random.shuffle(sample_records)
    if len(sample_records) < 5000:
        log_pipeline(f"{phase} FAIL — DATASET_GATE: could only sample {len(sample_records)} questions (< 5000)")
        raise SystemExit(1)
    logger.info(f"Running on-policy generation for {len(sample_records)} questions...")

    STUDENT_ANSWERS.parent.mkdir(parents=True, exist_ok=True)
    TEACHER_JUDGMENTS.parent.mkdir(parents=True, exist_ok=True)
    SFT_CORRECTIONS.parent.mkdir(parents=True, exist_ok=True)
    ORPO_PAIRS.parent.mkdir(parents=True, exist_ok=True)

    sft_corrections_count = 0
    orpo_pairs_count = 0

    with open(STUDENT_ANSWERS, "w") as sa_f, \
         open(TEACHER_JUDGMENTS, "w") as tj_f, \
         open(SFT_CORRECTIONS, "w") as sc_f, \
         open(ORPO_PAIRS, "w") as op_f:

        for i, rec in enumerate(sample_records):
            q = rec.get("q", rec.get("question", ""))
            gold_answer = rec.get("a", rec.get("answer", ""))
            if not q or not gold_answer:
                continue

            # Student generates answer
            prompt = (
                "<|im_start|>system\nYou are a maritime assistant. "
                "Answer from your knowledge only.\n/no_think<|im_end|>\n"
                f"<|im_start|>user\n{q}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )
            input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)
            with torch.no_grad():
                out = student_model.generate(
                    input_ids, max_new_tokens=200, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id
                )
            student_answer = tokenizer.decode(out[0][input_ids.shape[1]:], skip_special_tokens=True)

            # Save student answer
            sa_entry = {"question": q, "student_answer": student_answer, "gold_answer": gold_answer, "idx": i}
            sa_f.write(json.dumps(sa_entry) + "\n")

            # Teacher judges
            judge_prompt = f"""You are evaluating a maritime assistant's answer.

SOURCE QUESTION: {q}
GOLD ANSWER: {gold_answer}
STUDENT ANSWER: {student_answer}

/no_think
Rate the student answer 1-5 (5=correct, complete, safe; 1=wrong, incomplete, dangerous).
If score ≤ 3, provide the correct answer.
Output JSON only: {{"score": N, "correct_answer": "..." or null, "error_type": "factual_error|missing_step|modal_error|hallucination|null"}}"""

            judge_messages = [{"role": "user", "content": judge_prompt}]
            judge_response = call_teacher(teacher_port, judge_messages, max_tokens=300)

            if not judge_response:
                continue

            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{[^{}]+\}', judge_response, re.DOTALL)
                if not json_match:
                    continue
                judgment = json.loads(json_match.group())
            except Exception:
                continue

            score = judgment.get("score", 5)
            correct_answer = judgment.get("correct_answer")
            error_type = judgment.get("error_type", "null")

            tj_entry = {"question": q, "score": score, "error_type": error_type,
                        "correct_answer": correct_answer, "idx": i}
            tj_f.write(json.dumps(tj_entry) + "\n")

            if score <= 3 and correct_answer:
                # Add to SFT correction dataset
                sc_entry = {"q": q, "a": correct_answer, "type": rec.get("type", "factual"),
                            "source": "onpolicy_correction"}
                sc_f.write(json.dumps(sc_entry) + "\n")
                sft_corrections_count += 1

            if score in (3, 4) and correct_answer:
                # Close-but-wrong → ORPO pair
                op_entry = {
                    "prompt": q,
                    "chosen": correct_answer,
                    "rejected": student_answer,
                    "rejection_type": "on_policy",
                    "risk_tag": "safety_critical" if rec.get("type") == "safety" else "general"
                }
                op_f.write(json.dumps(op_entry) + "\n")
                orpo_pairs_count += 1

            if (i + 1) % 100 == 0:
                logger.info(f"Progress: {i+1}/{len(sample_records)} — corrections: {sft_corrections_count}, orpo_pairs: {orpo_pairs_count}")

    logger.info(f"On-policy complete: {sft_corrections_count} corrections, {orpo_pairs_count} ORPO pairs")

    # === ON-POLICY GATE CHECKS ===
    if sft_corrections_count < 1000 or orpo_pairs_count < 2000:
        log_pipeline(
            f"{phase} STATUS: FAIL — GATE: corrections={sft_corrections_count} (need >=1000), "
            f"orpo_pairs={orpo_pairs_count} (need >=2000)"
        )
        raise SystemExit(1)

    log_pipeline(f"{phase} STATUS: COMPLETE. {sft_corrections_count} corrections, {orpo_pairs_count} ORPO pairs")

if __name__ == "__main__":
    main()
