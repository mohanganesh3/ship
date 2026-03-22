#!/bin/bash
set -euo pipefail

# Overnight monitor loop (read-only): watches CPT + Wave1 + teacher health.
# Never kills or restarts anything.

ROOT="/home/mohanganesh/ship"
LOG_DIR="${ROOT}/logs"
PIPELINE_LOG="${LOG_DIR}/pipeline_execution.log"

CPT_LOG="${LOG_DIR}/cpt_1.7b_train.log"
GEN_DIR="${ROOT}/ship/maritime_pipeline/data/generation"
WAVE1_LOG="${GEN_DIR}/wave1_generation.log"
WAVE1_LOG_FALLBACK="${LOG_DIR}/wave1_generation.log"
MODEA_JSONL="${GEN_DIR}/wave1_modeA_raw.jsonl"

CPT_PID_FILE="${LOG_DIR}/cpt_1.7b_train.pid"
WAVE1_PID="1724216"

TEACHER_URL="http://127.0.0.1:8000/health"

cd "${ROOT}"
mkdir -p "${LOG_DIR}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] MONITOR STATUS: STARTING" >> "${PIPELINE_LOG}"

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  CPT_ALIVE="unknown"
  if [[ -f "${CPT_PID_FILE}" ]]; then
    CPT_PID=$(cat "${CPT_PID_FILE}" || true)
    if [[ "${CPT_PID}" =~ ^[0-9]+$ ]] && kill -0 "${CPT_PID}" 2>/dev/null; then
      CPT_ALIVE="up"
    else
      CPT_ALIVE="down"
    fi
  fi

  WAVE1_ALIVE="unknown"
  if [[ "${WAVE1_PID}" =~ ^[0-9]+$ ]] && kill -0 "${WAVE1_PID}" 2>/dev/null; then
    WAVE1_ALIVE="up"
  else
    WAVE1_ALIVE="down"
  fi

  CPT_TAIL="(missing)"
  if [[ -f "${CPT_LOG}" ]]; then
    CPT_TAIL=$(tail -n 50 "${CPT_LOG}" | tr '\n' ' ' | tail -c 2000 || true)
  fi

  W1_TAIL="(missing)"
  if [[ -f "${WAVE1_LOG}" ]]; then
    W1_TAIL=$(tail -n 50 "${WAVE1_LOG}" | tr '\n' ' ' | tail -c 2000 || true)
  elif [[ -f "${WAVE1_LOG_FALLBACK}" ]]; then
    W1_TAIL=$(tail -n 50 "${WAVE1_LOG_FALLBACK}" | tr '\n' ' ' | tail -c 2000 || true)
  elif [[ -f "${MODEA_JSONL}" ]]; then
    W1_TAIL=$(tail -n 5 "${MODEA_JSONL}" | tr '\n' ' ' | tail -c 2000 || true)
  fi

  MODEA_COUNT=0
  if [[ -f "${MODEA_JSONL}" ]]; then
    MODEA_COUNT=$(grep -cve '^\s*$' "${MODEA_JSONL}" || true)
  fi

  TEACHER_OK="down"
  if curl -fsS --max-time 3 "${TEACHER_URL}" >/dev/null 2>&1; then
    TEACHER_OK="up"
  fi

  echo "[${TS}] MONITOR SUMMARY: cpt=${CPT_ALIVE} wave1=${WAVE1_ALIVE} modeA_lines=${MODEA_COUNT} teacher8000=${TEACHER_OK} cpt_tail='${CPT_TAIL}' wave1_tail='${W1_TAIL}'" >> "${PIPELINE_LOG}"

  # 30 minutes
  sleep 1800
 done
