#!/usr/bin/env python3
"""Verify the *fp16* Transformers/PEFT/DeepSpeed training stack.

This repository intentionally does **not** use Unsloth or bitsandbytes (4-bit)
because Tesla K80 (sm_37) is incompatible with common 4-bit CUDA kernels.

Run this via `scripts/train_python.sh` so LD_LIBRARY_PATH + DeepSpeed flags are
set appropriately.

Checks:
- Python + Torch versions
- CUDA availability + GPU names + compute capability
- Imports + versions: transformers, peft, trl, accelerate, datasets, deepspeed
- Local model fp16 load on cuda:0 (Qwen3-1.7B by default)
- Attach PEFT LoRA adapters
- Forward pass loss + VRAM usage + trainable parameter counts

Exit codes:
- 0: success
- 1: failure
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback


def _pick_default_model_path() -> str:
    # Keep backward compatibility with older env var / paths.
    candidates = [
        os.environ.get("STUDENT_MODEL_PATH"),
        "models/student/student-1.7b",
        "models/student-1.7b",
        "models/student",
    ]
    for c in candidates:
        if not c:
            continue
        if os.path.isdir(c):
            return c
    # Fall back to the first non-empty candidate, even if missing, so we can
    # produce a helpful error message.
    return os.environ.get("STUDENT_MODEL_PATH", "models/student/student-1.7b")


def _count_params(model) -> tuple[int, int]:
    total = 0
    trainable = 0
    for p in model.parameters():
        n = p.numel()
        total += n
        if p.requires_grad:
            trainable += n
    return total, trainable


def _print_vram(prefix: str, device_index: int = 0) -> None:
    import torch  # noqa: WPS433

    if not torch.cuda.is_available():
        return
    alloc = torch.cuda.memory_allocated(device_index)
    reserved = torch.cuda.memory_reserved(device_index)
    peak = torch.cuda.max_memory_allocated(device_index)
    print(f"{prefix}_vram_alloc_bytes", int(alloc))
    print(f"{prefix}_vram_reserved_bytes", int(reserved))
    print(f"{prefix}_vram_peak_alloc_bytes", int(peak))


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path",
        default=_pick_default_model_path(),
        help="Local path to the student HF weights directory",
    )
    parser.add_argument(
        "--prompt",
        default="### Instruction\nSay hello in one sentence.\n\n### Response\n",
        help="Prompt used for the forward-pass loss smoke test.",
    )
    parser.add_argument("--max-seq-len", type=int, default=128)
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    print("python", sys.version.split()[0])

    import torch  # noqa: WPS433

    print("torch", torch.__version__)
    print("torch_cuda", getattr(torch.version, "cuda", None))
    print("cuda_available", torch.cuda.is_available())
    print("device_count", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f"gpu[{i}]", torch.cuda.get_device_name(i))
        try:
            cap = torch.cuda.get_device_capability(i)
            print(f"gpu[{i}]_capability", f"{cap[0]}.{cap[1]}")
        except Exception:  # noqa: BLE001
            pass

    # Package imports/versions (requested stack).
    import transformers  # noqa: WPS433
    import peft  # noqa: WPS433
    import trl  # noqa: WPS433
    import accelerate  # noqa: WPS433
    import datasets  # noqa: WPS433
    import deepspeed  # noqa: WPS433

    print("transformers", transformers.__version__)
    print("peft", peft.__version__)
    print("trl", trl.__version__)
    print("accelerate", accelerate.__version__)
    print("datasets", datasets.__version__)
    print("deepspeed", deepspeed.__version__)

    try:
        model_path = os.path.abspath(args.model_path)
        print("model_path", model_path)
        if not os.path.isdir(model_path):
            eprint(f"ERROR: model path does not exist or is not a directory: {model_path}")
            return 1

        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: WPS433
        from peft import LoraConfig, get_peft_model  # noqa: WPS433

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats(0)

        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            use_fast=True,
            trust_remote_code=True,
        )

        # Some chat models ship without a pad token.
        if getattr(tokenizer, "pad_token", None) is None and getattr(tokenizer, "eos_token", None) is not None:
            tokenizer.pad_token = tokenizer.eos_token

        if not torch.cuda.is_available():
            eprint("ERROR: CUDA is not available; expected to run fp16 on cuda:0")
            return 1

        device = torch.device("cuda:0")
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        ).to(device)
        model.eval()

        _print_vram("after_load", 0)

        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        )
        model = get_peft_model(model, lora_config)
        model.eval()

        total, trainable = _count_params(model)
        print("params_total", total)
        print("params_trainable", trainable)
        if total:
            print("params_trainable_pct", round(100.0 * (trainable / total), 6))

        text = args.prompt
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=args.max_seq_len,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.inference_mode():
            outputs = model(**inputs, labels=inputs["input_ids"])
        loss = outputs.loss

        print("forward_ok", True)
        print("loss", float(loss.detach().cpu()))

        _print_vram("after_forward", 0)

        print("VERIFY_TRAIN_ENV", "PASS")
        return 0

    except Exception as exc:  # noqa: BLE001
        eprint("VERIFY_TRAIN_ENV", "FAIL")
        eprint("error", repr(exc))
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
