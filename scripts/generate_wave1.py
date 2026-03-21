#!/home/mohanganesh/ship/.venv/bin/python

"""Wave 1 synthetic data generation.

Reads grounded maritime chunks and produces instruction/response JSONL pairs by querying
local teacher `llama-server` instances (OpenAI-compatible `/v1/chat/completions`).

Design goals:
- Resumable: tracks completed (mode, chunk_id, angle) in generation_progress.json
- Grounded: teacher is instructed to use ONLY the provided chunk text
- Robust: retries on 503/loading, validates basic output quality, atomic progress writes

Outputs (in out_dir):
- wave1_modeA_raw.jsonl
- wave1_modeB_raw.jsonl
- wave1_modeC_raw.jsonl

Progress file (in out_dir):
- generation_progress.json

Note: This script is intentionally conservative about concurrency because each teacher
instance is run with `--parallel 1`.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import requests

DEFAULT_INPUT = "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/chunks.jsonl"
DEFAULT_OUT_DIR = "/home/mohanganesh/ship/ship/maritime_pipeline/data/generation"
PIPE_LOG = "/home/mohanganesh/ship/logs/pipeline_execution.log"

FORBIDDEN_PHRASES = [
    "as an ai",
    "language model",
    "i cannot",
    "i can't",
    "i do not have access",
    "i don't have access",
    "my training data",
]


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_pipe(line: str) -> None:
    try:
        Path(PIPE_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(PIPE_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts()}] {line}\n")
    except Exception:
        # Don't let logging kill a multi-day job.
        pass


def atomic_write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def normalize_domain_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(t).strip().lower() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        # Sometimes it might be a comma-separated string.
        parts = [p.strip().lower() for p in tags.split(",")]
        return [p for p in parts if p]
    return [str(tags).strip().lower()]


def is_high_value(tags: Sequence[str], doc_type: str) -> bool:
    blob = " ".join(tags) + " " + (doc_type or "").lower()
    keywords = [
        "marpol",
        "annex",
        "emission",
        "sox",
        "nox",
        "ghg",
        "cii",
        "eexi",
        "eu ets",
        "solas",
        "ism",
        "isps",
        "colreg",
        "stcw",
        "port state",
        "psc",
        "ballast",
        "bwm",
        "class",
        "abs",
        "dnv",
        "lr",
    ]
    return any(k in blob for k in keywords)


def difficulty_policy(difficulty_hint: str) -> str:
    hint = (difficulty_hint or "").strip().lower()
    if hint in {"factual_lookup", "short", "easy"}:
        return "no_think"
    if hint in {"procedural_sequential", "procedural", "multi_step"}:
        return "step_by_step"
    return "concise"


def validate_text(text: str) -> List[str]:
    issues: List[str] = []
    if not text or not text.strip():
        return ["empty"]
    low = text.lower()
    for bad in FORBIDDEN_PHRASES:
        if bad in low:
            issues.append(f"forbidden({bad})")
    # Avoid clearly ungrounded citations.
    if "http" in low and "source_url" not in low:
        # Teacher sometimes invents URLs; we will separately include source_url in metadata.
        pass
    return issues


@dataclass
class Chunk:
    chunk_id: str
    text: str
    difficulty_hint: str
    doc_type: str
    source_type: str
    source_url: str
    domain_tags: List[str]
    quality_tier: str
    year: Optional[int]


def iter_chunks(path: Path) -> Iterable[Chunk]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            chunk_id = str(obj.get("id") or obj.get("chunk_id") or "").strip()
            text = str(obj.get("text") or "").strip()
            if not chunk_id or not text:
                continue

            yield Chunk(
                chunk_id=chunk_id,
                text=text,
                difficulty_hint=str(obj.get("difficulty_hint") or "").strip(),
                doc_type=str(obj.get("doc_type") or "").strip(),
                source_type=str(obj.get("source_type") or "").strip(),
                source_url=str(obj.get("source_url") or "").strip(),
                domain_tags=normalize_domain_tags(obj.get("domain_tags")),
                quality_tier=str(obj.get("quality_tier") or "").strip(),
                year=obj.get("year"),
            )


def truncate_text(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + "\n[TRUNCATED]"


def build_modeA_tasks(chunk: Chunk) -> List[Tuple[str, str]]:
    """Return list of (angle, instruction) for a chunk."""

    base_angles: List[Tuple[str, str]] = []

    policy = difficulty_policy(chunk.difficulty_hint)

    if policy == "no_think":
        style = "Answer directly and briefly. Do not include reasoning."
    elif policy == "step_by_step":
        style = "Provide a careful step-by-step solution. Use numbered steps."
    else:
        style = "Be concise and practical."

    common = (
        "You are a maritime domain expert. Use ONLY the provided SOURCE EXCERPT. "
        "Do not use outside knowledge. If the excerpt does not contain enough information, reply: 'INSUFFICIENT_SOURCE'. "
        "Do not mention being an AI or a language model. "
        f"{style}"
    )

    base_angles.append(
        (
            "qa",
            (
                f"{common}\n\n"
                "TASK: Write one user question that can be answered from the excerpt, then answer it. "
                "Return JSON with keys: question, answer.\n\n"
                "SOURCE EXCERPT:\n" + chunk.text
            ),
        )
    )

    base_angles.append(
        (
            "checklist",
            (
                f"{common}\n\n"
                "TASK: Create a compliance or inspection checklist derived from the excerpt. "
                "Return the checklist as bullet points.\n\n"
                "SOURCE EXCERPT:\n" + chunk.text
            ),
        )
    )

    base_angles.append(
        (
            "procedure",
            (
                f"{common}\n\n"
                "TASK: Extract or infer a procedure described in the excerpt. Present it as numbered steps.\n\n"
                "SOURCE EXCERPT:\n" + chunk.text
            ),
        )
    )

    base_angles.append(
        (
            "troubleshooting",
            (
                f"{common}\n\n"
                "TASK: Create a troubleshooting Q&A based on the excerpt: problem statement + likely causes + actions. "
                "Only include items supported by the excerpt.\n\n"
                "SOURCE EXCERPT:\n" + chunk.text
            ),
        )
    )

    base_angles.append(
        (
            "definitions",
            (
                f"{common}\n\n"
                "TASK: List key terms defined or implied in the excerpt and give short definitions grounded in the excerpt.\n\n"
                "SOURCE EXCERPT:\n" + chunk.text
            ),
        )
    )

    # Add extra angles for high-value content.
    if is_high_value(chunk.domain_tags, chunk.doc_type):
        base_angles.append(
            (
                "edge_cases",
                (
                    f"{common}\n\n"
                    "TASK: Write 2 edge-case questions that operators might ask about this excerpt, and answer them grounded in the excerpt.\n\n"
                    "SOURCE EXCERPT:\n" + chunk.text
                ),
            )
        )
        base_angles.append(
            (
                "audit",
                (
                    f"{common}\n\n"
                    "TASK: Turn the excerpt into an audit-ready summary: required actions, records to keep, and responsible roles (if mentioned).\n\n"
                    "SOURCE EXCERPT:\n" + chunk.text
                ),
            )
        )

    return base_angles


def build_modeC_task(chunk: Chunk) -> Tuple[str, str]:
    policy = difficulty_policy(chunk.difficulty_hint)
    if policy == "no_think":
        style = "Answer directly and briefly. Do not include reasoning."
    elif policy == "step_by_step":
        style = "Provide a careful step-by-step solution. Use numbered steps."
    else:
        style = "Be concise and practical."

    instruction = (
        "You are a maritime domain expert. Use ONLY the provided SOURCE EXCERPT. "
        "Do not use outside knowledge. If the excerpt does not contain enough information, reply: 'INSUFFICIENT_SOURCE'. "
        "Do not mention being an AI or a language model. "
        f"{style}\n\n"
        "TASK: The user asks a realistic maritime question that can be answered from the excerpt. "
        "Provide the best possible answer grounded in the excerpt.\n\n"
        "SOURCE EXCERPT:\n" + chunk.text
    )
    return ("direct_qa", instruction)


def build_modeB_task(chunk_a: Chunk, chunk_b: Chunk) -> Tuple[str, str]:
    instruction = (
        "You are a maritime domain expert. Use ONLY the provided SOURCE EXCERPTS A and B. "
        "Do not use outside knowledge. If the excerpts do not contain enough information, reply: 'INSUFFICIENT_SOURCE'. "
        "Do not mention being an AI or a language model.\n\n"
        "TASK: Write a single question that requires combining information from BOTH excerpts (multi-hop). "
        "Then answer it, explicitly referencing what comes from excerpt A vs excerpt B.\n\n"
        "Return JSON with keys: question, answer.\n\n"
        "SOURCE EXCERPT A:\n" + chunk_a.text + "\n\n"
        "SOURCE EXCERPT B:\n" + chunk_b.text
    )
    return ("multi_hop", instruction)


def call_teacher(
    port: int,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    retries: int,
) -> str:
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    payload = {
        "model": "teacher",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err: Optional[Exception] = None
    backoff = 5

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            if resp.status_code in {502, 503, 504}:
                raise RuntimeError(f"server_not_ready_http_{resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff)
                backoff = min(60, backoff + 5)

    raise RuntimeError(f"teacher_call_failed_after_retries: {last_err}")


@dataclass
class Job:
    mode: str
    chunk_ids: Tuple[str, ...]
    angle: str
    instruction: str
    meta: Dict[str, Any]


class PortWorker(threading.Thread):
    def __init__(
        self,
        port: int,
        q: Queue,
        out_fh,
        progress: "ProgressStore",
        stats: "Stats",
        args: argparse.Namespace,
        stop_event: threading.Event,
    ) -> None:
        super().__init__(daemon=True)
        self.port = port
        self.q = q
        self.out_fh = out_fh
        self.progress = progress
        self.stats = stats
        self.args = args
        self.stop_event = stop_event

    def run(self) -> None:
        system = "You are a maritime expert."
        while not self.stop_event.is_set():
            try:
                job: Optional[Job] = self.q.get(timeout=1)
            except Exception:
                continue
            if job is None:
                self.q.task_done()
                break

            key = self.progress.make_key(job.mode, job.chunk_ids, job.angle)
            if self.progress.is_done(key):
                self.q.task_done()
                continue

            # Try a couple of times to get a clean answer.
            content = ""
            last_issues: List[str] = []
            for attempt in range(1, self.args.sample_retries + 1):
                try:
                    content = call_teacher(
                        self.port,
                        system=system,
                        user=job.instruction,
                        temperature=self.args.temperature,
                        max_tokens=self.args.max_tokens,
                        timeout=self.args.request_timeout,
                        retries=self.args.request_retries,
                    )
                except Exception as e:
                    last_issues = [f"request_error({e})"]
                    continue

                issues = validate_text(content)
                if not issues:
                    last_issues = []
                    break
                last_issues = issues

            record = {
                "mode": job.mode,
                "angle": job.angle,
                "chunk_ids": list(job.chunk_ids),
                "instruction": job.instruction,
                "response": content,
                "teacher_port": self.port,
                "generated_at": ts(),
                **job.meta,
            }

            # Write even if low-quality; downstream filters can drop, but mark quality.
            if last_issues:
                record["_gen_issues"] = last_issues

            try:
                self.out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                self.out_fh.flush()
            except Exception:
                # If we can't write, stop the job.
                self.stop_event.set()
                self.q.task_done()
                break

            self.progress.mark_done(key)
            self.stats.mark_written(job.mode)
            self.q.task_done()


class ProgressStore:
    def __init__(self, path: Path, flush_every: int = 200) -> None:
        self.path = path
        self.flush_every = flush_every
        self._lock = threading.Lock()
        self._done: Set[str] = set()
        self._since_flush = 0

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._done = set(data.keys())
            elif isinstance(data, list):
                self._done = set(str(x) for x in data)
        except Exception:
            # Corrupt progress shouldn't brick the run; start from what we can.
            self._done = set()

    @staticmethod
    def make_key(mode: str, chunk_ids: Tuple[str, ...], angle: str) -> str:
        # Requirement: key is chunk_id + angle. For multi-hop, combine ids.
        joined = "+".join(chunk_ids)
        return f"{mode}:{joined}:{angle}"

    def is_done(self, key: str) -> bool:
        with self._lock:
            return key in self._done

    def mark_done(self, key: str) -> None:
        with self._lock:
            self._done.add(key)
            self._since_flush += 1
            if self._since_flush >= self.flush_every:
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        self._since_flush = 0
        # Persist as dict for O(1) membership when humans inspect the file.
        atomic_write_json(self.path, {k: True for k in sorted(self._done)})


class Stats:
    def __init__(self, report_every: int = 50) -> None:
        self.report_every = report_every
        self._lock = threading.Lock()
        self._total = 0
        self._by_mode: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
        self._last_report = time.time()

    def mark_written(self, mode: str) -> None:
        with self._lock:
            self._total += 1
            if mode in self._by_mode:
                self._by_mode[mode] += 1

            if self._total % self.report_every == 0:
                now = time.time()
                dt = max(1e-6, now - self._last_report)
                rate = self.report_every / dt
                self._last_report = now
                msg = (
                    f"[{ts()}] progress: written_total={self._total} "
                    f"A={self._by_mode['A']} B={self._by_mode['B']} C={self._by_mode['C']} "
                    f"rate={rate:.2f}/s"
                )
                print(msg, flush=True)


def install_signal_handlers(stop_event: threading.Event, progress: ProgressStore) -> None:
    def _handler(signum, frame):
        log_pipe(f"generate_wave1.py: received signal {signum}, flushing progress and stopping")
        stop_event.set()
        try:
            progress.flush()
        except Exception:
            pass

    for s in (signal.SIGINT, signal.SIGTERM):
        signal.signal(s, _handler)


def parse_ports(s: str) -> List[int]:
    ports: List[int] = []
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        ports.append(int(part))
    if not ports:
        raise ValueError("No teacher ports provided")
    return ports


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=DEFAULT_INPUT)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--mode", choices=["A", "B", "C", "all"], default="A")
    ap.add_argument("--ports", default="8000,8001")
    ap.add_argument("--max-chunks", type=int, default=0, help="0 means no limit")
    ap.add_argument("--max-chars", type=int, default=7000, help="truncate excerpt to this many chars")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--request-timeout", type=int, default=180)
    ap.add_argument("--request-retries", type=int, default=12)
    ap.add_argument("--sample-retries", type=int, default=2)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    random.seed(args.seed)

    in_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    progress_path = out_dir / "generation_progress.json"
    progress = ProgressStore(progress_path, flush_every=200)
    progress.load()

    stats = Stats(report_every=50)

    stop_event = threading.Event()
    install_signal_handlers(stop_event, progress)

    ports = parse_ports(args.ports)

    out_files = {
        "A": out_dir / "wave1_modeA_raw.jsonl",
        "B": out_dir / "wave1_modeB_raw.jsonl",
        "C": out_dir / "wave1_modeC_raw.jsonl",
    }

    modes: List[str]
    if args.mode == "all":
        modes = ["A", "B", "C"]
    else:
        modes = [args.mode]

    log_pipe(
        f"STEP2 generate_wave1.py: starting mode={args.mode} ports={ports} input={in_path} out_dir={out_dir}"
    )

    # For Mode B, keep a small per-tag cache to form pairs without loading all chunks.
    tag_cache: Dict[str, List[Chunk]] = {}

    jobs_by_mode: Dict[str, Queue] = {m: Queue(maxsize=2000) for m in modes}

    # Open outputs.
    out_fhs: Dict[str, Any] = {}
    for m in modes:
        out_fhs[m] = open(out_files[m], "a", encoding="utf-8")

    # Start workers: one worker per port per mode (conservative).
    workers: List[PortWorker] = []
    for m in modes:
        for p in ports:
            w = PortWorker(
                port=p,
                q=jobs_by_mode[m],
                out_fh=out_fhs[m],
                progress=progress,
                stats=stats,
                args=args,
                stop_event=stop_event,
            )
            w.start()
            workers.append(w)

    produced = {m: 0 for m in modes}
    seen_chunks = 0

    try:
        for chunk in iter_chunks(in_path):
            if stop_event.is_set():
                break
            seen_chunks += 1

            # Truncate once here so prompts are bounded.
            chunk = Chunk(
                **{
                    **chunk.__dict__,
                    "text": truncate_text(chunk.text, args.max_chars),
                }
            )

            if "A" in modes:
                for angle, instr in build_modeA_tasks(chunk):
                    key = progress.make_key("A", (chunk.chunk_id,), angle)
                    if progress.is_done(key):
                        continue
                    meta = {
                        "chunk_id": chunk.chunk_id,
                        "difficulty_hint": chunk.difficulty_hint,
                        "doc_type": chunk.doc_type,
                        "source_type": chunk.source_type,
                        "source_url": chunk.source_url,
                        "domain_tags": chunk.domain_tags,
                        "quality_tier": chunk.quality_tier,
                        "year": chunk.year,
                    }
                    jobs_by_mode["A"].put(Job("A", (chunk.chunk_id,), angle, instr, meta))
                    produced["A"] += 1

            if "C" in modes:
                angle, instr = build_modeC_task(chunk)
                key = progress.make_key("C", (chunk.chunk_id,), angle)
                if not progress.is_done(key):
                    meta = {
                        "chunk_id": chunk.chunk_id,
                        "difficulty_hint": chunk.difficulty_hint,
                        "doc_type": chunk.doc_type,
                        "source_type": chunk.source_type,
                        "source_url": chunk.source_url,
                        "domain_tags": chunk.domain_tags,
                        "quality_tier": chunk.quality_tier,
                        "year": chunk.year,
                    }
                    jobs_by_mode["C"].put(Job("C", (chunk.chunk_id,), angle, instr, meta))
                    produced["C"] += 1

            if "B" in modes:
                tags = chunk.domain_tags or ["__no_tag__"]
                # Choose one tag to index by, to avoid exploding cache inserts.
                tag = tags[0]
                cache = tag_cache.setdefault(tag, [])
                if cache:
                    other = random.choice(cache)
                    angle, instr = build_modeB_task(other, chunk)
                    key = progress.make_key("B", (other.chunk_id, chunk.chunk_id), angle)
                    if not progress.is_done(key):
                        meta = {
                            "chunk_id": chunk.chunk_id,
                            "chunk_id_a": other.chunk_id,
                            "chunk_id_b": chunk.chunk_id,
                            "difficulty_hint": chunk.difficulty_hint,
                            "doc_type": chunk.doc_type,
                            "source_type": chunk.source_type,
                            "source_url": chunk.source_url,
                            "domain_tags": chunk.domain_tags,
                            "quality_tier": chunk.quality_tier,
                            "year": chunk.year,
                        }
                        jobs_by_mode["B"].put(Job("B", (other.chunk_id, chunk.chunk_id), angle, instr, meta))
                        produced["B"] += 1

                cache.append(chunk)
                if len(cache) > 50:
                    del cache[0]

            if args.max_chunks and seen_chunks >= args.max_chunks:
                break

            if seen_chunks % 2000 == 0:
                log_pipe(
                    "STEP2 generate_wave1.py: queued_jobs="
                    + ", ".join(f"{m}={produced[m]}" for m in modes)
                    + f" after {seen_chunks} chunks"
                )

        # Wait for queues to drain.
        for m in modes:
            jobs_by_mode[m].join()

    finally:
        stop_event.set()
        try:
            progress.flush()
        except Exception:
            pass

        # Signal workers to exit.
        for m in modes:
            for _ in ports:
                try:
                    jobs_by_mode[m].put_nowait(None)
                except Exception:
                    pass

        for w in workers:
            w.join(timeout=5)

        for fh in out_fhs.values():
            try:
                fh.close()
            except Exception:
                pass

    log_pipe(
        "STEP2 generate_wave1.py: finished queued_jobs="
        + ", ".join(f"{m}={produced[m]}" for m in modes)
        + f" chunks_seen={seen_chunks}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
