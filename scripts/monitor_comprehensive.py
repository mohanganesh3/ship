#!/usr/bin/env python3
"""Monitor comprehensive data generation progress."""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta

STATS_FILE = Path("/home/mohanganesh/ship/training/comprehensive_data/generation_stats.json")
PROGRESS_FILE = Path("/home/mohanganesh/ship/training/comprehensive_data/generation_progress.json")
DATA_FILE = Path("/home/mohanganesh/ship/training/comprehensive_data/maritime_qa_comprehensive.jsonl")

TARGET = 500000

def format_time(seconds):
    """Format seconds to human readable."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        return f"{seconds/86400:.1f}d"

def monitor():
    """Display live progress."""
    while True:
        try:
            # Read stats
            if STATS_FILE.exists():
                with open(STATS_FILE) as f:
                    stats = json.load(f)
            else:
                print("Waiting for stats file...")
                time.sleep(5)
                continue
            
            # Read progress
            if PROGRESS_FILE.exists():
                with open(PROGRESS_FILE) as f:
                    progress = json.load(f)
            else:
                progress = {}
            
            # Count actual samples
            actual_count = 0
            if DATA_FILE.exists():
                with open(DATA_FILE) as f:
                    actual_count = sum(1 for line in f)
            
            # Calculate metrics
            successful = stats.get("successful", 0)
            failed = stats.get("failed", 0)
            total_attempts = successful + failed
            success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
            
            # Time calculations
            start = datetime.fromisoformat(stats["start_time"])
            elapsed = (datetime.now() - start).total_seconds()
            rate = successful / elapsed if elapsed > 0 else 0
            remaining = TARGET - successful
            eta_seconds = remaining / rate if rate > 0 else 0
            
            # Clear screen
            print("\033[2J\033[H")  # Clear screen and move to top
            
            # Header
            print("=" * 80)
            print("🚢 COMPREHENSIVE MARITIME DATA GENERATION - LIVE MONITOR")
            print("=" * 80)
            print()
            
            # Main stats
            print(f"📊 PROGRESS: {successful:,} / {TARGET:,} samples ({successful/TARGET*100:.2f}%)")
            progress_bar_width = 60
            filled = int(progress_bar_width * successful / TARGET)
            bar = "█" * filled + "░" * (progress_bar_width - filled)
            print(f"[{bar}]")
            print()
            
            # Metrics
            print(f"✓ Successful: {successful:,}")
            print(f"✗ Failed: {failed:,}")
            print(f"📈 Success Rate: {success_rate:.1f}%")
            print(f"📁 Files Written: {actual_count:,}")
            print()
            
            # Performance
            print(f"⏱️  Elapsed: {format_time(elapsed)}")
            print(f"⚡ Rate: {rate:.2f} samples/sec ({rate * 3600:.0f}/hour)")
            print(f"🎯 ETA: {format_time(eta_seconds)} ({(datetime.now() + timedelta(seconds=eta_seconds)).strftime('%Y-%m-%d %H:%M')})")
            print()
            
            # Provider distribution
            google = stats.get("google_count", 0)
            cerebras = stats.get("cerebras_count", 0)
            groq = stats.get("groq_count", 0)
            print(f"🔧 PROVIDER USAGE:")
            print(f"   Google:   {google:,} ({google/successful*100:.1f}%)" if successful > 0 else "   Google:   0")
            print(f"   Cerebras: {cerebras:,} ({cerebras/successful*100:.1f}%)" if successful > 0 else "   Cerebras: 0")
            print(f"   Groq:     {groq:,} ({groq/successful*100:.1f}%)" if successful > 0 else "   Groq:     0")
            print()
            
            # Top categories
            by_category = stats.get("by_category", {})
            if by_category:
                print(f"📚 TOP CATEGORIES:")
                sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]
                for cat, count in sorted_cats:
                    print(f"   {cat:30s}: {count:,}")
                print()
            
            # Completed categories
            completed = progress.get("completed_categories", {})
            if completed:
                num_complete = sum(1 for v in completed.values() if v > 100)
                print(f"✅ Categories in progress: {len(completed)}")
                print(f"✅ Categories with >100 samples: {num_complete}")
                print()
            
            print("=" * 80)
            print(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("Press Ctrl+C to exit")
            print("=" * 80)
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor()
