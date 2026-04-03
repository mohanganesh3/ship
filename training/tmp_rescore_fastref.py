#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from phase2_optionc_common import score_response


SRC = Path("/home/mohanganesh/ship/logs/local_eval_correction_rerun_fastref_1p7b.json")
BENCH = Path("/home/mohanganesh/ship/ship/maritime_pipeline/data/final/local_benchmark_1p7b.jsonl")
OUT = Path("/home/mohanganesh/ship/logs/local_eval_correction_rerun_fastref_rescored_1p7b.json")

THRESHOLDS = {
    "regulatory": 85.0,
    "procedural": 80.0,
    "troubleshooting": 75.0,
    "safety": 90.0,
    "calculation": 80.0,
    "trap": 80.0,
}


def main() -> None:
    original = json.loads(SRC.read_text(encoding="utf-8"))
    benchmark = {}
    with BENCH.open(encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            benchmark[item["id"]] = item

    categories = {}
    failures = {}
    for category, items in original.get("failures", {}).items():
        passed = 0
        escalation_miss_count = 0
        failed_items = []
        for item in items:
            bench_item = benchmark[item["id"]]
            score = score_response(
                item["model_answer"],
                required_checks=bench_item.get("required_checks", []),
                forbidden_checks=bench_item.get("forbidden_checks", []),
                escalation_targets=bench_item.get("escalation_targets", []),
                category=category,
            )
            if score["pass"]:
                passed += 1
            else:
                copy = dict(item)
                copy["score"] = score
                failed_items.append(copy)
            if bench_item.get("escalation_targets") and score["escalation_total"] > 0 and score["escalation_hit_count"] == 0:
                escalation_miss_count += 1

        tested = len(items)
        rate = (passed / tested * 100.0) if tested else 0.0
        categories[category] = {
            "tested": tested,
            "pass_count": passed,
            "pass_rate": round(rate, 2),
            "threshold": THRESHOLDS.get(category, 0.0),
            "status": "PASS" if rate >= THRESHOLDS.get(category, 0.0) else "FAIL",
            "escalation_miss_count": escalation_miss_count,
            "escalation_miss_rate": round((escalation_miss_count / tested * 100.0), 2) if tested else 0.0,
        }
        failures[category] = failed_items

    result = {
        "label": "correction_rerun_fastref_rescored",
        "adapter_dir": original.get("adapter_dir"),
        "benchmark": str(BENCH),
        "categories": categories,
        "failures": failures,
        "overall_status": "PASS"
        if all(bucket["pass_rate"] >= bucket["threshold"] for bucket in categories.values())
        else "FAIL",
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(result["overall_status"])
    print(json.dumps(categories, indent=2))


if __name__ == "__main__":
    main()
