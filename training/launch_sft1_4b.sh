#!/bin/bash
set -euo pipefail

export OMP_NUM_THREADS=48
export MKL_NUM_THREADS=48
export OPENBLAS_NUM_THREADS=48
export TOKENIZERS_PARALLELISM=false

cd /home/mohanganesh/ship
mkdir -p logs

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS] PHASE_2A_SFT1_4B STATUS: LAUNCHING" >> logs/pipeline_execution.log

nohup numactl --interleave=all \
  .venv-train/bin/python training/run_sft1_4b.py \
  "$@" \
  >> logs/sft1_4b_train.log 2>&1 &

echo $! > logs/sft1_4b_train.pid
PID=$(cat logs/sft1_4b_train.pid)
TS2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS2] PHASE_2A_SFT1_4B STATUS: LAUNCHED pid=${PID} log=logs/sft1_4b_train.log" >> logs/pipeline_execution.log
echo "SFT Stage 1 launched. PID: ${PID}"
