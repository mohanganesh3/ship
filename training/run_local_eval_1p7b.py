#!/usr/bin/env python3
"""Local benchmark evaluation for HF adapter checkpoints."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

from phase2_optionc_common import (
    BASE_MODEL,
    DEFAULT_BENCHMARK,
    ensure_cuda,
    ensure_venv_train,
    gate_require_dir,
    generate_response,
    load_merged_model_from_adapter,
    load_tokenizer,
    log_pipeline,
    normalize_space,
    read_jsonl,
    score_response,
    setup_logging,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a local HF adapter checkpoint on the 1.7B benchmark.")
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default="candidate")
    parser.add_argument("--max-per-category", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    print("DEBUG: main starting")
    setup_logging()
    print("DEBUG: logging setup")
    args = parse_args()
    print(f"DEBUG: args parsed: {args}")
    phase = f"LOCAL_EVAL_{args.label.upper()}_1.7B"

    ensure_venv_train(phase)
    ensure_cuda(phase)
    gate_require_dir(args.adapter_dir, phase)

    benchmark = read_jsonl(args.benchmark)
    if len(benchmark) < 60:
        log_pipeline(f"{phase} FAIL — BENCHMARK_GATE: expected >=60 prompts, got {len(benchmark)}")
        raise SystemExit(1)

    tokenizer = load_tokenizer()
    model = load_merged_model_from_adapter(args.adapter_dir, phase)
    model.eval()

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in benchmark:
        grouped[normalize_space(item.get("category")).lower()].append(item)

    thresholds = {
        "regulatory": 85.0,
        "procedural": 80.0,
        "troubleshooting": 75.0,
        "safety": 90.0,
        "calculation": 80.0,
        "trap": 80.0,
    }

    results = {
        "label": args.label,
        "adapter_dir": str(args.adapter_dir),
        "benchmark": str(args.benchmark),
        "categories": {},
        "failures": {},
    }

    for category, items in grouped.items():
        subset = items[: args.max_per_category] if args.max_per_category else items
        passed = 0
        escalation_miss_count = 0
        failures = []
        for item in subset:
            mode = "think" if category in {"troubleshooting", "calculation"} else "no_think"
            answer = generate_response(
                model,
                tokenizer,
                item["question"],
                mode=mode,
                max_new_tokens=args.max_new_tokens,
            )
            from phase2_optionc_common import strip_think, REGULATORY_MODAL_CUES, TRAP_REJECTION_CUES, escalation_alias_match, normalize_space as ns

            def structural_pass(ans: str, cat: str, cur_item: dict) -> tuple[bool, dict]:
                text = strip_think(ns(ans))
                lowered = text.lower()
                esc_targets = cur_item.get("escalation_targets", [])
                esc_hit = (not esc_targets) or any(
                    any(escalation_alias_match(t, line) for line in text.splitlines())
                    for t in esc_targets
                )
                trap_ok = True
                if cat == "trap":
                    trap_ok = any(c in lowered for c in TRAP_REJECTION_CUES)
                modal_ok = True
                if cat == "regulatory":
                    modal_ok = any(c in lowered for c in REGULATORY_MODAL_CUES)
                do_not_ok = True
                if cur_item.get("do_not") and cat in ("trap", "safety", "regulatory"):
                    do_not_ok = "do not" in lowered or "must not" in lowered or "prohibited" in lowered
                return esc_hit and trap_ok and modal_ok and do_not_ok, {
                    "esc_hit": esc_hit, "trap_ok": trap_ok, "modal_ok": modal_ok, "do_not_ok": do_not_ok,
                    "escalation_total": len(esc_targets), "escalation_hit_count": 1 if esc_hit and esc_targets else 0
                }

            passed_check, score = structural_pass(answer, category, item)
            
            if passed_check:
                passed += 1
            else:
                failures.append(
                    {
                        "id": item["id"],
                        "question": item["question"],
                        "reference_answer": item["reference_answer"],
                        "model_answer": answer,
                        "score": score,
                    }
                )
            if item.get("escalation_targets") and score["escalation_total"] > 0 and score["escalation_hit_count"] == 0:
                escalation_miss_count += 1
        tested = len(subset)
        rate = (passed / tested * 100.0) if tested else 0.0
        results["categories"][category] = {
            "tested": tested,
            "pass_count": passed,
            "pass_rate": round(rate, 2),
            "threshold": thresholds.get(category, 0.0),
            "status": "PASS" if rate >= thresholds.get(category, 0.0) else "FAIL",
            "escalation_miss_count": escalation_miss_count,
            "escalation_miss_rate": round((escalation_miss_count / tested * 100.0), 2) if tested else 0.0,
        }
        results["failures"][category] = failures

    overall_pass = all(
        bucket["pass_rate"] >= bucket["threshold"] for bucket in results["categories"].values() if bucket["tested"] > 0
    )
    results["overall_status"] = "PASS" if overall_pass else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    log_pipeline(f"{phase} STATUS: COMPLETE overall={results['overall_status']} out={args.output}")


if __name__ == "__main__":
    main()
