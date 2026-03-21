#!/bin/bash
set -euo pipefail

export OMP_NUM_THREADS=48
export MKL_NUM_THREADS=48
export OPENBLAS_NUM_THREADS=48
export TOKENIZERS_PARALLELISM=false

cd /home/mohanganesh/ship

mkdir -p logs training/checkpoints/cpt-1.7b

echo "=============================================="
echo "  CPT 1.7B — CPU-ONLY DRY RUN (20 steps)"
echo "=============================================="

numactl --interleave=all \
  .venv-train/bin/python training/run_cpt_1.7b.py --dry-run \
  2>&1 | tee logs/cpt_1.7b_dryrun.log

if grep -q "DRY_RUN PASS" logs/cpt_1.7b_dryrun.log; then
  echo "DRY RUN PASSED. Starting full training..."
else
  echo "DRY RUN FAILED. Check logs/cpt_1.7b_dryrun.log"
  exit 1
fi

echo "=============================================="
echo "  CPT 1.7B — FULL TRAINING (nohup, runs for days)"
echo "=============================================="

nohup numactl --interleave=all \
  .venv-train/bin/python training/run_cpt_1.7b.py \
  >> logs/cpt_1.7b_train.log 2>&1 &

echo $! > logs/cpt_1.7b_train.pid
echo "Training launched. PID: $(cat logs/cpt_1.7b_train.pid)"
echo "Monitor: tail -f logs/cpt_1.7b_train.log"
echo "Perplexity: tail -f logs/cpt_perplexity_1.7b.jsonl"
