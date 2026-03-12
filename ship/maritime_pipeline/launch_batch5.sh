#!/bin/bash
# launch_batch5.sh - Launch batch 5 scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching OpenAlex Wave 2..."
nohup /opt/anaconda3/bin/python scrapers/openalex_maritime2_scraper.py > logs/openalex2_scraper.log 2>&1 &
echo "OA2 launched"

sleep 1

echo "Launching ABS scraper..."
nohup /opt/anaconda3/bin/python scrapers/abs_scraper.py > logs/abs_scraper.log 2>&1 &
echo "ABS launched"

sleep 1

echo "Launching BIMCO scraper..."
nohup /opt/anaconda3/bin/python scrapers/bimco_scraper.py > logs/bimco_scraper.log 2>&1 &
echo "BIMCO launched"

echo "All batch 5 scrapers launched"
