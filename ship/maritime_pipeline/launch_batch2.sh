#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline
/opt/anaconda3/bin/python scrapers/emsa_scraper.py > logs/emsa_scraper.log 2>&1 &
echo "emsa PID: $!"
/opt/anaconda3/bin/python scrapers/steamship_scraper.py > logs/steamship_scraper.log 2>&1 &
echo "steamship PID: $!"
/opt/anaconda3/bin/python scrapers/itopf_scraper.py > logs/itopf_scraper.log 2>&1 &
echo "itopf PID: $!"
