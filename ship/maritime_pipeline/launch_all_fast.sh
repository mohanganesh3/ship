#!/bin/bash
cd /Users/mohanganesh/ship/maritime_pipeline

nohup /opt/anaconda3/bin/python scrapers/gcaptain_scraper.py >> logs/gcaptain_scraper.log 2>&1 &
echo "gCaptain PID: $!"

nohup /opt/anaconda3/bin/python scrapers/maritime_executive_scraper.py >> logs/maritime_executive_scraper.log 2>&1 &
echo "MarEx PID: $!"

nohup /opt/anaconda3/bin/python scrapers/safety4sea_scraper.py >> logs/safety4sea_scraper.log 2>&1 &
echo "S4S PID: $!"

nohup /opt/anaconda3/bin/python scrapers/hellenic_scraper.py >> logs/hellenic_scraper.log 2>&1 &
echo "Hellenic PID: $!"

nohup /opt/anaconda3/bin/python scrapers/marineinsight_scraper.py >> logs/marineinsight_scraper.log 2>&1 &
echo "MarineInsight PID: $!"

nohup /opt/anaconda3/bin/python scrapers/openalex2_scraper.py >> logs/openalex2_scraper.log 2>&1 &
echo "OA2 PID: $!"

nohup /opt/anaconda3/bin/python scrapers/openalex3_scraper.py >> logs/openalex3_scraper.log 2>&1 &
echo "OA3 PID: $!"

echo "All launched."
