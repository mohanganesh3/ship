#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
PID_FILE="/home/mohanganesh/ship/logs/teacher_pids.txt"
LOG_A="/home/mohanganesh/ship/logs/teacher_8000.log"
LOG_B="/home/mohanganesh/ship/logs/teacher_8001.log"

BIN="/home/mohanganesh/ship/llama.cpp/build/bin/llama-server"
MODEL_DIR="/home/mohanganesh/ship/models/teacher/Qwen_Qwen3-235B-A22B-Instruct-2507-Q4_K_M"

mkdir -p /home/mohanganesh/ship/logs

echo "[$(TS)] STEP1.2 start_teacher.sh: starting teacher instances on 8000 and 8001" | tee -a "$PIPE_LOG"

# Preflight: ensure required ports are free.
if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ':(8000|8001)$'; then
    echo "[$(TS)] ERROR: port 8000 and/or 8001 already in use. Free the ports before starting teacher servers." | tee -a "$PIPE_LOG" >&2
    ss -ltnp 2>/dev/null | grep -E ':8000|:8001' >&2 || true
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

rm -f "$PID_FILE"

start_one() {
  local port="$1" cores="$2" log_file="$3"
  # IMPORTANT: only print the PID to stdout (so command substitution captures it correctly).
  # Send log lines to the pipeline log (and stderr for human visibility) separately.
  {
    echo "[$(TS)] Starting llama-server port=$port cores=$cores threads=20 log=$log_file"
  } | tee -a "$PIPE_LOG" >&2
  # Run in background; logs go to per-port log file.
  taskset -c "$cores" "$BIN" \
    --model "$SHARD" \
    --host 127.0.0.1 \
    --port "$port" \
    --threads 20 \
    --ctx-size 8192 \
    --n-predict 300 \
    --no-repack \
    --parallel 1 \
    >>"$log_file" 2>&1 &
  echo $!
}

PID_A="$(start_one 8000 0-19 "$LOG_A")"
PID_B="$(start_one 8001 20-39 "$LOG_B")"

echo "[$(TS)] Launched: PID_A=$PID_A PID_B=$PID_B. Waiting 60s for model load..." | tee -a "$PIPE_LOG"
sleep 60

echo "$PID_A" >"$PID_FILE"
echo "$PID_B" >>"$PID_FILE"

echo "[$(TS)] Teacher PIDs written to $PID_FILE" | tee -a "$PIPE_LOG"
echo "[$(TS)] Instance A: http://127.0.0.1:8000/v1/chat/completions (PID $PID_A)" | tee -a "$PIPE_LOG"
echo "[$(TS)] Instance B: http://127.0.0.1:8001/v1/chat/completions (PID $PID_B)" | tee -a "$PIPE_LOG"
