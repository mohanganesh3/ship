# Stage 0 – Training-ready artifacts (offline)

This folder contains the Stage‑0 dataset builders that turn **extracted text** into the artifacts expected by the master plan.

## What it produces

Outputs are written to `ship/maritime_pipeline/data/final/`:

- `cpt_corpus.jsonl` – canonical, traceable maritime corpus
- `filter_report.jsonl` – every rejection w/ reason
- `cpt_corpus_deduped.jsonl` – MinHash-deduped corpus (doc_type-aware thresholds)
- `dedup_report.jsonl` – every near-dup removal (removed_id → kept_id)
- `general_replay.jsonl` – general-domain replay corpus (user-provided)
- `cpt_val_maritime.jsonl` – maritime validation split
- `cpt_val_general.jsonl` – general validation split
- `chunks.jsonl` – SFT-ready chunks (procedure-preserving)
- `eval_set.jsonl` – eval scaffold (manual fill required)
- `pipeline_audit.log` – append-only audit log of the full run

## How to run

Run from `ship/maritime_pipeline/` so that `stage0` is importable:

- `python -m stage0.run_stage0 --allow-empty-general`

Omit `--allow-empty-general` once you have a real general corpus available.

## General corpus input

`general_replay.jsonl` is built from either:

- `ship/maritime_pipeline/data/general/**/*.jsonl` (each record must have a `text` field), or
- `ship/maritime_pipeline/data/general.jsonl`

If neither exists, `build_general_replay.py` will fail unless you pass `--allow-empty`.

## Notes

- Modal verbs are preserved by design: cleaning is conservative and avoids edits that could change "shall/should" semantics.
- `eval_set.jsonl` is intentionally a template. You should manually fill questions + expected answers + citations.
