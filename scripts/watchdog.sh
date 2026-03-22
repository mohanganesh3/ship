#!/bin/bash
cd /home/mohanganesh/ship
LOG=logs/pipeline_execution.log

while true; do
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Guard CPT
  CPT_PID=$(cat logs/cpt_1.7b_train.pid 2>/dev/null)
  if [ -n "$CPT_PID" ] && kill -0 "$CPT_PID" 2>/dev/null; then
    echo "[$TS] WATCHDOG: CPT alive pid=$CPT_PID" >> $LOG
  else
    echo "[$TS] WATCHDOG: CPT DEAD — restarting" >> $LOG
    export OMP_NUM_THREADS=48 MKL_NUM_THREADS=48 TOKENIZERS_PARALLELISM=false
    nohup numactl --interleave=all .venv-train/bin/python training/run_cpt_1.7b.py >> logs/cpt_1.7b_train.log 2>&1 &
    echo $! > logs/cpt_1.7b_train.pid
    echo "[$TS] WATCHDOG: CPT restarted pid=$(cat logs/cpt_1.7b_train.pid)" >> $LOG
  fi

  # Guard Wave 1
  W1_PID=$(cat ship/maritime_pipeline/data/generation/wave1_generation.pid 2>/dev/null)
  MODA=$(wc -l < ship/maritime_pipeline/data/generation/wave1_modeA_raw.jsonl 2>/dev/null || echo 0)
  if [ -n "$W1_PID" ] && kill -0 "$W1_PID" 2>/dev/null; then
    echo "[$TS] WATCHDOG: Wave1 alive pid=$W1_PID modeA=$MODA" >> $LOG
  else
    echo "[$TS] WATCHDOG: Wave1 DEAD modeA=$MODA — restarting" >> $LOG
    export OMP_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
    nohup .venv/bin/python scripts/generate_wave1.py --mode all --ports 8000,8001,8002,8003 >> ship/maritime_pipeline/data/generation/wave1_generation.log 2>&1 &
    echo $! > ship/maritime_pipeline/data/generation/wave1_generation.pid
    echo "[$TS] WATCHDOG: Wave1 restarted pid=$(cat ship/maritime_pipeline/data/generation/wave1_generation.pid)" >> $LOG
  fi

  # Log PPL progress
  PPL=$(tail -n 1 logs/cpt_perplexity_1.7b.jsonl 2>/dev/null)
  [ -n "$PPL" ] && echo "[$TS] WATCHDOG: PPL $PPL" >> $LOG

  sleep 1800  # 30 minutes
 done
