#!/bin/bash
# launch_batch3.sh - Launch all pending scrapers
cd /Users/mohanganesh/ship/maritime_pipeline

mkdir -p logs

echo "Launching IACS scraper..."
/opt/anaconda3/bin/python scrapers/iacs_scraper.py > logs/iacs_scraper.log 2>&1 &
echo "IACS PID: $!"

sleep 1

echo "Launching DNV scraper..."
/opt/anaconda3/bin/python scrapers/dnv_scraper.py > logs/dnv_scraper.log 2>&1 &
echo "DNV PID: $!"

sleep 1

echo "Launching IMO scraper..."
/opt/anaconda3/bin/python scrapers/imo_scraper.py > logs/imo_scraper.log 2>&1 &
echo "IMO PID: $!"

sleep 1

echo "Launching ITOPF (fixed) scraper..."
/opt/anaconda3/bin/python scrapers/itopf_scraper.py > logs/itopf_scraper.log 2>&1 &
echo "ITOPF PID: $!"

sleep 1

echo "Launching CHIRP Maritime scraper..."
/opt/anaconda3/bin/python scrapers/chirp_scraper.py > logs/chirp_scraper.log 2>&1 &
echo "CHIRP PID: $!"

sleep 1

echo "Launching Transport Canada scraper..."
/opt/anaconda3/bin/python scrapers/transport_canada_scraper.py > logs/transport_canada_scraper.log 2>&1 &
echo "TC PID: $!"

sleep 1

echo "Launching OpenAlex maritime paper scraper..."
/opt/anaconda3/bin/python scrapers/openalex_maritime_scraper.py > logs/openalex_scraper.log 2>&1 &
echo "OpenAlex PID: $!"

echo ""
echo "All scrapers launched. Monitor with:"
echo "  tail -f logs/iacs_scraper.log"
echo "  tail -f logs/dnv_scraper.log"
echo "  tail -f logs/imo_scraper.log"
echo "  tail -f logs/itopf_scraper.log"
echo "  tail -f logs/chirp_scraper.log"
echo "  tail -f logs/openalex_scraper.log"
