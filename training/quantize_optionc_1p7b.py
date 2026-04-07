#!/usr/bin/env python3
"""Quantize the final 1.7B local candidate and validate Q4/Q5 against the fast local benchmark."""

from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from phase2_optionc_common import (
    DEFAULT_BENCHMARK,
    log_pipeline,
    merge_adapter_into_base,
    read_jsonl,
    score_response,
)

LLAMA_CPP = Path("/home/mohanganesh/ship/llama.cpp")
DEPLOY_DIR = Path("/home/mohanganesh/ship/deploy")
MERGED_DIR = Path("/home/mohanganesh/ship/training/merged/maritime-1.7b-local-final")
DEFAULT_LLAMA_THREADS = max(1, os.cpu_count() or 1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantize the local 1.7B candidate and validate Q4/Q5.")
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--reference-eval", type=Path, required=True)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("/home/mohanganesh/ship/logs/quantize_optionc_1p7b_summary.json"),
    )
    return parser.parse_args()


def require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")


def ensure_llama_cpp_target(binary_path: Path, target: str) -> Path:
    if binary_path.exists():
        return binary_path
    build_dir = LLAMA_CPP / "build"
    subprocess.run(["cmake", "--build", str(build_dir), "--target", target, "-j", "8"], check=True)
    require(binary_path, target)
    return binary_path


def run_convert_hf_to_gguf(convert_py: Path, model_dir: Path, outfile: Path) -> None:
    wrapper = (
        "import runpy, sys, torch; "
        "torch.uint64 = getattr(torch, 'uint64', torch.int64); "
        "torch.uint32 = getattr(torch, 'uint32', torch.int32); "
        "torch.uint16 = getattr(torch, 'uint16', torch.int16); "
        "torch.float8_e4m3fn = getattr(torch, 'float8_e4m3fn', torch.float16); "
        "torch.float8_e5m2 = getattr(torch, 'float8_e5m2', torch.float16); "
        f"sys.argv = {[str(convert_py), str(model_dir), '--outtype', 'f16', '--outfile', str(outfile)]!r}; "
        f"runpy.run_path({str(convert_py)!r}, run_name='__main__')"
    )
    subprocess.run([sys.executable, "-c", wrapper], check=True)


def wait_for_health(port: int, timeout_s: int = 300) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def server_chat(port: int, question: str) -> str | None:
    payload = {
        "model": "maritime",
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.0,
        "max_tokens": 160,
    }
    try:
        response = requests.post(f"http://127.0.0.1:{port}/v1/chat/completions", json=payload, timeout=120)
        if response.status_code != 200:
            return None
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def evaluate_gguf(gguf_path: Path, benchmark: list[dict], max_per_category: int) -> dict:
    bins = {
        "server": LLAMA_CPP / "build" / "bin" / "llama-server",
    }
    require(bins["server"], "llama-server")
    thread_count = int(os.environ.get("SHIP_LLAMA_THREADS", str(DEFAULT_LLAMA_THREADS)))
    port = 9011 if "q4" in gguf_path.name else 9012
    proc = subprocess.Popen(
        [
            str(bins["server"]),
            "-m",
            str(gguf_path),
            "--n-gpu-layers",
            "999",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--threads",
            str(thread_count),
            "--ctx-size",
            "2048",
            "--no-mmap",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_health(port, timeout_s=600):
            raise RuntimeError(f"llama-server failed for {gguf_path}")
        categories: dict[str, list[dict]] = {}
        for item in benchmark:
            categories.setdefault(item["category"], []).append(item)
        results = {"gguf": str(gguf_path), "categories": {}}
        for category, items in categories.items():
            subset = items[:max_per_category]
            passed = 0
            for item in subset:
                answer = server_chat(port, item["question"]) or ""
                score = score_response(
                    answer,
                    required_checks=item.get("required_checks", []),
                    forbidden_checks=item.get("forbidden_checks", []),
                    escalation_targets=item.get("escalation_targets", []),
                    category=category,
                )
                if score["pass"]:
                    passed += 1
            tested = len(subset)
            results["categories"][category] = {
                "tested": tested,
                "pass_count": passed,
                "pass_rate": round((passed / tested * 100.0), 2) if tested else 0.0,
            }
        return results
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main() -> None:
    args = parse_args()
    require(args.adapter_dir / "adapter_model.safetensors", "adapter checkpoint")
    require(args.reference_eval, "reference eval")
    benchmark = read_jsonl(args.benchmark)
    reference = json.loads(args.reference_eval.read_text(encoding="utf-8"))

    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_DIR.mkdir(parents=True, exist_ok=True)

    log_pipeline(f"PHASE_5_LOCAL_QUANTIZE_1.7B STATUS: MERGE START adapter={args.adapter_dir}")
    merge_adapter_into_base(args.adapter_dir, MERGED_DIR, "PHASE_5_LOCAL_QUANTIZE_1.7B")
    gc.collect()

    convert_py = LLAMA_CPP / "convert_hf_to_gguf.py"
    quantize_bin = LLAMA_CPP / "build" / "bin" / "llama-quantize"
    require(convert_py, "convert_hf_to_gguf.py")
    ensure_llama_cpp_target(quantize_bin, "llama-quantize")

    f16_gguf = DEPLOY_DIR / "maritime-1.7b-local-f16.gguf"
    q4 = DEPLOY_DIR / "maritime-1.7b-local-q4km.gguf"
    q5 = DEPLOY_DIR / "maritime-1.7b-local-q5km.gguf"

    run_convert_hf_to_gguf(convert_py, MERGED_DIR, f16_gguf)
    subprocess.run([str(quantize_bin), str(f16_gguf), str(q4), "Q4_K_M"], check=True)
    q4_eval = evaluate_gguf(q4, benchmark, max_per_category=10)

    chosen = q4
    chosen_eval = q4_eval
    reference_categories = reference.get("categories", {})
    q4_reg = q4_eval["categories"].get("regulatory", {}).get("pass_rate", 0.0)
    q4_safe = q4_eval["categories"].get("safety", {}).get("pass_rate", 0.0)
    ref_reg = reference_categories.get("regulatory", {}).get("pass_rate", 0.0)
    ref_safe = reference_categories.get("safety", {}).get("pass_rate", 0.0)

    if q4_reg < ref_reg - 3.0 or q4_safe < ref_safe - 3.0:
        subprocess.run([str(quantize_bin), str(f16_gguf), str(q5), "Q5_K_M"], check=True)
        q5_eval = evaluate_gguf(q5, benchmark, max_per_category=10)
        chosen = q5
        chosen_eval = q5_eval
    else:
        q5_eval = None

    summary = {
        "adapter_dir": str(args.adapter_dir),
        "reference_eval": reference,
        "q4_eval": q4_eval,
        "q5_eval": q5_eval,
        "chosen": str(chosen),
        "chosen_eval": chosen_eval,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log_pipeline(f"PHASE_5_LOCAL_QUANTIZE_1.7B STATUS: COMPLETE chosen={chosen}")


if __name__ == "__main__":
    main()
