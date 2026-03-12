from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_ntsb_metadata(metadata_jsonl: Path) -> dict[str, dict[str, Any]]:
    """Map report_number (e.g. MAR2101) -> metadata record."""
    out: dict[str, dict[str, Any]] = {}
    if not metadata_jsonl.exists():
        return out
    with open(metadata_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            rn = rec.get("report_number") or rec.get("title")
            if rn:
                out[str(rn).strip()] = rec
    return out


def load_mca_metadata(metadata_jsonl: Path) -> dict[str, dict[str, Any]]:
    """Map (notice_type, number, pdf basename) to metadata record."""
    out: dict[str, dict[str, Any]] = {}
    if not metadata_jsonl.exists():
        return out
    with open(metadata_jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            notice_type = str(rec.get("notice_type") or "").strip().upper()
            number = str(rec.get("number") or "").strip()
            local_path = str(rec.get("local_path") or "").strip()
            pdf_name = Path(local_path).name if local_path else ""
            key = f"{notice_type}/{number}/{pdf_name}" if pdf_name else f"{notice_type}/{number}"
            out[key] = rec
    return out
