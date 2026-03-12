from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .paths import import_config
from .utils import seeded_random


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception as exc:
                raise ValueError(f"Invalid JSON on {path}:{ln}") from exc
    return out


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def _require_source_ids(records: list[dict[str, Any]], label: str) -> None:
    missing = 0
    bad_type = 0
    for r in records:
        sid = r.get("source_id")
        if sid is None or sid == "":
            missing += 1
        elif not isinstance(sid, str):
            bad_type += 1
    if missing or bad_type:
        raise SystemExit(
            f"{label}: all records must have a non-empty string source_id for leakage checks "
            f"(missing={missing}, bad_type={bad_type})."
        )


def _atomic_overwrite_jsonl(dst: Path, records: list[dict[str, Any]]) -> None:
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    _write_jsonl(tmp, records)
    tmp.replace(dst)


def _get_domain_tags(record: dict[str, Any]) -> list[str]:
    """Return the domain tags for a record.

    The maritime CPT corpus uses `domain_tags` (list[str]).
    If a corpus provides `domain_tag` (str), we normalize it to a single-element list.
    """

    if isinstance(record.get("domain_tag"), str) and record.get("domain_tag"):
        return [str(record["domain_tag"]).strip()]

    tags = record.get("domain_tags")
    if isinstance(tags, list):
        out: list[str] = []
        for t in tags:
            if isinstance(t, str) and t.strip():
                out.append(t.strip())
        if out:
            return out
    return ["GENERAL"]


def _stratified_sample_source_ids_by_domain_tag(
    records: list[dict[str, Any]],
    fraction: float,
    seed: int,
) -> set[str]:
    """Sample source_ids with a 2% target *per domain tag*.

    For each unique domain tag value, sample ceil(n_tag * fraction) records
    (minimum 1) among records that contain that tag.

    Because records can have multiple tags, the final validation split is the union
    of the per-tag samples.
    """

    tag_to_indices: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        for tg in _get_domain_tags(r):
            tag_to_indices[tg].append(i)

    rng = seeded_random(seed)
    selected_source_ids: set[str] = set()

    for tg in sorted(tag_to_indices.keys()):
        idxs = tag_to_indices[tg]
        n = len(idxs)
        if n == 0:
            continue
        k = max(1, int(math.ceil(n * fraction)))
        chosen = rng.sample(idxs, k=min(k, n))
        for i in chosen:
            selected_source_ids.add(str(records[i]["source_id"]))

    return selected_source_ids


def _random_sample_source_ids(
    records: list[dict[str, Any]],
    fraction: float,
    seed: int,
) -> set[str]:
    rng = seeded_random(seed)
    n = len(records)
    if n == 0:
        return set()
    k = max(1, int(math.ceil(n * fraction)))
    chosen_idxs = rng.sample(range(n), k=min(k, n))
    return {str(records[i]["source_id"]) for i in chosen_idxs}


def _split_by_source_id(
    records: list[dict[str, Any]],
    selected_source_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    val: list[dict[str, Any]] = []
    train: list[dict[str, Any]] = []
    for r in records:
        sid = str(r["source_id"])
        if sid in selected_source_ids:
            val.append(r)
        else:
            train.append(r)
    return val, train


def _domain_breakdown(records: list[dict[str, Any]]) -> Counter[str]:
    c: Counter[str] = Counter()
    for r in records:
        # The maritime corpus is multi-label (domain_tags). We count a record once per tag.
        for tg in _get_domain_tags(r):
            c[tg] += 1
    return c


def _merge_back_for_resplit(train_path: Path, val_path: Path) -> list[dict[str, Any]]:
    """Merge train + existing val (if present) for a clean re-split.

    This makes the script safe to re-run with --force without progressively shrinking
    the training corpus.

    We do NOT de-duplicate here; we only apply a deterministic sort to make sampling
    reproducible across runs.
    """

    train = _load_jsonl(train_path)
    val: list[dict[str, Any]] = []
    if val_path.exists() and val_path.stat().st_size > 0:
        val = _load_jsonl(val_path)

    combined = train + val

    # Sort for stable sampling. Prefer source_id, then sha256/id if present.
    def _k(r: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(r.get("source_id") or ""),
            str(r.get("sha256") or ""),
            str(r.get("id") or ""),
        )

    combined.sort(key=_k)
    return combined


def _leakage_check(
    val_records: list[dict[str, Any]],
    train_records: list[dict[str, Any]],
    label: str,
) -> None:
    val_sids = {str(r["source_id"]) for r in val_records}
    train_sids = {str(r["source_id"]) for r in train_records}
    inter = val_sids.intersection(train_sids)
    if inter:
        sample = sorted(list(inter))[:10]
        raise SystemExit(
            f"Leakage check FAILED for {label}: {len(inter)} source_id values appear in both val and train. "
            f"Examples: {sample}"
        )


def main() -> int:
    cfg = import_config()

    ap = argparse.ArgumentParser(
        description=(
            "Create held-out validation splits for CPT (must never be trained on).\n\n"
            "Split 1: stratified 2% across domain_tag from cpt_corpus.jsonl\n"
            "Split 2: random 2% from general_replay.jsonl\n"
            "Both use seed=42 by default and overwrite the source corpora in place."
        )
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fraction", type=float, default=0.02)

    ap.add_argument(
        "--maritime-path",
        type=Path,
        default=cfg.FINAL_DIR / "cpt_corpus.jsonl",
    )
    ap.add_argument(
        "--general-path",
        type=Path,
        default=cfg.FINAL_DIR / "general_replay.jsonl",
    )

    ap.add_argument(
        "--out-val-maritime",
        type=Path,
        default=cfg.FINAL_DIR / "cpt_val_maritime.jsonl",
    )
    ap.add_argument(
        "--out-val-general",
        type=Path,
        default=cfg.FINAL_DIR / "cpt_val_general.jsonl",
    )

    ap.add_argument(
        "--force",
        action="store_true",
        help=(
            "Allow overwriting existing val split files and in-place corpora. "
            "When set, the script merges any existing val split back into the input corpus "
            "before re-splitting (prevents repeated shrinking)."
        ),
    )

    args = ap.parse_args()

    if not args.force:
        if args.out_val_maritime.exists() and args.out_val_maritime.stat().st_size > 0:
            raise SystemExit(
                f"Refusing to overwrite existing {args.out_val_maritime}. Re-run with --force if intended."
            )
        if args.out_val_general.exists() and args.out_val_general.stat().st_size > 0:
            raise SystemExit(
                f"Refusing to overwrite existing {args.out_val_general}. Re-run with --force if intended."
            )

    # ---- Split 1: maritime stratified by domain tag(s) ----
    maritime_records = (
        _merge_back_for_resplit(args.maritime_path, args.out_val_maritime)
        if args.force
        else _load_jsonl(args.maritime_path)
    )
    _require_source_ids(maritime_records, label="cpt_corpus.jsonl")

    maritime_selected_sids = _stratified_sample_source_ids_by_domain_tag(
        maritime_records, fraction=args.fraction, seed=args.seed
    )

    val_maritime, train_maritime = _split_by_source_id(maritime_records, maritime_selected_sids)

    # Write val first, then overwrite corpus
    _atomic_overwrite_jsonl(args.out_val_maritime, val_maritime)
    _atomic_overwrite_jsonl(args.maritime_path, train_maritime)

    # ---- Split 2: general replay random ----
    general_records = (
        _merge_back_for_resplit(args.general_path, args.out_val_general)
        if args.force
        else _load_jsonl(args.general_path)
    )
    _require_source_ids(general_records, label="general_replay.jsonl")

    general_selected_sids = _random_sample_source_ids(
        general_records,
        fraction=args.fraction,
        seed=args.seed,
    )

    val_general, train_general = _split_by_source_id(general_records, general_selected_sids)

    _atomic_overwrite_jsonl(args.out_val_general, val_general)
    _atomic_overwrite_jsonl(args.general_path, train_general)

    # ---- Leakage checks (source_id) ----
    _leakage_check(val_maritime, train_maritime, label="maritime")
    _leakage_check(val_general, train_general, label="general")

    # ---- Required prints ----
    print("cpt_val_maritime.jsonl")
    print(f"- total_records: {len(val_maritime)}")
    dom = _domain_breakdown(val_maritime)
    print("- breakdown_by_domain_tag:")
    for k, v in sorted(dom.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  - {k}: {v}")

    print("cpt_val_general.jsonl")
    print(f"- total_records: {len(val_general)}")

    print("cpt_corpus.jsonl")
    print(f"- new_total_records: {len(train_maritime)}")

    print("general_replay.jsonl")
    print(f"- new_total_records: {len(train_general)}")

    print("leakage_check")
    print("- maritime: OK (no source_id overlap between val/train)")
    print("- general:  OK (no source_id overlap between val/train)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
