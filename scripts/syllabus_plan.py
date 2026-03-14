from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


BUCKET_TO_DOMAINS: dict[str, tuple[str, ...]] = {
    "engineering": tuple("ABCDEFGHIJ"),
    "cargo": tuple("KLMN"),
    "safety": ("O", "P", "Q", "R", "S", "X", "Y", "Z"),
    "regulation": ("T", "U", "V", "W"),
}

DOMAIN_TO_BUCKET = {
    domain: bucket
    for bucket, domains in BUCKET_TO_DOMAINS.items()
    for domain in domains
}

PRIORITY_ORDER: tuple[str, ...] = (
    "O",
    "T",
    "Q",
    "R",
    "S",
    "P",
    "X",
    "Y",
    "Z",
    "U",
    "V",
    "W",
    "A",
    "D",
    "H",
    "J",
    "B",
    "C",
    "E",
    "F",
    "G",
    "I",
    "K",
    "L",
    "M",
    "N",
)

PRESETS: dict[str, dict[str, int]] = {
    # 29k across the focus buckets; existing cargo examples keep the total near 30k.
    "shipboard_30k": {
        "engineering": 8_000,
        "safety": 15_000,
        "regulation": 6_000,
    }
}


@dataclass(frozen=True)
class DomainRow:
    domain: str
    domain_name: str
    bucket: str
    subtopics: int
    current: int
    target: int

    @property
    def deficit(self) -> int:
        return max(0, self.target - self.current)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_syllabus(path: Path) -> dict[str, dict]:
    return load_json(path)


def subtopic_counts(syllabus: dict[str, dict]) -> dict[str, int]:
    return {
        domain: len(payload["Subcategories"])
        for domain, payload in syllabus.items()
    }


def largest_remainder_alloc(weights: dict[str, int], total: int) -> dict[str, int]:
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        return {key: 0 for key in weights}

    raw = {
        key: total * value / weight_sum
        for key, value in weights.items()
    }
    allocated = {key: int(value) for key, value in raw.items()}
    remaining = total - sum(allocated.values())

    if remaining > 0:
        remainders = sorted(
            ((raw[key] - allocated[key], key) for key in weights),
            reverse=True,
        )
        for _, key in remainders[:remaining]:
            allocated[key] += 1

    return allocated


def existing_domain_counts(gold_root: Path, generated_file: Path | None = None) -> dict[str, int]:
    counts = {domain: 0 for domain in DOMAIN_TO_BUCKET}

    for domain in DOMAIN_TO_BUCKET:
        domain_file = gold_root / f"domain_{domain}.jsonl"
        if domain_file.exists():
            with domain_file.open("r", encoding="utf-8") as handle:
                counts[domain] += sum(1 for line in handle if line.strip())

    if generated_file and generated_file.exists():
        with generated_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                domain = record.get("domain_letter")
                if domain in counts:
                    counts[domain] += 1

    return counts


def compute_domain_targets(
    syllabus: dict[str, dict],
    preset: str,
    focus_buckets: tuple[str, ...] | None = None,
    existing_counts: dict[str, int] | None = None,
) -> dict[str, int]:
    if preset not in PRESETS:
        raise KeyError(f"Unknown preset: {preset}")

    existing_counts = existing_counts or {}
    focus = focus_buckets or tuple(PRESETS[preset].keys())
    counts = subtopic_counts(syllabus)
    targets: dict[str, int] = {}

    for bucket in focus:
        domains = BUCKET_TO_DOMAINS[bucket]
        bucket_target = PRESETS[preset][bucket]
        weights = {domain: counts[domain] for domain in domains}
        bucket_alloc = largest_remainder_alloc(weights, bucket_target)
        for domain, target in bucket_alloc.items():
            targets[domain] = max(target, existing_counts.get(domain, 0))

    return targets


def build_domain_rows(
    syllabus: dict[str, dict],
    targets: dict[str, int],
    existing_counts: dict[str, int],
) -> list[DomainRow]:
    counts = subtopic_counts(syllabus)
    rows: list[DomainRow] = []

    for domain, target in targets.items():
        rows.append(
            DomainRow(
                domain=domain,
                domain_name=syllabus[domain]["Domain"],
                bucket=DOMAIN_TO_BUCKET[domain],
                subtopics=counts[domain],
                current=existing_counts.get(domain, 0),
                target=target,
            )
        )

    order_index = {domain: index for index, domain in enumerate(PRIORITY_ORDER)}
    rows.sort(key=lambda row: order_index.get(row.domain, 999))
    return rows


def bucket_summary(rows: list[DomainRow]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = summary.setdefault(
            row.bucket,
            {"current": 0, "target": 0, "deficit": 0, "subtopics": 0},
        )
        bucket["current"] += row.current
        bucket["target"] += row.target
        bucket["deficit"] += row.deficit
        bucket["subtopics"] += row.subtopics
    return summary
