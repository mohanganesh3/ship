#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
PID_FILE="/home/mohanganesh/ship/logs/teacher_pids.txt"

BIN="/home/mohanganesh/ship/llama.cpp/build/bin/llama-server"
MODEL_DIR="/home/mohanganesh/ship/models/teacher/Qwen_Qwen3-235B-A22B-Instruct-2507-Q4_K_M"

# Optional overrides:
# - TEACHER_PORTS: comma-separated ports to start (default: 8000,8001)
# - TEACHER_WAIT_SECS: how long to wait before returning (default: 60)
# - TEACHER_APPEND_PIDS: if set to 1, append PIDs to teacher_pids.txt instead of overwriting it
# - TEACHER_THREADS: override thread count per instance (useful when manually adding an instance)
# - TEACHER_CORES: for single-port runs, override CPU core range passed to taskset (e.g. "12-23")
PORTS_CSV="${TEACHER_PORTS:-8000,8001}"
WAIT_SECS="${TEACHER_WAIT_SECS:-60}"
APPEND_PIDS="${TEACHER_APPEND_PIDS:-0}"
THREADS_OVERRIDE="${TEACHER_THREADS:-}"
CORES_OVERRIDE="${TEACHER_CORES:-}"

mkdir -p /home/mohanganesh/ship/logs

echo "[$(TS)] STEP1.2 start_teacher.sh: starting teacher instances on ports=${PORTS_CSV}" | tee -a "$PIPE_LOG"

IFS=',' read -r -a PORTS <<<"$PORTS_CSV"
if [[ "${#PORTS[@]}" -lt 1 ]]; then
  echo "[$(TS)] ERROR: TEACHER_PORTS resulted in an empty port list" | tee -a "$PIPE_LOG" >&2
  exit 1
fi

# Preflight: ensure required ports are free.
if command -v ss >/dev/null 2>&1; then
  for port in "${PORTS[@]}"; do
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ":${port}$"; then
      echo "[$(TS)] ERROR: port ${port} already in use. Free it before starting teacher servers." | tee -a "$PIPE_LOG" >&2
      ss -ltnp 2>/dev/null | grep -E ":${port}" >&2 || true
      exit 1
    fi
  done
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

if [[ "$APPEND_PIDS" != "1" ]]; then
  rm -f "$PID_FILE"
fi

start_one() {
  local port="$1" cores="$2" log_file="$3" threads="$4"
  # IMPORTANT: only print the PID to stdout (so command substitution captures it correctly).
  # Send log lines to the pipeline log (and stderr for human visibility) separately.
  {
    echo "[$(TS)] Starting llama-server port=$port cores=$cores threads=$threads log=$log_file"
  } | tee -a "$PIPE_LOG" >&2
  # Run in background; logs go to per-port log file.
  taskset -c "$cores" "$BIN" \
    --model "$SHARD" \
    --host 127.0.0.1 \
    --port "$port" \
    --threads "$threads" \
    --ctx-size 8192 \
    --n-predict 300 \
    --no-repack \
    --parallel 1 \
    >>"$log_file" 2>&1 &
  echo $!
}

CPU_COUNT="$(nproc)"
INSTANCES="${#PORTS[@]}"
THREADS=$(( CPU_COUNT / INSTANCES ))
if [[ "$THREADS" -lt 1 ]]; then THREADS=1; fi
if [[ -n "$THREADS_OVERRIDE" ]]; then
  THREADS="$THREADS_OVERRIDE"
fi

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

declare -a PIDS
for i in "${!PORTS[@]}"; do
  port="${PORTS[$i]}"
  log_file="/home/mohanganesh/ship/logs/teacher_${port}.log"
  cores="$(core_range "$i")"
  if [[ -n "$CORES_OVERRIDE" ]] && [[ "$INSTANCES" -eq 1 ]]; then
    cores="$CORES_OVERRIDE"
  fi
  pid="$(start_one "$port" "$cores" "$log_file" "$THREADS")"
  PIDS+=("$pid")
done

echo "[$(TS)] Launched teacher instances on ports=${PORTS_CSV}. Waiting ${WAIT_SECS}s for model load..." | tee -a "$PIPE_LOG"
sleep "$WAIT_SECS"

if [[ "$APPEND_PIDS" != "1" ]]; then
  rm -f "$PID_FILE"
fi
for pid in "${PIDS[@]}"; do
  echo "$pid" >>"$PID_FILE"
done

echo "[$(TS)] Teacher PIDs written to $PID_FILE" | tee -a "$PIPE_LOG"
