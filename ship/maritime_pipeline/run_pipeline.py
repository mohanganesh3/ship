"""
run_pipeline.py — Full maritime data collection pipeline runner.

Runs all scrapers + extraction + filtering + deduplication in sequence.
Each stage is skippable via flags; all stages are resumable.

Usage:
    cd maritime_pipeline
    python run_pipeline.py                    # run everything
    python run_pipeline.py --skip-scraping    # extraction + filter + dedup only
    python run_pipeline.py --only maib gard   # run specific scrapers only
    python run_pipeline.py --stage extract    # run one stage only
"""

import sys
import logging
import argparse
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import LOGS_DIR
from db import init_db, pipeline_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pipeline")

BASE = Path(__file__).parent

# ── Scraper registry ──────────────────────────────────────────────────────────
SCRAPERS: dict[str, Path] = {
    "maib":          BASE / "scrapers" / "maib_scraper.py",
    "mca":           BASE / "scrapers" / "mca_scraper.py",
    "ntsb":          BASE / "scrapers" / "ntsb_scraper.py",
    "wartsila":      BASE / "scrapers" / "wartsila_scraper.py",
    "gard":          BASE / "scrapers" / "gard_scraper.py",
    "wikipedia":     BASE / "scrapers" / "wikipedia_scraper.py",
    "marineinsight": BASE / "scrapers" / "marineinsight_scraper.py",
    "uscg_nvic":     BASE / "scrapers" / "uscg_nvic_scraper.py",
    "dutch_safety":  BASE / "scrapers" / "dutch_safety_scraper.py",
    "nsia":          BASE / "scrapers" / "nsia_scraper.py",
}

STAGES: dict[str, Path] = {
    "extract": BASE / "extraction" / "pdf_extractor.py",
    "filter":  BASE / "filtering"  / "quality_filter.py",
    "dedup":   BASE / "dedup"      / "minhash_dedup.py",
}


def _run(script: Path, extra_args: list[str] = None) -> bool:
    """Run a Python script as a subprocess. Returns True on success."""
    cmd = [sys.executable, str(script)] + (extra_args or [])
    log.info("▶ Running: %s", " ".join(str(c) for c in cmd))
    start = time.time()
    result = subprocess.run(cmd, cwd=str(BASE))
    elapsed = time.time() - start
    if result.returncode == 0:
        log.info("✓ Completed in %.1f s: %s", elapsed, script.name)
        return True
    else:
        log.error("✗ Failed (exit %d) after %.1f s: %s",
                  result.returncode, elapsed, script.name)
        return False


def run(
    scrapers: list[str] = None,
    stages: list[str] = None,
    skip_scraping: bool = False,
    skip_extraction: bool = False,
    skip_filter: bool = False,
    skip_dedup: bool = False,
) -> None:
    init_db()
    t_start = time.time()
    results: dict[str, bool] = {}

    # ── 1. Scrapers ───────────────────────────────────────────────────────────
    if not skip_scraping and (stages is None or "scrape" in stages):
        to_run = scrapers if scrapers else list(SCRAPERS.keys())
        log.info("═══ STAGE 1: Scraping (%d scrapers) ═══", len(to_run))
        for name in to_run:
            script = SCRAPERS.get(name)
            if not script:
                log.warning("Unknown scraper: %s", name)
                continue
            results[f"scrape_{name}"] = _run(script)

    # ── 2. PDF Extraction ─────────────────────────────────────────────────────
    if not skip_extraction and (stages is None or "extract" in stages):
        log.info("═══ STAGE 2: PDF/EPUB Text Extraction ═══")
        results["extract"] = _run(STAGES["extract"])

    # ── 3. Quality Filter ─────────────────────────────────────────────────────
    if not skip_filter and (stages is None or "filter" in stages):
        log.info("═══ STAGE 3: Quality Filtering ═══")
        results["filter"] = _run(STAGES["filter"])

    # ── 4. Deduplication ──────────────────────────────────────────────────────
    if not skip_dedup and (stages is None or "dedup" in stages):
        log.info("═══ STAGE 4: MinHash Deduplication ═══")
        results["dedup"] = _run(STAGES["dedup"])

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    ok  = sum(1 for v in results.values() if v)
    err = sum(1 for v in results.values() if not v)
    log.info("═══ PIPELINE COMPLETE in %.1f s ═══", elapsed)
    log.info("  Stages: %d OK, %d FAILED", ok, err)

    if err:
        failed = [k for k, v in results.items() if not v]
        log.warning("Failed stages: %s", ", ".join(failed))

    # Print DB stats
    try:
        stats = pipeline_stats()
        log.info("Database stats: %s", stats)
    except Exception:
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Maritime data pipeline runner")
    ap.add_argument("--only", nargs="+", metavar="SCRAPER",
                    choices=list(SCRAPERS.keys()),
                    help="Run only these scrapers (default: all)")
    ap.add_argument("--stage", nargs="+", metavar="STAGE",
                    choices=["scrape", "extract", "filter", "dedup"],
                    help="Run only these pipeline stages")
    ap.add_argument("--skip-scraping",   action="store_true")
    ap.add_argument("--skip-extraction", action="store_true")
    ap.add_argument("--skip-filter",     action="store_true")
    ap.add_argument("--skip-dedup",      action="store_true")
    args = ap.parse_args()

    run(
        scrapers=args.only,
        stages=args.stage,
        skip_scraping=args.skip_scraping,
        skip_extraction=args.skip_extraction,
        skip_filter=args.skip_filter,
        skip_dedup=args.skip_dedup,
    )
