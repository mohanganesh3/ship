"""
quality_filter.py — Text quality filter for extracted maritime documents.

Removes:
  - Navigation menus, cookie notices, page headers/footers
  - Documents shorter than MIN_WORDS words
  - Non-English content (langdetect confidence < threshold)
  - Gibberish (high symbol density, repetitive patterns)

Keeps:
  - Actual technical maritime content
  - Min 100 words, English, coherent prose

Input:  EXTRACTED_DIR/**/*.txt  (produced by pdf_extractor.py)
Output: FILTERED_DIR/**/*.txt   (same structure, lower quality docs dropped)
        FILTERED_DIR/filter_report.jsonl  (per-doc decisions with scores)

Usage:
    cd maritime_pipeline
    python filtering/quality_filter.py [--min-words 100] [--lang-threshold 0.85]
"""

import sys
import re
import json
import logging
import argparse
import hashlib
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    EXTRACTED_DIR, FILTERED_DIR, LOGS_DIR,
    MIN_WORDS_PER_DOC, MAX_WORDS_PER_DOC,
    ENGLISH_CONFIDENCE_THRESHOLD, MIN_QUALITY_SCORE,
)
from db import init_db

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):  # type: ignore[misc]
        return it

try:
    from langdetect import detect_langs, LangDetectException
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False

try:
    import ftfy
    _FTFY_AVAILABLE = True
except ImportError:
    _FTFY_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "quality_filter.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("filter")

# ── Boilerplate patterns (strip before analysis) ──────────────────────────────
_BOILERPLATE_PATTERNS = [
    # Cookie notices
    re.compile(r"(?i)we use cookies.*?(?:accept|agree|ok|consent)", re.DOTALL),
    re.compile(r"(?i)cookie policy.*?(?:accept|agree)", re.DOTALL),
    # Navigation
    re.compile(r"(?i)^(?:home|about|contact|sitemap|privacy policy|terms of use)\s*$",
               re.MULTILINE),
    # Page numbers
    re.compile(r"^\s*(?:page|p\.)\s*\d+\s*(?:of\s*\d+)?\s*$", re.MULTILINE | re.IGNORECASE),
    # Headers/footers (ALL CAPS short lines)
    re.compile(r"^[A-Z\s\W]{2,60}$\n?", re.MULTILINE),
    # Repetitive dashes/underscores (table formatting)
    re.compile(r"[-_=]{10,}"),
    # URLs in plain text
    re.compile(r"https?://\S+"),
    # Email addresses
    re.compile(r"\S+@\S+\.\S+"),
]

# ── Gibberish detectors ───────────────────────────────────────────────────────
_NON_ALPHA_RE  = re.compile(r"[^a-zA-Z\s]")
_REPEAT_WORD   = re.compile(r"\b(\w{3,})\s+\1\b")   # "the the" type repeats
_LONG_WORD_RE  = re.compile(r"\b\w{40,}\b")           # very long "words" = extraction artifact


def _strip_boilerplate(text: str) -> str:
    """Remove known boilerplate patterns from text."""
    for pat in _BOILERPLATE_PATTERNS:
        text = pat.sub(" ", text)
    # Collapse excessive whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fix_encoding(text: str) -> str:
    """Fix common encoding problems using ftfy if available."""
    if _FTFY_AVAILABLE:
        return ftfy.fix_text(text)
    # Minimal fallback: replace common bad sequences
    text = text.replace("\x00", "").replace("\ufffd", " ")
    return text


def _detect_language(text: str) -> tuple[str, float]:
    """Return (lang_code, confidence). Defaults to ('en', 0.0) on error."""
    if not _LANGDETECT_AVAILABLE:
        return "en", 1.0   # assume English if library not available

    # Use a sample for speed (first 2000 chars)
    sample = text[:2000].strip()
    if not sample:
        return "und", 0.0

    try:
        langs = detect_langs(sample)
        if langs:
            top = langs[0]
            return top.lang, round(top.prob, 4)
    except LangDetectException:
        pass
    return "und", 0.0


def _quality_score(text: str) -> float:
    """
    Heuristic quality score in [0, 1].
    Combines:
      - Alpha ratio (real words vs symbols)
      - Repetition penalty
      - Long-token penalty (OCR artifacts)
      - Sentence-like structure (ends with punctuation)
    """
    if not text:
        return 0.0

    words = text.split()
    n_words = len(words)
    if n_words == 0:
        return 0.0

    # 1. Alpha ratio
    non_alpha = len(_NON_ALPHA_RE.findall(text))
    alpha_ratio = 1.0 - min(1.0, non_alpha / max(len(text), 1))

    # 2. Repetition penalty
    repeats = len(_REPEAT_WORD.findall(text))
    repeat_score = max(0.0, 1.0 - (repeats / max(n_words, 1)) * 10)

    # 3. Long-token penalty (OCR artifacts produce very long tokens)
    long_tokens = len(_LONG_WORD_RE.findall(text))
    long_token_score = max(0.0, 1.0 - (long_tokens / max(n_words, 1)) * 5)

    # 4. Sentence structure
    sentences = re.split(r"[.!?]+", text)
    terminated = sum(1 for s in sentences if s.strip())
    sentence_score = min(1.0, terminated / max(n_words / 15, 1))

    score = (
        alpha_ratio * 0.4
        + repeat_score * 0.2
        + long_token_score * 0.2
        + sentence_score * 0.2
    )
    return round(score, 4)


def _should_keep(text: str, min_words: int, lang_threshold: float) -> tuple[bool, dict]:
    """
    Returns (keep, metadata_dict) with explanatory metadata.
    """
    meta: dict = {}

    # Step 1: fix encoding
    text = _fix_encoding(text)

    # Step 2: strip boilerplate
    text = _strip_boilerplate(text)

    # Step 3: word count
    words = text.split()
    n_words = len(words)
    meta["word_count"] = n_words

    if n_words < min_words:
        meta["reason"] = f"too_short ({n_words} < {min_words})"
        return False, meta

    if n_words > MAX_WORDS_PER_DOC:
        meta["reason"] = f"too_long ({n_words} > {MAX_WORDS_PER_DOC})"
        return False, meta

    # Step 4: language detection
    lang, confidence = _detect_language(text)
    meta["lang"] = lang
    meta["lang_confidence"] = confidence

    if lang != "en" and confidence >= lang_threshold:
        meta["reason"] = f"non_english (lang={lang}, conf={confidence})"
        return False, meta

    # Step 5: quality score
    score = _quality_score(text)
    meta["quality_score"] = score

    if score < MIN_QUALITY_SCORE:
        meta["reason"] = f"low_quality_score ({score:.3f} < {MIN_QUALITY_SCORE})"
        return False, meta

    meta["reason"] = "passed"
    meta["clean_text"] = text
    return True, meta


def _doc_id(path: Path) -> str:
    return hashlib.sha256(str(path).encode()).hexdigest()[:16]


def _output_path(src: Path) -> Path:
    try:
        rel = src.relative_to(EXTRACTED_DIR)
    except ValueError:
        rel = Path(src.name)
    out = FILTERED_DIR / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def run(min_words: int = MIN_WORDS_PER_DOC,
        lang_threshold: float = ENGLISH_CONFIDENCE_THRESHOLD) -> None:
    init_db()
    FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    report_path = FILTERED_DIR / "filter_report.jsonl"

    # Collect already-reported doc IDs for resumability
    done_ids: set[str] = set()
    if report_path.exists():
        with open(report_path) as f:
            for line in f:
                if line.strip():
                    try:
                        done_ids.add(json.loads(line)["doc_id"])
                    except Exception:
                        pass
        log.info("Resume: %d docs already filtered", len(done_ids))

    txt_files = list(EXTRACTED_DIR.glob("**/*.txt"))
    todo = [f for f in txt_files if _doc_id(f) not in done_ids]
    log.info("Files: %d total, %d to filter", len(txt_files), len(todo))

    kept = dropped = 0
    with open(report_path, "a", encoding="utf-8") as rpt_fh:
        for src_path in tqdm(todo, desc="Quality filtering", unit="doc"):
            doc_id = _doc_id(src_path)
            try:
                raw_text = src_path.read_text(encoding="utf-8", errors="replace")
                keep, meta = _should_keep(raw_text, min_words, lang_threshold)

                report_record = {
                    "doc_id": doc_id,
                    "source_file": str(src_path),
                    "status": "kept" if keep else "dropped",
                    **{k: v for k, v in meta.items() if k != "clean_text"},
                }
                rpt_fh.write(json.dumps(report_record) + "\n")
                rpt_fh.flush()

                if keep:
                    out_path = _output_path(src_path)
                    out_path.write_text(meta["clean_text"], encoding="utf-8")
                    kept += 1
                    log.debug("KEPT  %s (%d words)", src_path.name, meta["word_count"])
                else:
                    dropped += 1
                    log.debug("DROP  %s — %s", src_path.name, meta.get("reason"))

            except Exception as exc:
                log.error("Error processing %s: %s", src_path.name, exc)
                dropped += 1

    total = kept + dropped
    log.info(
        "Filtering complete. Kept=%d (%.1f%%)  Dropped=%d",
        kept, (kept / total * 100) if total else 0, dropped,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Maritime text quality filter")
    ap.add_argument("--min-words", type=int, default=MIN_WORDS_PER_DOC,
                    help="Minimum word count to keep a document")
    ap.add_argument("--lang-threshold", type=float, default=ENGLISH_CONFIDENCE_THRESHOLD,
                    help="langdetect confidence threshold for non-English rejection")
    args = ap.parse_args()
    run(min_words=args.min_words, lang_threshold=args.lang_threshold)
