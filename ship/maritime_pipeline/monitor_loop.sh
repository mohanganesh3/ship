#!/bin/bash
# Monitors scraper progress every 30 minutes, logs to monitor.log
LOG=/Users/mohanganesh/ship/maritime_pipeline/logs/monitor.log
cd /Users/mohanganesh/ship/maritime_pipeline

while true; do
    TS=$(date '+%Y-%m-%d %H:%M:%S LOCAL')
    UTC=$(date -u '+%H:%M UTC')
    echo "" >> $LOG
    echo "=== $TS ($UTC) ===" >> $LOG

    echo "-- Processes --" >> $LOG
    ps aux | grep "python.*scraper" | grep -v grep | awk '{print $2, $NF}' >> $LOG

    echo "-- Article counts --" >> $LOG
    wc -l data/extracted_text/*.jsonl | sort -rn | head -12 >> $LOG

    echo "-- Recent log tails --" >> $LOG
    echo "[safety4sea]" >> $LOG; tail -1 logs/safety4sea_scraper.log >> $LOG 2>/dev/null
    echo "[gcaptain]" >> $LOG;   tail -1 logs/gcaptain_scraper.log >> $LOG 2>/dev/null
    echo "[maritime_executive]" >> $LOG; tail -1 logs/maritime_executive_scraper.log >> $LOG 2>/dev/null
    echo "[hellenic]" >> $LOG;   tail -1 logs/hellenic_scraper.log >> $LOG 2>/dev/null
    echo "[marineinsight]" >> $LOG; tail -1 logs/marineinsight_scraper.log >> $LOG 2>/dev/null
    echo "[wikipedia]" >> $LOG;  tail -1 logs/wikipedia_scraper.log >> $LOG 2>/dev/null
    echo "[oa2]" >> $LOG;        tail -1 logs/openalex2_scraper.log >> $LOG 2>/dev/null
    echo "[oa3]" >> $LOG;        tail -1 logs/openalex3_scraper.log >> $LOG 2>/dev/null

    sleep 1800  # 30 minutes
done
