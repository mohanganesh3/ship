#!/usr/bin/env bash
set -euo pipefail

TS() { date -u +%Y-%m-%dT%H:%M:%SZ; }

PIPE_LOG="/home/mohanganesh/ship/logs/pipeline_execution.log"
OUT_DIR="/home/mohanganesh/ship/ship/maritime_pipeline/data/generation"
ROOT="/home/mohanganesh/ship"

mkdir -p "$OUT_DIR" /home/mohanganesh/ship/logs

echo "[$(TS)] STEP2 run_wave1_generation.sh: launching Wave1 generation (modes A,B,C)" | tee -a "$PIPE_LOG"

echo "[$(TS)] NOTE: This is a long-running job. Logs: $OUT_DIR/wave1_generation.log" | tee -a "$PIPE_LOG"

# Default to the 2 standard ports. If you started additional teacher instances,
# override with e.g. PORTS=8000,8001,8002,8003.
PORTS="${PORTS:-8000,8001}"

# Generation sizing (can be overridden via env to trade off throughput vs. answer length).
MAX_TOKENS="${WAVE1_MAX_TOKENS:-350}"
MAX_CHARS="${WAVE1_MAX_CHARS:-5000}"
MAX_INFLIGHT_PER_PORT="${WAVE1_MAX_INFLIGHT_PER_PORT:-1}"

# Optional repair modes (set to 1 to enable):
#   WAVE1_PURGE_EMPTY=1         -> drop progress keys that produced empty responses
#   WAVE1_PURGE_INSUFFICIENT=1  -> drop progress keys that produced INSUFFICIENT_SOURCE
PURGE_ARGS=()
if [[ "${WAVE1_PURGE_EMPTY:-0}" == "1" ]]; then
  PURGE_ARGS+=("--purge-empty-progress")
fi
if [[ "${WAVE1_PURGE_INSUFFICIENT:-0}" == "1" ]]; then
  PURGE_ARGS+=("--purge-insufficient-progress")
fi

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
  --wait-for-teachers \
  --max-tokens "${MAX_TOKENS}" \
  --max-chars "${MAX_CHARS}" \
  --max-inflight-per-port "${MAX_INFLIGHT_PER_PORT}" \
  "${PURGE_ARGS[@]}" \
  >>"$OUT_DIR/wave1_generation.log" 2>&1 &

echo $! >"$OUT_DIR/wave1_generation.pid"

echo "[$(TS)] Wave1 generation PID: $(cat "$OUT_DIR/wave1_generation.pid")" | tee -a "$PIPE_LOG"
