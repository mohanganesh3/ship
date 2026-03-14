#!/bin/bash
# Launch REAL maritime data generation with multi-account support

echo "═══════════════════════════════════════════════════════════════"
echo "🚢 REAL MARITIME DATA GENERATION - MULTI-ACCOUNT"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Configuration
TARGET=500000
LOG_DIR="/home/mohanganesh/ship/logs"
SCRIPT="/home/mohanganesh/ship/scripts/multi_account_real_generator.py"
CONFIG="/home/mohanganesh/ship/accounts.json"

mkdir -p "$LOG_DIR"

# Check accounts
NUM_ACCOUNTS=$(python3 -c "import json; print(len(json.load(open('$CONFIG'))['accounts']))")
echo "📋 Configuration:"
echo "   Accounts: $NUM_ACCOUNTS API keys"
echo "   Target: $TARGET samples"
echo "   Config: $CONFIG"
echo ""

# Calculate ETA
if [ "$NUM_ACCOUNTS" -eq 3 ]; then
    RATE=6750
    HOURS=$(python3 -c "print(f'{$TARGET/$RATE:.1f}')")
    echo "⏱️  Estimated time: ~$HOURS hours (~3 days)"
elif [ "$NUM_ACCOUNTS" -eq 30 ]; then
    RATE=67500
    HOURS=$(python3 -c "print(f'{$TARGET/$RATE:.1f}')")
    echo "⏱️  Estimated time: ~$HOURS hours"
else
    RATE=$((NUM_ACCOUNTS * 2250))
    HOURS=$(python3 -c "print(f'{$TARGET/$RATE:.1f}')")
    echo "⏱️  Estimated time: ~$HOURS hours"
fi
echo ""

# Confirm
read -p "Start generation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

# Launch
LOG_FILE="$LOG_DIR/real_maritime_gen_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "🚀 Starting generation..."
nohup python3 "$SCRIPT" --target "$TARGET" > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ Started with PID: $PID"
echo "📊 Log file: $LOG_FILE"
echo ""
echo "Monitor with:"
echo "   tail -f $LOG_FILE"
echo ""
echo "Stop with:"
echo "   kill $PID"
echo ""

# Show initial output
echo "⏳ Waiting for startup..."
sleep 8

if [ -f "$LOG_FILE" ]; then
    echo "═══════════════════════════════════════════════════════════════"
    tail -30 "$LOG_FILE"
    echo "═══════════════════════════════════════════════════════════════"
fi

echo ""
echo "✅ Generation is running in background!"
echo "   PID: $PID"
echo "   Monitor: tail -f $LOG_FILE"
echo ""
