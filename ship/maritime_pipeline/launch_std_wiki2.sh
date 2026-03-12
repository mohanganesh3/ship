#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching Standard Club scraper..."
nohup /opt/anaconda3/bin/python scrapers/standard_club_scraper.py > logs/standard_club_scraper.log 2>&1 &
echo "Standard Club launched"

sleep 2

echo "Launching Wikipedia2 scraper..."
nohup /opt/anaconda3/bin/python scrapers/wikipedia_maritime2_scraper.py > logs/wikipedia2_scraper.log 2>&1 &
echo "Wiki2 launched"

sleep 8
echo "=== Standard Club log ==="
tail -5 logs/standard_club_scraper.log
echo "=== Wikipedia2 log ==="
tail -5 logs/wikipedia2_scraper.log
