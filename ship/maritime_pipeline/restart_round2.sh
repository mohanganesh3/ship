#!/bin/bash
# restart_round2.sh — restart MCA, Dutch Safety, NSIA scrapers
PYTHON=/opt/anaconda3/bin/python
PIPELINE=/Users/mohanganesh/ship/maritime_pipeline
LOGS=$PIPELINE/logs
SCRAPERS=$PIPELINE/scrapers

pkill -f mca_scraper 2>/dev/null || true
pkill -f dutch_safety_scraper 2>/dev/null || true
pkill -f nsia_scraper 2>/dev/null || true
sleep 1

$PYTHON $SCRAPERS/mca_scraper.py > $LOGS/mca.log 2>&1 &
echo "mca          PID=$!"

$PYTHON $SCRAPERS/dutch_safety_scraper.py > $LOGS/dutch_safety.log 2>&1 &
echo "dutch_safety PID=$!"

$PYTHON $SCRAPERS/nsia_scraper.py > $LOGS/nsia.log 2>&1 &
echo "nsia         PID=$!"

echo "Round 2 scrapers relaunched."
