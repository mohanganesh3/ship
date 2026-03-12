from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING


def pipeline_base_dir() -> Path:
    # ship/maritime_pipeline/stage0/paths.py -> ship/maritime_pipeline
    return Path(__file__).resolve().parents[1]


def import_config():
    base = pipeline_base_dir()
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
    import config  # type: ignore

    return config
