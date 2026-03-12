from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .constants import DIFFICULTY_HINTS
from .paths import import_config
from .utils import now_iso, stable_id


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


_STEP_RE = re.compile(r"^\s*(?:step\s*\d+|\d+\.|\([0-9]+\)|[a-z]\)|\u2022|\-|\*)\s+", re.I)

# --- Difficulty hint signals (two-layer: metadata base + text overrides) ------

_DIGIT_RE = re.compile(r"\d")

_CALC_INTENT_RE = re.compile(
    r"\b("
    r"calculate|formula|gz curve|metacentric height|displacement of|fuel consumption rate|"
    r"specific fuel oil consumption|shaft power|stability criterion|boil-off rate|"
    r"is given by|expressed as"
    r")\b",
    re.I,
)

_NUMBERED_STEP_LINE_RE = re.compile(r"^\s*\d+[\.)]\s+", re.M)

_IMPERATIVE_START_RE = re.compile(
    r"(?:^|[\n\r]|[.!?]\s+)\s*"
    r"(ensure|verify|check|open|close|start|stop|isolate|disconnect|connect|install|remove|apply|"
    r"drain|bleed|tighten|adjust|replace|clean|lubricate)\b",
    re.I,
)

_REG_EXCEPTION_RE = re.compile(
    r"\b(except|unless|provided that|does not apply|notwithstanding|in lieu of|exemption|waiver|derogation|alternative|equivalent)\b",
    re.I,
)

_DIAGNOSTIC_SIGNAL_RE = re.compile(
    r"\b(probable cause|contributing factor|root cause|failure mode|symptom|troubleshoot|caused by|resulted in|led to|sequence of events)\b",
    re.I,
)


def _count_occurrences(pattern: re.Pattern[str], text: str) -> int:
    return len(pattern.findall(text or ""))


def _is_procedure_line(line: str) -> bool:
    return bool(_STEP_RE.match(line.strip()))


def _split_paragraphs(text: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return paras


def _headingish(para: str) -> bool:
    # short line with many uppercase letters
    if "\n" in para:
        return False
    s = para.strip()
    if len(s) < 6 or len(s) > 80:
        return False
    upper = sum(1 for ch in s if ch.isupper())
    letters = sum(1 for ch in s if ch.isalpha())
    return letters > 0 and (upper / letters) > 0.6


def _difficulty_hint(doc_type: str, source_type: str, text: str) -> str:
    """Two-layer difficulty hint assignment.

    Layer 1: assign base hint from doc_type + source_type.
    Layer 2: apply text-signal overrides (upgrade or downgrade).
    """

    dt = (doc_type or "unknown").strip().lower()
    st = (source_type or "").strip().lower()
    t = text or ""

    # --- Layer 1: source-based defaults ------------------------------------
    base = "factual_simple"

    # doc_type-driven base
    if dt in {"accident_investigation", "near_miss"}:
        base = "diagnostic_multistep"
    elif dt in {"regulation", "circular"}:
        base = "regulatory_exception"
    elif dt == "guidance":
        base = "procedural_sequential"
    elif dt == "textbook":
        base = "procedural_sequential"
    elif dt in {"encyclopedia", "academic_abstract"}:
        base = "factual_technical"

    # source_type-driven base (only if doc_type didn't already pick a stronger prior)
    # NOTE: we intentionally allow source_type to override factual_simple/factual_technical,
    # but not accident/reg/circular/guidance/textbook which are already high-signal.
    if base in {"factual_simple", "factual_technical"}:
        if any(x in st for x in ["ntsb", "bsu", "maib", "nsia"]):
            base = "diagnostic_multistep"
        elif any(x in st for x in ["imo", "mca", "uscg", "transport_canada"]):
            base = "regulatory_exception"
        elif "wartsila" in st:
            base = "factual_technical"
        elif "openalex" in st:
            base = "factual_technical"
        elif "wikipedia" in st:
            base = "factual_simple"
        elif "tier1_books" in st:
            base = "procedural_sequential"
        else:
            base = base  # keep

    # --- Layer 2: text overrides -------------------------------------------

    # Override to calculation if calc-intent phrase AND digit.
    if _CALC_INTENT_RE.search(t) and _DIGIT_RE.search(t):
        return "calculation"

    # Override to procedural_sequential if base is regulatory_exception or factual_simple
    # and we see strong procedural structure.
    if base in {"regulatory_exception", "factual_simple"}:
        numbered_lines = len(_NUMBERED_STEP_LINE_RE.findall(t))
        imperative_n = len(_IMPERATIVE_START_RE.findall(t))
        if numbered_lines >= 3 or imperative_n >= 3:
            return "procedural_sequential"

    # Override to diagnostic_multistep if base is factual_simple or factual_technical
    # and diagnostic signals appear >= 2 times.
    if base in {"factual_simple", "factual_technical"}:
        if _count_occurrences(_DIAGNOSTIC_SIGNAL_RE, t) >= 2:
            return "diagnostic_multistep"

    return base


def _groundable(text: str) -> bool:
    # Conservative: groundable if it stands alone and isn't mostly cross-refs.
    t = text.lower()
    if re.search(r"\b(see above|see below|as shown in figure|table \d+)\b", t):
        return False
    return True


def chunk_record(
    record: dict[str, Any],
    target_words: int,
    min_words: int,
    max_words: int,
) -> list[dict[str, Any]]:
    """Chunk into coherent spans.

    Rule: never split contiguous procedure blocks.
    """
    text = str(record.get("text") or "")
    doc_type = str(record.get("doc_type") or "unknown")

    paras = _split_paragraphs(text)
    if not paras:
        return []

    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0

    def flush() -> None:
        nonlocal buf, buf_words
        if not buf:
            return
        chunks.append("\n\n".join(buf).strip())
        buf = []
        buf_words = 0

    i = 0
    while i < len(paras):
        para = paras[i]
        p_words = len(para.split())

        # Keep heading with the next paragraph.
        if _headingish(para) and i + 1 < len(paras):
            next_para = paras[i + 1]
            para = para + "\n\n" + next_para
            p_words = len(para.split())
            i += 1

        # Detect procedure blocks: consecutive paragraphs that are mostly steps.
        lines = [ln for ln in para.split("\n") if ln.strip()]
        is_proc = sum(1 for ln in lines if _is_procedure_line(ln)) >= max(2, len(lines) // 2)
        if is_proc:
            # Flush buffer first, then place procedure as its own chunk
            flush()
            chunks.append(para)
            i += 1
            continue

        if buf_words + p_words <= target_words or not buf:
            buf.append(para)
            buf_words += p_words
        else:
            flush()
            buf.append(para)
            buf_words = p_words
        i += 1

    flush()

    # post-process size constraints: merge small neighbours
    normalized: list[str] = []
    for ch in chunks:
        w = len(ch.split())
        if normalized and w < min_words:
            normalized[-1] = normalized[-1].rstrip() + "\n\n" + ch
        else:
            normalized.append(ch)

    # split huge chunks (rare): hard split by sentences
    final: list[str] = []
    for ch in normalized:
        w = len(ch.split())
        if w <= max_words:
            final.append(ch)
            continue
        # sentence split
        sentences = re.split(r"(?<=[.!?])\s+", ch)
        b: list[str] = []
        bw = 0
        for s in sentences:
            sw = len(s.split())
            if bw + sw <= target_words or not b:
                b.append(s)
                bw += sw
            else:
                final.append(" ".join(b).strip())
                b = [s]
                bw = sw
        if b:
            final.append(" ".join(b).strip())

    out: list[dict[str, Any]] = []
    for idx, ch in enumerate(final):
        w = len(ch.split())
        if w < min_words:
            continue
        hint = _difficulty_hint(doc_type, str(record.get("source_type") or ""), ch)
        if hint not in DIFFICULTY_HINTS:
            hint = "factual_simple"

        chunk_id = stable_id(str(record.get("id")), str(idx))
        out.append(
            {
                "id": chunk_id,
                "parent_id": record.get("id"),
                "source_id": record.get("source_id"),
                "source_type": record.get("source_type"),
                "source_url": record.get("source_url"),
                "jurisdiction": record.get("jurisdiction"),
                "doc_type": doc_type,
                "quality_tier": record.get("quality_tier"),
                "year": record.get("year"),
                "domain_tags": record.get("domain_tags") or [],
                "difficulty_hint": hint,
                "groundable": _groundable(ch),
                "word_count": w,
                "text": ch,
                "created_at": now_iso(),
            }
        )

    return out


def main() -> int:
    cfg = import_config()
    ap = argparse.ArgumentParser(description="Chunk Stage-0 corpus into SFT-ready chunks.jsonl.")
    ap.add_argument("--in", dest="inp", type=Path, default=cfg.FINAL_DIR / "cpt_corpus_deduped.jsonl")
    ap.add_argument("--out", type=Path, default=cfg.FINAL_DIR / "chunks.jsonl")
    ap.add_argument("--target-words", type=int, default=cfg.SFT_CHUNK_WORDS)
    ap.add_argument("--min-words", type=int, default=80)
    ap.add_argument("--max-words", type=int, default=900)
    args = ap.parse_args()

    records = load_jsonl(args.inp)
    chunks: list[dict[str, Any]] = []
    for r in records:
        chunks.extend(
            chunk_record(
                r,
                target_words=args.target_words,
                min_words=args.min_words,
                max_words=args.max_words,
            )
        )

    write_jsonl(args.out, chunks)
    print(f"Input records: {len(records)}")
    print(f"Output chunks: {len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
