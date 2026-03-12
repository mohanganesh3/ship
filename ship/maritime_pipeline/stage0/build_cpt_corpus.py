from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .cleaning import source_aware_clean
from .constants import DOC_TYPES, DOMAIN_TAGS, JURISDICTIONS, QUALITY_TIERS
from .metadata_loaders import load_mca_metadata, load_ntsb_metadata
from .paths import import_config
from .utils import (
    estimate_tokens,
    infer_year_from_text,
    now_iso,
    sha256_text,
    should_shall_ratio,
    stable_id,
)


try:
    from langdetect import detect_langs  # type: ignore

    _LANGDETECT_AVAILABLE = True
except Exception:  # pragma: no cover
    detect_langs = None  # type: ignore
    _LANGDETECT_AVAILABLE = False


def _detect_english_confidence(text: str) -> float:
    if not _LANGDETECT_AVAILABLE:
        return 1.0
    try:
        langs = detect_langs(text[:5000])
        for l in langs:
            if l.lang == "en":
                return float(l.prob)
    except Exception:
        return 0.0
    return 0.0


def infer_source_type_from_path(extracted_path: Path, extracted_root: Path) -> str:
    try:
        rel = extracted_path.relative_to(extracted_root)
        parts = rel.parts
        if parts:
            return parts[0]
    except Exception:
        pass
    return "unknown"


def infer_doc_type(source_type: str, path: Path, text: str) -> str:
    st = source_type.lower()
    name = path.name.lower()

    if st in {"ntsb", "maib", "bsu", "dutch_safety", "transport_canada", "nsia", "hellenic"}:
        return "accident_investigation"
    if st in {"wikipedia", "wartsila"}:
        return "encyclopedia"
    if st in {"openalex"}:
        return "academic_abstract"
    if st in {"gcaptain", "maritime_executive", "safety4sea", "marine_insight"}:
        return "news_article"

    # lightweight heuristics based on filename and text
    if any(k in name for k in ["resolution", "msc", "me pc", "mepc", "solas", "marpol", "stcw", "colreg"]):
        return "regulation"

    if re.search(r"\b(circular|circ\.)\b", text[:2000], re.I):
        return "circular"

    if st in {"mca", "uscg_nvic", "iacs", "dnv", "abs", "lloyds_register", "ocimf", "bimco"}:
        return "guidance"

    return "unknown"


def infer_jurisdiction(source_type: str) -> str:
    st = source_type.lower()
    if st in {"imo"}:
        return "IMO_INTERNATIONAL"
    if st in {"mca", "maib"}:
        return "UK_MCA"
    if st in {"ntsb", "uscg_nvic"}:
        return "US_USCG"
    if st in {"emsa", "paris_mou"}:
        return "EU_EMSA"
    if st in {"transport_canada"}:
        return "CANADA_TC"
    if st in {"bsu"}:
        return "GERMANY_BSU"
    return "GENERAL"


def infer_quality_tier(source_type: str) -> str:
    st = source_type.lower()
    if st in {
        "imo",
        "mca",
        "maib",
        "ntsb",
        "emsa",
        "uscg_nvic",
        "paris_mou",
        "transport_canada",
        "bsu",
        "dutch_safety",
        "nsia",
    }:
        return "A"
    if st in {"gard", "ukpandi", "nepia", "standard_club", "skuld", "steamship"}:
        return "B"
    return "C"


def infer_domain_tags(text: str) -> list[str]:
    t = text.lower()
    tags: set[str] = set()
    if "solas" in t:
        tags.add("SOLAS")
    if "marpol" in t:
        tags.add("MARPOL")
    if "stcw" in t:
        tags.add("STCW")
    if "colreg" in t or "colregs" in t:
        tags.add("COLREG")

    # lightweight buckets
    if any(k in t for k in ["engine", "boiler", "shaft", "propeller", "lube oil"]):
        tags.add("ENGINES")
    if any(k in t for k in ["chart", "ecdis", "pilot", "voyage plan", "ais"]):
        tags.add("NAVIGATION")
    if any(k in t for k in ["lifeboat", "liferaft", "fire", "muster", "emergency"]):
        tags.add("SAFETY")
    if any(k in t for k in ["collision", "grounding", "capsize", "incident", "accident"]):
        tags.add("INCIDENT")
    if any(k in t for k in ["stability", "gm", "trim", "list", "freeboard"]):
        tags.add("STABILITY")
    if any(k in t for k in ["cargo", "container", "bulk", "tanker", "lpg", "lng"]):
        tags.add("CARGO")
    if any(k in t for k in ["pollution", "oily", "bilge", "annex", "sulphur", "sox", "nox"]):
        tags.add("POLLUTION")

    if not tags:
        tags.add("GENERAL")

    # validate against vocabulary
    tags = {tg for tg in tags if tg in DOMAIN_TAGS}
    return sorted(tags)


def _word_count(text: str) -> int:
    return len(text.split())


def _quality_score(text: str) -> float:
    """Heuristic quality score in [0, 1]. Conservative and explainable."""
    words = _word_count(text)
    if words <= 0:
        return 0.0

    # coverage / density
    long_lines = sum(1 for ln in text.split("\n") if len(ln.strip()) > 80)
    lines = max(1, len(text.split("\n")))
    line_density = min(1.0, long_lines / lines)

    # punctuation sanity
    punct = sum(text.count(ch) for ch in [".", ",", ";", ":"])
    punct_per_1k = punct / max(1.0, words) * 1000.0
    punct_score = 1.0 if 3.0 <= punct_per_1k <= 80.0 else 0.6 if punct_per_1k > 0 else 0.2

    # excessive symbols or broken OCR
    non_alnum = sum(1 for ch in text if not (ch.isalnum() or ch.isspace() or ch in ".,:;()[]-\n'\"/"))
    noise_frac = non_alnum / max(1, len(text))
    noise_score = 1.0 if noise_frac < 0.02 else 0.7 if noise_frac < 0.05 else 0.3

    # short docs are allowed for encyclopedia stubs; the filter handles MIN_WORDS.
    length_score = 1.0 if words >= 300 else 0.8 if words >= 150 else 0.5

    score = 0.35 * length_score + 0.25 * line_density + 0.25 * punct_score + 0.15 * noise_score
    return max(0.0, min(1.0, score))


def _may_be_superseded(year: Optional[int], doc_type: str, now_year: int) -> bool:
    if year is None:
        return False
    if doc_type not in {"regulation", "circular", "guidance"}:
        return False
    return (now_year - year) >= 10


def iter_extracted_txt(extracted_root: Path) -> Iterator[Path]:
    yield from sorted(extracted_root.glob("**/*.txt"))


def iter_extracted_jsonl(extracted_root: Path) -> Iterator[Path]:
    yield from sorted(extracted_root.glob("**/*.jsonl"))


def _load_jsonl_records(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _tier1_base_source_id(I am thinking that what we have done, I mean, do the data correction. All we have planned many things for training. The data thing was completed right now, or say, given the prompt to make it complete everything properly. I will give what it had done last. source_id: str, fallback: str) -> str:
    """Normalize per-chapter Tier-1 source_id into a per-book base id.

    Examples:
      tier1/SomeBook/chapter_12 -> tier1/SomeBook
      tier1/SomeBook/part_2 -> tier1/SomeBook
    """
    sid = (source_id or "").strip()
    if not sid:
        return fallback

    # Standard format from extract_tier1_books.py
    if "/chapter_" in sid:
        return sid.split("/chapter_")[0]

    # Safety: if we already have a nested id, strip the last segment.
    if sid.startswith("tier1/") and "/" in sid[len("tier1/") :]:
        return sid.rsplit("/", 1)[0]

    return sid


def _aggregate_tier1_jsonl_per_book(jp: Path, max_words: int) -> list[dict[str, Any]]:
    """Aggregate Tier-1 textbook JSONL (per-chapter lines) into per-book doc(s).

    This avoids dropping most chapters due to the global min_words filter.

    If the book would exceed max_words, split into multiple parts.
    """

    sections: list[str] = []
    seen_words = 0
    base_source_id: Optional[str] = None

    # Prefer a stable base id derived from the first record.
    fallback_sid = f"tier1/{jp.stem}"

    for jrec in _load_jsonl_records(jp):
        txt = (jrec.get("text") or jrec.get("content") or "").strip()
        if not txt:
            continue
        sections.append(str(txt))
        seen_words += len(str(txt).split())

        if base_source_id is None:
            sid = str(jrec.get("source_id") or "").strip()
            base_source_id = _tier1_base_source_id(sid, fallback=fallback_sid)

    if not sections:
        return []

    base_source_id = base_source_id or fallback_sid

    # If we're comfortably under max_words, emit a single document.
    if max_words <= 0 or seen_words <= max_words:
        return [
            {
                "title": jp.stem,
                "source_id": base_source_id,
                "doc_type": "textbook",
                "quality_tier": "A",
                "text": "\n\n".join(sections).strip(),
            }
        ]

    # Otherwise split into parts that each stay within max_words.
    parts: list[dict[str, Any]] = []
    buf: list[str] = []
    buf_words = 0

    def flush(part_idx: int) -> None:
        nonlocal buf, buf_words
        if not buf:
            return
        parts.append(
            {
                "title": f"{jp.stem} (part {part_idx})",
                "source_id": f"{base_source_id}/part_{part_idx}",
                "doc_type": "textbook",
                "quality_tier": "A",
                "text": "\n\n".join(buf).strip(),
            }
        )
        buf = []
        buf_words = 0

    part_idx = 1
    for sec in sections:
        w = len(sec.split())
        # Start a new part if adding this section would exceed max_words.
        if buf and (buf_words + w) > max_words:
            flush(part_idx)
            part_idx += 1
        buf.append(sec)
        buf_words += w

    flush(part_idx)
    return parts


def _source_id_from_metadata(
    source_type: str,
    extracted_path: Path,
    text: str,
    ntsb_by_report: dict[str, dict[str, Any]],
    mca_by_key: dict[str, dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Return (source_id, extra_fields)."""
    extra: dict[str, Any] = {}
    st = source_type.lower()

    if st == "ntsb":
        # Try to match by report number present in filename.
        stem = extracted_path.stem
        # Common format: MAR2101 or something containing it.
        m = re.search(r"\b(MAR\d{4})\b", stem.upper())
        report_number = m.group(1) if m else stem.upper()
        rec = ntsb_by_report.get(report_number)
        year = None
        if rec:
            extra["source_url"] = rec.get("pdf_url")
            extra["source_path"] = rec.get("local_path")
            try:
                year = int(rec.get("date")) if rec.get("date") else None
            except Exception:
                year = None
        if year is None:
            year = infer_year_from_text(text)
        extra["year"] = year
        return f"NTSB_{report_number}_{year or 'UNKNOWN'}", extra

    if st == "mca":
        # metadata keys are (notice_type/number[/pdfname])
        notice_type = None
        number = None
        # try parse file name: MGN_675 or MIN_123
        m = re.search(r"\b(MGN|MIN|MSN|MCA)\D{0,2}(\d{1,5})\b", extracted_path.stem.upper())
        if m:
            notice_type = m.group(1)
            number = m.group(2)
        # best-effort: look up using basename
        key_candidates = []
        if notice_type and number:
            key_candidates.append(f"{notice_type}/{number}/{extracted_path.with_suffix('.pdf').name}")
            key_candidates.append(f"{notice_type}/{number}")
        key_candidates.append(f"//{extracted_path.with_suffix('.pdf').name}")
        rec = None
        for k in key_candidates:
            if k in mca_by_key:
                rec = mca_by_key[k]
                break
        if rec:
            notice_type = notice_type or str(rec.get("notice_type") or "").upper().strip()
            number = number or str(rec.get("number") or "").strip()
            extra["source_url"] = rec.get("pdf_url")
            extra["source_path"] = rec.get("local_path")
        if notice_type and number:
            return f"UK_MCA_{notice_type}_{number}", extra
        return f"UK_MCA_{extracted_path.stem}", extra

    # fallback
    year = infer_year_from_text(text)
    if year:
        extra["year"] = year
    return f"{source_type.upper()}_{extracted_path.stem}", extra


def build_records(
    extracted_root: Path,
    raw_pdfs_root: Path,
    min_words: int,
    max_words: int,
    english_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (kept_records, filter_report_records)."""

    # Load metadata where available.
    ntsb_meta = load_ntsb_metadata(raw_pdfs_root / "ntsb" / "metadata.jsonl")
    mca_meta = load_mca_metadata(raw_pdfs_root / "mca" / "metadata.jsonl")

    kept: list[dict[str, Any]] = []
    report: list[dict[str, Any]] = []

    now_year = int(now_iso()[:4])

    def reject(reason: str, **fields: Any) -> None:
        fields.setdefault("reason", reason)
        fields.setdefault("timestamp", now_iso())
        report.append(fields)

    # 1) TXT documents from extracted PDFs/EPUB/DJVU
    for p in iter_extracted_txt(extracted_root):
        try:
            raw_text = p.read_text(encoding="utf-8", errors="replace").strip()
        except Exception as exc:
            reject("read_error", path=str(p), error=str(exc))
            continue

        if not raw_text:
            reject("empty", path=str(p))
            continue

        source_type = infer_source_type_from_path(p, extracted_root)
        doc_type = infer_doc_type(source_type, p, raw_text)
        jurisdiction = infer_jurisdiction(source_type)
        quality_tier = infer_quality_tier(source_type)

        cleaned, clean_flags = source_aware_clean(raw_text, source_type=source_type, doc_type=doc_type)
        wc = _word_count(cleaned)
        if wc < min_words:
            reject(
                "too_short",
                path=str(p),
                source_type=source_type,
                doc_type=doc_type,
                word_count=wc,
            )
            continue
        if wc > max_words:
            reject(
                "too_long",
                path=str(p),
                source_type=source_type,
                doc_type=doc_type,
                word_count=wc,
            )
            continue

        en_conf = _detect_english_confidence(cleaned)
        if en_conf < english_threshold:
            reject(
                "non_english",
                path=str(p),
                source_type=source_type,
                doc_type=doc_type,
                english_confidence=en_conf,
            )
            continue

        q = _quality_score(cleaned)
        if q < 0.15:
            reject(
                "garbled_low_quality",
                path=str(p),
                source_type=source_type,
                doc_type=doc_type,
                quality_score=q,
            )
            continue

        source_id, extra = _source_id_from_metadata(source_type, p, cleaned, ntsb_meta, mca_meta)
        year = extra.get("year")

        should_n, shall_n, ratio = should_shall_ratio(cleaned)

        rec_id = stable_id(source_id, sha256_text(cleaned)[:16])
        url = extra.get("source_url")

        kept.append(
            {
                "id": rec_id,
                "source_id": source_id,
                "source_type": source_type,
                "source_url": url,
                "jurisdiction": jurisdiction if jurisdiction in JURISDICTIONS else "GENERAL",
                "doc_type": doc_type if doc_type in DOC_TYPES else "unknown",
                "quality_tier": quality_tier if quality_tier in QUALITY_TIERS else "C",
                "year": year,
                "title": p.stem,
                "language": "en",
                "word_count": wc,
                "token_est": estimate_tokens(wc),
                "sha256": sha256_text(cleaned),
                "domain_tags": infer_domain_tags(cleaned),
                "text": cleaned,
                "created_at": now_iso(),
                "cleaning": clean_flags,
                "should_count": should_n,
                "shall_count": shall_n,
                "should_shall_ratio": round(ratio, 6) if ratio != float("inf") else None,
                "may_be_superseded": _may_be_superseded(year, doc_type, now_year),
            }
        )

    # 2) JSONL documents from web scrapes / academic APIs / synthetic procedures
    for jp in iter_extracted_jsonl(extracted_root):
        source_type = infer_source_type_from_path(jp, extracted_root)

        # Tier-1 textbooks are extracted as per-chapter JSONL lines; aggregate per-book.
        if source_type.lower() == "tier1_books":
            jsonl_records: Iterable[dict[str, Any]] = _aggregate_tier1_jsonl_per_book(jp, max_words=max_words)
        else:
            jsonl_records = _load_jsonl_records(jp)

        for jrec in jsonl_records:
            text = (jrec.get("text") or jrec.get("content") or "").strip()
            if not text:
                reject("jsonl_empty_text", path=str(jp), source_type=source_type)
                continue

            if source_type.lower() == "tier1_books":
                doc_type = "textbook"
                jurisdiction = "GENERAL"
                quality_tier = "A"
            else:
                doc_type = infer_doc_type(source_type, jp, text)
                jurisdiction = infer_jurisdiction(source_type)
                quality_tier = infer_quality_tier(source_type)

            cleaned, clean_flags = source_aware_clean(text, source_type=source_type, doc_type=doc_type)
            wc = _word_count(cleaned)
            if wc < min_words:
                reject(
                    "too_short",
                    path=str(jp),
                    source_type=source_type,
                    doc_type=doc_type,
                    word_count=wc,
                )
                continue
            if wc > max_words:
                reject(
                    "too_long",
                    path=str(jp),
                    source_type=source_type,
                    doc_type=doc_type,
                    word_count=wc,
                )
                continue
            en_conf = _detect_english_confidence(cleaned)
            if en_conf < english_threshold:
                reject(
                    "non_english",
                    path=str(jp),
                    source_type=source_type,
                    doc_type=doc_type,
                    english_confidence=en_conf,
                )
                continue
            q = _quality_score(cleaned)
            if q < 0.15:
                reject(
                    "garbled_low_quality",
                    path=str(jp),
                    source_type=source_type,
                    doc_type=doc_type,
                    quality_score=q,
                )
                continue

            # provenance from jsonl itself
            url = jrec.get("url") or jrec.get("source_url")
            title = jrec.get("title") or jrec.get("name") or jp.stem
            year = jrec.get("year")
            if not year:
                year = infer_year_from_text(cleaned)

            # Prefer explicit source_id when provided (Tier-1 textbooks embed one).
            if source_type.lower() == "tier1_books" and jrec.get("source_id"):
                source_id = str(jrec.get("source_id"))
            else:
                source_id = f"{source_type.upper()}_{stable_id(title, url or jp.name)}"

            should_n, shall_n, ratio = should_shall_ratio(cleaned)
            rec_id = stable_id(source_id, sha256_text(cleaned)[:16])
            kept.append(
                {
                    "id": rec_id,
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_url": url,
                    "jurisdiction": jurisdiction if jurisdiction in JURISDICTIONS else "GENERAL",
                    "doc_type": doc_type if doc_type in DOC_TYPES else "unknown",
                    "quality_tier": quality_tier if quality_tier in QUALITY_TIERS else "C",
                    "year": year,
                    "title": title,
                    "language": "en",
                    "word_count": wc,
                    "token_est": estimate_tokens(wc),
                    "sha256": sha256_text(cleaned),
                    "domain_tags": infer_domain_tags(cleaned),
                    "text": cleaned,
                    "created_at": now_iso(),
                    "cleaning": clean_flags,
                    "should_count": should_n,
                    "shall_count": shall_n,
                    "should_shall_ratio": round(ratio, 6) if ratio != float("inf") else None,
                    "may_be_superseded": _may_be_superseded(year if isinstance(year, int) else None, doc_type, now_year),
                }
            )

    return kept, report


def main() -> int:
    cfg = import_config()

    ap = argparse.ArgumentParser(description="Build Stage-0 CPT corpus with traceable metadata.")
    ap.add_argument("--extracted-root", type=Path, default=cfg.EXTRACTED_DIR)
    ap.add_argument("--raw-pdfs-root", type=Path, default=cfg.RAW_PDFS_DIR)
    ap.add_argument("--out", type=Path, default=cfg.FINAL_DIR / "cpt_corpus.jsonl")
    ap.add_argument("--filter-report", type=Path, default=cfg.FINAL_DIR / "filter_report.jsonl")
    ap.add_argument("--min-words", type=int, default=cfg.MIN_WORDS_PER_DOC)
    ap.add_argument("--max-words", type=int, default=cfg.MAX_WORDS_PER_DOC)
    ap.add_argument("--english-threshold", type=float, default=cfg.ENGLISH_CONFIDENCE_THRESHOLD)
    args = ap.parse_args()

    kept, filter_report = build_records(
        extracted_root=args.extracted_root,
        raw_pdfs_root=args.raw_pdfs_root,
        min_words=args.min_words,
        max_words=args.max_words,
        english_threshold=args.english_threshold,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(args.filter_report, "w", encoding="utf-8") as f:
        for rec in filter_report:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # minimal summary to stdout (audit log is written by runner)
    print(f"Wrote {len(kept)} records to {args.out}")
    print(f"Wrote {len(filter_report)} filter events to {args.filter_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
