#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/home/mohanganesh/ship/.venv/bin/python"

STUDENT_DIR="/home/mohanganesh/ship/models/student"
TEACHER_DIR="/home/mohanganesh/ship/models/teacher"
PROGRESS_LOG="/home/mohanganesh/ship/models/logs/download_progress.log"
DOWNLOAD_LOG_LATEST="/home/mohanganesh/ship/models/logs/download_models.latest_log"

stamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

echo "[$(stamp)] status report"

echo "--- processes ---"
if [ -f /home/mohanganesh/ship/models/logs/download_models.pid ]; then
  DL_PID=$(cat /home/mohanganesh/ship/models/logs/download_models.pid || true)
  if [ -n "${DL_PID:-}" ]; then
    ps -p "$DL_PID" -o pid,etime,cmd || echo "download_models.sh not running"
  fi
fi
if [ -f /home/mohanganesh/ship/models/logs/monitor_progress.pid ]; then
  MON_PID=$(cat /home/mohanganesh/ship/models/logs/monitor_progress.pid || true)
  if [ -n "${MON_PID:-}" ]; then
    ps -p "$MON_PID" -o pid,etime,cmd || echo "monitor not running"
  fi
fi

echo "--- directory sizes ---"
du -sh "$STUDENT_DIR" "$TEACHER_DIR" 2>/dev/null || true

echo "--- remaining GB (latest) ---"
if [ -f "$PROGRESS_LOG" ]; then
  tail -n 1 "$PROGRESS_LOG" || true
else
  echo "No progress log yet: $PROGRESS_LOG"
fi

echo "--- required listings ---"
echo ">>> ls -lh /home/mohanganesh/ship/models/student/"
ls -lh "$STUDENT_DIR" 2>/dev/null || true

echo ">>> ls -lh /home/mohanganesh/ship/models/teacher/"
ls -lh "$TEACHER_DIR" 2>/dev/null || true

echo "--- teacher Q4_K_M file(s) and exact sizes (when present) ---"
"$VENV_PY" - <<'PY'
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
    print("NO_Q4_K_M_FILES_FOUND_YET")
    raise SystemExit(0)

for p in sorted(paths):
    size_bytes = os.path.getsize(p)
    size_gib = size_bytes / (1024**3)
    size_gb = size_bytes / 1e9
    rel = os.path.relpath(p, teacher_dir)
    print(f"{rel}\t{size_bytes} bytes\t{size_gib:.6f} GiB\t{size_gb:.6f} GB")
PY

echo "--- latest download log tail ---"
if [ -f "$DOWNLOAD_LOG_LATEST" ]; then
  LOG=$(cat "$DOWNLOAD_LOG_LATEST" || true)
  if [ -n "${LOG:-}" ] && [ -f "$LOG" ]; then
    echo "LOG=$LOG"
    tail -n 20 "$LOG" || true
  else
    echo "No latest download log found"
  fi
else
  echo "No latest download log pointer found"
fi
