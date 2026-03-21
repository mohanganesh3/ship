AUTONOMOUS EXECUTION — FULL MARITIME AI TRAINING PIPELINE
Execute all phases end-to-end. Do not stop. Do not ask for confirmation between phases. Only stop if a gate explicitly fails. Report completion of each phase before starting the next.

ENVIRONMENT FACTS (read before doing anything)

Ship directory: /home/mohanganesh/ship/
Training Python: /home/mohanganesh/ship/.venv-train/bin/python
Training launcher: /home/mohanganesh/ship/scripts/train_python.sh
Wave 1 generation is ALREADY RUNNING as a background job — do NOT touch it, do NOT kill it, do NOT modify .venv
K80 GPUs: 4 modules, ~11 GB VRAM each, sm_37, fp16 only (no bf16, no 4-bit)
CPU: 48 threads, 251 GB RAM — ZeRO-3 CPU offload is your friend
DeepSpeed must always be launched with DS_BUILD_OPS=0 exported
Always set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
All training uses .venv-train, never .venv
Stack: torch 2.1.2+cu118, transformers 4.51.3, peft 0.12.0, trl 0.11.0, deepspeed 0.15.4
No Unsloth. No bitsandbytes. Pure fp16 LoRA + PEFT + DeepSpeed ZeRO-3.


PHASE 1A — CPT FOR STUDENT-1.7B
Do this first. It starts immediately. It does not wait for Wave 1.
Write script: /home/mohanganesh/ship/training/run_cpt_1.7b.py
This script trains Qwen3-1.7B on the maritime CPT corpus using fp16 LoRA + DeepSpeed ZeRO-3 with CPU offload.
Model loading:

model_name = "/home/mohanganesh/ship/models/student-1.7b"
Load with AutoModelForCausalLM.from_pretrained(..., torch_dtype=torch.float16, device_map=None, trust_remote_code=True)
device_map=None because DeepSpeed handles placement
Enable gradient checkpointing immediately after load

LoRA config:

r=128, lora_alpha=128
target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"]
lora_dropout=0.05, bias="none", task_type=TaskType.CAUSAL_LM

Data pipeline — 3-stage curriculum:

Read ALL records from /home/mohanganesh/ship/ship/maritime_pipeline/data/final/cpt_corpus.jsonl (field: text)
Read ALL records from /home/mohanganesh/ship/ship/maritime_pipeline/data/final/general_replay.jsonl (field: text)
Stage 1 (first 10% of total training steps): sample 50% maritime, 50% general per batch
Stage 2 (steps 10% to 85%): sample 80% maritime, 20% general per batch
Stage 3 (final 15% of steps): sample 70% maritime, 30% general per batch
Pack text into sequences of max 2048 tokens. Concatenate documents separated by EOS token. No padding.

Training hyperparameters:

learning_rate=2e-5
warmup_ratio=0.03
weight_decay=0.01
max_seq_length=2048
per_device_train_batch_size=1
gradient_accumulation_steps=16
num_train_epochs=3
lr_scheduler_type="cosine"
fp16=True, bf16=False
save_steps=500
logging_steps=25
dataloader_num_workers=4

Perplexity monitoring (every 500 steps):

Compute perplexity on /home/mohanganesh/ship/ship/maritime_pipeline/data/final/cpt_val_maritime.jsonl
Compute perplexity on /home/mohanganesh/ship/ship/maritime_pipeline/data/final/cpt_val_general.jsonl
Log to /home/mohanganesh/ship/logs/cpt_perplexity_1.7b.jsonl as JSON lines: {"step": N, "maritime_ppl": X, "general_ppl": Y, "ts": "..."}

Checkpoints: save to /home/mohanganesh/ship/training/checkpoints/cpt-1.7b/
Support --dry-run flag: runs exactly 20 steps, does not save, prints loss at step 1 and step 20, prints peak VRAM.
Write DeepSpeed config: /home/mohanganesh/ship/configs/ds_config_cpt.json
json{
  "train_batch_size": "auto",
  "train_micro_batch_size_per_gpu": 1,
  "gradient_accumulation_steps": 16,
  "gradient_clipping": 1.0,
  "fp16": {"enabled": true, "auto_cast": false, "loss_scale": 0, "loss_scale_window": 1000, "initial_scale_power": 16, "hysteresis": 2, "min_loss_scale": 1},
  "bf16": {"enabled": false},
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {"device": "cpu", "pin_memory": true},
    "offload_param": {"device": "cpu", "pin_memory": true},
    "overlap_comm": true,
    "contiguous_gradients": true,
    "reduce_bucket_size": 5e7,
    "stage3_prefetch_bucket_size": 5e7,
    "stage3_param_persistence_threshold": 1e5,
    "sub_group_size": 1e8,
    "stage3_max_live_parameters": 1e8,
    "stage3_max_reuse_distance": 1e8,
    "stage3_gather_16bit_weights_on_model_save": true
  },
  "optimizer": {"type": "AdamW", "params": {"lr": "auto", "betas": [0.9, 0.999], "eps": 1e-8, "weight_decay": "auto"}},
  "scheduler": {"type": "WarmupDecayLR", "params": {"warmup_min_lr": 0, "warmup_max_lr": "auto", "warmup_num_steps": "auto", "total_num_steps": "auto"}},
  "steps_per_print": 25,
  "wall_clock_breakdown": false
}
Write launcher: /home/mohanganesh/ship/training/launch_cpt_1.7b.sh
bash#!/bin/bash
export DS_BUILD_OPS=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export TOKENIZERS_PARALLELISM=false

cd /home/mohanganesh/ship

# DRY RUN FIRST
/home/mohanganesh/ship/.venv-train/bin/deepspeed \
  --num_gpus 4 \
  training/run_cpt_1.7b.py \
  --deepspeed configs/ds_config_cpt.json \
  --dry-run \
  2>&1 | tee logs/cpt_1.7b_dryrun.log

echo "=== DRY RUN COMPLETE. CHECK ABOVE FOR ERRORS ==="
echo "=== STARTING FULL TRAINING ==="

nohup /home/mohanganesh/ship/.venv-train/bin/deepspeed \
  --num_gpus 4 \
  training/run_cpt_1.7b.py \
  --deepspeed configs/ds_config_cpt.json \
  2>&1 >> logs/cpt_1.7b_train.log &

echo $! > logs/cpt_1.7b_train.pid
echo "CPT 1.7B training launched. PID=$(cat logs/cpt_1.7b_train.pid)"
echo "Monitor: tail -f logs/cpt_1.7b_train.log"
Execute:

Run the dry run. If it fails, fix it and re-run. Do not start full training until dry run completes 20 steps with valid loss.
After dry run passes, launch full training via bash training/launch_cpt_1.7b.sh
Monitor logs/cpt_1.7b_train.log every 30 minutes. Check that loss is decreasing.

CPT GATE (must pass before Phase 2A):

Maritime perplexity has decreased by at least 15% from the first checkpoint to the final checkpoint
General perplexity has NOT increased by more than 10% (catastrophic forgetting guard)
Check these values from logs/cpt_perplexity_1.7b.jsonl
If general perplexity increased more than 10%, the CPT overfit on maritime data. Report this and wait for instructions.
If both conditions pass, proceed to Phase 2A immediately.


PHASE 1B — CPT FOR STUDENT-4B (parallel with 1.7B if VRAM allows, else after)
While student-1.7b CPT is running, check VRAM usage:

Run nvidia-smi and check how many GB are free across all 4 modules
If all 4 modules are heavily loaded by 1.7B training: wait for 1.7B CPT to finish, then run 4B CPT
If modules 2 and 3 have more than 6 GB free each: start 4B CPT on GPUs 2 and 3 simultaneously

Write script: /home/mohanganesh/ship/training/run_cpt_4b.py
Identical structure to run_cpt_1.7b.py with these differences:

model_name = "/home/mohanganesh/ship/models/student-4b"
save_steps=500
per_device_train_batch_size=1
gradient_accumulation_steps=32 (4B model needs more accumulation for effective batch size)
Checkpoints: /home/mohanganesh/ship/training/checkpoints/cpt-4b/
Perplexity log: /home/mohanganesh/ship/logs/cpt_perplexity_4b.jsonl
Training log: logs/cpt_4b_train.log

Write launcher: /home/mohanganesh/ship/training/launch_cpt_4b.sh
Same as 1.7B launcher. If running in parallel with 1.7B, use --include localhost:2,3 to restrict to GPUs 2 and 3. If running sequentially, use --num_gpus 4.
CPT GATE for 4B: same thresholds as 1.7B.

PHASE 2 — WAIT FOR WAVE 1 DATA (if not already complete)
Before SFT can start, you need the filtered training data. Check:
bashwc -l /home/mohanganesh/ship/ship/maritime_pipeline/data/generation/wave1_modeA_raw.jsonl
wc -l /home/mohanganesh/ship/ship/maritime_pipeline/data/generation/wave1_modeB_raw.jsonl
wc -l /home/mohanganesh/ship/ship/maritime_pipeline/data/generation/wave1_modeC_raw.jsonl
If Mode A has fewer than 50,000 lines: wait. Check every 2 hours. Do not start SFT until Mode A has at least 50,000 lines.
If Mode A has 50,000 or more lines: proceed to SuperFiltering immediately even if generation is still running. You can filter whatever exists so far.
Write script: /home/mohanganesh/ship/scripts/filter_wave1.py
This runs SuperFiltering (IFD) on the raw wave 1 outputs.
Stage 1 — Hard rejection (cheap, run first):

Reject if answer field is null or empty
Reject if answer word count < 10 words
Reject if answer contains any forbidden phrase: "as an AI", "I cannot", "language model", "I don't have access", "I'm unable to"
For regulatory type: reject if answer contains none of: "shall", "must", "require", "prohibit", "regulation", "annex", "convention"
Reject procedural answers with word count < 40 words (procedures need steps)
Keep all INSUFFICIENT_CONTEXT responses (they are valid trap answers)

Stage 2 — IFD scoring using GPT-2:

Load GPT-2 (gpt2, 124M) from HuggingFace
For each sample compute: cond_ppl = perplexity of answer given question, uncond_ppl = perplexity of answer alone
ifd_score = cond_ppl / uncond_ppl
Keep samples where 0.03 ≤ ifd_score ≤ 0.97
Keep up to 500 very-low-IFD samples (simple factual grounding)
Run on CPU (do not use GPU for this)

Stage 3 — Merge all three modes:

Combine filtered Mode A + Mode B + Mode C into sft_curated.jsonl
Output to /home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_curated.jsonl
Print final count per mode and total

Filtering gate: sft_curated.jsonl must have at least 30,000 records to proceed. If fewer, extend the filtering threshold slightly (widen IFD to 0.02–0.98) and refilter.

PHASE 2A — SFT STAGE 1 (REASONING FIRST) FOR STUDENT-1.7B
Only start after: CPT 1.7B gate passed AND sft_curated.jsonl has ≥30,000 records
Write script: /home/mohanganesh/ship/training/run_sft1_1.7b.py
This trains ONLY on /think examples from sft_curated.jsonl. These are the diagnostic and calculation Q/A pairs.
Data: filter sft_curated.jsonl to records where type field is in ["troubleshooting", "calculation"] OR where mode field is "think". These are approximately 20% of total data. If fewer than 3,000 such records exist, use all records with the word "step" in the answer (procedural reasoning as fallback).
Format each record as:
<|im_start|>system
You are a maritime AI assistant. Think carefully before answering.
/think
<|im_end|>
<|im_start|>user
{question}
<|im_end|>
<|im_start|>assistant
<think>
{thinking}
</think>
{answer}<|im_end|>
If a record has no thinking field, use the answer as both thinking and answer (short thinking trace).
Load from the BEST CPT checkpoint (last saved checkpoint in /home/mohanganesh/ship/training/checkpoints/cpt-1.7b/).
LoRA config:

r=32, lora_alpha=32
Same target modules as CPT
lora_dropout=0.05

Hyperparameters:

learning_rate=2e-4
num_train_epochs=2
per_device_train_batch_size=1
gradient_accumulation_steps=8
warmup_ratio=0.03
fp16=True
neftune_noise_alpha=5 (add noise to embeddings during training for better generalization — use TRL's SFTTrainer which supports this natively)
save_steps=200

Use TRL's SFTTrainer for this stage. It handles NEFTune and formatting automatically.
Checkpoints: /home/mohanganesh/ship/training/checkpoints/sft1-1.7b/
Log: logs/sft1_1.7b_train.log
Write launcher: /home/mohanganesh/ship/training/launch_sft1_1.7b.sh
Same structure as CPT launcher. Use --num_gpus 4. Use configs/ds_config_sft.json (if this doesn't exist, create it — same as CPT config but with gradient_accumulation_steps: 8).
SFT Stage 1 gate (must pass before Stage 2):

Run this evaluation after SFT Stage 1:

Take 50 random troubleshooting/diagnostic questions from sft_curated.jsonl
Run them through the model with /think system prompt
Count how many answers contain a reasoning trace (text between <think> and </think> tags with more than 20 words)
PASS condition: ≥70% of answers contain a valid reasoning trace


If FAIL: training may have been too short. Run one more epoch and re-evaluate.


PHASE 2B — SFT STAGE 2 (CONCISE RESPONSES) FOR STUDENT-1.7B
Only start after SFT Stage 1 gate passes
Write script: /home/mohanganesh/ship/training/run_sft2_1.7b.py
This trains on the remaining 80% of sft_curated.jsonl — the factual, regulatory, procedural, and safety Q/A pairs. These are /no_think mode.
Data: filter sft_curated.jsonl to records where type is in ["factual", "regulatory", "safety", "procedural", "trap"] AND mode is "no_think" (or mode field is missing, treating as no_think).
Additionally, append 200 ThinkFollow examples. These are multi-turn conversations where the user first asks a complex question (getting a /think response) and then asks a simple follow-up (getting a /no_think response). Build these synthetically: for each of 200 random procedural chunk records, create a two-turn conversation:

Turn 1: complex question → /think response with reasoning trace
Turn 2: "just give me the key step" → /no_think short answer

Format for /no_think records:
<|im_start|>system
You are a maritime AI assistant. Give direct, actionable answers.
/no_think
<|im_end|>
<|im_start|>user
{question}
<|im_end|>
<|im_start|>assistant
{answer}<|im_end|>
Load from best SFT Stage 1 checkpoint.
Hyperparameters:

learning_rate=1e-4 (lower than Stage 1 — don't destroy the reasoning scaffold)
num_train_epochs=2
per_device_train_batch_size=1
gradient_accumulation_steps=8
neftune_noise_alpha=5
fp16=True
save_steps=200

Checkpoints: /home/mohanganesh/ship/training/checkpoints/sft2-1.7b/
Log: logs/sft2_1.7b_train.log
SFT Stage 2 gate:
Run 25 trap questions from Mode C data through the model with /no_think system prompt. Count how many responses include an explicit statement of uncertainty (contain "I don't have", "insufficient information", "unable to confirm", "cannot determine", "recommend verifying"). PASS condition: ≥60% explicit uncertainty on trap questions. If FAIL: one more epoch.

PHASE 3 — ON-POLICY CORRECTION ROUND FOR STUDENT-1.7B
Only start after SFT Stage 2 gate passes
Write script: /home/mohanganesh/ship/training/run_onpolicy_1.7b.py
This is the most important correction step. The student generates answers to its own training questions, and the teacher judges and corrects. Wrong student answers become ORPO rejected pairs.
Step 3.1 — Student generates answers:

Take 5,000 questions randomly sampled from sft_curated.jsonl
Load the post-SFT-Stage-2 model from best checkpoint
Run each question through the model (batch of 4), max 256 tokens
Save student answers to /home/mohanganesh/ship/ship/maritime_pipeline/data/generation/student_answers_1.7b.jsonl

Step 3.2 — Teacher judges:

For each (question, student_answer) pair, send to the teacher server (port 8000, checking if it is still alive first)
Teacher receives: the original question, the student's answer, and the original gold answer from sft_curated.jsonl
Teacher prompt: "Score the student answer 1-5 (5=correct, complete, safe; 1=wrong, incomplete, dangerous). If the score is 3 or below, provide the correct answer. Output JSON: {score: N, correct_answer: '...' or null}"
Save judge results to /home/mohanganesh/ship/ship/maritime_pipeline/data/generation/teacher_judgments_1.7b.jsonl

Step 3.3 — Build correction pairs:

Pairs where teacher score ≤ 3: create SFT correction record using teacher's correct_answer as the label
Pairs where teacher score is 3 or 4 (close but wrong): create ORPO pair where student_answer is rejected, teacher correct_answer is chosen
Save correction SFT data to data/final/sft_corrections_1.7b.jsonl
Save ORPO pairs to data/final/orpo_pairs_1.7b.jsonl

Step 3.4 — SFT correction round:

Fine-tune the model on sft_corrections_1.7b.jsonl for 1 epoch
learning_rate=5e-5 (very low — targeted correction)
gradient_accumulation_steps=4
No NEFTune for this step
Checkpoint: /home/mohanganesh/ship/training/checkpoints/correction-1.7b/


PHASE 4 — ORPO PREFERENCE POLISH FOR STUDENT-1.7B
Only start after Phase 3 completes and orpo_pairs_1.7b.jsonl exists with ≥500 pairs
Write script: /home/mohanganesh/ship/training/run_orpo_1.7b.py
ORPO combines SFT and preference optimization in a single loss. No reference model needed.
Data: load orpo_pairs_1.7b.jsonl. Each record has prompt, chosen (teacher correct answer), rejected (student wrong answer).
Augment with hard-coded rejection examples for the four rejection categories (R1-R4) if fewer than 1,000 pairs exist. Create synthetic close-but-wrong examples:

R1 Regulatory precision: take regulatory answers and replace "shall" with "should" in rejected version
R2 Missing safety step: take procedural answers and remove the safety check step in rejected version
R3 Unit error: take calculation answers and swap kPa/bar or nm/km in rejected version
R4 Plausible hallucination: take regulatory answers and change annex numbers by 1 in rejected version

Training:

Use TRL's ORPOTrainer
beta=0.1 (the ORPO lambda — do not increase)
learning_rate=8e-6
num_train_epochs=1
per_device_train_batch_size=1
gradient_accumulation_steps=8
fp16=True
disable_dropout=True
Load from correction checkpoint (checkpoints/correction-1.7b/)
Checkpoint: /home/mohanganesh/ship/training/checkpoints/orpo-1.7b/
Log: logs/orpo_1.7b_train.log

ORPO gate:

Run 25 trap questions: ≥80% must trigger explicit uncertainty (up from ≥60% after SFT)
If safety step completeness has regressed by more than 5%: this run overfit. Revert to pre-ORPO checkpoint.
If factual recall has regressed more than 3%: revert and re-run with beta=0.05


PHASE 5 — GGUF QUANTIZATION FOR STUDENT-1.7B
Only start after ORPO gate passes
Write script: /home/mohanganesh/ship/training/quantize_1.7b.sh
Step 5.1 — Merge LoRA into base weights:
pythonfrom peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

base = AutoModelForCausalLM.from_pretrained(
    "/home/mohanganesh/ship/models/student-1.7b",
    torch_dtype=torch.float16,
    device_map="cpu"
)
model = PeftModel.from_pretrained(base, "/home/mohanganesh/ship/training/checkpoints/orpo-1.7b/")
model = model.merge_and_unload()
model.save_pretrained("/home/mohanganesh/ship/training/merged/maritime-1.7b-merged/")
tokenizer = AutoTokenizer.from_pretrained("/home/mohanganesh/ship/models/student-1.7b")
tokenizer.save_pretrained("/home/mohanganesh/ship/training/merged/maritime-1.7b-merged/")
print("Merge complete")
Step 5.2 — Convert to GGUF Q4_K_M:
bash/home/mohanganesh/ship/.venv-train/bin/python \
  /home/mohanganesh/ship/llama.cpp/convert_hf_to_gguf.py \
  /home/mohanganesh/ship/training/merged/maritime-1.7b-merged/ \
  --outtype f16 \
  --outfile /home/mohanganesh/ship/deploy/maritime-1.7b-f16.gguf

/home/mohanganesh/ship/llama.cpp/build/bin/llama-quantize \
  /home/mohanganesh/ship/deploy/maritime-1.7b-f16.gguf \
  /home/mohanganesh/ship/deploy/maritime-1.7b-q4km.gguf \
  Q4_K_M
Step 5.3 — Post-quantization validation:

Start a temporary llama-server on port 9000 pointing to maritime-1.7b-q4km.gguf
Run 20 regulatory questions from sft_curated.jsonl against both the fp16 merged model (via transformers) and the GGUF model (via llama-server)
Compare: if regulatory answer quality drops more than 3% (judge by presence of correct modal verbs "shall/must"), rebuild with Q5_K_M instead
Decision rule: Q4_K_M ships unless regulatory drop > 3%, then Q5_K_M

Step 5.4 — Write TTC routing policy:

Write /home/mohanganesh/ship/deploy/routing_policy.py
Pure rule-based router, no ML
Think triggers: keywords ["diagnose", "troubleshoot", "why is", "calculate", "stability", "what would happen", "root cause", "step by step", "exception to", "notwithstanding"] plus regex \b\d+\s*(bar|kPa|rpm|kW|nm|knots|GRT|DWT)\b
Default: /no_think
Target: triggers /think on approximately 20% of queries


PHASE 1B-5 FOR STUDENT-4B
After student-1.7b pipeline is fully complete AND both GGUF files exist
Repeat ALL phases (1B through 5) for student-4b with these differences:

All model paths: student-4b → cpt-4b, sft1-4b, sft2-4b, correction-4b, orpo-4b
gradient_accumulation_steps=32 for CPT (larger model needs larger effective batch)
All other hyperparameters identical
GGUF output: /home/mohanganesh/ship/deploy/maritime-4b-q4km.gguf
Q4_K_M target size ~2.5 GB


FINAL ACCEPTANCE TEST
Run after both GGUFs exist
Write script: /home/mohanganesh/ship/training/run_final_eval.py
Run 475 total eval questions across both models. Questions sourced from sft_curated.jsonl held-out slice (last 10% of each type, not used in training).
For each model (1.7B GGUF and 4B GGUF), evaluate:
CategoryQuestionsPass threshold 1.7BPass threshold 4BRegulatory compliance100≥82%≥87%Procedural completeness125≥78%≥83%Troubleshooting root cause100≥72%≥78%Safety step completeness75≥88%≥92%Calculation accuracy50≥75%≥82%Trap question refusals25≥80%≥82%
Scoring method: for each answer, use the teacher (port 8000) to judge correctness with a binary score. Teacher prompt: "Does this answer correctly and safely address the maritime question? Answer only YES or NO." Count YES / total per category.
Save full results to /home/mohanganesh/ship/logs/final_eval_results.json.
If any category fails: log the failure category, log 5 example failures, and stop. Do not declare success.
If all categories pass: print "DEPLOYMENT READY" and report final scores.

LOGGING REQUIREMENTS (every phase)
For every phase, append a status line to /home/mohanganesh/ship/logs/pipeline_execution.log in format:
[TIMESTAMP] PHASE_NAME STATUS: PASS/FAIL/RUNNING. Details: ...
This log is the ground truth of what happened.

HARD RULES

Never touch .venv — it is used by Wave 1 generation which must keep running
Never kill any process whose PID is in logs/teacher_pids.txt or logs/wave1_generation.pid
Every training launch is via nohup background job so it survives disconnection
Every gate must be checked before starting the next phase — do not skip gates
If a gate fails, stop and log the failure. Do not proceed.
fp16 everywhere. No bf16. No 4-bit. No Unsloth. No bitsandbytes.
DS_BUILD_OPS=0 always exported before any deepspeed command
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 always exported

START NOW. Begin Phase 1A CPT dry run for student-1.7b. Do not stop until final acceptance test completes or a gate fails.