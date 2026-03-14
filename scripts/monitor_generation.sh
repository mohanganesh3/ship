#!/bin/bash

OUTPUT_FILE="/home/mohanganesh/ship/training/real_world_data/maritime_real_world.jsonl"
LOG_FILE="/home/mohanganesh/ship/logs/real_world_generation.log"
TARGET=500000

echo "🚢 MARITIME DATA GENERATION MONITOR"
echo "===================================================="
echo "Target: $TARGET samples"
echo

while true; do
    if [ -f "$OUTPUT_FILE" ]; then
        COUNT=$(wc -l < "$OUTPUT_FILE")
        PERCENT=$(echo "scale=2; $COUNT * 100 / $TARGET" | bc)
        
        clear
        echo "🚢 MARITIME DATA GENERATION MONITOR"
        echo "===================================================="
        echo "Generated: $COUNT / $TARGET samples ($PERCENT%)"
        echo
        
        # Show progress bar
        PROGRESS=$(echo "scale=0; $COUNT * 50 / $TARGET" | bc)
        printf "["
        for i in $(seq 1 $PROGRESS); do printf "="; done
        for i in $(seq $PROGRESS 50); do printf " "; done
        printf "]\n\n"
        
        # Show recent samples
        echo "Latest 3 samples:"
        echo "---"
        tail -3 "$OUTPUT_FILE" | jq -r '"\(.category) - \(.provider) - \(.question[:80])..."' 2>/dev/null || tail -3 "$OUTPUT_FILE"
        echo
        
        # Show category distribution (last 100 samples)
        echo "Recent category distribution (last 100):"
        tail -100 "$OUTPUT_FILE" | jq -r '.category' | sort | uniq -c | sort -rn | head -10
        echo
        
        # Show errors from log
        echo "Recent log tail:"
        tail -5 "$LOG_FILE" | grep -E "Error|error|ERROR|Exception" || echo "No errors detected"
        echo
        
        echo "Updated: $(date)"
        echo "Press Ctrl+C to exit monitor"
    else
        echo "Waiting for output file..."
    fi
    
    sleep 30
done
