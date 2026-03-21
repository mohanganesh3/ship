#!/bin/bash
# restart_failed.sh — restart only the 3 scrapers that failed initially
PYTHON=/opt/anaconda3/bin/python
PIPELINE=/Users/mohanganesh/ship/maritime_pipeline
LOGS=$PIPELINE/logs
SCRAPERS=$PIPELINE/scrapers

mkdir -p "$LOGS"
cd "$PIPELINE"

$PYTHON $SCRAPERS/marineinsight_scraper.py > $LOGS/marineinsight.log 2>&1 &
echo "marineinsight PID=$!"

$PYTHON $SCRAPERS/gard_scraper.py > $LOGS/gard.log 2>&1 &
echo "gard          PID=$!"

$PYTHON $SCRAPERS/ntsb_scraper.py > $LOGS/ntsb.log 2>&1 &
echo "ntsb          PID=$!"

echo "3 fixed scrapers relaunched."
