#!/usr/bin/env python3
"""Verify the training venv is usable on this machine.

This script is meant to be run via `scripts/train_python.sh` so the correct
LD_LIBRARY_PATH and DeepSpeed env vars are set.

Checks:
- Python + Torch version
- CUDA availability + GPU names
- Unsloth import
- Tiny QLoRA load test:
  - Load local model weights in 4-bit
  - Attach LoRA adapters
  - Run a short generation

Exit codes:
- 0: success
- 1: failure
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-path",
        default=os.environ.get("STUDENT_MODEL_PATH", "models/student-1.7b"),
        help="Local path to the student HF weights directory (default: models/student-1.7b)",
    )
    parser.add_argument("--max-seq-len", type=int, default=128)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    print("python", sys.version.split()[0])

    import torch  # noqa: WPS433

    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    print("device_count", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f"gpu[{i}]", torch.cuda.get_device_name(i))

    try:
        import unsloth  # noqa: F401, WPS433
        from unsloth import FastLanguageModel  # noqa: WPS433

        print("unsloth_import", "ok")

        model_path = os.path.abspath(args.model_path)
        print("model_path", model_path)
        if not os.path.isdir(model_path):
            eprint(f"ERROR: model path does not exist or is not a directory: {model_path}")
            return 1

        try:
            # Minimal 4-bit load via Unsloth (fast path).
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=model_path,
                max_seq_length=args.max_seq_len,
                dtype=None,
                load_in_4bit=True,
            )

            # Attach LoRA adapters (tiny config; this is just a smoke test).
            model = FastLanguageModel.get_peft_model(
                model,
                r=8,
                target_modules=[
                    "q_proj",
                    "k_proj",
                    "v_proj",
                    "o_proj",
                    "gate_proj",
                    "up_proj",
                    "down_proj",
                ],
                lora_alpha=16,
                lora_dropout=0.0,
                bias="none",
                use_gradient_checkpointing=False,
                random_state=3407,
            )

            FastLanguageModel.for_inference(model)
            prompt = "### Instruction\nSay hello in one sentence.\n\n### Response\n"
            inputs = tokenizer([prompt], return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.to("cuda") for k, v in inputs.items()}

            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                )

            text = tokenizer.decode(out[0], skip_special_tokens=True)
            print("qlora_path", "unsloth")
            print("generation_ok", True)
            print("generation_sample", text[:300].replace("\n", "\\n"))

        except NotImplementedError as nie:
            # Unsloth doesn't support every architecture yet (e.g., Qwen3).
            # Fall back to a standard Transformers-based smoke test.
            # We *prefer* 4-bit QLoRA, but on Tesla K80 (Kepler, sm_37) bitsandbytes
            # CUDA kernels are often unsupported. If 4-bit fails, we degrade to
            # fp16 LoRA to still validate the training stack can load + attach LoRA.
            print("qlora_path", "transformers_peft")
            print("unsloth_model_support", "no")
            print("unsloth_reason", str(nie).splitlines()[0])

            from transformers import (  # noqa: WPS433
                AutoModelForCausalLM,
                AutoTokenizer,
            )
            from peft import LoraConfig, get_peft_model  # noqa: WPS433

            tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

            qlora_4bit_ok = False
            qlora_4bit_error: str | None = None
            model = None

            if torch.cuda.is_available():
                # bitsandbytes 4-bit kernels generally require >= sm_50.
                # Tesla K80 is sm_37 (Kepler) and tends to crash/hard-fail.
                cap = torch.cuda.get_device_capability(0)
                if cap < (5, 0):
                    qlora_4bit_error = f"compute_capability {cap[0]}.{cap[1]} < 5.0 (4-bit bitsandbytes unsupported)"
                else:
                    try:
                        from transformers import BitsAndBytesConfig  # noqa: WPS433

                        bnb_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4",
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_compute_dtype=torch.float16,
                        )
                        model = AutoModelForCausalLM.from_pretrained(
                            model_path,
                            quantization_config=bnb_config,
                            device_map="auto",
                            torch_dtype=torch.float16,
                            low_cpu_mem_usage=True,
                        )
                        qlora_4bit_ok = True
                    except Exception as qexc:  # noqa: BLE001
                        qlora_4bit_error = repr(qexc)
                        model = None

            if model is None:
                # fp16 fallback (LoRA, not QLoRA)
                model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    device_map="auto" if torch.cuda.is_available() else None,
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                )

            print("qlora_4bit_ok", qlora_4bit_ok)
            if qlora_4bit_error is not None:
                print("qlora_4bit_error", qlora_4bit_error)

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

            prompt = "### Instruction\nSay hello in one sentence.\n\n### Response\n"
            inputs = tokenizer([prompt], return_tensors="pt")
            if torch.cuda.is_available():
                device = next(model.parameters()).device
                inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=False,
                )

            text = tokenizer.decode(out[0], skip_special_tokens=True)
            print("generation_ok", True)
            print("generation_sample", text[:300].replace("\n", "\\n"))

        print("VERIFY_TRAIN_ENV", "PASS")
        return 0

    except Exception as exc:  # noqa: BLE001
        eprint("VERIFY_TRAIN_ENV", "FAIL")
        eprint("error", repr(exc))
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
