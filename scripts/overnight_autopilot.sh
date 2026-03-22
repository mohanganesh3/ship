#!/bin/bash
set -euo pipefail

# Autonomous pipeline controller (safe): advances phases when gates and artifacts are satisfied.
# Hard rules:
# - Never kill CPT/Wave1 processes if they are alive.
# - Use .venv-train for training + filtering + eval steps.
# - All phase actions append to logs/pipeline_execution.log.

ROOT="/home/mohanganesh/ship"
LOG_DIR="${ROOT}/logs"
PIPELINE_LOG="${LOG_DIR}/pipeline_execution.log"

export OMP_NUM_THREADS=48
export MKL_NUM_THREADS=48
export OPENBLAS_NUM_THREADS=48
export TOKENIZERS_PARALLELISM=false

MODEA_JSONL="${ROOT}/ship/maritime_pipeline/data/generation/wave1_modeA_raw.jsonl"
CURATED_JSONL="${ROOT}/ship/maritime_pipeline/data/final/sft_curated.jsonl"

CPT_ROOT_DIR="${ROOT}/training/checkpoints/cpt-1.7b"
SFT1_FINAL_DIR="${ROOT}/training/checkpoints/sft1-1.7b/final"
SFT2_FINAL_DIR="${ROOT}/training/checkpoints/sft2-1.7b/final"

SUPERFILTER_LOG="${LOG_DIR}/filter_wave1.log"
SUPERFILTER_PID="${LOG_DIR}/filter_wave1.pid"
SUPERFILTER_ATTEMPT_FILE="${LOG_DIR}/filter_wave1.attempt"

cd "${ROOT}"
mkdir -p "${LOG_DIR}"

utc_ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

logp() {
  echo "[$(utc_ts)] AUTOPILOT $*" >> "${PIPELINE_LOG}"
}

nonempty_lines() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo 0
    return
  fi
  grep -cve '^\s*$' "$f" 2>/dev/null || echo 0
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

file_has() {
  local f="$1"
  local s="$2"
  [[ -f "$f" ]] && grep -Fq "$s" "$f"
}

latest_cpt_checkpoint_dir() {
  # Prefer final/ else highest checkpoint-N under CPT_ROOT_DIR
  if [[ -d "${CPT_ROOT_DIR}/final" ]]; then
    echo "${CPT_ROOT_DIR}/final"
    return
  fi
  local best
  best=$(ls -d "${CPT_ROOT_DIR}"/checkpoint-* 2>/dev/null | sort -t'-' -k2,2n | tail -n 1 || true)
  if [[ -n "${best}" ]] && [[ -d "${best}" ]]; then
    echo "${best}"
    return
  fi
  echo ""
}

cpt_gate_pass() {
  # Returns 0 if gate PASS based on perplexity log.
  if [[ ! -f "${LOG_DIR}/cpt_perplexity_1.7b.jsonl" ]]; then
    return 1
  fi
  .venv-train/bin/python - << 'PY'
import json
from pathlib import Path
p = Path('logs/cpt_perplexity_1.7b.jsonl')
lines = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
if len(lines) < 2:
    raise SystemExit(1)
bm, bg = lines[0]['maritime_ppl'], lines[0]['general_ppl']
lm, lg = lines[-1]['maritime_ppl'], lines[-1]['general_ppl']
mdrop = (bm - lm) / bm * 100
grise = (lg - bg) / bg * 100
raise SystemExit(0 if (mdrop >= 15 and grise <= 10) else 1)
PY
}

start_superfilter() {
  local attempt="$1"
  local args=("scripts/filter_wave1.py")

  if [[ "$attempt" == "1" ]]; then
    args+=("--ifd-min" "0.05" "--ifd-max" "0.95" "--very-low-keep" "500")
  elif [[ "$attempt" == "2" ]]; then
    args+=("--ifd-min" "0.01" "--ifd-max" "0.99" "--very-low-keep" "1500")
  else
    args+=("--ifd-min" "0.01" "--ifd-max" "0.99" "--very-low-keep" "2500")
  fi

  logp "SUPERFILTER: STARTING attempt=${attempt} args='${args[*]}'"

  nohup numactl --interleave=all \
    .venv-train/bin/python "${args[@]}" \
    >> "${SUPERFILTER_LOG}" 2>&1 &

  echo $! > "${SUPERFILTER_PID}"
  echo "${attempt}" > "${SUPERFILTER_ATTEMPT_FILE}"

  logp "SUPERFILTER: LAUNCHED pid=$(cat "${SUPERFILTER_PID}") log=${SUPERFILTER_LOG} attempt=${attempt}"
}

logp "STATUS: STARTING"

while true; do
  # ---- Wave1 -> curated dataset (SuperFilter) ----
  MODEA_COUNT=$(nonempty_lines "${MODEA_JSONL}")
  CURATED_COUNT=$(nonempty_lines "${CURATED_JSONL}")

  # Check if superfilter is already running
  SF_PID=""
  if [[ -f "${SUPERFILTER_PID}" ]]; then
    SF_PID=$(cat "${SUPERFILTER_PID}" || true)
  fi

  if pid_alive "${SF_PID}"; then
    logp "SUPERFILTER: RUNNING pid=${SF_PID} modeA_lines=${MODEA_COUNT} curated_lines=${CURATED_COUNT}"
  else
    # If we have enough ModeA and curated is missing/small, launch SuperFilter.
    if [[ "${MODEA_COUNT}" -ge 5000 ]] && [[ "${CURATED_COUNT}" -lt 3000 ]]; then
      attempt="1"
      if [[ -f "${SUPERFILTER_ATTEMPT_FILE}" ]]; then
        attempt=$(cat "${SUPERFILTER_ATTEMPT_FILE}" || echo "1")
      fi

      # If we already attempted and output is still low, increment attempt.
      if [[ "${CURATED_COUNT}" -gt 0 ]] && [[ "${CURATED_COUNT}" -lt 3000 ]]; then
        if [[ "${attempt}" -lt 3 ]]; then
          attempt=$((attempt + 1))
        fi
      fi

      if [[ "${attempt}" -le 3 ]]; then
        start_superfilter "${attempt}"
      else
        logp "SUPERFILTER: WARNING attempt_exhausted curated_lines=${CURATED_COUNT} (need >=3000)"
      fi
    fi
  fi

  # ---- SFT1 ----
  CPT_BEST_DIR=$(latest_cpt_checkpoint_dir)
  CPT_PASS=false
  if cpt_gate_pass; then
    CPT_PASS=true
  fi

  if [[ -n "${CPT_BEST_DIR}" ]] && [[ "${CPT_PASS}" == "true" ]] && [[ "${CURATED_COUNT}" -ge 3000 ]]; then
    if [[ ! -d "${SFT1_FINAL_DIR}" ]]; then
      # Only launch if no existing PID seems alive
      SFT1_PID_FILE="${LOG_DIR}/sft1_1.7b_train.pid"
      SFT1_PID=""
      if [[ -f "${SFT1_PID_FILE}" ]]; then
        SFT1_PID=$(cat "${SFT1_PID_FILE}" || true)
      fi
      if pid_alive "${SFT1_PID}"; then
        logp "PHASE_2A_SFT1_1.7B STATUS: RUNNING pid=${SFT1_PID}"
      else
        logp "PHASE_2A_SFT1_1.7B STATUS: LAUNCHING via training/launch_sft1_1.7b.sh cpt_best=${CPT_BEST_DIR} curated_lines=${CURATED_COUNT}"
        (cd "${ROOT}" && bash training/launch_sft1_1.7b.sh) || logp "PHASE_2A_SFT1_1.7B STATUS: WARNING launch_failed"
      fi
    fi
  fi

  # If SFT1 gate failed, re-run once with --extra-epoch (if not already attempted)
  if file_has "${PIPELINE_LOG}" "PHASE_2A_SFT1_1.7B GATE: FAIL"; then
    EXTRA_MARK="${LOG_DIR}/sft1_1.7b.extra_epoch_rerun"
    if [[ ! -f "${EXTRA_MARK}" ]]; then
      logp "PHASE_2A_SFT1_1.7B STATUS: RETRY extra_epoch"
      (cd "${ROOT}" && bash training/launch_sft1_1.7b.sh --extra-epoch) || true
      touch "${EXTRA_MARK}"
    fi
  fi

  # ---- SFT2 ----
  if [[ -d "${SFT1_FINAL_DIR}" ]] && file_has "${PIPELINE_LOG}" "PHASE_2A_SFT1_1.7B GATE: PASS" && [[ "${CURATED_COUNT}" -ge 3000 ]]; then
    if [[ ! -d "${SFT2_FINAL_DIR}" ]]; then
      SFT2_PID_FILE="${LOG_DIR}/sft2_1.7b_train.pid"
      SFT2_PID=""
      if [[ -f "${SFT2_PID_FILE}" ]]; then
        SFT2_PID=$(cat "${SFT2_PID_FILE}" || true)
      fi
      if pid_alive "${SFT2_PID}"; then
        logp "PHASE_2B_SFT2_1.7B STATUS: RUNNING pid=${SFT2_PID}"
      else
        logp "PHASE_2B_SFT2_1.7B STATUS: LAUNCHING via training/launch_sft2_1.7b.sh"
        (cd "${ROOT}" && bash training/launch_sft2_1.7b.sh) || logp "PHASE_2B_SFT2_1.7B STATUS: WARNING launch_failed"
      fi
    fi
  fi

  # ---- On-policy / correction / ORPO / quantize / final eval ----
  # These phases are intentionally conservative here: they can be enabled once SFT2 has a clear gate PASS in logs.
  if [[ -d "${SFT2_FINAL_DIR}" ]] && file_has "${PIPELINE_LOG}" "PHASE_2B_SFT2_1.7B GATE: PASS"; then
    # On-policy
    ONP_COMPLETE=false
    if file_has "${PIPELINE_LOG}" "PHASE_3_ONPOLICY_1.7B STATUS: COMPLETE"; then
      ONP_COMPLETE=true
    fi

    ONP_PID_FILE="${LOG_DIR}/onpolicy_1.7b_train.pid"
    ONP_PID=""
    if [[ -f "${ONP_PID_FILE}" ]]; then
      ONP_PID=$(cat "${ONP_PID_FILE}" || true)
    fi
    if ! pid_alive "${ONP_PID}"; then
      if [[ "${ONP_COMPLETE}" != "true" ]]; then
        # Require teacher health before launching
        if curl -fsS --max-time 3 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
          logp "PHASE_3_ONPOLICY_1.7B STATUS: LAUNCHING via training/launch_onpolicy_1.7b.sh"
          (cd "${ROOT}" && bash training/launch_onpolicy_1.7b.sh) || logp "PHASE_3_ONPOLICY_1.7B STATUS: WARNING launch_failed"
        else
          logp "PHASE_3_ONPOLICY_1.7B STATUS: WAITING teacher8000_down"
        fi
      fi
    fi

    # Correction SFT
    CORR_FINAL_DIR="${ROOT}/training/checkpoints/correction-1.7b/final"
    CORRECTIONS_DATA="${ROOT}/ship/maritime_pipeline/data/final/sft_corrections_1.7b.jsonl"
    if [[ "${ONP_COMPLETE}" == "true" ]] && [[ -f "${CORRECTIONS_DATA}" ]] && [[ ! -d "${CORR_FINAL_DIR}" ]]; then
      CORR_PID_FILE="${LOG_DIR}/correction_1.7b_train.pid"
      CORR_PID=""
      if [[ -f "${CORR_PID_FILE}" ]]; then
        CORR_PID=$(cat "${CORR_PID_FILE}" || true)
      fi
      if ! pid_alive "${CORR_PID}"; then
        logp "PHASE_4_CORRECTION_1.7B STATUS: LAUNCHING training/run_correction_1.7b.py"
        nohup numactl --interleave=all \
          .venv-train/bin/python training/run_correction_1.7b.py \
          >> "${LOG_DIR}/correction_1.7b_train.log" 2>&1 &
        echo $! > "${CORR_PID_FILE}"
        logp "PHASE_4_CORRECTION_1.7B STATUS: LAUNCHED pid=$(cat "${CORR_PID_FILE}") log=${LOG_DIR}/correction_1.7b_train.log"
      fi
    fi

    # ORPO
    ORPO_FINAL_DIR="${ROOT}/training/checkpoints/orpo-1.7b/final"
    ORPO_PAIRS_DATA="${ROOT}/ship/maritime_pipeline/data/final/orpo_pairs_1.7b.jsonl"
    if [[ -d "${CORR_FINAL_DIR}" ]] && [[ -f "${ORPO_PAIRS_DATA}" ]] && [[ ! -d "${ORPO_FINAL_DIR}" ]]; then
      ORPO_PID_FILE="${LOG_DIR}/orpo_1.7b_train.pid"
      ORPO_PID=""
      if [[ -f "${ORPO_PID_FILE}" ]]; then
        ORPO_PID=$(cat "${ORPO_PID_FILE}" || true)
      fi
      if ! pid_alive "${ORPO_PID}"; then
        logp "PHASE_5_ORPO_1.7B STATUS: LAUNCHING via training/launch_orpo_1.7b.sh"
        (cd "${ROOT}" && bash training/launch_orpo_1.7b.sh) || logp "PHASE_5_ORPO_1.7B STATUS: WARNING launch_failed"
      fi
    fi

    # Quantize + final eval (run once ORPO final exists)
    if [[ -d "${ORPO_FINAL_DIR}" ]]; then
      if ! file_has "${PIPELINE_LOG}" "PHASE_5_QUANTIZE_1.7B STATUS: STARTING"; then
        logp "PHASE_5_QUANTIZE_1.7B STATUS: LAUNCHING training/quantize_1.7b.py"
        nohup numactl --interleave=all \
          .venv-train/bin/python training/quantize_1.7b.py \
          >> "${LOG_DIR}/quantize_1.7b.log" 2>&1 &
      fi

      if ! file_has "${PIPELINE_LOG}" "FINAL_EVAL STATUS: STARTING"; then
        logp "FINAL_EVAL STATUS: LAUNCHING training/run_final_eval.py"
        nohup numactl --interleave=all \
          .venv-train/bin/python training/run_final_eval.py \
          >> "${LOG_DIR}/final_eval.log" 2>&1 &
      fi
    fi
  fi

  # Tick every 10 minutes
  sleep 600
 done
