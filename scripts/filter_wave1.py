#!/usr/bin/env python3
"""Wave 1 SuperFiltering (IFD) for maritime SFT data.

Implements the 3-stage filter specified in TRAINING-PLAN / detailedprompt:
1) Hard rejection rules (cheap)
2) IFD scoring using GPT-2 on CPU: ifd_score = cond_ppl / uncond_ppl
3) Merge Mode A/B/C into final sft_curated.jsonl

Hard rules:
- Run on CPU (do not use GPU)
- Do not touch the non-training venv (.venv)

Outputs:
- /home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl

Also appends pipeline phase status lines to:
- /home/mohanganesh/ship/logs/pipeline_execution.log
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast


PIPELINE_EXEC_LOG = "/home/mohanganesh/ship/logs/pipeline_execution.log"
DEFAULT_GEN_DIR = "/home/mohanganesh/ship/ship/maritime_pipeline/data/generation"
DEFAULT_FINAL_DIR = "/home/mohanganesh/ship/ship/maritime_pipeline/data/final"

DEFAULT_MODE_A = f"{DEFAULT_GEN_DIR}/wave1_modeA_raw.jsonl"
DEFAULT_MODE_B = f"{DEFAULT_GEN_DIR}/wave1_modeB_raw.jsonl"
DEFAULT_MODE_C = f"{DEFAULT_GEN_DIR}/wave1_modeC_raw.jsonl"

DEFAULT_OUT = f"{DEFAULT_FINAL_DIR}/sft_curated.jsonl"

FORBIDDEN_PHRASES = [
    "as an ai",
    "i cannot",
    "language model",
    "i don't have access",
    "i do not have access",
    "i'm unable to",
    "im unable to",
]

UNCERTAIN_KEEP_MARKERS = [
    "INSUFFICIENT_CONTEXT",
    "INSUFFICIENT_SOURCE",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_pipeline_log(phase: str, status: str, details: str) -> None:
    Path(PIPELINE_EXEC_LOG).parent.mkdir(parents=True, exist_ok=True)
    line = f"[{_utc_now_iso()}] {phase} STATUS: {status}. Details: {details}\n"
    with open(PIPELINE_EXEC_LOG, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()


def _iter_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


def _contains_any_ci(text: str, needles: Iterable[str]) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def _is_keep_marker(answer: str) -> bool:
    return any(m in answer for m in UNCERTAIN_KEEP_MARKERS)


def _extract_question_answer(rec: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of (question, answer) from raw Wave 1 records.

    Observed schema:
    - Some records have a JSON string in `response` with keys {question, answer}
    - Some records may directly include `question` / `answer`

    Returns (None, None) if extraction fails.
    """

    q = rec.get("question")
    a = rec.get("answer")
    if isinstance(q, str) and isinstance(a, str):
        return q.strip() or None, a.strip() or None

    resp = rec.get("response")
    if isinstance(resp, dict):
        q2 = resp.get("question")
        a2 = resp.get("answer")
        if isinstance(q2, str) and isinstance(a2, str):
            return q2.strip() or None, a2.strip() or None

    if isinstance(resp, str):
        s = resp.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict):
                q2 = obj.get("question")
                a2 = obj.get("answer")
                if isinstance(q2, str) and isinstance(a2, str):
                    return q2.strip() or None, a2.strip() or None

    return None, None


@dataclass
class HardRejectStats:
    total: int = 0
    kept: int = 0
    rejected_empty: int = 0
    rejected_short: int = 0
    rejected_forbidden: int = 0
    rejected_regulatory_keywords: int = 0
    rejected_procedural_short: int = 0
    rejected_no_qa: int = 0


def hard_reject_filter(
    recs: Iterable[Dict[str, Any]],
    *,
    mode_name: str,
) -> Tuple[List[Dict[str, Any]], HardRejectStats]:
    stats = HardRejectStats()
    out: List[Dict[str, Any]] = []

    for rec in recs:
        stats.total += 1
        q, a = _extract_question_answer(rec)
        if not isinstance(a, str) or not a.strip() or not isinstance(q, str) or not q.strip():
            stats.rejected_no_qa += 1
            continue

        answer = a.strip()
        question = q.strip()

        # Keep marker responses regardless of other constraints.
        if _is_keep_marker(answer):
            out.append({**rec, "question": question, "answer": answer})
            stats.kept += 1
            continue

        if not answer:
            stats.rejected_empty += 1
            continue

        if _contains_any_ci(answer, FORBIDDEN_PHRASES):
            stats.rejected_forbidden += 1
            continue

        wc = _word_count(answer)
        if wc < 10:
            stats.rejected_short += 1
            continue

        rec_type = rec.get("type")
        if isinstance(rec_type, str) and rec_type.lower() == "regulatory":
            if not _contains_any_ci(answer, ["shall", "must", "require", "prohibit", "regulation", "annex", "convention"]):
                stats.rejected_regulatory_keywords += 1
                continue

        # Procedural answers should be longer.
        difficulty_hint = str(rec.get("difficulty_hint") or "")
        if (
            (isinstance(rec_type, str) and rec_type.lower() == "procedural")
            or ("procedural" in difficulty_hint.lower())
        ):
            if wc < 40:
                stats.rejected_procedural_short += 1
                continue

        out.append({**rec, "question": question, "answer": answer})
        stats.kept += 1

    return out, stats


def _nll_on_suffix(
    model: GPT2LMHeadModel,
    input_ids: torch.Tensor,
    suffix_mask: torch.Tensor,
) -> Tuple[float, int]:
    """Compute total NLL over tokens where suffix_mask==1.

    suffix_mask is aligned with input_ids (shape [seq]).
    """

    # Labels: ignore prefix tokens, predict next token for suffix.
    labels = input_ids.clone()
    labels[suffix_mask == 0] = -100

    out = model(input_ids=input_ids.unsqueeze(0), labels=labels.unsqueeze(0))
    loss = out.loss
    if loss is None:
        return 0.0, 0

    # loss is mean over non-ignored labels.
    n_tokens = int((labels != -100).sum().item())
    return float(loss.item()) * max(1, n_tokens), n_tokens


def _ppl_from_nll(nll_sum: float, n_tokens: int) -> float:
    if n_tokens <= 0:
        return float("inf")
    mean = nll_sum / float(n_tokens)
    # Avoid inf from exp on pathological values.
    return float(math.exp(min(20.0, mean)))


def compute_ifd_score(
    *,
    model: GPT2LMHeadModel,
    tokenizer: GPT2TokenizerFast,
    question: str,
    answer: str,
    device: torch.device,
) -> float:
    """IFD score = cond_ppl / uncond_ppl."""

    # Conditional: prefix includes the question; only score answer tokens.
    prefix = f"Question: {question}\nAnswer: "
    prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
    answer_ids = tokenizer.encode(answer, add_special_tokens=False)

    # If answer is empty or tokenization fails, reject later.
    if not answer_ids:
        return float("nan")

    cond_ids = torch.tensor(prefix_ids + answer_ids, dtype=torch.long, device=device)
    cond_mask = torch.zeros_like(cond_ids)
    cond_mask[len(prefix_ids) :] = 1

    cond_nll_sum, cond_tok = _nll_on_suffix(model, cond_ids, cond_mask)
    cond_ppl = _ppl_from_nll(cond_nll_sum, cond_tok)

    # Unconditional: score the answer alone.
    uncond_ids = torch.tensor(answer_ids, dtype=torch.long, device=device)
    uncond_mask = torch.ones_like(uncond_ids)
    uncond_nll_sum, uncond_tok = _nll_on_suffix(model, uncond_ids, uncond_mask)
    uncond_ppl = _ppl_from_nll(uncond_nll_sum, uncond_tok)

    if not math.isfinite(cond_ppl) or not math.isfinite(uncond_ppl) or uncond_ppl <= 0:
        return float("nan")

    return float(cond_ppl / uncond_ppl)


def ifd_filter(
    recs: List[Dict[str, Any]],
    *,
    ifd_min: float,
    ifd_max: float,
    keep_very_low_max: int,
    device: torch.device,
) -> List[Dict[str, Any]]:
    """Apply IFD filtering on CPU.

    Keeps:
    - all samples with ifd_min <= score <= ifd_max
    - plus up to keep_very_low_max samples with score < ifd_min (very-low-IFD)
    """

    # CPU only.
    if device.type != "cpu":
        raise ValueError("IFD scoring must run on CPU")

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    model.to(device)
    model.eval()

    kept: List[Dict[str, Any]] = []
    very_low: List[Tuple[float, Dict[str, Any]]] = []

    with torch.inference_mode():
        for rec in recs:
            q = rec.get("question")
            a = rec.get("answer")
            if not isinstance(q, str) or not isinstance(a, str):
                continue
            score = compute_ifd_score(
                model=model,
                tokenizer=tokenizer,
                question=q,
                answer=a,
                device=device,
            )
            if not math.isfinite(score):
                continue

            rec2 = {**rec, "ifd_score": float(score)}

            if ifd_min <= score <= ifd_max:
                kept.append(rec2)
            elif score < ifd_min:
                very_low.append((score, rec2))

    # Keep up to N very-low scores (lowest first)
    very_low.sort(key=lambda x: x[0])
    kept.extend([r for _, r in very_low[: int(keep_very_low_max)]])

    return kept


def write_jsonl(path: str, recs: Iterable[Dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in recs:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()

    p.add_argument("--mode-a", default=DEFAULT_MODE_A)
    p.add_argument("--mode-b", default=DEFAULT_MODE_B)
    p.add_argument("--mode-c", default=DEFAULT_MODE_C)

    p.add_argument("--out", default=DEFAULT_OUT)

    p.add_argument("--ifd-min", type=float, default=0.03)
    p.add_argument("--ifd-max", type=float, default=0.97)
    p.add_argument("--very-low-keep", type=int, default=500)

    p.add_argument("--max-records", type=int, default=0, help="Optional cap for debugging (0 = no cap).")

    p.add_argument(
        "--hard-only",
        action="store_true",
        help="Run only hard-rejection and write merged output (no GPT-2 IFD stage).",
    )

    p.add_argument(
        "--widen-ifd",
        action="store_true",
        help="Widen IFD keep range to 0.02–0.98 (use only if final count is below gate).",
    )

    return p.parse_args()


def main() -> int:
    # Enforce CPU-only.
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
    torch.set_num_threads(max(1, int(os.environ.get("OMP_NUM_THREADS", "40"))))

    args = parse_args()

    phase = "PHASE_2_SUPERFILTER_WAVE1"
    _append_pipeline_log(phase, "RUNNING", "starting")

    if args.widen_ifd:
        ifd_min, ifd_max = 0.02, 0.98
    else:
        ifd_min, ifd_max = float(args.ifd_min), float(args.ifd_max)

    out_path = str(args.out)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    mode_paths = [("A", args.mode_a), ("B", args.mode_b), ("C", args.mode_c)]

    merged: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}

    for mode_name, path in mode_paths:
        if not os.path.exists(path):
            counts[mode_name] = 0
            continue

        recs_iter = _iter_jsonl(path)
        if args.max_records and args.max_records > 0:
            recs_list: List[Dict[str, Any]] = []
            for i, r in enumerate(recs_iter, start=1):
                recs_list.append(r)
                if i >= int(args.max_records):
                    break
            recs_iter2 = recs_list
        else:
            recs_iter2 = list(recs_iter)

        hard_kept, stats = hard_reject_filter(recs_iter2, mode_name=mode_name)

        if args.hard_only:
            kept = hard_kept
        else:
            kept = ifd_filter(
                hard_kept,
                ifd_min=ifd_min,
                ifd_max=ifd_max,
                keep_very_low_max=int(args.very_low_keep),
                device=torch.device("cpu"),
            )

        counts[mode_name] = len(kept)
        merged.extend(kept)

        # Minimal per-mode stats line.
        _append_pipeline_log(
            phase,
            "RUNNING",
            f"mode={mode_name} total={stats.total} kept_hard={len(hard_kept)} kept_final={len(kept)}",
        )

    write_jsonl(out_path, merged)

    total = sum(counts.values())
    details = f"counts={counts} total={total} out={out_path}"
    _append_pipeline_log(phase, "PASS", details)

    print("FILTER COMPLETE")
    print(details)

    # Gate is checked externally by the pipeline controller.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
