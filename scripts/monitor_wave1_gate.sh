#!/usr/bin/env bash
set -euo pipefail

# Monitor Wave1 → SuperFilter hard-only count until it reaches the curated gate.
# Intended to run alongside Wave1 generation.
#
# Env overrides:
#   WAVE1_GATE=3000               # stop when total curated >= this
#   WAVE1_MONITOR_SECS=900        # polling interval
#   WAVE1_STOP_ON_GATE=0|1        # if 1, terminate the Wave1 generator when gate is reached
#   WAVE1_OUT_DIR=/abs/path       # generation output dir
#   WAVE1_PID_FILE=/abs/path      # pid file for generator
#   VENV_PY=/abs/path/to/python   # python interpreter to run filter
#
# Behavior:
# - Runs: scripts/filter_wave1.py --hard-only --widen-hard
# - Logs status lines to logs/pipeline_execution.log
# - When gate is reached, attempts to terminate the Wave1 generator (PID file) and exits 0.

ROOT="/home/mohanganesh/ship"
PIPE_LOG="${ROOT}/logs/pipeline_execution.log"

OUT_DIR="${WAVE1_OUT_DIR:-${ROOT}/ship/maritime_pipeline/data/generation}"
PID_FILE="${WAVE1_PID_FILE:-${OUT_DIR}/wave1_generation.pid}"

GATE="${WAVE1_GATE:-3000}"
INTERVAL="${WAVE1_MONITOR_SECS:-900}"
STOP_ON_GATE="${WAVE1_STOP_ON_GATE:-0}"

VENV_PY="${VENV_PY:-${ROOT}/.venv/bin/python}"
FILTER_PY="${ROOT}/scripts/filter_wave1.py"

cd "${ROOT}"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${msg}" >> "${PIPE_LOG}" || true
}

if [[ ! -x "${VENV_PY}" ]]; then
  echo "ERROR: python not found/executable at ${VENV_PY}" >&2
  exit 2
fi
if [[ ! -f "${FILTER_PY}" ]]; then
  echo "ERROR: missing ${FILTER_PY}" >&2
  exit 2
fi

log "monitor_wave1_gate.sh: starting gate=${GATE} interval=${INTERVAL}s stop_on_gate=${STOP_ON_GATE} out_dir=${OUT_DIR}"

tmp_out="$(mktemp)"
trap 'rm -f "${tmp_out}"' EXIT

while true; do
  set +e
  "${VENV_PY}" "${FILTER_PY}" --hard-only --widen-hard >"${tmp_out}" 2>&1
  rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    log "monitor_wave1_gate.sh: filter failed rc=${rc}; will retry; tail='$(tail -n 5 "${tmp_out}" | tr '\n' ' ' | tail -c 800)'"
    sleep "${INTERVAL}"
    continue
  fi

  # Example line: counts={'A': 133, 'B': 32, 'C': 96} total=261 out=/.../sft_curated.jsonl
  total=$(grep -Eo 'total=[0-9]+' "${tmp_out}" | tail -n 1 | cut -d= -f2 || true)
  counts=$(grep -Eo "counts=\{[^}]*\}" "${tmp_out}" | tail -n 1 || true)

  if [[ -z "${total}" ]]; then
    log "monitor_wave1_gate.sh: could not parse total; raw='$(tail -n 5 "${tmp_out}" | tr '\n' ' ' | tail -c 800)'"
    sleep "${INTERVAL}"
    continue
  fi

  log "monitor_wave1_gate.sh: curated_hard_only=${total} ${counts}"

  if [[ "${total}" -ge "${GATE}" ]]; then
    log "monitor_wave1_gate.sh: GATE REACHED curated_hard_only=${total} >= ${GATE}"

    if [[ "${STOP_ON_GATE}" == "1" ]]; then
      if [[ -f "${PID_FILE}" ]]; then
        pid="$(cat "${PID_FILE}" 2>/dev/null || true)"
        if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
          log "monitor_wave1_gate.sh: stopping wave1 generator pid=${pid}"
          kill -TERM "${pid}" 2>/dev/null || true
        else
          log "monitor_wave1_gate.sh: generator pid not running (pid_file=${PID_FILE} pid=${pid})"
        fi
      else
        log "monitor_wave1_gate.sh: no pid file at ${PID_FILE}; nothing to stop"
      fi
    else
      log "monitor_wave1_gate.sh: stop_on_gate=0 (not stopping generator)"
    fi

    exit 0
  fi

  sleep "${INTERVAL}"
done
