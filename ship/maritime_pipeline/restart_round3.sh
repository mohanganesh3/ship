#!/bin/bash
# Restart Round 3 - for mca, dutch_safety, nsia with fixed scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Killing old mca, dutch_safety, nsia processes..."
pkill -f "mca_scraper.py" 2>/dev/null || true
pkill -f "dutch_safety_scraper.py" 2>/dev/null || true
pkill -f "nsia_scraper.py" 2>/dev/null || true

sleep 3

echo "Starting MCA scraper (fixed MIN URL)..."
/opt/anaconda3/bin/python scrapers/mca_scraper.py > logs/mca_scraper.log 2>&1 &
MCA_PID=$!
echo "MCA PID: $MCA_PID"

sleep 2

echo "Starting Dutch Safety scraper (fixed shipping thema URL)..."
/opt/anaconda3/bin/python scrapers/dutch_safety_scraper.py > logs/dutch_safety_scraper.log 2>&1 &
DUTCH_PID=$!
echo "Dutch Safety PID: $DUTCH_PID"

sleep 2

echo "Starting NSIA scraper (fixed PDF URL pattern)..."
/opt/anaconda3/bin/python scrapers/nsia_scraper.py > logs/nsia_scraper.log 2>&1 &
NSIA_PID=$!
echo "NSIA PID: $NSIA_PID"

echo "All 3 scrapers restarted!"
echo "Monitor: tail -f logs/mca_scraper.log logs/dutch_safety_scraper.log logs/nsia_scraper.log"
