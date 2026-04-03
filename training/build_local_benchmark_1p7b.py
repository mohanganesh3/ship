#!/usr/bin/env python3
"""Build the 240-prompt local benchmark bank for the 1.7B maritime branch."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from phase2_optionc_common import (
    DEFAULT_BENCHMARK,
    DEFAULT_OPTIONC_DATA,
    DEFAULT_OPTIONC_TRAPS,
    DEFAULT_REASONING_REPLAY,
    benchmark_record_from_source,
    coalesce_question,
    extract_numeric_candidates,
    infer_category,
    normalize_space,
    read_jsonl,
    round_robin_pick,
    write_jsonl,
)

TARGETS = {
    "regulatory": 40,
    "procedural": 40,
    "troubleshooting": 40,
    "safety": 40,
    "trap": 40,
    "calculation": 40,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local benchmark bank for the 1.7B completion pipeline.")
    parser.add_argument("--optionc", type=Path, default=DEFAULT_OPTIONC_DATA)
    parser.add_argument("--traps", type=Path, default=DEFAULT_OPTIONC_TRAPS)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REASONING_REPLAY)
    parser.add_argument("--out", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/local_benchmark_1p7b_summary.json"),
    )
    return parser.parse_args()


def calculation_candidates(optionc_records: list[dict], replay_records: list[dict]) -> list[dict]:
    explicit = []
    numeric = []
    for record in optionc_records + replay_records:
        question = coalesce_question(record)
        if not question:
            continue
        rtype = normalize_space(record.get("type")).lower()
        difficulty = normalize_space(record.get("difficulty_hint")).lower()
        if rtype == "calculation" or "calculation" in difficulty:
            explicit.append(record)
        elif extract_numeric_candidates(record):
            numeric.append(record)
    picked = round_robin_pick(explicit, TARGETS["calculation"])
    if len(picked) < TARGETS["calculation"]:
        extras = []
        seen = {coalesce_question(record).lower() for record in picked}
        for record in round_robin_pick(numeric, TARGETS["calculation"] * 2):
            qkey = coalesce_question(record).lower()
            if qkey in seen:
                continue
            extras.append(record)
            seen.add(qkey)
            if len(picked) + len(extras) >= TARGETS["calculation"]:
                break
        picked.extend(extras)
    return picked[: TARGETS["calculation"]]


def main() -> None:
    args = parse_args()
    optionc_records = read_jsonl(args.optionc)
    trap_records = read_jsonl(args.traps)
    replay_records = read_jsonl(args.replay) if args.replay.exists() else []

    grouped: dict[str, list[dict]] = {category: [] for category in TARGETS}
    for record in optionc_records:
        category = infer_category(record)
        if category in grouped and category != "calculation":
            grouped[category].append(record)

    grouped["trap"] = trap_records
    grouped["calculation"] = calculation_candidates(optionc_records, replay_records)

    benchmark: list[dict] = []
    summary: dict[str, dict] = {}

    for category, target in TARGETS.items():
        selected = round_robin_pick(grouped.get(category, []), target)
        if len(selected) < target:
            raise SystemExit(f"benchmark build failed: category={category} only {len(selected)} of {target}")
        summary[category] = {"selected": len(selected)}
        for index, record in enumerate(selected, start=1):
            benchmark.append(
                benchmark_record_from_source(
                    record,
                    category=category,
                    benchmark_id=f"{category[:3]}-{index:03d}",
                    source_tag="optionc" if category != "calculation" else "optionc_or_replay",
                )
            )

    write_jsonl(args.out, benchmark)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(
            {
                "total": len(benchmark),
                "targets": TARGETS,
                "categories": summary,
                "sources": {
                    "optionc": str(args.optionc),
                    "traps": str(args.traps),
                    "replay": str(args.replay),
                },
                "output": str(args.out),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
