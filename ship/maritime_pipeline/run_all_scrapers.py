#!/usr/bin/env python3
"""
run_all_scrapers.py — Master orchestrator for all maritime data scrapers.

Runs all scrapers in priority order, handling errors gracefully.
After all scrapers complete, prints a token count summary.

Usage:
    cd /Users/mohanganesh/ship/maritime_pipeline
    python run_all_scrapers.py

    # Skip specific scrapers:
    python run_all_scrapers.py --skip wikipedia marineinsight

    # Run only specific scrapers:
    python run_all_scrapers.py --only wartsila maib gard
"""

import sys
import os
import time
import json
import argparse
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# ── Setup ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
SCRAPERS_DIR = BASE_DIR / "scrapers"
LOGS_DIR   = BASE_DIR / "logs"
DATA_DIR   = BASE_DIR / "data"
EXTRACTED  = DATA_DIR / "extracted_text"
RAW_PDFS   = DATA_DIR / "raw_pdfs"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "run_all_scrapers.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("orchestrator")

# ── Scraper registry (priority order — highest token yield first) ─────────────
SCRAPERS = [
    # name, script, estimated_tokens, description
    ("wartsila",      "wartsila_scraper.py",      "~8M",  "Wärtsilä Encyclopedia (4000+ engineering entries)"),
    ("marineinsight", "marineinsight_scraper.py", "~15M", "MarineInsight.com (10,000+ how-to articles)"),
    ("wikipedia",     "wikipedia_scraper.py",     "~10M", "Wikipedia maritime categories"),
    ("maib",          "maib_scraper.py",          "~5M",  "MAIB UK accident PDFs (1000+ reports)"),
    ("gard",          "gard_scraper.py",          "~3M",  "Gard P&I Club articles (1454+)"),
    ("mca",           "mca_scraper.py",           "~3M",  "UK MCA notices (MGN/MSN/MIN)"),
    ("uscg_nvic",     "uscg_nvic_scraper.py",     "~2M",  "USCG Navigation & Vessel Inspection Circulars"),
    ("ntsb",          "ntsb_scraper.py",          "~2M",  "NTSB US marine investigation reports"),
    ("dutch_safety",  "dutch_safety_scraper.py",  "~1M",  "Dutch Safety Board maritime reports"),
    ("nsia",          "nsia_scraper.py",          "~1M",  "Norwegian NSIA maritime investigation reports"),
    ("bsu",           "bsu_scraper.py",           "~1M",  "BSU German maritime investigation reports"),
]


def _count_tokens_in_jsonl(path: Path) -> tuple[int, int]:
    """Return (num_records, estimated_token_count) from a JSONL file."""
    records = tokens = 0
    if not path.exists():
        return 0, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                text = obj.get("text", "")
                word_count = obj.get("word_count", len(text.split()))
                # Rough: 1 token ≈ 0.75 words
                tokens += int(word_count / 0.75)
                records += 1
            except Exception:
                pass
    return records, tokens


def _count_tokens_in_pdfs(dir_path: Path) -> tuple[int, int]:
    """Count PDF files and estimate token count (avg 2000 tokens/page, ~15 pages)."""
    if not dir_path.exists():
        return 0, 0
    pdfs = list(dir_path.rglob("*.pdf"))
    # Rough estimate: each PDF ≈ 10 pages avg ≈ 3000 tokens/page
    return len(pdfs), len(pdfs) * 30_000


def _print_token_summary() -> None:
    """Print a summary of all collected data and token estimates."""
    log.info("\n" + "=" * 70)
    log.info("TOKEN COLLECTION SUMMARY")
    log.info("=" * 70)

    total_tokens = 0
    total_records = 0

    # JSONL files (Wartsila, MarineInsight, Wikipedia, Gard)
    jsonl_files = {
        "wartsila":      EXTRACTED / "wartsila_encyclopedia.jsonl",
        "marineinsight": EXTRACTED / "marineinsight_articles.jsonl",
        "wikipedia":     EXTRACTED / "wikipedia_maritime.jsonl",
        "gard":          EXTRACTED / "gard_articles.jsonl",
    }
    for name, path in jsonl_files.items():
        recs, toks = _count_tokens_in_jsonl(path)
        log.info("  %-20s  %6d records  %8.1fM tokens  [JSONL]",
                 name, recs, toks / 1_000_000)
        total_records += recs
        total_tokens += toks

    # PDF directories
    pdf_dirs = {
        "maib":       RAW_PDFS / "maib",
        "mca":        RAW_PDFS / "mca",
        "uscg_nvic":  RAW_PDFS / "uscg_nvic",
        "ntsb":       RAW_PDFS / "ntsb",
        "dutch_safety": RAW_PDFS / "dutch_safety",
        "nsia":       RAW_PDFS / "nsia",
        "bsu":        RAW_PDFS / "bsu",
    }
    for name, dir_path in pdf_dirs.items():
        count, toks = _count_tokens_in_pdfs(dir_path)
        log.info("  %-20s  %6d PDFs     %8.1fM tokens  [PDF, est]",
                 name, count, toks / 1_000_000)
        total_tokens += toks
        total_records += count

    # Also count pre-existing data
    existing_data = Path("/Users/mohanganesh/ship/data")
    if existing_data.exists():
        existing_pdfs = list(existing_data.glob("*.pdf")) + list(existing_data.glob("*.djvu")) + list(existing_data.glob("*.epub"))
        existing_toks = len(existing_pdfs) * 80_000  # textbooks avg 40 pages × 2000 tok
        log.info("  %-20s  %6d files    %8.1fM tokens  [existing books, est]",
                 "pre-existing textbooks", len(existing_pdfs), existing_toks / 1_000_000)
        total_tokens += existing_toks
        total_records += len(existing_pdfs)

    log.info("-" * 70)
    log.info("  %-20s  %6d items    %8.1fM tokens  TOTAL",
             "GRAND TOTAL", total_records, total_tokens / 1_000_000)
    log.info("  Target: 50M tokens — Status: %s",
             "✅ ACHIEVED" if total_tokens >= 50_000_000 else f"❌ Need {(50_000_000 - total_tokens)/1_000_000:.1f}M more")
    log.info("=" * 70 + "\n")


def run_scraper(name: str, script: str) -> bool:
    """Run a single scraper script. Return True on success."""
    script_path = SCRAPERS_DIR / script
    if not script_path.exists():
        log.error("Script not found: %s", script_path)
        return False

    log.info("\n%s", "─" * 70)
    log.info("▶  Starting: %s  (%s)", name, script)
    log.info("%s", "─" * 70)

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=False,   # stream output live to terminal
            timeout=18000,          # 5 hours max per scraper
        )
        elapsed = time.time() - start
        if result.returncode == 0:
            log.info("✅ %s completed in %.0f seconds", name, elapsed)
            return True
        else:
            log.error("❌ %s exited with code %d in %.0f seconds",
                      name, result.returncode, elapsed)
            return False
    except subprocess.TimeoutExpired:
        log.error("⏱  %s timed out after 5 hours", name)
        return False
    except KeyboardInterrupt:
        log.info("⏹  Interrupted by user during %s", name)
        raise
    except Exception as exc:
        log.error("❌ %s crashed: %s", name, exc)
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Run all maritime scrapers")
    ap.add_argument("--skip", nargs="*", default=[], metavar="NAME",
                    help="Scraper names to skip")
    ap.add_argument("--only", nargs="*", default=[], metavar="NAME",
                    help="Run only these scrapers (ignores --skip)")
    ap.add_argument("--summary-only", action="store_true",
                    help="Only print token summary, don't run scrapers")
    args = ap.parse_args()

    if args.summary_only:
        _print_token_summary()
        return

    # Select which scrapers to run
    to_run = SCRAPERS
    if args.only:
        only_set = set(args.only)
        to_run = [s for s in SCRAPERS if s[0] in only_set]
    elif args.skip:
        skip_set = set(args.skip)
        to_run = [s for s in SCRAPERS if s[0] not in skip_set]

    log.info("=" * 70)
    log.info("MARITIME DATA COLLECTION — %d scrapers queued", len(to_run))
    log.info("Started: %s", datetime.utcnow().isoformat())
    log.info("=" * 70)

    for name, desc, est_tokens, _ in to_run:
        log.info("  %-20s  %-8s  %s", name, est_tokens, _)
    log.info("")

    results = {}
    for name, script, est_tokens, description in to_run:
        try:
            success = run_scraper(name, script)
            results[name] = "✅" if success else "❌"
        except KeyboardInterrupt:
            log.info("\nCollection interrupted. Printing summary of work done so far…")
            results[name] = "⏹"
            break

    # Final summary
    log.info("\n%s", "=" * 70)
    log.info("SCRAPER RUN RESULTS:")
    for name, status in results.items():
        log.info("  %s  %s", status, name)

    _print_token_summary()


if __name__ == "__main__":
    main()
