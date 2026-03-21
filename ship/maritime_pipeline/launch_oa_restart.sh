#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Relaunching OA2 (with 1.5s rate limit)..."
nohup /opt/anaconda3/bin/python scrapers/openalex_maritime2_scraper.py >> logs/openalex2_scraper.log 2>&1 &
OA2_PID=$!
echo "OA2 PID=$OA2_PID"

sleep 2

echo "Relaunching OA3 (with 2.0s rate limit)..."
nohup /opt/anaconda3/bin/python scrapers/openalex_maritime3_scraper.py >> logs/openalex3_scraper.log 2>&1 &
OA3_PID=$!
echo "OA3 PID=$OA3_PID"

sleep 5
echo "--- OA2 recent ---"
tail -3 logs/openalex2_scraper.log
echo "--- OA3 recent ---"
tail -3 logs/openalex3_scraper.log
