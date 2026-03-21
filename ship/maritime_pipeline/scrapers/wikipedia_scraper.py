"""
wikipedia_scraper.py — Wikipedia maritime category article extractor.

Uses the wikipedia-api library (wraps MediaWiki API) to pull all articles from:
  - Category:Marine engineering      - Category:Maritime transport
  - Category:Navigation              - Category:Ship types
  - Category:Maritime safety         - Category:Shipbuilding

Wikitext is converted to plain English using the library's built-in summarisation.
Each article is saved as a JSONL record.

Usage:
    pip install wikipedia-api
    cd maritime_pipeline
    python scrapers/wikipedia_scraper.py [--lang en]
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_RATE_LIMIT_SECONDS, LOGS_DIR,
)
from db import init_db

try:
    import wikipediaapi
except ImportError:
    raise SystemExit(
        "wikipedia-api not installed. Run: pip install wikipedia-api"
    )

from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "wikipedia_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("wikipedia")

SOURCE_NAME  = "wikipedia"
OUT_DIR      = SOURCES[SOURCE_NAME]
OUT_JSONL    = OUT_DIR.parent.parent.parent / "data" / "extracted_text" / "wikipedia_maritime.jsonl"
RATE_LIMIT   = max(DEFAULT_RATE_LIMIT_SECONDS, 0.5)

MARITIME_CATEGORIES = [
    "Marine engineering",
    "Maritime transport",
    "Navigation",
    "Ship types",
    "Maritime safety",
    "Shipbuilding",
    "Naval architecture",
    "Marine propulsion",
    "Seamanship",
    "Nautical terminology",
]

# Wikitext cleaning patterns
_RE_TEMPLATE   = re.compile(r"\{\{[^}]*\}\}")
_RE_WIKILINK   = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]")
_RE_EXTLINK    = re.compile(r"\[https?://\S+ ([^\]]+)\]")
_RE_MARKUP     = re.compile(r"'{2,3}|={2,6}|<!--.*?-->", re.DOTALL)
_RE_WHITESPACE = re.compile(r"\n{3,}")


def _clean_text(raw: str) -> str:
    """Remove common MediaWiki markup from raw wikitext."""
    text = _RE_TEMPLATE.sub("", raw)
    text = _RE_WIKILINK.sub(r"\1", text)
    text = _RE_EXTLINK.sub(r"\1", text)
    text = _RE_MARKUP.sub("", text)
    text = _RE_WHITESPACE.sub("\n\n", text)
    return text.strip()


def _collect_category_members(
    wiki: "wikipediaapi.Wikipedia",
    category_name: str,
    seen: set[str],
    depth: int = 0,
    max_depth: int = 2,
) -> list[str]:
    """Recursively collect article titles from a category (up to max_depth)."""
    titles: list[str] = []
    cat_page = wiki.page(f"Category:{category_name}")
    if not cat_page.exists():
        log.warning("Category not found: %s", category_name)
        return titles

    for member in cat_page.categorymembers.values():
        if member.ns == wikipediaapi.Namespace.MAIN:   # article
            if member.title not in seen:
                seen.add(member.title)
                titles.append(member.title)
        elif member.ns == wikipediaapi.Namespace.CATEGORY and depth < max_depth:
            sub_name = member.title.replace("Category:", "")
            time.sleep(RATE_LIMIT * 0.5)
            sub_titles = _collect_category_members(wiki, sub_name, seen,
                                                   depth + 1, max_depth)
            titles.extend(sub_titles)

    return titles


def _fetch_article(wiki: "wikipediaapi.Wikipedia", title: str) -> dict | None:
    """Fetch a single article and return a clean record."""
    try:
        time.sleep(RATE_LIMIT)
        page = wiki.page(title)
        if not page.exists():
            return None
        # wikipedia-api exposes plain text via .text (it strips most markup)
        body = page.text
        if not body or len(body.split()) < 50:
            return None
        return {
            "title": page.title,
            "url": page.fullurl,
            "summary": page.summary[:1000],
            "text": body,
            "word_count": len(body.split()),
            "source": SOURCE_NAME,
            "scraped_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        log.error("Failed to fetch '%s': %s", title, exc)
        return None


def run(lang: str = "en", max_depth: int = 2) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    wiki = wikipediaapi.Wikipedia(
        language=lang,
        user_agent="MaritimeAI-DataCollector/1.0 (Educational Research; Wikipedia API)",
        extract_format=wikipediaapi.ExtractFormat.WIKI,
    )

    # Load already-done page titles
    done_titles: set[str] = set()
    if OUT_JSONL.exists():
        with open(OUT_JSONL) as f:
            for line in f:
                if line.strip():
                    try:
                        done_titles.add(json.loads(line)["title"])
                    except Exception:
                        pass
        log.info("Resuming: %d articles already done", len(done_titles))

    # Collect all article titles from all categories
    all_titles: list[str] = []
    seen_titles: set[str] = set(done_titles)
    for cat in MARITIME_CATEGORIES:
        log.info("Collecting members of Category:%s …", cat)
        titles = _collect_category_members(wiki, cat, seen_titles, max_depth=max_depth)
        log.info("  +%d articles", len(titles))
        all_titles.extend(titles)

    log.info("Total articles to fetch: %d", len(all_titles))

    ok = fail = 0
    with open(OUT_JSONL, "a", encoding="utf-8") as out_fh:
        for title in tqdm(all_titles, desc="Fetching Wikipedia articles", unit="article"):
            record = _fetch_article(wiki, title)
            if record:
                out_fh.write(json.dumps(record) + "\n")
                out_fh.flush()
                ok += 1
            else:
                fail += 1

    log.info("Done. Fetched=%d  Failed=%d  Previously done=%d", ok, fail, len(done_titles))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Wikipedia maritime category scraper")
    ap.add_argument("--lang", default="en", help="Wikipedia language code")
    ap.add_argument("--max-depth", type=int, default=2,
                    help="Category recursion depth (default: 2)")
    args = ap.parse_args()
    run(lang=args.lang, max_depth=args.max_depth)
