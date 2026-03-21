#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/home/mohanganesh/ship/.venv/bin/python"
HF_CLI="/home/mohanganesh/ship/.venv/bin/hf"

STUDENT_DIR="/home/mohanganesh/ship/models/student"
TEACHER_DIR="/home/mohanganesh/ship/models/teacher"
LOG_DIR="/home/mohanganesh/ship/models/logs"

mkdir -p "$STUDENT_DIR" "$TEACHER_DIR" "$LOG_DIR"

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "[$(stamp)] Starting model downloads"
echo "[$(stamp)] Using python: $VENV_PY"
echo "[$(stamp)] Using hf cli: $HF_CLI"

# Ensure deps are present in the venv
"$VENV_PY" -m pip install -U huggingface_hub hf_transfer

# Enable hf_transfer accelerated downloads
export HF_HUB_ENABLE_HF_TRANSFER=1
export HF_HUB_DISABLE_TELEMETRY=1

# Auth is optional for public repos; log status if available
if "$HF_CLI" auth whoami >/dev/null 2>&1; then
  echo "[$(stamp)] Hugging Face auth: logged in"
else
  echo "[$(stamp)] Hugging Face auth: not logged in (ok if repos are public)"
fi

echo "[$(stamp)] Downloading STUDENT model (small) -> $STUDENT_DIR"
"$HF_CLI" download unsloth/Qwen3-4B-Instruct-2507 \
  --local-dir "$STUDENT_DIR"

echo "[$(stamp)] Downloading TEACHER model (large, GGUF Q4_K_M only) -> $TEACHER_DIR"
"$HF_CLI" download bartowski/Qwen_Qwen3-235B-A22B-Instruct-2507-GGUF \
  --include "*Q4_K_M*" \
  --local-dir "$TEACHER_DIR"

echo "[$(stamp)] Downloads finished"

echo "[$(stamp)] Listing student files"
ls -lh "$STUDENT_DIR" || true

echo "[$(stamp)] Listing teacher files"
ls -lh "$TEACHER_DIR" || true

echo "[$(stamp)] Teacher GGUF Q4_K_M files and exact sizes"
"$VENV_PY" - <<'PY'
import os
import glob

teacher_dir = "/home/mohanganesh/ship/models/teacher"
patterns = ["**/*Q4_K_M*.gguf", "**/*Q4_K_M*"]
seen = set()
paths = []
for pat in patterns:
    for p in glob.glob(os.path.join(teacher_dir, pat), recursive=True):
        if os.path.isfile(p) and p not in seen:
            seen.add(p)
            paths.append(p)

if not paths:
    print("NO_Q4_K_M_FILES_FOUND")
    raise SystemExit(0)

for p in sorted(paths):
    size_bytes = os.path.getsize(p)
    size_gib = size_bytes / (1024**3)
    size_gb = size_bytes / 1e9
    rel = os.path.relpath(p, teacher_dir)
    print(f"{rel}\t{size_bytes} bytes\t{size_gib:.6f} GiB\t{size_gb:.6f} GB")
PY

echo "[$(stamp)] Done"
