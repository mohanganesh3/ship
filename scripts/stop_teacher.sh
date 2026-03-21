#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
PID_FILE="/home/mohanganesh/ship/logs/teacher_pids.txt"

echo "[$(TS)] stop_teacher.sh: stopping teacher instances" | tee -a "$PIPE_LOG"

if [[ ! -f "$PID_FILE" ]]; then
  echo "[$(TS)] No PID file found at $PID_FILE; nothing to stop." | tee -a "$PIPE_LOG"
  exit 0
fi

mapfile -t PIDS < "$PID_FILE" || true
if [[ ${#PIDS[@]} -eq 0 ]]; then
  echo "[$(TS)] PID file empty; nothing to stop." | tee -a "$PIPE_LOG"
  rm -f "$PID_FILE"
  exit 0
fi

for pid in "${PIDS[@]}"; do
  [[ -z "$pid" ]] && continue
  if kill -0 "$pid" 2>/dev/null; then
    echo "[$(TS)] Sending SIGTERM to PID $pid" | tee -a "$PIPE_LOG"
    kill "$pid" 2>/dev/null || true
  else
    echo "[$(TS)] PID $pid not running" | tee -a "$PIPE_LOG"
  fi
done

# Give them time to exit gracefully.
sleep 10

for pid in "${PIDS[@]}"; do
  [[ -z "$pid" ]] && continue
  if kill -0 "$pid" 2>/dev/null; then
    echo "[$(TS)] PID $pid still running; sending SIGKILL" | tee -a "$PIPE_LOG"
    kill -9 "$pid" 2>/dev/null || true
  fi
done

rm -f "$PID_FILE"
echo "[$(TS)] Teacher instances stopped; removed $PID_FILE" | tee -a "$PIPE_LOG"
