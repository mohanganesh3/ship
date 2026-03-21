# Data Preparation Master Plan

This file was originally intended to store the full **"Data Preparation Master Plan — From Raw Files to Training‑Ready Artifacts"** text that was provided in chat.

At the moment, only a placeholder line existed in the repo. To avoid inventing or corrupting the plan text, this document now:

1) Records the **Stage‑0 artifact contract** implemented in code, and
2) Provides the **entrypoints** and expected directories.

If you want the full master plan text preserved verbatim, paste it into this file (replacing the section below) and I’ll keep all subsequent edits consistent with it.

## Stage‑0 implementation entrypoints

All Stage‑0 builders live in `ship/maritime_pipeline/stage0/`.

Run from `ship/maritime_pipeline/`:

- `python -m stage0.run_stage0 --allow-empty-general`

The flag `--allow-empty-general` is a temporary escape hatch to let the pipeline run even if no general-domain corpus has been provided yet.

## Stage‑0 artifact checklist (produced in `data/final/`)

- `cpt_corpus.jsonl`
	- Canonical maritime pretraining corpus.
	- Each record is traceable via `source_id`, and includes source metadata (`source_type`, `source_url` when known, `doc_type`, `jurisdiction`, etc.).

- `filter_report.jsonl`
	- Every filtered/rejected item with a machine-readable `reason`.

- `cpt_corpus_deduped.jsonl`
	- Deduplicated corpus using MinHash LSH.
	- Thresholds are **doc_type-aware** (e.g., stricter for `regulation`).

- `dedup_report.jsonl`
	- Every near-duplicate removal as `{removed_id -> kept_id}` plus threshold used.

- `general_replay.jsonl`
	- General-domain replay corpus (must be user-provided under `data/general/**` or `data/general.jsonl`).

- `cpt_val_maritime.jsonl`
	- Maritime validation split from the deduped corpus.

- `cpt_val_general.jsonl`
	- General validation split from the general replay corpus.

- `chunks.jsonl`
	- Chunked records intended for SFT dataset construction.
	- Chunking is procedure-preserving (tries not to split step blocks).

- `eval_set.jsonl`
	- Evaluation scaffold (manual fill required): each row references a `chunk_id`.

- `pipeline_audit.log`
	- Append-only log capturing every Stage‑0 command executed and its stdout/stderr.

## Current safety-critical constraints enforced

- Traceability: every record keeps a human-readable `source_id`.
- Conservative cleaning: whitespace + obvious PDF artifacts only; no transformations that would rewrite modal verbs.

## Known gaps (deliberate)

- `eval_set.jsonl` is scaffolding only; it does **not** auto-generate questions.
- A real `general_replay.jsonl` requires you to place a general-domain corpus on disk.
