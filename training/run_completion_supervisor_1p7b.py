#!/usr/bin/env python3
"""Non-stop local completion supervisor for the 1.7B maritime branch."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from phase2_optionc_common import final_adapter_exists, log_pipeline

ROOT = Path("/home/mohanganesh/ship")
TRAIN_DIR = ROOT / "training"
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "ship" / "maritime_pipeline" / "data" / "final"
PYTHON = ROOT / ".venv-train" / "bin" / "python"

SFT1_ROOT = TRAIN_DIR / "checkpoints" / "phase2-optionc-sft1-1.7b"
SFT2_ROOT = TRAIN_DIR / "checkpoints" / "phase2-optionc-sft2-1.7b"
BOUNDARY_ROOT = TRAIN_DIR / "checkpoints" / "phase2-optionc-boundary-1.7b"
CORRECTION_ROOT = TRAIN_DIR / "checkpoints" / "phase3-local-correction-1.7b"
ORPO_ROOT = TRAIN_DIR / "checkpoints" / "phase4-local-orpo-1.7b"

BENCHMARK = DATA_DIR / "local_benchmark_1p7b.jsonl"
SFT2_EVAL = LOG_DIR / "local_eval_sft2_1p7b.json"
BOUNDARY_EVAL = LOG_DIR / "local_eval_boundary_1p7b.json"
CORRECTION_EVAL = LOG_DIR / "local_eval_correction_1p7b.json"
FINAL_EVAL = LOG_DIR / "local_eval_final_1p7b.json"
FAST_REF_EVAL = LOG_DIR / "local_eval_fastref_1p7b.json"
SUMMARY_MD = LOG_DIR / "completion_summary_1p7b.md"
CPU_THREADS = max(1, os.cpu_count() or 1)


@dataclass
class ManagedPhase:
    name: str
    command: list[str]
    log_path: Path
    final_artifact: Path
    gpu: int | None = None
    gpu_role: str = "train"
    required_free_mb: int = 9000
    max_gpu_used_mb: int | None = 512
    max_restarts: int = 20
    restart_sleep_s: int = 90
    stale_seconds: int = 1200
    min_gpu_mem_mb: int = 3000


def env_for_gpu(gpu: int) -> dict[str, str]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu)
    thread_budget = str(int(os.environ.get("SHIP_CPU_THREADS", CPU_THREADS)))
    env.setdefault("OMP_NUM_THREADS", thread_budget)
    env.setdefault("MKL_NUM_THREADS", thread_budget)
    env.setdefault("OPENBLAS_NUM_THREADS", thread_budget)
    env.setdefault("NUMEXPR_NUM_THREADS", thread_budget)
    env.setdefault("VECLIB_MAXIMUM_THREADS", thread_budget)
    env.setdefault("SHIP_LLAMA_THREADS", thread_budget)
    env.setdefault("SHIP_SFT_DATA", str(DATA_DIR / "sft_curated_optionc_1p7b.jsonl"))
    env.setdefault("SHIP_SFT_TRAPS", str(DATA_DIR / "sft_curated_traps_optionc_1p7b.jsonl"))
    env.setdefault("SHIP_SFT_REPLAY_DATA", str(DATA_DIR / "sft_curated.jsonl"))
    env.setdefault("SHIP_CORRECTIONS_DATA", str(DATA_DIR / "sft_corrections_optionc_1p7b.jsonl"))
    env.setdefault("SHIP_ORPO_DATA", str(DATA_DIR / "orpo_pairs_optionc_1p7b.jsonl"))
    return env


def query_gpus() -> list[dict[str, int]]:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=index,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
    except Exception:
        return []
    rows = []
    for line in output.splitlines():
        parts = [chunk.strip() for chunk in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            index = int(parts[0])
            used = int(parts[1])
            total = int(parts[2])
            util = int(parts[3])
        except ValueError:
            continue
        rows.append(
            {
                "index": index,
                "used": used,
                "total": total,
                "free": total - used,
                "util": util,
            }
        )
    return rows


def preferred_gpu_from_env(role: str) -> int | None:
    key = f"SHIP_{role.upper()}_GPU"
    raw = os.environ.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def wait_for_free_gpu(
    role: str,
    *,
    exclude: set[int] | None = None,
    required_free_mb: int = 9000,
    max_gpu_used_mb: int | None = 512,
) -> int:
    exclude = exclude or set()
    preferred = preferred_gpu_from_env(role)
    if preferred is not None and preferred not in exclude:
        log_pipeline(f"SUPERVISOR STATUS: GPU_SELECT role={role} gpu={preferred} source=env")
        return preferred

    wait_seconds = int(os.environ.get("SHIP_GPU_POLL_SECONDS", "60"))
    last_snapshot = None
    while True:
        rows = query_gpus()
        candidates = [
            row
            for row in rows
            if row["index"] not in exclude
            and row["free"] >= required_free_mb
            and (max_gpu_used_mb is None or row["used"] <= max_gpu_used_mb)
            and row["util"] <= 20
        ]
        if candidates:
            chosen = max(candidates, key=lambda row: (row["free"], -row["util"], -row["index"]))
            log_pipeline(
                f"SUPERVISOR STATUS: GPU_SELECT role={role} gpu={chosen['index']} free_mb={chosen['free']} util={chosen['util']}"
            )
            return chosen["index"]
        snapshot = [(row["index"], row["used"], row["free"], row["util"]) for row in rows]
        if snapshot != last_snapshot:
            log_pipeline(
                f"SUPERVISOR STATUS: GPU_WAIT role={role} required_free_mb={required_free_mb} snapshot={snapshot}"
            )
            last_snapshot = snapshot
        time.sleep(wait_seconds)


def pid_gpu_mem_mb(pid: int) -> int:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,used_gpu_memory",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
    except Exception:
        return 0
    for line in output.splitlines():
        parts = [chunk.strip() for chunk in line.split(",")]
        if len(parts) != 2:
            continue
        if parts[0] == str(pid):
            try:
                return int(parts[1])
            except Exception:
                return 0
    return 0


def log_is_stale(path: Path, threshold_s: int) -> bool:
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) > threshold_s


def run_simple(
    command: list[str],
    *,
    gpu: int | None = None,
    gpu_role: str = "eval",
    required_free_mb: int = 9000,
    max_gpu_used_mb: int | None = 512,
    exclude_gpus: set[int] | None = None,
    label: str,
    retries: int = 3,
    retry_sleep_s: int = 30,
) -> None:
    attempt = 0
    while True:
        attempt += 1
        selected_gpu = (
            gpu
            if gpu is not None
            else wait_for_free_gpu(
                gpu_role,
                exclude=exclude_gpus,
                required_free_mb=required_free_mb,
                max_gpu_used_mb=max_gpu_used_mb,
            )
        )
        env = env_for_gpu(selected_gpu)
        log_pipeline(f"SUPERVISOR STATUS: RUN {label} attempt={attempt} gpu={selected_gpu}")
        try:
            subprocess.run(command, cwd=TRAIN_DIR, env=env, check=True)
            return
        except subprocess.CalledProcessError:
            if attempt >= retries:
                raise
            log_pipeline(f"SUPERVISOR RETRY: {label} attempt={attempt} gpu={selected_gpu}")
            time.sleep(retry_sleep_s)


def run_managed_phase(phase: ManagedPhase) -> None:
    if phase.final_artifact.exists():
        log_pipeline(f"SUPERVISOR STATUS: SKIP {phase.name} final already exists")
        return
    restarts = 0
    while not phase.final_artifact.exists():
        if restarts > phase.max_restarts:
            raise RuntimeError(f"{phase.name} exceeded restart budget")
        phase.log_path.parent.mkdir(parents=True, exist_ok=True)
        phase_gpu = (
            phase.gpu
            if phase.gpu is not None
            else wait_for_free_gpu(
                phase.gpu_role,
                required_free_mb=phase.required_free_mb,
                max_gpu_used_mb=phase.max_gpu_used_mb,
            )
        )
        with phase.log_path.open("a", encoding="utf-8") as handle:
            proc = subprocess.Popen(
                phase.command,
                cwd=TRAIN_DIR,
                env=env_for_gpu(phase_gpu),
                stdout=handle,
                stderr=handle,
            )
        log_pipeline(f"SUPERVISOR STATUS: LAUNCH {phase.name} gpu={phase_gpu} pid={proc.pid}")
        start = time.time()
        warmup = 300
        while proc.poll() is None:
            time.sleep(60)
            if time.time() - start < warmup:
                continue
            if log_is_stale(phase.log_path, phase.stale_seconds):
                proc.kill()
                proc.wait(timeout=30)
                restarts += 1
                log_pipeline(f"SUPERVISOR RESTART: {phase.name} stale_log gpu={phase_gpu} restart={restarts}")
                time.sleep(phase.restart_sleep_s)
                break
            gpu_mem = pid_gpu_mem_mb(proc.pid)
            if gpu_mem and gpu_mem < phase.min_gpu_mem_mb:
                proc.kill()
                proc.wait(timeout=30)
                restarts += 1
                log_pipeline(
                    f"SUPERVISOR RESTART: {phase.name} low_gpu_mem={gpu_mem} gpu={phase_gpu} restart={restarts}"
                )
                time.sleep(phase.restart_sleep_s)
                break
        else:
            pass
        if proc.poll() is not None and not phase.final_artifact.exists():
            restarts += 1
            log_pipeline(
                f"SUPERVISOR RESTART: {phase.name} exit_code={proc.returncode} gpu={phase_gpu} restart={restarts}"
            )
            time.sleep(phase.restart_sleep_s)
    log_pipeline(f"SUPERVISOR STATUS: COMPLETE {phase.name}")


def need_boundary(eval_path: Path) -> bool:
    payload = json.loads(eval_path.read_text(encoding="utf-8"))
    trap = payload.get("categories", {}).get("trap", {})
    return trap.get("pass_rate", 0.0) < 80.0 or trap.get("escalation_miss_rate", 0.0) > 10.0


def final_adapter() -> Path:
    if final_adapter_exists(ORPO_ROOT):
        return ORPO_ROOT / "final"
    if final_adapter_exists(CORRECTION_ROOT):
        return CORRECTION_ROOT / "final"
    raise RuntimeError("no final adapter found")


def write_summary() -> None:
    sections = []
    for path, label in [
        (SFT2_EVAL, "SFT2"),
        (BOUNDARY_EVAL, "Boundary"),
        (CORRECTION_EVAL, "Correction"),
        (FINAL_EVAL, "Final"),
    ]:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            sections.append(f"## {label}\n\n```json\n{json.dumps(payload.get('categories', {}), indent=2)}\n```")
    summary = "# 1.7B Completion Summary\n\n" + "\n\n".join(sections)
    SUMMARY_MD.write_text(summary, encoding="utf-8")


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_pipeline("SUPERVISOR STATUS: START 1.7B completion pipeline")

    run_managed_phase(
        ManagedPhase(
            name="sft1",
            command=[str(PYTHON), "run_phase2_optionc_sft1_1p7b.py"],
            log_path=LOG_DIR / "phase2_optionc_sft1_1p7b.log",
            final_artifact=SFT1_ROOT / "final" / "adapter_model.safetensors",
            gpu_role="train",
            required_free_mb=9000,
        )
    )
    run_managed_phase(
        ManagedPhase(
            name="sft2",
            command=[str(PYTHON), "run_phase2_optionc_sft2_1p7b.py"],
            log_path=LOG_DIR / "phase2_optionc_sft2_1p7b.log",
            final_artifact=SFT2_ROOT / "final" / "adapter_model.safetensors",
            gpu_role="train",
            required_free_mb=9000,
        )
    )

    if not BENCHMARK.exists():
        run_simple([str(PYTHON), "build_local_benchmark_1p7b.py"], gpu_role="train", required_free_mb=9000, label="build_benchmark")

    run_simple(
        [
            str(PYTHON),
            "run_local_eval_1p7b.py",
            "--adapter-dir",
            str(SFT2_ROOT / "final"),
            "--benchmark",
            str(BENCHMARK),
            "--output",
            str(SFT2_EVAL),
            "--label",
            "sft2",
            "--max-new-tokens",
            "160",
        ],
        gpu_role="eval",
        required_free_mb=5000,
        max_gpu_used_mb=None,
        label="eval_sft2",
    )

    current_eval = SFT2_EVAL
    current_adapter = SFT2_ROOT / "final"
    if need_boundary(SFT2_EVAL):
        run_managed_phase(
            ManagedPhase(
                name="boundary",
                command=[str(PYTHON), "run_phase2_optionc_boundary_1p7b.py"],
                log_path=LOG_DIR / "phase2_optionc_boundary_1p7b.log",
                final_artifact=BOUNDARY_ROOT / "final" / "adapter_model.safetensors",
                gpu_role="train",
                required_free_mb=9000,
            )
        )
        run_simple(
            [
                str(PYTHON),
                "run_local_eval_1p7b.py",
                "--adapter-dir",
                str(BOUNDARY_ROOT / "final"),
                "--benchmark",
                str(BENCHMARK),
                "--output",
                str(BOUNDARY_EVAL),
                "--label",
                "boundary",
                "--max-new-tokens",
                "160",
            ],
            gpu_role="eval",
            required_free_mb=5000,
            max_gpu_used_mb=None,
            label="eval_boundary",
        )
        current_eval = BOUNDARY_EVAL
        current_adapter = BOUNDARY_ROOT / "final"

    run_simple(
        [
            str(PYTHON),
            "build_local_corrections_1p7b.py",
            "--benchmark",
            str(BENCHMARK),
            "--eval-results",
            str(current_eval),
        ],
        gpu_role="train",
        required_free_mb=9000,
        label="build_corrections",
    )

    run_managed_phase(
        ManagedPhase(
            name="correction",
            command=[str(PYTHON), "run_local_correction_1p7b.py"],
            log_path=LOG_DIR / "phase3_local_correction_1p7b.log",
            final_artifact=CORRECTION_ROOT / "final" / "adapter_model.safetensors",
            gpu_role="train",
            required_free_mb=9000,
        )
    )

    run_simple(
        [
            str(PYTHON),
            "run_local_eval_1p7b.py",
            "--adapter-dir",
            str(CORRECTION_ROOT / "final"),
            "--benchmark",
            str(BENCHMARK),
            "--output",
            str(CORRECTION_EVAL),
            "--label",
            "correction",
            "--max-new-tokens",
            "160",
        ],
        gpu_role="eval",
        required_free_mb=5000,
        max_gpu_used_mb=None,
        label="eval_correction",
    )

    run_simple(
        [
            str(PYTHON),
            "build_local_orpo_pairs_1p7b.py",
            "--benchmark",
            str(BENCHMARK),
            "--eval-results",
            str(CORRECTION_EVAL),
        ],
        gpu_role="train",
        required_free_mb=9000,
        label="build_orpo_pairs",
    )

    smoke_success = False
    for attempt in range(1, 4):
        try:
            run_simple(
                [str(PYTHON), "run_local_orpo_1p7b.py", "--smoke"],
                gpu_role="train",
                required_free_mb=9000,
                label=f"orpo_smoke_{attempt}",
            )
            smoke_success = True
            break
        except subprocess.CalledProcessError:
            log_pipeline(f"SUPERVISOR STATUS: ORPO smoke failed attempt={attempt}")
            time.sleep(30)

    if smoke_success:
        run_managed_phase(
            ManagedPhase(
                name="orpo",
                command=[str(PYTHON), "run_local_orpo_1p7b.py"],
                log_path=LOG_DIR / "phase4_local_orpo_1p7b.log",
                final_artifact=ORPO_ROOT / "final" / "adapter_model.safetensors",
                gpu_role="train",
                required_free_mb=9000,
            )
        )

    final_candidate = final_adapter()
    run_simple(
        [
            str(PYTHON),
            "run_local_eval_1p7b.py",
            "--adapter-dir",
            str(final_candidate),
            "--benchmark",
            str(BENCHMARK),
            "--output",
            str(FINAL_EVAL),
            "--label",
            "final",
            "--max-new-tokens",
            "160",
        ],
        gpu_role="eval",
        required_free_mb=5000,
        max_gpu_used_mb=None,
        label="eval_final",
    )
    run_simple(
        [
            str(PYTHON),
            "run_local_eval_1p7b.py",
            "--adapter-dir",
            str(final_candidate),
            "--benchmark",
            str(BENCHMARK),
            "--output",
            str(FAST_REF_EVAL),
            "--label",
            "fastref",
            "--max-per-category",
            "10",
            "--max-new-tokens",
            "160",
        ],
        gpu_role="eval",
        required_free_mb=5000,
        max_gpu_used_mb=None,
        label="eval_fast_reference",
    )
    run_simple(
        [
            str(PYTHON),
            "quantize_optionc_1p7b.py",
            "--adapter-dir",
            str(final_candidate),
            "--benchmark",
            str(BENCHMARK),
            "--reference-eval",
            str(FAST_REF_EVAL),
        ],
        gpu_role="eval",
        required_free_mb=6000,
        max_gpu_used_mb=None,
        label="quantize",
    )

    write_summary()
    log_pipeline("SUPERVISOR STATUS: COMPLETE 1.7B completion pipeline")


if __name__ == "__main__":
    main()
