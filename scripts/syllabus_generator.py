#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import random
import re
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
import urllib3

from syllabus_plan import (
    DOMAIN_TO_BUCKET,
    PRESETS,
    PRIORITY_ORDER,
    build_domain_rows,
    compute_domain_targets,
    existing_domain_counts,
    load_syllabus,
)


REPO_ROOT = Path(os.environ.get("SHIP_REPO_ROOT", "/home/mohanganesh/ship"))
GOLD_ROOT = REPO_ROOT / "training/gold_standard"
OUTPUT_TAG = os.environ.get("SHIP_OUTPUT_TAG", "").strip()
GENERATED_ROOT_BASE = GOLD_ROOT / "generated"
GENERATED_ROOT = GENERATED_ROOT_BASE / OUTPUT_TAG if OUTPUT_TAG else GENERATED_ROOT_BASE
SYLLABUS_FILE = GOLD_ROOT / "master_syllabus_v1.json"
ACCOUNTS_FILE = REPO_ROOT / "accounts_MASTER.json"
OUTPUT_FILE = GENERATED_ROOT / "syllabus_generated.jsonl"
REJECT_FILE = GENERATED_ROOT / "syllabus_rejections.jsonl"
STATS_FILE = GENERATED_ROOT / "syllabus_stats.json"
PLAN_FILE = GENERATED_ROOT / "syllabus_plan.json"
SSL_VERIFY = os.environ.get("SHIP_SSL_VERIFY", "").lower() in {"1", "true", "yes"}

if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOCAL_TEACHER_HOST = os.environ.get("SHIP_TEACHER_HOST", "127.0.0.1")
LOCAL_TEACHER_PORTS = (
    os.environ.get("SHIP_TEACHER_PORTS")
    or os.environ.get("TEACHER_PORTS")
    or "8000,8001,8002,8003,8004,8005"
)
LOCAL_TEACHER_MODEL = os.environ.get("SHIP_TEACHER_MODEL", "local-teacher")
LOCAL_TEACHER_TIMEOUT = int(os.environ.get("SHIP_TEACHER_TIMEOUT", "360"))

PROVIDER_CONFIG = {
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "timeout": 45,
    },
    "cerebras": {
        "model": "llama3.1-8b",
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "timeout": 60,
    },
    "local": {
        "model": LOCAL_TEACHER_MODEL,
        "url": "",
        "timeout": LOCAL_TEACHER_TIMEOUT,
    },
}

CITATION_TERMS = (
    "solas",
    "marpol",
    "stcw",
    "colreg",
    "ism",
    "isps",
    "mlc",
    "fss code",
    "lsa code",
    "iamsar",
)

ESCALATION_TERMS = (
    "master",
    "chief engineer",
    "bridge",
    "raise the alarm",
    "report",
    "stop",
    "isolate",
    "evacuate",
    "permit",
    "standby",
)

CALCULATION_UNITS = (
    "bar",
    "kw",
    "rpm",
    "mm",
    "c",
    "°c",
    "%",
    "ppm",
    "kn",
    "nm",
    "tonne",
    "m3",
    "kg",
)

DANGEROUS_PHRASES = (
    "ignore the alarm",
    "skip the permit",
    "enter alone",
    "no gas test",
    "no need to inform",
    "use water on the oil fire",
)

SAMPLE_TYPES = {
    "engineering": ("troubleshooting", "procedure", "calculation", "wrong_action"),
    "safety": ("emergency", "wrong_action", "procedure", "recovery"),
    "regulation": ("compliance", "inspection", "documentation", "wrong_action"),
    "cargo": ("procedure", "inspection", "troubleshooting", "wrong_action"),
}

SCENARIO_CLASS = {
    "troubleshooting": "abnormal",
    "procedure": "routine",
    "calculation": "calculation",
    "wrong_action": "emergency",
    "emergency": "emergency",
    "recovery": "abnormal",
    "compliance": "regulatory",
    "inspection": "regulatory",
    "documentation": "regulatory",
}


@dataclass(frozen=True)
class Task:
    domain_letter: str
    domain_name: str
    bucket: str
    subtopic_id: str
    subtopic: str
    sample_type: str
    criticality: str
    ordinal: int
    attempt: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing syllabus-aligned maritime QA data."
    )
    parser.add_argument(
        "--preset",
        default="shipboard_30k",
        choices=sorted(PRESETS),
    )
    parser.add_argument(
        "--focus",
        default="engineering,safety,regulation",
        help="Comma-separated focus buckets.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional cap on the total number of new samples for this run.",
    )
    parser.add_argument(
        "--domains",
        help="Optional comma-separated domain letters to restrict generation.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=24,
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--providers",
        default="groq,cerebras",
        help="Comma-separated provider list. Options: local, groq, cerebras.",
    )
    parser.add_argument(
        "--account-shard-index",
        type=int,
        default=0,
        help="0-based shard index for account slicing.",
    )
    parser.add_argument(
        "--account-shard-count",
        type=int,
        default=1,
        help="Total number of account shards.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def prompt_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_accounts(
    allowed_providers: set[str] | None = None,
    shard_index: int = 0,
    shard_count: int = 1,
) -> list[dict[str, str]]:
    workers: list[dict[str, str]] = []
    if shard_count < 1:
        raise ValueError("account_shard_count must be >= 1")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("account_shard_index must be in [0, account_shard_count)")

    if allowed_providers and "local" in allowed_providers:
        ports = [part.strip() for part in str(LOCAL_TEACHER_PORTS).split(",") if part.strip()]
        if not ports:
            raise ValueError(
                "No local teacher ports configured (SHIP_TEACHER_PORTS/TEACHER_PORTS)."
            )
        # Optional sharding across ports for multi-process runs.
        ports = ports[shard_index::shard_count]
        for port in ports:
            workers.append(
                {
                    "provider": "local",
                    "api_key": "",
                    "model": PROVIDER_CONFIG["local"]["model"],
                    "url": f"http://{LOCAL_TEACHER_HOST}:{port}/v1/chat/completions",
                }
            )

    api_providers = {"groq", "cerebras"}
    wants_accounts = (
        not allowed_providers or bool(api_providers.intersection(allowed_providers))
    )
    if wants_accounts and ACCOUNTS_FILE.exists():
        raw = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        accounts = raw.get("accounts", [])
        sliced_accounts = accounts[shard_index::shard_count]
        for account in sliced_accounts:
            for provider, key_name in (
                ("groq", "groq_api_key"),
                ("cerebras", "cerebras_api_key"),
            ):
                if allowed_providers and provider not in allowed_providers:
                    continue
                api_key = account.get(key_name)
                if api_key:
                    workers.append(
                        {
                            "provider": provider,
                            "api_key": api_key,
                            "model": PROVIDER_CONFIG[provider]["model"],
                        }
                    )
    return workers



def load_exemplars() -> dict[str, list[dict]]:
    exemplars: dict[str, list[dict]] = {}
    for domain in DOMAIN_TO_BUCKET:
        records: list[dict] = []
        domain_file = GOLD_ROOT / f"domain_{domain}.jsonl"
        if domain_file.exists():
            with domain_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if record.get("prompt") and record.get("response"):
                        records.append(record)
        exemplars[domain] = records
    return exemplars


def load_existing_hashes(exemplars: dict[str, list[dict]]) -> set[str]:
    hashes = set()
    for records in exemplars.values():
        for record in records:
            hashes.add(prompt_hash(record["prompt"]))

    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("prompt"):
                    hashes.add(prompt_hash(record["prompt"]))
    return hashes


def criticality_for_domain(domain: str, bucket: str) -> str:
    if bucket in {"safety", "regulation"}:
        return "critical"
    if domain in {"A", "D", "H", "J"}:
        return "high"
    return "medium"


def build_tasks(
    syllabus: dict[str, dict],
    focus: tuple[str, ...],
    preset: str,
    existing_counts: dict[str, int],
    requested_domains: set[str] | None,
    limit: int | None,
) -> list[Task]:
    targets = compute_domain_targets(
        syllabus,
        preset=preset,
        focus_buckets=focus,
        existing_counts=existing_counts,
    )
    rows = build_domain_rows(syllabus, targets, existing_counts)
    per_domain_tasks: dict[str, list[Task]] = {}

    for row in rows:
        if requested_domains and row.domain not in requested_domains:
            continue
        if row.deficit <= 0:
            continue

        subtopics = list(syllabus[row.domain]["Subcategories"].items())
        sample_types = SAMPLE_TYPES[row.bucket]
        tasks_for_domain: list[Task] = []
        for ordinal in range(row.deficit):
            subtopic_id, subtopic = subtopics[ordinal % len(subtopics)]
            sample_type = sample_types[(ordinal // len(subtopics)) % len(sample_types)]
            tasks_for_domain.append(
                Task(
                    domain_letter=row.domain,
                    domain_name=row.domain_name,
                    bucket=row.bucket,
                    subtopic_id=subtopic_id,
                    subtopic=subtopic,
                    sample_type=sample_type,
                    criticality=criticality_for_domain(row.domain, row.bucket),
                    ordinal=ordinal + 1,
                )
            )
        per_domain_tasks[row.domain] = tasks_for_domain

    ordered_domains = [
        domain
        for domain in PRIORITY_ORDER
        if domain in per_domain_tasks
    ]
    tasks: list[Task] = []
    round_index = 0
    while ordered_domains:
        next_round: list[str] = []
        for domain in ordered_domains:
            domain_tasks = per_domain_tasks[domain]
            if round_index < len(domain_tasks):
                tasks.append(domain_tasks[round_index])
                next_round.append(domain)
                if limit is not None and len(tasks) >= limit:
                    return tasks
        ordered_domains = next_round
        round_index += 1

    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def choose_exemplars(domain_letter: str, exemplars: dict[str, list[dict]]) -> list[dict]:
    records = exemplars.get(domain_letter, [])
    if len(records) <= 2:
        return records
    return random.sample(records, 2)


def build_prompt(task: Task, examples: list[dict]) -> str:
    example_text = []
    for index, sample in enumerate(examples, start=1):
        example_text.append(
            f"Example {index} prompt:\n{sample['prompt']}\n\n"
            f"Example {index} response:\n{sample['response']}\n"
        )

    sample_type_instruction = {
        "troubleshooting": "Make the user describe a symptom, alarm, or abnormal condition that requires diagnosis.",
        "procedure": "Make the answer an operational checklist with clear sequencing.",
        "calculation": "Include at least one worked number, threshold, or unit-based check.",
        "wrong_action": "Challenge an unsafe suggestion and correct it explicitly.",
        "emergency": "Treat it as an immediate emergency with first actions and escalation.",
        "recovery": "Focus on follow-up actions after the initial response stabilizes the situation.",
        "compliance": "Focus on whether the vessel or crew is compliant and what evidence is required.",
        "inspection": "Frame it as an onboard inspection, deficiency, or survey preparation issue.",
        "documentation": "Require documents, records, permits, or log entries to be addressed.",
    }[task.sample_type]

    return f"""You are writing one gold-standard maritime training sample for a shipboard assistant.

Domain letter: {task.domain_letter}
Domain name: {task.domain_name}
Subtopic ID: {task.subtopic_id}
Subtopic: {task.subtopic}
Training bucket: {task.bucket}
Sample type: {task.sample_type}
Criticality: {task.criticality}

Return ONLY valid JSON with these keys:
{{
  "prompt": "",
  "response": "",
  "required_inputs": [],
  "escalation_triggers": [],
  "escalation_targets": [],
  "source_refs": [{{"instrument": "", "clause": "", "edition": "", "status": "mandatory|guidance|company"}}]
}}

Requirements:
- The prompt must sound like a real officer, engineer, or operator speaking from onboard operations.
- The response must start with <think> and must include </think>.
- Inside <think>, use exactly four numbered lines:
  1. Context
  2. Logic
  3. Numbers / limits
  4. Citation
- After </think>, give the visible answer as numbered shipboard actions.
- The visible answer must include one explicit line that begins with "Do not:".
- {sample_type_instruction}
- Match the style density and operational tone of the examples.
- If the domain is safety or regulation related, include escalation, stop conditions, and a clear unsafe action to avoid.
- Cite only high-confidence maritime authorities such as SOLAS, MARPOL, STCW, COLREG, ISM Code, ISPS Code, MLC, FSS Code, LSA Code, IAMSAR, or OEM manuals. If unsure, cite the code family rather than inventing a clause number.
- Do not mention being an AI.
- Do not return markdown fences.

{chr(10).join(example_text)}
Generate the JSON now."""


def extract_json_object(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def call_provider(
    prompt: str,
    provider: str,
    api_key: str,
    model: str,
    url: str | None = None,
) -> str | None:
    config = PROVIDER_CONFIG[provider]
    request_url = url or config["url"]
    if not request_url:
        raise RuntimeError("missing_request_url")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1500,
    }
    if provider == "groq":
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = requests.post(
        request_url,
        headers=headers,
        json=payload,
        timeout=config["timeout"],
        verify=SSL_VERIFY,
    )

    if response.status_code == 429:
        raise RuntimeError("rate_limited")
    if response.status_code >= 400:
        raise RuntimeError(f"http_{response.status_code}")

    data = response.json()
    return data["choices"][0]["message"]["content"]



def subtopic_tokens(task: Task) -> list[str]:
    tokens = []
    for token in re.split(r"[^A-Za-z0-9]+", task.subtopic.lower()):
        if len(token) >= 5 and token not in {"series", "system", "engine", "ships"}:
            tokens.append(token)
    return tokens[:8]


def validate_sample(task: Task, record: dict, seen_hashes: set[str]) -> list[str]:
    issues: list[str] = []
    prompt = str(record.get("prompt", "")).strip()
    response = str(record.get("response", "")).strip()
    body = f"{prompt} {response}".lower()

    if len(prompt) < 35:
        issues.append("prompt_too_short")
    if len(response) < 250:
        issues.append("response_too_short")
    if not response.startswith("<think>"):
        issues.append("missing_think_open")
    if response.count("<think>") != 1 or response.count("</think>") != 1:
        issues.append("invalid_think_block")
    if "</think>" not in response:
        issues.append("missing_think_close")
    else:
        final_answer = response.split("</think>", 1)[1].strip()
        if len(final_answer) < 80:
            issues.append("weak_final_answer")

    if prompt_hash(prompt) in seen_hashes:
        issues.append("duplicate_prompt")

    anchor_tokens = subtopic_tokens(task)
    if anchor_tokens and not any(token in body for token in anchor_tokens):
        issues.append("weak_subtopic_grounding")

    if task.bucket == "regulation":
        if not any(term in body for term in CITATION_TERMS):
            issues.append("missing_regulatory_citation")
        if not record.get("source_refs"):
            issues.append("missing_source_refs")

    if task.criticality == "critical":
        if not any(term in body for term in ESCALATION_TERMS):
            issues.append("missing_escalation")
        if not record.get("escalation_targets"):
            issues.append("missing_escalation_targets")

    if task.sample_type == "calculation":
        if not re.search(r"\d", response):
            issues.append("missing_numeric_work")
        if not any(unit in body for unit in CALCULATION_UNITS):
            issues.append("missing_units")

    if task.sample_type in {"wrong_action", "emergency"} and not any(
        phrase in body for phrase in ("do not", "never", "unsafe", "wrong")
    ):
        issues.append("missing_unsafe_action_guardrail")

    if any(phrase in body for phrase in DANGEROUS_PHRASES):
        issues.append("dangerous_phrase_present")

    return issues


def write_jsonl(path: Path, payload: dict, lock: threading.Lock) -> None:
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def save_stats(stats: dict, lock: threading.RLock) -> None:
    with lock:
        STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATS_FILE.write_text(json.dumps(stats, indent=2), encoding="utf-8")


def authority_scope(task: Task) -> str:
    if task.domain_letter == "X":
        return "medical"
    if task.bucket == "engineering":
        return "engine"
    if task.bucket in {"safety", "regulation"}:
        return "mixed"
    return "deck"


def build_output_record(task: Task, provider: str, model: str, parsed: dict) -> dict:
    required_inputs = parsed.get("required_inputs") or []
    escalation_triggers = parsed.get("escalation_triggers") or []
    escalation_targets = parsed.get("escalation_targets") or []
    source_refs = parsed.get("source_refs") or []
    return {
        "sample_id": hashlib.sha1(
            f"{task.domain_letter}|{task.subtopic_id}|{parsed['prompt']}".encode("utf-8")
        ).hexdigest()[:16],
        "domain_letter": task.domain_letter,
        "domain_name": task.domain_name,
        "bucket": task.bucket,
        "subtopic_id": task.subtopic_id,
        "subtopic": task.subtopic,
        "sample_type": task.sample_type,
        "topic_tags": [task.domain_letter, task.subtopic_id, task.bucket, task.sample_type],
        "scenario_class": SCENARIO_CLASS[task.sample_type],
        "risk_level": task.criticality,
        "vessel_context": {
            "vessel_type": "",
            "operation_phase": "",
            "cargo_or_equipment": "",
        },
        "authority_scope": authority_scope(task),
        "jurisdiction_scope": {
            "imo": True,
            "flag_state": "",
            "coastal_or_port": "",
            "company_sms_required": task.bucket in {"safety", "regulation"},
        },
        "required_inputs": required_inputs,
        "escalation_triggers": escalation_triggers,
        "escalation_targets": escalation_targets,
        "source_refs": source_refs,
        "calc_schema": {
            "formula": "",
            "units": "",
            "expected_result": "",
            "tolerance": "",
            "rounding_rule": "conservative",
        }
        if task.sample_type == "calculation"
        else None,
        "response_format": "think_then_answer_v1",
        "human_review_required": task.criticality == "critical" or task.sample_type == "calculation",
        "provider": provider,
        "model": model,
        "generated_at": now_iso(),
        "prompt": parsed["prompt"].strip(),
        "response": parsed["response"].strip(),
    }


def worker_loop(
    account: dict[str, str],
    tasks: queue.Queue,
    exemplars: dict[str, list[dict]],
    seen_hashes: set[str],
    seen_hashes_lock: threading.Lock,
    write_lock: threading.Lock,
    stats_lock: threading.RLock,
    stats: dict,
    max_attempts: int,
) -> None:
    provider = account["provider"]
    api_key = account["api_key"]
    model = account["model"]

    while True:
        try:
            task = tasks.get(timeout=2)
        except queue.Empty:
            return

        examples = choose_exemplars(task.domain_letter, exemplars)
        prompt = build_prompt(task, examples)

        try:
            content = call_provider(prompt, provider, api_key, model, url=account.get("url"))
            parsed = extract_json_object(content or "")
            if parsed is None:
                raise ValueError("invalid_json")

            with seen_hashes_lock:
                issues = validate_sample(task, parsed, seen_hashes)
                if not issues:
                    seen_hashes.add(prompt_hash(parsed["prompt"]))

            if issues:
                write_jsonl(
                    REJECT_FILE,
                    {
                        **asdict(task),
                        "provider": provider,
                        "model": model,
                        "generated_at": now_iso(),
                        "issues": issues,
                        "raw": parsed,
                    },
                    write_lock,
                )
                if task.attempt + 1 < max_attempts:
                    tasks.put(Task(**{**asdict(task), "attempt": task.attempt + 1}))
                else:
                    with stats_lock:
                        stats["rejected"] += 1
                        stats["rejections_by_issue"].extend(issues)
                        save_stats(stats, stats_lock)
                continue

            output = build_output_record(task, provider, model, parsed)
            write_jsonl(OUTPUT_FILE, output, write_lock)

            with stats_lock:
                stats["accepted"] += 1
                stats["accepted_by_domain"][task.domain_letter] = (
                    stats["accepted_by_domain"].get(task.domain_letter, 0) + 1
                )
                stats["accepted_by_bucket"][task.bucket] = (
                    stats["accepted_by_bucket"].get(task.bucket, 0) + 1
                )
                stats["accepted_by_provider"][provider] = (
                    stats["accepted_by_provider"].get(provider, 0) + 1
                )
                if stats["accepted"] % 25 == 0:
                    save_stats(stats, stats_lock)

        except Exception as exc:
            write_jsonl(
                REJECT_FILE,
                {
                    **asdict(task),
                    "provider": provider,
                    "model": model,
                    "generated_at": now_iso(),
                    "issues": [str(exc)],
                },
                write_lock,
            )
            if task.attempt + 1 < max_attempts:
                tasks.put(Task(**{**asdict(task), "attempt": task.attempt + 1}))
            else:
                with stats_lock:
                    stats["failed"] += 1
                    save_stats(stats, stats_lock)
        finally:
            tasks.task_done()
            if provider == "local":
                time.sleep(0.05)
            elif provider == "groq":
                time.sleep(1.0)
            else:
                time.sleep(1.4)


def main() -> None:
    args = parse_args()
    focus = tuple(part.strip() for part in args.focus.split(",") if part.strip())
    providers = {part.strip() for part in args.providers.split(",") if part.strip()}
    requested_domains = None
    if args.domains:
        requested_domains = {part.strip().upper() for part in args.domains.split(",") if part.strip()}

    syllabus = load_syllabus(SYLLABUS_FILE)
    exemplars = load_exemplars()
    existing = existing_domain_counts(GOLD_ROOT, OUTPUT_FILE)
    tasks_to_run = build_tasks(
        syllabus=syllabus,
        focus=focus,
        preset=args.preset,
        existing_counts=existing,
        requested_domains=requested_domains,
        limit=args.limit,
    )

    targets = compute_domain_targets(
        syllabus,
        preset=args.preset,
        focus_buckets=focus,
        existing_counts=existing,
    )
    plan_payload = {
        "generated_at": now_iso(),
        "preset": args.preset,
        "focus": list(focus),
        "requested_domains": sorted(requested_domains) if requested_domains else None,
        "task_count": len(tasks_to_run),
        "domains": [
            {
                "domain": row.domain,
                "bucket": row.bucket,
                "current": row.current,
                "target": row.target,
                "deficit": row.deficit,
                "subtopics": row.subtopics,
                "domain_name": row.domain_name,
            }
            for row in build_domain_rows(syllabus, targets, existing)
        ],
    }
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(plan_payload, indent=2), encoding="utf-8")

    if args.dry_run:
        print(f"Dry run: {len(tasks_to_run):,} tasks")
        for task in tasks_to_run[:20]:
            print(
                f"- {task.domain_letter} {task.subtopic_id} "
                f"{task.sample_type:14} {task.criticality:8} {task.subtopic}"
            )
        return

    accounts = load_accounts(
        providers,
        shard_index=args.account_shard_index,
        shard_count=args.account_shard_count,
    )
    if not accounts:
        raise SystemExit("No workers available for selected providers. Use --providers local (with teacher servers running) or add API keys to accounts_MASTER.json.")

    worker_count = min(args.max_workers, len(accounts), max(1, len(tasks_to_run)))
    work_queue: queue.Queue = queue.Queue()
    for task in tasks_to_run:
        work_queue.put(task)

    seen_hashes = load_existing_hashes(exemplars)
    seen_hashes_lock = threading.Lock()
    write_lock = threading.Lock()
    stats_lock = threading.RLock()
    stats = {
        "started_at": now_iso(),
        "preset": args.preset,
        "focus": list(focus),
        "accepted": 0,
        "rejected": 0,
        "failed": 0,
        "accepted_by_domain": {},
        "accepted_by_bucket": {},
        "accepted_by_provider": {},
        "rejections_by_issue": [],
    }
    save_stats(stats, stats_lock)

    threads = []
    for index in range(worker_count):
        thread = threading.Thread(
            target=worker_loop,
            args=(
                accounts[index],
                work_queue,
                exemplars,
                seen_hashes,
                seen_hashes_lock,
                write_lock,
                stats_lock,
                stats,
                args.max_attempts,
            ),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    with stats_lock:
        stats["finished_at"] = now_iso()
        save_stats(stats, stats_lock)

    print(
        f"Accepted={stats['accepted']:,} "
        f"Rejected={stats['rejected']:,} "
        f"Failed={stats['failed']:,}"
    )


if __name__ == "__main__":
    main()
