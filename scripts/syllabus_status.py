#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from syllabus_plan import (
    PRESETS,
    build_domain_rows,
    bucket_summary,
    compute_domain_targets,
    existing_domain_counts,
    load_syllabus,
)


REPO_ROOT = Path(os.environ.get("SHIP_REPO_ROOT", "/home/mohanganesh/ship"))
GOLD_ROOT = REPO_ROOT / "training/gold_standard"
SYLLABUS_FILE = GOLD_ROOT / "master_syllabus_v1.json"
GENERATED_FILE = GOLD_ROOT / "generated/syllabus_generated.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show exact syllabus coverage status for the 1.7B data push."
    )
    parser.add_argument(
        "--preset",
        default="shipboard_30k",
        choices=sorted(PRESETS),
    )
    parser.add_argument(
        "--focus",
        default="engineering,safety,regulation",
        help="Comma-separated focus buckets.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional path to write the status as JSON.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    focus = tuple(part.strip() for part in args.focus.split(",") if part.strip())

    syllabus = load_syllabus(SYLLABUS_FILE)
    existing = existing_domain_counts(GOLD_ROOT, GENERATED_FILE)
    targets = compute_domain_targets(
        syllabus,
        preset=args.preset,
        focus_buckets=focus,
        existing_counts=existing,
    )
    rows = build_domain_rows(syllabus, targets, existing)
    summary = bucket_summary(rows)

    total_current = sum(row.current for row in rows)
    total_target = sum(row.target for row in rows)
    total_deficit = sum(row.deficit for row in rows)

    print(f"Preset: {args.preset}")
    print(f"Focus: {', '.join(focus)}")
    print(f"Current: {total_current:,}")
    print(f"Target:  {total_target:,}")
    print(f"Deficit: {total_deficit:,}")
    print()

    print("Bucket Summary")
    for bucket, payload in summary.items():
        print(
            f"- {bucket:11} current={payload['current']:>5,} "
            f"target={payload['target']:>5,} deficit={payload['deficit']:>5,} "
            f"subtopics={payload['subtopics']:>3}"
        )

    print()
    print("Domain Summary")
    for row in rows:
        print(
            f"- {row.domain} {row.bucket:11} current={row.current:>5,} "
            f"target={row.target:>5,} deficit={row.deficit:>5,} "
            f"subtopics={row.subtopics:>3}  {row.domain_name}"
        )

    if args.json_out:
        payload = {
            "preset": args.preset,
            "focus": list(focus),
            "summary": summary,
            "domains": [
                {
                    "domain": row.domain,
                    "domain_name": row.domain_name,
                    "bucket": row.bucket,
                    "subtopics": row.subtopics,
                    "current": row.current,
                    "target": row.target,
                    "deficit": row.deficit,
                }
                for row in rows
            ],
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
