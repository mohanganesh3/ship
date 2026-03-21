#!/home/mohanganesh/ship/.venv/bin/python

import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

import argparse
import requests

PIPE_LOG = "/home/mohanganesh/ship/logs/pipeline_execution.log"

FORBIDDEN = [
    "as an ai",
    "i cannot",
    "language model",
    "my training data",
    "i don't have access",
]

REQUIRED_KEYWORDS = [
    "sulphur",
    "nox",
    "sox",
    "air pollution",
    "emissions",
    "annex vi",
]

SYSTEM = "You are a maritime expert. /no_think"
USER = "What does MARPOL Annex VI regulate? Answer in 30 words maximum."


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_line(line: str) -> None:
    with open(PIPE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts()}] {line}\n")


def word_count(text: str) -> int:
    return len([w for w in text.strip().split() if w])


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ports",
        default="8000,8001",
        help="Comma-separated list of teacher ports to validate (default: 8000,8001)",
    )
    ap.add_argument(
        "--max-attempts",
        type=int,
        default=40,
        help="Max request attempts per port while waiting for readiness (default: 40)",
    )
    ap.add_argument(
        "--sleep-seconds",
        type=int,
        default=30,
        help="Sleep between attempts while waiting for readiness (default: 30)",
    )
    return ap.parse_args()

def validate_content(content: str) -> List[str]:
    issues: List[str] = []
    if not content or not content.strip():
        issues.append("empty response")
        return issues

    wc = word_count(content)
    if wc > 50:
        issues.append(f"word_count_exceeded({wc} > 50)")

    low = content.lower()
    for bad in FORBIDDEN:
        if bad in low:
            issues.append(f"forbidden_phrase({bad})")

    if not any(k in low for k in REQUIRED_KEYWORDS):
        issues.append("missing_required_keyword")

    return issues


def call_instance(port: int) -> Dict:
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    payload = {
        "model": "teacher",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "temperature": 0.2,
        "max_tokens": 120,
    }

    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()


def extract_content(data: Dict) -> str:
    # OpenAI-compatible response: choices[0].message.content
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


def main() -> int:
    args = parse_args()
    ports = [int(p.strip()) for p in args.ports.split(",") if p.strip()]
    if not ports:
        print("No ports provided")
        return 2

    log_line(
        "STEP1.3 validate_teacher.py: starting validation gate for ports " + ",".join(str(p) for p in ports)
    )

    # The 235B MoE model can take several minutes to fully load; be patient and retry.
    max_attempts = args.max_attempts
    sleep_seconds = args.sleep_seconds
    all_pass = True

    for port in ports:
        print(f"--- Validating port {port} ---")

        last_err = None
        data = None
        for attempt in range(1, max_attempts + 1):
            try:
                data = call_instance(port)
                break
            except Exception as e:
                last_err = e
                msg = f"port {port}: not ready (attempt {attempt}/{max_attempts}): {e}"
                print(msg)
                log_line(msg)
                if attempt < max_attempts:
                    time.sleep(sleep_seconds)

        if data is None:
            all_pass = False
            msg = f"FAIL port {port}: request_error_after_retries: {last_err}"
            print(msg)
            log_line(msg)
            continue

        content = extract_content(data)

        issues = validate_content(content)
        if issues:
            all_pass = False
            msg = f"FAIL port {port}: {', '.join(issues)}"
            print(msg)
            log_line(msg)
            # Print a short snippet for debugging.
            snippet = content.strip().replace("\n", " ")[:200]
            print(f"Response snippet: {snippet!r}")
        else:
            msg = f"PASS port {port}"
            print(msg)
            log_line(msg)

    if all_pass:
        print("GATE: PASS (all instances)")
        log_line("GATE Step1.3: PASS")
        return 0

    print("GATE: FAIL (one or more instances failed)")
    log_line("GATE Step1.3: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
