"""Stage-0 (data preparation) pipeline.

This package builds training-ready artifacts from raw/extracted maritime sources.

Design goals:
- Safety-critical traceability: every record retains a human-readable source_id.
- Reproducibility: deterministic outputs given the same inputs + seed.
- Auditable: every rejection and dedup removal is logged.

See: ship/DATA_PREPARATION_MASTER_PLAN.md
"""
