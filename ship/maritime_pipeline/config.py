"""
config.py – Single source of truth for all pipeline parameters.
Edit this file rather than touching individual scraper/filter settings.
"""
from pathlib import Path
import os

# ── Root directories ──────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DATA_DIR       = BASE_DIR / "data"
RAW_PDFS_DIR   = DATA_DIR / "raw_pdfs"
EXTRACTED_DIR  = DATA_DIR / "extracted_text"
FILTERED_DIR   = DATA_DIR / "filtered"
DEDUPED_DIR    = DATA_DIR / "deduped"
CHUNKS_DIR     = DATA_DIR / "chunks"
FINAL_DIR      = DATA_DIR / "final"
LOGS_DIR       = BASE_DIR / "logs"

# Make sure all dirs exist
for _d in [RAW_PDFS_DIR, EXTRACTED_DIR, FILTERED_DIR,
           DEDUPED_DIR, CHUNKS_DIR, FINAL_DIR, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── SQLite progress database ──────────────────────────────────────────────────
DB_PATH = BASE_DIR / "pipeline_progress.db"

# ── HTTP settings ─────────────────────────────────────────────────────────────
DEFAULT_HEADERS = {
    "User-Agent": (
        "MaritimeAIResearchBot/1.0 "
        "(Academic data collection for NLP; contact: research@example.com)"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}
DEFAULT_RATE_LIMIT_SECONDS = 1.5   # seconds between requests per domain
MAX_RETRIES                = 5
REQUEST_TIMEOUT            = 60    # seconds

# ── PDF Extraction ────────────────────────────────────────────────────────────
MARKER_WORKERS    = 4              # parallel Marker processes
MARKER_GPU        = False          # set True if CUDA available
PYMUPDF_FALLBACK  = True          # fall back to PyMuPDF on Marker failure

# ── Quality Filter ────────────────────────────────────────────────────────────
MIN_WORDS_PER_DOC              = 150     # discard documents shorter than this
MAX_WORDS_PER_DOC              = 500_000 # discard absurdly large garbage
ENGLISH_CONFIDENCE_THRESHOLD   = 0.90    # langdetect confidence
# Heuristic quality score thresholds (0-1)
MIN_QUALITY_SCORE              = 0.40
# Perplexity (if KenLM enabled)  – values below this are kept
PERPLEXITY_THRESHOLD           = 500.0
KENLM_MODEL_PATH               = os.getenv("KENLM_MODEL", "")  # optional

# ── Deduplication ─────────────────────────────────────────────────────────────
MINHASH_NUM_PERM         = 128     # hash functions
MINHASH_THRESHOLD        = 0.85    # Jaccard similarity → near-duplicate
EXACT_HASH_FIRST         = True    # do exact SHA-256 pass before MinHash

# ── Chunking ─────────────────────────────────────────────────────────────────
CPT_CHUNK_WORDS          = 1536
CPT_OVERLAP_WORDS        = 128
SFT_CHUNK_WORDS          = 384
SFT_OVERLAP_WORDS        = 48

# ── Sources (name → raw PDF subdirectory) ─────────────────────────────────────
SOURCES = {
    "maib":          RAW_PDFS_DIR / "maib",
    "mca":           RAW_PDFS_DIR / "mca",
    "ntsb":          RAW_PDFS_DIR / "ntsb",
    "marine_insight": RAW_PDFS_DIR / "marine_insight",
    "wartsila":      RAW_PDFS_DIR / "wartsila",
    "wikipedia":     RAW_PDFS_DIR / "wikipedia",
    "gard":          RAW_PDFS_DIR / "gard",
    "ukpandi":       RAW_PDFS_DIR / "ukpandi",
    "nepia":         RAW_PDFS_DIR / "nepia",
    "emsa":          RAW_PDFS_DIR / "emsa",
    "steamship":     RAW_PDFS_DIR / "steamship",
    "itopf":         RAW_PDFS_DIR / "itopf",
    "uscg_nvic":     RAW_PDFS_DIR / "uscg_nvic",
    "dutch_safety":  RAW_PDFS_DIR / "dutch_safety",
    "nsia":          RAW_PDFS_DIR / "nsia",
    "bsu":           RAW_PDFS_DIR / "bsu",
    "iacs":          RAW_PDFS_DIR / "iacs",
    "dnv":           RAW_PDFS_DIR / "dnv",
    "imo":           RAW_PDFS_DIR / "imo",
    "openalex":      RAW_PDFS_DIR / "openalex",
    "chirp":         RAW_PDFS_DIR / "chirp",
    "ocimf":         RAW_PDFS_DIR / "ocimf",
    "transport_canada": RAW_PDFS_DIR / "transport_canada",
    "lloyds_register": RAW_PDFS_DIR / "lloyds_register",
    "paris_mou":     RAW_PDFS_DIR / "paris_mou",
    "skuld":         RAW_PDFS_DIR / "skuld",
    "abs":           RAW_PDFS_DIR / "abs",
    "bimco":         RAW_PDFS_DIR / "bimco",
    "classnk":       RAW_PDFS_DIR / "classnk",
    "hellenic":      RAW_PDFS_DIR / "hellenic",
    "standard_club": RAW_PDFS_DIR / "standard_club",
    "safety4sea":    RAW_PDFS_DIR / "safety4sea",
    "gcaptain":      RAW_PDFS_DIR / "gcaptain",
    "maritime_executive": RAW_PDFS_DIR / "maritime_executive",
}
for _p in SOURCES.values():
    _p.mkdir(parents=True, exist_ok=True)

# ── Target token counts ───────────────────────────────────────────────────────
TARGET_TOKENS_TOTAL  = 40_000_000   # ~40M tokens
WORDS_PER_TOKEN_EST  = 0.75         # rough estimation factor
