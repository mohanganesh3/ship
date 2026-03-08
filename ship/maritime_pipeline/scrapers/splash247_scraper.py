#!/usr/bin/env python3
"""
Splash247 scraper — sitemap-based, year by year (2012-2026)
Target: 10,000 articles from splash247.com
"""
import json, logging, re, time
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SOURCES, DEFAULT_HEADERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("splash247")

BASE_URL    = "https://splash247.com"
MAX_ARTICLES = 10000
RATE_LIMIT   = 0.7
OUT_FILE     = Path(__file__).parent.parent / "data" / "extracted_text" / "splash247_articles.jsonl"

# Year sitemaps from newest to oldest
SITEMAP_YEARS = list(range(2026, 2011, -1))

SKIP_PATTERNS = ["wp-content/uploads", "cdn-cgi", "?", "#", ".jpg", ".jpeg",
                 ".png", ".gif", ".pdf", "-author-", "sitemap", "page/",
                 "/tag/", "/category/", "author/"]


def fetch(url, timeout=20):
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning("Fetch error %s: %s", url, e)
        return None


def collect_urls():
    all_urls = []
    for year in SITEMAP_YEARS:
        sm_url = f"{BASE_URL}/sitemap-posttype-post.{year}.xml"
        log.info("Fetching sitemap year %d …", year)
        xml = fetch(sm_url)
        if not xml:
            continue
        soup = BeautifulSoup(xml, "lxml-xml")
        locs = [t.get_text(strip=True) for t in soup.find_all("loc")]
        year_urls = []
        for u in locs:
            path = u.replace(BASE_URL, "").strip("/")
            if not path:
                continue
            if any(p in path for p in SKIP_PATTERNS):
                continue
            # root-level slug only (no extra slashes)
            if "/" in path:
                continue
            year_urls.append(u)
        log.info("  Year %d: %d article URLs", year, len(year_urls))
        all_urls.extend(year_urls)
        if len(all_urls) >= MAX_ARTICLES * 2:
            break
        time.sleep(0.5)
    return all_urls


def extract_article(html, url):
    soup = BeautifulSoup(html, "html.parser")
    # Title
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Content selectors
    content_div = (
        soup.find("div", class_=re.compile(r"entry-content|post-content|article-body|td-post-content"))
        or soup.find("article")
        or soup.find("main")
    )
    if not content_div:
        return None

    # Remove noise
    for tag in content_div.find_all(["script", "style", "figure", "aside",
                                      "nav", "footer", ".sharedaddy", "iframe"]):
        tag.decompose()

    text = content_div.get_text(separator=" ", strip=True)
    text = re.sub(r"\s{2,}", " ", text).strip()
    word_count = len(text.split())

    if word_count < 80:
        return None

    return {"url": url, "title": title, "content": text, "word_count": word_count,
            "source": "splash247"}


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load already saved URLs
    seen_urls = set()
    if OUT_FILE.exists():
        with open(OUT_FILE) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    seen_urls.add(d["url"])
                except Exception:
                    pass
    log.info("Already saved: %d articles", len(seen_urls))

    all_links = collect_urls()
    log.info("Total unique article links collected: %d", len(all_links))
    all_links = [u for u in all_links if u not in seen_urls]
    log.info("After dedup: %d new URLs to fetch", len(all_links))

    saved = len(seen_urls)
    with open(OUT_FILE, "a") as out:
        for url in all_links:
            if saved >= MAX_ARTICLES:
                break
            html = fetch(url)
            if not html:
                time.sleep(RATE_LIMIT * 2)
                continue
            article = extract_article(html, url)
            if not article:
                time.sleep(RATE_LIMIT)
                continue
            out.write(json.dumps(article, ensure_ascii=False) + "\n")
            out.flush()
            saved += 1
            log.info("Saved [%d]: %s (%d words)", saved, article["title"][:60], article["word_count"])
            time.sleep(RATE_LIMIT)

    log.info("Done. Saved=%d articles to %s", saved, OUT_FILE)


if __name__ == "__main__":
    main()
