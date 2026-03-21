from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .paths import import_config
from .utils import now_iso


# --- Domain tag inference ----------------------------------------------------

def infer_domain_tag(filename: str) -> str:
    fn = filename.lower()

    # Priority matches (most specific first)
    if "reeds" in fn:
        return "ENGINES"
    if "isgott" in fn:
        return "SAFETY"
    if "marpol" in fn:
        return "MARPOL"
    if "stcw" in fn:
        return "STCW"

    nav_markers = [
        "navigation",
        "nautical",
        "colregs",
        "colreg",
        "radar",
        "arpa",
        "celestial",
        "chart",
        "pilotage",
    ]
    if any(m in fn for m in nav_markers):
        return "NAVIGATION"

    return "GENERAL"


SAFETY_CRITICAL_PHRASES = [
    "abandon ship",
    "enclosed space",
    "fire fighting",
    "man overboard",
    "life-saving",
    "emergency procedure",
]


def safety_critical_from_text(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in SAFETY_CRITICAL_PHRASES)


# --- Audit logging -----------------------------------------------------------

def append_audit(audit_log: Path, message: str) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_log, "a", encoding="utf-8") as f:
        f.write(f"[{now_iso()}] [extract_tier1_books] {message}\n")


def jsonl_section_word_stats(path: Path) -> tuple[int, int]:
    """Return (sections, word_count) by streaming the JSONL.

    This is used for resumable runs when outputs already exist.
    """
    sections = 0
    words = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            txt = obj.get("text", "")
            if isinstance(txt, str) and txt:
                sections += 1
                words += len(txt.split())
    return sections, words


# --- PDF extraction ----------------------------------------------------------


def short_line_ratio(text: str) -> float:
    lines = [ln.strip() for ln in text.splitlines()]
    non_empty = [ln for ln in lines if ln]
    if not non_empty:
        return 1.0
    short = sum(1 for ln in non_empty if len(ln) < 10)
    return short / max(len(non_empty), 1)


def _docling_convert_subprocess(pdf_path: Path, out_path: Path, timeout_seconds: int = 0) -> None:
    """Run docling conversion in a separate Python process.

    This makes timeouts reliable even if docling internally blocks.
    """

    code = r"""
import sys
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrAutoOptions, ThreadedPdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def _result_to_markdown(res) -> str:
    # Try common result shapes
    for attr in ["document", "doc", "output"]:
        if hasattr(res, attr):
            res = getattr(res, attr)
            break

    if hasattr(res, "export_to_markdown"):
        return res.export_to_markdown()
    if hasattr(res, "to_markdown"):
        return res.to_markdown()
    if hasattr(res, "text"):
        return str(res.text)
    return str(res)


def _convert(do_ocr: bool) -> str:
    if do_ocr:
        # Prefer RapidOCR when available because it does not rely on system-level
        # Tesseract binaries (which are often missing in offline environments).
        try:
            import rapidocr_onnxruntime  # noqa: F401

            from docling.datamodel.pipeline_options import RapidOcrOptions

            ocr_opts = RapidOcrOptions(lang=["eng"])
        except Exception:
            ocr_opts = OcrAutoOptions(lang=["eng"])
    else:
        ocr_opts = OcrAutoOptions(lang=[])

    # Docling v2 configures OCR via PDF pipeline options, not via convert() kwargs.
    pipe = ThreadedPdfPipelineOptions(
        do_ocr=do_ocr,
        # When OCR is disabled, still prefer the backend text extraction.
        force_backend_text=True,
        # Use an OCR options type that provides the required `.kind` discriminator.
        # Docling's OCR factory expects this; plain `OcrOptions` doesn't define it.
        ocr_options=ocr_opts,
    )
    pdf_opts = PdfFormatOption(pipeline_options=pipe)
    converter = DocumentConverter(format_options={InputFormat.PDF: pdf_opts})
    res = converter.convert(pdf)
    return _result_to_markdown(res)


pdf = sys.argv[1]
outp = Path(sys.argv[2])

try:
    md = _convert(do_ocr=True)
except Exception as e:
    # Some docling 2.80 installs have an internal mismatch where the OCR factory expects
    # `ocr_options.kind`, but OcrOptions doesn't define it. In that case, fall back to
    # non-OCR extraction so we still get usable text instead of crashing.
    msg = f"{type(e).__name__}: {e}"
    if "OcrOptions" in msg and "kind" in msg:
        md = _convert(do_ocr=False)
    else:
        raise

outp.write_text(md or "", encoding="utf-8", errors="replace")
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code, str(pdf_path), str(out_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=(timeout_seconds if timeout_seconds and timeout_seconds > 0 else None),
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"docling subprocess timed out after {timeout_seconds}s for {pdf_path.name}"
        ) from e

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        tail = (stderr or stdout)[-800:]
        raise RuntimeError(
            f"docling subprocess failed for {pdf_path.name} (exit={proc.returncode}): {tail}"
        )


def extract_pdf_markdown_pymupdf4llm(pdf_path: Path) -> str:
    # pymupdf4llm produces relatively clean markdown from PDFs
    try:
        from pymupdf4llm import to_markdown  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pymupdf4llm is not available. Install with pip install pymupdf4llm"
        ) from e

    # Some versions accept Path; normalize to str.
    md = to_markdown(str(pdf_path))
    # pymupdf4llm may return None for some malformed/scanned PDFs; treat as empty
    # so our quality gate can trigger the docling fallback.
    return md if isinstance(md, str) else ""


def extract_pdf_markdown_docling_ocr(pdf_path: Path, timeout_seconds: int = 0) -> str:
    """Extract markdown from a PDF using docling in a subprocess.

    We use a subprocess to make timeouts reliable and to avoid hangs inside
    docling's converter.
    """
    # Sanity-check availability early so we fail fast with a clear message.
    try:
        import docling  # noqa: F401
    except Exception as e:
        raise RuntimeError(
            "docling is not available. Install with pip install docling"
        ) from e

    with tempfile.TemporaryDirectory(prefix="tier1_docling_") as td:
        md_path = Path(td) / (pdf_path.stem + ".md")
        _docling_convert_subprocess(pdf_path, md_path, timeout_seconds=timeout_seconds)
        try:
            return md_path.read_text(encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return ""


def extract_pdf_text_rapidocr(pdf_path: Path, zoom: float = 1.5, max_pages: int | None = None) -> str:
    """Direct OCR fallback using RapidOCR + PyMuPDF.

    This is meant as a last resort when:
    - The PDF is image-only (pymupdf4llm returns empty), and
    - Docling OCR is unavailable/hangs in the current environment.
    """
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError("numpy is required for RapidOCR fallback") from e

    try:
        import fitz  # type: ignore
    except Exception as e:
        raise RuntimeError("PyMuPDF (fitz) is required for RapidOCR fallback") from e

    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "rapidocr-onnxruntime is not available. Install with pip install rapidocr-onnxruntime"
        ) from e

    doc = fitz.open(str(pdf_path))
    ocr = RapidOCR()

    parts: list[str] = []
    page_count = doc.page_count
    limit = min(page_count, max_pages) if max_pages is not None else page_count

    mat = fitz.Matrix(zoom, zoom)

    for page_i in range(limit):
        page = doc.load_page(page_i)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # pix.samples is row-major, with pix.n channels.
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # Disable the classifier stage for speed; rotation errors are acceptable
        # for this last-resort fallback.
        res, _elapse = ocr(img, use_cls=False)
        if not res:
            continue

        # Sort OCR lines roughly top-to-bottom, left-to-right.
        def _key(item: object) -> tuple[float, float]:
            try:
                box = item[0]  # type: ignore[index]
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                return (min(ys), min(xs))
            except Exception:
                return (0.0, 0.0)

        res_sorted = sorted(res, key=_key)
        lines = []
        for item in res_sorted:
            try:
                txt = item[1]
            except Exception:
                continue
            if isinstance(txt, str):
                t = txt.strip()
                if t:
                    lines.append(t)

        if lines:
            parts.append(f"\n\n# Page {page_i + 1}\n\n" + "\n".join(lines))

    return "\n".join(parts).strip()


def extract_epub_sections(epub_path: Path) -> list[tuple[str, str]]:
    """Return list of (title, text) sections in spine order."""
    try:
        from ebooklib import epub  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "ebooklib is not available. Install with pip install ebooklib"
        ) from e

    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "beautifulsoup4 is not available. Install with pip install beautifulsoup4"
        ) from e

    book = epub.read_epub(str(epub_path))

    # Build id -> item lookup
    id_to_item = {item.get_id(): item for item in book.get_items()}

    sections: list[tuple[str, str]] = []

    # spine entries are (idref, linear)
    spine_ids: list[str] = []
    for entry in book.spine:
        if isinstance(entry, tuple) and entry:
            spine_ids.append(entry[0])
        elif isinstance(entry, str):
            spine_ids.append(entry)

    # Fallback: if spine empty, use all document items
    if not spine_ids:
        spine_ids = [i.get_id() for i in book.get_items() if i.get_type() == 9]

    chapter_idx = 0
    for item_id in spine_ids:
        item = id_to_item.get(item_id)
        if item is None:
            continue
        if item.get_type() != 9:  # ebooklib.ITEM_DOCUMENT
            continue

        chapter_idx += 1
        raw = item.get_content()
        soup = BeautifulSoup(raw, "html.parser")

        title = None
        # Prefer explicit headings
        h1 = soup.find(["h1", "h2"])
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)
        if not title:
            ttag = soup.find("title")
            if ttag and ttag.get_text(strip=True):
                title = ttag.get_text(strip=True)
        if not title:
            title = f"Chapter {chapter_idx}"

        # Extract text with line breaks
        text = soup.get_text("\n")
        # Light normalization: collapse huge whitespace blocks
        text = "\n".join(ln.rstrip() for ln in text.splitlines())
        text = "\n".join(ln for ln in text.splitlines() if ln.strip() != "")

        sections.append((title, text))

    return sections


# --- DJVU conversion ---------------------------------------------------------


def convert_djvu_to_pdf(djvu_path: Path, out_pdf: Path) -> None:
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    # Prefer djvu2pdf if available.
    cmd = shutil.which("djvu2pdf")
    if cmd:
        proc = subprocess.run(
            [cmd, str(djvu_path), str(out_pdf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"djvu2pdf failed for {djvu_path.name}: {proc.stderr.strip() or proc.stdout.strip()}"
            )
        return

    # Fallback to djvulibre's ddjvu.
    ddjvu = shutil.which("ddjvu")
    if ddjvu:
        proc = subprocess.run(
            [ddjvu, "-format=pdf", str(djvu_path), str(out_pdf)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"ddjvu -format=pdf failed for {djvu_path.name}: {proc.stderr.strip() or proc.stdout.strip()}"
            )
        return

    raise RuntimeError(
        "Neither djvu2pdf nor ddjvu was found. Install djvulibre (system package) to convert DJVU -> PDF."
    )


# --- Output records ----------------------------------------------------------


@dataclass
class BookResult:
    path: Path
    output_jsonl: Optional[Path]
    sections: int
    word_count: int
    avg_section_words: float
    flagged_short: bool
    extractor: str
    notes: str = ""


def iter_files(data_dir: Path) -> list[Path]:
    exts = {".pdf", ".epub", ".djvu"}
    files: list[Path] = []
    for root, _, names in os.walk(data_dir):
        for n in names:
            p = Path(root) / n
            if p.suffix.lower() in exts:
                files.append(p)
    files.sort(key=lambda p: (p.suffix.lower(), p.name.lower()))
    return files


def write_book_jsonl(
    out_path: Path,
    book_stem: str,
    domain_tag: str,
    sections: Iterable[tuple[str, str]],
) -> BookResult:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sec_n = 0
    words_total = 0
    flagged = False

    with open(out_path, "w", encoding="utf-8") as f:
        for idx, (title, body) in enumerate(sections, start=1):
            sec_n += 1
            body_words = len(body.split())
            words_total += body_words

            # Preserve chapter titles as section headers
            text = f"# {title}\n\n{body}".strip()

            rec = {
                "text": text,
                "source_id": f"tier1/{book_stem}/chapter_{idx}",
                "domain_tag": domain_tag,
                "doc_type": "textbook",
                "quality_tier": "A",
                "safety_critical": safety_critical_from_text(text),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    avg = (words_total / sec_n) if sec_n else 0.0
    if avg < 100:
        flagged = True

    return BookResult(
        path=Path(""),
        output_jsonl=out_path,
        sections=sec_n,
        word_count=words_total,
        avg_section_words=avg,
        flagged_short=flagged,
        extractor="",
    )


def extract_book_to_jsonl(
    src_path: Path,
    out_dir: Path,
    audit_log: Path,
    quality_threshold_shortline_ratio: float = 0.20,
    skip_existing: bool = True,
    docling_timeout_seconds: int = 0,
) -> BookResult:
    domain_tag = infer_domain_tag(src_path.name)
    book_stem = src_path.stem
    out_path = out_dir / f"{book_stem}.jsonl"

    if skip_existing and out_path.exists() and out_path.stat().st_size > 0:
        append_audit(audit_log, f"SKIP book={src_path.name} reason=output_exists out={out_path}")
        # Compute stats from existing JSONL so spot-check report remains meaningful.
        try:
            sec_n, words_total = jsonl_section_word_stats(out_path)
        except Exception as e:
            return BookResult(
                path=src_path,
                output_jsonl=out_path,
                sections=0,
                word_count=0,
                avg_section_words=0.0,
                flagged_short=True,
                extractor="skipped",
                notes=f"skipped_existing_output;stats_error={type(e).__name__}: {e}",
            )

        avg = (words_total / sec_n) if sec_n else 0.0
        return BookResult(
            path=src_path,
            output_jsonl=out_path,
            sections=sec_n,
            word_count=words_total,
            avg_section_words=avg,
            flagged_short=(avg < 100),
            extractor="skipped",
            notes="skipped_existing_output",
        )

    append_audit(audit_log, f"START book={src_path.name} size_bytes={src_path.stat().st_size}")

    try:
        if src_path.suffix.lower() == ".epub":
            sections = extract_epub_sections(src_path)
            # Convert list[(title,text)] to iterator of sections
            result = write_book_jsonl(out_path, book_stem, domain_tag, sections)
            result.path = src_path
            result.extractor = "epub(ebooklib+bs4)"
            append_audit(
                audit_log,
                f"DONE book={src_path.name} extractor={result.extractor} sections={result.sections} words={result.word_count}",
            )
            return result

        if src_path.suffix.lower() == ".djvu":
            with tempfile.TemporaryDirectory(prefix="tier1_djvu_") as td:
                pdf_path = Path(td) / f"{book_stem}.pdf"
                convert_djvu_to_pdf(src_path, pdf_path)
                # Recurse into pdf pipeline
                res = extract_book_to_jsonl(
                    pdf_path,
                    out_dir,
                    audit_log,
                    quality_threshold_shortline_ratio=quality_threshold_shortline_ratio,
                    skip_existing=skip_existing,
                )
                res.path = src_path
                res.notes = (res.notes + ";" if res.notes else "") + "converted_from_djvu"
                return res

        # PDF pipeline
        extractor_used = "pdf(pymupdf4llm)"
        md_primary = extract_pdf_markdown_pymupdf4llm(src_path)
        ratio = short_line_ratio(md_primary)

        md = md_primary
        notes = f"short_line_ratio={ratio:.3f}"
        if ratio > quality_threshold_shortline_ratio:
            append_audit(
                audit_log,
                f"FALLBACK book={src_path.name} reason=short_line_ratio ratio={ratio:.3f} threshold={quality_threshold_shortline_ratio:.3f}",
            )

            # 1) Try Docling OCR in a subprocess.
            try:
                extractor_used = "pdf(docling+ocr)"
                md_docling = extract_pdf_markdown_docling_ocr(
                    src_path, timeout_seconds=docling_timeout_seconds
                )
                if md_docling.strip():
                    md = md_docling
                else:
                    notes += ";docling_empty_output"
            except Exception as e:
                # Keep the primary extraction if docling fails; we'll try a final OCR fallback below.
                extractor_used = "pdf(pymupdf4llm)"
                notes += f";docling_error={type(e).__name__}"
                append_audit(
                    audit_log,
                    f"DOCLING_ERROR book={src_path.name} err={type(e).__name__}: {e}",
                )

            ratio2 = short_line_ratio(md)
            notes += f";fallback_short_line_ratio={ratio2:.3f}"

            # 2) If we still have no usable text, do a last-resort OCR using RapidOCR directly.
            if not md.strip():
                try:
                    extractor_used = "pdf(rapidocr)"
                    md = extract_pdf_text_rapidocr(src_path)
                    notes += ";used_rapidocr"
                except Exception as e:
                    notes += f";rapidocr_error={type(e).__name__}"
                    append_audit(
                        audit_log,
                        f"RAPIDOCR_ERROR book={src_path.name} err={type(e).__name__}: {e}",
                    )

        # Split PDF markdown into coarse sections.
        # If markdown has headings, split on headings; else chunk by ~1500 words.
        sections: list[tuple[str, str]] = []
        lines = md.splitlines()

        current_title = None
        current_buf: list[str] = []
        for ln in lines:
            s = ln.lstrip()
            if s.startswith("#"):
                # Treat any markdown heading as a section boundary.
                if current_buf:
                    title = current_title or f"Section {len(sections) + 1}"
                    sections.append((title, "\n".join(current_buf).strip()))
                    current_buf = []
                current_title = s.lstrip("#").strip() or None
            else:
                current_buf.append(ln)

        if current_buf:
            title = current_title or f"Section {len(sections) + 1}"
            sections.append((title, "\n".join(current_buf).strip()))

        # Fallback splitting if only 1 tiny section
        if len(sections) <= 1:
            words = md.split()
            if words:
                sections = []
                target_words = 1500
                i = 0
                sec_idx = 0
                while i < len(words):
                    sec_idx += 1
                    chunk = " ".join(words[i : i + target_words])
                    sections.append((f"Section {sec_idx}", chunk))
                    i += target_words

        result = write_book_jsonl(out_path, book_stem, domain_tag, sections)
        result.path = src_path
        result.extractor = extractor_used
        result.notes = notes

        append_audit(
            audit_log,
            f"DONE book={src_path.name} extractor={result.extractor} sections={result.sections} words={result.word_count} {notes}",
        )
        return result

    except Exception as e:
        append_audit(audit_log, f"ERROR book={src_path.name} err={type(e).__name__}: {e}")
        return BookResult(
            path=src_path,
            output_jsonl=None,
            sections=0,
            word_count=0,
            avg_section_words=0.0,
            flagged_short=True,
            extractor="",
            notes=f"error={type(e).__name__}: {e}",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract Tier-1 maritime textbooks into JSONL sections.")
    ap.add_argument(
        "--data-dir",
        type=str,
        default="/home/mohanganesh/ship/ship/data",
        help="Directory containing Tier-1 book files (PDF/EPUB/DJVU).",
    )
    ap.add_argument(
        "--quality-threshold",
        type=float,
        default=0.20,
        help="Fallback to OCR if short-line ratio exceeds this threshold.",
    )
    ap.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Re-extract books even if their output JSONL already exists.",
    )
    ap.add_argument(
        "--docling-timeout-seconds",
        type=int,
        default=1800,
        help="Max seconds allowed for docling fallback per PDF before flagging as failed (0 disables timeout).",
    )
    args = ap.parse_args()

    config = import_config()

    data_dir = Path(args.data_dir)
    out_dir = Path(config.EXTRACTED_DIR) / "tier1_books"
    audit_log = Path(config.FINAL_DIR) / "pipeline_audit.log"

    files = iter_files(data_dir)

    append_audit(audit_log, f"SCAN data_dir={data_dir} found_files={len(files)}")

    print("Tier-1 book scan:")
    for p in files:
        try:
            sz = p.stat().st_size
        except FileNotFoundError:
            sz = 0
        print(f"- {p.name}\t{sz/1024/1024:.2f} MiB\t{p}")

    results: list[BookResult] = []
    for i, p in enumerate(files, start=1):
        print(f"\n[{i}/{len(files)}] Extracting {p.name} ...", flush=True)
        res = extract_book_to_jsonl(
            p,
            out_dir=out_dir,
            audit_log=audit_log,
            quality_threshold_shortline_ratio=float(args.quality_threshold),
            skip_existing=not bool(args.no_skip_existing),
            docling_timeout_seconds=int(args.docling_timeout_seconds),
        )
        # If it's a temp PDF produced from DJVU, its path won't point to original. Keep original in notes.
        results.append(res)

    # Spot-check report
    print("\nSpot-check report:")
    any_fail = False
    for r in results:
        if r.output_jsonl is None:
            any_fail = True
            print(f"[FAIL] {r.path.name}: {r.notes}")
            continue

        avg = (r.word_count / r.sections) if r.sections else 0.0
        flag = " **FLAG(avg<100)**" if avg < 100 else ""
        if avg < 100:
            any_fail = True
        note = f" ({r.notes})" if r.notes else ""
        print(
            f"[OK] {r.path.name}: sections={r.sections}, words={r.word_count}, avg_section_words={avg:.1f}, extractor={r.extractor}{flag}{note}"
        )

        append_audit(
            audit_log,
            f"REPORT book={r.path.name} sections={r.sections} words={r.word_count} avg_section_words={avg:.1f} extractor={r.extractor} flagged={avg < 100} {r.notes}",
        )

    append_audit(audit_log, f"FINISH total_books={len(results)} any_flagged={any_fail}")

    # Exit non-zero if any flagged/failed so this can be used as a gate.
    return 2 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
