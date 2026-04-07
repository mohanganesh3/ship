#!/usr/bin/env python3
"""Autonomous follow-up runner for the 1.7B maritime backend pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path("/home/mohanganesh/ship")
TRAIN_DIR = ROOT / "training"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "ship" / "maritime_pipeline" / "data" / "final"
PYTHON = ROOT / ".venv-train" / "bin" / "python"

BENCHMARK = DATA_DIR / "local_benchmark_1p7b.jsonl"
CURRENT_CORRECTION = TRAIN_DIR / "checkpoints" / "phase3-local-correction-1.7b" / "final"
CURRENT_FASTREF = LOG_DIR / "local_eval_correction_gpu1_fastref_1p7b.json"
FOLLOWUP_LOG = LOG_DIR / "autonomous_followup_1p7b.log"
FOLLOWUP_SUMMARY = LOG_DIR / "autonomous_followup_1p7b_summary.json"

THRESHOLDS = {
    "regulatory": 85.0,
    "procedural": 80.0,
    "troubleshooting": 75.0,
    "safety": 90.0,
    "calculation": 80.0,
    "trap": 80.0,
}


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    FOLLOWUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FOLLOWUP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{ts}] {msg}\n")
    print(msg, flush=True)


def query_gpus() -> list[dict]:
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
        text=True,
    )
    rows = []
    for line in out.splitlines():
        idx, used, total, util = [int(x.strip()) for x in line.split(",")]
        rows.append({"index": idx, "used": used, "free": total - used, "util": util})
    return rows


def choose_gpu(min_free_mb: int, *, exclude: set[int] | None = None) -> int:
    exclude = exclude or set()
    while True:
        rows = [r for r in query_gpus() if r["index"] not in exclude]
        candidates = [r for r in rows if r["free"] >= min_free_mb]
        if candidates:
            best = max(candidates, key=lambda r: (r["free"], -r["util"], -r["index"]))
            log(f"GPU_SELECT gpu={best['index']} free_mb={best['free']} util={best['util']} min_free_mb={min_free_mb}")
            return best["index"]
        log(f"GPU_WAIT min_free_mb={min_free_mb} snapshot={rows}")
        time.sleep(60)


def run(cmd: list[str], *, gpu: int | None = None, env_extra: dict[str, str] | None = None, log_path: Path | None = None) -> None:
    env = os.environ.copy()
    if gpu is not None:
        env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    if env_extra:
        env.update(env_extra)
    stdout = subprocess.PIPE if log_path is None else log_path.open("a", encoding="utf-8")
    try:
        proc = subprocess.run(cmd, cwd=TRAIN_DIR, env=env, stdout=stdout, stderr=subprocess.STDOUT, text=True, check=True)
        if proc.stdout:
            log(proc.stdout)
    finally:
        if log_path is not None:
            stdout.close()


def read_eval(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def eval_passes(result: dict) -> bool:
    for category, bucket in result.get("categories", {}).items():
        if bucket.get("pass_rate", 0.0) < THRESHOLDS.get(category, 0.0):
            return False
    return True


def wait_for_eval(path: Path, timeout_s: int = 7200) -> dict:
    start = time.time()
    while time.time() - start < timeout_s:
        if path.exists():
            return read_eval(path)
        time.sleep(30)
    raise TimeoutError(f"Timed out waiting for eval output: {path}")


def correction_output(iter_idx: int) -> Path:
    return TRAIN_DIR / "checkpoints" / f"phase3-local-correction-iter{iter_idx}-1.7b"


def correction_fastref(iter_idx: int) -> Path:
    return LOG_DIR / f"local_eval_correction_iter{iter_idx}_fastref_1p7b.json"


def orpo_output(iter_idx: int) -> Path:
    return TRAIN_DIR / "checkpoints" / f"phase4-local-orpo-iter{iter_idx}-1.7b"


def orpo_smoke_output(iter_idx: int) -> Path:
    return TRAIN_DIR / "checkpoints" / f"phase4-local-orpo-smoke-iter{iter_idx}-1.7b"


def main() -> None:
    log("FOLLOWUP START")
    summary: dict[str, object] = {"steps": []}

    latest_adapter = CURRENT_CORRECTION
    latest_eval = wait_for_eval(CURRENT_FASTREF)
    summary["initial_eval"] = latest_eval["categories"]
    summary["steps"].append({"name": "wait_initial_eval", "status": latest_eval["overall_status"]})

    max_iters = 3
    iter_idx = 1
    while not eval_passes(latest_eval) and iter_idx <= max_iters:
        corr_data = DATA_DIR / f"sft_corrections_optionc_iter{iter_idx}_1p7b.jsonl"
        corr_summary = DATA_DIR / f"sft_corrections_optionc_iter{iter_idx}_1p7b_summary.json"
        next_output = correction_output(iter_idx)
        next_final = next_output / "final"
        next_eval = correction_fastref(iter_idx)

        if not next_final.exists():
            log(f"CORRECTION_ITER start iter={iter_idx} base={latest_adapter}")
            run(
                [
                    str(PYTHON),
                    "build_local_corrections_1p7b.py",
                    "--benchmark",
                    str(BENCHMARK),
                    "--eval-results",
                    str(CURRENT_FASTREF if iter_idx == 1 else correction_fastref(iter_idx - 1)),
                    "--output",
                    str(corr_data),
                    "--summary",
                    str(corr_summary),
                ],
                log_path=LOG_DIR / f"build_corrections_iter{iter_idx}.log",
            )

            train_gpu = choose_gpu(8000)
            run(
                [str(PYTHON), "run_local_correction_1p7b.py", "--epochs", "2.0"],
                gpu=train_gpu,
                env_extra={
                    "SHIP_CORRECTIONS_DATA": str(corr_data),
                    "SHIP_CORRECTION_BASE": str(latest_adapter),
                    "SHIP_CORRECTION_OUTPUT_DIR": str(next_output),
                    "PYTHONUNBUFFERED": "1",
                },
                log_path=LOG_DIR / f"phase3_local_correction_iter{iter_idx}.log",
            )
        else:
            log(f"CORRECTION_ITER skipping training for iter={iter_idx}, {next_final} exists")
            train_gpu = -1
        latest_adapter = next_final

        eval_gpu = choose_gpu(5000, exclude={train_gpu})
        run(
            [
                str(PYTHON),
                "run_local_eval_1p7b.py",
                "--adapter-dir",
                str(latest_adapter),
                "--benchmark",
                str(BENCHMARK),
                "--output",
                str(next_eval),
                "--label",
                f"correction_iter{iter_idx}_fastref",
                "--max-per-category",
                "10",
                "--max-new-tokens",
                "300",
            ],
            gpu=eval_gpu,
            env_extra={"PYTHONUNBUFFERED": "1"},
            log_path=LOG_DIR / f"local_eval_correction_iter{iter_idx}_fastref.log",
        )
        latest_eval = read_eval(next_eval)
        summary["steps"].append(
            {
                "name": f"correction_iter_{iter_idx}",
                "status": latest_eval["overall_status"],
                "adapter": str(latest_adapter),
                "eval": str(next_eval),
            }
        )
        iter_idx += 1

    if eval_passes(latest_eval):
        orpo_pairs = DATA_DIR / "orpo_pairs_optionc_followup_1p7b.jsonl"
        orpo_summary = DATA_DIR / "orpo_pairs_optionc_followup_1p7b_summary.json"
        smoke_dir = orpo_smoke_output(iter_idx)
        full_dir = orpo_output(iter_idx)

        run(
            [
                str(PYTHON),
                "build_local_orpo_pairs_1p7b.py",
                "--benchmark",
                str(BENCHMARK),
                "--eval-results",
                str(CURRENT_FASTREF if iter_idx == 1 else correction_fastref(iter_idx - 1)),
                "--output",
                str(orpo_pairs),
                "--summary",
                str(orpo_summary),
            ],
            log_path=LOG_DIR / "build_orpo_followup.log",
        )

        orpo_gpu = choose_gpu(8000)
        run(
            [
                str(PYTHON),
                "run_local_orpo_1p7b.py",
                "--smoke",
                "--data",
                str(orpo_pairs),
                "--base-adapter",
                str(latest_adapter),
                "--smoke-dir",
                str(smoke_dir),
            ],
            gpu=orpo_gpu,
            env_extra={"PYTHONUNBUFFERED": "1"},
            log_path=LOG_DIR / "phase4_local_orpo_followup_smoke.log",
        )
        run(
            [
                str(PYTHON),
                "run_local_orpo_1p7b.py",
                "--data",
                str(orpo_pairs),
                "--base-adapter",
                str(latest_adapter),
                "--output-dir",
                str(full_dir),
            ],
            gpu=orpo_gpu,
            env_extra={"PYTHONUNBUFFERED": "1"},
            log_path=LOG_DIR / "phase4_local_orpo_followup.log",
        )
        summary["steps"].append({"name": "orpo_followup", "status": "COMPLETE", "output": str(full_dir / 'final')})

    summary["latest_adapter"] = str(latest_adapter)
    summary["latest_eval"] = latest_eval.get("categories", {})
    summary["overall_status"] = "PASS" if eval_passes(latest_eval) else "FAIL"
    FOLLOWUP_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"FOLLOWUP COMPLETE overall={summary['overall_status']} latest_adapter={latest_adapter}")


if __name__ == "__main__":
    main()
