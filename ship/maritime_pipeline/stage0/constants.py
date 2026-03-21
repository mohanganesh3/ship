"""Controlled vocabularies and constants for Stage-0 corpus preparation."""

from __future__ import annotations

DOMAIN_TAGS: set[str] = {
    "SOLAS",
    "MARPOL",
    "STCW",
    "COLREG",
    "ENGINES",
    "NAVIGATION",
    "SAFETY",
    "INCIDENT",
    "GENERAL",
    "STABILITY",
    "CARGO",
    "POLLUTION",
    "ELECTRICAL",
    "COMMUNICATIONS",
}

DOC_TYPES: set[str] = {
    "regulation",
    "circular",
    "guidance",
    "accident_investigation",
    "near_miss",
    "textbook",
    "encyclopedia",
    "academic_abstract",
    "news_article",
    "synthetic_procedure",
    "unknown",
}

QUALITY_TIERS: set[str] = {"A", "B", "C"}

JURISDICTIONS: set[str] = {
    "IMO_INTERNATIONAL",
    "UK_MCA",
    "US_USCG",
    "EU_EMSA",
    "CANADA_TC",
    "GERMANY_BSU",
    "GENERAL",
}

DIFFICULTY_HINTS: set[str] = {
    "factual_simple",
    "factual_technical",
    "procedural_sequential",
    "regulatory_exception",
    "diagnostic_multistep",
    "calculation",
}

# Maritime keyword list for lightweight domain tagging and replay filtering.
MARITIME_KEYWORDS: set[str] = {
    "ballast",
    "bilge",
    "bunkering",
    "colreg",
    "colregs",
    "dwt",
    "eca",
    "ecdis",
    "engine room",
    "fps",
    "freeboard",
    "gmdss",
    "gyro",
    "hull",
    "imo",
    "inmarsat",
    "isgott",
    "load line",
    "marpol",
    "muster",
    "oily water",
    "pilotage",
    "port state",
    "psc",
    "rudder",
    "solas",
    "stability",
    "stcw",
    "tank sounding",
    "tonnage",
    "vtms",
}

SAFETY_CRITICAL_TRIGGERS: set[str] = {
    "abandon ship",
    "man overboard",
    "fire",
    "lifeboat",
    "liferaft",
    "enclosed space",
    "co2",
    "evacuation",
    "muster",
    "rescue",
    "emergency",
}
