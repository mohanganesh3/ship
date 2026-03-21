#!/bin/bash
set -euo pipefail

export OMP_NUM_THREADS=48
export MKL_NUM_THREADS=48
export OPENBLAS_NUM_THREADS=48
export TOKENIZERS_PARALLELISM=false

cd /home/mohanganesh/ship
mkdir -p logs

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS] PHASE_3_ONPOLICY_1.7B STATUS: LAUNCHING" >> logs/pipeline_execution.log

nohup numactl --interleave=all \
  .venv-train/bin/python training/run_onpolicy_1.7b.py \
  >> logs/onpolicy_1.7b.log 2>&1 &

echo $! > logs/onpolicy_1.7b.pid
PID=$(cat logs/onpolicy_1.7b.pid)
TS2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS2] PHASE_3_ONPOLICY_1.7B STATUS: LAUNCHED pid=${PID} log=logs/onpolicy_1.7b.log" >> logs/pipeline_execution.log
echo "On-policy launched. PID: ${PID}"
