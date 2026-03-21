#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
PID_FILE="/home/mohanganesh/ship/logs/teacher_pids.txt"

BIN="/home/mohanganesh/ship/llama.cpp/build/bin/llama-server"
MODEL_DIR="/home/mohanganesh/ship/models/teacher/Qwen_Qwen3-235B-A22B-Instruct-2507-Q4_K_M"

mkdir -p /home/mohanganesh/ship/logs

echo "[$(TS)] STEP2 start_teacher_4.sh: starting teacher instances on 8000-8003" | tee -a "$PIPE_LOG"

# Preflight: ensure required ports are free.
if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ':(8000|8001|8002|8003)$'; then
    echo "[$(TS)] ERROR: one or more ports 8000-8003 already in use. Free the ports before starting teacher servers." | tee -a "$PIPE_LOG" >&2
    ss -ltnp 2>/dev/null | grep -E ':8000|:8001|:8002|:8003' >&2 || true
    exit 1
  fi
fi

if [[ ! -x "$BIN" ]]; then
  echo "[$(TS)] ERROR: llama-server not found or not executable at $BIN" | tee -a "$PIPE_LOG" >&2
  exit 1
fi

if [[ ! -d "$MODEL_DIR" ]]; then
  echo "[$(TS)] ERROR: teacher model dir not found at $MODEL_DIR" | tee -a "$PIPE_LOG" >&2
  exit 1
fi

SHARD=""
if ls "$MODEL_DIR"/*00001-of-00004.gguf >/dev/null 2>&1; then
  SHARD="$(ls "$MODEL_DIR"/*00001-of-00004.gguf | head -n 1)"
else
  SHARD="$(ls "$MODEL_DIR"/*.gguf | sort | head -n 1)"
fi

if [[ -z "$SHARD" ]] || [[ ! -f "$SHARD" ]]; then
  echo "[$(TS)] ERROR: could not find a GGUF shard in $MODEL_DIR" | tee -a "$PIPE_LOG" >&2
  exit 1
fi

echo "[$(TS)] Using model shard: $SHARD" | tee -a "$PIPE_LOG"

CPU_COUNT="$(nproc)"
INSTANCES=4
THREADS=$(( CPU_COUNT / INSTANCES ))
if [[ "$THREADS" -lt 1 ]]; then THREADS=1; fi

# Split CPU cores into 4 contiguous blocks.
# Example: 40 cores => 0-9, 10-19, 20-29, 30-39.
block=$(( CPU_COUNT / INSTANCES ))
if [[ "$block" -lt 1 ]]; then block=1; fi

core_range() {
  local idx="$1"
  local start=$(( idx * block ))
  local end=$(( (idx+1) * block - 1 ))
  if [[ "$idx" -eq $((INSTANCES-1)) ]]; then
    end=$(( CPU_COUNT - 1 ))
  fi
  echo "${start}-${end}"
}

rm -f "$PID_FILE"

start_one() {
  local port="$1" cores="$2" log_file="$3"
  {
    echo "[$(TS)] Starting llama-server port=$port cores=$cores threads=$THREADS log=$log_file"
  } | tee -a "$PIPE_LOG" >&2

  taskset -c "$cores" "$BIN" \
    --model "$SHARD" \
    --host 127.0.0.1 \
    --port "$port" \
    --threads "$THREADS" \
    --ctx-size 8192 \
    --n-predict 300 \
    --no-repack \
    --parallel 1 \
    >>"$log_file" 2>&1 &
  echo $!
}

LOG_8000="/home/mohanganesh/ship/logs/teacher_8000.log"
LOG_8001="/home/mohanganesh/ship/logs/teacher_8001.log"
LOG_8002="/home/mohanganesh/ship/logs/teacher_8002.log"
LOG_8003="/home/mohanganesh/ship/logs/teacher_8003.log"

PID_8000="$(start_one 8000 "$(core_range 0)" "$LOG_8000")"
PID_8001="$(start_one 8001 "$(core_range 1)" "$LOG_8001")"
PID_8002="$(start_one 8002 "$(core_range 2)" "$LOG_8002")"
PID_8003="$(start_one 8003 "$(core_range 3)" "$LOG_8003")"

echo "[$(TS)] Launched: 8000=$PID_8000 8001=$PID_8001 8002=$PID_8002 8003=$PID_8003. Waiting 60s for model load..." | tee -a "$PIPE_LOG"
sleep 60

echo "$PID_8000" >"$PID_FILE"
echo "$PID_8001" >>"$PID_FILE"
echo "$PID_8002" >>"$PID_FILE"
echo "$PID_8003" >>"$PID_FILE"

echo "[$(TS)] Teacher PIDs written to $PID_FILE" | tee -a "$PIPE_LOG"
