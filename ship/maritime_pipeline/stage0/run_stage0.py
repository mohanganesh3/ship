from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .paths import import_config, pipeline_base_dir
from .utils import now_iso


def _run(cmd: list[str], audit_path: Path) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as audit:
        audit.write(f"[{now_iso()}] RUN: {' '.join(cmd)}\n")
        audit.flush()
        p = subprocess.run(cmd, capture_output=True, text=True)
        audit.write(p.stdout)
        if p.stderr:
            audit.write("\n[stderr]\n")
            audit.write(p.stderr)
        audit.write(f"\n[{now_iso()}] EXIT: {p.returncode}\n\n")
        audit.flush()
        if p.returncode != 0:
            raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(cmd)}")


def main() -> int:
    cfg = import_config()
    base = pipeline_base_dir()

    ap = argparse.ArgumentParser(description="Run Stage-0 artifact generation end-to-end.")
    ap.add_argument("--allow-empty-general", action="store_true")
    ap.add_argument("--min-eval-filled", type=int, default=0)
    args = ap.parse_args()

    audit_path = cfg.FINAL_DIR / "pipeline_audit.log"

    # Ensure audit starts fresh for reproducibility.
    audit_path.write_text(f"[{now_iso()}] Stage-0 start\n", encoding="utf-8")

    # Run as module so relative imports work.
    py = sys.executable

    _run([py, "-m", "stage0.build_cpt_corpus"], audit_path)
    _run([py, "-m", "stage0.dedup_corpus"], audit_path)
    _run([py, "-m", "stage0.chunk_corpus"], audit_path)

    # general replay may be provided by the user; allow placeholders when requested
    gen_cmd = [py, "-m", "stage0.build_general_replay"]
    if args.allow_empty_general:
        gen_cmd.append("--allow-empty")
    _run(gen_cmd, audit_path)

    split_cmd = [py, "-m", "stage0.split_sets"]
    if args.allow_empty_general:
        split_cmd.append("--allow-empty-general")
    _run(split_cmd, audit_path)

    # Only create eval scaffold if file doesn't exist (so manual edits persist)
    eval_path = cfg.FINAL_DIR / "eval_set.jsonl"
    if not eval_path.exists() or eval_path.stat().st_size == 0:
        _run([py, "-m", "stage0.build_eval_scaffold"], audit_path)

    vcmd = [py, "-m", "stage0.validate_stage0"]
    if args.allow_empty_general:
        vcmd.append("--allow-empty-general")
    if args.min_eval_filled:
        vcmd.extend(["--min-eval-filled", str(args.min_eval_filled)])
    _run(vcmd, audit_path)

    with open(audit_path, "a", encoding="utf-8") as audit:
        audit.write(f"[{now_iso()}] Stage-0 complete\n")

    print(f"Stage-0 complete. Audit log: {audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
