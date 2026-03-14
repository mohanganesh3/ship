#!/bin/bash
# Start comprehensive maritime data generation
# This runs in the background and logs to a file

LOG_DIR="/home/mohanganesh/ship/logs"
DATA_DIR="/home/mohanganesh/ship/training/comprehensive_data"
SCRIPT="/home/mohanganesh/ship/scripts/comprehensive_maritime_generator.py"

mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

LOG_FILE="$LOG_DIR/comprehensive_generation_$(date +%Y%m%d_%H%M%S).log"

echo "Starting comprehensive maritime data generation..."
echo "Log file: $LOG_FILE"
echo "Output dir: $DATA_DIR"
echo ""
echo "Monitor with: tail -f $LOG_FILE"
echo ""

# Run in background with nohup
nohup python3 "$SCRIPT" > "$LOG_FILE" 2>&1 &
PID=$!

echo "✓ Started with PID: $PID"
echo "✓ To stop: kill $PID"
echo ""
echo "Waiting 5 seconds for startup..."
sleep 5

# Show initial output
echo "=== Initial Output ==="
tail -30 "$LOG_FILE"
echo ""
echo "=== Generation is running in background ==="
echo "Monitor: tail -f $LOG_FILE"
echo "Stop: kill $PID"
