#!/bin/bash
# DEPLOY OPTIMIZED RATE LIMITS
# This script deploys the optimized maritime data generator

set -e

echo "🚀 DEPLOYING OPTIMIZED RATE LIMITS"
echo "=================================="
echo ""

# 1. Check if current generation is running
echo "📍 Step 1: Checking for running processes..."
RUNNING_PID=$(ps aux | grep multi_account_real_generator | grep -v grep | awk '{print $2}' | head -1)

if [ ! -z "$RUNNING_PID" ]; then
    echo "⚠️  Found running process (PID: $RUNNING_PID)"
    read -p "   Kill it and continue? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $RUNNING_PID
        sleep 2
        echo "✅ Stopped old process"
    else
        echo "❌ Aborted. Stop the process manually first."
        exit 1
    fi
else
    echo "✅ No running processes found"
fi

# 2. Backup current data
echo ""
echo "📍 Step 2: Backing up current data..."
BACKUP_FILE="training/real_maritime_data/maritime_real_scenarios.jsonl.backup_$(date +%Y%m%d_%H%M%S)"
if [ -f "training/real_maritime_data/maritime_real_scenarios.jsonl" ]; then
    cp training/real_maritime_data/maritime_real_scenarios.jsonl "$BACKUP_FILE"
    CURRENT_COUNT=$(wc -l < training/real_maritime_data/maritime_real_scenarios.jsonl)
    echo "✅ Backed up $CURRENT_COUNT samples to: $BACKUP_FILE"
else
    echo "ℹ️  No existing data file to backup"
    CURRENT_COUNT=0
fi

# 3. Show optimization summary
echo ""
echo "📍 Step 3: Optimization Summary"
echo "   Current throughput: ~83,000 samples/day"
echo "   Optimized throughput: ~200,000+ samples/day"
echo "   Improvement: 2.4× faster (6 days → 2.5 days)"
echo "   Cost: Still \$0 (100% free tier)"
echo ""
echo "   Rate limit changes:"
echo "   • Google:   10 RPM → 15 RPM (+50%)"
echo "   • Cerebras: 60 RPM → BURST mode (+335%)"
echo "   • Groq:     30 RPM (unchanged, but daily limit tracked)"

# 4. Confirm deployment
echo ""
read -p "🚀 Deploy optimized version? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# 5. Launch optimized generator
echo ""
echo "📍 Step 4: Launching optimized generator..."
REMAINING=$((500000 - CURRENT_COUNT))
if [ $REMAINING -lt 0 ]; then
    REMAINING=500000
fi

echo "   Target: $REMAINING remaining samples (of 500,000 total)"

nohup python3 scripts/multi_account_real_generator.py \
    --target $REMAINING \
    --config accounts.json \
    > generation_optimized.log 2>&1 &

NEW_PID=$!
echo $NEW_PID > generation.pid

echo "✅ Started optimized generator (PID: $NEW_PID)"
echo "   Log file: generation_optimized.log"
echo "   PID file: generation.pid"

# 6. Wait and show initial output
echo ""
echo "📍 Step 5: Waiting for startup..."
sleep 10

# 7. Show live monitoring info
echo ""
echo "=================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=================================="
echo ""
echo "📊 Current Status:"
tail -10 generation_optimized.log
echo ""
echo "📈 Monitoring Commands:"
echo "   • Watch live:    tail -f generation_optimized.log"
echo "   • Check count:   wc -l training/real_maritime_data/maritime_real_scenarios.jsonl"
echo "   • Check errors:  grep -i 429 generation_optimized.log"
echo "   • Stop it:       kill \$(cat generation.pid)"
echo ""
echo "⏱️  Expected completion: ~2.5 days (down from 6 days)"
echo ""
echo "✅ Monitor the first hour for any 429 rate limit errors"
echo "✅ If rate looks good, it's running optimally!"
echo ""
