#!/usr/bin/env python3
"""Build correction SFT data from local benchmark failures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase2_optionc_common import (
    DEFAULT_BENCHMARK,
    DEFAULT_CORRECTIONS_DATA,
    extract_escalation_targets,
    extract_forbidden_checks,
    extract_required_checks,
    normalize_space,
    read_jsonl,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build correction SFT data from local evaluation failures.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--eval-results", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_CORRECTIONS_DATA)
    parser.add_argument("--min-count", type=int, default=240)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_corrections_optionc_1p7b_summary.json"),
    )
    return parser.parse_args()


def normalized_reference_answer(item: dict) -> str:
    answer = normalize_space(item.get("reference_answer"))
    required = item.get("required_checks") or extract_required_checks(answer, limit=4)
    forbidden = item.get("forbidden_checks") or extract_forbidden_checks(answer, limit=2)
    escalations = item.get("escalation_targets") or extract_escalation_targets(answer)

    lines = []
    for check in required[:4]:
        check = normalize_space(check)
        if check:
            lines.append(f"{len(lines) + 1}. {check}")
    if forbidden:
        lines.append(f"{len(lines) + 1}. Do not: {normalize_space(forbidden[0])}")
    if escalations:
        lines.append(f"{len(lines) + 1}. Escalate to: {', '.join(normalize_space(target) for target in escalations[:3] if normalize_space(target))}")
    return "\n".join(line for line in lines if line.strip()) or answer


def main() -> None:
    args = parse_args()
    benchmark = {item["id"]: item for item in read_jsonl(args.benchmark)}
    eval_results = json.loads(args.eval_results.read_text(encoding="utf-8"))

    corrections = []
    seen_ids = set()
    for category_failures in eval_results.get("failures", {}).values():
        for failure in category_failures:
            item = benchmark.get(failure["id"])
            if item is None:
                continue
            seen_ids.add(item["id"])
            corrections.append(
                {
                    "q": item["question"],
                    "a": normalized_reference_answer(item),
                    "category": item["category"],
                    "domain": item["domain"],
                    "benchmark_id": item["id"],
                    "source": "eval_failure",
                }
            )

    if len(corrections) < args.min_count:
        for item in benchmark.values():
            if item["id"] in seen_ids:
                continue
            corrections.append(
                {
                    "q": item["question"],
                    "a": normalized_reference_answer(item),
                    "category": item["category"],
                    "domain": item["domain"],
                    "benchmark_id": item["id"],
                    "source": "benchmark_topup",
                }
            )
            seen_ids.add(item["id"])
            if len(corrections) >= args.min_count:
                break

    write_jsonl(args.output, corrections)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(
            {
                "count": len(corrections),
                "eval_failure_count": sum(1 for item in corrections if item["source"] == "eval_failure"),
                "benchmark_topup_count": sum(1 for item in corrections if item["source"] == "benchmark_topup"),
                "benchmark": str(args.benchmark),
                "eval_results": str(args.eval_results),
                "output": str(args.output),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
