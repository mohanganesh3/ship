#!/bin/bash
# Launch Safety4Sea, gCaptain, and Maritime Executive scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching Safety4Sea scraper..."
nohup /opt/anaconda3/bin/python scrapers/safety4sea_scraper.py > logs/safety4sea_scraper.log 2>&1 &
S4S_PID=$!
echo "Safety4Sea PID: $S4S_PID"
sleep 3

echo "Launching gCaptain scraper..."
nohup /opt/anaconda3/bin/python scrapers/gcaptain_scraper.py > logs/gcaptain_scraper.log 2>&1 &
GC_PID=$!
echo "gCaptain PID: $GC_PID"
sleep 3

echo "Launching Maritime Executive scraper..."
nohup /opt/anaconda3/bin/python scrapers/maritime_executive_scraper.py > logs/maritime_executive_scraper.log 2>&1 &
ME_PID=$!
echo "Maritime Executive PID: $ME_PID"

echo ""
echo "All scrapers launched. PIDs:"
echo "  Safety4Sea: $S4S_PID"
echo "  gCaptain: $GC_PID"
echo "  Maritime Executive: $ME_PID"
echo ""
echo "Checking logs in 10s..."
sleep 10
echo "=== Safety4Sea ==="
tail -5 logs/safety4sea_scraper.log
echo "=== gCaptain ==="
tail -5 logs/gcaptain_scraper.log
echo "=== Maritime Executive ==="
tail -5 logs/maritime_executive_scraper.log
