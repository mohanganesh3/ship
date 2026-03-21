from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator

from .paths import import_config
from .utils import now_iso

try:
    from datasketch import MinHash, MinHashLSH  # type: ignore

    _DATASKETCH_AVAILABLE = True
except Exception:  # pragma: no cover
    MinHash = None  # type: ignore
    MinHashLSH = None  # type: ignore
    _DATASKETCH_AVAILABLE = False


def _tokenise(text: str) -> list[str]:
    import re

    return re.findall(r"\b[a-z]{2,}\b", text.lower())


def _ngrams(tokens: list[str], n: int = 5) -> Iterator[str]:
    for i in range(len(tokens) - n + 1):
        yield " ".join(tokens[i : i + n])


def _build_sig(text: str, num_perm: int) -> Any:
    m = MinHash(num_perm=num_perm)
    toks = _tokenise(text)
    for ng in _ngrams(toks, n=5):
        m.update(ng.encode("utf-8", errors="replace"))
    return m


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


def doc_threshold(doc_type: str, default: float) -> float:
    # Regulatory / circular text is often repeated with minor formatting differences.
    if doc_type in {"regulation", "circular"}:
        return max(default, 0.92)
    if doc_type in {"guidance"}:
        return max(default, 0.88)
    return default


def dedup(
    records: list[dict[str, Any]],
    threshold_default: float,
    num_perm: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (kept_records, dedup_report_records)."""
    def exact_dedup(recs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Always-available exact dedup on sha256(text)."""
        seen: dict[str, str] = {}
        kept: list[dict[str, Any]] = []
        report: list[dict[str, Any]] = []
        for r in recs:
            sha = str(r.get("sha256") or "")
            if not sha:
                # fall back to hashing text in a stable way
                import hashlib

                sha = hashlib.sha256(str(r.get("text") or "").encode("utf-8", errors="replace")).hexdigest()
            rid = str(r.get("id"))
            if sha in seen:
                report.append(
                    {
                        "timestamp": now_iso(),
                        "doc_type": r.get("doc_type"),
                        "threshold": None,
                        "removed_id": rid,
                        "kept_id": seen[sha],
                        "removed_source_id": r.get("source_id"),
                        "kept_source_id": None,
                        "reason": "exact_sha256_duplicate",
                    }
                )
            else:
                seen[sha] = rid
                kept.append(r)
        return kept, report

    if not _DATASKETCH_AVAILABLE:
        # Degraded mode: exact dedup only.
        # This keeps the pipeline runnable in minimal environments, but the audit log will
        # clearly indicate that near-duplicate removal was skipped.
        kept, report = exact_dedup(records)
        report.insert(
            0,
            {
                "timestamp": now_iso(),
                "reason": "datasketch_missing_exact_only",
                "message": "datasketch is not installed; performed exact SHA-256 dedup only (no MinHash near-dup removal)",
            },
        )
        return kept, report

    # Group by doc_type to allow different thresholds.
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_type[str(r.get("doc_type") or "unknown")].append(r)

    kept_all: list[dict[str, Any]] = []
    report_all: list[dict[str, Any]] = []

    for dt, group in sorted(by_type.items(), key=lambda x: x[0]):
        thr = doc_threshold(dt, threshold_default)
        lsh = MinHashLSH(threshold=thr, num_perm=num_perm)

        # Build signatures
        sigs: dict[str, Any] = {}
        for r in group:
            sigs[r["id"]] = _build_sig(r["text"], num_perm=num_perm)

        # Keep longest in each cluster
        rep_text_len: dict[str, int] = {}
        cluster_rep: dict[str, str] = {}

        for r in group:
            rid = r["id"]
            sig = sigs[rid]
            neighbours = lsh.query(sig)
            if neighbours:
                rep = neighbours[0]
                # choose the longer doc as representative
                cur_len = int(r.get("word_count") or len(r["text"].split()))
                rep_len = rep_text_len.get(rep, 0)
                if cur_len > rep_len:
                    # swap representative
                    try:
                        lsh.remove(rep)
                    except Exception:
                        pass
                    lsh.insert(rid, sig)
                    rep_text_len[rid] = cur_len
                    cluster_rep[rep] = rid
                    rep = rid
                cluster_rep[rid] = rep
            else:
                lsh.insert(rid, sig)
                cur_len = int(r.get("word_count") or len(r["text"].split()))
                rep_text_len[rid] = cur_len
                cluster_rep[rid] = rid

        # Resolve representative chains if swaps occurred
        def resolve(x: str) -> str:
            seen = set()
            while cluster_rep.get(x, x) != x and x not in seen:
                seen.add(x)
                x = cluster_rep[x]
            return x

        for k in list(cluster_rep.keys()):
            cluster_rep[k] = resolve(cluster_rep[k])

        reps = {cluster_rep[r["id"]] for r in group}
        rep_to_records: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in group:
            rep_to_records[cluster_rep[r["id"]]].append(r)

        for rep_id, members in rep_to_records.items():
            # keep the representative record
            rep_rec = next((m for m in members if m["id"] == rep_id), members[0])
            kept_all.append(rep_rec)
            for m in members:
                if m["id"] == rep_id:
                    continue
                report_all.append(
                    {
                        "timestamp": now_iso(),
                        "doc_type": dt,
                        "threshold": thr,
                        "removed_id": m["id"],
                        "kept_id": rep_id,
                        "removed_source_id": m.get("source_id"),
                        "kept_source_id": rep_rec.get("source_id"),
                        "reason": "minhash_near_duplicate",
                    }
                )

    return kept_all, report_all


def main() -> int:
    cfg = import_config()
    ap = argparse.ArgumentParser(description="Deduplicate Stage-0 CPT corpus by doc_type-aware MinHash thresholds.")
    ap.add_argument("--in", dest="inp", type=Path, default=cfg.FINAL_DIR / "cpt_corpus.jsonl")
    ap.add_argument("--out", type=Path, default=cfg.FINAL_DIR / "cpt_corpus_deduped.jsonl")
    ap.add_argument("--report", type=Path, default=cfg.FINAL_DIR / "dedup_report.jsonl")
    ap.add_argument("--threshold", type=float, default=cfg.MINHASH_THRESHOLD)
    ap.add_argument("--num-perm", type=int, default=cfg.MINHASH_NUM_PERM)
    args = ap.parse_args()

    records = load_jsonl(args.inp)
    kept, report = dedup(records, threshold_default=args.threshold, num_perm=args.num_perm)

    write_jsonl(args.out, kept)
    write_jsonl(args.report, report)

    print(f"Input records: {len(records)}")
    print(f"Kept records : {len(kept)}")
    print(f"Removed      : {len(records) - len(kept)}")
    print(f"Report lines : {len(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
