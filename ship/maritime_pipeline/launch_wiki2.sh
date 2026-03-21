#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
nohup /opt/anaconda3/bin/python scrapers/wikipedia_maritime2_scraper.py > logs/wikipedia2_scraper.log 2>&1 &
WIKI2_PID=$!
echo "Wiki2 PID=$WIKI2_PID"
sleep 5
tail -5 logs/wikipedia2_scraper.log
