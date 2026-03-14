#!/bin/bash
# Real-time generation dashboard

OUTPUT_FILE="/home/mohanganesh/ship/training/real_world_data/maritime_real_world.jsonl"
LOG_FILE="/home/mohanganesh/ship/logs/real_world_generation.log"
TARGET=500000

while true; do
    clear
    echo "════════════════════════════════════════════════════════════════"
    echo "       🚢 MARITIME AI TRAINING DATA GENERATION DASHBOARD"
    echo "════════════════════════════════════════════════════════════════"
    echo
    
    # Check if file exists
    if [ ! -f "$OUTPUT_FILE" ]; then
        echo "⏳ Waiting for generation to start..."
        sleep 5
        continue
    fi
    
    # Get counts
    TOTAL=$(wc -l < "$OUTPUT_FILE")
    PERCENT=$(awk "BEGIN {printf \"%.2f\", ($TOTAL * 100 / $TARGET)}")
    REMAINING=$(($TARGET - $TOTAL))
    
    # Parse log for stats
    LAST_LOG=$(tail -1 "$LOG_FILE")
    SUCCESS=$(echo "$LAST_LOG" | grep -oP 'Success: \K[0-9,]+' | tr -d ',')
    FAILED=$(echo "$LAST_LOG" | grep -oP 'Failed: \K[0-9]+')
    RATE=$(echo "$LAST_LOG" | grep -oP 'Rate: \K[0-9.]+')
    ETA=$(echo "$LAST_LOG" | grep -oP 'ETA: \K[0-9.]+')
    
    # Display stats
    echo "📊 OVERALL PROGRESS"
    echo "────────────────────────────────────────────────────────────────"
    echo "   Generated: $(printf "%'d" $TOTAL) / $(printf "%'d" $TARGET) samples ($PERCENT%)"
    echo "   Remaining: $(printf "%'d" $REMAINING) samples"
    echo
    
    # Progress bar
    BAR_WIDTH=50
    FILLED=$(awk "BEGIN {printf \"%.0f\", ($TOTAL * $BAR_WIDTH / $TARGET)}")
    printf "   ["
    for ((i=0; i<$FILLED; i++)); do printf "█"; done
    for ((i=$FILLED; i<$BAR_WIDTH; i++)); do printf "░"; done
    printf "]\n\n"
    
    # Performance stats
    if [ -n "$SUCCESS" ]; then
        echo "⚡ PERFORMANCE"
        echo "────────────────────────────────────────────────────────────────"
        echo "   Success rate: $SUCCESS successful"
        echo "   Failed: $FAILED attempts"
        echo "   Generation rate: $RATE samples/sec"
        echo "   ETA: $ETA hours"
        echo
    fi
    
    # API distribution
    echo "🔑 API USAGE DISTRIBUTION"
    echo "────────────────────────────────────────────────────────────────"
    cat "$OUTPUT_FILE" | jq -r '.provider' 2>/dev/null | sort | uniq -c | while read count provider; do
        pct=$(awk "BEGIN {printf \"%.1f\", ($count * 100 / $TOTAL)}")
        printf "   %-12s %6d samples (%5s%%)\n" "$provider" "$count" "$pct"
    done
    echo
    
    # Category distribution (top 10)
    echo "📋 TOP 10 CATEGORIES"
    echo "────────────────────────────────────────────────────────────────"
    cat "$OUTPUT_FILE" | jq -r '.category' 2>/dev/null | sort | uniq -c | sort -rn | head -10 | while read count cat; do
        pct=$(awk "BEGIN {printf \"%.1f\", ($count * 100 / $TOTAL)}")
        printf "   %-25s %5d (%4s%%)\n" "$cat" "$count" "$pct"
    done
    echo
    
    # Recent samples
    echo "📝 LATEST 3 SAMPLES"
    echo "────────────────────────────────────────────────────────────────"
    tail -3 "$OUTPUT_FILE" | jq -r '"   " + .category + " (" + .provider + ")\n   Q: " + (.question[:70] + "...")' 2>/dev/null
    echo
    
    # System info
    echo "💻 SYSTEM STATUS"
    echo "────────────────────────────────────────────────────────────────"
    PID=$(pgrep -f "real_world_generator.py" | head -1)
    if [ -n "$PID" ]; then
        CPU=$(ps -p $PID -o %cpu --no-headers)
        MEM=$(ps -p $PID -o %mem --no-headers)
        RUNTIME=$(ps -p $PID -o etime --no-headers)
        echo "   PID: $PID | CPU: ${CPU}% | Memory: ${MEM}% | Runtime: $RUNTIME"
    else
        echo "   ⚠️  Generator process not found!"
    fi
    
    FILE_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
    echo "   Output file: $FILE_SIZE"
    echo
    echo "────────────────────────────────────────────────────────────────"
    echo "   Last updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "   Press Ctrl+C to exit dashboard"
    echo "════════════════════════════════════════════════════════════════"
    
    sleep 10
done
