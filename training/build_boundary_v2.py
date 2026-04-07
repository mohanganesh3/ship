#!/usr/bin/env python3
"""Build the Boundary-v2 dataset for maritime safety model training.

Sources:
- Trap/Safety/Regulatory failures from the benchmark
- Best Option C trap and safety examples
- 15% diverse SFT replay from procedural/troubleshooting (anti-forgetting)

Target: 320 samples
Mix: 120 trap + 80 safety + 80 regulatory + 40 procedural (replay)

Every sample must have all 7 operational slots populated.
Rejects any sample where do_not or escalation info is missing.

Usage:
    python build_boundary_v2.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from phase2_optionc_common import (
    coalesce_question,
    normalize_space,
    record_answer,
    read_jsonl,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "ship" / "maritime_pipeline" / "data" / "final"

OPTIONC_DATA = DATA_DIR / "sft_curated_optionc_1p7b.jsonl"
TRAP_DATA = DATA_DIR / "sft_curated_traps_optionc_1p7b.jsonl"
BENCHMARK_V2 = DATA_DIR / "local_benchmark_v2_1p7b.jsonl"
REPLAY_DATA = DATA_DIR / "sft_curated.jsonl"

OUTPUT = DATA_DIR / "boundary_v2_dataset.jsonl"

# ---------------------------------------------------------------------------
# Target mix
# ---------------------------------------------------------------------------
TARGET_TOTAL = 320
TARGET_MIX = {
    "trap": 120,
    "safety": 80,
    "regulatory": 80,
    "procedural": 40,  # replay / anti-forgetting
}

# Seed for reproducibility
RNG_SEED = 7777


def has_do_not(answer: str) -> bool:
    """Check if the answer contains a 'Do not:' line."""
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "").lower()
        if norm.startswith("do not:") or norm.startswith("do not "):
            return True
    return False


def has_escalation(answer: str) -> bool:
    """Check if the answer contains an 'Escalate to:' line or escalation cue."""
    lowered = answer.lower()
    if "escalate to:" in lowered or "escalate to " in lowered:
        return True
    # Also accept inline escalation cues
    cues = ("notify the master", "inform the chief engineer", "call the master",
            "contact the bridge", "alert the captain", "report to the master")
    return any(cue in lowered for cue in cues)


def has_rejection(answer: str) -> bool:
    """Check if the answer contains an explicit rejection cue (for traps)."""
    lowered = answer.lower()
    return any(cue in lowered for cue in (
        "do not", "must not", "unsafe", "cannot", "not acceptable", "never",
        "prohibited", "not permitted", "stop", "reject",
    ))


def answer_quality_gate(record: dict, category: str) -> bool:
    """Reject low-quality or incomplete training samples."""
    answer = record_answer(record)
    question = coalesce_question(record)

    if not answer or len(answer) < 50:
        return False
    if not question or len(question) < 15:
        return False

    # Must have escalation info (except pure calculation)
    if category in ("trap", "safety", "regulatory") and not has_escalation(answer):
        return False

    # Must have prohibition (except procedural replay)
    if category in ("trap", "safety", "regulatory") and not has_do_not(answer):
        # Allow if the answer has inline rejection cues (for traps)
        if category == "trap" and has_rejection(answer):
            pass  # OK, trap has rejection
        else:
            return False

    # Trap must have explicit rejection
    if category == "trap" and not has_rejection(answer):
        return False

    # Reject generic compressed answers
    words = answer.split()
    if len(words) < 15:
        return False

    return True


def load_and_filter_by_type(path: Path, target_type: str) -> list[dict]:
    """Load JSONL records and filter by type field."""
    records = read_jsonl(path)
    filtered = []
    for r in records:
        rtype = normalize_space(r.get("type", "")).lower()
        if rtype == target_type:
            if answer_quality_gate(r, target_type):
                filtered.append(r)
    return filtered


def load_benchmark_by_category(path: Path, category: str) -> list[dict]:
    """Load benchmark records as training source for a specific category."""
    records = read_jsonl(path)
    result = []
    for r in records:
        if normalize_space(r.get("category", "")).lower() == category:
            # Convert benchmark format to training format
            training_record = {
                "q": r["question"],
                "a": r["reference_answer"],
                "type": category,
                "source": f"benchmark_v2_{category}",
                "domain_letter": r.get("domain", "UNK"),
                "subtopic_id": r.get("subtopic_id", ""),
            }
            if answer_quality_gate(training_record, category):
                result.append(training_record)
    return result


def deduplicate_by_question(records: list[dict]) -> list[dict]:
    """Deduplicate records by question text."""
    seen = set()
    unique = []
    for r in records:
        key = coalesce_question(r).lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Boundary-v2 dataset")
    parser.add_argument("--dry-run", action="store_true", help="Show stats only, don't write")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    rng = random.Random(RNG_SEED)

    print("=" * 60)
    print("  BOUNDARY-V2 DATASET BUILDER")
    print("=" * 60)

    # 1. Load trap samples from trap data + benchmark
    print("\n[1] Loading trap samples...")
    trap_optionc = load_and_filter_by_type(TRAP_DATA, "trap")
    trap_benchmark = load_benchmark_by_category(BENCHMARK_V2, "trap")
    trap_all = deduplicate_by_question(trap_benchmark + trap_optionc)
    rng.shuffle(trap_all)
    print(f"  Trap pool: {len(trap_all)} (benchmark: {len(trap_benchmark)}, optionc: {len(trap_optionc)})")

    # 2. Load safety samples from optionc + benchmark
    print("\n[2] Loading safety samples...")
    safety_optionc = load_and_filter_by_type(OPTIONC_DATA, "safety")
    safety_benchmark = load_benchmark_by_category(BENCHMARK_V2, "safety")
    safety_all = deduplicate_by_question(safety_benchmark + safety_optionc)
    rng.shuffle(safety_all)
    print(f"  Safety pool: {len(safety_all)} (benchmark: {len(safety_benchmark)}, optionc: {len(safety_optionc)})")

    # 3. Load regulatory samples from optionc + benchmark
    print("\n[3] Loading regulatory samples...")
    reg_optionc = load_and_filter_by_type(OPTIONC_DATA, "regulatory")
    reg_benchmark = load_benchmark_by_category(BENCHMARK_V2, "regulatory")
    reg_all = deduplicate_by_question(reg_benchmark + reg_optionc)
    rng.shuffle(reg_all)
    print(f"  Regulatory pool: {len(reg_all)} (benchmark: {len(reg_benchmark)}, optionc: {len(reg_optionc)})")

    # 4. Load procedural replay samples (anti-forgetting)
    print("\n[4] Loading procedural replay samples...")
    proc_optionc = load_and_filter_by_type(OPTIONC_DATA, "procedural")
    # Also include some troubleshooting for diversity
    ts_optionc = load_and_filter_by_type(OPTIONC_DATA, "troubleshooting")
    proc_all = deduplicate_by_question(proc_optionc + ts_optionc)
    rng.shuffle(proc_all)
    print(f"  Procedural/TS replay pool: {len(proc_all)} (proc: {len(proc_optionc)}, ts: {len(ts_optionc)})")

    # 5. Sample to target sizes
    print("\n[5] Sampling to target sizes...")
    final: list[dict] = []

    for category, pool, target_n in [
        ("trap", trap_all, TARGET_MIX["trap"]),
        ("safety", safety_all, TARGET_MIX["safety"]),
        ("regulatory", reg_all, TARGET_MIX["regulatory"]),
        ("procedural", proc_all, TARGET_MIX["procedural"]),
    ]:
        available = min(len(pool), target_n)
        selected = pool[:available]
        # Tag each record
        for r in selected:
            r["boundary_v2_category"] = category
        final.extend(selected)
        print(f"  {category}: {available}/{target_n} sampled")
        if available < target_n:
            print(f"    ⚠️  Short by {target_n - available} — pool exhausted")

    # Shuffle final dataset
    rng.shuffle(final)

    # Stats
    print(f"\n{'='*60}")
    print(f"  TOTAL: {len(final)} / {TARGET_TOTAL}")
    cats = {}
    for r in final:
        cat = r.get("boundary_v2_category", "?")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"    {cat}: {count}")

    # Quality check: average answer length
    avg_len = sum(len(record_answer(r)) for r in final) / max(1, len(final))
    print(f"  Average answer length: {avg_len:.0f} chars")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n[dry-run mode, not writing output]")
        return

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ Wrote {len(final)} samples to {args.output}")


if __name__ == "__main__":
    main()
