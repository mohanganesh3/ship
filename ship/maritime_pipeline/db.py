"""
db.py – SQLite-backed progress tracker.

Every URL and every file that passes through the pipeline is recorded here so
the entire pipeline is fully resumable: rerunning a phase skips work already done.

Schema
------
downloads(url, file_path, source, status, file_hash, bytes, created_at, updated_at)
extractions(file_path, out_path, status, word_count, created_at, updated_at)
filter_results(doc_id, source_file, status, quality_score, word_count, lang, reason, created_at)
dedup_results(doc_id, status, cluster_id, created_at)
"""
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Optional
import logging

from config import DB_PATH

log = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent writes
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = _connect()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS downloads (
            url         TEXT PRIMARY KEY,
            file_path   TEXT,
            source      TEXT,
            status      TEXT DEFAULT 'pending',
            file_hash   TEXT,
            bytes       INTEGER DEFAULT 0,
            created_at  REAL DEFAULT (unixepoch()),
            updated_at  REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS extractions (
            file_path   TEXT PRIMARY KEY,
            out_path    TEXT,
            status      TEXT DEFAULT 'pending',
            word_count  INTEGER DEFAULT 0,
            created_at  REAL DEFAULT (unixepoch()),
            updated_at  REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS filter_results (
            doc_id        TEXT PRIMARY KEY,
            source_file   TEXT,
            status        TEXT DEFAULT 'pending',
            quality_score REAL DEFAULT 0.0,
            word_count    INTEGER DEFAULT 0,
            lang          TEXT,
            reason        TEXT,
            created_at    REAL DEFAULT (unixepoch())
        );

        CREATE TABLE IF NOT EXISTS dedup_results (
            doc_id     TEXT PRIMARY KEY,
            status     TEXT DEFAULT 'pending',
            cluster_id TEXT,
            created_at REAL DEFAULT (unixepoch())
        );

        CREATE INDEX IF NOT EXISTS idx_downloads_source  ON downloads(source);
        CREATE INDEX IF NOT EXISTS idx_downloads_status  ON downloads(status);
        CREATE INDEX IF NOT EXISTS idx_filter_status     ON filter_results(status);
        """)
    conn.close()
    log.info("Database initialised at %s", DB_PATH)


# ── Download tracking ──────────────────────────────────────────────────────────

def is_downloaded(url: str) -> bool:
    conn = _connect()
    row = conn.execute(
        "SELECT status FROM downloads WHERE url=?", (url,)
    ).fetchone()
    conn.close()
    return row is not None and row["status"] == "done"


def mark_download_pending(url: str, source: str) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT OR IGNORE INTO downloads(url, source, status, created_at, updated_at)
               VALUES(?,?,'pending',unixepoch(),unixepoch())""",
            (url, source),
        )
    conn.close()


def mark_download_done(url: str, file_path: Path, file_hash: str, n_bytes: int) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO downloads(url,file_path,status,file_hash,bytes,updated_at)
               VALUES(?,?,'done',?,?,unixepoch())
               ON CONFLICT(url) DO UPDATE SET
                  file_path=excluded.file_path,
                  status='done',
                  file_hash=excluded.file_hash,
                  bytes=excluded.bytes,
                  updated_at=unixepoch()""",
            (url, str(file_path), file_hash, n_bytes),
        )
    conn.close()


def mark_download_failed(url: str, reason: str = "") -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO downloads(url,status,updated_at)
               VALUES(?,'failed',unixepoch())
               ON CONFLICT(url) DO UPDATE SET status='failed', updated_at=unixepoch()""",
            (url,),
        )
    conn.close()


# ── Extraction tracking ────────────────────────────────────────────────────────

def is_extracted(file_path: str) -> bool:
    conn = _connect()
    row = conn.execute(
        "SELECT status FROM extractions WHERE file_path=?", (str(file_path),)
    ).fetchone()
    conn.close()
    return row is not None and row["status"] == "done"


def mark_extraction_done(file_path: str, out_path: str, word_count: int) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO extractions(file_path,out_path,status,word_count,updated_at)
               VALUES(?,?,'done',?,unixepoch())
               ON CONFLICT(file_path) DO UPDATE SET
                  out_path=excluded.out_path, status='done',
                  word_count=excluded.word_count, updated_at=unixepoch()""",
            (str(file_path), str(out_path), word_count),
        )
    conn.close()


def mark_extraction_failed(file_path: str) -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """INSERT INTO extractions(file_path,status,updated_at)
               VALUES(?,'failed',unixepoch())
               ON CONFLICT(file_path) DO UPDATE SET status='failed', updated_at=unixepoch()""",
            (str(file_path),),
        )
    conn.close()


# ── Statistics helpers ────────────────────────────────────────────────────────

def pipeline_stats() -> dict:
    conn = _connect()
    stats: dict = {}

    stats["downloads"] = dict(conn.execute(
        "SELECT status, COUNT(*) as n, SUM(bytes) as total_bytes "
        "FROM downloads GROUP BY status"
    ).fetchall() or [])

    stats["extractions"] = dict(conn.execute(
        "SELECT status, COUNT(*) as n, SUM(word_count) as total_words "
        "FROM extractions GROUP BY status"
    ).fetchall() or [])

    stats["filter"] = dict(conn.execute(
        "SELECT status, COUNT(*) as n FROM filter_results GROUP BY status"
    ).fetchall() or [])

    stats["dedup"] = dict(conn.execute(
        "SELECT status, COUNT(*) as n FROM dedup_results GROUP BY status"
    ).fetchall() or [])

    conn.close()
    return stats


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
