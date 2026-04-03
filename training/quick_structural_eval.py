#!/usr/bin/env python3
"""Quick structural eval for Boundary-v2 candidate using the v2 benchmark."""
import sys
sys.path.insert(0, '/home/mohanganesh/ship/training')

from pathlib import Path
from collections import defaultdict
from phase2_optionc_common import (
    load_tokenizer, load_merged_model_from_adapter,
    generate_response, read_jsonl, normalize_space,
    strip_think, REGULATORY_MODAL_CUES, TRAP_REJECTION_CUES, escalation_alias_match
)


def structural_pass(answer, category, item):
    text = strip_think(normalize_space(answer))
    lowered = text.lower()
    esc_targets = item.get('escalation_targets', [])
    esc_hit = (not esc_targets) or any(
        any(escalation_alias_match(t, line) for line in text.splitlines())
        for t in esc_targets
    )
    trap_ok = True
    if category == 'trap':
        trap_ok = any(c in lowered for c in TRAP_REJECTION_CUES)
    modal_ok = True
    if category == 'regulatory':
        modal_ok = any(c in lowered for c in REGULATORY_MODAL_CUES)
    do_not_ok = True
    if item.get('do_not') and category in ('trap', 'safety', 'regulatory'):
        do_not_ok = 'do not' in lowered or 'must not' in lowered or 'prohibited' in lowered
    return esc_hit and trap_ok and modal_ok and do_not_ok


CANDIDATE = Path('/home/mohanganesh/ship/training/checkpoints/boundary-v2-1.7b/candidate')
BENCHMARK = Path('/home/mohanganesh/ship/ship/maritime_pipeline/data/final/local_benchmark_v2_1p7b.jsonl')

print('Loading model from candidate...')
tok = load_tokenizer()
model = load_merged_model_from_adapter(CANDIDATE, 'EVAL')
model.eval()
print('Model loaded.')

bm = read_jsonl(BENCHMARK)
grouped = defaultdict(list)
for item in bm:
    grouped[item['category']].append(item)

results = {}
for cat, items in sorted(grouped.items()):
    subset = items[:10]
    passed = 0
    for item in subset:
        mode = 'think' if cat in ('troubleshooting', 'calculation') else 'no_think'
        ans = generate_response(model, tok, item['question'], mode=mode, max_new_tokens=300)
        ok = structural_pass(ans, cat, item)
        if ok:
            passed += 1
    rate = passed / len(subset) * 100
    results[cat] = (passed, len(subset), rate)
    print(f'  {cat}: {passed}/{len(subset)} ({rate:.0f}%)')

trap_r = results.get('trap', (0, 0, 0))[2]
safety_r = results.get('safety', (0, 0, 0))[2]
print(f'\nGATE: trap={trap_r:.0f}% safety={safety_r:.0f}% (need trap>=60 safety>=50)')
print('GATE RESULT:', 'PASS' if trap_r >= 60 and safety_r >= 50 else 'FAIL')
