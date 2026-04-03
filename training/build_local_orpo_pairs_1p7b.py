#!/usr/bin/env python3
"""Build ORPO pairs from local benchmark failures and synthetic negatives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase2_optionc_common import (
    DEFAULT_BENCHMARK,
    DEFAULT_CORRECTIONS_DATA,
    DEFAULT_OPTIONC_TRAPS,
    DEFAULT_ORPO_DATA,
    normalize_multiline,
    read_jsonl,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local ORPO pairs for the 1.7B branch.")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--eval-results", type=Path, required=True)
    parser.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS_DATA)
    parser.add_argument("--traps", type=Path, default=DEFAULT_OPTIONC_TRAPS)
    parser.add_argument("--output", type=Path, default=DEFAULT_ORPO_DATA)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/orpo_pairs_optionc_1p7b_summary.json"),
    )
    return parser.parse_args()


def plausible_failure(model_answer: str, score: dict) -> bool:
    if len(normalize_multiline(model_answer).split()) < 12:
        return False
    return score.get("required_hit_count", 0) > 0 or not score.get("forbidden_hits")


def weaken_answer(answer: str, index: int) -> str:
    lines = [line for line in normalize_multiline(answer).splitlines() if line.strip()]
    if not lines:
        return answer
    mode = index % 4
    if mode == 0:
        lines = [line for line in lines if not line.lower().startswith("6. escalate to:") and not line.lower().startswith("escalate to:")]
    elif mode == 1 and len(lines) > 2:
        lines = lines[1:]
    elif mode == 2:
        lines = [line.replace("must", "should").replace("shall", "should") for line in lines]
    else:
        lines = [line.replace("Do not:", "Consider:") for line in lines]
    weakened = "\n".join(lines).strip()
    return weakened or answer


def main() -> None:
    args = parse_args()
    benchmark = {item["id"]: item for item in read_jsonl(args.benchmark)}
    eval_results = json.loads(args.eval_results.read_text(encoding="utf-8"))
    corrections = read_jsonl(args.corrections) if args.corrections.exists() else []
    traps = read_jsonl(args.traps) if args.traps.exists() else []

    pairs = []
    for failures in eval_results.get("failures", {}).values():
        for failure in failures:
            item = benchmark.get(failure["id"])
            if item is None:
                continue
            if plausible_failure(failure.get("model_answer", ""), failure.get("score", {})):
                pairs.append(
                    {
                        "prompt": item["question"],
                        "chosen": item["reference_answer"],
                        "rejected": failure.get("model_answer", ""),
                        "source": "benchmark_failure",
                        "benchmark_id": item["id"],
                        "category": item["category"],
                    }
                )

    topup_pool = corrections + traps
    index = 0
    while len(pairs) < 300 and index < len(topup_pool) * 4:
        record = topup_pool[index % len(topup_pool)]
        question = record.get("q") or record.get("question") or ""
        answer = record.get("a") or record.get("answer") or ""
        if question and answer:
            pairs.append(
                {
                    "prompt": question,
                    "chosen": answer,
                    "rejected": weaken_answer(answer, index),
                    "source": "synthetic_negative",
                    "benchmark_id": None,
                    "category": record.get("category") or record.get("type") or "trap",
                }
            )
        index += 1

    pairs = pairs[:800]
    write_jsonl(args.output, pairs)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(
            {
                "count": len(pairs),
                "benchmark_pairs": sum(1 for pair in pairs if pair["source"] == "benchmark_failure"),
                "synthetic_pairs": sum(1 for pair in pairs if pair["source"] == "synthetic_negative"),
                "output": str(args.output),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
