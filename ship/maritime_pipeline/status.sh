#!/bin/bash
# status.sh — show live status of all scrapers
LOGS=/Users/mohanganesh/ship/maritime_pipeline/logs
DATA=/Users/mohanganesh/ship/maritime_pipeline/data/extracted_text

echo "=== SCRAPER STATUS ===" 
date
echo ""

echo "--- Log file sizes (recent activity) ---"
ls -lht $LOGS/*.log 2>/dev/null | head -20

echo ""
echo "--- JSONL output files ---"
for f in $DATA/*.jsonl; do
    if [ -f "$f" ]; then
        lines=$(wc -l < "$f" 2>/dev/null || echo 0)
        size=$(du -sh "$f" 2>/dev/null | cut -f1)
        name=$(basename "$f")
        echo "  $name: $lines entries ($size)"
    fi
done

echo ""
echo "--- Running python scraper processes ---"
ps aux | grep "scrapers/" | grep -v grep | awk '{print $2, $11, $12}' || echo "  (none running)"

echo ""
echo "--- Token estimate from JSONL ---"
total_chars=0
for f in $DATA/*.jsonl; do
    if [ -f "$f" ]; then
        chars=$(wc -c < "$f" 2>/dev/null || echo 0)
        total_chars=$((total_chars + chars))
    fi
done
tokens=$((total_chars / 4))
echo "  Approx total tokens: $(echo $tokens | sed ':a;s/\B[0-9]\{3\}\>/,&/;ta')"
