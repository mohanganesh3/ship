#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/home/mohanganesh/ship/.venv/bin/python"

TEACHER_DIR="/home/mohanganesh/ship/models/teacher"
STUDENT_DIR="/home/mohanganesh/ship/models/student"
LOG_DIR="/home/mohanganesh/ship/models/logs"
OUT_LOG="$LOG_DIR/download_progress.log"
CACHE_JSON="$LOG_DIR/teacher_expected_q4km.bytes"

mkdir -p "$LOG_DIR"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

get_dir_bytes() {
  local d="$1"
  if [ -d "$d" ]; then
    du -sb "$d" 2>/dev/null | awk '{print $1}'
  else
    echo 0
  fi
}

get_expected_teacher_bytes() {
  if [ -s "$CACHE_JSON" ]; then
    cat "$CACHE_JSON"
    return 0
  fi

  # Compute once from Hub metadata (sizes) and cache
  "$VENV_PY" - <<'PY' > "$CACHE_JSON"
import fnmatch
from huggingface_hub import HfApi

repo_id = "bartowski/Qwen_Qwen3-235B-A22B-Instruct-2507-GGUF"
pattern = "*Q4_K_M*"
api = HfApi()

total = 0
for e in api.list_repo_tree(repo_id=repo_id, repo_type="model", recursive=True):
    if getattr(e, "type", None) == "directory":
        continue
    size = getattr(e, "size", None)
    if size is None:
        continue
    if fnmatch.fnmatch(e.path, pattern):
        total += size

print(total)
PY

  cat "$CACHE_JSON"
}

expected_teacher=$(get_expected_teacher_bytes)

{
  echo "[$(timestamp)] monitor started"
  echo "[$(timestamp)] expected_teacher_bytes_q4km=$expected_teacher"
} >> "$OUT_LOG"

while true; do
  have_teacher=$(get_dir_bytes "$TEACHER_DIR")
  have_student=$(get_dir_bytes "$STUDENT_DIR")

  remaining=$(( expected_teacher > have_teacher ? expected_teacher - have_teacher : 0 ))

  # percentage (integer)
  if [ "$expected_teacher" -gt 0 ]; then
    pct=$(( have_teacher * 100 / expected_teacher ))
  else
    pct=0
  fi

  # human-ish output via python for GiB/GB formatting
  "$VENV_PY" - <<PY >> "$OUT_LOG"
from datetime import datetime, timezone

expected = int(${expected_teacher})
have_t = int(${have_teacher})
remain = int(${remaining})
have_s = int(${have_student})
pct = int(${pct})

def fmt(n: int) -> str:
    gib = n/(1024**3)
    gb = n/1e9
    return f"{gib:7.2f} GiB ({gb:7.2f} GB)"

ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
print(f"[{ts}] teacher={fmt(have_t)} / {fmt(expected)}  remaining={fmt(remain)}  pct={pct}%  student={fmt(have_s)}")
PY

  sleep 60
done
