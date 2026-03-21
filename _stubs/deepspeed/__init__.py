"""Minimal DeepSpeed stub.

Why this exists:
- Some TRL trainers import `deepspeed` unconditionally at import time.
- On many machines (including this one), the CUDA toolkit (CUDA_HOME) is not
  installed, and importing the real DeepSpeed package can raise immediately.

This stub makes `import deepspeed` succeed for import-time dependency probing.
If you actually want to *train with DeepSpeed*, remove this stub from PYTHONPATH
and install/configure a working DeepSpeed + CUDA toolkit toolchain.
"""

__all__ = ["__version__"]
__version__ = "0.0.0-stub"
