#!/bin/bash
set -euo pipefail

export OMP_NUM_THREADS=48
export MKL_NUM_THREADS=48
export OPENBLAS_NUM_THREADS=48
export TOKENIZERS_PARALLELISM=false

cd /home/mohanganesh/ship
mkdir -p logs

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS] PHASE_2B_SFT2_1.7B STATUS: LAUNCHING" >> logs/pipeline_execution.log

nohup numactl --interleave=all \
  .venv-train/bin/python training/run_sft2_1.7b.py \
  >> logs/sft2_1.7b_train.log 2>&1 &

echo $! > logs/sft2_1.7b_train.pid
PID=$(cat logs/sft2_1.7b_train.pid)
TS2=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "[$TS2] PHASE_2B_SFT2_1.7B STATUS: LAUNCHED pid=${PID} log=logs/sft2_1.7b_train.log" >> logs/pipeline_execution.log
echo "SFT Stage 2 launched. PID: ${PID}"
