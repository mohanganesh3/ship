#!/usr/bin/env bash
set -euo pipefail

STAMP() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

VENV_PY="/home/mohanganesh/ship/.venv/bin/python"
STUDENT_DIR="/home/mohanganesh/ship/models/student"
TEACHER_DIR="/home/mohanganesh/ship/models/teacher"
LOG_DIR="/home/mohanganesh/ship/models/logs"
PIDFILE="$LOG_DIR/download_models.pid"
LATEST_LOG_PTR="$LOG_DIR/download_models.latest_log"

mkdir -p "$LOG_DIR"

OUT_REPORT="$LOG_DIR/final_model_report_$(date -u +%Y%m%dT%H%M%SZ).txt"

{
  echo "[$(STAMP)] finalize_model_downloads starting"
  echo "PIDFILE=$PIDFILE"
  echo "LATEST_LOG_PTR=$LATEST_LOG_PTR"
  echo "OUT_REPORT=$OUT_REPORT"
} >> "$OUT_REPORT"

if [ ! -s "$PIDFILE" ]; then
  echo "[$(STAMP)] ERROR: PID file missing/empty: $PIDFILE" >> "$OUT_REPORT"
  exit 1
fi

DL_PID=$(cat "$PIDFILE" | tr -d ' \t\n\r')
if [ -z "$DL_PID" ]; then
  echo "[$(STAMP)] ERROR: PID empty" >> "$OUT_REPORT"
  exit 1
fi

# Wait for the download script to exit
while ps -p "$DL_PID" >/dev/null 2>&1; do
  echo "[$(STAMP)] waiting: download pid $DL_PID still running" >> "$OUT_REPORT"
  sleep 300
done

echo "[$(STAMP)] download pid $DL_PID finished" >> "$OUT_REPORT"

# Capture tail of download log (useful for debugging)
if [ -s "$LATEST_LOG_PTR" ]; then
  LOG=$(cat "$LATEST_LOG_PTR" | tr -d ' \t\n\r')
  if [ -n "$LOG" ] && [ -f "$LOG" ]; then
    {
      echo ""
      echo "=== latest download log (tail 80) ==="
      echo "LOG=$LOG"
      tail -n 80 "$LOG" || true
    } >> "$OUT_REPORT"
  fi
fi

{
  echo ""
  echo "=== required listings ==="
  echo ">>> ls -lh $STUDENT_DIR/"
  ls -lh "$STUDENT_DIR" || true
  echo ""
  echo ">>> ls -lh $TEACHER_DIR/"
  ls -lh "$TEACHER_DIR" || true
  echo ""
  echo "=== teacher Q4_K_M file(s) and exact sizes ==="
} >> "$OUT_REPORT"

"$VENV_PY" - <<'PY' >> "$OUT_REPORT"
import os
import glob

teacher_dir = "/home/mohanganesh/ship/models/teacher"
patterns = ["**/*Q4_K_M*.gguf", "**/*Q4_K_M*"]

paths = []
seen = set()
for pat in patterns:
    for p in glob.glob(os.path.join(teacher_dir, pat), recursive=True):
        if os.path.isfile(p) and p not in seen:
            seen.add(p)
            paths.append(p)

if not paths:
    print("NO_Q4_K_M_FILES_FOUND")
else:
    for p in sorted(paths):
        size_bytes = os.path.getsize(p)
        size_gib = size_bytes / (1024**3)
        size_gb = size_bytes / 1e9
        rel = os.path.relpath(p, teacher_dir)
        print(f"{rel}\t{size_bytes} bytes\t{size_gib:.6f} GiB\t{size_gb:.6f} GB")
PY

echo "[$(STAMP)] finalize_model_downloads done" >> "$OUT_REPORT"

echo "$OUT_REPORT" > "$LOG_DIR/final_model_report.latest"
