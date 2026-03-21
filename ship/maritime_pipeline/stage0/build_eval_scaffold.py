from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .paths import import_config
from .utils import now_iso, seeded_random, stable_id


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def build_scaffold(
    chunks: list[dict[str, Any]],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Select a diverse subset of chunks and create empty eval items.

    This does NOT attempt to generate questions automatically. It creates a structured
    template that must be manually filled and traced back to `chunk_id`.
    """
    r = seeded_random(seed)

    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for c in chunks:
        buckets[(str(c.get("doc_type") or "unknown"), str(c.get("difficulty_hint") or "factual_simple"))].append(c)

    keys = sorted(buckets.keys())
    per_bucket = max(1, n // max(1, len(keys)))

    selected: list[dict[str, Any]] = []
    for k in keys:
        items = buckets[k]
        r.shuffle(items)
        selected.extend(items[:per_bucket])

    # top up
    if len(selected) < n:
        remaining = [c for c in chunks if c not in selected]
        r.shuffle(remaining)
        selected.extend(remaining[: (n - len(selected))])

    selected = selected[:n]

    eval_items: list[dict[str, Any]] = []
    for c in selected:
        eid = stable_id("eval", str(c.get("id")))
        eval_items.append(
            {
                "id": eid,
                "chunk_id": c.get("id"),
                "source_id": c.get("source_id"),
                "doc_type": c.get("doc_type"),
                "difficulty_hint": c.get("difficulty_hint"),
                "question": None,
                "expected_answer": None,
                "answer_type": None,
                "citations": [],
                "notes": "FILL ME: Write a question that is answerable ONLY from this chunk. Add citations by quoting exact substrings.",
                "created_at": now_iso(),
            }
        )

    return eval_items


def main() -> int:
    cfg = import_config()
    ap = argparse.ArgumentParser(description="Create an eval_set.jsonl scaffold (manual fill required).")
    ap.add_argument("--chunks", type=Path, default=cfg.FINAL_DIR / "chunks.jsonl")
    ap.add_argument("--out", type=Path, default=cfg.FINAL_DIR / "eval_set.jsonl")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    chunks = load_jsonl(args.chunks)
    items = build_scaffold(chunks, n=args.n, seed=args.seed)
    write_jsonl(args.out, items)
    print(f"Wrote {len(items)} eval scaffold items to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
