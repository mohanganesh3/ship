#!/usr/bin/env python3
"""
Master runner for all depth-boosting scrapers.
Runs scrapers sequentially with progress tracking.
"""
import subprocess, sys, os, time
from datetime import datetime

PYTHON = "/opt/anaconda3/bin/python3"
SCRAPERS_DIR = os.path.dirname(os.path.abspath(__file__))

scrapers = [
    ("APEM / Passage Planning", os.path.join(SCRAPERS_DIR, "scrape_apem_passage.py")),
    ("COW + Enclosed Space Entry", os.path.join(SCRAPERS_DIR, "scrape_cow_ese.py")),
    ("FWG + Tank Gauging", os.path.join(SCRAPERS_DIR, "scrape_fwg_gauging.py")),
    ("Bunkering + Drydocking + MO", os.path.join(SCRAPERS_DIR, "scrape_bunkering_dry_mo.py")),
]

print(f"\n{'='*60}")
print(f"MARITIME DEPTH SCRAPER MASTER RUNNER")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}\n")

failed = []
for name, script in scrapers:
    print(f"\n{'─'*60}")
    print(f"▶ Running: {name}")
    print(f"  Script: {os.path.basename(script)}")
    print(f"{'─'*60}")
    t0 = time.time()
    try:
        result = subprocess.run([PYTHON, script], capture_output=False, text=True, timeout=600)
        elapsed = time.time() - t0
        if result.returncode == 0:
            print(f"\n  ✅ Completed in {elapsed:.0f}s")
        else:
            print(f"\n  ❌ Failed (exit {result.returncode}) in {elapsed:.0f}s")
            failed.append(name)
    except subprocess.TimeoutExpired:
        print(f"\n  ⏱ Timeout after 600s")
        failed.append(name)
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        failed.append(name)

print(f"\n{'='*60}")
print(f"DONE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
if failed:
    print(f"⚠️  Failed: {', '.join(failed)}")
else:
    print(f"✅ All scrapers completed successfully")
print(f"{'='*60}")
print("\nNext step: Run audit_depth.py to verify improvements")
