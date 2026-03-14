#!/usr/bin/env bash
set -euo pipefail

# Wrapper to run the training venv Python with LD_LIBRARY_PATH configured so
# bitsandbytes can find the CUDA 11.x shared libraries shipped by pip wheels.
#
# Usage:
#   scripts/train_python.sh -c "import torch; print(torch.__version__)"
#   scripts/train_python.sh -m bitsandbytes

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${VENV_TRAIN:-"$ROOT_DIR/.venv-train"}"
PYTHON="$VENV/bin/python"

# Legacy compatibility shims live in `_stubs/`. These were used for earlier
# experiments and can shadow real packages (e.g. `deepspeed`). Keep them opt-in.
if [[ "${USE_STUBS:-0}" == "1" && -d "$ROOT_DIR/_stubs" ]]; then
  export PYTHONPATH="$ROOT_DIR/_stubs${PYTHONPATH:+:$PYTHONPATH}"
fi

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: training venv python not found at: $PYTHON" >&2
  echo "       Set VENV_TRAIN to override, e.g. VENV_TRAIN=/path/to/.venv-train" >&2
  exit 1
fi

# These directories are created by pip packages like nvidia-cusparse-cu11, etc.
# They are NOT automatically in the dynamic loader search path on many systems.
CUDA_LIB_DIRS=(
  "$VENV/lib/python3.10/site-packages/nvidia/cublas/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cuda_cupti/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cuda_nvrtc/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cuda_runtime/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cudnn/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cufft/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/curand/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cusolver/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/cusparse/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/nccl/lib"
  "$VENV/lib/python3.10/site-packages/nvidia/nvtx/lib"
)

# Prepend (don’t overwrite) so system CUDA (if present) can still be used.
for d in "${CUDA_LIB_DIRS[@]}"; do
  if [[ -d "$d" ]]; then
    export LD_LIBRARY_PATH="$d${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  fi
done

# DeepSpeed sometimes tries to JIT-compile CUDA ops at import time.
# On many cluster nodes CUDA toolkit headers (CUDA_HOME) are not available.
# These flags tell DeepSpeed to skip building optional ops, letting imports work.
export DS_BUILD_OPS=0
export DS_BUILD_AIO=0
export DS_BUILD_CCL=0
export DS_BUILD_UTILS=0

exec "$PYTHON" "$@"
