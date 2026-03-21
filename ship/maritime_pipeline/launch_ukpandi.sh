#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
/opt/anaconda3/bin/python scrapers/ukpandi_scraper.py > logs/ukpandi_scraper.log 2>&1 &
echo "ukpandi PID: $!"
