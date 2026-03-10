"""
pdf_extractor.py — Batch PDF & EPUB text extraction pipeline.

Supports:
  - Digital PDFs via PyMuPDF (fast, no GPU)
  - Scanned PDFs via Marker (uses OCR, optional GPU)
  - EPUB files via ebooklib + html2text
  - Plain .txt pass-through

Features:
  - Resume: skips already-extracted files (tracked in SQLite)
  - tqdm progress bar
  - Parallel workers (configurable)
  - Output: one .txt per source file, preserving subdirectory structure

Usage:
    cd maritime_pipeline
    python extraction/pdf_extractor.py [--workers 4] [--use-marker]
"""

import sys
import os
import re
import logging
import argparse
import hashlib
import concurrent.futures
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    RAW_PDFS_DIR, EXTRACTED_DIR, LOGS_DIR,
    MARKER_WORKERS, MARKER_GPU, PYMUPDF_FALLBACK,
)
from db import init_db, is_extracted, mark_extraction_done, mark_extraction_failed

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):  # type: ignore[misc]
        return it

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pdf_extractor.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("extractor")


# ── Backend: PyMuPDF ──────────────────────────────────────────────────────────

def _extract_with_pymupdf(pdf_path: Path) -> str:
    """Extract text from a digital PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(str(pdf_path))
    pages: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            pages.append(text)
    doc.close()
    return "\n\n".join(pages)


# ── Backend: Marker ───────────────────────────────────────────────────────────

def _extract_with_marker(pdf_path: Path) -> str:
    """
    Extract text using the Marker library (OCR-capable).
    Falls back to PyMuPDF on failure if PYMUPDF_FALLBACK is True.
    """
    try:
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
    except ImportError:
        if PYMUPDF_FALLBACK:
            log.warning("Marker not installed, falling back to PyMuPDF for %s", pdf_path.name)
            return _extract_with_pymupdf(pdf_path)
        raise RuntimeError("Marker not installed. Run: pip install marker-pdf")

    models = load_all_models()
    # convert_single_pdf returns (text, images, metadata)
    full_text, _, _ = convert_single_pdf(
        str(pdf_path),
        models,
        max_pages=None,
        langs=["English"],
        batch_multiplier=2,
    )
    if not full_text and PYMUPDF_FALLBACK:
        log.warning("Marker returned empty — falling back to PyMuPDF for %s", pdf_path.name)
        return _extract_with_pymupdf(pdf_path)
    return full_text or ""


# ── Backend: EPUB ─────────────────────────────────────────────────────────────

def _extract_epub(epub_path: Path) -> str:
    """Extract plain text from an EPUB file."""
    try:
        import ebooklib
        from ebooklib import epub
        import html2text
    except ImportError:
        raise RuntimeError(
            "ebooklib/html2text not installed. Run: pip install ebooklib html2text"
        )

    book = epub.read_epub(str(epub_path))
    h2t = html2text.HTML2Text()
    h2t.ignore_links = True
    h2t.ignore_images = True
    h2t.ignore_emphasis = False
    h2t.body_width = 0  # no line-wrapping

    parts: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html_content = item.get_content().decode("utf-8", errors="replace")
        text = h2t.handle(html_content)
        cleaned = re.sub(r"\n{3,}", "\n\n", text).strip()
        if cleaned:
            parts.append(cleaned)

    return "\n\n".join(parts)


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _extract_file(src_path: Path, use_marker: bool = False) -> str:
    """Route to the appropriate extractor based on file extension."""
    suffix = src_path.suffix.lower()
    if suffix == ".epub":
        return _extract_epub(src_path)
    elif suffix == ".txt":
        return src_path.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".pdf":
        if use_marker:
            return _extract_with_marker(src_path)
        # Heuristic: try PyMuPDF first; if word count is very low, maybe scanned
        text = _extract_with_pymupdf(src_path)
        word_count = len(text.split())
        # Fewer than 50 words per MB → likely scanned, try Marker if available
        size_mb = src_path.stat().st_size / 1_048_576
        if word_count < max(50, 50 * size_mb) and PYMUPDF_FALLBACK:
            log.info("Low word count (%d) for %s — trying Marker …", word_count, src_path.name)
            try:
                marker_text = _extract_with_marker(src_path)
                if len(marker_text.split()) > word_count:
                    return marker_text
            except Exception as exc:
                log.warning("Marker failed for %s: %s", src_path.name, exc)
        return text
    else:
        log.warning("Unsupported file type: %s", src_path.suffix)
        return ""


def _output_path(src_path: Path) -> Path:
    """
    Mirror the source directory structure under EXTRACTED_DIR.
    /data/raw_pdfs/maib/report.pdf → /data/extracted_text/maib/report.txt
    """
    try:
        rel = src_path.relative_to(RAW_PDFS_DIR)
    except ValueError:
        rel = Path(src_path.name)
    out = EXTRACTED_DIR / rel.with_suffix(".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def _process_one(args: tuple[Path, bool]) -> dict:
    src_path, use_marker = args
    out_path = _output_path(src_path)
    result = {"src": str(src_path), "out": str(out_path), "ok": False, "words": 0}

    if is_extracted(str(src_path)):
        result["skipped"] = True
        return result

    try:
        text = _extract_file(src_path, use_marker=use_marker)
        if not text:
            log.warning("Empty extraction: %s", src_path.name)
            mark_extraction_failed(str(src_path))
            return result

        # Light post-processing
        text = re.sub(r"[ \t]+", " ", text)         # collapse spaces
        text = re.sub(r"\n{4,}", "\n\n\n", text)    # max 3 blank lines
        text = text.strip()

        out_path.write_text(text, encoding="utf-8")
        word_count = len(text.split())
        mark_extraction_done(str(src_path), str(out_path), word_count)
        result.update({"ok": True, "words": word_count})
        log.info("✓ %s → %d words", src_path.name, word_count)
    except Exception as exc:
        log.error("✗ %s: %s", src_path.name, exc)
        mark_extraction_failed(str(src_path))

    return result


def run(workers: int = MARKER_WORKERS, use_marker: bool = False,
        source_dir: Path = None) -> None:
    init_db()
    search_root = source_dir or RAW_PDFS_DIR
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all extractable files
    patterns = ["**/*.pdf", "**/*.epub", "**/*.txt"]
    files: list[Path] = []
    for pat in patterns:
        files.extend(search_root.glob(pat))

    # Filter already-done
    todo = [f for f in files if not is_extracted(str(f))]
    done_count = len(files) - len(todo)
    log.info("Files: %d total, %d already extracted, %d to process",
             len(files), done_count, len(todo))

    if not todo:
        log.info("Nothing to do.")
        return

    tasks = [(f, use_marker) for f in todo]
    ok = fail = 0

    if workers > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_process_one, t): t[0] for t in tasks}
            for fut in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(tasks),
                desc="Extracting text",
                unit="file",
            ):
                res = fut.result()
                if res.get("ok"):
                    ok += 1
                elif not res.get("skipped"):
                    fail += 1
    else:
        for task in tqdm(tasks, desc="Extracting text", unit="file"):
            res = _process_one(task)
            if res.get("ok"):
                ok += 1
            elif not res.get("skipped"):
                fail += 1

    log.info("Extraction complete. OK=%d  Failed=%d  Pre-existing=%d",
             ok, fail, done_count)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Batch PDF/EPUB text extractor")
    ap.add_argument("--workers", type=int, default=MARKER_WORKERS,
                    help="Parallel worker processes (default from config)")
    ap.add_argument("--use-marker", action="store_true",
                    help="Force Marker (OCR-capable) for all PDFs")
    ap.add_argument("--source-dir", type=Path, default=None,
                    help="Override source directory (default: data/raw_pdfs)")
    args = ap.parse_args()
    run(workers=args.workers, use_marker=args.use_marker, source_dir=args.source_dir)
