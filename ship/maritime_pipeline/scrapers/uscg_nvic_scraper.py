"""
uscg_nvic_scraper.py — US Coast Guard Navigation & Vessel Inspection Circulars downloader.

Source  : https://www.dco.uscg.mil/Our-Organization/NVIC/
Licence : US Government — public domain
These are official USCG policy circulars covering vessel inspection, crew certification, etc.

Usage:
    cd maritime_pipeline
    python scrapers/uscg_nvic_scraper.py
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "uscg_nvic_scraper.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("uscg_nvic")

BASE_URL     = "https://www.dco.uscg.mil"
NVIC_INDEX   = "https://www.dco.uscg.mil/Our-Organization/NVIC/"
# USCG also publishes NVICs via CGMIX XML — more reliable than scraping HTML
CGMIX_BASE   = "https://cgmix.uscg.mil/icsms/nvic/nvic.aspx"
SOURCE_NAME  = "uscg_nvic"
OUT_DIR      = SOURCES[SOURCE_NAME]
METADATA_FILE = OUT_DIR / "metadata.jsonl"
RATE_LIMIT   = DEFAULT_RATE_LIMIT_SECONDS

SESSION = requests.Session()
SESSION.headers.update({
    **DEFAULT_HEADERS,
    "User-Agent": "MaritimeAI-DataCollector/1.0 (Educational Research)",
})


def _get(url: str, stream: bool = False, **kwargs) -> requests.Response:
    delay = RATE_LIMIT
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            time.sleep(delay)
            resp = SESSION.get(url, timeout=REQUEST_TIMEOUT, stream=stream,
                               allow_redirects=True, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d for %s: %s", attempt, MAX_RETRIES, url, exc)
            if attempt == MAX_RETRIES:
                raise
            delay = min(delay * 2, 60)
    raise RuntimeError("Unreachable")


def _scrape_nvic_index_html() -> list[dict]:
    """Parse the DCO USCG NVIC index page (and sub-pages by year)."""
    items: list[dict] = []
    seen_urls: set[str] = set()

    log.info("Fetching NVIC index: %s", NVIC_INDEX)
    try:
        resp = _get(NVIC_INDEX)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find year links that lead to sub-pages with NVICs
        year_links: list[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            # Year pages like /NVIC/2023/
            if re.search(r"/NVIC/\d{4}/?$", href, re.IGNORECASE):
                year_links.append(urljoin(BASE_URL, href))
            # Or direct PDF links on index page
            elif ".pdf" in href.lower():
                pdf_url = urljoin(BASE_URL, href)
                if pdf_url not in seen_urls:
                    seen_urls.add(pdf_url)
                    nvic_m = re.search(r"(?:NVIC[_\-\s]?)?(\d{2}[_\-]\d{2,4})", text + href,
                                       re.IGNORECASE)
                    items.append({
                        "nvic": nvic_m.group(1).replace("_", "-") if nvic_m else "",
                        "title": text,
                        "pdf_url": pdf_url,
                        "year": "",
                        "date": "",
                    })

        # Fetch each year sub-page
        for year_url in tqdm(year_links, desc="Year pages", unit="year"):
            try:
                yr_resp = _get(year_url)
                yr_soup = BeautifulSoup(yr_resp.text, "html.parser")
                year_str = re.search(r"/(\d{4})/?$", year_url)
                year = year_str.group(1) if year_str else ""

                for a in yr_soup.find_all("a", href=True):
                    href = a["href"]
                    if ".pdf" not in href.lower():
                        continue
                    pdf_url = urljoin(BASE_URL, href)
                    if pdf_url in seen_urls:
                        continue
                    seen_urls.add(pdf_url)
                    text = a.get_text(strip=True)
                    nvic_m = re.search(r"(\d{2}[_\-]\d{2,4})", text + href)
                    items.append({
                        "nvic": nvic_m.group(1).replace("_", "-") if nvic_m else "",
                        "title": text,
                        "pdf_url": pdf_url,
                        "year": year,
                        "date": "",
                    })
            except Exception as exc:
                log.warning("Year page %s failed: %s", year_url, exc)

    except Exception as exc:
        log.error("Index page failed: %s", exc)

    log.info("HTML scrape: %d NVIC PDFs found", len(items))
    return items


def _scrape_cgmix() -> list[dict]:
    """
    CGMIX provides a more structured NVIC listing if the HTML approach is thin.
    This fetches the CGMIX NVIC list.
    """
    items: list[dict] = []
    try:
        resp = _get(CGMIX_BASE)
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            nvic_cell = cells[0].get_text(strip=True)
            title_cell = cells[1].get_text(strip=True)
            link = row.find("a", href=True)
            if link:
                pdf_url = urljoin(CGMIX_BASE, link["href"])
                items.append({
                    "nvic": nvic_cell,
                    "title": title_cell,
                    "pdf_url": pdf_url,
                    "year": nvic_cell[:4] if nvic_cell[:4].isdigit() else "",
                    "date": "",
                })
        log.info("CGMIX: %d NVICs found", len(items))
    except Exception as exc:
        log.warning("CGMIX scrape failed: %s", exc)
    return items


def _download_pdf(item: dict) -> bool:
    pdf_url = item["pdf_url"]
    if not pdf_url:
        return False
    if is_downloaded(pdf_url):
        return True

    filename = pdf_url.split("/")[-1].split("?")[0]
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    if item.get("nvic"):
        filename = f"NVIC_{item['nvic']}_{filename}"
    filename = re.sub(r"[^A-Za-z0-9_.\-]", "_", filename)

    sub = OUT_DIR / (item.get("year") or "misc")
    sub.mkdir(parents=True, exist_ok=True)
    out_path = sub / filename

    mark_download_pending(pdf_url, SOURCE_NAME)
    try:
        resp = _get(pdf_url, stream=True)
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(65536):
                fh.write(chunk)
        h = sha256_file(out_path)
        n = out_path.stat().st_size
        mark_download_done(pdf_url, out_path, h, n)
        with open(METADATA_FILE, "a") as mf:
            mf.write(json.dumps({**item, "local_path": str(out_path),
                                  "downloaded_at": datetime.utcnow().isoformat()}) + "\n")
        log.info("✓ %s (%.1f KB)", out_path.name, n / 1024)
        return True
    except Exception as exc:
        log.error("✗ %s: %s", pdf_url, exc)
        mark_download_failed(pdf_url, str(exc))
        return False


def run() -> None:
    init_db()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = _scrape_nvic_index_html()

    if len(items) < 20:
        log.info("HTML scrape thin — supplementing with CGMIX …")
        cgmix = _scrape_cgmix()
        existing_urls = {i["pdf_url"] for i in items}
        for item in cgmix:
            if item["pdf_url"] not in existing_urls:
                items.append(item)

    log.info("Total NVICs to download: %d", len(items))

    ok = fail = skip = 0
    for item in tqdm(items, desc="Downloading NVICs", unit="pdf"):
        if is_downloaded(item["pdf_url"]):
            skip += 1
            continue
        if _download_pdf(item):
            ok += 1
        else:
            fail += 1

    log.info("Done. Downloaded=%d  Failed=%d  Skipped=%d", ok, fail, skip)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="USCG NVIC downloader")
    ap.parse_args()
    run()
