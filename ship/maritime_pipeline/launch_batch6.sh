#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching ClassNK scraper..."
nohup /opt/anaconda3/bin/python scrapers/classnk_scraper.py > logs/classnk_scraper.log 2>&1 &
echo "ClassNK launched"

sleep 2

echo "Launching Hellenic Shipping News scraper..."
nohup /opt/anaconda3/bin/python scrapers/hellenic_scraper.py > logs/hellenic_scraper.log 2>&1 &
echo "Hellenic launched"

sleep 2

echo "Launching Standard Club scraper..."
nohup /opt/anaconda3/bin/python scrapers/standard_club_scraper.py > logs/standard_club_scraper.log 2>&1 &
echo "Standard Club launched"

sleep 8
echo "=== ClassNK log ==="
tail -5 logs/classnk_scraper.log
echo "=== Hellenic log ==="
tail -5 logs/hellenic_scraper.log
echo "=== Standard Club log ==="
tail -5 logs/standard_club_scraper.log
