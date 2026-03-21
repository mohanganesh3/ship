#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
nohup /opt/anaconda3/bin/python scrapers/marineinsight_scraper.py >> logs/marineinsight_scraper.log 2>&1 &
echo "MarineInsight restarted PID: $!"
