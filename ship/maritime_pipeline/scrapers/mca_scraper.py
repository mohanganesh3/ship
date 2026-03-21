"""
mca_scraper.py — UK Maritime & Coastguard Agency notice downloader.

Covers:
  MGN  Marine Guidance Notes     https://www.gov.uk/guidance/marine-guidance-notes-mgns
  MSN  Merchant Shipping Notices https://www.gov.uk/guidance/merchant-shipping-notices-msns
  MIN  Marine Information Notes  https://www.gov.uk/guidance/marine-information-notes-mins

Licence: Open Government Licence v3.0 (free for AI training)

Usage:
    cd maritime_pipeline
    python scrapers/mca_scraper.py [--types mgn msn min]
"""

import sys
import re
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SOURCES, DEFAULT_HEADERS, DEFAULT_RATE_LIMIT_SECONDS,
    MAX_RETRIES, REQUEST_TIMEOUT, LOGS_DIR,
)
from db import (
    init_db, is_downloaded, mark_download_pending,
    mark_download_done, mark_download_failed, sha256_file,
)

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "mca_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("mca")

# ── source config ─────────────────────────────────────────────────────────────
BASE_URL   = "https://www.gov.uk"
SOURCE_MAP = {
    "mgn": {
        "url": "https://www.gov.uk/government/collections/marine-guidance-notices-mgns",
        "label": "Marine Guidance Note",
    },
    "msn": {
        "url": "https://www.gov.uk/government/collections/merchant-shipping-notices-msns",
        "label": "Merchant Shipping Notice",
    },
    "min": {
        "url": "https://www.gov.uk/government/collections/marine-information-notes-mins",
        "label": "Marine Information Note",
    },
}
OUT_DIR       = SOURCES["mca"]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT    = DEFAULT_RATE_LIMIT_SECONDS

# ── HTTP session ──────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
})


def _get(url: str, stream: bool = False) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _extract_pdf_links_from_page(soup: BeautifulSoup) -> list[str]:
    """Return all PDF hrefs on the page."""
    pdfs: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" in href.lower():
            pdfs.append(urljoin(BASE_URL, href))
    return pdfs


def _parse_notice_index(page_url: str, notice_type: str) -> list[dict]:
    """
    GOV.UK guidance pages list notices either inline or as tables.
    Walk all <a> tags to find 'MGN NNN', 'MSN NNN', 'MIN NNN' pattern links.
    """
    log.info("Fetching index: %s", page_url)
    resp = _get(page_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    pattern = re.compile(
        rf"\b{notice_type.upper()}\s*[\u2013\-]?\s*(\d+)", re.IGNORECASE
    )

    items: list[dict] = []
    seen: set[str] = set()

    # Strategy A: direct PDF links on the index page
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_href = urljoin(BASE_URL, href)
        text = a.get_text(strip=True)

        m = pattern.search(text) or pattern.search(href)
        number = m.group(1) if m else ""

        if ".pdf" in href.lower() and full_href not in seen:
            seen.add(full_href)
            items.append({
                "notice_type": notice_type.upper(),
                "number": number,
                "title": text or f"{notice_type.upper()} {number}",
                "pdf_url": full_href,
                "detail_url": "",
                "date": "",
            })

        elif href.startswith("/") and full_href not in seen and "gov.uk" in full_href:
            # Detail page link — we'll resolve the PDF later
            if m:  # only if it looks like a notice link
                seen.add(full_href)
                items.append({
                    "notice_type": notice_type.upper(),
                    "number": number,
                    "title": text,
                    "pdf_url": "",
                    "detail_url": full_href,
                    "date": "",
                })

    log.info("Found %d %s items from index", len(items), notice_type.upper())
    return items


def _resolve_pdf_from_detail(detail_url: str) -> str:
    """Visit a GOV.UK detail page to find the PDF download link."""
    try:
        resp = _get(detail_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        pdf_links = _extract_pdf_links_from_page(soup)
        if pdf_links:
            return pdf_links[0]
    except Exception as exc:
        log.warning("Cannot resolve PDF at %s: %s", detail_url, exc)
    return ""


def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        log.warning("No PDF URL for %s %s", item["notice_type"], item["number"])
        return False
    if is_downloaded(pdf_url):
        return True

    # Build local filename: MGN_1234_some_name.pdf
    raw_name = pdf_url.split("/")[-1].split("?")[0]
    if not raw_name.endswith(".pdf"):
        raw_name += ".pdf"
    prefix = f"{item['notice_type']}_{item['number']}_" if item["number"] else ""
    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", prefix + raw_name)
    # Subdirectory per notice type
    sub_dir = OUT_DIR / item["notice_type"].lower()
    sub_dir.mkdir(parents=True, exist_ok=True)
    out_path = sub_dir / filename

    mark_download_pending(pdf_url, f"mca_{item['notice_type'].lower()}")
    try:
        resp = _get(pdf_url, stream=True)
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(65536):
                fh.write(chunk)
        file_hash = sha256_file(out_path)
        n_bytes = out_path.stat().st_size
        mark_download_done(pdf_url, out_path, file_hash, n_bytes)
        with open(METADATA_FILE, "a", encoding="utf-8") as mf:
            mf.write(json.dumps({**item, "local_path": str(out_path),
                                  "downloaded_at": datetime.utcnow().isoformat()}) + "\n")
        log.info("✓ %s → %s (%.1f KB)", filename, out_path.name, n_bytes / 1024)
        return True
    except Exception as exc:
        log.error("✗ Failed %s: %s", pdf_url, exc)
        mark_download_failed(pdf_url, str(exc))
        return False


def run(types: list[str] = None) -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    types = types or list(SOURCE_MAP.keys())

    all_items: list[dict] = []
    for notice_type in types:
        cfg = SOURCE_MAP[notice_type]
        try:
            items = _parse_notice_index(cfg["url"], notice_type)
            all_items.extend(items)
        except Exception as exc:
            log.error("Failed to parse index for %s: %s", notice_type, exc)

    # Resolve missing PDF URLs from detail pages
    needs_resolve = [i for i in all_items if not i["pdf_url"] and i["detail_url"]]
    log.info("Resolving %d detail pages for PDF links …", len(needs_resolve))
    for item in tqdm(needs_resolve, desc="Resolving PDFs", unit="page"):
        item["pdf_url"] = _resolve_pdf_from_detail(item["detail_url"])

    # Download all PDFs
    ok = fail = skip = 0
    for item in tqdm(all_items, desc="Downloading notices", unit="pdf"):
        if not item.get("pdf_url"):
            skip += 1
            continue
        if is_downloaded(item["pdf_url"]):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="UK MCA Marine Notices scraper")
    ap.add_argument("--types", nargs="+", choices=["mgn", "msn", "min"],
                    default=["mgn", "msn", "min"], help="Notice types to download")
    args = ap.parse_args()
    run(types=args.types)
