#!/bin/bash
# launch_abs_bimco.sh - relaunch fixed ABS and BIMCO scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching ABS scraper (fixed)..."
nohup /opt/anaconda3/bin/python scrapers/abs_scraper.py > logs/abs_scraper.log 2>&1 &
echo "ABS launched"

sleep 1

echo "Launching BIMCO scraper (fixed)..."
nohup /opt/anaconda3/bin/python scrapers/bimco_scraper.py > logs/bimco_scraper.log 2>&1 &
echo "BIMCO launched"

echo "Done"
