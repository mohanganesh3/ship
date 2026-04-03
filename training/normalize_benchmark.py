#!/usr/bin/env python3
"""Normalize the 1.7B maritime benchmark into the 7-slot operational contract.

Reads the existing local_benchmark_1p7b.jsonl and produces
local_benchmark_v2_1p7b.jsonl with:
- Properly populated escalation_targets (extracted from required_checks and reference_answer)
- Separated do_not field (no longer mixed into required_checks)
- Clean required_checks (only actionable checks, no "Do not:" or "Escalate to:" entries)
- 7-slot operational contract in a "slots" field
- modal_required flag based on category

Usage:
    python normalize_benchmark.py [--validate]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
BENCHMARK_IN = BASE_DIR / "ship" / "maritime_pipeline" / "data" / "final" / "local_benchmark_1p7b.jsonl"
BENCHMARK_OUT = BASE_DIR / "ship" / "maritime_pipeline" / "data" / "final" / "local_benchmark_v2_1p7b.jsonl"

# ---------------------------------------------------------------------------
# Escalation aliases — any of these map to the same canonical role
# ---------------------------------------------------------------------------
ESCALATION_ALIASES: dict[str, str] = {
    "master": "Master",
    "ship's master": "Master",
    "the master": "Master",
    "captain": "Master",
    "chief engineer": "Chief Engineer",
    "c/e": "Chief Engineer",
    "the chief engineer": "Chief Engineer",
    "chief officer": "Chief Officer",
    "chief mate": "Chief Officer",
    "dpa": "DPA",
    "designated person ashore": "DPA",
    "flag state": "Flag State",
    "company": "Company",
    "port state control": "Port State Control",
    "psc": "Port State Control",
    "tmas": "TMAS",
    "rcc": "RCC",
    "mrcc": "RCC",
    "bridge team": "Bridge Team",
    "security officer": "Security Officer",
    "ship security officer": "Security Officer",
    "sso": "Security Officer",
    "cso": "Company Security Officer",
    "company security officer": "Company Security Officer",
    "medical officer": "Medical Officer",
    "terminal": "Terminal",
    "class surveyor": "Class Surveyor",
    "classification society": "Class Surveyor",
}


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def resolve_escalation_alias(raw: str) -> str:
    """Map a raw escalation target string to its canonical form."""
    lowered = normalize_space(raw).lower().strip("., ")
    # Direct alias lookup
    if lowered in ESCALATION_ALIASES:
        return ESCALATION_ALIASES[lowered]
    # Partial match — check if any alias key is a substring
    for alias_key, canonical in ESCALATION_ALIASES.items():
        if alias_key in lowered:
            return canonical
    # If no alias found, title-case the original
    return normalize_space(raw).strip("., ").title()


def extract_escalation_from_text(text: str) -> list[str]:
    """Extract escalation targets from free text containing 'Escalate to:' lines."""
    targets = []
    for line in text.splitlines():
        norm = normalize_space(line)
        # Remove numbering
        norm = re.sub(r"^\d+\.\s*", "", norm)
        norm = normalize_space(norm).replace("**", "")
        lowered = norm.lower()
        if lowered.startswith("escalate to:") or lowered.startswith("escalate to "):
            payload = norm.split(":", 1)[1].strip() if ":" in norm else norm[len("escalate to "):].strip()
            # Split by comma or " and "
            parts = re.split(r",|\band\b", payload)
            for part in parts:
                cleaned = normalize_space(part).strip("., ")
                if cleaned and len(cleaned) > 1:
                    canonical = resolve_escalation_alias(cleaned)
                    if canonical and canonical not in targets:
                        targets.append(canonical)
    return targets


def extract_do_not_from_text(text: str) -> list[str]:
    """Extract 'Do not:' prohibitions from free text."""
    prohibitions = []
    for line in text.splitlines():
        norm = normalize_space(line)
        norm = re.sub(r"^\d+\.\s*", "", norm)
        norm = normalize_space(norm).replace("**", "")
        lowered = norm.lower()
        if lowered.startswith("do not:") or lowered.startswith("do not "):
            payload = norm.split(":", 1)[1].strip() if ":" in norm else norm[len("do not "):].strip()
            payload = normalize_space(payload)
            if payload and len(payload) > 5:
                prohibitions.append(payload)
    return prohibitions


def extract_immediate_control(answer: str) -> str:
    """Extract the first actionable line from the answer as immediate control."""
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "")
        lowered = norm.lower()
        if not norm or len(norm) < 10:
            continue
        # Skip meta headings
        if any(cue in lowered for cue in ("context", "logical error", "aesthetic", "background", "scenario")):
            continue
        # Skip "Do not:" and "Escalate to:" lines
        if lowered.startswith("do not:") or lowered.startswith("escalate to:"):
            continue
        # Look for immediate action cues
        if any(cue in lowered for cue in ("immediately", "stop", "isolate", "activate", "secure", "shut down")):
            return norm
        # First actionable line
        if any(cue in lowered for cue in ("check", "verify", "inspect", "confirm", "ensure", "document", "record")):
            return norm
    # Fallback: first non-meta line
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "")
        lowered = norm.lower()
        if not norm or len(norm) < 10:
            continue
        if any(cue in lowered for cue in ("context", "logical error", "aesthetic", "background")):
            continue
        if not lowered.startswith("do not:") and not lowered.startswith("escalate to:"):
            return norm
    return ""


def extract_verification_inputs(answer: str) -> str:
    """Extract verification/checking steps from the answer."""
    verifications = []
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "")
        lowered = norm.lower()
        if not norm or len(norm) < 10:
            continue
        if any(cue in lowered for cue in ("verify", "check", "inspect", "review", "confirm status", "examine")):
            if not lowered.startswith("do not:") and not lowered.startswith("escalate to:"):
                verifications.append(norm)
    return "; ".join(verifications[:2]) if verifications else ""


def extract_corrective_action(answer: str) -> str:
    """Extract the corrective/procedural action from the answer."""
    actions = []
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "")
        lowered = norm.lower()
        if not norm or len(norm) < 10:
            continue
        if any(cue in lowered for cue in (
            "correct", "schedule", "replace", "repair", "adjust", "restore",
            "apply", "implement", "initiate", "perform", "conduct", "arrange",
            "calibrate", "only if", "must be", "shall", "required",
        )):
            if not lowered.startswith("do not:") and not lowered.startswith("escalate to:"):
                actions.append(norm)
    return "; ".join(actions[:2]) if actions else ""


def extract_documentation(answer: str) -> str:
    """Extract documentation/logging steps from the answer."""
    docs = []
    for line in answer.splitlines():
        norm = normalize_space(re.sub(r"^\d+\.\s*", "", line)).replace("**", "")
        lowered = norm.lower()
        if not norm or len(norm) < 10:
            continue
        if any(cue in lowered for cue in ("document", "log", "record", "report", "notify", "brief")):
            if not lowered.startswith("do not:") and not lowered.startswith("escalate to:"):
                docs.append(norm)
    return "; ".join(docs[:2]) if docs else ""


def clean_required_checks(checks: list[str]) -> list[str]:
    """Remove 'Do not:' and 'Escalate to:' entries from required_checks."""
    cleaned = []
    for check in checks:
        norm = normalize_space(check)
        lowered = norm.lower()
        if lowered.startswith("do not:") or lowered.startswith("do not "):
            continue
        if lowered.startswith("escalate to:") or lowered.startswith("escalate to "):
            continue
        if norm and len(norm) > 5:
            cleaned.append(norm)
    return cleaned


def extract_do_not_from_checks(checks: list[str]) -> list[str]:
    """Extract 'Do not:' items from the required_checks list."""
    prohibitions = []
    for check in checks:
        norm = normalize_space(check)
        lowered = norm.lower()
        if lowered.startswith("do not:"):
            payload = norm.split(":", 1)[1].strip() if ":" in norm else ""
            if payload and len(payload) > 5:
                prohibitions.append(payload)
        elif lowered.startswith("do not "):
            payload = norm[len("Do not "):].strip()
            if payload and len(payload) > 5:
                prohibitions.append(payload)
    return prohibitions


def extract_escalation_from_checks(checks: list[str]) -> list[str]:
    """Extract escalation targets from the required_checks list."""
    targets = []
    for check in checks:
        norm = normalize_space(check)
        lowered = norm.lower()
        if lowered.startswith("escalate to:") or lowered.startswith("escalate to "):
            payload = norm.split(":", 1)[1].strip() if ":" in norm else norm[len("escalate to "):].strip()
            parts = re.split(r",|\band\b", payload)
            for part in parts:
                cleaned = normalize_space(part).strip("., ")
                if cleaned and len(cleaned) > 1:
                    canonical = resolve_escalation_alias(cleaned)
                    if canonical and canonical not in targets:
                        targets.append(canonical)
    return targets


def normalize_record(record: dict) -> dict:
    """Normalize a single benchmark record into the v2 format."""
    answer = normalize_space(record.get("reference_answer", ""))
    old_checks = record.get("required_checks", [])
    old_escalation = record.get("escalation_targets", [])
    category = normalize_space(record.get("category", "")).lower()

    # Extract escalation targets from both required_checks and reference_answer
    escalation_from_checks = extract_escalation_from_checks(old_checks)
    escalation_from_answer = extract_escalation_from_text(record.get("reference_answer", ""))
    # Also resolve any existing escalation_targets
    escalation_from_old = [resolve_escalation_alias(t) for t in old_escalation if normalize_space(t)]

    # Merge and deduplicate (preserving order)
    all_escalation = []
    for t in escalation_from_checks + escalation_from_answer + escalation_from_old:
        if t not in all_escalation:
            all_escalation.append(t)

    # Extract do_not from both required_checks and reference_answer
    do_not_from_checks = extract_do_not_from_checks(old_checks)
    do_not_from_answer = extract_do_not_from_text(record.get("reference_answer", ""))
    all_do_not = []
    for d in do_not_from_checks + do_not_from_answer:
        if d not in all_do_not:
            all_do_not.append(d)

    # Clean required_checks (remove "Do not:" and "Escalate to:" entries)
    clean_checks = clean_required_checks(old_checks)

    # Extract 7-slot structure
    full_answer = record.get("reference_answer", "")
    slots = {
        "immediate_control": extract_immediate_control(full_answer),
        "verification_inputs": extract_verification_inputs(full_answer),
        "corrective_action": extract_corrective_action(full_answer),
        "documentation": extract_documentation(full_answer),
        "do_not": all_do_not,
        "escalation_targets": all_escalation,
        "modal_required": category in ("regulatory",),
    }

    # Build normalized record
    normalized = {
        "id": record["id"],
        "category": record["category"],
        "domain": record.get("domain", "UNK"),
        "subtopic_id": record.get("subtopic_id", ""),
        "question": record["question"],
        "reference_answer": record["reference_answer"],
        "required_checks": clean_checks,
        "forbidden_checks": record.get("forbidden_checks", []),
        "do_not": all_do_not,
        "escalation_targets": all_escalation,
        "modal_required": slots["modal_required"],
        "slots": slots,
        "source": record.get("source", ""),
    }
    return normalized


def validate_record(record: dict, idx: int) -> list[str]:
    """Validate a normalized record, return list of issues."""
    issues = []
    if not record.get("required_checks"):
        issues.append(f"[{record['id']}] (line {idx+1}) Empty required_checks")
    if not record.get("escalation_targets"):
        issues.append(f"[{record['id']}] (line {idx+1}) Empty escalation_targets")
    if not record.get("do_not"):
        issues.append(f"[{record['id']}] (line {idx+1}) Empty do_not")
    if record.get("modal_required") and record.get("category") != "regulatory":
        issues.append(f"[{record['id']}] (line {idx+1}) modal_required set for non-regulatory")
    if record.get("category") == "regulatory" and not record.get("modal_required"):
        issues.append(f"[{record['id']}] (line {idx+1}) regulatory without modal_required")
    # Check for generic prohibitions
    for d in record.get("do_not", []):
        lowered = d.lower()
        if lowered in ("continue", "proceed", "do it"):
            issues.append(f"[{record['id']}] (line {idx+1}) Generic prohibition: {d}")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize maritime benchmark to 7-slot format")
    parser.add_argument("--validate", action="store_true", help="Validate only, don't write output")
    parser.add_argument("--input", type=Path, default=BENCHMARK_IN)
    parser.add_argument("--output", type=Path, default=BENCHMARK_OUT)
    args = parser.parse_args()

    # Read input
    records = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"Read {len(records)} records from {args.input}")

    # Normalize
    normalized = [normalize_record(r) for r in records]

    # Category distribution
    cats: dict[str, int] = {}
    for r in normalized:
        cat = r["category"]
        cats[cat] = cats.get(cat, 0) + 1
    print("\nCategory distribution:")
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")

    # Coverage stats
    has_escalation = sum(1 for r in normalized if r["escalation_targets"])
    has_do_not = sum(1 for r in normalized if r["do_not"])
    has_checks = sum(1 for r in normalized if r["required_checks"])
    print(f"\nCoverage:")
    print(f"  has escalation_targets: {has_escalation}/{len(normalized)}")
    print(f"  has do_not: {has_do_not}/{len(normalized)}")
    print(f"  has required_checks: {has_checks}/{len(normalized)}")

    # Validate
    all_issues = []
    for idx, r in enumerate(normalized):
        issues = validate_record(r, idx)
        all_issues.extend(issues)

    if all_issues:
        print(f"\n⚠️  Validation issues ({len(all_issues)}):")
        for issue in all_issues[:30]:
            print(f"  {issue}")
        if len(all_issues) > 30:
            print(f"  ... and {len(all_issues) - 30} more")
    else:
        print("\n✅ All records pass validation")

    if args.validate:
        print("\n[validate-only mode, not writing output]")
        return

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for r in normalized:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ Wrote {len(normalized)} normalized records to {args.output}")


if __name__ == "__main__":
    main()
