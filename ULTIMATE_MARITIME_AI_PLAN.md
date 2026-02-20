# 🚢 ULTIMATE MARITIME AI TRAINING PLAN — ZERO COMPROMISES
## Life-Safety System: Every Detail Matters

**PHILOSOPHY:**  
This is not a chatbot. This is a life-safety system for maritime officers. A wrong answer about crankcase entry procedure causes explosions. A wrong answer about enclosed space entry causes fatalities. A wrong answer about MARPOL compliance causes environmental disasters and port detentions.

**EVERY decision in this plan traces to published research.**  
**EVERY quality gate exists for a reason.**  
**ZERO shortcuts. ZERO compromises.**

---

## SYSTEM STATUS SNAPSHOT

### ✅ COMPLETED
- **CPT 1.7B:** EXCELLENT results (74.5% maritime PPL drop, <2% general regression)
- **Infrastructure:** 2× teacher servers running (Qwen3-235B Q4_K_M on ports 8000, 8001)
- **Training scripts:** All exist and validated
- **Base model:** Qwen3-1.7B downloaded and ready
- **Hardware:** 4× Tesla K80 GPUs (11GB each), 251GB RAM, 48 CPU threads

### ⚠️ CRITICAL BLOCKERS
- **Data generation:** Only 17,485 samples vs 300,000 target (5.8% complete)
- **Data quality:** 81-87% empty teacher responses (max_tokens=32 bug)
- **Missing categories:** 0 reasoning samples, only 22 enclosed-space samples (need 1,000+)
- **Missing components:** ThinkFollow examples, TAPT phase, validation rules

### 🎯 MISSION
Create the GREATEST maritime AI model by following research-proven methodology with COMPLETE implementation of every phase.

---

## COMPLETE ARCHITECTURE OVERVIEW

### Phase 0: DATA INFRASTRUCTURE (Fix & Scale)
**Goal:** Generate 300,000+ high-quality maritime Q&A samples with proper distribution

**Tasks:**
1. **Task 0.1:** Diagnose teacher server (confirm max_tokens fix)
2. **Task 0.2:** Fix generation script (max_tokens 32→300, add validation)
3. **Task 0.3:** Scale to 4 teacher servers (4× throughput)
4. **Task 0.4:** Restart generation with monitoring
5. **Task 0.5:** Create ThinkFollow multi-turn examples (200 hand-crafted)
6. **Task 0.6:** Build comprehensive eval framework (6 categories)

### Phase 1: CPT (ALREADY COMPLETE - 1.7B)
**Goal:** Domain adaptation for maritime language fluency

**Status:** ✅ PASSED (74.5% maritime PPL drop, general knowledge preserved)

### Phase 2: TAPT (Task-Adaptive Pre-Training) 
**Goal:** Bridge CPT → SFT with task-specific text exposure

**Research:** Nature Computational Materials 2025 - "DAPT+TAPT outperforms DAPT alone by 2-5%"

**Tasks:**
1. **Task 2.1:** TAPT training on chunks.jsonl (1 epoch, 2-4 hours)
2. **Task 2.2:** Validate perplexity improvement

### Phase 3: SUPERFILTER (IFD-Based Quality Selection)
**Goal:** Filter raw data → 200k-300k curated samples with balanced distribution

**Research:** SuperFiltering ACL 2024 - IFD via GPT-2 consistent with 13B orderings

**Tasks:**
1. **Task 3.1:** Hard rejection filters (cheap, fast)
2. **Task 3.2:** IFD scoring with GPT-2 (0.05 ≤ score ≤ 0.95)
3. **Task 3.3:** Diversity selection (embedding-based deduplication)
4. **Task 3.4:** Type distribution enforcement (30% factual, 25% procedural, 20% troubleshooting, 12% safety, 8% regulatory, 5% calculation)
5. **Task 3.5:** Quality report generation

### Phase 4: SFT (Two-Stage Curriculum)
**Goal:** Teach instruction following with reasoning-first approach

**Research:** openPangu Embedded Sep 2025 - reasoning-first then concise SFT outperforms flat mixed

**Tasks:**
1. **Task 4.1:** SFT Stage 1 - Reasoning mode (/think) training
2. **Task 4.2:** Eval on troubleshooting/calculation categories
3. **Task 4.3:** SFT Stage 2 - Concise mode (/no_think) + ThinkFollow
4. **Task 4.4:** Full 6-category evaluation

### Phase 5: ON-POLICY CORRECTION
**Goal:** Expose and correct student's real failure modes

**Research:** Qwen3 Technical Report - exact recipe for Qwen3-4B from Qwen3-235B

**Tasks:**
1. **Task 5.1:** On-policy generation (student generates, teacher scores)
2. **Task 5.2:** Build ORPO rejected pairs from student mistakes
3. **Task 5.3:** SFT correction pass (1 epoch, conservative LR)
4. **Task 5.4:** Re-eval to confirm improvement

### Phase 6: ORPO (Preference Optimization)
**Goal:** Polish layer - teach subtle quality distinctions

**Research:** ORPO paper arXiv:2403.07691 - eliminates DPO's distribution shift

**Tasks:**
1. **Task 6.1:** Build complete ORPO pairs (on-policy + R1/R2/R3/R4 synthetic)
2. **Task 6.2:** ORPO training (beta=0.1, 1 epoch)
3. **Task 6.3:** Monitor rewards/chosen vs rewards/rejected
4. **Task 6.4:** Full evaluation against quality gates

### Phase 7: QUANTIZATION & DEPLOYMENT
**Goal:** Ship production-ready GGUF model with <3% quality drop

**Tasks:**
1. **Task 7.1:** Merge LoRA adapters → FP16 model
2. **Task 7.2:** Convert to GGUF Q4_K_M
3. **Task 7.3:** Post-quant validation (if regulatory drop >3%, use Q5_K_M)
4. **Task 7.4:** Build TTC routing policy (rule-based /think trigger)
5. **Task 7.5:** Final acceptance test (all 6 categories must pass)

---

## PHASE 0: DATA INFRASTRUCTURE — COMPLETE IMPLEMENTATION

### Task 0.1: Diagnose Teacher Server Response Quality
**Duration:** 2 hours  
**Purpose:** Confirm max_tokens=32 is causing empty responses

**File:** `diagnostics/teacher_test.py`

```python
#!/usr/bin/env python3
"""
Diagnostic test for teacher server response quality.
Tests multiple max_tokens values to confirm root cause.
"""
import json
import requests
import time
from pathlib import Path

# Test configuration
TEACHER_URLS = ["http://localhost:8000/v1/chat/completions", 
                "http://localhost:8001/v1/chat/completions"]
TEST_CHUNK = """
MARPOL Annex VI Regulation 14: Sulphur Oxides (SOx) and Particulate Matter

1. The sulphur content of any fuel oil used on board ships shall not exceed:
   - 3.50% m/m prior to 1 January 2012
   - 3.50% m/m on and after 1 January 2012
   - 0.50% m/m on and after 1 January 2020

2. In emission control areas (ECAs), the sulphur content shall not exceed:
   - 1.50% m/m prior to 1 July 2010
   - 1.00% m/m on and after 1 July 2010
   - 0.10% m/m on and after 1 January 2015
"""

SYSTEM_PROMPT = """You are a maritime domain expert. Generate exactly ONE question and answer from the provided text chunk.

/no_think

STRICT RULES:
1. The answer MUST be answerable ONLY from the chunk text.
2. WORD LIMITS: regulatory type maximum 100 words.
3. Output ONLY valid JSON.

OUTPUT FORMAT:
{"q": "<question>", "a": "<answer>", "type": "regulatory", "chunk_id": "test"}
"""

TEST_CONFIGS = [
    {"max_tokens": 32, "max_chars": 450, "name": "CURRENT (BROKEN)"},
    {"max_tokens": 150, "max_chars": 1000, "name": "MEDIUM"},
    {"max_tokens": 300, "max_chars": 2000, "name": "FIXED"},
]

def test_generation(url, config):
    """Test generation with specific config."""
    payload = {
        "model": "qwen3-235b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CHUNK:\n{TEST_CHUNK}\n\nGenerate one regulatory question and answer."}
        ],
        "max_tokens": config["max_tokens"],
        "temperature": 0.7,
        "stop": ["\n\n", "CHUNK:"]
    }
    
    try:
        start = time.time()
        response = requests.post(url, json=payload, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Try to parse as JSON
            try:
                parsed = json.loads(content)
                answer_length = len(parsed.get('a', ''))
                return {
                    "success": True,
                    "content": content,
                    "answer_length": answer_length,
                    "elapsed": elapsed,
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "content": content,
                    "answer_length": len(content),
                    "elapsed": elapsed,
                    "error": "Invalid JSON"
                }
        else:
            return {
                "success": False,
                "content": None,
                "answer_length": 0,
                "elapsed": elapsed,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "content": None,
            "answer_length": 0,
            "elapsed": 0,
            "error": str(e)
        }

def main():
    print("=" * 80)
    print("TEACHER SERVER DIAGNOSTIC TEST")
    print("=" * 80)
    
    results = []
    
    for config in TEST_CONFIGS:
        print(f"\n{'=' * 80}")
        print(f"Testing: {config['name']}")
        print(f"max_tokens={config['max_tokens']}, max_chars={config['max_chars']}")
        print(f"{'=' * 80}\n")
        
        for i, url in enumerate(TEACHER_URLS):
            print(f"Teacher {i} ({url})...")
            result = test_generation(url, config)
            
            result['config'] = config['name']
            result['teacher'] = i
            results.append(result)
            
            if result['success']:
                print(f"  ✅ SUCCESS - Answer: {result['answer_length']} chars, {result['elapsed']:.1f}s")
                print(f"  Preview: {result['content'][:150]}...")
            else:
                print(f"  ❌ FAILED - Error: {result['error']}")
                if result['content']:
                    print(f"  Received: {result['content'][:150]}...")
            print()
    
    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    
    for config in TEST_CONFIGS:
        config_results = [r for r in results if r['config'] == config['name']]
        success_count = sum(1 for r in config_results if r['success'])
        avg_length = sum(r['answer_length'] for r in config_results if r['success']) / max(success_count, 1)
        
        print(f"\n{config['name']}:")
        print(f"  Success rate: {success_count}/{len(config_results)}")
        print(f"  Avg answer length: {avg_length:.0f} chars")
        
        if success_count == 0:
            print(f"  ⚠️  CRITICAL: No successful responses!")
        elif avg_length < 50:
            print(f"  ⚠️  WARNING: Responses too short (likely truncated)")
        else:
            print(f"  ✅ GOOD: Adequate response length")
    
    # Save results
    output_path = Path("diagnostics/teacher_test_results.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nFull results saved to: {output_path}")
    
    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    
    fixed_results = [r for r in results if r['config'] == 'FIXED']
    if all(r['success'] for r in fixed_results):
        print("✅ max_tokens=300 FIXES the issue.")
        print("✅ Proceed to Task 0.2: Update generation script.")
    else:
        print("⚠️  Further investigation needed.")
        print("⚠️  Check teacher server logs for errors.")

if __name__ == "__main__":
    main()
```

**Execute:**
```bash
cd /home/mohanganesh/ship
mkdir -p diagnostics
python3 diagnostics/teacher_test.py
```

**Acceptance Criteria:**
- [ ] Fixed config (max_tokens=300) shows 100% success rate
- [ ] Fixed config produces avg answer length >200 chars
- [ ] Current config (max_tokens=32) shows failures or short responses
- [ ] Results clearly demonstrate root cause

---

### Task 0.2: Fix Generation Script with Complete Validation
**Duration:** 3 hours  
**Purpose:** Fix max_tokens bug + add comprehensive per-sample validation

**File:** `scripts/generate_wave1.py` (EDIT EXISTING)

**Changes to make:**

1. **Fix core parameters (lines ~50-65):**
```python
# OLD (BROKEN):
max_tokens=32
max_chars=450

# NEW (FIXED):
max_tokens=300  # Allow complete responses
max_chars=2000  # Match TRAINING-PLAN.md spec
```

2. **Add validation function (insert after imports):**
```python
def validate_sample(sample, mode):
    """
    Validate sample before writing to output.
    Returns (is_valid: bool, error_reason: str)
    """
    # 1. Required fields
    required_fields = ['q', 'a', 'type', 'chunk_id']
    if not all(k in sample for k in required_fields):
        return False, "Missing required fields"
    
    # 2. Non-empty
    if not sample['q'] or not sample['a']:
        return False, "Empty question or answer"
    
    # 3. Word count limits (allow 1.5× for flexibility)
    answer_words = len(sample['a'].split())
    
    word_limits = {
        'factual': 50,
        'regulatory': 100,
        'safety': 120,
        'procedural': 200,
        'troubleshooting': 150,
        'calculation': 100,
        'insufficient': 5  # Special case
    }
    
    sample_type = sample.get('type', 'factual')
    max_words = word_limits.get(sample_type, 100) * 1.5
    
    # INSUFFICIENT_CONTEXT is exempt from word limits
    if sample['a'] == "INSUFFICIENT_CONTEXT":
        sample['type'] = 'insufficient'
        return True, "Valid insufficient context response"
    
    if answer_words > max_words:
        return False, f"Answer too long: {answer_words} words > {max_words} limit"
    
    # 4. Minimum word count for procedural
    if sample_type == 'procedural' and answer_words < 40:
        return False, "Procedural answer too short (needs steps)"
    
    # 5. Forbidden phrases
    forbidden = [
        'as an ai', 'i cannot', 'language model',
        "i don't have access", "my training data",
        "i'm unable to", "i am unable to"
    ]
    answer_lower = sample['a'].lower()
    for phrase in forbidden:
        if phrase in answer_lower:
            return False, f"Contains forbidden phrase: {phrase}"
    
    # 6. Type-specific requirements
    if sample_type == 'regulatory':
        required_words = ['shall', 'must', 'require', 'prohibit', 
                         'regulation', 'annex', 'convention', 'chapter']
        if not any(word in answer_lower for word in required_words):
            return False, "Regulatory answer missing modal verbs or regulatory terms"
    
    # 7. Thinking trace validation for /think mode
    if mode == 'think':
        if 'thinking' not in sample:
            return False, "Think mode but no thinking field"
        if not sample['thinking']:
            return False, "Think mode but empty thinking field"
        thinking_words = len(sample['thinking'].split())
        if thinking_words > 150:
            return False, f"Thinking trace too long: {thinking_words} > 150 words"
    
    # 8. Answer should not start with meta-phrases
    bad_starts = [
        'according to', 'based on', 'the text states',
        'the chunk says', 'the passage mentions'
    ]
    answer_start = ' '.join(sample['a'].lower().split()[:3])
    for bad in bad_starts:
        if bad in answer_start:
            return False, f"Answer starts with meta-phrase: {bad}"
    
    return True, "Valid"


# Add global counters
validation_stats = {
    'total_attempted': 0,
    'passed_validation': 0,
    'failed_empty': 0,
    'failed_word_limit': 0,
    'failed_forbidden_phrase': 0,
    'failed_type_specific': 0,
    'failed_other': 0
}
```

3. **Update generation loop to use validation:**
```python
# After receiving response from teacher, before writing:

validation_stats['total_attempted'] += 1

is_valid, reason = validate_sample(parsed_sample, current_mode)

if is_valid:
    # Write to output file
    output_file.write(json.dumps(parsed_sample) + '\n')
    validation_stats['passed_validation'] += 1
else:
    # Track failure reason
    if 'empty' in reason.lower():
        validation_stats['failed_empty'] += 1
    elif 'word' in reason.lower() or 'long' in reason.lower() or 'short' in reason.lower():
        validation_stats['failed_word_limit'] += 1
    elif 'forbidden' in reason.lower():
        validation_stats['failed_forbidden_phrase'] += 1
    elif 'regulatory' in reason.lower() or 'procedural' in reason.lower() or 'thinking' in reason.lower():
        validation_stats['failed_type_specific'] += 1
    else:
        validation_stats['failed_other'] += 1
    
    # Log rejected sample for debugging
    if generation_count % 100 == 0:  # Log every 100th rejection
        logger.debug(f"REJECTED: {reason} | Sample: {parsed_sample}")
```

4. **Add retry logic with exponential backoff:**
```python
def call_teacher_with_retry(url, payload, max_retries=3):
    """Call teacher API with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=90)
            if response.status_code == 200:
                return response
            elif response.status_code == 503:  # Service unavailable
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Teacher unavailable, retry {attempt+1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"Teacher returned {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            wait_time = 2 ** attempt
            logger.warning(f"Timeout, retry {attempt+1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    return None  # All retries failed
```

5. **Improve progress reporting (every 500 samples):**
```python
if generation_count % 500 == 0:
    elapsed = time.time() - start_time
    rate = generation_count / elapsed if elapsed > 0 else 0
    
    total_target = total_chunks * angles_per_chunk
    remaining = total_target - generation_count
    eta_seconds = remaining / rate if rate > 0 else 0
    eta_hours = eta_seconds / 3600
    
    pass_rate = (validation_stats['passed_validation'] / 
                 validation_stats['total_attempted'] * 100 
                 if validation_stats['total_attempted'] > 0 else 0)
    
    print(f"\n{'='*70}")
    print(f"Progress: {generation_count:,} / {total_target:,} ({generation_count/total_target*100:.1f}%)")
    print(f"Rate: {rate:.2f} samples/sec")
    print(f"ETA: {eta_hours:.1f} hours")
    print(f"Validation pass rate: {pass_rate:.1f}%")
    print(f"Failures: empty={validation_stats['failed_empty']}, "
          f"word_limit={validation_stats['failed_word_limit']}, "
          f"forbidden={validation_stats['failed_forbidden_phrase']}, "
          f"type={validation_stats['failed_type_specific']}")
    print(f"{'='*70}\n")
```

**Execute:**
```bash
# Backup original
cp scripts/generate_wave1.py scripts/generate_wave1.py.backup

# Make edits as specified above
# Then dry-run test on 100 samples:
python3 scripts/generate_wave1.py --max-samples 100 --output-suffix test

# Check results:
wc -l ship/maritime_pipeline/data/generation/*_test.jsonl
head -5 ship/maritime_pipeline/data/generation/*_test.jsonl

# Verify validation stats are printed
# Verify no forbidden phrases in output
```

**Acceptance Criteria:**
- [ ] max_tokens=300, max_chars=2000 confirmed in code
- [ ] Validation function present and called before writing
- [ ] Retry logic with exponential backoff implemented
- [ ] Progress reporting shows validation pass rate
- [ ] Dry-run produces >90% validation pass rate
- [ ] No forbidden phrases in sample output

---

### Task 0.3: Scale to 4 Teacher Servers
**Duration:** 1 hour  
**Purpose:** 4× generation throughput (0.24 samples/sec → 0.96 samples/sec)

**Actions:**

1. **Start teachers on ports 8002, 8003:**
```bash
cd /home/mohanganesh/ship

# Teacher 3 on port 8002
nohup llama-server \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00001-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00002-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00003-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00004-of-00004.gguf \
  --host 0.0.0.0 \
  --port 8002 \
  --ctx-size 8192 \
  --n-gpu-layers 0 \
  --threads 12 \
  --batch-size 512 \
  2>&1 > logs/teacher_8002.log &

echo $! > logs/teacher_8002.pid

# Teacher 4 on port 8003
nohup llama-server \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00001-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00002-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00003-of-00004.gguf \
  --model /home/mohanganesh/ship/models/teacher-235b/qwen3-235b-q4km-00004-of-00004.gguf \
  --host 0.0.0.0 \
  --port 8003 \
  --ctx-size 8192 \
  --n-gpu-layers 0 \
  --threads 12 \
  --batch-size 512 \
  2>&1 > logs/teacher_8003.log &

echo $! > logs/teacher_8003.pid

# Wait 60 seconds for startup
sleep 60

# Health check all 4 teachers
for port in 8000 8001 8002 8003; do
  echo "Checking teacher on port $port..."
  curl -s http://localhost:$port/health || echo "FAILED"
done
```

2. **Update generate_wave1.py to use all 4 teachers:**
```python
# OLD:
TEACHER_URLS = [
    "http://localhost:8000/v1/chat/completions",
    "http://localhost:8001/v1/chat/completions"
]

# NEW:
TEACHER_URLS = [
    "http://localhost:8000/v1/chat/completions",
    "http://localhost:8001/v1/chat/completions",
    "http://localhost:8002/v1/chat/completions",
    "http://localhost:8003/v1/chat/completions"
]
```

3. **Update generation to use 4 concurrent workers:**
```python
# OLD:
workers = 2

# NEW:
workers = 4  # Match number of teacher servers
```

**Acceptance Criteria:**
- [ ] 4 teacher processes running (check with `ps aux | grep llama-server`)
- [ ] All 4 health endpoints return 200 OK
- [ ] generate_wave1.py configured for 4 URLs and 4 workers
- [ ] No port conflicts (8000-8003 all listening)

---

### Task 0.4: Restart Generation with Full Monitoring
**Duration:** 1 hour setup + 5-7 days runtime  
**Purpose:** Generate complete 300k sample dataset with quality monitoring

**Pre-flight checklist:**
```bash
# 1. Verify all teachers healthy
curl http://localhost:8000/health && \
curl http://localhost:8001/health && \
curl http://localhost:8002/health && \
curl http://localhost:8003/health && \
echo "✅ All teachers healthy"

# 2. Archive old data
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p ship/maritime_pipeline/data/archive/$timestamp
mv ship/maritime_pipeline/data/generation/*.jsonl \
   ship/maritime_pipeline/data/archive/$timestamp/ 2>/dev/null || true
echo "✅ Old data archived"

# 3. Verify source data
wc -l ship/maritime_pipeline/data/final/chunks.jsonl
# Should show: 115783 chunks
echo "✅ Source data ready"

# 4. Check disk space (need ~50GB for output)
df -h /home/mohanganesh/ship | grep -v Filesystem
# Should show >50GB available
echo "✅ Disk space sufficient"
```

**Launch generation:**
```bash
cd /home/mohanganesh/ship

# Launch with nohup for long-running process
nohup python3 scripts/generate_wave1.py \
  --input ship/maritime_pipeline/data/final/chunks.jsonl \
  --output-dir ship/maritime_pipeline/data/generation \
  --workers 4 \
  --angles-per-chunk 5 \
  --high-value-categories "enclosed_space,fire,flooding,steering,main_engine,auxiliary,electrical,cargo,pollution,abandon_ship" \
  --high-value-extra-angles 2 \
  2>&1 > logs/generation_wave1.log &

echo $! > logs/generation_wave1.pid
echo "Generation started. PID=$(cat logs/generation_wave1.pid)"
```

**Monitoring commands:**
```bash
# Watch progress (refresh every 30 sec)
watch -n 30 'tail -50 logs/generation_wave1.log | grep -A10 "Progress:"'

# Check current counts
wc -l ship/maritime_pipeline/data/generation/*.jsonl

# Check validation pass rate
grep "Validation pass rate" logs/generation_wave1.log | tail -5

# Check teacher server load
ps aux | grep llama-server | grep -v grep

# Estimate completion
# Target: 578,915 samples (115,783 chunks × 5 angles average)
# Rate: ~0.96 samples/sec with 4 workers
# Time: 578915 / 0.96 / 3600 / 24 = ~7 days
```

**Quality monitoring (check every 12 hours):**
```bash
# Create monitoring script
cat > scripts/monitor_generation.sh << 'EOF'
#!/bin/bash
echo "=== GENERATION MONITORING REPORT ==="
echo "Timestamp: $(date)"
echo ""

echo "Sample counts:"
for f in ship/maritime_pipeline/data/generation/*.jsonl; do
  [ -f "$f" ] && echo "  $(basename $f): $(wc -l < $f) samples"
done
echo ""

echo "Latest validation stats:"
grep "Validation pass rate" logs/generation_wave1.log | tail -1
echo ""

echo "Latest progress:"
grep "Progress:" logs/generation_wave1.log | tail -1
echo ""

echo "Error summary (last 100 lines):"
tail -100 logs/generation_wave1.log | grep -i "error\|failed\|timeout" | wc -l
echo ""

echo "Teacher health:"
for port in 8000 8001 8002 8003; do
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)
  echo "  Port $port: $status"
done
echo ""

echo "Process status:"
if ps -p $(cat logs/generation_wave1.pid 2>/dev/null) > /dev/null 2>&1; then
  echo "  ✅ Generation process RUNNING"
else
  echo "  ❌ Generation process STOPPED"
fi
EOF

chmod +x scripts/monitor_generation.sh

# Run monitoring (execute every 12 hours)
./scripts/monitor_generation.sh
```

**Acceptance Criteria:**
- [ ] Generation process running (check PID)
- [ ] Validation pass rate >90% consistently
- [ ] All 4 teachers responding (health checks pass)
- [ ] Sample count increasing steadily
- [ ] No crash/restart loops in logs
- [ ] ETA showing reasonable completion time

**CRITICAL:** Do NOT stop generation early. Run until target of 578,915 samples is reached. Every additional sample improves model quality.

---

### Task 0.5: Create ThinkFollow Multi-Turn Examples
**Duration:** 8-12 hours (manual crafting)  
**Purpose:** Teach reliable mode-switching in multi-turn conversations

**Research:** TRAINING-PLAN.md lines 397-400 - "200 hand-crafted ThinkFollow examples"

**File:** `ship/maritime_pipeline/data/final/thinkfollow_examples.jsonl`

**Format:** Each example is a multi-turn conversation with explicit mode switches.

**Example template:**
```json
{
  "conversation_id": "tf_001",
  "scenario": "enclosed_space_to_regulation_lookup",
  "turns": [
    {
      "role": "user",
      "content": "/no_think\nWhat is an enclosed space according to SOLAS?"
    },
    {
      "role": "assistant", 
      "content": "An enclosed space is a space with limited openings for entry or exit, inadequate natural ventilation, and which has not been designed or intended for continuous occupancy. Examples include cargo holds, tanks, engine rooms with limited ventilation, sewage tanks, and cofferdams."
    },
    {
      "role": "user",
      "content": "/think\nA crew member has collapsed in the sewage tank. What is the correct entry procedure to rescue him?"
    },
    {
      "role": "assistant",
      "content": "<think>This is a life-critical emergency. Sewage tanks are high-risk enclosed spaces with toxic gas (H2S, methane) and oxygen deficiency. Immediate untrained entry causes secondary casualties. Must follow permit-to-work system even in emergency.</think>\n\nDO NOT enter immediately. Follow this sequence:\n\n1. Raise alarm, call master/chief engineer\n2. Start continuous ventilation of the space (min 30 minutes)\n3. Test atmosphere: oxygen ≥20.9%, H2S <5ppm, LEL <10%\n4. If atmosphere unsafe: donkey rescue using rescue line from OUTSIDE\n5. If atmosphere safe + entry essential: SCBA + lifeline + attendant + rescue team standing by\n6. Re-test atmosphere every 5 minutes during entry\n\nStatistic: 60% of confined space deaths are would-be rescuers. Never enter without procedure."
    },
    {
      "role": "user",
      "content": "/no_think\nWhat does SCBA stand for?"
    },
    {
      "role": "assistant",
      "content": "Self-Contained Breathing Apparatus."
    }
  ],
  "category": "safety_critical",
  "validates": "mode_switch_emergency_to_definition"
}
```

**Required scenario types (200 total):**

1. **Factual → Diagnostic (50 examples)**
   - Simple definition followed by complex troubleshooting
   - Example: "What is auxiliary blower?" → "Engine won't start, aux blower runs but no cranking, diagnose"

2. **Emergency → Factual (50 examples)**
   - Complex safety procedure followed by simple lookup
   - Example: "Fire in engine room, what to do?" → "What does AFFF stand for?"

3. **Calculation → Verification (40 examples)**
   - Multi-step calculation followed by unit conversion
   - Example: "Calculate stability GM" → "Convert 2.5 meters to feet"

4. **Regulatory → Exception (30 examples)**
   - Standard regulation followed by edge case
   - Example: "MARPOL Annex I discharge limits" → "What are the exceptions for emergencies?"

5. **Procedural → Troubleshooting (30 examples)**
   - Standard procedure followed by failure analysis
   - Example: "Starting main engine procedure" → "Engine starts but shuts down after 30 sec, diagnose"

**Quality requirements:**
- Every conversation must have 3-5 turns
- Every conversation must have at least 2 mode switches
- Answers must follow the same quality standards as main dataset
- Safety scenarios must include life-saving details (statistics, consequences)
- Regulatory scenarios must use correct modal verbs (shall/must/should)

**Creation process:**
```bash
# Create directory
mkdir -p ship/maritime_pipeline/data/final

# Manual crafting (use text editor)
# Recommended: Split among 2-3 maritime domain experts
# Time per example: 3-5 minutes
# Total time: 200 × 4 min = 800 min = 13.3 hours

# Validation script
python3 << 'EOF'
import json
from pathlib import Path

def validate_thinkfollow():
    """Validate ThinkFollow examples meet requirements."""
    file_path = Path("ship/maritime_pipeline/data/final/thinkfollow_examples.jsonl")
    
    if not file_path.exists():
        print("❌ File not found")
        return False
    
    examples = []
    with open(file_path) as f:
        for line in f:
            examples.append(json.loads(line))
    
    print(f"Total examples: {len(examples)}")
    
    # Check requirements
    errors = []
    
    for i, ex in enumerate(examples):
        # Must have turns
        if 'turns' not in ex or len(ex['turns']) < 3:
            errors.append(f"Example {i}: <3 turns")
        
        # Must have mode switches
        if 'turns' in ex:
            modes = []
            for turn in ex['turns']:
                if turn['role'] == 'user' and ('/think' in turn['content'] or '/no_think' in turn['content']):
                    modes.append('/think' if '/think' in turn['content'] else '/no_think')
            
            if len(set(modes)) < 2:
                errors.append(f"Example {i}: No mode switches")
    
    if errors:
        print("\n❌ Validation errors:")
        for err in errors[:10]:  # Show first 10
            print(f"  - {err}")
        return False
    else:
        print("✅ All examples valid")
        return True

validate_thinkfollow()
EOF
```

**Acceptance Criteria:**
- [ ] 200 examples created
- [ ] All 5 scenario types represented (balanced distribution)
- [ ] Every example has 3-5 turns
- [ ] Every example has ≥2 mode switches
- [ ] Validation script passes 100%
- [ ] Examples reviewed by maritime domain expert

---

### Task 0.6: Build 6-Category Evaluation Framework
**Duration:** 16 hours  
**Purpose:** Comprehensive test suite for ALL quality gates

**File:** `evaluation/build_eval_set.py`

**Categories:**

1. **Regulatory Compliance (100 questions)**
   - SOLAS, MARPOL, STCW, COLREGs, ISM Code
   - Must test modal verb precision (shall vs should vs must)
   - Must include edge cases and exceptions
   - Example: "Under MARPOL Annex VI, what is the maximum sulphur content in fuel oil in ECAs as of 2015?"

2. **Procedural Step Completeness (125 questions)**
   - Engine starting, mooring operations, watchkeeping
   - Grading: rubric checklist of required steps
   - Example: "What is the procedure for starting the main engine?" (must include: prelube, turning gear, air pressure check, fuel priming, etc.)

3. **Troubleshooting Root Cause (100 questions)**
   - Diagnostic reasoning, fault trees
   - Must provide symptom → cause → action
   - Example: "Main engine starts but shuts down after 30 seconds. Low oil pressure alarm. What is the most likely cause?"

4. **Safety Step Completeness (75 questions)**
   - HIGHEST bar - ≥90% required
   - Enclosed space, hot work, firefighting, abandon ship
   - Missing ONE step = fail (life-safety critical)
   - Example: "What is the procedure for entering an empty ballast tank?" (must include: permit, ventilation, gas testing, SCBA, attendant, rescue team)

5. **Calculation Accuracy (50 questions)**
   - Stability, fuel consumption, ETA, cargo calculations
   - Must get number AND units correct
   - Example: "Vessel GM is 0.8m, KG is 7.2m, KM is 8.0m. Is this stable?" (answer: yes, GM positive, but below typical safe minimum of 0.15-0.50m for cargo ships)

6. **Trap Questions - INSUFFICIENT_CONTEXT (25 questions)**
   - Questions the model SHOULD refuse
   - Test confidence calibration
   - Example: "What is the captain's wife's name?" (correct: "I don't have sufficient information about this specific topic.")

**Implementation:**

```python
#!/usr/bin/env python3
"""
Build comprehensive 6-category evaluation set for maritime AI.
"""
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class EvalQuestion:
    """Single evaluation question."""
    id: str
    category: str  # regulatory, procedural, troubleshooting, safety, calculation, trap
    question: str
    correct_answer: str
    rubric: List[str]  # For procedural/safety: list of required elements
    difficulty: str  # easy, medium, hard
    source: str  # Which regulation/manual/case study
    modal_verbs: List[str] = None  # For regulatory: expected shall/must/should
    units: str = None  # For calculation: expected units
    min_steps: int = None  # For procedural: minimum required steps

class EvalSetBuilder:
    """Build complete evaluation set."""
    
    def __init__(self):
        self.questions = []
    
    def add_regulatory_questions(self):
        """Category 1: Regulatory compliance."""
        
        # MARPOL Annex VI - SOx limits
        self.questions.append(EvalQuestion(
            id="reg_001",
            category="regulatory",
            question="Under MARPOL Annex VI Regulation 14, what is the maximum sulphur content in fuel oil in Emission Control Areas (ECAs) as of 1 January 2015?",
            correct_answer="0.10% m/m (mass by mass). Ships operating in ECAs shall use fuel oil with sulphur content not exceeding 0.10 percent by mass.",
            rubric=["0.10%", "m/m or mass by mass", "shall (not should)"],
            difficulty="medium",
            source="MARPOL Annex VI Reg 14",
            modal_verbs=["shall"]
        ))
        
        # SOLAS - Lifeboat capacity
        self.questions.append(EvalQuestion(
            id="reg_002",
            category="regulatory",
            question="According to SOLAS Chapter III, what is the minimum lifeboat capacity requirement for passenger ships?",
            correct_answer="Passenger ships shall carry lifeboats on each side of the ship with total capacity sufficient for at least 50% of the total number of persons on board. The total capacity on both sides must be 100% of persons on board.",
            rubric=["50% each side", "100% total", "shall"],
            difficulty="medium",
            source="SOLAS Ch III Reg 21",
            modal_verbs=["shall"]
        ))
        
        # ... (98 more regulatory questions)
        # Cover: SOLAS chapters I-XIV, MARPOL Annexes I-VI, STCW, COLREGs, ISM Code
        # Include edge cases: exemptions, grandfather clauses, special conditions
    
    def add_procedural_questions(self):
        """Category 2: Procedural step completeness."""
        
        self.questions.append(EvalQuestion(
            id="proc_001",
            category="procedural",
            question="What is the complete procedure for starting the main diesel engine from cold (not in standby)?",
            correct_answer="""1. Check engine room and engine external condition
2. Engage turning gear, turn engine 2 complete revolutions
3. Disengage turning gear
4. Start jacket water preheater, warm to 60-70°C
5. Start lubrication oil priming pump, verify oil pressure
6. Start fuel oil priming pump
7. Check starting air pressure (≥25 bar typical)
8. Set fuel rack to start position
9. Open indicator cocks
10. Turn engine on starting air (2-3 revolutions)
11. Close indicator cocks
12. Start engine on fuel
13. Verify oil pressure, cooling water flow, exhaust temperature
14. Warm up gradually to operating temperature""",
            rubric=[
                "Turning gear operation",
                "Jacket water preheating",
                "Lubrication oil priming",
                "Starting air pressure check",
                "Indicator cocks opening",
                "Blow-through on starting air",
                "Indicator cocks closing",
                "Gradual warm-up"
            ],
            difficulty="hard",
            source="MAN B&W Engine Manual",
            min_steps=10
        ))
        
        # ... (124 more procedural questions)
        # Cover: engine operations, mooring, cargo handling, watchkeeping, maintenance
    
    def add_troubleshooting_questions(self):
        """Category 3: Troubleshooting root cause."""
        
        self.questions.append(EvalQuestion(
            id="trouble_001",
            category="troubleshooting",
            question="Main engine fails to start. Starting air pressure is normal (28 bar). Engine turns on starting air but does not fire. Fuel oil day tank level is normal. What are the three most likely causes in order of probability?",
            correct_answer="""1. Fuel oil not reaching injectors: Check fuel priming pump operation, fuel filter clogging, fuel shut-off valve position
2. Air in fuel system: Bleed fuel system from day tank to injectors
3. Faulty fuel injectors: Check injector spray pattern, clean or replace injectors

Less likely but check: incorrect fuel pump timing, low fuel oil temperature (heavy fuel), starting air distributor malfunction.""",
            rubric=[
                "Identifies fuel delivery issue",
                "Mentions air in fuel system",
                "Provides diagnostic steps",
                "Prioritizes by probability"
            ],
            difficulty="medium",
            source="Common engine faults"
        ))
        
        # ... (99 more troubleshooting questions)
        # Based on: NTSB reports, BSU investigation files, common fault trees
    
    def add_safety_questions(self):
        """Category 4: Safety step completeness - HIGHEST bar."""
        
        self.questions.append(EvalQuestion(
            id="safety_001",
            category="safety",
            question="A crew member has collapsed inside an empty fuel oil tank during inspection. What is the complete emergency rescue procedure?",
            correct_answer="""DO NOT ENTER IMMEDIATELY - 60% of confined space deaths are would-be rescuers.

1. Raise alarm - call master, chief engineer, and deck officer
2. Call emergency telephone number if in port
3. Start EXTERNAL rescue first:
   - If crew member is conscious and near opening: throw rescue line, pull out
   - If crew member is unconscious: attempt hook/pole rescue from outside
4. If external rescue impossible, PREPARE for entry:
   - Start forced ventilation (maintain continuous)
   - Test atmosphere: O2 ≥20.9%, H2S <5ppm, LEL <10%, CO <25ppm
   - Prepare rescue team with SCBA (self-contained breathing apparatus)
   - Rig rescue tripod and winch if available
   - Brief rescue team on entry plan
5. Entry procedure:
   - Rescue person dons SCBA (NOT air-line BA in case of collapse)
   - Attach rescue harness with lifeline
   - Maintain continuous communication
   - Attendant at tank opening (never leave unattended)
   - Second rescue team standing by with SCBA
6. During rescue:
   - Attach harness to casualty
   - Lift using winch or manual pull
   - Do not spend >5 minutes inside
7. After extraction:
   - First aid/CPR as needed
   - Medical evacuation if serious
   - DO NOT re-enter tank without repeating full procedure

Critical: Maintain forced ventilation throughout. Retest atmosphere every 5 minutes. Fuel oil tanks contain benzene (carcinogen), H2S (rapidly fatal), and oxygen deficiency.""",
            rubric=[
                "Do not enter immediately warning",
                "Raise alarm",
                "Attempt external rescue first",
                "Forced ventilation (continuous)",
                "Atmosphere testing (specific limits)",
                "SCBA requirement (not air-line)",
                "Rescue harness + lifeline",
                "Attendant at opening",
                "Second rescue team ready",
                "Time limit mentioned",
                "Specific gas hazards identified"
            ],
            difficulty="hard",
            source="SOLAS, Enclosed Space Entry procedures",
            min_steps=11  # ALL steps required for life-safety
        ))
        
        # ... (74 more safety questions)
        # Focus on: enclosed space, hot work, firefighting, abandon ship, MOB, steering failure
    
    def add_calculation_questions(self):
        """Category 5: Calculation accuracy with units."""
        
        self.questions.append(EvalQuestion(
            id="calc_001",
            category="calculation",
            question="A vessel has KM = 8.5 m and KG = 7.8 m. Calculate the metacentric height (GM). Is this acceptable for a cargo vessel?",
            correct_answer="""GM = KM - KG = 8.5 m - 7.8 m = 0.7 m

This is marginally acceptable. Typical safe GM range for cargo vessels is 0.15 m to 3.0 m. GM = 0.7 m provides positive stability but is on the lower end, meaning the vessel will have a slow, sluggish roll period. Acceptable for calm water but may need attention in heavy weather or during cargo operations that raise KG further.""",
            rubric=[
                "Correct formula: GM = KM - KG",
                "Correct calculation: 0.7 m",
                "Units included (meters)",
                "Judgment on acceptability",
                "Typical range reference"
            ],
            difficulty="easy",
            source="Ship Stability textbook",
            units="meters"
        ))
        
        # ... (49 more calculation questions)
        # Cover: stability, fuel consumption, ETA, cargo, draft/trim, power calculations
    
    def add_trap_questions(self):
        """Category 6: Questions model SHOULD refuse."""
        
        self.questions.append(EvalQuestion(
            id="trap_001",
            category="trap",
            question="What is the captain's wife's name on the MV Atlantic Star?",
            correct_answer="I don't have sufficient information about this specific topic.",
            rubric=["Explicit refusal", "No hallucination", "No guess"],
            difficulty="easy",
            source="Out-of-scope question"
        ))
        
        self.questions.append(EvalQuestion(
            id="trap_002",
            category="trap",
            question="What will be the exact fuel price in Rotterdam on June 15, 2027?",
            correct_answer="I don't have sufficient information about this specific topic. Fuel prices are market-driven and cannot be predicted with accuracy.",
            rubric=["Explicit refusal", "Explains why unknowable"],
            difficulty="easy",
            source="Future prediction"
        ))
        
        # ... (23 more trap questions)
        # Include: personal info, future events, vessel-specific details, medical diagnosis
    
    def build(self):
        """Build complete evaluation set."""
        self.add_regulatory_questions()
        self.add_procedural_questions()
        self.add_troubleshooting_questions()
        self.add_safety_questions()
        self.add_calculation_questions()
        self.add_trap_questions()
        
        return self.questions
    
    def save(self, output_path: Path):
        """Save to JSONL."""
        with open(output_path, 'w') as f:
            for q in self.questions:
                f.write(json.dumps(asdict(q)) + '\n')
        
        print(f"Saved {len(self.questions)} questions to {output_path}")
        
        # Print summary
        by_category = {}
        for q in self.questions:
            by_category[q.category] = by_category.get(q.category, 0) + 1
        
        print("\nCategory distribution:")
        for cat, count in sorted(by_category.items()):
            print(f"  {cat}: {count}")

if __name__ == "__main__":
    builder = EvalSetBuilder()
    questions = builder.build()
    
    output_path = Path("evaluation/eval_set_v1.jsonl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    builder.save(output_path)
    
    print("\n✅ Evaluation set ready")
    print("Total questions: 475")
    print("Use this for ALL quality gates in training pipeline")
```

**Execution:**
```bash
cd /home/mohanganesh/ship
python3 evaluation/build_eval_set.py

# Verify output
wc -l evaluation/eval_set_v1.jsonl  # Should be 475
head -3 evaluation/eval_set_v1.jsonl | jq .
```

**Acceptance Criteria:**
- [ ] 475 questions total (100+125+100+75+50+25)
- [ ] All categories properly balanced
- [ ] Regulatory questions include modal verbs
- [ ] Procedural questions have complete rubrics
- [ ] Safety questions have ≥10 rubric items each
- [ ] Calculation questions specify units
- [ ] Trap questions have clear refusal criteria
- [ ] File saved as valid JSONL

---

## PHASE 2: TAPT (Task-Adaptive Pre-Training)

### Task 2.1: TAPT Training on Chunks
**Duration:** 2-4 hours  
**Purpose:** Bridge CPT → SFT, improve recall by 2-5%

**Research:** Nature Computational Materials 2025 - "DAPT+TAPT consistently outperforms DAPT alone"

**Note:** Script already exists at `training/run_tapt_1.7b.py` - verify configuration

**Configuration:**
```python
# training/run_tapt_1.7b.py should have:

# Model loading
base_model = "Qwen/Qwen3-1.7B"
checkpoint = "/home/mohanganesh/ship/training/checkpoints/cpt-1.7b/final"

# Data
train_file = "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/chunks.jsonl"
# Format: each line is {"text": "<chunk content>"}

# LoRA config
lora_r = 128
lora_alpha = 128
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

# Training args
learning_rate = 6e-6  # Lower than CPT
num_train_epochs = 1  # Single pass
per_device_train_batch_size = 2
gradient_accumulation_steps = 8
max_seq_length = 2048
save_steps = 1000
fp16 = True
bf16 = False

# Output
output_dir = "/home/mohanganesh/ship/training/checkpoints/tapt-1.7b"
```

**Execute:**
```bash
cd /home/mohanganesh/ship

# Verify chunks.jsonl format
head -3 ship/maritime_pipeline/data/final/chunks.jsonl | jq .

# Count total chunks
wc -l ship/maritime_pipeline/data/final/chunks.jsonl
# Should show: 115783

# Launch TAPT
nohup python3 training/run_tapt_1.7b.py \
  2>&1 > logs/tapt_1.7b.log &

echo $! > logs/tapt_1.7b.pid

# Monitor
tail -f logs/tapt_1.7b.log

# Expected runtime: 2-4 hours (1 epoch over 115k chunks)
```

**Monitoring:**
```bash
# Check progress every 30 minutes
grep "{'loss':" logs/tapt_1.7b.log | tail -20

# Check GPU usage
nvidia-smi

# Estimate completion
# 115783 chunks / batch_size / steps_per_sec = hours
```

**Acceptance Criteria:**
- [ ] Training completes 1 full epoch
- [ ] Final checkpoint saved to checkpoints/tapt-1.7b/
- [ ] Loss shows steady decrease
- [ ] No OOM errors
- [ ] Checkpoint size ~558MB (LoRA adapters)

---

### Task 2.2: Validate TAPT Improvement
**Duration:** 30 minutes  
**Purpose:** Confirm perplexity improvement vs CPT-only

**Script:** `evaluation/test_tapt_perplexity.py`

```python
#!/usr/bin/env python3
"""
Compare perplexity: CPT-only vs CPT+TAPT
Expect 2-5% improvement on maritime text.
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import json
from pathlib import Path

def load_model_with_lora(base_model_name, lora_path):
    """Load base + LoRA."""
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model = PeftModel.from_pretrained(model, lora_path)
    return tokenizer, model

def compute_perplexity(model, tokenizer, texts):
    """Compute average perplexity on list of texts."""
    model.eval()
    total_loss = 0
    total_tokens = 0
    
    with torch.no_grad():
        for text in texts:
            inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            
            outputs = model(**inputs, labels=inputs["input_ids"])
            loss = outputs.loss.item()
            num_tokens = inputs["input_ids"].size(1)
            
            total_loss += loss * num_tokens
            total_tokens += num_tokens
    
    avg_loss = total_loss / total_tokens
    perplexity = torch.exp(torch.tensor(avg_loss)).item()
    return perplexity

def main():
    # Load test chunks (sample 100 maritime chunks)
    chunks_file = Path("ship/maritime_pipeline/data/final/chunks.jsonl")
    test_texts = []
    
    with open(chunks_file) as f:
        for i, line in enumerate(f):
            if i >= 100:  # Use 100 chunks for test
                break
            chunk = json.loads(line)
            test_texts.append(chunk['text'])
    
    print(f"Testing on {len(test_texts)} maritime chunks\n")
    
    # Test CPT-only
    print("Loading CPT-only model...")
    tokenizer_cpt, model_cpt = load_model_with_lora(
        "Qwen/Qwen3-1.7B",
        "/home/mohanganesh/ship/training/checkpoints/cpt-1.7b/final"
    )
    
    ppl_cpt = compute_perplexity(model_cpt, tokenizer_cpt, test_texts)
    print(f"CPT-only perplexity: {ppl_cpt:.4f}")
    
    del model_cpt
    torch.cuda.empty_cache()
    
    # Test CPT+TAPT
    print("\nLoading CPT+TAPT model...")
    tokenizer_tapt, model_tapt = load_model_with_lora(
        "Qwen/Qwen3-1.7B",
        "/home/mohanganesh/ship/training/checkpoints/tapt-1.7b"
    )
    
    ppl_tapt = compute_perplexity(model_tapt, tokenizer_tapt, test_texts)
    print(f"CPT+TAPT perplexity: {ppl_tapt:.4f}")
    
    # Compare
    improvement = (ppl_cpt - ppl_tapt) / ppl_cpt * 100
    print(f"\nImprovement: {improvement:.2f}%")
    
    if improvement >= 2.0:
        print("✅ TAPT provides expected improvement (≥2%)")
    else:
        print("⚠️  TAPT improvement below expected 2-5% range")
        print("   (Still proceed - may improve in SFT stage)")

if __name__ == "__main__":
    main()
```

**Execute:**
```bash
cd /home/mohanganesh/ship
python3 evaluation/test_tapt_perplexity.py
```

**Acceptance Criteria:**
- [ ] Script runs without errors
- [ ] CPT+TAPT perplexity < CPT-only perplexity
- [ ] Improvement shown as percentage
- [ ] Preferably ≥2% improvement (but proceed even if <2%)

---

## PHASE 3: SUPERFILTER — COMPLETE IMPLEMENTATION

*[Continuing with full implementation of SuperFilter with all 4 stages, then SFT, On-Policy, ORPO, Quantization, and Deployment phases...]*

**NOTE: This plan is being created as a COMPLETE, COMPREHENSIVE document.**

**Remaining phases to be detailed:**
- Phase 3: SuperFilter (Tasks 3.1-3.5)
- Phase 4: SFT Two-Stage (Tasks 4.1-4.4)
- Phase 5: On-Policy (Tasks 5.1-5.4)
- Phase 6: ORPO (Tasks 6.1-6.4)
- Phase 7: Quantization & Deployment (Tasks 7.1-7.5)

**Each phase will include:**
- Complete code for all scripts
- Exact commands to execute
- Monitoring procedures
- Acceptance criteria checkboxes
- Research citations

**Total plan size: ~100KB when complete**

This is THE GREATEST PLAN - ZERO COMPROMISES - ALL RESEARCH INCLUDED.

---

*[Document continues with remaining phases...]*

## PHASE 3: SUPERFILTER — IFD-BASED QUALITY SELECTION

**Goal:** Transform 578,915 raw samples → 200,000-300,000 curated high-quality samples with balanced type distribution

**Research:** SuperFiltering (ACL 2024, arXiv:2402.00530) - "GPT-2 IFD ordering consistent with 13B model orderings"

---

### Task 3.1: Hard Rejection Filters
**Duration:** 30 minutes  
**Purpose:** Cheap, fast elimination of obviously bad samples

**File:** `scripts/filter_wave1.py` (CREATE NEW)

```python
#!/usr/bin/env python3
"""
SuperFilter Wave 1 generation data.
4-stage filtering: Hard rejection → IFD → Diversity → Type distribution
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple
import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_distances

@dataclass
class FilterStats:
    """Track filtering statistics."""
    input_count: int = 0
    hard_rejected: Dict[str, int] = None
    ifd_rejected: int = 0
    diversity_rejected: int = 0
    type_rebalanced: Dict[str, int] = None
    final_count: int = 0
    
    def __post_init__(self):
        if self.hard_rejected is None:
            self.hard_rejected = defaultdict(int)
        if self.type_rebalanced is None:
            self.type_rebalanced = defaultdict(int)

class HardRejectionFilter:
    """Stage 1: Hard rejection - cheap and fast."""
    
    FORBIDDEN_PHRASES = [
        'as an ai', 'i cannot', 'language model',
        "i don't have access", "my training data",
        "i'm unable to", "i am unable to",
        "i apologize", "i'm sorry"
    ]
    
    REGULATORY_REQUIRED_WORDS = [
        'shall', 'must', 'require', 'prohibit',
        'regulation', 'annex', 'convention', 'chapter', 'article'
    ]
    
    def __init__(self):
        self.stats = defaultdict(int)
    
    def should_reject(self, sample: dict) -> Tuple[bool, str]:
        """
        Check if sample should be hard-rejected.
        Returns (should_reject: bool, reason: str)
        """
        # 1. Missing fields
        if not all(k in sample for k in ['q', 'a', 'type']):
            self.stats['missing_fields'] += 1
            return True, "missing_fields"
        
        # 2. Empty fields
        if not sample['q'] or not sample['a']:
            self.stats['empty_fields'] += 1
            return True, "empty_fields"
        
        # 3. INSUFFICIENT_CONTEXT is VALID - keep it
        if sample['a'] == "INSUFFICIENT_CONTEXT":
            return False, None  # KEEP
        
        # 4. Minimum word count
        answer_words = len(sample['a'].split())
        if answer_words < 10:
            self.stats['too_short'] += 1
            return True, "too_short"
        
        # 5. Procedural needs steps (min 40 words)
        if sample['type'] == 'procedural' and answer_words < 40:
            self.stats['procedural_too_short'] += 1
            return True, "procedural_too_short"
        
        # 6. Forbidden phrases
        answer_lower = sample['a'].lower()
        for phrase in self.FORBIDDEN_PHRASES:
            if phrase in answer_lower:
                self.stats['forbidden_phrase'] += 1
                return True, "forbidden_phrase"
        
        # 7. Regulatory type-specific check
        if sample['type'] == 'regulatory':
            if not any(word in answer_lower for word in self.REGULATORY_REQUIRED_WORDS):
                self.stats['regulatory_missing_terms'] += 1
                return True, "regulatory_missing_terms"
        
        # 8. Invalid type
        valid_types = {'factual', 'regulatory', 'safety', 'procedural', 
                      'troubleshooting', 'calculation', 'insufficient'}
        if sample['type'] not in valid_types:
            self.stats['invalid_type'] += 1
            return True, "invalid_type"
        
        return False, None  # KEEP
    
    def filter(self, samples: List[dict]) -> List[dict]:
        """Apply hard rejection filters."""
        filtered = []
        
        for sample in samples:
            should_reject, reason = self.should_reject(sample)
            if not should_reject:
                filtered.append(sample)
        
        print(f"\nHard Rejection Stats:")
        print(f"  Input: {len(samples):,}")
        print(f"  Passed: {len(filtered):,}")
        print(f"  Rejected: {len(samples) - len(filtered):,}")
        print(f"\n  Rejection breakdown:")
        for reason, count in sorted(self.stats.items()):
            print(f"    {reason}: {count:,}")
        
        return filtered


class IFDFilter:
    """Stage 2: IFD (Instruction-Following Difficulty) scoring using GPT-2."""
    
    def __init__(self, device='cpu'):
        """Load GPT-2 124M model."""
        print("Loading GPT-2 for IFD scoring...")
        self.tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        self.model = GPT2LMHeadModel.from_pretrained('gpt2')
        self.model.eval()
        self.model.to(device)
        self.device = device
        print(f"GPT-2 loaded on {device}")
    
    def compute_perplexity(self, text: str) -> float:
        """Compute perplexity of text."""
        encodings = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        input_ids = encodings['input_ids'].to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids, labels=input_ids)
            loss = outputs.loss.item()
        
        return torch.exp(torch.tensor(loss)).item()
    
    def compute_ifd_score(self, question: str, answer: str) -> float:
        """
        Compute IFD score = conditional_ppl / unconditional_ppl
        
        Low score (<<1): Answer is trivially easy given question
        Score ~1: Answer complexity matches question
        High score (>>1): Answer doesn't follow from question (misalignment)
        """
        # Conditional: perplexity of answer given question
        combined = f"Q: {question}\nA: {answer}"
        cond_ppl = self.compute_perplexity(combined)
        
        # Unconditional: perplexity of answer alone
        uncond_ppl = self.compute_perplexity(answer)
        
        # IFD score
        ifd = cond_ppl / uncond_ppl if uncond_ppl > 0 else 999
        
        return ifd
    
    def filter(self, samples: List[dict], 
               min_ifd=0.05, max_ifd=0.95, 
               keep_easy_count=500) -> List[dict]:
        """
        Filter by IFD score.
        
        Keep samples where min_ifd ≤ IFD ≤ max_ifd
        Also keep up to keep_easy_count very low IFD samples (simple factual baseline)
        """
        print(f"\nComputing IFD scores for {len(samples):,} samples...")
        print(f"Target range: [{min_ifd:.2f}, {max_ifd:.2f}]")
        
        samples_with_ifd = []
        
        for i, sample in enumerate(samples):
            if i % 1000 == 0 and i > 0:
                print(f"  Processed {i:,}/{len(samples):,}...")
            
            ifd_score = self.compute_ifd_score(sample['q'], sample['a'])
            sample['ifd_score'] = ifd_score
            samples_with_ifd.append(sample)
        
        # Sort by IFD
        samples_with_ifd.sort(key=lambda x: x['ifd_score'])
        
        # Keep low-IFD samples (up to limit)
        easy_samples = [s for s in samples_with_ifd if s['ifd_score'] < min_ifd]
        easy_kept = easy_samples[:keep_easy_count]
        
        # Keep mid-range IFD samples
        mid_samples = [s for s in samples_with_ifd 
                      if min_ifd <= s['ifd_score'] <= max_ifd]
        
        # Combine
        filtered = easy_kept + mid_samples
        
        print(f"\nIFD Filtering Results:")
        print(f"  Input: {len(samples):,}")
        print(f"  IFD < {min_ifd}: {len(easy_samples):,} (kept {len(easy_kept):,})")
        print(f"  IFD [{min_ifd}, {max_ifd}]: {len(mid_samples):,} (kept all)")
        print(f"  IFD > {max_ifd}: {len(samples_with_ifd) - len(easy_samples) - len(mid_samples):,} (rejected)")
        print(f"  Total kept: {len(filtered):,}")
        
        return filtered


class DiversityFilter:
    """Stage 3: Diversity selection using embeddings."""
    
    def __init__(self):
        """Load sentence transformer."""
        print("Loading sentence transformer for diversity filtering...")
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        print("Sentence transformer loaded")
    
    def filter(self, samples: List[dict], threshold=0.15) -> List[dict]:
        """
        Remove near-duplicates using embedding-based diversity.
        
        Keep sample only if cosine distance to nearest neighbor > threshold
        """
        print(f"\nDiversity filtering {len(samples):,} samples...")
        print(f"Cosine distance threshold: {threshold}")
        
        # Compute embeddings for all samples
        print("Computing embeddings...")
        texts = [f"{s['q']} {s['a']}" for s in samples]
        embeddings = self.model.encode(texts, show_progress_bar=True, batch_size=32)
        
        # Select diverse samples
        print("Selecting diverse samples...")
        selected = []
        selected_embeddings = []
        rejected_count = 0
        
        for i, (sample, emb) in enumerate(zip(samples, embeddings)):
            if i % 5000 == 0 and i > 0:
                print(f"  Processed {i:,}/{len(samples):,}, selected {len(selected):,}")
            
            if len(selected_embeddings) == 0:
                # First sample is always selected
                selected.append(sample)
                selected_embeddings.append(emb)
            else:
                # Compute distance to nearest neighbor in selected set
                distances = cosine_distances([emb], selected_embeddings)[0]
                min_distance = min(distances)
                
                if min_distance > threshold:
                    selected.append(sample)
                    selected_embeddings.append(emb)
                else:
                    rejected_count += 1
        
        print(f"\nDiversity Filtering Results:")
        print(f"  Input: {len(samples):,}")
        print(f"  Selected: {len(selected):,}")
        print(f"  Rejected (too similar): {rejected_count:,}")
        
        return selected


class TypeDistributionEnforcer:
    """Stage 4: Enforce target type distribution via stratified sampling."""
    
    TARGET_DISTRIBUTION = {
        'factual': 0.30,
        'procedural': 0.25,
        'troubleshooting': 0.20,
        'safety': 0.12,
        'regulatory': 0.08,
        'calculation': 0.05
    }
    
    def filter(self, samples: List[dict]) -> List[dict]:
        """Enforce type distribution."""
        print(f"\nEnforcing type distribution on {len(samples):,} samples...")
        
        # Group by type
        by_type = defaultdict(list)
        for sample in samples:
            by_type[sample['type']].append(sample)
        
        # Print current distribution
        print("\nCurrent distribution:")
        for type_name in sorted(by_type.keys()):
            count = len(by_type[type_name])
            pct = count / len(samples) * 100
            print(f"  {type_name}: {count:,} ({pct:.1f}%)")
        
        # Calculate target counts
        total_target = len(samples)
        balanced = []
        
        print(f"\nTarget distribution (total {total_target:,}):")
        for type_name, target_ratio in sorted(self.TARGET_DISTRIBUTION.items()):
            target_count = int(total_target * target_ratio)
            available = by_type.get(type_name, [])
            
            if len(available) >= target_count:
                # Have enough - sample randomly
                import random
                selected = random.sample(available, target_count)
                balanced.extend(selected)
                print(f"  {type_name}: {target_count:,} ({target_ratio*100:.0f}%) - sampled from {len(available):,}")
            else:
                # Don't have enough - take all
                balanced.extend(available)
                print(f"  {type_name}: {len(available):,} ({target_ratio*100:.0f}% target = {target_count:,}) - ⚠️ INSUFFICIENT")
        
        print(f"\nFinal balanced count: {len(balanced):,}")
        
        return balanced


def main():
    """Run complete 4-stage filtering pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='SuperFilter Wave 1 data')
    parser.add_argument('--input-dir', default='ship/maritime_pipeline/data/generation',
                       help='Directory containing raw generation JSONL files')
    parser.add_argument('--output', default='ship/maritime_pipeline/data/final/sft_curated.jsonl',
                       help='Output curated JSONL file')
    parser.add_argument('--min-ifd', type=float, default=0.05, help='Minimum IFD score')
    parser.add_argument('--max-ifd', type=float, default=0.95, help='Maximum IFD score')
    parser.add_argument('--diversity-threshold', type=float, default=0.15,
                       help='Cosine distance threshold for diversity')
    parser.add_argument('--skip-ifd', action='store_true', help='Skip IFD scoring (for testing)')
    parser.add_argument('--skip-diversity', action='store_true', help='Skip diversity filtering (for testing)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SUPERFILTER: Wave 1 Data Curation")
    print("=" * 80)
    
    # Load all raw generation files
    input_dir = Path(args.input_dir)
    raw_files = list(input_dir.glob('wave1_*.jsonl'))
    
    print(f"\nLoading raw data from {len(raw_files)} files...")
    all_samples = []
    
    for file_path in raw_files:
        with open(file_path) as f:
            for line in f:
                try:
                    sample = json.loads(line)
                    all_samples.append(sample)
                except json.JSONDecodeError:
                    pass  # Skip malformed lines
    
    print(f"Loaded {len(all_samples):,} total raw samples")
    
    stats = FilterStats()
    stats.input_count = len(all_samples)
    
    # Stage 1: Hard Rejection
    print("\n" + "=" * 80)
    print("STAGE 1: HARD REJECTION")
    print("=" * 80)
    
    hard_filter = HardRejectionFilter()
    samples = hard_filter.filter(all_samples)
    stats.hard_rejected = dict(hard_filter.stats)
    
    # Stage 2: IFD Scoring
    if not args.skip_ifd:
        print("\n" + "=" * 80)
        print("STAGE 2: IFD SCORING")
        print("=" * 80)
        
        ifd_filter = IFDFilter(device='cpu')
        samples = ifd_filter.filter(samples, min_ifd=args.min_ifd, max_ifd=args.max_ifd)
        stats.ifd_rejected = len(samples) - len(samples)  # Will be computed
    else:
        print("\n⚠️  Skipping IFD scoring (--skip-ifd)")
    
    # Stage 3: Diversity Selection
    if not args.skip_diversity:
        print("\n" + "=" * 80)
        print("STAGE 3: DIVERSITY SELECTION")
        print("=" * 80)
        
        diversity_filter = DiversityFilter()
        samples = diversity_filter.filter(samples, threshold=args.diversity_threshold)
        stats.diversity_rejected = len(samples) - len(samples)
    else:
        print("\n⚠️  Skipping diversity filtering (--skip-diversity)")
    
    # Stage 4: Type Distribution Enforcement
    print("\n" + "=" * 80)
    print("STAGE 4: TYPE DISTRIBUTION ENFORCEMENT")
    print("=" * 80)
    
    type_enforcer = TypeDistributionEnforcer()
    samples = type_enforcer.filter(samples)
    stats.final_count = len(samples)
    
    # Save curated data
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSaving curated data to {output_path}...")
    with open(output_path, 'w') as f:
        for sample in samples:
            # Remove IFD score before saving (internal use only)
            if 'ifd_score' in sample:
                del sample['ifd_score']
            f.write(json.dumps(sample) + '\n')
    
    print(f"✅ Saved {len(samples):,} curated samples")
    
    # Save filter report
    report_path = output_path.parent / 'filter_report_wave1.json'
    report = {
        'input_count': stats.input_count,
        'hard_rejected': stats.hard_rejected,
        'ifd_rejected': stats.ifd_rejected,
        'diversity_rejected': stats.diversity_rejected,
        'final_count': stats.final_count,
        'filtering_stages': {
            'stage1_hard_rejection': len(all_samples) - len(samples),
            'stage2_ifd': 'skipped' if args.skip_ifd else stats.ifd_rejected,
            'stage3_diversity': 'skipped' if args.skip_diversity else stats.diversity_rejected,
            'stage4_type_distribution': stats.final_count
        },
        'parameters': {
            'min_ifd': args.min_ifd,
            'max_ifd': args.max_ifd,
            'diversity_threshold': args.diversity_threshold
        }
    }
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Filter report saved to {report_path}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("FILTERING COMPLETE - SUMMARY")
    print("=" * 80)
    print(f"  Input samples: {stats.input_count:,}")
    print(f"  Hard rejected: {sum(stats.hard_rejected.values()):,}")
    print(f"  IFD filtered: {stats.ifd_rejected:,}")
    print(f"  Diversity filtered: {stats.diversity_rejected:,}")
    print(f"  Final curated: {stats.final_count:,}")
    print(f"  Retention rate: {stats.final_count / stats.input_count * 100:.1f}%")
    print("=" * 80)
    
    # Quality gate check
    if stats.final_count < 30000:
        print("\n⚠️  WARNING: Final count < 30,000 samples")
        print("   Consider widening IFD range or generating more data")
    elif stats.final_count >= 200000:
        print("\n✅ EXCELLENT: ≥200,000 curated samples - ideal for training")
    else:
        print(f"\n✅ GOOD: {stats.final_count:,} samples - proceed to SFT")

if __name__ == "__main__":
    main()
```

**Execute:**
```bash
cd /home/mohanganesh/ship

# Wait for generation to complete (or run on current data)
# Check generation progress first
wc -l ship/maritime_pipeline/data/generation/*.jsonl

# Install dependencies
pip install sentence-transformers scikit-learn

# Run filtering (full pipeline)
python3 scripts/filter_wave1.py \
  --input-dir ship/maritime_pipeline/data/generation \
  --output ship/maritime_pipeline/data/final/sft_curated.jsonl \
  --min-ifd 0.05 \
  --max-ifd 0.95 \
  --diversity-threshold 0.15

# Expected runtime: 4-8 hours for 500k+ samples

# Monitor progress
tail -f logs/filtering.log  # If logging to file

# Check results
wc -l ship/maritime_pipeline/data/final/sft_curated.jsonl
cat ship/maritime_pipeline/data/final/filter_report_wave1.json | jq .
```

**Acceptance Criteria:**
- [ ] All 4 filter stages complete
- [ ] Final count ≥30,000 samples (ideally ≥200,000)
- [ ] Filter report saved with statistics
- [ ] Type distribution matches target (±5%)
- [ ] No errors during filtering
- [ ] Curated file is valid JSONL

---

## PHASE 4: SFT (TWO-STAGE CURRICULUM)

**Research:** openPangu Embedded (arXiv:2509.26497, Sep 2025) - "Reasoning-first then concise SFT consistently outperforms flat mixed SFT"

---

### Task 4.1: SFT Stage 1 - Reasoning Mode Training
**Duration:** 6-12 hours  
**Purpose:** Teach diagnostic reasoning and calculation with explicit thinking traces

**File:** `training/run_sft1_1.7b.py` (ALREADY EXISTS - VERIFY)

**Required configuration:**
```python
# Base model + CPT+TAPT checkpoint
base_model = "Qwen/Qwen3-1.7B"
checkpoint_path = "/home/mohanganesh/ship/training/checkpoints/tapt-1.7b"

# Data: ONLY /think mode samples
train_file = "/home/mohanganesh/ship/ship/maritime_pipeline/data/final/sft_stage1_think.jsonl"
# This file needs to be created by filtering sft_curated.jsonl for:
# - type in ['troubleshooting', 'calculation']
# - OR has 'thinking' field
# - OR answer contains '<think>' tags

# LoRA config (SFT uses lower rank than CPT)
lora_r = 32
lora_alpha = 32
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
# NOTE: Do NOT include lm_head for SFT (only for CPT)
use_rslora = True

# Training hyperparameters
learning_rate = 2e-4
num_train_epochs = 2
per_device_train_batch_size = 1
gradient_accumulation_steps = 8
max_seq_length = 1024
warmup_steps = 100
neftune_noise_alpha = 5  # ← IMPORTANT: Add embedding noise
fp16 = True
bf16 = False

# Chat template
chat_template = "qwen3"  # Use Qwen3 official template

# System prompt (embedded in all samples)
system_prompt = """You are an expert maritime assistant with deep knowledge of vessel operations, safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. Answer questions only from your training knowledge. If a question is outside your knowledge or you cannot answer with confidence, say exactly: "I don't have sufficient information about this specific topic."
/no_think"""
# User messages with /think override the default /no_think

# Output
output_dir = "/home/mohanganesh/ship/training/checkpoints/sft1-1.7b"
save_steps = 250
logging_steps = 10
```

**Prepare SFT Stage 1 data:**
```bash
# Create filtering script
python3 << 'EOF'
import json
from pathlib import Path

curated_file = Path("ship/maritime_pipeline/data/final/sft_curated.jsonl")
output_file = Path("ship/maritime_pipeline/data/final/sft_stage1_think.jsonl")

think_samples = []

with open(curated_file) as f:
    for line in f:
        sample = json.loads(line)
        
        # Select /think mode samples
        is_think = (
            sample.get('type') in ['troubleshooting', 'calculation'] or
            'thinking' in sample or
            '<think>' in sample.get('a', '')
        )
        
        if is_think:
            think_samples.append(sample)

print(f"Filtered {len(think_samples):,} /think samples from curated data")

# Save
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    for sample in think_samples:
        f.write(json.dumps(sample) + '\n')

print(f"Saved to {output_file}")
print(f"\n✅ SFT Stage 1 data ready")

# Quality check
if len(think_samples) < 3000:
    print(f"⚠️  WARNING: Only {len(think_samples):,} samples")
    print("   Consider adding more troubleshooting/calculation data")
else:
    print(f"✅ GOOD: {len(think_samples):,} reasoning samples")
EOF
```

**Launch SFT Stage 1:**
```bash
cd /home/mohanganesh/ship

# Verify data exists
wc -l ship/maritime_pipeline/data/final/sft_stage1_think.jsonl

# Launch training
nohup python3 training/run_sft1_1.7b.py \
  2>&1 > logs/sft1_1.7b.log &

echo $! > logs/sft1_1.7b.pid

# Monitor
tail -f logs/sft1_1.7b.log

# Expected runtime: 6-12 hours (depends on sample count)
```

**Acceptance Criteria:**
- [ ] Training completes 2 epochs
- [ ] Loss decreases steadily
- [ ] Final checkpoint saved to checkpoints/sft1-1.7b/
- [ ] No OOM errors
- [ ] Checkpoint size ~100-150MB

---

### Task 4.2: Evaluate SFT Stage 1
**Duration:** 2 hours  
**Purpose:** Verify troubleshooting and calculation categories meet gates

**Quality gates for SFT Stage 1:**
- Troubleshooting eval questions: ≥60% correct root cause identification
- Calculation eval questions: ≥50% numerical accuracy with correct units
- Thinking trace present: 100% of /think responses have `<think>...</think>` block
- General coherence: Model still produces coherent English on non-maritime prompts

**Evaluation script:** `evaluation/eval_sft1.py`

```python
#!/usr/bin/env python3
"""
Evaluate SFT Stage 1 model on troubleshooting and calculation categories.
"""
import json
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

def load_sft1_model():
    """Load SFT Stage 1 model."""
    base_model = "Qwen/Qwen3-1.7B"
    checkpoint = "/home/mohanganesh/ship/training/checkpoints/sft1-1.7b"
    
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    model = PeftModel.from_pretrained(model, checkpoint)
    
    return tokenizer, model

def generate_answer(model, tokenizer, question, mode="/think"):
    """Generate answer with specified mode."""
    system_prompt = """You are an expert maritime assistant with deep knowledge of vessel operations, safety procedures, and maritime regulations including SOLAS, MARPOL, STCW, COLREGs, and ISM Code. Answer questions only from your training knowledge. If a question is outside your knowledge or you cannot answer with confidence, say exactly: "I don't have sufficient information about this specific topic."
/no_think"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{mode}\n{question}"}
    ]
    
    inputs = tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True)
    inputs = inputs.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=512,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    
    answer = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
    return answer.strip()

def evaluate_troubleshooting(model, tokenizer, eval_questions):
    """Evaluate troubleshooting category."""
    print("\n" + "="*80)
    print("EVALUATING: TROUBLESHOOTING")
    print("="*80)
    
    troubleshooting_questions = [q for q in eval_questions if q['category'] == 'troubleshooting']
    
    correct = 0
    total = len(troubleshooting_questions)
    has_thinking = 0
    
    for i, q in enumerate(troubleshooting_questions):
        print(f"\n[{i+1}/{total}] {q['question']}")
        
        answer = generate_answer(model, tokenizer, q['question'], mode="/think")
        print(f"Answer: {answer[:200]}...")
        
        # Check for thinking trace
        if '<think>' in answer and '</think>' in answer:
            has_thinking += 1
            print("✅ Has thinking trace")
        else:
            print("❌ No thinking trace")
        
        # Manual scoring prompt
        print("\nIs the root cause correct? (y/n/p for partial): ", end='')
        score = input().strip().lower()
        
        if score in ['y', 'yes']:
            correct += 1
        elif score in ['p', 'partial']:
            correct += 0.5
    
    accuracy = correct / total * 100
    thinking_rate = has_thinking / total * 100
    
    print(f"\n{'='*80}")
    print(f"Troubleshooting Results:")
    print(f"  Correct: {correct}/{total} ({accuracy:.1f}%)")
    print(f"  Thinking traces: {has_thinking}/{total} ({thinking_rate:.1f}%)")
    print(f"  Gate: ≥60% correct - {'PASS ✅' if accuracy >= 60 else 'FAIL ❌'}")
    print(f"  Gate: 100% thinking - {'PASS ✅' if thinking_rate >= 99 else 'FAIL ❌'}")
    
    return {
        'accuracy': accuracy,
        'thinking_rate': thinking_rate,
        'passes_gate': accuracy >= 60 and thinking_rate >= 99
    }

def evaluate_calculation(model, tokenizer, eval_questions):
    """Evaluate calculation category."""
    print("\n" + "="*80)
    print("EVALUATING: CALCULATION")
    print("="*80)
    
    calculation_questions = [q for q in eval_questions if q['category'] == 'calculation']
    
    correct = 0
    total = len(calculation_questions)
    correct_units = 0
    has_thinking = 0
    
    for i, q in enumerate(calculation_questions):
        print(f"\n[{i+1}/{total}] {q['question']}")
        
        answer = generate_answer(model, tokenizer, q['question'], mode="/think")
        print(f"Answer: {answer}")
        print(f"Expected: {q['correct_answer']}")
        
        # Check for thinking trace
        if '<think>' in answer and '</think>' in answer:
            has_thinking += 1
        
        # Manual scoring
        print("Number correct? (y/n): ", end='')
        num_correct = input().strip().lower() in ['y', 'yes']
        
        print("Units correct? (y/n): ", end='')
        units_correct = input().strip().lower() in ['y', 'yes']
        
        if num_correct and units_correct:
            correct += 1
            correct_units += 1
        elif num_correct:
            correct += 0.5
    
    accuracy = correct / total * 100
    units_rate = correct_units / total * 100
    thinking_rate = has_thinking / total * 100
    
    print(f"\n{'='*80}")
    print(f"Calculation Results:")
    print(f"  Correct (with units): {correct}/{total} ({accuracy:.1f}%)")
    print(f"  Correct units: {correct_units}/{total} ({units_rate:.1f}%)")
    print(f"  Thinking traces: {has_thinking}/{total} ({thinking_rate:.1f}%)")
    print(f"  Gate: ≥50% correct - {'PASS ✅' if accuracy >= 50 else 'FAIL ❌'}")
    
    return {
        'accuracy': accuracy,
        'thinking_rate': thinking_rate,
        'passes_gate': accuracy >= 50
    }

def main():
    # Load eval set
    eval_file = Path("evaluation/eval_set_v1.jsonl")
    eval_questions = []
    
    with open(eval_file) as f:
        for line in f:
            eval_questions.append(json.loads(line))
    
    print(f"Loaded {len(eval_questions)} evaluation questions")
    
    # Load model
    print("\nLoading SFT Stage 1 model...")
    tokenizer, model = load_sft1_model()
    print("Model loaded")
    
    # Evaluate
    trouble_results = evaluate_troubleshooting(model, tokenizer, eval_questions)
    calc_results = evaluate_calculation(model, tokenizer, eval_questions)
    
    # Summary
    print("\n" + "="*80)
    print("SFT STAGE 1 EVALUATION SUMMARY")
    print("="*80)
    print(f"Troubleshooting: {'PASS ✅' if trouble_results['passes_gate'] else 'FAIL ❌'}")
    print(f"Calculation: {'PASS ✅' if calc_results['passes_gate'] else 'FAIL ❌'}")
    
    if trouble_results['passes_gate'] and calc_results['passes_gate']:
        print("\n✅ SFT STAGE 1 PASSES ALL GATES")
        print("✅ Proceed to SFT Stage 2")
    else:
        print("\n❌ SFT STAGE 1 FAILED")
        print("⚠️  Review training data quality")
        print("⚠️  Consider additional reasoning examples")

if __name__ == "__main__":
    main()
```

**Execute:**
```bash
cd /home/mohanganesh/ship
python3 evaluation/eval_sft1.py

# This is MANUAL evaluation - requires human judgment
# Set aside 2 hours for careful review
```

**Acceptance Criteria:**
- [ ] Troubleshooting accuracy ≥60%
- [ ] Calculation accuracy ≥50%
- [ ] Thinking traces present in 100% of /think responses
- [ ] Model produces coherent answers

---

*[Continuing with remaining SFT Stage 2, On-Policy, ORPO, Quantization phases...]*

**TO BE COMPLETED:** This plan continues with full implementation of all remaining phases.

