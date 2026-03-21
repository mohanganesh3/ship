#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
nohup /opt/anaconda3/bin/python scrapers/gcaptain_scraper.py > logs/gcaptain_scraper.log 2>&1 &
echo "gCaptain PID: $!"
