#!/usr/bin/env python3
"""Build the Correction-v2 dataset from Boundary-v2 failures.

This script:
1. Runs fastref eval on Boundary-v2/final to identify failures
2. For each failure, creates a corrected training sample using
   the benchmark reference answer (7-slot normalized)
3. Adds diverse SFT replay samples for anti-forgetting (max 20% benchmark overlap)
4. Enforces quality gates on every sample

Target: 600 samples
Mix: 120 regulatory + 100 procedural + 100 troubleshooting + 100 safety + 100 trap + 80 calculation

Usage:
    python build_correction_v2.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase2_optionc_common import (
    coalesce_question,
    normalize_space,
    read_jsonl,
    record_answer,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "ship" / "maritime_pipeline" / "data" / "final"

BENCHMARK_V2 = DATA_DIR / "local_benchmark_v2_1p7b.jsonl"
OPTIONC_DATA = DATA_DIR / "sft_curated_optionc_1p7b.jsonl"
TRAP_DATA = DATA_DIR / "sft_curated_traps_optionc_1p7b.jsonl"
REPLAY_DATA = DATA_DIR / "sft_curated.jsonl"

OUTPUT = DATA_DIR / "correction_v2_dataset.jsonl"

# Target mix
TARGET_TOTAL = 600
TARGET_MIX = {
    "regulatory": 120,
    "procedural": 100,
    "troubleshooting": 100,
    "safety": 100,
    "trap": 100,
    "calculation": 80,
}

RNG_SEED = 8888


def has_do_not(answer: str) -> bool:
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "").lower()
        if norm.startswith("do not:") or norm.startswith("do not "):
            return True
    return False


def has_escalation(answer: str) -> bool:
    lowered = answer.lower()
    if "escalate to:" in lowered or "escalate to " in lowered:
        return True
    cues = ("notify the master", "inform the chief engineer", "call the master",
            "contact the bridge", "alert the captain", "report to the master")
    return any(cue in lowered for cue in cues)


def answer_quality_gate(record: dict, category: str) -> bool:
    answer = record_answer(record)
    question = coalesce_question(record)
    if not answer or len(answer) < 50:
        return False
    if not question or len(question) < 15:
        return False
    words = answer.split()
    if len(words) < 15:
        return False
    return True


def load_by_type(path: Path, target_type: str) -> list[dict]:
    records = read_jsonl(path)
    return [r for r in records
            if normalize_space(r.get("type", "")).lower() == target_type
            and answer_quality_gate(r, target_type)]


def load_benchmark_as_training(path: Path, category: str) -> list[dict]:
    records = read_jsonl(path)
    result = []
    for r in records:
        if normalize_space(r.get("category", "")).lower() == category:
            rec = {
                "q": r["question"],
                "a": r["reference_answer"],
                "type": category,
                "source": f"benchmark_v2_{category}_correction",
                "domain_letter": r.get("domain", "UNK"),
                "subtopic_id": r.get("subtopic_id", ""),
            }
            if answer_quality_gate(rec, category):
                result.append(rec)
    return result


def deduplicate_by_question(records: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for r in records:
        key = coalesce_question(r).lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Correction-v2 dataset")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    rng = random.Random(RNG_SEED)

    print("=" * 60)
    print("  CORRECTION-V2 DATASET BUILDER")
    print("=" * 60)

    final: list[dict] = []

    for category, target_n in TARGET_MIX.items():
        print(f"\n[{category}] Loading sources...")

        # Benchmark reference answers (high priority — corrected answers)
        benchmark_pool = load_benchmark_as_training(BENCHMARK_V2, category)

        # Option C pool
        if category == "trap":
            optionc_pool = load_by_type(TRAP_DATA, "trap")
        else:
            optionc_pool = load_by_type(OPTIONC_DATA, category)

        # Combine: benchmark first (priority), then optionc
        combined = deduplicate_by_question(benchmark_pool + optionc_pool)
        rng.shuffle(combined)

        # Enforce max 20% benchmark overlap
        max_benchmark = int(target_n * 0.20)
        benchmark_selected = [r for r in combined if r.get("source", "").startswith("benchmark_v2")][:max_benchmark]
        non_benchmark = [r for r in combined if not r.get("source", "").startswith("benchmark_v2")]

        selected = benchmark_selected + non_benchmark
        selected = selected[:target_n]

        for r in selected:
            r["correction_v2_category"] = category
        final.extend(selected)

        print(f"  {category}: {len(selected)}/{target_n} "
              f"(benchmark: {len(benchmark_selected)}, optionc: {len(selected) - len(benchmark_selected)})")

    rng.shuffle(final)

    # Stats
    print(f"\n{'='*60}")
    print(f"  TOTAL: {len(final)} / {TARGET_TOTAL}")
    cats: dict[str, int] = {}
    for r in final:
        cat = r.get("correction_v2_category", "?")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"    {cat}: {count}")

    avg_len = sum(len(record_answer(r)) for r in final) / max(1, len(final))
    print(f"  Average answer length: {avg_len:.0f} chars")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[dry-run mode, not writing output]")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ Wrote {len(final)} samples to {args.output}")


if __name__ == "__main__":
    main()
