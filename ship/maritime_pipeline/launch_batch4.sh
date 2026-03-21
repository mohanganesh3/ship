#!/bin/bash
# launch_batch4.sh - Launch new scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

echo "Launching Lloyd's Register scraper..."
nohup /opt/anaconda3/bin/python scrapers/lloyds_register_scraper.py > logs/lloyds_register_scraper.log 2>&1 &
LR_PID=$!
echo "LR PID: $LR_PID"

sleep 1

echo "Launching Paris MOU scraper..."
nohup /opt/anaconda3/bin/python scrapers/paris_mou_scraper.py > logs/paris_mou_scraper.log 2>&1 &
PARIS_PID=$!
echo "Paris PID: $PARIS_PID"

sleep 1

echo "Launching Skuld scraper..."
nohup /opt/anaconda3/bin/python scrapers/skuld_scraper.py > logs/skuld_scraper.log 2>&1 &
SKULD_PID=$!
echo "Skuld PID: $SKULD_PID"

echo "All batch 4 scrapers launched"
echo "LR=$LR_PID, Paris=$PARIS_PID, Skuld=$SKULD_PID"
