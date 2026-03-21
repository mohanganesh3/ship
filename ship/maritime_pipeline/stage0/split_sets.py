from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .paths import import_config
from .utils import seeded_random


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


def main() -> int:
    cfg = import_config()

    ap = argparse.ArgumentParser(description="Create CPT validation splits (maritime + general).")
    ap.add_argument(
        "--maritime-in",
        type=Path,
        default=cfg.FINAL_DIR / "cpt_corpus_deduped.jsonl",
        help="Deduped maritime corpus",
    )
    ap.add_argument(
        "--general-in",
        type=Path,
        default=cfg.FINAL_DIR / "general_replay.jsonl",
        help="General replay corpus",
    )
    ap.add_argument("--val-fraction", type=float, default=0.01)
    ap.add_argument("--min-val", type=int, default=200)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out-maritime", type=Path, default=cfg.FINAL_DIR / "cpt_val_maritime.jsonl")
    ap.add_argument("--out-general", type=Path, default=cfg.FINAL_DIR / "cpt_val_general.jsonl")
    ap.add_argument("--allow-empty-general", action="store_true")
    args = ap.parse_args()

    rng = seeded_random(args.seed)

    maritime = load_jsonl(args.maritime_in)
    rng.shuffle(maritime)
    n_val_m = max(args.min_val, int(len(maritime) * args.val_fraction)) if maritime else 0
    val_m = maritime[:n_val_m]

    write_jsonl(args.out_maritime, val_m)

    general = []
    if args.general_in.exists():
        general = load_jsonl(args.general_in)

    if not general and not args.allow_empty_general:
        raise SystemExit(
            "General replay is empty/missing. Run build_general_replay.py with a general corpus or pass --allow-empty-general."
        )

    rng.shuffle(general)
    n_val_g = max(50, int(len(general) * args.val_fraction)) if general else 0
    val_g = general[:n_val_g]

    write_jsonl(args.out_general, val_g)

    print(f"Maritime val: {len(val_m)}")
    print(f"General  val: {len(val_g)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
