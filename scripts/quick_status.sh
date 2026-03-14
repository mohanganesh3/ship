#!/bin/bash
# Quick status check for maritime data generation

FILE="/home/mohanganesh/ship/training/real_world_data/maritime_real_world.jsonl"
TARGET=500000

if [ ! -f "$FILE" ]; then
    echo "❌ Generation not started yet"
    exit 1
fi

COUNT=$(wc -l < "$FILE")
PERCENT=$(awk "BEGIN {printf \"%.4f\", ($COUNT * 100 / $TARGET)}")

echo "🚢 MARITIME DATA GENERATION STATUS"
echo "═══════════════════════════════════════════════════════════"
echo "  Generated: $COUNT / $TARGET samples ($PERCENT%)"
echo
echo "  API Distribution:"
cat "$FILE" | jq -r '.provider' | sort | uniq -c | while read n p; do
    echo "    $p: $n samples"
done
echo
echo "  Top 5 Categories:"
cat "$FILE" | jq -r '.category' | sort | uniq -c | sort -rn | head -5 | while read n c; do
    echo "    $c: $n samples"
done
echo
echo "  Latest sample:"
tail -1 "$FILE" | jq -r '"    " + .category + " (" + .provider + ")"'
echo
echo "  File size: $(ls -lh "$FILE" | awk '{print $5}')"
echo "  Last updated: $(stat -c %y "$FILE" | cut -d'.' -f1)"
echo "═══════════════════════════════════════════════════════════"

# Check if generator is running
PID=$(pgrep -f "real_world_generator.py" | head -1)
if [ -n "$PID" ]; then
    echo "  ✅ Generator RUNNING (PID: $PID)"
    RUNTIME=$(ps -p $PID -o etime --no-headers | tr -d ' ')
    echo "  Runtime: $RUNTIME"
else
    echo "  ⚠️  Generator NOT RUNNING"
fi
