#!/usr/bin/env python3
"""
Monitor REAL maritime data generation progress
"""

import json
import os
import time
from datetime import datetime, timedelta

DATA_FILE = "/home/mohanganesh/ship/training/real_maritime_data/maritime_real_scenarios.jsonl"

def get_stats():
    """Get current generation stats"""
    if not os.path.exists(DATA_FILE):
        return 0, 0, None, None
    
    count = 0
    start_time = None
    latest_time = None
    
    with open(DATA_FILE, 'r') as f:
        for line in f:
            if line.strip():
                count += 1
                try:
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data.get('timestamp', ''))
                    if start_time is None:
                        start_time = timestamp
                    latest_time = timestamp
                except:
                    pass
    
    return count, 0, start_time, latest_time

def main():
    print("🚢 REAL MARITIME DATA GENERATION MONITOR")
    print("=" * 70)
    
    target = 500000
    last_count = 0
    
    while True:
        count, _, start_time, latest_time = get_stats()
        
        # Calculate rate
        if start_time and latest_time:
            elapsed = (latest_time - start_time).total_seconds() / 3600  # hours
            if elapsed > 0:
                rate_per_hour = count / elapsed
                eta_hours = (target - count) / rate_per_hour if rate_per_hour > 0 else 0
                eta_time = datetime.now() + timedelta(hours=eta_hours)
            else:
                rate_per_hour = 0
                eta_hours = 0
                eta_time = None
        else:
            rate_per_hour = 0
            eta_hours = 0
            eta_time = None
        
        # Recent rate (since last check)
        delta = count - last_count
        last_count = count
        
        # Display
        progress_pct = (count / target) * 100
        bar_length = 40
        filled = int(bar_length * count / target)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        print(f"\r{bar} {count:,}/{target:,} ({progress_pct:.2f}%)", end='')
        print(f" | {rate_per_hour:.0f}/hr", end='')
        if eta_time:
            print(f" | ETA: {eta_time.strftime('%b %d %H:%M')}", end='')
        print(f" | +{delta} ", end='', flush=True)
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ Monitoring stopped")
