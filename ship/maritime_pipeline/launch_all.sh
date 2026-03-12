#!/bin/bash
# launch_all.sh — launch all 11 scrapers in parallel background processes
set -e

PYTHON=/opt/anaconda3/bin/python
PIPELINE=/Users/mohanganesh/ship/maritime_pipeline
LOGS=$PIPELINE/logs
SCRAPERS=$PIPELINE/scrapers

mkdir -p "$LOGS"
cd "$PIPELINE"

echo "=== Maritime Scraper Launch ===" | tee $LOGS/launch.log
date | tee -a $LOGS/launch.log

$PYTHON $SCRAPERS/wartsila_scraper.py    > $LOGS/wartsila.log    2>&1 &  echo "wartsila    PID=$!"
$PYTHON $SCRAPERS/marineinsight_scraper.py > $LOGS/marineinsight.log 2>&1 & echo "marineinsight PID=$!"
$PYTHON $SCRAPERS/wikipedia_scraper.py   > $LOGS/wikipedia.log   2>&1 &  echo "wikipedia   PID=$!"
$PYTHON $SCRAPERS/maib_scraper.py        > $LOGS/maib.log        2>&1 &  echo "maib        PID=$!"
$PYTHON $SCRAPERS/gard_scraper.py        > $LOGS/gard.log        2>&1 &  echo "gard        PID=$!"
$PYTHON $SCRAPERS/mca_scraper.py         > $LOGS/mca.log         2>&1 &  echo "mca         PID=$!"
$PYTHON $SCRAPERS/uscg_nvic_scraper.py   > $LOGS/uscg_nvic.log   2>&1 &  echo "uscg_nvic   PID=$!"
$PYTHON $SCRAPERS/ntsb_scraper.py        > $LOGS/ntsb.log        2>&1 &  echo "ntsb        PID=$!"
$PYTHON $SCRAPERS/dutch_safety_scraper.py > $LOGS/dutch_safety.log 2>&1 & echo "dutch_safety PID=$!"
$PYTHON $SCRAPERS/nsia_scraper.py        > $LOGS/nsia.log        2>&1 &  echo "nsia        PID=$!"
$PYTHON $SCRAPERS/bsu_scraper.py         > $LOGS/bsu.log         2>&1 &  echo "bsu         PID=$!"

echo ""
echo "All 11 scrapers launched in background."
echo "Monitor live: tail -f $LOGS/wartsila.log"
echo "Check all logs: ls -lh $LOGS/"
