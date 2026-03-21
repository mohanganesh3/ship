#!/bin/bash
# launch_lr_paris.sh - Launch fixed LR and Paris MOU scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching Lloyd's Register scraper..."
nohup /opt/anaconda3/bin/python scrapers/lloyds_register_scraper.py > logs/lloyds_register_scraper.log 2>&1 &
echo "LR launched"

sleep 1

echo "Launching Paris MOU scraper..."
nohup /opt/anaconda3/bin/python scrapers/paris_mou_scraper.py > logs/paris_mou_scraper.log 2>&1 &
echo "Paris MOU launched"

echo "Done"
