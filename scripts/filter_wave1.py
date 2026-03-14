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
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

# Enforce CPU-only before importing torch to avoid CUDA init warnings on older drivers.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

# Some environments have old NVIDIA drivers; even on CPU-only runs, torch/transformers
# may probe CUDA and emit a warning. Silence it to keep pipeline logs clean.
warnings.filterwarnings(
    "ignore",
    message=r"CUDA initialization: The NVIDIA driver on your system is too old.*",
)

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


def _strip_code_fences(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    # Remove a leading ```lang
    s = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", s)
    # Remove trailing ```
    s = re.sub(r"```\s*$", "", s)
    return s.strip()


def _extract_task_prompt(instruction: str) -> Optional[str]:
    """Extract the TASK directive from a teacher prompt, without the source excerpt.

    We intentionally avoid including the SOURCE EXCERPT itself in the user prompt.
    """

    if not isinstance(instruction, str) or not instruction.strip():
        return None

    # Keep only the pre-excerpt portion.
    pre = re.split(r"\n\nSOURCE EXCERPT(S)?:\n", instruction, maxsplit=1, flags=re.IGNORECASE)
    pre = pre[0] if pre else instruction

    m = re.search(r"(?is)\bTASK:\s*(.+)$", pre)
    if not m:
        return None

    task = m.group(1).strip()

    # Remove common trailing boilerplate.
    task = re.sub(r"(?is)\bReturn JSON.*$", "", task).strip()
    task = re.sub(r"(?is)\bReturn the checklist.*$", "", task).strip()
    task = re.sub(r"(?is)\bReturn the .* as .*\.?$", "", task).strip()

    # Collapse whitespace.
    task = re.sub(r"\s+", " ", task).strip()
    return task or None


def _try_parse_qa_from_response_text(resp: str) -> Tuple[Optional[str], Optional[str]]:
    """Try to parse a (question, answer) pair from a response string.

    Handles:
    - JSON object string: {"question": ..., "answer": ...}
    - JSON in code fences
    - JSON embedded in surrounding text (best-effort)
    """

    if not isinstance(resp, str):
        return None, None
    s = _strip_code_fences(resp)
    if not s:
        return None, None

    # Fast path: full JSON object.
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            q = obj.get("question")
            a = obj.get("answer")
            if isinstance(q, str) and isinstance(a, str):
                return q.strip() or None, a.strip() or None

    # Best-effort: try to extract the first {...} span.
    if "{" in s and "}" in s:
        start = s.find("{")
        end = s.rfind("}")
        if 0 <= start < end:
            cand = s[start : end + 1].strip()
            try:
                obj = json.loads(cand)
            except json.JSONDecodeError:
                obj = None
            if isinstance(obj, dict):
                q = obj.get("question")
                a = obj.get("answer")
                if isinstance(q, str) and isinstance(a, str):
                    return q.strip() or None, a.strip() or None

    return None, None


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
        q2, a2 = _try_parse_qa_from_response_text(resp)
        if isinstance(q2, str) and isinstance(a2, str) and q2.strip() and a2.strip():
            return q2.strip(), a2.strip()

        # Fallback: for non-JSON response formats (e.g., checklist/procedure/definitions),
        # derive a concise prompt from the TASK line and use the raw response as the answer.
        instruction = rec.get("instruction")
        if isinstance(instruction, str):
            task_prompt = _extract_task_prompt(instruction)
        else:
            task_prompt = None

        s = resp.strip()
        if task_prompt and s:
            return task_prompt, s

        angle = rec.get("angle")
        if isinstance(angle, str) and angle.strip() and s:
            return f"{angle.strip()} (from source excerpt)", s

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
    min_words: int = 10,
    procedural_min_words: int = 40,
    require_regulatory_keywords: bool = True,
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
        if wc < int(min_words):
            stats.rejected_short += 1
            continue

        rec_type = rec.get("type")
        if require_regulatory_keywords and isinstance(rec_type, str) and rec_type.lower() == "regulatory":
            if not _contains_any_ci(
                answer,
                ["shall", "must", "require", "prohibit", "regulation", "annex", "convention"],
            ):
                stats.rejected_regulatory_keywords += 1
                continue

        # Procedural answers should be longer.
        difficulty_hint = str(rec.get("difficulty_hint") or "")
        if (isinstance(rec_type, str) and rec_type.lower() == "procedural") or (
            "procedural" in difficulty_hint.lower()
        ):
            if wc < int(procedural_min_words):
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

    p.add_argument("--ifd-min", type=float, default=0.01)
    p.add_argument("--ifd-max", type=float, default=0.99)
    p.add_argument("--very-low-keep", type=int, default=500)

    p.add_argument("--max-records", type=int, default=0, help="Optional cap for debugging (0 = no cap).")

    p.add_argument(
        "--hard-only",
        action="store_true",
        help="Run only hard-rejection and write merged output (no GPT-2 IFD stage).",
    )

    p.add_argument(
        "--min-words",
        type=int,
        default=10,
        help="Minimum word count for non-marker answers (default: 10).",
    )
    p.add_argument(
        "--procedural-min-words",
        type=int,
        default=40,
        help="Minimum word count for procedural answers (default: 40).",
    )
    p.add_argument(
        "--no-regulatory-keyword-requirement",
        action="store_true",
        help="Do not require regulatory answers to contain keywords like 'shall/must/annex'.",
    )
    p.add_argument(
        "--widen-hard",
        action="store_true",
        help=(
            "Relax hard-rejection thresholds to increase yield (min-words=5, procedural-min-words=20, "
            "and disable regulatory keyword requirement)."
        ),
    )

    p.add_argument(
        "--widen-ifd",
        action="store_true",
        help="Widen IFD keep range to 0.0–2.0 (use only if final count is below gate).",
    )

    return p.parse_args()


def main() -> int:
    # Enforce CPU-only.
    torch.set_num_threads(max(1, int(os.environ.get("OMP_NUM_THREADS", "40"))))

    args = parse_args()

    phase = "PHASE_2_SUPERFILTER_WAVE1"
    _append_pipeline_log(phase, "RUNNING", "starting")

    if args.widen_ifd:
        ifd_min, ifd_max = 0.0, 2.0
    else:
        ifd_min, ifd_max = float(args.ifd_min), float(args.ifd_max)

    if args.widen_hard:
        min_words = 5
        procedural_min_words = 20
        require_regulatory_keywords = False
    else:
        min_words = int(args.min_words)
        procedural_min_words = int(args.procedural_min_words)
        require_regulatory_keywords = not bool(args.no_regulatory_keyword_requirement)

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

        hard_kept, stats = hard_reject_filter(
            recs_iter2,
            mode_name=mode_name,
            min_words=min_words,
            procedural_min_words=procedural_min_words,
            require_regulatory_keywords=require_regulatory_keywords,
        )

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
