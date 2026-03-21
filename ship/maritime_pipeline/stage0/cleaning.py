from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CleanResult:
    text: str
    removed_fraction: float


_PAGE_NUM_RE = re.compile(r"^\s*(?:page|p\.)\s*\d+\s*(?:of\s*\d+)?\s*$", re.I)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def strip_common_pdf_artifacts(text: str) -> CleanResult:
    """Conservative removal: page numbers + repeated separators + obvious web chrome."""
    original_len = max(len(text), 1)
    lines = text.split("\n")
    kept_lines = []
    removed = 0

    for ln in lines:
        s = ln.strip()
        if not s:
            kept_lines.append("")
            continue
        if _PAGE_NUM_RE.match(s):
            removed += len(ln) + 1
            continue
        if re.fullmatch(r"[-_=]{10,}", s):
            removed += len(ln) + 1
            continue
        # cookie / navigation fragments
        if re.search(r"(?i)we use cookies|cookie policy|accept cookies", s):
            removed += len(ln) + 1
            continue
        kept_lines.append(ln)

    cleaned = "\n".join(kept_lines)
    cleaned = normalize_whitespace(cleaned)
    return CleanResult(text=cleaned, removed_fraction=min(1.0, removed / original_len))


def source_aware_clean(text: str, source_type: str, doc_type: str) -> tuple[str, dict]:
    """Return cleaned text and a metadata dict describing flags.

    IMPORTANT: This avoids any transformations that could change modal verbs.
    """
    flags: dict = {}

    res = strip_common_pdf_artifacts(text)
    flags["removed_fraction"] = round(res.removed_fraction, 4)
    text = res.text

    # Source-aware trims (conservative)
    if source_type in {"gcaptain", "maritime_executive", "safety4sea"}:
        # remove common "Share" / social / newsletter blocks
        text = re.sub(r"(?is)\bsubscribe\b.*$", "", text).strip()

    if source_type == "wartsila" and doc_type == "encyclopedia":
        # remove A-Z navigation block seen in scraped entries
        text = re.sub(r"(?s)^(?:\s*[A-Z]\s*\n\n){10,}", "", text).strip()
        text = re.sub(r"(?is)\bYou might also enjoy\b.*$", "", text).strip()

    return normalize_whitespace(text), flags
