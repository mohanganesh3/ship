#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/mohanganesh/ship"
VENV="$ROOT/.venv-train/bin/activate"
TRAIN_DIR="$ROOT/training"
DATA_DIR="$ROOT/ship/maritime_pipeline/data/final"
LOG_DIR="$ROOT/logs"

mkdir -p "$LOG_DIR"

source "$VENV"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export SHIP_SFT_DATA="${SHIP_SFT_DATA:-$DATA_DIR/sft_curated_optionc_1p7b.jsonl}"
export SHIP_SFT_TRAPS="${SHIP_SFT_TRAPS:-$DATA_DIR/sft_curated_traps_optionc_1p7b.jsonl}"
export SHIP_SFT_REPLAY_DATA="${SHIP_SFT_REPLAY_DATA:-$DATA_DIR/sft_curated.jsonl}"

cd "$TRAIN_DIR"

if [[ ! -f "$TRAIN_DIR/checkpoints/phase2-optionc-sft1-1.7b/final/adapter_model.safetensors" ]]; then
  python run_phase2_optionc_sft1_1p7b.py >> "$LOG_DIR/phase2_optionc_sft1_1p7b.log" 2>&1
fi

if [[ ! -f "$TRAIN_DIR/checkpoints/phase2-optionc-sft2-1.7b/final/adapter_model.safetensors" ]]; then
  python run_phase2_optionc_sft2_1p7b.py >> "$LOG_DIR/phase2_optionc_sft2_1p7b.log" 2>&1
fi
