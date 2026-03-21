#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="/home/mohanganesh/ship/ship/maritime_pipeline/data/generation"
PID_FILE="$OUT_DIR/wave1_generation.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file found at $PID_FILE"
  exit 1
fi

PID="$(cat "$PID_FILE")"

echo "Wave1 generation PID: $PID"

echo "--- Process ---"
ps -p "$PID" -o pid,etimes,cmd || true

echo "--- Outputs (line counts) ---"
for f in "$OUT_DIR"/wave1_mode*_raw.jsonl; do
  [[ -f "$f" ]] || continue
  echo -n "$(basename "$f"): "
  wc -l "$f" | awk '{print $1}'
done

echo "--- Recent log ---"
tail -n 50 "$OUT_DIR/wave1_generation.log" || true
