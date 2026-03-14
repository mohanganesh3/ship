#!/bin/bash
# Launch FAST comprehensive generation (500K samples in 24-48 hours)

echo "🚢 COMPREHENSIVE MARITIME DATA GENERATION - FAST MODE"
echo "======================================================="
echo ""

# Stop existing slow generation if running
if ps aux | grep -q "[c]omprehensive_maritime_generator.py"; then
    OLD_PID=$(ps aux | grep "[c]omprehensive_maritime_generator.py" | awk '{print $2}')
    echo "⚠️  Stopping existing generation (PID: $OLD_PID)..."
    kill $OLD_PID 2>/dev/null
    sleep 2
fi

# Directories
LOG_DIR="/home/mohanganesh/ship/logs"
DATA_DIR="/home/mohanganesh/ship/training/comprehensive_data_fast"
SCRIPT="/home/mohanganesh/ship/scripts/comprehensive_fast.py"

mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"

LOG_FILE="$LOG_DIR/fast_generation_$(date +%Y%m%d_%H%M%S).log"

echo "📋 Configuration:"
echo "   Workers: 15 parallel (5 per API)"
echo "   Target: 500,000 samples"
echo "   APIs: Google Gemini + Cerebras + Groq"
echo "   Output: $DATA_DIR/maritime_qa_comprehensive.jsonl"
echo "   Log: $LOG_FILE"
echo ""

# Start generation
echo "🚀 Starting fast generation..."
nohup python3 "$SCRIPT" > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ Started with PID: $PID"
echo ""
echo "📊 Monitor progress:"
echo "   tail -f $LOG_FILE"
echo "   python3 /home/mohanganesh/ship/scripts/monitor_comprehensive.py"
echo ""
echo "🛑 To stop:"
echo "   kill $PID"
echo ""

# Wait for startup
echo "⏳ Waiting for startup..."
sleep 5

# Show initial output
if [ -f "$LOG_FILE" ]; then
    echo "=== Initial Output ==="
    tail -30 "$LOG_FILE"
    echo ""
fi

echo "======================================================="
echo "✅ Fast generation is running!"
echo "Expected completion: 24-48 hours"
echo "Expected rate: 5,000-10,000 samples/hour"
echo "======================================================="
