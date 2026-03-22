#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
OUT_DIR="/home/mohanganesh/ship/ship/maritime_pipeline/data/generation"
ROOT="/home/mohanganesh/ship"

mkdir -p "$OUT_DIR" /home/mohanganesh/ship/logs

echo "[$(TS)] STEP2 run_wave1_generation.sh: launching Wave1 generation (modes A,B,C)" | tee -a "$PIPE_LOG"

echo "[$(TS)] NOTE: This is a long-running job. Logs: $OUT_DIR/wave1_generation.log" | tee -a "$PIPE_LOG"

# Default to 4 ports if the user started 4 instances; otherwise set PORTS env to 8000,8001.
PORTS="${PORTS:-8000,8001,8002,8003}"

# Prefer the dedicated training environment (per runbook); fall back only if missing.
PY_TRAIN="${ROOT}/.venv-train/bin/python"
PY_FALLBACK="${ROOT}/.venv/bin/python"
PY="${PY_TRAIN}"
if [[ ! -x "${PY}" ]]; then
  PY="${PY_FALLBACK}"
  echo "[$(TS)] WARN: .venv-train not found/executable; falling back to ${PY_FALLBACK}" | tee -a "$PIPE_LOG"
fi

nohup "${PY}" /home/mohanganesh/ship/scripts/generate_wave1.py \
  --mode all \
  --ports "$PORTS" \
  --out-dir "$OUT_DIR" \
  --max-tokens 350 \
  --max-chars 5000 \
  --max-inflight-per-port 1 \
  >>"$OUT_DIR/wave1_generation.log" 2>&1 &

echo $! >"$OUT_DIR/wave1_generation.pid"

echo "[$(TS)] Wave1 generation PID: $(cat "$OUT_DIR/wave1_generation.pid")" | tee -a "$PIPE_LOG"
