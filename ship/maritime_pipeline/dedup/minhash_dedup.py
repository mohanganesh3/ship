"""
minhash_dedup.py — Near-duplicate text removal using MinHashLSH.

Algorithm:
  1. Optional exact-SHA256 pass (extremely fast, catches identical docs)
  2. Sliding-window chunking: each document → overlapping 512-word shingles
  3. MinHash with 128 hash functions per shingle
  4. LSH with Jaccard threshold 0.80 groups near-duplicates into clusters
  5. Keeps exactly ONE representative per cluster (the longest doc)
  6. Outputs deduplicated JSONL with cluster annotations

Input:  FILTERED_DIR/**/*.txt          (from quality_filter.py)
        or any JSONL with {"text": ...} records
Output: DEDUPED_DIR/deduplicated.jsonl  (one record per kept document)
        DEDUPED_DIR/dedup_report.jsonl  (cluster assignments)

Usage:
    cd maritime_pipeline
    python dedup/minhash_dedup.py [--threshold 0.80] [--num-perm 128]
"""

import sys
import re
import json
import logging
import argparse
import hashlib
from pathlib import Path
from typing import Any, Generator

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    FILTERED_DIR, DEDUPED_DIR, LOGS_DIR,
    MINHASH_NUM_PERM, MINHASH_THRESHOLD, EXACT_HASH_FIRST,
)
from db import init_db

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):  # type: ignore[misc]
        return it

try:
    from datasketch import MinHash, MinHashLSH
    _DATASKETCH_AVAILABLE = True
except ImportError:
    _DATASKETCH_AVAILABLE = False
    MinHash = None  # type: ignore[assignment,misc]
    MinHashLSH = None  # type: ignore[assignment,misc]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "minhash_dedup.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("dedup")

CHUNK_WORDS   = 512    # words per chunk/shingle
CHUNK_OVERLAP = 64     # overlap between chunks


# ── Text utilities ────────────────────────────────────────────────────────────

def _tokenise(text: str) -> list[str]:
    """Lowercase word tokens, strip punctuation."""
    return re.findall(r"\b[a-z]{2,}\b", text.lower())


def _ngrams(tokens: list[str], n: int = 5) -> Generator[str, None, None]:
    """Yield n-gram strings from token list."""
    for i in range(len(tokens) - n + 1):
        yield " ".join(tokens[i : i + n])


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _windows(tokens: list[str], size: int, overlap: int) -> Generator[list[str], None, None]:
    """Sliding window over token list."""
    step = max(1, size - overlap)
    for start in range(0, max(1, len(tokens) - size + 1), step):
        yield tokens[start : start + size]


# ── Pure-Python MinHash (fallback when datasketch not installed) ──────────────

class _SimpleMinhash:
    """Minimal MinHash implementation using universal hashing. 128 permutations."""

    _P = (1 << 61) - 1  # Mersenne prime

    def __init__(self, num_perm: int = 128, seed: int = 1):
        import random
        rng = random.Random(seed)
        self.num_perm = num_perm
        # (a, b) pairs for ax+b mod p
        self._a = [rng.randint(1, self._P - 1) for _ in range(num_perm)]
        self._b = [rng.randint(0, self._P - 1) for _ in range(num_perm)]
        self.hashvalues = [self._P] * num_perm

    def update(self, text_shingle: str) -> None:
        h = int(hashlib.md5(text_shingle.encode()).hexdigest(), 16) & 0xFFFF_FFFF_FFFF_FFFF
        for i in range(self.num_perm):
            v = (self._a[i] * h + self._b[i]) % self._P
            if v < self.hashvalues[i]:
                self.hashvalues[i] = v

    def jaccard(self, other: "_SimpleMinhash") -> float:
        return sum(a == b for a, b in zip(self.hashvalues, other.hashvalues)) / self.num_perm


# ── Document loading ──────────────────────────────────────────────────────────

def _load_txt_documents(source_dir: Path) -> list[dict]:
    """Load all .txt files from filtered dir as document dicts."""
    docs: list[dict] = []
    for p in sorted(source_dir.glob("**/*.txt")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                docs.append({
                    "id": _sha256(str(p))[:16],
                    "source_file": str(p),
                    "text": text,
                    "word_count": len(text.split()),
                })
        except Exception as exc:
            log.warning("Could not read %s: %s", p, exc)
    return docs


def _load_jsonl_documents(jsonl_path: Path) -> list[dict]:
    """Load documents from a JSONL file (must have 'text' field)."""
    docs: list[dict] = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
                text = rec.get("text", "")
                if text:
                    rec.setdefault("id", _sha256(text)[:16])
                    rec.setdefault("word_count", len(text.split()))
                    docs.append(rec)
            except json.JSONDecodeError:
                pass
    return docs


# ── Exact dedup pass ──────────────────────────────────────────────────────────

def _exact_dedup(docs: list[dict]) -> tuple[list[dict], int]:
    """Remove exact duplicates by SHA-256 of full text. Returns (unique_docs, n_removed)."""
    seen: dict[str, str] = {}  # hash → doc id
    unique: list[dict] = []
    removed = 0
    for doc in docs:
        h = _sha256(doc["text"])
        if h in seen:
            removed += 1
            log.debug("Exact dup: %s == %s", doc["id"], seen[h])
        else:
            seen[h] = doc["id"]
            unique.append(doc)
    return unique, removed


# ── MinHash dedup ─────────────────────────────────────────────────────────────

def _build_minhash_datasketch(text: str, num_perm: int) -> Any:
    """Build a datasketch MinHash for the given text."""
    m = MinHash(num_perm=num_perm)
    tokens = _tokenise(text)
    for ng in _ngrams(tokens, n=5):
        m.update(ng.encode("utf-8"))
    return m


def _build_minhash_simple(text: str, num_perm: int) -> _SimpleMinhash:
    m = _SimpleMinhash(num_perm=num_perm)
    tokens = _tokenise(text)
    for ng in _ngrams(tokens, n=5):
        m.update(ng)
    return m


def _minhash_dedup_datasketch(
    docs: list[dict], threshold: float, num_perm: int
) -> tuple[list[dict], dict[str, str]]:
    """
    Use datasketch LSH for O(n) near-duplicate detection.  # noqa: ANN
    Returns (kept_docs, cluster_map {doc_id → representative_id}).
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    signatures: dict[str, Any] = {}

    log.info("Building MinHash signatures for %d documents …", len(docs))
    for doc in tqdm(docs, desc="Building MinHash", unit="doc"):
        sig = _build_minhash_datasketch(doc["text"], num_perm)
        signatures[doc["id"]] = sig

    log.info("Building LSH index …")
    cluster_map: dict[str, str] = {}   # doc_id → cluster representative id
    kept: list[dict] = []

    for doc in tqdm(docs, desc="LSH dedup", unit="doc"):
        sig = signatures[doc["id"]]
        neighbours = lsh.query(sig)
        if neighbours:
            # Already in index — find existing representative
            rep_id = neighbours[0]
            # Keep the longer document as representative
            rep_doc = next((d for d in kept if d["id"] == rep_id), None)
            if rep_doc and doc["word_count"] > rep_doc["word_count"]:
                # Swap representative
                lsh.remove(rep_id)
                lsh.insert(doc["id"], sig)
                cluster_map[rep_id] = doc["id"]
                kept.remove(rep_doc)
                kept.append(doc)
                rep_id = doc["id"]
            cluster_map[doc["id"]] = rep_id
        else:
            lsh.insert(doc["id"], sig)
            cluster_map[doc["id"]] = doc["id"]
            kept.append(doc)

    return kept, cluster_map


def _minhash_dedup_simple(
    docs: list[dict], threshold: float, num_perm: int
) -> tuple[list[dict], dict[str, str]]:
    """
    O(n²) brute-force MinHash dedup (used when datasketch not available).
    Only practical for up to ~5,000 docs.
    """
    log.warning("datasketch not available — using O(n²) brute-force dedup. "
                "Install: pip install datasketch")
    signatures = {}
    log.info("Building signatures for %d docs …", len(docs))
    for doc in tqdm(docs, desc="Building MinHash", unit="doc"):
        signatures[doc["id"]] = _build_minhash_simple(doc["text"], num_perm)

    cluster_map: dict[str, str] = {}
    for doc in docs:
        cluster_map[doc["id"]] = doc["id"]   # everyone is their own rep initially

    for i, doc_a in enumerate(tqdm(docs, desc="Comparing", unit="doc")):
        if cluster_map[doc_a["id"]] != doc_a["id"]:
            continue   # already absorbed into a cluster
        for doc_b in docs[i + 1 :]:
            if cluster_map[doc_b["id"]] != doc_b["id"]:
                continue
            j = signatures[doc_a["id"]].jaccard(signatures[doc_b["id"]])
            if j >= threshold:
                cluster_map[doc_b["id"]] = doc_a["id"]

    kept = [d for d in docs if cluster_map[d["id"]] == d["id"]]
    return kept, cluster_map


# ── Main ──────────────────────────────────────────────────────────────────────

def run(
    threshold: float = MINHASH_THRESHOLD,
    num_perm: int = MINHASH_NUM_PERM,
    source_dir: Path = None,
    source_jsonl: Path = None,
) -> None:
    init_db()
    DEDUPED_DIR.mkdir(parents=True, exist_ok=True)

    # Load documents
    if source_jsonl and source_jsonl.exists():
        log.info("Loading documents from JSONL: %s", source_jsonl)
        docs = _load_jsonl_documents(source_jsonl)
    else:
        src = source_dir or FILTERED_DIR
        log.info("Loading .txt documents from: %s", src)
        docs = _load_txt_documents(src)

    log.info("Loaded %d documents", len(docs))
    if not docs:
        log.warning("No documents found. Exiting.")
        return

    # Exact dedup first
    n_before = len(docs)
    if EXACT_HASH_FIRST:
        docs, n_exact = _exact_dedup(docs)
        log.info("Exact dedup: removed %d exact duplicates (%d remain)", n_exact, len(docs))

    # MinHash dedup
    if _DATASKETCH_AVAILABLE:
        kept, cluster_map = _minhash_dedup_datasketch(docs, threshold, num_perm)
    else:
        kept, cluster_map = _minhash_dedup_simple(docs, threshold, num_perm)

    n_removed = len(docs) - len(kept)
    log.info(
        "MinHash dedup: removed %d near-duplicates (%.1f%%) | %d docs remaining",
        n_removed,
        n_removed / max(len(docs), 1) * 100,
        len(kept),
    )

    # Write deduplicated output
    out_jsonl = DEDUPED_DIR / "deduplicated.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for doc in kept:
            record = {
                "id": doc["id"],
                "source_file": doc.get("source_file", ""),
                "text": doc["text"],
                "word_count": doc["word_count"],
                "cluster_id": cluster_map.get(doc["id"], doc["id"]),
            }
            # Preserve extra fields (title, url, etc.)
            for k, v in doc.items():
                if k not in record:
                    record[k] = v
            f.write(json.dumps(record) + "\n")

    log.info("Wrote %d docs to %s", len(kept), out_jsonl)

    # Write cluster report
    report_path = DEDUPED_DIR / "dedup_report.jsonl"
    with open(report_path, "w", encoding="utf-8") as f:
        for doc_id, rep_id in cluster_map.items():
            f.write(json.dumps({
                "doc_id": doc_id,
                "representative_id": rep_id,
                "is_kept": doc_id == rep_id,
            }) + "\n")

    log.info("Cluster report written to %s", report_path)
    log.info(
        "Summary: input=%d  exact_removed=%s  near_dup_removed=%d  final=%d",
        n_before,
        f"{n_exact}" if EXACT_HASH_FIRST else "N/A",
        n_removed,
        len(kept),
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MinHash near-duplicate text deduplication")
    ap.add_argument("--threshold", type=float, default=MINHASH_THRESHOLD,
                    help="Jaccard similarity threshold (default: 0.80)")
    ap.add_argument("--num-perm", type=int, default=MINHASH_NUM_PERM,
                    help="Number of MinHash hash functions (default: 128)")
    ap.add_argument("--source-dir", type=Path, default=None,
                    help="Source directory of .txt files (default: data/filtered)")
    ap.add_argument("--source-jsonl", type=Path, default=None,
                    help="Source JSONL file with {'text': ...} records")
    args = ap.parse_args()
    run(
        threshold=args.threshold,
        num_perm=args.num_perm,
        source_dir=args.source_dir,
        source_jsonl=args.source_jsonl,
    )
