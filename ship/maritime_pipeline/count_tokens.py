#!/usr/bin/env python3
"""Count words/tokens across all data sources.

This script intentionally uses a *rough* token estimate based on word counts.
It is meant for quick corpus sizing, not exact tokenizer-level accounting.
"""

import json
from pathlib import Path


base = Path(__file__).resolve().parent
total_words = 0

print("=== JSONL Sources ===")
for jf in sorted((base / 'data' / 'extracted_text').glob('*.jsonl')):
    if jf.stat().st_size == 0:
        continue
    words = 0
    lines = 0
    with open(jf) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Try common text fields
                text = (obj.get('text') or obj.get('content') or 
                        obj.get('body') or obj.get('summary') or
                        obj.get('article_text') or obj.get('full_text') or '')
                if not text:
                    # Combine all string values
                    text = ' '.join(str(v) for v in obj.values() if isinstance(v, str))
                words += len(text.split())
                lines += 1
            except:
                pass
    print(f"  {words:>10,} words ({lines} docs): {jf.name}")
    total_words += words

print()
print("=== Extracted Text Files ===")
txt_words = 0
txt_count = 0
for src_dir in sorted((base / 'data' / 'extracted_text').iterdir()):
    if src_dir.is_dir():
        src_words = 0
        src_count = 0
        for tf in src_dir.rglob('*.txt'):
            w = len(tf.read_text(errors='ignore').split())
            src_words += w
            src_count += 1
        if src_count > 0:
            print(f"  {src_words:>10,} words ({src_count} files): {src_dir.name}/")
            txt_words += src_words
            txt_count += src_count

total_words += txt_words

print()
print(f"=== TOTALS ===")
print(f"  JSONL text:   {total_words - txt_words:>10,} words")
print(f"  Extracted .txt: {txt_words:>10,} words ({txt_count} files)")
print(f"  GRAND TOTAL:  {total_words:>10,} words")
print(f"  ≈ tokens:     {int(total_words * 1.3):>10,} tokens (×1.3 estimate)")
print(f"  ≈ tokens (÷0.75): {int(total_words / 0.75):>10,} tokens")
