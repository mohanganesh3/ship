#!/bin/bash
# Check Gard and NTSB status
echo "=== Running scrapers ==="
ps aux | grep -E "python.*scraper" | grep -v grep | awk '{print $2, $11}' | sed 's|.*/scrapers/||'

echo ""
echo "=== Gard JSONL ==="
wc -l /Users/mohanganesh/ship/maritime_pipeline/data/extracted_text/gard_articles.jsonl

echo ""
echo "=== Gard log tail ==="
tail -5 /Users/mohanganesh/ship/maritime_pipeline/logs/gard.log

echo ""
echo "=== NTSB log tail ==="
tail -5 /Users/mohanganesh/ship/maritime_pipeline/logs/ntsb.log

echo ""
echo "=== MCA log tail ==="
tail -5 /Users/mohanganesh/ship/maritime_pipeline/logs/mca_scraper.log

echo ""
echo "=== Total PDFs ==="
find /Users/mohanganesh/ship/maritime_pipeline/data -name "*.pdf" | wc -l
