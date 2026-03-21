from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .paths import import_config
from .utils import now_iso


def _iter_input_jsonl(paths: list[Path]) -> Iterator[dict[str, Any]]:
    for p in paths:
        if not p.exists() or p.is_dir():
            continue
        if p.suffix.lower() != ".jsonl":
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _slugify_title(title: str, max_len: int = 120) -> str:
    s = (title or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "untitled"
    return s[:max_len]


def _compile_maritime_patterns() -> list[re.Pattern[str]]:
    # Use word boundaries to avoid false positives like "relationSHIP".
    phrases = [
        r"\bvessel\b",
        r"\bship\b",
        r"\bmaritime\b",
        r"\bsolas\b",
        r"\bmarpol\b",
        r"\bseafarer\b",
        r"\bnautical\b",
        r"\bport\s+authority\b",
        r"\bcargo\s+ship\b",
        r"\bballast\b",
    ]
    return [re.compile(p, re.I) for p in phrases]


def _maritime_keyword_hits(text: str, patterns: list[re.Pattern[str]]) -> int:
    t = text or ""
    hits = 0
    for pat in patterns:
        if pat.search(t):
            hits += 1
    return hits


def _clean_text(text: str) -> str:
    # Keep simple paragraphs but normalize excessive whitespace.
    t = (text or "").strip()
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs (not newlines)
    t = re.sub(r"[ \t\f\v]+", " ", t)
    # Collapse excessive blank lines
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    return t.strip()


def build_from_datasets(
    out_path: Path,
    min_total_chars: int,
    wiki_max_articles: int,
    wiki_target_chars: int,
    owt_target_chars: int,
    max_maritime_keywords: int,
    seed: int = 0,
) -> tuple[int, int]:
    """Write general_replay.jsonl and return (line_count, char_count)."""

    try:
        from datasets import load_dataset  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "datasets is required for --mode datasets. Install with: pip install datasets"
        ) from exc

    patterns = _compile_maritime_patterns()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_lines = 0
    n_chars = 0

    def write_record(f, rec: dict[str, Any]) -> None:
        nonlocal n_lines, n_chars
        line = json.dumps(rec, ensure_ascii=False)
        f.write(line + "\n")
        n_lines += 1
        n_chars += len(line) + 1

    # ---- Source 1: Wikipedia general articles ----
    # NOTE: With newer `datasets` versions, script-based datasets may be unsupported.
    # `wikimedia/wikipedia` is parquet-backed and supports streaming.
    wiki_written_chars = 0
    wiki_stream = load_dataset(
        "wikimedia/wikipedia",
        "20231101.en",
        split="train",
        streaming=True,
    )

    # ---- Source 2: OpenWebText-style web text ----
    # Prefer parquet-backed config.
    owt_written_chars = 0
    owt_stream = load_dataset(
        "Skylion007/openwebtext",
        "plain_text",
        split="train",
        streaming=True,
    )

    with open(out_path, "w", encoding="utf-8") as f:
        # Wikipedia pass (scan first N articles, write until wiki_target_chars reached)
        for idx, ex in enumerate(wiki_stream):
            if idx >= wiki_max_articles:
                break
            if wiki_written_chars >= wiki_target_chars:
                continue

            title = str(ex.get("title") or "")
            text = _clean_text(str(ex.get("text") or ""))
            if not text:
                continue

            if _maritime_keyword_hits(text, patterns) > max_maritime_keywords:
                continue

            source_id = f"wikipedia_general/{_slugify_title(title)}"
            rec = {
                "text": text,
                "source_id": source_id,
                "domain_tag": "GENERAL",
                "doc_type": "encyclopedia_general",
                "quality_tier": "B",
            }
            write_record(f, rec)
            wiki_written_chars += len(text)

        # OpenWebText pass (write until total meets min_total_chars and owt_target_chars)
        # We honor both: aim for owt_target_chars, but always ensure min_total_chars overall.
        owt_idx = 0
        for ex in owt_stream:
            need_total = n_chars < min_total_chars
            need_owt = owt_written_chars < owt_target_chars
            if not (need_total or need_owt):
                break

            text = _clean_text(str(ex.get("text") or ""))
            if not text:
                owt_idx += 1
                continue

            if _maritime_keyword_hits(text, patterns) > max_maritime_keywords:
                owt_idx += 1
                continue

            source_id = f"openwebtext/{owt_idx}"
            rec = {
                "text": text,
                "source_id": source_id,
                "domain_tag": "GENERAL",
                "doc_type": "web_text",
                "quality_tier": "B",
            }
            write_record(f, rec)
            owt_written_chars += len(text)
            owt_idx += 1

    return n_lines, n_chars


def verify_general_replay(
    path: Path,
    max_maritime_keywords: int,
) -> None:
    """Verify required post-build constraints without printing any text."""

    patterns = _compile_maritime_patterns()
    n_lines = 0
    n_chars = 0
    n_violations = 0
    worst_hits = 0
    worst_source_id: Optional[str] = None
    first3: list[tuple[str, int]] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line:
                continue
            n_chars += len(line)
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                # Ignore malformed lines (should not happen)
                continue

            n_lines += 1
            text = str(rec.get("text") or "")
            hits = _maritime_keyword_hits(text, patterns)
            if hits > worst_hits:
                worst_hits = hits
                worst_source_id = str(rec.get("source_id") or "")
            if hits > max_maritime_keywords:
                n_violations += 1

            if len(first3) < 3:
                source_id = str(rec.get("source_id") or "")
                # Simple word count (whitespace split) — no text printed.
                wc = len(text.split())
                first3.append((source_id, wc))

    print("Post-build verification:")
    print(f"- lines: {n_lines}")
    print(f"- chars: {n_chars}")
    print(f"- est_tokens(chars/4): {int(n_chars/4)}")
    if n_violations == 0:
        print(
            f"- maritime keyword constraint: OK (no record exceeds {max_maritime_keywords} keyword hits)"
        )
    else:
        print(
            f"- maritime keyword constraint: FAIL ({n_violations} records exceed {max_maritime_keywords} keyword hits; worst_hits={worst_hits}; worst_source_id={worst_source_id})"
        )

    print("- first_3_records:")
    for sid, wc in first3:
        print(f"  - source_id={sid} words={wc}")


def main() -> int:
    cfg = import_config()

    ap = argparse.ArgumentParser(
        description=(
            "Build general_replay.jsonl.\n"
            "Modes:\n"
            "- datasets: stream Wikipedia + OpenWebText and filter maritime-heavy text\n"
            "- local: read user-provided data/general/**/*.jsonl or data/general.jsonl"
        )
    )
    ap.add_argument("--mode", choices=["datasets", "local"], default="datasets")
    ap.add_argument("--general-dir", type=Path, default=cfg.DATA_DIR / "general")
    ap.add_argument("--general-jsonl", type=Path, default=cfg.DATA_DIR / "general.jsonl")
    ap.add_argument("--out", type=Path, default=cfg.FINAL_DIR / "general_replay.jsonl")
    ap.add_argument("--max-records", type=int, default=0, help="0 means no limit")
    ap.add_argument("--allow-empty", action="store_true")

    # datasets-mode controls
    ap.add_argument("--min-total-chars", type=int, default=40_000_000)
    ap.add_argument("--wiki-max-articles", type=int, default=50_000)
    ap.add_argument("--wiki-target-chars", type=int, default=20_000_000)
    ap.add_argument("--owt-target-chars", type=int, default=20_000_000)
    ap.add_argument("--max-maritime-keywords", type=int, default=3)
    args = ap.parse_args()

    if args.mode == "datasets":
        n_lines, n_chars = build_from_datasets(
            out_path=args.out,
            min_total_chars=args.min_total_chars,
            wiki_max_articles=args.wiki_max_articles,
            wiki_target_chars=args.wiki_target_chars,
            owt_target_chars=args.owt_target_chars,
            max_maritime_keywords=args.max_maritime_keywords,
        )
        print(f"Wrote {n_lines} records to {args.out}")
        print(f"Total characters (file, incl newlines): {n_chars}")
        print(f"Estimated tokens (chars/4): {int(n_chars/4)}")
        verify_general_replay(args.out, max_maritime_keywords=args.max_maritime_keywords)
        return 0

    # local mode (legacy)
    input_paths: list[Path] = []
    if args.general_dir.exists() and args.general_dir.is_dir():
        input_paths.extend(sorted(args.general_dir.glob("**/*.jsonl")))
    if args.general_jsonl.exists():
        input_paths.append(args.general_jsonl)

    out_records: list[dict[str, Any]] = []
    for rec in _iter_input_jsonl(input_paths):
        text = (rec.get("text") or rec.get("content") or "").strip()
        if not text:
            continue
        out_records.append(
            {
                "text": text,
                "source_id": rec.get("source_id") or "GENERAL_CORPUS",
                "domain_tag": "GENERAL",
                "doc_type": rec.get("doc_type") or "general",
                "quality_tier": rec.get("quality_tier") or "B",
            }
        )
        if args.max_records and len(out_records) >= args.max_records:
            break

    if not out_records and not args.allow_empty:
        raise SystemExit(
            "No general corpus inputs found. Provide data/general/**/*.jsonl or data/general.jsonl, "
            "or rerun with --allow-empty for a placeholder."
        )

    write_jsonl(args.out, out_records)
    print(f"Wrote {len(out_records)} records to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
