#!/bin/bash
# relaunch_marineinsight.sh
PYTHON=/opt/anaconda3/bin/python
PIPELINE=/Users/mohanganesh/ship/maritime_pipeline
LOGS=$PIPELINE/logs
SCRAPERS=$PIPELINE/scrapers

pkill -f marineinsight_scraper 2>/dev/null || true
sleep 1
$PYTHON $SCRAPERS/marineinsight_scraper.py > $LOGS/marineinsight.log 2>&1 &
echo "marineinsight relaunched PID=$!"
