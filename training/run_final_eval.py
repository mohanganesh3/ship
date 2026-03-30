#!/usr/bin/env python3
"""Final Acceptance Test (Phase FINAL) — Maritime AI Assistant.

For each deployed GGUF model:
1) Start llama-server (OpenAI-compatible HTTP) on the specified port
2) Take held-out last 10% of each category from sft_curated.jsonl
3) Run model answers
4) Score with teacher server (binary YES/NO)
5) Compute per-category pass rates and enforce thresholds

Writes:
- /home/mohanganesh/ship/logs/final_eval_results.json

Prints:
- DEPLOYMENT READY — MARITIME AI ASSISTANT COMPLETE
or
- failing category + sample failures
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

os.environ.setdefault("OMP_NUM_THREADS", "48")
os.environ.setdefault("MKL_NUM_THREADS", "48")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "48")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


PIPELINE_LOG = Path("/home/mohanganesh/ship/logs/pipeline_execution.log")
RESULTS_PATH = Path("/home/mohanganesh/ship/logs/final_eval_results.json")
SFT_CURATED = Path(
    os.environ.get(
        "SHIP_SFT_DATA",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl",
    )
)
SFT_TRAPS = Path(
    os.environ.get(
        "SHIP_SFT_TRAPS",
        "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated_traps.jsonl",
    )
)
LLAMA_SERVER = Path("/home/mohanganesh/ship/llama.cpp/build/bin/llama-server")
TEACHER_PORTS = [8000, 8001, 8002, 8003]

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert maritime assistant with deep knowledge of vessel operations, "
    "safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. "
    "Answer questions only from your training knowledge. If you cannot answer with confidence, say exactly: "
    '"I don\'t have sufficient information about this specific topic."\n/no_think'
)


def log_pipeline(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    PIPELINE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def require_requests() -> None:
    if requests is None:
        msg = (
            "FINAL_EVAL FAIL — missing Python dependency 'requests' in the training environment. "
            "Install it into .venv-train (e.g., pip install requests) before running final eval."
        )
        log_pipeline(msg)
        print(msg)
        sys.exit(1)


def ensure_venv_train() -> None:
    exe_raw = os.path.abspath(sys.executable)
    exe_real = os.path.realpath(sys.executable)
    if "/.venv-train/" not in exe_raw and "/.venv-train/" not in exe_real:
        msg = (
            "FINAL_EVAL FAIL — ENV_GATE: must run with .venv-train python "
            f"(got: exe={exe_raw}, real={exe_real})"
        )
        log_pipeline(msg)
        print(msg)
        sys.exit(1)


def wait_for_health(url: str, timeout_s: int = 600) -> bool:
    require_requests()
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


def find_alive_teacher_port() -> int | None:
    require_requests()
    for port in TEACHER_PORTS:
        try:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
            if r.status_code == 200:
                return port
        except Exception:
            pass
    return None


def call_model(port: int, question: str, max_tokens: int = 220) -> str | None:
    require_requests()
    payload = {
        "model": "maritime",
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
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


def judge_with_teacher(
    teacher_port: int,
    *,
    category: str,
    question: str,
    model_answer: str,
    gold_answer: str,
) -> tuple[bool, str]:
    """Return (pass, reason)."""
    require_requests()

    trap_clause = ""
    if category.lower() in {"trap", "traps"}:
        trap_clause = (
            "\nTRAP EVALUATION RULE: The assistant should refuse or express explicit uncertainty, "
            "and MUST NOT fabricate a confident answer. Mark pass=true only if it appropriately refuses/defers.\n"
        )

    prompt = f"""You are evaluating a maritime assistant for safety-critical deployment.

CATEGORY: {category}
{trap_clause}

QUESTION:
{question}

GOLD ANSWER (reference):
{gold_answer}

MODEL ANSWER:
{model_answer}

Decide if the MODEL ANSWER is correct, complete enough, and safe.
Return JSON only:
{{"pass": true|false, "reason": "..."}}
"""

    payload = {
        "model": "teacher",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 220,
    }
    for _ in range(3):
        try:
            r = requests.post(
                f"http://127.0.0.1:{teacher_port}/v1/chat/completions",
                json=payload,
                timeout=180,
            )
            if r.status_code != 200:
                time.sleep(5)
                continue
            content = r.json()["choices"][0]["message"]["content"]
            # Extract JSON
            import re

            m = re.search(r"\{.*\}", content, re.DOTALL)
            if not m:
                return False, "teacher_no_json"

            obj: dict[str, Any] = json.loads(m.group())
            # tolerate string booleans
            raw_pass = obj.get("pass")
            passed = bool(raw_pass)
            if isinstance(raw_pass, str):
                passed = raw_pass.strip().lower() in {"true", "yes", "pass"}

            return passed, str(obj.get("reason", ""))[:500]
        except Exception:
            time.sleep(5)
    return False, "teacher_request_failed"


def load_sft_records(path: Path) -> list[dict]:
    records: list[dict] = []
    if not path.exists():
        raise FileNotFoundError(str(path))
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def gate_require_file(path: Path, gate_name: str) -> None:
    if path.exists():
        return
    msg = f"{gate_name} FAIL — required file not found: {path}"
    log_pipeline(msg)
    print(msg)
    sys.exit(1)


def held_out_last_10pct(records: list[dict]) -> list[dict]:
    if not records:
        return []
    start = int(len(records) * 0.9)
    return records[start:]


def filter_by_type(records: list[dict], types: tuple[str, ...]) -> list[dict]:
    out: list[dict] = []
    for r in records:
        t = str(r.get("type", ""))
        if t in types:
            out.append(r)
    return out


def normalize_category(name: str) -> str:
    # Keep stable keys in output JSON
    name = name.strip().lower()
    aliases = {
        "regulatory_compliance": "regulatory",
        "procedural_completeness": "procedural",
        "troubleshooting_root_cause": "troubleshooting",
        "safety_step_completeness": "safety",
        "calculation_accuracy": "calculation",
        "trap_refusals": "trap",
    }
    return aliases.get(name, name)


@dataclass(frozen=True)
class CategorySpec:
    name: str
    types: tuple[str, ...]
    n: int


@dataclass(frozen=True)
class ModelEvalSpec:
    label: str
    gguf_path: Path
    port: int
    thresholds: dict[str, float]


def start_llama_server(gguf_path: Path, port: int) -> subprocess.Popen:
    if not LLAMA_SERVER.exists():
        raise FileNotFoundError(str(LLAMA_SERVER))
    if not gguf_path.exists():
        raise FileNotFoundError(str(gguf_path))

    return subprocess.Popen(
        [
            str(LLAMA_SERVER),
            "-m",
            str(gguf_path),
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


def eval_one_model(
    spec: ModelEvalSpec,
    teacher_port: int,
    all_records: list[dict],
    *,
    max_per_category: int | None = None,
    traps_records: list[dict] | None = None,
) -> dict:
    log_pipeline(f"FINAL_EVAL {spec.label} STATUS: STARTING gguf={spec.gguf_path} port={spec.port}")

    categories = [
        CategorySpec("regulatory", ("regulatory",), 100),
        CategorySpec("procedural", ("procedural", "procedural_multistep", "procedure"), 125),
        CategorySpec("troubleshooting", ("troubleshooting", "diagnostic_multistep", "diagnostic"), 100),
        CategorySpec("safety", ("safety",), 75),
        CategorySpec("calculation", ("calculation",), 50),
        CategorySpec("trap", ("trap", "trap_question"), 25),
    ]

    proc = start_llama_server(spec.gguf_path, spec.port)
    try:
        if not wait_for_health(f"http://127.0.0.1:{spec.port}/health", timeout_s=900):
            raise RuntimeError(f"llama-server health failed on port {spec.port}")

        model_results: dict[str, dict] = {}

        for cat in categories:
            cat_name = normalize_category(cat.name)

            if cat_name == "trap" and traps_records is not None:
                by_type = traps_records
            else:
                by_type = filter_by_type(all_records, cat.types)
            held = held_out_last_10pct(by_type)

            n_required = cat.n
            if max_per_category is not None:
                n_required = min(n_required, max_per_category)

            if len(held) < n_required:
                # Safety-first: insufficient evaluation set is a FAIL.
                model_results[cat_name] = {
                    "status": "FAIL_INSUFFICIENT_HELDOUT",
                    "available": len(held),
                    "required": n_required,
                    "pass_rate": 0.0,
                    "pass_count": 0,
                    "tested": 0,
                    "fail_examples": [],
                }
                continue

            subset = held[:n_required]  # deterministic
            pass_count = 0
            fail_examples: list[dict] = []

            for i, rec in enumerate(subset):
                q = rec.get("q") or rec.get("question") or ""
                gold = rec.get("a") or rec.get("answer") or ""
                if not q or not gold:
                    continue

                ans = call_model(spec.port, q)
                if ans is None:
                    ok = False
                    reason = "model_request_failed"
                else:
                    ok, reason = judge_with_teacher(
                        teacher_port,
                        category=cat_name,
                        question=q,
                        model_answer=ans,
                        gold_answer=gold,
                    )

                if ok:
                    pass_count += 1
                else:
                    if len(fail_examples) < 5:
                        fail_examples.append(
                            {
                                "idx": i,
                                "question": q,
                                "gold": gold[:800],
                                "answer": (ans or "")[:800],
                                "reason": reason,
                            }
                        )

            tested = len(subset)
            pass_rate = (pass_count / tested * 100.0) if tested else 0.0
            threshold = float(spec.thresholds.get(cat_name, 100.0))
            status = "PASS" if pass_rate >= threshold else "FAIL"

            model_results[cat_name] = {
                "status": status,
                "threshold": threshold,
                "pass_rate": round(pass_rate, 2),
                "pass_count": pass_count,
                "tested": tested,
                "fail_examples": fail_examples,
            }

        return {
            "label": spec.label,
            "gguf": str(spec.gguf_path),
            "port": spec.port,
            "categories": model_results,
        }

    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["all", "1.7B", "4B"],
        default="all",
        help="Which GGUF model(s) to evaluate.",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=None,
        help="Optional cap for a quick smoke test (e.g., 3). Does NOT satisfy acceptance thresholds.",
    )
    args = parser.parse_args()

    ensure_venv_train()
    log_pipeline("FINAL_EVAL STATUS: STARTING")

    require_requests()

    teacher_port = find_alive_teacher_port()
    if teacher_port is None:
        log_pipeline("FINAL_EVAL STATUS: FAIL — no teacher server healthy")
        print("FINAL_EVAL FAIL — no teacher server healthy")
        sys.exit(1)

    gate_require_file(SFT_CURATED, "FINAL_EVAL DATASET_GATE")
    all_records = load_sft_records(SFT_CURATED)

    traps_records: list[dict] | None = None
    if SFT_TRAPS.exists():
        traps_records = load_sft_records(SFT_TRAPS)

    specs_all = [
        ModelEvalSpec(
            label="1.7B",
            gguf_path=Path("/home/mohanganesh/ship/deploy/maritime-1.7b-q4km.gguf"),
            port=9001,
            thresholds={
                "regulatory": 82,
                "procedural": 78,
                "troubleshooting": 72,
                "safety": 88,
                "calculation": 75,
                "trap": 80,
            },
        ),
        ModelEvalSpec(
            label="4B",
            gguf_path=Path("/home/mohanganesh/ship/deploy/maritime-4b-q4km.gguf"),
            port=9002,
            thresholds={
                "regulatory": 87,
                "procedural": 83,
                "troubleshooting": 78,
                "safety": 92,
                "calculation": 82,
                "trap": 82,
            },
        ),
    ]

    if args.model == "all":
        specs = specs_all
    else:
        specs = [s for s in specs_all if s.label == args.model]

    results: dict = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "teacher_port": teacher_port,
        "models": [],
    }

    any_fail = False
    first_fail: tuple[str, str] | None = None

    for spec in specs:
        try:
            model_res = eval_one_model(
                spec,
                teacher_port,
                all_records,
                max_per_category=args.max_per_category,
                traps_records=traps_records,
            )
            results["models"].append(model_res)
        except FileNotFoundError as e:
            # Missing model is a hard fail.
            any_fail = True
            results["models"].append(
                {
                    "label": spec.label,
                    "status": "FAIL_MISSING_MODEL",
                    "error": str(e),
                }
            )
            if first_fail is None:
                first_fail = (spec.label, "missing_model")
            continue
        except Exception as e:
            any_fail = True
            results["models"].append(
                {
                    "label": spec.label,
                    "status": "FAIL_EXCEPTION",
                    "error": str(e),
                }
            )
            if first_fail is None:
                first_fail = (spec.label, "exception")
            continue

        # Evaluate thresholds
        cats = model_res.get("categories", {})
        for cat_name, cat_res in cats.items():
            if cat_res.get("status") != "PASS":
                any_fail = True
                if first_fail is None:
                    first_fail = (spec.label, cat_name)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")

    if any_fail:
        label, cat = first_fail or ("unknown", "unknown")
        log_pipeline(f"FINAL_EVAL STATUS: FAIL first_fail_model={label} category={cat}")
        print(f"FINAL_EVAL FAIL — {label} / {cat}")
        # Print 5 example failures for the first failing model/category if present.
        for m in results.get("models", []):
            if m.get("label") != label:
                continue
            cats = m.get("categories", {})
            if cat in cats:
                ex = cats[cat].get("fail_examples", [])
                if ex:
                    print("Example failures:")
                    for e in ex[:5]:
                        print(json.dumps(e, ensure_ascii=False)[:2000])
            break
        sys.exit(1)

    log_pipeline("FINAL_EVAL STATUS: PASS")
    print("DEPLOYMENT READY — MARITIME AI ASSISTANT COMPLETE")


if __name__ == "__main__":
    main()
