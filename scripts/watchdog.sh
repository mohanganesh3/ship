#!/bin/bash
cd /home/mohanganesh/ship
LOG=logs/pipeline_execution.log

ensure_cpt_job() {
  local label="$1"
  local script="$2"
  local pidfile="$3"
  local logfile="$4"
  local gpu="$5"

  local pid=""
  if [[ -f "$pidfile" ]]; then
    pid=$(cat "$pidfile" 2>/dev/null | tr -d ' \n\t\r' || true)
  fi

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    if ps -p "$pid" -o args= 2>/dev/null | grep -q "$script"; then
      echo "[$TS] WATCHDOG: ${label} alive pid=${pid}" >> "$LOG"
      return 0
    fi
  fi

  # PID file missing/stale: try to discover an already-running process.
  local found_pid
  found_pid=$(pgrep -af "\.venv-train/bin/python ${script}" | head -n 1 | awk '{print $1}')
  if [[ -n "$found_pid" ]]; then
    echo "$found_pid" > "$pidfile"
    echo "[$TS] WATCHDOG: ${label} alive pid=${found_pid} (pidfile repaired)" >> "$LOG"
    return 0
  fi

  echo "[$TS] WATCHDOG: ${label} DEAD — restarting on GPU${gpu}" >> "$LOG"

  # NOTE: scripts default to correct GPU, but we set it explicitly to be safe.
  TOKENIZERS_PARALLELISM=false CUDA_VISIBLE_DEVICES="$gpu" \
    nohup .venv-train/bin/python "$script" >> "$logfile" 2>&1 &
  local new_pid="$!"

  # Verify we captured the right PID; fall back to discovery if needed.
  if [[ -n "$new_pid" ]] && ps -p "$new_pid" -o args= 2>/dev/null | grep -q "$script"; then
    echo "$new_pid" > "$pidfile"
  else
    found_pid=$(pgrep -af "\.venv-train/bin/python ${script}" | head -n 1 | awk '{print $1}')
    if [[ -n "$found_pid" ]]; then
      echo "$found_pid" > "$pidfile"
      new_pid="$found_pid"
    else
      echo "$new_pid" > "$pidfile"
    fi
  fi

  echo "[$TS] WATCHDOG: ${label} restarted pid=$(cat "$pidfile" 2>/dev/null)" >> "$LOG"
}

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Guard CPT (GPU) - skip if already marked complete
  if grep -q "CPT_1.7B: COMPLETE" logs/pipeline_execution.log 2>/dev/null; then
    echo "[$TS] WATCHDOG: CPT_1.7B already complete, skipping" >> $LOG
  else
    ensure_cpt_job "CPT_1.7B" "training/run_cpt_1.7b.py" "logs/cpt_1.7b_train.pid" "logs/cpt_1.7b_train.log" "0"
  fi
  
  if grep -q "CPT_4B: COMPLETE" logs/pipeline_execution.log 2>/dev/null; then
    echo "[$TS] WATCHDOG: CPT_4B already complete, skipping" >> $LOG
  else
    ensure_cpt_job "CPT_4B" "training/run_cpt_4b.py" "logs/cpt_4b_train.pid" "logs/cpt_4b_train.log" "1"
  fi

  # Guard Wave 1
  W1_PID=$(cat ship/maritime_pipeline/data/generation/wave1_generation.pid 2>/dev/null)
  MODA=$(wc -l < ship/maritime_pipeline/data/generation/wave1_modeA_raw.jsonl 2>/dev/null || echo 0)
  if [ -n "$W1_PID" ] && kill -0 "$W1_PID" 2>/dev/null; then
    echo "[$TS] WATCHDOG: Wave1 alive pid=$W1_PID modeA=$MODA" >> $LOG
  else
    echo "[$TS] WATCHDOG: Wave1 DEAD modeA=$MODA — restarting" >> $LOG
    # Default to 6 ports; override via WAVE1_PORTS if desired.
    WAVE1_PORTS=${WAVE1_PORTS:-8000,8001,8002,8003,8004,8005}
    # Default to Mode A to maximize throughput toward the >=500 curated gate.
    # Override via WAVE1_MODE (A, B, C, all) if you want full coverage.
    WAVE1_MODE=${WAVE1_MODE:-all}
    # Speed/quality knobs (lower tokens/chars -> much faster on CPU-only teachers).
    WAVE1_MAX_TOKENS=${WAVE1_MAX_TOKENS:-300}
    WAVE1_MAX_CHARS=${WAVE1_MAX_CHARS:-2000}
      WAVE1_MAX_INFLIGHT_PER_PORT=${WAVE1_MAX_INFLIGHT_PER_PORT:-3}
    export OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
    nohup .venv-train/bin/python scripts/generate_wave1.py \
      --mode "$WAVE1_MODE" \
      --ports "$WAVE1_PORTS" \
      --max-tokens "$WAVE1_MAX_TOKENS" \
      --max-chars "$WAVE1_MAX_CHARS" \
      --max-inflight-per-port "$WAVE1_MAX_INFLIGHT_PER_PORT" \
      --purge-empty-progress \
      --purge-insufficient-progress \
      --wait-for-teachers \
      --teacher-ready-poll-secs 60 \
      >> ship/maritime_pipeline/data/generation/wave1_generation.log 2>&1 &
    echo $! > ship/maritime_pipeline/data/generation/wave1_generation.pid
    echo "[$TS] WATCHDOG: Wave1 restarted pid=$(cat ship/maritime_pipeline/data/generation/wave1_generation.pid)" >> $LOG
  fi

  # Log PPL progress
  PPL=$(tail -n 1 logs/cpt_perplexity_1.7b.jsonl 2>/dev/null)
  [ -n "$PPL" ] && echo "[$TS] WATCHDOG: PPL $PPL" >> $LOG

  sleep 1800  # 30 minutes
 done
