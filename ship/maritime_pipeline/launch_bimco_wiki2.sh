#!/bin/bash
set -e
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching BIMCO scraper (sitemap-based)..."
nohup /opt/anaconda3/bin/python scrapers/bimco_scraper.py > logs/bimco_scraper.log 2>&1 &
BIMCO_PID=$!
echo "BIMCO PID=$BIMCO_PID"
sleep 3
tail -5 logs/bimco_scraper.log

echo "Launching Wikipedia2 scraper..."
nohup /opt/anaconda3/bin/python scrapers/wikipedia_maritime2_scraper.py > logs/wikipedia2_scraper.log 2>&1 &
WIKI2_PID=$!
echo "Wiki2 PID=$WIKI2_PID"
sleep 3
tail -3 logs/wikipedia2_scraper.log
