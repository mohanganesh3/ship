#!/bin/bash
# Wait until midnight UTC, then restart OA2 and OA3 scrapers
# OpenAlex budget resets at midnight UTC

cd /Users/mohanganesh/ship/maritime_pipeline

echo "Waiting until midnight UTC to restart OpenAlex scrapers..."

# Wait in a loop checking UTC time
while true; do
    utc_hour=$(date -u +%H)
    utc_min=$(date -u +%M)
    if [ "$utc_hour" = "00" ] && [ "$utc_min" -lt "05" ]; then
        echo "Midnight UTC reached - starting OpenAlex scrapers..."
        break
    fi
    echo "Current UTC: ${utc_hour}:${utc_min} - sleeping 5 minutes..."
    sleep 300
done

# Wait another 2 minutes to be safe
sleep 120

echo "Launching OA2..."
nohup /opt/anaconda3/bin/python scrapers/openalex_maritime2_scraper.py >> logs/openalex2_scraper.log 2>&1 &
echo "OA2 launched"

# Wait 10 minutes before starting OA3 to stagger
sleep 600

echo "Launching OA3..."
nohup /opt/anaconda3/bin/python scrapers/openalex_maritime3_scraper.py >> logs/openalex3_scraper.log 2>&1 &
echo "OA3 launched"

echo "All OpenAlex scrapers restarted."
