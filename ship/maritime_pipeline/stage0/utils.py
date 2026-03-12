from __future__ import annotations

import hashlib
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .constants import MARITIME_KEYWORDS, SAFETY_CRITICAL_TRIGGERS


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def stable_id(*parts: str, n: int = 16) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8", errors="replace")).hexdigest()
    return h[:n]


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")


def infer_year_from_text(text: str) -> Optional[int]:
    # prefer explicit patterns like "Adopted on" / "(Adopted on 14 March 2025)"
    for pat in [
        re.compile(r"\bAdopted on\b[^\n]{0,60}?(19\d{2}|20\d{2})"),
        re.compile(r"\bPublished\b[^\n]{0,60}?(19\d{2}|20\d{2})"),
        re.compile(r"\bDate\b\s*[:\-]\s*(19\d{2}|20\d{2})"),
    ]:
        m = pat.search(text)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

    m2 = _YEAR_RE.search(text[:2000])
    if m2:
        try:
            return int(m2.group(1))
        except Exception:
            return None
    return None


def estimate_tokens(word_count: int, words_per_token: float = 0.75) -> int:
    # token ~= word / words_per_token
    return int(word_count / max(words_per_token, 1e-6))


def contains_maritime_keywords(text: str, threshold: int = 5) -> bool:
    t = text.lower()
    hits = sum(1 for kw in MARITIME_KEYWORDS if kw in t)
    return hits >= threshold


def is_safety_critical(text: str) -> bool:
    t = text.lower()
    return any(trig in t for trig in SAFETY_CRITICAL_TRIGGERS)


def should_shall_ratio(text: str) -> tuple[int, int, float]:
    t = text.lower()
    should = len(re.findall(r"\bshould\b", t))
    shall = len(re.findall(r"\bshall\b", t))
    ratio = (should / shall) if shall else float("inf") if should else 0.0
    return should, shall, ratio


def seeded_random(seed: int) -> random.Random:
    r = random.Random(seed)
    return r
