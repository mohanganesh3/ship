#!/usr/bin/env python3
"""Phase 5 — Quantize student-4B to GGUF.

CPU-only utility script.
- Merges ORPO LoRA into base HF weights
- Converts to GGUF f16
- Quantizes to Q4_K_M (fallback to Q5_K_M if modal precision drops)

Logs phase status to logs/pipeline_execution.log (ISO UTC timestamps).
"""

from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

os.environ.setdefault("OMP_NUM_THREADS", "48")
os.environ.setdefault("MKL_NUM_THREADS", "48")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "48")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
BASE_MODEL = "/home/mohanganesh/ship/models/student-4b"
ORPO_CHECKPOINT = Path("/home/mohanganesh/ship/training/checkpoints/orpo-4b/final")
MERGED_DIR = Path("/home/mohanganesh/ship/training/merged/maritime-4b-merged")
DEPLOY_DIR = Path("/home/mohanganesh/ship/deploy")
LLAMA_CPP = Path("/home/mohanganesh/ship/llama.cpp")


def log_pipeline(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def ensure_venv_train(phase_tag: str) -> None:
    exe = os.path.realpath(sys.executable)
    if "/.venv-train/" not in exe:
        log_pipeline(f"{phase_tag} FAIL — ENV_GATE: must run with .venv-train python (got: {exe})")
        raise SystemExit(1)


def require_requests(phase_tag: str) -> None:
    if requests is None:
        log_pipeline(f"{phase_tag} FAIL — DEPENDENCY_GATE: 'requests' not installed in this environment")
        raise SystemExit(1)


@dataclass
class LlamaBinaries:
    convert_py: Path
    quantize_bin: Path
    server_bin: Path


def find_llama_bins(llama_cpp_dir: Path) -> LlamaBinaries:
    convert_py = llama_cpp_dir / "convert_hf_to_gguf.py"
    quantize_bin = llama_cpp_dir / "build" / "bin" / "llama-quantize"
    server_bin = llama_cpp_dir / "build" / "bin" / "llama-server"

    missing: list[str] = []
    if not convert_py.exists():
        missing.append(str(convert_py))
    if not quantize_bin.exists():
        missing.append(str(quantize_bin))
    if not server_bin.exists():
        missing.append(str(server_bin))

    if missing:
        raise FileNotFoundError(
            "Missing llama.cpp artifacts. Build llama.cpp first. Missing: " + ", ".join(missing)
        )

    return LlamaBinaries(convert_py=convert_py, quantize_bin=quantize_bin, server_bin=server_bin)


def wait_for_health(url: str, timeout_s: int = 300) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def server_chat(port: int, prompt: str, max_tokens: int = 160) -> str | None:
    payload = {
        "model": "maritime",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    try:
        r = requests.post(f"http://127.0.0.1:{port}/v1/chat/completions", json=payload, timeout=120)
        if r.status_code != 200:
            return None
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def main() -> None:
    phase = "PHASE_5_QUANTIZE_4B"
    ensure_venv_train(phase)
    require_requests(phase)
    log_pipeline(f"{phase} STATUS: STARTING")

    try:
        bins = find_llama_bins(LLAMA_CPP)
    except Exception as e:
        log_pipeline(f"{phase} STATUS: FAIL — llama.cpp artifacts missing: {e}")
        raise

    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    if not ORPO_CHECKPOINT.exists():
        log_pipeline(f"{phase} STATUS: FAIL — ORPO checkpoint missing: {ORPO_CHECKPOINT}")
        raise FileNotFoundError(str(ORPO_CHECKPOINT))

    # Step 1: merge LoRA
    log_pipeline(f"{phase} STATUS: MERGE_LORA_START")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float32,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    model = PeftModel.from_pretrained(base, str(ORPO_CHECKPOINT))
    model = model.merge_and_unload()

    model.save_pretrained(str(MERGED_DIR), safe_serialization=True)
    tok.save_pretrained(str(MERGED_DIR))

    del model
    del base
    gc.collect()
    log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: MERGE_LORA_DONE merged_dir={MERGED_DIR}")

    # Step 2: convert to GGUF f16
    f16_gguf = DEPLOY_DIR / "maritime-4b-f16.gguf"
    log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: GGUF_F16_CONVERT_START out={f16_gguf}")
    r = subprocess.run(
        [
            "/home/mohanganesh/ship/.venv-train/bin/python",
            str(bins.convert_py),
            str(MERGED_DIR),
            "--outtype",
            "f16",
            "--outfile",
            str(f16_gguf),
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        log_pipeline("PHASE_5_QUANTIZE_4B STATUS: FAIL — f16 GGUF conversion failed")
        sys.stderr.write(r.stderr)
        raise RuntimeError("convert_hf_to_gguf.py failed")

    # Step 3: quantize Q4_K_M
    q4km = DEPLOY_DIR / "maritime-4b-q4km.gguf"
    log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: QUANTIZE_Q4KM_START out={q4km}")
    r = subprocess.run([str(bins.quantize_bin), str(f16_gguf), str(q4km), "Q4_K_M"], capture_output=True, text=True)
    if r.returncode != 0:
        log_pipeline("PHASE_5_QUANTIZE_4B STATUS: FAIL — Q4_K_M quantization failed")
        sys.stderr.write(r.stderr)
        raise RuntimeError("llama-quantize failed")

    # Step 4: modal precision quick-check via llama-server
    log_pipeline("PHASE_5_QUANTIZE_4B STATUS: POST_QUANT_VALIDATION_START")
    port = 9002
    proc = subprocess.Popen(
        [
            str(bins.server_bin),
            "-m",
            str(q4km),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--threads",
            "24",
            "--ctx-size",
            "2048",
            "--no-mmap",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        if not wait_for_health(f"http://127.0.0.1:{port}/health", timeout_s=300):
            log_pipeline("PHASE_5_QUANTIZE_4B STATUS: FAIL — Q4_K_M server failed to start")
            raise RuntimeError("llama-server health check failed")

        sft_path = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl")
        reg: list[dict] = []
        if sft_path.exists():
            with open(sft_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if rec.get("type") == "regulatory":
                        reg.append(rec)

        if not reg:
            log_pipeline("PHASE_5_QUANTIZE_4B STATUS: WARNING — no regulatory records found for validation")
        else:
            import random

            random.seed(1234)
            sample = random.sample(reg, min(20, len(reg)))
            hits = 0
            for rec in sample:
                q = rec.get("q") or rec.get("question") or ""
                if not q:
                    continue
                resp = server_chat(port, q)
                if not resp:
                    continue
                if any(w in resp.lower() for w in ("shall", "must", "required", "require")):
                    hits += 1

            pct = hits / max(1, len(sample)) * 100
            log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: Q4KM_MODAL_PRECISION {pct:.1f}%")

            if pct < 85:
                log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: Q4KM_TOO_LOW fallback=Q5_K_M")
                q5km = DEPLOY_DIR / "maritime-4b-q5km.gguf"
                r = subprocess.run([str(bins.quantize_bin), str(f16_gguf), str(q5km), "Q5_K_M"], capture_output=True, text=True)
                if r.returncode != 0:
                    log_pipeline("PHASE_5_QUANTIZE_4B STATUS: FAIL — Q5_K_M fallback quantization failed")
                    sys.stderr.write(r.stderr)
                    raise RuntimeError("Q5_K_M fallback failed")
                log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: COMPLETE fallback_model={q5km}")
            else:
                log_pipeline(f"PHASE_5_QUANTIZE_4B STATUS: COMPLETE model={q4km}")

    finally:
        try:
            proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
