from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .paths import import_config


def count_jsonl(path: Path) -> int:
    return count_jsonl_limited(path, max_lines=0)


def count_jsonl_limited(path: Path, max_lines: int = 0) -> int:
    """Count non-empty JSONL lines.

    If max_lines > 0, stop after counting that many lines (useful for very large files).
    """
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
                if max_lines and n >= max_lines:
                    break
    return n


def _eval_items_filled(path: Path) -> tuple[int, int]:
    """Return (total, filled)."""
    if not path.exists():
        return (0, 0)
    total = 0
    filled = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("question") and rec.get("expected_answer") and rec.get("citations"):
                filled += 1
    return total, filled


def main() -> int:
    cfg = import_config()
    ap = argparse.ArgumentParser(description="Validate presence and basic integrity of Stage-0 artifacts.")
    ap.add_argument("--final-dir", type=Path, default=cfg.FINAL_DIR)
    ap.add_argument("--allow-empty-general", action="store_true")
    ap.add_argument("--min-eval-filled", type=int, default=0)
    args = ap.parse_args()

    final_dir = args.final_dir

    required = {
        "cpt_corpus.jsonl": final_dir / "cpt_corpus.jsonl",
        "filter_report.jsonl": final_dir / "filter_report.jsonl",
        "cpt_corpus_deduped.jsonl": final_dir / "cpt_corpus_deduped.jsonl",
        "dedup_report.jsonl": final_dir / "dedup_report.jsonl",
        "cpt_val_maritime.jsonl": final_dir / "cpt_val_maritime.jsonl",
        "cpt_val_general.jsonl": final_dir / "cpt_val_general.jsonl",
        "chunks.jsonl": final_dir / "chunks.jsonl",
        "eval_set.jsonl": final_dir / "eval_set.jsonl",
        "pipeline_audit.log": final_dir / "pipeline_audit.log",
        "general_replay.jsonl": final_dir / "general_replay.jsonl",
    }

    missing = [name for name, p in required.items() if not p.exists()]
    if missing:
        print("Missing required artifacts:")
        for m in missing:
            print(f"- {m}")
        return 2

    # Non-empty checks (corpus must exist)
    corpus_n = count_jsonl_limited(required["cpt_corpus.jsonl"], max_lines=1)
    if corpus_n <= 0:
        print("cpt_corpus.jsonl is empty")
        return 2

    dedup_n = count_jsonl_limited(required["cpt_corpus_deduped.jsonl"], max_lines=1)
    if dedup_n <= 0:
        print("cpt_corpus_deduped.jsonl is empty")
        return 2

    chunks_n = count_jsonl_limited(required["chunks.jsonl"], max_lines=1)
    if chunks_n <= 0:
        print("chunks.jsonl is empty")
        return 2

    total_eval, filled_eval = _eval_items_filled(required["eval_set.jsonl"])
    if total_eval < 1:
        print("eval_set.jsonl has no items; run build_eval_scaffold.py")
        return 2

    if filled_eval < args.min_eval_filled:
        print(f"eval_set.jsonl filled items {filled_eval} < required {args.min_eval_filled}")
        return 2

    # Optional general replay content requirement (artifact required, content may be empty)
    if not required["general_replay.jsonl"].exists() and args.allow_empty_general:
        required["general_replay.jsonl"].write_text("", encoding="utf-8")

    print("Stage-0 validation passed.")
    print(f"Docs kept: >= {corpus_n}")
    print(f"Docs deduped: >= {dedup_n}")
    print(f"Chunks: >= {chunks_n}")
    print(f"Eval items: {total_eval} (filled: {filled_eval})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
